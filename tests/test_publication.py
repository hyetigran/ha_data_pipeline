import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from house_account.model import Entity, Observation
from house_account.publication import SCHEMA_VERSION, publish
from house_account.storage import connect_readonly, write_snapshot

FILES = [{'path':'source.json','bytes':2,'sha256':'fixture','role':'source'}]


def build(path, label='Original'):
    observation = Observation(source='fixture',account='one',kind='provider',key='1',file='source.json',locator='/0',raw={'name':label},normalized=Entity(kind='provider',display_name=label))
    return write_snapshot([observation], path, FILES)


def test_transactional_publication_preserves_inode_and_reader_revision(tmp_path):
    database = tmp_path / 'db.sqlite'
    build(database)
    inode = database.stat().st_ino
    reader = connect_readonly(database)
    revision = reader.execute('SELECT id FROM snapshot').fetchone()[0]
    build(database, 'Changed')
    assert database.stat().st_ino == inode
    assert reader.execute('SELECT id FROM snapshot').fetchone()[0] == revision
    assert reader.execute('SELECT display_name FROM providers').fetchone()[0] == 'Original'
    reader.close()
    with connect_readonly(database) as connection:
        assert connection.execute('SELECT display_name FROM providers').fetchone()[0] == 'Changed'


def test_unsupported_schema_refused_before_changes(tmp_path):
    database = tmp_path / 'db.sqlite'
    build(database)
    with sqlite3.connect(database) as connection:
        connection.execute('PRAGMA user_version=99')
    before = database.read_bytes()
    with pytest.raises(ValueError, match='unsupported database schema'):
        build(database, 'Wrong')
    assert database.read_bytes() == before
    assert not list(tmp_path.glob('*.bak'))


def test_legacy_migration_keeps_verified_restore_copy(tmp_path):
    database, candidate = tmp_path / 'legacy.sqlite', tmp_path / 'candidate.sqlite'
    with sqlite3.connect(database) as connection:
        connection.executescript('''CREATE TABLE providers(id TEXT PRIMARY KEY,display_name TEXT);
            CREATE TABLE source_records(id TEXT PRIMARY KEY,source TEXT,account TEXT,kind TEXT,source_key TEXT);
            CREATE TABLE snapshot(id TEXT); CREATE TABLE occurrences(id INTEGER);
            INSERT INTO providers VALUES('old','Legacy'); INSERT INTO snapshot VALUES('legacy');''')
    build(candidate, 'New')
    receipt = publish(candidate, database)
    backup = Path(receipt['migration_backup'])
    with sqlite3.connect(backup) as old, connect_readonly(database) as current:
        assert old.execute('SELECT display_name FROM providers').fetchone()[0] == 'Legacy'
        assert old.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        assert current.execute('SELECT display_name FROM providers').fetchone()[0] == 'New'
        assert current.execute('PRAGMA user_version').fetchone()[0] == SCHEMA_VERSION
        restored = sqlite3.connect(tmp_path / 'restored.sqlite')
        old.backup(restored)
        assert restored.execute('SELECT display_name FROM providers').fetchone()[0] == 'Legacy'
        restored.close()


@pytest.mark.parametrize(('phase','expected'), [('before_commit','Original'),('after_commit','Changed')])
def test_process_exit_at_commit_boundary(tmp_path, phase, expected):
    database, candidate = tmp_path / 'db.sqlite', tmp_path / 'candidate.sqlite'
    build(database)
    build(candidate, 'Changed')
    command = '''import os,sys
from pathlib import Path
from house_account import publication
publication._checkpoint=lambda phase: os._exit(73) if phase==sys.argv[3] else None
publication.publish(Path(sys.argv[1]),Path(sys.argv[2]))
'''
    result = subprocess.run([sys.executable, '-c', command, str(candidate), str(database), phase], check=False, env={**os.environ, 'PYTHONPATH':str(Path(__file__).parents[1]/'src')}, capture_output=True)
    assert result.returncode == 73, result.stderr
    with connect_readonly(database) as connection:
        assert connection.execute('SELECT display_name FROM providers').fetchone()[0] == expected
        assert connection.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        assert connection.execute('PRAGMA foreign_key_check').fetchall() == []


def test_calendar_and_hours_keep_declarations_without_expanding_occurrences(tmp_path):
    from house_account.model import identity
    provider_id = identity('fixture', 'one', 'provider', '1')
    observations = [
        Observation(source='fixture',account='one',kind='provider',key='1',file='source.json',locator='/0',raw={},normalized=Entity(kind='provider',display_name='Provider')),
        Observation(source='fixture',account='one',kind='profile',key='profile',file='source.json',locator='/1',raw={},normalized=Entity(kind='profile',provider_id=provider_id,attributes={'working_hours':{'timezone':'America/Chicago','weekdays':{'mon':[['08:00','17:00']],'sun':[]}}})),
        Observation(source='fixture',account='one',kind='calendar_block',key='vacation:',file='source.json',locator='/2',raw={},normalized=Entity(kind='calendar_block',provider_id=provider_id,status='confirmed',attributes={'start_local':'2026-11-04','end_local':'2026-11-09','all_day':True,'end_exclusive':True,'rrule':None,'recurrence_id':'','transparency':'OPAQUE'})),
    ]
    database = tmp_path / 'db.sqlite'
    write_snapshot(observations, database, FILES)
    with connect_readonly(database) as connection:
        assert connection.execute('SELECT uid,start_local,end_local,all_day,end_exclusive,transparency FROM calendar_blocks').fetchone() == ('vacation','2026-11-04','2026-11-09',1,1,'OPAQUE')
        assert connection.execute('SELECT weekday,local_start,local_end,declaration_state FROM provider_hour_declarations ORDER BY weekday').fetchall() == [
            (0,'08:00','17:00','known'),(1,None,None,'unknown'),(2,None,None,'unknown'),(3,None,None,'unknown'),(4,None,None,'unknown'),(5,None,None,'unknown'),(6,None,None,'closed')]


def test_failed_migration_preserves_legacy_rows_and_backup(tmp_path, monkeypatch):
    from house_account import publication
    database, candidate = tmp_path / 'legacy.sqlite', tmp_path / 'candidate.sqlite'
    with sqlite3.connect(database) as connection:
        connection.executescript('''CREATE TABLE providers(id TEXT PRIMARY KEY,display_name TEXT);
            CREATE TABLE source_records(id TEXT PRIMARY KEY,source TEXT,account TEXT,kind TEXT,source_key TEXT);
            CREATE TABLE snapshot(id TEXT); CREATE TABLE occurrences(id INTEGER);
            INSERT INTO providers VALUES('old','Legacy'); INSERT INTO snapshot VALUES('legacy');''')
    build(candidate, 'New')

    def interrupt(phase):
        if phase == 'before_commit':
            raise RuntimeError('migration interrupted')

    monkeypatch.setattr(publication, '_checkpoint', interrupt)
    with pytest.raises(RuntimeError, match='migration interrupted'):
        publish(candidate, database)
    with sqlite3.connect(database) as old:
        assert old.execute('SELECT display_name FROM providers').fetchone()[0] == 'Legacy'
        assert old.execute('PRAGMA user_version').fetchone()[0] == 0
    assert database.with_name(database.name + '.pre-v2.bak').exists()
    monkeypatch.setattr(publication, '_checkpoint', lambda phase: None)
    publish(candidate, database)
    with connect_readonly(database) as current:
        assert current.execute('SELECT display_name FROM providers').fetchone()[0] == 'New'
