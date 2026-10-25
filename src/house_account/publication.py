from __future__ import annotations

import os
import sqlite3
from graphlib import TopologicalSorter
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 2


def _checkpoint(phase: str) -> None:
    pass


def schema_version(connection: sqlite3.Connection) -> int:
    version = connection.execute('PRAGMA user_version').fetchone()[0]
    tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if version == SCHEMA_VERSION:
        return version
    if version in (0, 1) and {'source_records', 'snapshot', 'occurrences', 'providers'} <= tables:
        return 1
    raise ValueError(f'unsupported database schema version: {version}')


def backup_database(database: Path, backup: Path) -> None:
    if backup.exists():
        raise ValueError('migration backup already exists; preserve it or select a fresh database path')
    fd = os.open(backup, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(fd)
    try:
        with sqlite3.connect(database.resolve().as_uri() + '?mode=ro', uri=True) as source, sqlite3.connect(backup) as target:
            source.backup(target)
            if target.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise ValueError('migration backup integrity validation failed')
        with backup.open('rb') as handle:
            os.fsync(handle.fileno())
        directory = os.open(backup.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    except BaseException:
        backup.unlink(missing_ok=True)
        raise


def _table_order(connection: sqlite3.Connection) -> list[str]:
    tables = {row[0] for row in connection.execute("SELECT name FROM staged.sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
    dependencies = {name: {row[2] for row in connection.execute(f'PRAGMA staged.foreign_key_list("{name}")')
                          if row[2] != name} for name in sorted(tables)}
    if 'lineage_entities' in dependencies:
        dependencies['lineage_entities'].update(tables & {
            'canonical_providers', 'canonical_properties', 'canonical_jobs',
            'canonical_estimates', 'canonical_visits', 'job_services',
            'estimate_services', 'service_completions',
        })
    return list(TopologicalSorter(dependencies).static_order())


def publish(candidate: Path, database: Path) -> dict[str, Any]:
    existed = database.exists()
    previous_version = None
    migration_backup = None
    if existed:
        with sqlite3.connect(database.resolve().as_uri() + '?mode=ro', uri=True) as old:
            previous_version = schema_version(old)
        if previous_version != SCHEMA_VERSION:
            migration_backup = database.with_name(database.name + '.pre-v2.bak')
            if migration_backup.exists():
                with sqlite3.connect(migration_backup.resolve().as_uri() + '?mode=ro', uri=True) as backup, sqlite3.connect(database.resolve().as_uri() + '?mode=ro', uri=True) as current:
                    if schema_version(backup) != 1 or list(backup.iterdump()) != list(current.iterdump()):
                        raise ValueError('existing migration backup differs from the current legacy database')
            else:
                backup_database(database, migration_backup)
    else:
        fd = os.open(database, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
    connection = sqlite3.connect(database, timeout=30)
    committed = False
    result: dict[str, Any] = {'publication': 'transactional', 'schema_version': SCHEMA_VERSION}
    try:
        connection.execute('PRAGMA journal_mode=WAL')
        connection.execute('PRAGMA synchronous=FULL')
        connection.execute('PRAGMA foreign_keys=OFF')
        connection.execute('ATTACH DATABASE ? AS staged', (str(candidate),))
        if connection.execute('PRAGMA staged.user_version').fetchone()[0] != SCHEMA_VERSION:
            raise ValueError('candidate has unsupported schema version')
        staged_objects = connection.execute("SELECT type,name,sql FROM staged.sqlite_master WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%' ORDER BY type='table' DESC,name").fetchall()
        current_objects = connection.execute("SELECT type,name,sql FROM main.sqlite_master WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%' ORDER BY type='table' DESC,name").fetchall()
        table_order = _table_order(connection)
        migration = current_objects != staged_objects
        if previous_version == SCHEMA_VERSION and migration:
            raise ValueError('schema version unchanged but database definitions differ')
        connection.execute('BEGIN IMMEDIATE')
        if migration:
            for object_type, name, _ in reversed(current_objects):
                if object_type in ('table', 'view', 'trigger', 'index'):
                    connection.execute(f'DROP {object_type} IF EXISTS "{name}"')
            for _, _, ddl in staged_objects:
                connection.execute(ddl)
        else:
            for name in reversed(table_order):
                connection.execute(f'DELETE FROM "{name}"')
        for name in table_order:
            connection.execute(f'INSERT INTO main."{name}" SELECT * FROM staged."{name}"')
        connection.execute(f'PRAGMA main.user_version={SCHEMA_VERSION}')
        if connection.execute('PRAGMA main.foreign_key_check').fetchone():
            raise ValueError('publication foreign key validation failed')
        if connection.execute('PRAGMA main.integrity_check').fetchone()[0] != 'ok':
            raise ValueError('publication integrity validation failed')
        _checkpoint('before_commit')
        connection.commit()
        committed = True
        _checkpoint('after_commit')
        if migration_backup:
            result['migration_backup'] = str(migration_backup)
        try:
            directory = os.open(database.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        except OSError:
            result['warnings'] = ['Snapshot published, but directory durability could not be confirmed.']
        return result
    finally:
        connection.close()
        if not existed and not committed:
            database.unlink(missing_ok=True)
            Path(str(database) + '-wal').unlink(missing_ok=True)
            Path(str(database) + '-shm').unlink(missing_ok=True)
