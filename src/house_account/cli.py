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


def ingest(data: Path, database: Path, *, fail_after: int | None = None, ledger: Path = Path('review/decisions.jsonl'), lock_held: bool = False, identity_source: Path | None = None) -> dict[str, Any]:
    data = data.resolve()
    database = database.resolve()
    if database == data or data in database.parents:
        raise ImportFailure('database must be outside the source pack')
    files = inventory(data, adapters.file_role)
    def observations():
        yield from adapters.load(data)
        if files != inventory(data, adapters.file_role):
            raise ImportFailure('source pack changed during import')
    from .identity import reconcile
    return write_snapshot(observations(), database, files, fail_after=fail_after, projector=lambda c: reconcile(c,ledger), lock_held=lock_held, identity_source=identity_source)


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
    command.add_argument('--ledger', type=Path, default=Path('review/decisions.jsonl'))
    review = subcommands.add_parser('review')
    review.add_argument('action', choices=['export','validate','apply'])
    review.add_argument('--file',type=Path,default=Path('review/reconciliation.json'))
    review.add_argument('--ledger',type=Path,default=Path('review/decisions.jsonl'))
    review.add_argument('--data',type=Path,default=Path('data'))
    review.add_argument('--database',type=Path,default=Path('var/house_account.sqlite'))
    review.add_argument('--dry-run',action='store_true')
    query = subcommands.add_parser('query')
    query.add_argument('kind',choices=['property','radius','block','provider'])
    query.add_argument('value')
    query.add_argument('--database',type=Path,default=Path('var/house_account.sqlite'))
    arguments = parser.parse_args()
    try:
        if arguments.command == 'review':
            from .review import apply_review, export_review, safe_paths
            safe_paths(arguments.data,arguments.database,arguments.file,arguments.ledger)
            if arguments.action == 'export':
                result = export_review(arguments.database,arguments.file,arguments.ledger)
            elif arguments.action == 'validate':
                checked = apply_review(arguments.data,arguments.database,arguments.file,arguments.ledger,dry_run=True)
                result = {'status':'valid','new_decisions':checked['decisions_to_record'],'stale_decisions':checked['stale_decisions']}
            else:
                result = apply_review(arguments.data,arguments.database,arguments.file,arguments.ledger,dry_run=arguments.dry_run)
            print(json.dumps(result,sort_keys=True))
            return 0
        if arguments.command == 'query':
            from .queries import (
                block_schedule,
                history_radius,
                property_history,
                provider_summary,
            )
            functions = {'property':property_history,'radius':history_radius,'block':block_schedule,'provider':provider_summary}
            print(json.dumps(functions[arguments.kind](arguments.database,arguments.value),sort_keys=True))
            return 0
        if arguments.report:
            report_path = arguments.report.resolve()
            source = arguments.data.resolve()
            if source == report_path or source in report_path.parents or report_path in {arguments.database.resolve(),arguments.ledger.resolve()}:
                raise ImportFailure('report must be outside the data pack and distinct from database')
        report = ingest(arguments.data, arguments.database, ledger=arguments.ledger)
        if arguments.report:
            try:
                write_report(arguments.report, report)
            except OSError:
                print(json.dumps({'status': 'published_report_failed', 'message': 'Snapshot published successfully, but report could not be written.'}), file=sys.stderr)
                return 2
        print(json.dumps({key: value for key, value in report.items() if key != 'files'}, sort_keys=True))
        return 0
    except (ValueError, OSError, RuntimeError, KeyError, TypeError, sqlite3.Error, OverflowError) as exc:
        if str(exc).startswith('decisions recorded but not applied'):
            print(json.dumps({'status':'recorded_not_applied','message':'Decisions recorded; previous snapshot preserved. Rebuild to recover.'}),file=sys.stderr)
            return 1
        print(json.dumps({'status': 'failed', 'error_type': type(exc).__name__,
                          'message': 'Import failed; source data and any previous snapshot are preserved.'}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
