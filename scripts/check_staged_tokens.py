"""Enforce the authored-file budget against Git's index, not working files."""
from __future__ import annotations

import subprocess
import sys

MAX_BYTES = 20_000


def git(*args: str, data: bytes | None = None) -> bytes:
    return subprocess.run(
        ['git', *args], input=data, capture_output=True, check=True,
    ).stdout


def check() -> int:
    changed = git('diff', '--cached', '--name-only', '--no-renames',
                  '--diff-filter=ACMT', '-z').split(b'\0')
    paths = {path for path in changed if path}
    if not paths:
        return 0
    attributes = git('check-attr', '--cached', '-z', '--stdin',
                     'token-limit-exempt', data=b'\0'.join(sorted(paths)) + b'\0').split(b'\0')
    exempt = {attributes[i] for i in range(0, len(attributes) - 1, 3)
              if attributes[i + 2] == b'set'}
    violations = []
    for entry in git('ls-files', '--stage', '-z').split(b'\0'):
        if not entry:
            continue
        metadata, path = entry.split(b'\t', 1)
        mode, oid, stage = metadata.split()
        if path not in paths or path in exempt or stage != b'0' or mode not in {b'100644', b'100755'}:
            continue
        blob_id = oid.decode('ascii')
        size = int(git('cat-file', '-s', blob_id))
        if size <= MAX_BYTES:
            continue
        content = git('cat-file', 'blob', blob_id)
        if b'\0' in content[:8000]:
            continue
        violations.append((path.decode('utf-8', errors='backslashreplace'), size))
    if not violations:
        return 0
    print('Commit blocked: staged authored files exceed 5,000 tokens (bytes / 4).', file=sys.stderr)
    for path, size in violations:
        print(f'  {path!r}: {size:,} bytes = {size / 4:,.2f} tokens; maximum 20,000 bytes.', file=sys.stderr)
    print(
        '\nSplit each file before committing:\n'
        '  1. Group code by responsibility; extract cohesive modules with narrow interfaces.\n'
        '     Move their tests into matching test files and update imports/callers.\n'
        '  2. Split long documents by topic; keep a short index linking the new pages.\n'
        '     Split maintained fixtures by scenario and update the fixture loaders.\n'
        '  3. Keep EVERY resulting file at or below 20,000 bytes. Do not minify,\n'
        '     remove useful tests/docs, or label authored code as generated to bypass this check.\n'
        '  4. Run relevant checks, then git add the split files, updated callers, and deletions.\n'
        '     Retry the commit. Unstaged edits cannot fix an oversized staged blob.\n'
        '\nFor genuinely generated/vendor files only, add a specific path with\n'
        'token-limit-exempt in .gitattributes and stage that attribute change too.',
        file=sys.stderr,
    )
    return 1


if __name__ == '__main__':
    try:
        sys.exit(check())
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f'Cannot inspect staged files; commit blocked ({type(exc).__name__}).', file=sys.stderr)
        sys.exit(1)
