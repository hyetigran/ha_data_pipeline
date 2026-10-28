import os
import subprocess
import sys
from pathlib import Path

import pytest

CHECKER = Path(__file__).resolve().parents[1] / 'scripts/check_staged_tokens.py'
HOOK = Path(__file__).resolve().parents[1] / '.githooks'


@pytest.fixture
def repository(tmp_path):
    subprocess.run(['git', 'init', '-q', str(tmp_path)], check=True)
    return tmp_path


def git(root, *args):
    return subprocess.run(['git', '-C', str(root), *args], check=True, capture_output=True)


def check(root):
    return subprocess.run([sys.executable, str(CHECKER)], cwd=root,
                          check=False, capture_output=True, text=True)


def stage(root, name, content):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    git(root, 'add', '--', name)


def test_exact_threshold_and_unstaged_content(repository):
    stage(repository, 'module.py', b'x' * 20_000)
    (repository / 'module.py').write_bytes(b'x' * 30_000)
    (repository / 'unstaged.py').write_bytes(b'x' * 30_000)
    assert check(repository).returncode == 0
    stage(repository, 'module.py', b'x' * 20_001)
    (repository / 'module.py').write_bytes(b'x')
    result = check(repository)
    assert result.returncode == 1
    assert '5,000.25 tokens' in result.stderr
    assert 'extract cohesive modules' in result.stderr
    assert 'Unstaged edits cannot fix' in result.stderr


def test_bytes_not_characters_and_unusual_names(repository):
    name = 'space and\nnewline.txt'
    stage(repository, name, ('é' * 10_001).encode())
    result = check(repository)
    assert result.returncode == 1
    assert '20,002 bytes' in result.stderr
    assert repr(name) in result.stderr


def test_exclusions_use_staged_attributes(repository):
    stage(repository, 'uv.lock', b'x' * 30_000)
    stage(repository, 'generated/output.py', b'x' * 30_000)
    attrs = b'*.lock token-limit-exempt\ngenerated/** token-limit-exempt\n'
    (repository / '.gitattributes').write_bytes(attrs)
    assert check(repository).returncode == 1
    git(repository, 'add', '.gitattributes')
    (repository / '.gitattributes').write_bytes(b'')
    assert check(repository).returncode == 0
    stage(repository, 'maintained.json', b'x' * 30_000)
    assert check(repository).returncode == 1


def test_unchanged_deletions_renames_binary_and_symlink(repository):
    stage(repository, 'existing.txt', b'x' * 30_000)
    git(repository, '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid',
        '-c', 'core.hooksPath=/dev/null', 'commit', '-qm', 'Fixture')
    stage(repository, 'small.txt', b'ok')
    assert check(repository).returncode == 0
    git(repository, 'mv', 'existing.txt', 'renamed.txt')
    assert check(repository).returncode == 1
    git(repository, 'rm', '-f', 'renamed.txt')
    stage(repository, 'asset.bin', b'\0' + b'x' * 30_000)
    os.symlink('small.txt', repository / 'link')
    git(repository, 'add', 'link')
    assert check(repository).returncode == 0


def test_real_hook_blocks_commit(repository):
    scripts = repository / 'scripts'
    scripts.mkdir()
    (scripts / CHECKER.name).write_bytes(CHECKER.read_bytes())
    stage(repository, 'oversized.py', b'x' * 20_001)
    result = subprocess.run(
        ['git', '-C', str(repository), '-c', 'user.name=Test',
         '-c', 'user.email=test@example.invalid', '-c', f'core.hooksPath={HOOK}',
         'commit', '-qm', 'Must be blocked'], check=False, capture_output=True, text=True,
    )
    assert result.returncode != 0
    assert 'Commit blocked' in result.stderr
    assert subprocess.run(['git', '-C', str(repository), 'rev-parse', '--verify', 'HEAD'],
                          check=False, capture_output=True).returncode != 0
