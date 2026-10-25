import sqlite3

import pytest

from house_account.registry import assign_ids, resolve_identity, seed_registry


def database():
    connection = sqlite3.connect(':memory:')
    connection.execute('PRAGMA foreign_keys=ON')
    connection.execute('CREATE TABLE source_records(id TEXT PRIMARY KEY,source TEXT,account TEXT,kind TEXT,source_key TEXT)')
    connection.executemany('INSERT INTO source_records VALUES(?,?,?,?,?)', [(key, 'fixture', 'one', 'provider', key) for key in ('a','b','c')])
    seed_registry(connection, None)
    return connection


def test_existing_identity_survives_added_evidence_and_repeated_import():
    connection = database()
    assert assign_ids(connection, 'provider', {'a':'initial'}) == {'a':'initial'}
    assert assign_ids(connection, 'provider', {'a':'new-group','b':'new-group'}) == {'a':'initial','b':'initial'}
    assert assign_ids(connection, 'provider', {'a':'new-group','b':'new-group'}) == {'a':'initial','b':'initial'}
    assert connection.execute('SELECT count(*) FROM identity_registry').fetchone()[0] == 1


def test_merge_redirect_and_split_are_retained_across_copy():
    connection = database()
    assign_ids(connection, 'provider', {'a':'first','b':'second'})
    assign_ids(connection, 'provider', {'a':'merged','b':'merged'})
    assert resolve_identity(connection, 'second', 'provider') == {'status':'resolved','requested_id':'second','ids':['first']}
    split = assign_ids(connection, 'provider', {'a':'a-only','b':'b-only'})
    assert split['a'] != split['b']
    assert resolve_identity(connection, 'first', 'provider')['status'] == 'ambiguous'
    assert resolve_identity(connection, 'second', 'provider')['status'] == 'ambiguous'
    connection.commit()
    copied = sqlite3.connect(':memory:')
    connection.backup(copied)
    assert assign_ids(copied, 'provider', {'a':'a-only','b':'b-only'}) == split
    assert resolve_identity(copied, 'first', 'provider')['ids'] == sorted(split.values())


def test_registry_rejects_wrong_kind_membership():
    connection = database()
    assign_ids(connection, 'provider', {'a':'provider-id'})
    connection.commit()
    with pytest.raises(sqlite3.IntegrityError):
        connection.execute("INSERT INTO identity_memberships VALUES('b','property','provider-id')")
        connection.commit()
    connection.rollback()


def test_legacy_bootstrap_preserves_original_ids():
    previous = sqlite3.connect(':memory:')
    previous.execute('CREATE TABLE source_records(id TEXT,source TEXT,account TEXT,kind TEXT,source_key TEXT)')
    previous.execute("INSERT INTO source_records VALUES('a','fixture','one','provider','a')")
    previous.execute('CREATE TABLE canonical_crosswalk(source_id TEXT,kind TEXT,canonical_id TEXT)')
    previous.execute("INSERT INTO canonical_crosswalk VALUES('a','provider','legacy-id')")
    connection = sqlite3.connect(':memory:')
    connection.execute('CREATE TABLE IF NOT EXISTS source_records(id TEXT,source TEXT,account TEXT,kind TEXT,source_key TEXT)')
    connection.execute("INSERT INTO source_records VALUES('a','fixture','one','provider','a')")
    seed_registry(connection, previous)
    assert assign_ids(connection, 'provider', {'a':'different-group-hash'}) == {'a':'legacy-id'}


def test_redirect_to_split_stays_ambiguous_even_if_successors_remerge():
    connection = database()
    assign_ids(connection, 'provider', {'a':'first','b':'second'})
    assign_ids(connection, 'provider', {'a':'merged','b':'merged'})
    assign_ids(connection, 'provider', {'a':'a-only','b':'b-only'})
    assign_ids(connection, 'provider', {'a':'merged-again','b':'merged-again'})
    result = resolve_identity(connection, 'second', 'provider')
    assert result['status'] == 'ambiguous'
    assert len(result['ids']) == 1
