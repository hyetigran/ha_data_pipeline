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
from .publication import SCHEMA_VERSION, publish, schema_version
from .registry import seed_registry
from .source_models import MODELS

TABLES = {
    'provider': 'providers', 'customer': 'customers', 'property': 'properties',
    'job': 'jobs', 'estimate': 'estimates', 'visit': 'visits',
    'calendar_block': 'calendar_blocks', 'profile': 'profiles', 'street_segment': 'street_segments',
}


SOURCE_FIELDS = {
    'provider': ('display_name', 'trade'),
    'customer': ('provider_id', 'display_name'),
    'property': ('provider_id', 'customer_id', 'house_number', 'street', 'unit', 'city', 'state', 'postal_code'),
    'job': ('provider_id', 'property_id', 'customer_id', 'trade', 'service', 'status', 'source_status', 'amount_minor', 'currency', 'source_status_updated_at'),
    'estimate': ('provider_id', 'property_id', 'customer_id', 'trade', 'service', 'status', 'source_status', 'amount_minor', 'currency', 'source_status_updated_at'),
    'visit': ('provider_id', 'property_id', 'customer_id', 'job_id', 'estimate_id', 'status', 'source_status', 'start_utc', 'end_utc', 'timezone_origin', 'appointment_kind', 'source_completed_at'),
    'calendar_block': ('provider_id', 'status', 'source_status', 'start_utc', 'end_utc', 'timezone_origin', 'uid', 'start_local', 'end_local', 'all_day', 'end_exclusive', 'rrule', 'recurrence_id', 'transparency'),
    'profile': ('provider_id', 'display_name'),
    'street_segment': ('street_name', 'street_type', 'city', 'state', 'zip', 'from_number', 'to_number', 'start_lat', 'end_lat', 'start_lon', 'end_lon'),
}


class ImportFailure(ValueError):
    pass


def connect_readonly(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)
    connection.execute('PRAGMA foreign_keys=ON')
    connection.execute('PRAGMA query_only=ON')
    connection.execute('BEGIN')
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
    connection.execute(f'PRAGMA user_version={SCHEMA_VERSION}')
    references = {'provider_id':'providers', 'property_id':'properties', 'customer_id':'customers',
                  'job_id':'jobs', 'estimate_id':'estimates'}
    for kind, table in TABLES.items():
        definitions = ['id TEXT PRIMARY KEY NOT NULL REFERENCES source_records(id)']
        for field in SOURCE_FIELDS[kind]:
            column_type = ('INTEGER' if field in ('amount_minor', 'house_number', 'from_number', 'to_number', 'all_day', 'end_exclusive') else 'REAL' if field in ('start_lat', 'end_lat', 'start_lon', 'end_lon') else 'TEXT')
            definition = f'{field} {column_type}'
            if field in references:
                definition += f' REFERENCES {references[field]}(id) DEFERRABLE INITIALLY DEFERRED'
            definitions.append(definition)
        definitions.append('attributes_json TEXT NOT NULL')
        if kind == 'visit':
            definitions.append("CHECK((appointment_kind='job' AND job_id IS NOT NULL AND estimate_id IS NULL) OR (appointment_kind='estimate' AND estimate_id IS NOT NULL AND job_id IS NULL))")
        connection.execute(f'CREATE TABLE {table}(' + ','.join(definitions) + ') STRICT')
        for field in ('provider_id', 'property_id', 'status', 'start_utc'):
            if field in SOURCE_FIELDS[kind]:
                connection.execute(f'CREATE INDEX {table}_{field} ON {table}({field})')
    connection.execute('''CREATE TABLE provider_hour_declarations(
        id TEXT PRIMARY KEY NOT NULL, source_profile_id TEXT NOT NULL REFERENCES profiles(id),
        provider_id TEXT NOT NULL REFERENCES providers(id), weekday INTEGER NOT NULL CHECK(weekday BETWEEN 0 AND 6),
        local_start TEXT, local_end TEXT, timezone_name TEXT NOT NULL,
        declaration_state TEXT NOT NULL CHECK(declaration_state IN ('known','closed','unknown')),
        emergency_only INTEGER NOT NULL CHECK(emergency_only IN (0,1)),
        effective_from TEXT, effective_before TEXT,
        CHECK((declaration_state='known' AND local_start IS NOT NULL AND local_end IS NOT NULL AND local_start<local_end)
            OR (declaration_state<>'known' AND local_start IS NULL AND local_end IS NULL))) STRICT''')
    connection.execute('CREATE INDEX source_lookup ON source_records(source,account,kind)')
    connection.execute('CREATE INDEX issue_code ON issues(code)')


def source_values(observation: Observation, values: dict[str, Any]) -> dict[str, Any]:
    result = {key: values.get(key) for key in SOURCE_FIELDS[observation.kind]}
    attributes = observation.normalized.attributes
    if observation.kind == 'property':
        from .addresses import normalize
        address = normalize(attributes.get('address', {}), [])
        result.update(house_number=address.number, street=address.street or None,
                      unit=address.unit or None, city=address.city or None,
                      state=address.state or None, postal_code=address.postal_code or None)
    elif observation.kind == 'street_segment':
        result.update({key: attributes.get(key) for key in SOURCE_FIELDS['street_segment']})
    elif observation.kind == 'calendar_block':
        recurrence = str(attributes.get('recurrence_id') or '')
        suffix = ':' + recurrence
        result['uid'] = observation.key.removesuffix(suffix)
        result.update({key: attributes.get(key) for key in ('start_local', 'end_local', 'all_day', 'end_exclusive', 'rrule', 'recurrence_id', 'transparency')})
    elif observation.kind in ('job', 'estimate'):
        result['source_status_updated_at'] = observation.raw.get('LastStatusUpdate')
    elif observation.kind == 'visit':
        work_timestamps = attributes.get('work_timestamps') or {}
        result['source_completed_at'] = attributes.get('completed_at') or work_timestamps.get('completed_at')
    return MODELS[observation.kind].model_validate(result).model_dump()


def write_hours(connection: sqlite3.Connection, observation: Observation) -> None:
    hours = observation.normalized.attributes.get('working_hours') or {}
    weekdays = hours.get('weekdays') or {}
    for weekday, name in enumerate(('mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun')):
        spans = weekdays.get(name)
        state = 'unknown' if spans is None else 'known' if spans else 'closed'
        for index, span in enumerate(spans or [(None, None)]):
            connection.execute('INSERT INTO provider_hour_declarations VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                (digest([observation.id, name, index]), observation.id, observation.normalized.provider_id,
                 weekday, span[0], span[1], hours.get('timezone', 'America/Chicago'), state,
                 int(bool(hours.get('emergency_only'))), None, None))


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
                   files: list[dict[str, Any]], *, fail_after: int | None = None,
                   projector: Callable[[sqlite3.Connection], dict[str, Any]] | None = None,
                   lock_held: bool = False, identity_source: Path | None = None) -> dict[str, Any]:
    database = database.resolve()
    database.parent.mkdir(parents=True, exist_ok=True)
    lock_path = database.with_suffix(database.suffix + '.lock')
    lock_fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        if not lock_held:
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
        prior = identity_source or database
        if prior.exists():
            with connect_readonly(prior) as previous:
                schema_version(previous)
                seed_registry(connection, previous)
        else:
            seed_registry(connection, None)
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
                values = observation.normalized.model_dump(exclude={'kind', 'attributes'})
                unexpected = {key for key,value in values.items() if value is not None and key not in SOURCE_FIELDS[observation.kind]}
                if unexpected:
                    raise ImportFailure('entity has fields outside its source schema')
                entity = source_values(observation, values)
                entity['attributes_json'] = canonical_json(observation.normalized.attributes)
                columns = ','.join(['id', *entity])
                connection.execute(f'INSERT INTO {TABLES[observation.kind]}({columns}) VALUES({",".join("?" for _ in range(len(entity)+1))})', [key, *entity.values()])
                if observation.kind == 'profile':
                    write_hours(connection, observation)
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
        projection = projector(connection) if projector else None
        if connection.execute('PRAGMA foreign_key_check').fetchone():
            raise ImportFailure('foreign key validation failed')
        source_files = connection.execute("SELECT count(*) FROM input_files f WHERE role='source' AND NOT EXISTS(SELECT 1 FROM occurrences o WHERE o.file=f.path)").fetchone()[0]
        if source_files:
            raise ImportFailure('source file produced no accounted observations')
        if connection.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ImportFailure('SQLite integrity validation failed')
        counts_by_table = {table: connection.execute(f'SELECT count(*) FROM {table}').fetchone()[0] for table in TABLES.values()}
        counts_by_table['provider_hour_declarations'] = connection.execute('SELECT count(*) FROM provider_hour_declarations').fetchone()[0]
        report: dict[str, Any] = {
            'schema_version': SCHEMA_VERSION, 'status': 'success', 'ingested_at': ingested_at,
            'manifest_hash': manifest_hash, 'files': files,
            'sources': {source: {field: values[field] for field in ('seen', 'accepted', 'duplicate', 'unresolved', 'rejected')} for source, values in sorted(counters.items())},
            'by_source_kind': {key: {field: values[field] for field in ('seen', 'accepted', 'duplicate', 'unresolved', 'rejected')} for key, values in sorted(kinds.items())},
            'entities': counts_by_table, 'source_records': len(hashes),
            'occurrences': sum(value['seen'] for value in counters.values()),
            'issues': dict(connection.execute('SELECT code,count(*) FROM issues GROUP BY code')),
            'limitations': ['Source-local identities only; P2 reconciliation is not implemented.', 'Calendar recurrence definitions are retained; openings are not calculated.', 'Readers retain a consistent publication until their read transaction ends.'],
        }
        if projection is not None:
            report['reconciliation'] = projection
            report['limitations'][0] = 'Canonical reconciliation is conservative; unresolved matches remain separate.'
        connection.commit()
        connection.close()
        with temporary.open('rb') as handle:
            os.fsync(handle.fileno())
        report.update(publish(temporary, database))
        return report
    finally:
        connection.close()
        temporary.unlink(missing_ok=True)
        Path(str(temporary) + '-journal').unlink(missing_ok=True)
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        os.close(lock_fd)
