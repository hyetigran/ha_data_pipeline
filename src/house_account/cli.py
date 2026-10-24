from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import tempfile
from pathlib import Path
from typing import Any

from . import adapters
from .storage import ImportFailure, inventory, write_snapshot


def ingest(data: Path, database: Path, *, fail_after: int | None = None) -> dict[str, Any]:
    data = data.resolve()
    database = database.resolve()
    if database == data or data in database.parents:
        raise ImportFailure('database must be outside the source pack')
    files = inventory(data, adapters.file_role)
    def observations():
        yield from adapters.load(data)
        if files != inventory(data, adapters.file_role):
            raise ImportFailure('source pack changed during import')
    return write_snapshot(observations(), database, files, fail_after=fail_after)


def write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix='.report-')
    try:
        with os.fdopen(fd, 'w') as handle:
            json.dump(report, handle, indent=2)
            handle.write('\n')
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description='Import the supplied pack into a private local snapshot.')
    subcommands = parser.add_subparsers(dest='command', required=True)
    command = subcommands.add_parser('ingest')
    command.add_argument('--data', type=Path, default=Path('data'))
    command.add_argument('--database', type=Path, default=Path('var/house_account.sqlite'))
    command.add_argument('--report', type=Path)
    arguments = parser.parse_args()
    try:
        if arguments.report:
            report_path = arguments.report.resolve()
            source = arguments.data.resolve()
            if source == report_path or source in report_path.parents or report_path == arguments.database.resolve():
                raise ImportFailure('report must be outside the data pack and distinct from database')
        report = ingest(arguments.data, arguments.database)
        if arguments.report:
            try:
                write_report(arguments.report, report)
            except OSError:
                print(json.dumps({'status': 'published_report_failed', 'message': 'Snapshot published successfully, but report could not be written.'}), file=sys.stderr)
                return 2
        print(json.dumps({key: value for key, value in report.items() if key != 'files'}, sort_keys=True))
        return 0
    except (ValueError, OSError, RuntimeError, KeyError, TypeError, sqlite3.Error, OverflowError) as exc:
        print(json.dumps({'status': 'failed', 'error_type': type(exc).__name__,
                          'message': 'Import failed; source data and any previous snapshot are preserved.'}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
