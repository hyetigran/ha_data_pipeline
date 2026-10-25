import hashlib
import sqlite3
from pathlib import Path

import pytest

from house_account.model import Entity, Issue, Observation, identity, instant, money
from house_account.storage import ImportFailure, connect_readonly, write_snapshot

FILES = [{'path': 'source.json', 'bytes': 2, 'sha256': 'fixture', 'role': 'source'}]


def provider(name='Original', locator='/0'):
    return Observation(source='fixture', account='one', kind='provider', key='1',
                       file='source.json', locator=locator, raw={'name': name},
                       normalized=Entity(kind='provider', display_name=name))


def test_nested_visits_estimates_and_provenance(tmp_path):
    p = provider()
    job = Observation(source='fixture', account='one', kind='job', key='job', file='source.json',
                      locator='/job', raw={'status': 'Done'}, snapshot_at='2026-11-02T06:00:00Z',
                      normalized=Entity(kind='job', provider_id=p.id, status='completed', source_status='Done'))
    estimate = Observation(source='fixture', account='one', kind='estimate', key='estimate', file='source.json',
                           locator='/estimate', raw={'status': 'complete rated'},
                           normalized=Entity(kind='estimate', provider_id=p.id, status='completed', source_status='complete rated'))
    visits = [Observation(source='fixture', account='one', kind='visit', key=str(i), file='source.json',
                          locator=f'/visit/{i}', raw={'visit': i},
                          normalized=Entity(kind='visit', provider_id=p.id, job_id=job.id, appointment_kind='job')) for i in range(2)]
    database = tmp_path / 'db.sqlite'
    report = write_snapshot([p, job, estimate, *visits], database, FILES)
    assert report['entities']['jobs'] == 1
    with connect_readonly(database) as db:
        assert db.execute('SELECT count(*) FROM visits WHERE job_id=?', (job.id,)).fetchone()[0] == 2
        assert db.execute('SELECT count(*) FROM estimates').fetchone()[0] == 1
        assert db.execute('SELECT count(*) FROM entity_evidence').fetchone()[0] == 5
        assert db.execute('SELECT snapshot_at,ingested_at FROM source_records WHERE id=?', (job.id,)).fetchone()[0] == '2026-11-02T06:00:00Z'
        with pytest.raises(sqlite3.OperationalError):
            db.execute('DELETE FROM jobs')
    assert database.stat().st_mode & 0o777 == 0o600


def test_duplicate_occurrences_and_conflict_rollback(tmp_path):
    database = tmp_path / 'db.sqlite'
    report = write_snapshot([provider(), provider(locator='/1')], database, FILES)
    assert report['sources']['fixture'] == {'seen': 2, 'accepted': 1, 'duplicate': 1, 'unresolved': 0, 'rejected': 0}
    before = database.read_bytes()
    with pytest.raises(ImportFailure, match='conflicting payload'):
        write_snapshot([provider(), provider('Changed', '/1')], database, FILES)
    assert database.read_bytes() == before
    assert not list(tmp_path.glob('*.tmp'))


def test_failure_and_live_reader_snapshot_adoption(tmp_path):
    database = tmp_path / 'db.sqlite'
    write_snapshot([provider()], database, FILES)
    reader = connect_readonly(database)
    assert reader.execute('SELECT display_name FROM providers').fetchone()[0] == 'Original'
    before = hashlib.sha256(database.read_bytes()).hexdigest()
    with pytest.raises(ImportFailure, match='injected'):
        write_snapshot([provider('Changed')], database, FILES, fail_after=1)
    assert hashlib.sha256(database.read_bytes()).hexdigest() == before
    write_snapshot([provider('Changed')], database, FILES)
    assert reader.execute('SELECT display_name FROM providers').fetchone()[0] == 'Original'
    reader.close()
    with connect_readonly(database) as new_reader:
        assert new_reader.execute('SELECT display_name FROM providers').fetchone()[0] == 'Changed'


def test_unresolved_retained_and_missing_reference_aborts(tmp_path):
    p = provider()
    p.issues = [Issue(code='unknown_status', field='status')]
    report = write_snapshot([p], tmp_path / 'good.sqlite', FILES)
    assert report['sources']['fixture']['unresolved'] == 1
    broken = Observation(source='fixture', account='one', kind='job', key='j', file='source.json', locator='/job',
                         raw={}, normalized=Entity(kind='job', provider_id=identity('fixture', 'one', 'provider', 'missing')))
    with pytest.raises(ImportFailure, match='foreign key'):
        write_snapshot([broken], tmp_path / 'bad.sqlite', FILES)
    assert not (tmp_path / 'bad.sqlite').exists()


def test_money_and_time_are_exact():
    assert money('$1,234.56') == 123456
    assert money(123456, cents=True) == 123456
    assert money('') is None
    with pytest.raises(ValueError):
        money('0.001')
    assert instant('2026-11-03T10:00:00') == '2026-11-03T16:00:00+00:00'
    assert instant('2026-07-01T10:00:00') == '2026-07-01T15:00:00+00:00'
    for invalid in ('2026-11-01T01:30:00', '2026-03-08T02:30:00'):
        with pytest.raises(ValueError, match='ambiguous or nonexistent'):
            instant(invalid)


def test_writer_lock(tmp_path):
    import fcntl
    database = tmp_path / 'locked.sqlite'
    lock = Path(str(database) + '.lock')
    with lock.open('w') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(ImportFailure, match='another importer'):
            write_snapshot([provider()], database, FILES)


def test_postpublication_durability_failure_reports_published(tmp_path, monkeypatch):
    import os
    database = tmp_path / 'snapshot.sqlite'
    write_snapshot([provider()], database, FILES)
    real_fsync = os.fsync
    calls = 0

    def fail_directory_fsync(fd):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError('synthetic directory failure')
        real_fsync(fd)

    monkeypatch.setattr(os, 'fsync', fail_directory_fsync)
    report = write_snapshot([provider('Published')], database, FILES)
    assert report['status'] == 'success'
    assert 'published' in report['warnings'][0]
    with connect_readonly(database) as db:
        assert db.execute('SELECT display_name FROM providers').fetchone()[0] == 'Published'


def test_cli_structural_errors_are_private(tmp_path, monkeypatch, capsys):
    import sys

    from house_account import cli

    def broken(*args, **kwargs):
        raise KeyError('private homeowner details')

    monkeypatch.setattr(cli, 'ingest', broken)
    monkeypatch.setattr(sys, 'argv', ['house-account', 'ingest'])
    assert cli.main() == 1
    output = capsys.readouterr()
    assert output.out == ''
    assert 'private homeowner' not in output.err
    assert 'KeyError' in output.err


def test_report_failure_after_success_is_explicit(tmp_path, monkeypatch, capsys):
    import sys

    from house_account import cli

    monkeypatch.setattr(cli, 'ingest', lambda *args, **kwargs: {'status': 'success'})

    def fail_report(*args):
        raise OSError('cannot write')

    monkeypatch.setattr(cli, 'write_report', fail_report)
    monkeypatch.setattr(sys, 'argv', ['house-account', 'ingest', '--report', str(tmp_path / 'report.json')])
    assert cli.main() == 2
    assert 'published_report_failed' in capsys.readouterr().err


def test_removed_pack_file_aborts_without_touching_snapshot(tmp_path):
    import shutil

    from house_account.cli import ingest
    fixture = tmp_path / 'pack'
    shutil.copytree(Path(__file__).resolve().parents[1] / 'data', fixture)
    database = tmp_path / 'snapshot.sqlite'
    write_snapshot([provider()], database, FILES)
    before = database.read_bytes()
    next((fixture / 'sources' / 'jobber').glob('*.json')).unlink()
    with pytest.raises(ImportFailure, match='missing'):
        ingest(fixture, database)
    assert database.read_bytes() == before


def test_changed_inputs_abort_before_publication(tmp_path, monkeypatch):
    from house_account import cli
    database = tmp_path / 'snapshot.sqlite'
    write_snapshot([provider()], database, FILES)
    before = database.read_bytes()
    count = 0

    def changing_inventory(root, classify):
        nonlocal count
        count += 1
        return FILES if count == 1 else [{**FILES[0], 'sha256': 'changed'}]

    monkeypatch.setattr(cli, 'inventory', changing_inventory)
    monkeypatch.setattr(cli.adapters, 'load', lambda root: iter([provider()]))
    with pytest.raises(ImportFailure, match='changed during import'):
        cli.ingest(tmp_path / 'pack', database)
    assert database.read_bytes() == before
