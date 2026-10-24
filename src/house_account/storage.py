from __future__ import annotations

import fcntl
import hashlib
import json
import os
import sqlite3
import tempfile
from collections import Counter, defaultdict
from collections.abc import Callable, Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .model import Observation, canonical_json, digest

TABLES = {
    'provider': 'providers', 'customer': 'customers', 'property': 'properties',
    'job': 'jobs', 'estimate': 'estimates', 'visit': 'visits',
    'calendar_block': 'calendar_blocks', 'profile': 'profiles', 'street_segment': 'street_segments',
}


class ImportFailure(ValueError):
    pass


def connect_readonly(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)
    connection.execute('PRAGMA foreign_keys=ON')
    connection.execute('PRAGMA query_only=ON')
    return connection


def inventory(root: Path, classify: Callable[[str, Path], str]) -> list[dict[str, Any]]:
    expected = json.loads(Path(__file__).with_name('pack_manifest.json').read_text())
    paths = {p.relative_to(root).as_posix(): p for p in root.rglob('*') if p.is_file()}
    required = {p for p in expected if not p.endswith('.DS_Store')}
    missing = required - paths.keys()
    unexpected = {p for p in paths if not p.endswith('.DS_Store')} - required
    if missing or unexpected:
        raise ImportFailure(f'input manifest differs: {len(missing)} missing, {len(unexpected)} unexpected files')
    if any(p.is_symlink() or root.resolve() not in p.resolve().parents for p in paths.values()):
        raise ImportFailure('source symlinks are not supported')
    return [{'path': name, 'bytes': path.stat().st_size,
                 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                 'role': classify(name, path)}
            for name, path in sorted(paths.items())]


def schema(connection: sqlite3.Connection) -> None:
    connection.executescript('''
    PRAGMA foreign_keys=ON;
    PRAGMA journal_mode=DELETE;
    PRAGMA synchronous=FULL;
    CREATE TABLE snapshot(id TEXT PRIMARY KEY, ingested_at TEXT NOT NULL, manifest_hash TEXT NOT NULL);
    CREATE TABLE input_files(path TEXT PRIMARY KEY, bytes INTEGER NOT NULL, sha256 TEXT NOT NULL, role TEXT NOT NULL);
    CREATE TABLE source_records(
        id TEXT PRIMARY KEY, source TEXT NOT NULL, account TEXT NOT NULL, kind TEXT NOT NULL,
        source_key TEXT NOT NULL, content_hash TEXT NOT NULL, snapshot_at TEXT,
        ingested_at TEXT NOT NULL, raw_json TEXT NOT NULL,
        UNIQUE(source,account,kind,source_key));
    CREATE TABLE occurrences(
        id INTEGER PRIMARY KEY, record_id TEXT NOT NULL REFERENCES source_records(id),
        file TEXT NOT NULL REFERENCES input_files(path), locator TEXT NOT NULL,
        disposition TEXT NOT NULL CHECK(disposition IN ('accepted','duplicate','unresolved','rejected')),
        UNIQUE(file,locator,record_id));
    CREATE TABLE entity_evidence(
        entity_id TEXT NOT NULL, record_id TEXT NOT NULL REFERENCES source_records(id),
        rule TEXT NOT NULL, confidence TEXT NOT NULL, PRIMARY KEY(entity_id,record_id));
    CREATE TABLE issues(
        record_id TEXT NOT NULL REFERENCES source_records(id), code TEXT NOT NULL,
        field TEXT NOT NULL, detail TEXT NOT NULL);
    ''')
    for kind, table in TABLES.items():
        constraints = ''
        if kind == 'visit':
            constraints = ", CHECK((appointment_kind='job' AND job_id IS NOT NULL AND estimate_id IS NULL) OR (appointment_kind='estimate' AND estimate_id IS NOT NULL AND job_id IS NULL))"
        connection.execute(f'''CREATE TABLE {table}(
            id TEXT PRIMARY KEY REFERENCES source_records(id),
            provider_id TEXT REFERENCES providers(id) DEFERRABLE INITIALLY DEFERRED,
            property_id TEXT REFERENCES properties(id) DEFERRABLE INITIALLY DEFERRED,
            customer_id TEXT REFERENCES customers(id) DEFERRABLE INITIALLY DEFERRED,
            job_id TEXT REFERENCES jobs(id) DEFERRABLE INITIALLY DEFERRED,
            estimate_id TEXT REFERENCES estimates(id) DEFERRABLE INITIALLY DEFERRED,
            display_name TEXT, trade TEXT, service TEXT, status TEXT, source_status TEXT,
            amount_minor INTEGER, currency TEXT, start_utc TEXT, end_utc TEXT,
            timezone_origin TEXT, appointment_kind TEXT, attributes_json TEXT NOT NULL
            {constraints})''')
        for field in ('provider_id', 'property_id', 'trade', 'status', 'start_utc'):
            connection.execute(f'CREATE INDEX {table}_{field} ON {table}({field})')
    connection.execute('CREATE INDEX source_lookup ON source_records(source,account,kind)')
    connection.execute('CREATE INDEX issue_code ON issues(code)')


def validate_observation(observation: Observation) -> None:
    entity = observation.normalized
    if observation.kind != entity.kind:
        raise ImportFailure('observation/entity kind mismatch')
    if entity.kind in ('job', 'estimate', 'visit', 'calendar_block', 'profile') and not entity.provider_id:
        raise ImportFailure('entity missing provider reference')
    if entity.kind == 'visit':
        if (entity.appointment_kind == 'job' and entity.job_id and not entity.estimate_id) or entity.appointment_kind == 'estimate' and entity.estimate_id and not entity.job_id:
            pass
        else:
            raise ImportFailure('visit requires exactly one matching parent')
    if (entity.start_utc and entity.end_utc and entity.end_utc <= entity.start_utc
            and not any(issue.code == 'invalid_interval' for issue in observation.issues)):
        raise ImportFailure('non-positive interval without an explicit issue')


def write_snapshot(observations: Iterable[Observation], database: Path,
                   files: list[dict[str, Any]], *, fail_after: int | None = None) -> dict[str, Any]:
    database = database.resolve()
    database.parent.mkdir(parents=True, exist_ok=True)
    lock_path = database.with_suffix(database.suffix + '.lock')
    lock_fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        os.close(lock_fd)
        raise ImportFailure('another importer holds the database lock') from exc
    fd, name = tempfile.mkstemp(prefix='.' + database.name + '.', suffix='.tmp', dir=database.parent)
    os.close(fd)
    temporary = Path(name)
    connection = sqlite3.connect(temporary)
    ingested_at = datetime.now(UTC).isoformat()
    manifest_hash = digest(files)
    counters: dict[str, Counter[str]] = defaultdict(Counter)
    kinds: dict[str, Counter[str]] = defaultdict(Counter)
    hashes: dict[str, str] = {}
    try:
        schema(connection)
        connection.execute('BEGIN')
        connection.executemany('INSERT INTO input_files VALUES(:path,:bytes,:sha256,:role)', files)
        connection.execute('INSERT INTO snapshot VALUES(?,?,?)', (digest([manifest_hash, ingested_at]), ingested_at, manifest_hash))
        for number, observation in enumerate(observations, 1):
            validate_observation(observation)
            content_hash = digest(observation.raw)
            key = observation.id
            counts = counters[observation.source]
            counts['seen'] += 1
            kind_counts = kinds[observation.source + ':' + observation.kind]
            kind_counts['seen'] += 1
            if key in hashes:
                if hashes[key] != content_hash:
                    raise ImportFailure('conflicting payload for an existing source identity')
                disposition = 'duplicate'
            else:
                disposition = 'unresolved' if observation.issues else 'accepted'
                hashes[key] = content_hash
                connection.execute('INSERT INTO source_records VALUES(?,?,?,?,?,?,?,?,?)',
                                   (key, observation.source, observation.account, observation.kind,
                                    observation.key, content_hash, observation.snapshot_at, ingested_at,
                                    canonical_json(observation.raw)))
                entity = observation.normalized.model_dump(exclude={'kind', 'attributes'})
                entity['attributes_json'] = canonical_json(observation.normalized.attributes)
                columns = ','.join(['id', *entity])
                connection.execute(f'INSERT INTO {TABLES[observation.kind]}({columns}) VALUES({",".join("?" for _ in range(len(entity)+1))})', [key, *entity.values()])
                connection.execute('INSERT INTO entity_evidence VALUES(?,?,?,?)',
                                   (key, key, observation.rule, 'high' if not observation.issues else 'low'))
                connection.executemany('INSERT INTO issues VALUES(?,?,?,?)',
                                       [(key, issue.code, issue.field, issue.detail) for issue in observation.issues])
            connection.execute('INSERT INTO occurrences(record_id,file,locator,disposition) VALUES(?,?,?,?)',
                               (key, observation.file, observation.locator, disposition))
            counts[disposition] += 1
            kind_counts[disposition] += 1
            if fail_after is not None and number >= fail_after:
                raise ImportFailure('injected import failure')
        if connection.execute('PRAGMA foreign_key_check').fetchone():
            raise ImportFailure('foreign key validation failed')
        source_files = connection.execute("SELECT count(*) FROM input_files f WHERE role='source' AND NOT EXISTS(SELECT 1 FROM occurrences o WHERE o.file=f.path)").fetchone()[0]
        if source_files:
            raise ImportFailure('source file produced no accounted observations')
        if connection.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ImportFailure('SQLite integrity validation failed')
        counts_by_table = {table: connection.execute(f'SELECT count(*) FROM {table}').fetchone()[0] for table in TABLES.values()}
        report = {
            'schema_version': 1, 'status': 'success', 'ingested_at': ingested_at,
            'manifest_hash': manifest_hash, 'files': files,
            'sources': {source: {field: values[field] for field in ('seen', 'accepted', 'duplicate', 'unresolved', 'rejected')} for source, values in sorted(counters.items())},
            'by_source_kind': {key: {field: values[field] for field in ('seen', 'accepted', 'duplicate', 'unresolved', 'rejected')} for key, values in sorted(kinds.items())},
            'entities': counts_by_table, 'source_records': len(hashes),
            'occurrences': sum(value['seen'] for value in counters.values()),
            'issues': dict(connection.execute('SELECT code,count(*) FROM issues GROUP BY code')),
            'limitations': ['Source-local identities only; P2 reconciliation is not implemented.', 'Calendar recurrence definitions are retained; openings are not calculated.', 'Existing readers retain the previous snapshot until reconnect.'],
        }
        connection.commit()
        connection.close()
        with temporary.open('rb') as handle:
            os.fsync(handle.fileno())
        os.replace(temporary, database)
        try:
            directory_fd = os.open(database.parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        except OSError:
            report['warnings'] = ['Snapshot published, but directory durability could not be confirmed.']
        return report
    finally:
        connection.close()
        temporary.unlink(missing_ok=True)
        Path(str(temporary) + '-journal').unlink(missing_ok=True)
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        os.close(lock_fd)
