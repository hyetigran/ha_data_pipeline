"""Capture all six required answers over real stdio MCP, without fixed old counts."""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import tempfile
from datetime import timedelta
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from verify_p4 import CALLS, logical, public_check


async def capture(database: Path, source: Path, output: Path) -> None:
    database = database.resolve()
    if not database.is_file():
        raise ValueError('An existing isolated snapshot is required')
    output.mkdir(parents=True, exist_ok=False)
    before = logical(database)
    with tempfile.TemporaryDirectory(prefix='required-answers-') as scratch:
        params = StdioServerParameters(command=sys.executable,
            args=['-m','house_account.cli','--database',str(database),'--as-of','2026-11-02'],
            cwd=scratch, env={'PYTHONPATH':str(source.resolve()),'TMPDIR':scratch})
        with (output/'stderr.log').open('w') as stderr:
            async with stdio_client(params,errlog=stderr) as streams, ClientSession(
                    *streams,read_timeout_seconds=timedelta(seconds=120)) as client:
                await client.initialize()
                answers = {}
                for index,(tool,arguments) in enumerate(CALLS,1):
                    result = await client.call_tool(tool,arguments)
                    assert not result.isError, (tool,result)
                    public_check(result.structuredContent)
                    answers[f'Q{index}'] = {'tool':tool,'arguments':arguments,
                                           'answer':result.structuredContent}
                (output/'answers.json').write_text(json.dumps(answers,indent=2)+'\n')
    assert logical(database)==before
    (output/'receipt.json').write_text(json.dumps({
        'tools_called':6,'database_logically_unchanged':True,'scratch_removed':True,
        'source_root':str(source.resolve()),'as_of':'2026-11-02'},indent=2)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database',type=Path,required=True)
    parser.add_argument('--source',type=Path,default=Path('src'))
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    asyncio.run(capture(args.database,args.source,args.output))
