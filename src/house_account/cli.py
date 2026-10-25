from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import tempfile
from contextlib import closing
from datetime import date
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
    parser = argparse.ArgumentParser(description='Serve six read-only MCP tools, or maintain the local snapshot.')
    parser.add_argument('--data', type=Path, default=Path('data'))
    parser.add_argument('--database', type=Path, default=Path('var/house_account.sqlite'))
    parser.add_argument('--ledger', type=Path, default=Path('review/decisions.jsonl'))
    parser.add_argument('--as-of', type=date.fromisoformat, default=date(2026,11,2))
    subcommands = parser.add_subparsers(dest='command')
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
    query.add_argument('kind',choices=['property','radius','block','provider','openings','available','recommend'])
    query.add_argument('value')
    query.add_argument('--database',type=Path,default=Path('var/house_account.sqlite'))
    query.add_argument('--start')
    query.add_argument('--end')
    query.add_argument('--duration-minutes',type=int)
    query.add_argument('--limit',type=int)
    query.add_argument('--trade')
    query.add_argument('--service')
    arguments = parser.parse_args()
    try:
        if arguments.command is None:
            from .publication import SCHEMA_VERSION, schema_version
            from .server import ServerSettings, create_server
            from .storage import connect_readonly
            database = arguments.database.resolve()
            if not database.exists():
                ingest(arguments.data,database,ledger=arguments.ledger)
            with closing(connect_readonly(database)) as connection:
                if schema_version(connection) != SCHEMA_VERSION or connection.execute('PRAGMA integrity_check').fetchone()[0] != 'ok' or connection.execute('PRAGMA foreign_key_check').fetchone() is not None or connection.execute('SELECT count(*) FROM snapshot').fetchone()[0] != 1:
                    raise ValueError('invalid snapshot')
                connection.execute('SELECT provider_id FROM provider_hour_declarations LIMIT 1')
            create_server(ServerSettings(database,arguments.as_of)).run(transport='stdio')
            return 0
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
            if arguments.kind not in {'openings','available','recommend'} and any(getattr(arguments,key) is not None for key in ('start','end','duration_minutes','limit','trade','service')):
                raise ValueError('availability options require an availability query')
            if arguments.trade is not None and arguments.kind!='available' or arguments.service is not None and arguments.kind!='recommend':
                raise ValueError('trade and service options require matching query kind')
            if arguments.kind in {'openings','available','recommend'}:
                from .availability import available_providers, next_openings
                from .ranking import recommend_providers
                options = {key:getattr(arguments,key) for key in ('start','end','duration_minutes','limit') if getattr(arguments,key) is not None}
                if arguments.kind=='available' and arguments.trade is not None:
                    options['trade']=arguments.trade
                if arguments.kind=='recommend' and arguments.service is not None:
                    options['service']=arguments.service
                operation: Any = {'openings':next_openings,'available':available_providers,'recommend':recommend_providers}[arguments.kind]
                print(json.dumps(operation(arguments.database,arguments.value,**options),sort_keys=True))
                return 0
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
                          'message': 'Query failed; check the provider, supported service, dates, duration and horizon.' if arguments.command=='query' else 'Startup failed; prepare a valid snapshot with the maintenance CLI.' if arguments.command is None else 'Import failed; source data and any previous snapshot are preserved.'}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
