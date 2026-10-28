"""Export portable MCP settings and optionally merge Claude's project entry."""
from __future__ import annotations

import argparse
import json
import os
import shlex
import tempfile
from pathlib import Path


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix='.mcp-')
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(value, stream, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def configure(root: Path, data: Path, database: Path, ledger: Path, state: Path, client: str) -> dict:
    entry = {
        'type': 'stdio',
        'command': str(root / '.venv/bin/python'),
        'args': ['-m', 'house_account.cli', '--data', str(data), '--database', str(database),
                 '--ledger', str(ledger), '--as-of', '2026-11-02'],
    }
    exported = {'mcpServers': {'house_account': entry}}
    if client == 'claude':
        path = root / '.mcp.json'
        config = json.loads(path.read_text()) if path.exists() else {}
        if not isinstance(config, dict) or not isinstance(config.get('mcpServers', {}), dict):
            raise ValueError('Existing .mcp.json must contain an object of mcpServers')
        config.setdefault('mcpServers', {})['house_account'] = entry
        write_json(path, config)
    write_json(state / 'mcp-config.json', exported)
    return entry


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('root', 'data', 'database', 'ledger', 'state'):
        parser.add_argument(f'--{name}', type=Path, required=True)
    parser.add_argument('--client', choices=('codex', 'claude', 'none'), required=True)
    args = parser.parse_args()
    entry = configure(*(getattr(args, key).resolve() for key in ('root', 'data', 'database', 'ledger', 'state')), args.client)
    if args.client == 'none':
        print('Server executable and arguments:')
        print(json.dumps(entry, indent=2))
        print('Equivalent launch command:')
        print(shlex.join([entry['command'], *entry['args']]))


if __name__ == '__main__':
    main()
