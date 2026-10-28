"""Setup must not register an unprepared snapshot or depend on the caller's cwd."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def setup_checkout(tmp_path):
    root = tmp_path / 'checkout with spaces'
    root.mkdir()
    shutil.copy2(ROOT / 'setup.sh', root / 'setup.sh')
    (root / 'scripts').mkdir()
    shutil.copy2(ROOT / 'scripts/configure_mcp.py', root / 'scripts/configure_mcp.py')
    for name in ('sources', 'reference'):
        (root / 'data' / name).mkdir(parents=True)
    (root / 'data/README.md').write_text('fixture')
    binaries = tmp_path / 'bin'
    binaries.mkdir()
    log = tmp_path / 'calls.jsonl'
    stub = '''#!PYTHON_EXECUTABLE
import json, os, pathlib, sys
name = pathlib.Path(sys.argv[0]).name
if name == 'python' and sys.argv[1].endswith('configure_mcp.py'):
    os.execv(sys.executable, [sys.executable, *sys.argv[1:]])
with open(os.environ['SETUP_TEST_LOG'], 'a') as stream:
    stream.write(json.dumps([name, sys.argv[1:]]) + '\\n')
if os.environ.get('SETUP_TEST_FAIL') == name:
    sys.exit(1)
if name == 'uv':
    target = pathlib.Path('.venv/bin/python')
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(pathlib.Path(sys.argv[0]).read_text())
    target.chmod(0o755)
if name == 'python':
    for option in ('--database', '--report'):
        target = pathlib.Path(sys.argv[sys.argv.index(option)+1])
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text('{}')
if name == 'codex' and 'get' in sys.argv:
    print('{}')
'''
    stub = stub.replace('PYTHON_EXECUTABLE', sys.executable)
    for name in ('uv', 'codex', 'claude'):
        target = binaries / name
        target.write_text(stub)
        target.chmod(0o755)
    env = dict(os.environ, PATH=f'{binaries}:{os.environ["PATH"]}', SETUP_TEST_LOG=str(log))
    return root, env, log


def invoke(root, env, *args):
    return subprocess.run(['sh', str(root / 'setup.sh'), *args], check=False, cwd=root.parent,
                          env=env, capture_output=True, text=True)


def test_fresh_uat_and_repeated_registration(setup_checkout):
    root, env, log = setup_checkout
    databases = []
    for _ in range(2):
        result = invoke(root, env, '--client', 'codex', '--uat')
        assert result.returncode == 0, result.stderr
        assert 'Setup complete.' in result.stdout
        calls = [json.loads(line) for line in log.read_text().splitlines()][-4:]
        assert [call[0] for call in calls] == ['uv', 'python', 'codex', 'codex']
        assert calls[0][1] == ['sync', '--locked', '--python', '3.13']
        arguments = calls[2][1]
        assert arguments[:4] == ['mcp', 'add', 'house_account', '--']
        assert arguments[4] == str(root / '.venv/bin/python')
        database = arguments[arguments.index('--database') + 1]
        assert Path(database).is_file()
        assert database in calls[1][1]
        databases.append(database)
    assert databases[0] != databases[1]


@pytest.mark.parametrize('failure', ['uv', 'python', 'codex'])
def test_failure_stops_setup(setup_checkout, failure):
    root, env, log = setup_checkout
    result = invoke(root, dict(env, SETUP_TEST_FAIL=failure), '--client', 'codex')
    assert result.returncode != 0
    assert 'Setup complete.' not in result.stdout
    names = [json.loads(line)[0] for line in log.read_text().splitlines()]
    assert names == ['uv', 'python', 'codex'][:['uv', 'python', 'codex'].index(failure) + 1]


def test_missing_pack_fails_before_install(setup_checkout):
    root, env, log = setup_checkout
    (root / 'data/README.md').unlink()
    result = invoke(root, env)
    assert result.returncode != 0
    assert 'supplied data pack' in result.stderr
    assert not log.exists()


def test_external_pack_relative_to_invocation_directory(setup_checkout):
    root, env, log = setup_checkout
    pack = root.parent / 'external pack'
    (root / 'data').rename(pack)
    result = invoke(root, env, '--client', 'codex', '--data', 'external pack')
    assert result.returncode == 0, result.stderr
    calls = [json.loads(line) for line in log.read_text().splitlines()]
    for _, arguments in calls[1:3]:
        assert arguments[arguments.index('--data') + 1] == str(pack)


@pytest.mark.parametrize('client', ['codex', 'claude', 'none'])
def test_bootstrap_missing_tools_without_system_installations(setup_checkout, client):
    root, env, log = setup_checkout
    binaries = Path(env['PATH'].split(':')[0])
    stub = root.parent / 'tool-stub'
    shutil.copy2(binaries / 'uv', stub)
    for name in ('uv', 'codex', 'claude'):
        (binaries / name).unlink()
    for name in ('sh', 'bash', 'dirname', 'uname', 'mktemp', 'rm', 'mkdir'):
        (binaries / name).symlink_to(shutil.which(name))
    curl = binaries / 'curl'
    curl.write_text(f"#!{sys.executable}\n" + r'''import os, pathlib, shlex, sys
if os.environ.get('SETUP_TEST_DOWNLOAD_FAIL'):
    sys.exit(22)
url = sys.argv[2]
names = {'https://astral.sh/uv/install.sh': 'uv', 'https://chatgpt.com/codex/install.sh': 'codex', 'https://claude.ai/install.sh': 'claude'}
name = names[url]
destination = pathlib.Path(os.environ['HOUSE_ACCOUNT_TOOLS_DIR']) / name
script = '/bin/mkdir -p ' + shlex.quote(str(destination.parent)) + '\n'
script += '/bin/cp ' + shlex.quote(os.environ['SETUP_TEST_STUB']) + ' ' + shlex.quote(str(destination)) + '\n'
script += '/bin/chmod +x ' + shlex.quote(str(destination)) + '\n'
pathlib.Path(sys.argv[sys.argv.index('-o') + 1]).write_text(script)
''')
    curl.chmod(0o755)
    env.update(PATH=str(binaries), HOUSE_ACCOUNT_TOOLS_DIR=str(binaries), SETUP_TEST_STUB=str(stub))
    failed = invoke(root, dict(env, SETUP_TEST_DOWNLOAD_FAIL='1'), '--client', client)
    assert failed.returncode != 0
    assert not log.exists()
    result = invoke(root, env, '--client', client)
    assert result.returncode == 0, result.stderr
    assert 'Installing uv using its official installer' in result.stdout
    assert (binaries / 'uv').is_file()
    for agent in ('codex', 'claude'):
        assert (binaries / agent).exists() == (client == agent)


@pytest.mark.parametrize('client', ['none', 'claude'])
def test_client_modes_preserve_unrelated_configuration(setup_checkout, client):
    root, env, log = setup_checkout
    config = root / '.mcp.json'
    original = {'mcpServers': {'other': {'command': 'other-server'}, 'house_account': {'command': 'old'}}, 'otherSetting': True}
    config.write_text(json.dumps(original))
    for _ in range(2):
        result = invoke(root, env, '--client', client, '--uat')
        assert result.returncode == 0, result.stderr
    calls = [json.loads(line) for line in log.read_text().splitlines()]
    assert [name for name, _ in calls] == ['uv', 'python', 'uv', 'python']
    exports = list((root / 'var/uat').glob('*/mcp-config.json'))
    assert len(exports) == 2
    entries = [json.loads(path.read_text())['mcpServers']['house_account'] for path in exports]
    assert all(entry['command'] == str(root / '.venv/bin/python') for entry in entries)
    assert entries[0]['args'] != entries[1]['args']
    actual = json.loads(config.read_text())
    if client == 'none':
        assert actual == original
        assert 'Equivalent launch command:' in result.stdout
    else:
        assert actual['mcpServers']['other'] == original['mcpServers']['other']
        assert actual['otherSetting'] is True
        assert actual['mcpServers']['house_account'] in entries
        assert 'approve' in result.stdout


def test_default_does_not_configure_client(setup_checkout):
    root, env, log = setup_checkout
    result = invoke(root, env)
    assert result.returncode == 0, result.stderr
    assert 'No agent client was installed or configured' in result.stdout
    assert not (root / '.mcp.json').exists()
    assert [json.loads(line)[0] for line in log.read_text().splitlines()] == ['uv', 'python']


@pytest.mark.parametrize('args', [('--client', 'invalid'), ('--client',)])
def test_invalid_client_fails_before_mutation(setup_checkout, args):
    root, env, log = setup_checkout
    assert invoke(root, env, *args).returncode != 0
    assert not log.exists()


def test_invalid_claude_config_is_preserved(setup_checkout):
    root, env, _log = setup_checkout
    config = root / '.mcp.json'
    config.write_text('{broken')
    result = invoke(root, env, '--client', 'claude')
    assert result.returncode != 0
    assert config.read_text() == '{broken'
    assert 'Setup complete.' not in result.stdout
