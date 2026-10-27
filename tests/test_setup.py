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
    for name in ('sources', 'reference'):
        (root / 'data' / name).mkdir(parents=True)
    (root / 'data/README.md').write_text('fixture')
    binaries = tmp_path / 'bin'
    binaries.mkdir()
    log = tmp_path / 'calls.jsonl'
    stub = '''#!PYTHON_EXECUTABLE
import json, os, pathlib, sys
name = pathlib.Path(sys.argv[0]).name
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
    for name in ('uv', 'codex'):
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
        result = invoke(root, env, '--uat')
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
    result = invoke(root, dict(env, SETUP_TEST_FAIL=failure))
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
    result = invoke(root, env, '--data', 'external pack')
    assert result.returncode == 0, result.stderr
    calls = [json.loads(line) for line in log.read_text().splitlines()]
    for _, arguments in calls[1:3]:
        assert arguments[arguments.index('--data') + 1] == str(pack)


def test_bootstrap_missing_tools_without_system_installations(setup_checkout):
    root, env, log = setup_checkout
    binaries = Path(env['PATH'].split(':')[0])
    stub = root.parent / 'tool-stub'
    shutil.copy2(binaries / 'uv', stub)
    for name in ('uv', 'codex'):
        (binaries / name).unlink()
    for name in ('sh', 'dirname', 'uname', 'mktemp', 'rm', 'mkdir'):
        (binaries / name).symlink_to(shutil.which(name))
    curl = binaries / 'curl'
    curl.write_text(f"#!{sys.executable}\n" + r'''import os, pathlib, shlex, sys
if os.environ.get('SETUP_TEST_DOWNLOAD_FAIL'):
    sys.exit(22)
url = sys.argv[2]
assert url in ('https://astral.sh/uv/install.sh', 'https://chatgpt.com/codex/install.sh')
name = 'uv' if 'astral.sh' in url else 'codex'
destination = pathlib.Path(os.environ['HOUSE_ACCOUNT_TOOLS_DIR']) / name
script = '/bin/mkdir -p ' + shlex.quote(str(destination.parent)) + '\n'
script += '/bin/cp ' + shlex.quote(os.environ['SETUP_TEST_STUB']) + ' ' + shlex.quote(str(destination)) + '\n'
script += '/bin/chmod +x ' + shlex.quote(str(destination)) + '\n'
pathlib.Path(sys.argv[sys.argv.index('-o') + 1]).write_text(script)
''')
    curl.chmod(0o755)
    env.update(PATH=str(binaries), HOUSE_ACCOUNT_TOOLS_DIR=str(binaries), SETUP_TEST_STUB=str(stub))
    failed = invoke(root, dict(env, SETUP_TEST_DOWNLOAD_FAIL='1'))
    assert failed.returncode != 0
    assert not log.exists()
    result = invoke(root, env)
    assert result.returncode == 0, result.stderr
    assert 'Installing uv using its official installer' in result.stdout
    assert 'Installing codex using its official installer' in result.stdout
    assert (binaries / 'uv').is_file() and (binaries / 'codex').is_file()
