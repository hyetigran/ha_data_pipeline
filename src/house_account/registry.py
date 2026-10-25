from __future__ import annotations

import sqlite3
from collections import defaultdict

from .model import digest

REGISTRY_TABLES = ('identity_registry', 'identity_sources', 'identity_memberships', 'identity_successors')


def create_registry(connection: sqlite3.Connection) -> None:
    statements = [
        """CREATE TABLE identity_registry(
            id TEXT NOT NULL PRIMARY KEY, kind TEXT NOT NULL CHECK(kind IN ('provider','property','job','estimate','visit')),
            state TEXT NOT NULL CHECK(state IN ('active','redirect','ambiguous')),
            redirect_id TEXT REFERENCES identity_registry(id) DEFERRABLE INITIALLY DEFERRED,
            UNIQUE(id,kind), CHECK((state='redirect')=(redirect_id IS NOT NULL)), CHECK(id<>redirect_id)) STRICT""",
        """CREATE TABLE identity_sources(
            id TEXT NOT NULL PRIMARY KEY, source TEXT NOT NULL, account TEXT NOT NULL,
            source_kind TEXT NOT NULL, source_key TEXT NOT NULL,
            UNIQUE(source,account,source_kind,source_key)) STRICT""",
        """CREATE TABLE identity_memberships(
            source_id TEXT NOT NULL REFERENCES identity_sources(id), kind TEXT NOT NULL,
            identity_id TEXT NOT NULL, PRIMARY KEY(source_id,kind),
            FOREIGN KEY(identity_id,kind) REFERENCES identity_registry(id,kind) DEFERRABLE INITIALLY DEFERRED) STRICT""",
        """CREATE TABLE identity_successors(
            old_id TEXT NOT NULL REFERENCES identity_registry(id), new_id TEXT NOT NULL REFERENCES identity_registry(id),
            PRIMARY KEY(old_id,new_id), CHECK(old_id<>new_id)) STRICT""",
    ]
    for statement in statements:
        connection.execute(statement)


def seed_registry(connection: sqlite3.Connection, previous: sqlite3.Connection | None) -> None:
    create_registry(connection)
    if previous is None:
        return
    tables = {r[0] for r in previous.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if 'identity_registry' in tables:
        for table in REGISTRY_TABLES:
            cursor = previous.execute(f'SELECT * FROM {table}')
            placeholders = ','.join('?' for _ in cursor.description)
            connection.executemany(f'INSERT INTO {table} VALUES({placeholders})', cursor)
        return
    connection.executemany('INSERT INTO identity_sources VALUES(?,?,?,?,?)', previous.execute(
        'SELECT id,source,account,kind,source_key FROM source_records'))
    if 'canonical_crosswalk' in tables:
        for source_id, kind, canonical_id in previous.execute('SELECT source_id,kind,canonical_id FROM canonical_crosswalk'):
            connection.execute("INSERT OR IGNORE INTO identity_registry VALUES(?,?,'active',NULL)", (canonical_id, kind))
            connection.execute('INSERT INTO identity_memberships VALUES(?,?,?)', (source_id, kind, canonical_id))
    if 'canonical_visits' in tables:
        for (source_id,) in previous.execute('SELECT id FROM canonical_visits'):
            connection.execute("INSERT OR IGNORE INTO identity_registry VALUES(?,'visit','active',NULL)", (source_id,))
            connection.execute("INSERT OR IGNORE INTO identity_memberships VALUES(?,'visit',?)", (source_id, source_id))


def assign_ids(connection: sqlite3.Connection, kind: str, groups: dict[str, str]) -> dict[str, str]:
    connection.execute('''INSERT OR IGNORE INTO identity_sources
        SELECT id,source,account,kind,source_key FROM source_records''')
    previous = dict(connection.execute('SELECT source_id,identity_id FROM identity_memberships WHERE kind=?', (kind,)))
    members: dict[str, list[str]] = defaultdict(list)
    prior_targets: dict[str, set[str]] = defaultdict(set)
    for source_id, group in groups.items():
        members[group].append(source_id)
        if source_id in previous:
            prior_targets[previous[source_id]].add(group)
    split = {old for old, targets in prior_targets.items() if len(targets) > 1}
    allocated: dict[str, str] = {}
    for group, source_ids in sorted(members.items()):
        ancestors = {previous[s] for s in source_ids if s in previous}
        reusable = sorted(ancestors - split)
        if reusable:
            chosen = reusable[0]
        else:
            chosen = digest(['split', kind, sorted(source_ids), sorted(ancestors)]) if ancestors else group
        connection.execute("INSERT OR IGNORE INTO identity_registry VALUES(?,?,'active',NULL)", (chosen, kind))
        connection.execute("UPDATE identity_registry SET state='active',redirect_id=NULL WHERE id=?", (chosen,))
        allocated[group] = chosen
        for old in reusable[1:]:
            connection.execute('UPDATE identity_memberships SET identity_id=? WHERE identity_id=? AND kind=?', (chosen, old, kind))
            connection.execute("UPDATE identity_registry SET state='redirect',redirect_id=? WHERE id=?", (chosen, old))
        for source_id in source_ids:
            connection.execute('''INSERT INTO identity_memberships VALUES(?,?,?)
                ON CONFLICT(source_id,kind) DO UPDATE SET identity_id=excluded.identity_id''', (source_id, kind, chosen))
    for old in split:
        connection.execute("UPDATE identity_registry SET state='ambiguous',redirect_id=NULL WHERE id=?", (old,))
        connection.executemany('INSERT OR IGNORE INTO identity_successors VALUES(?,?)',
                               [(old, allocated[group]) for group in sorted(prior_targets[old])])
    return {source_id: allocated[group] for source_id, group in groups.items()}


def resolve_identity(connection: sqlite3.Connection, identity_id: str, kind: str) -> dict[str, object]:
    ambiguous = False

    def targets(key: str, seen: set[str]) -> set[str]:
        nonlocal ambiguous
        if key in seen:
            raise ValueError('identity registry cycle')
        row = connection.execute('SELECT state,redirect_id FROM identity_registry WHERE id=? AND kind=?', (key, kind)).fetchone()
        if row is None:
            return set()
        state, redirect = row
        if state == 'ambiguous':
            ambiguous = True
        if state == 'active':
            return {key}
        children = [redirect] if state == 'redirect' else [r[0] for r in connection.execute('SELECT new_id FROM identity_successors WHERE old_id=?', (key,))]
        return set().union(*(targets(child, seen | {key}) for child in children))

    result = sorted(targets(identity_id, set()))
    row = connection.execute('SELECT state FROM identity_registry WHERE id=? AND kind=?', (identity_id, kind)).fetchone()
    state = 'unknown' if row is None else 'ambiguous' if ambiguous or len(result) > 1 else 'resolved'
    return {'status': state, 'requested_id': identity_id, 'ids': result}
