"""Capture real Codex answers and MCP events without changing user configuration."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import signal
import sqlite3
import subprocess
import sys
import tempfile
import time
from contextlib import closing
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def save(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n")


def fingerprint(path: Path) -> dict[str, str]:
    files = sorted(path.rglob("*")) if path.is_dir() else [path]
    return {
        str(file.relative_to(path) if path.is_dir() else file.name):
        hashlib.sha256(file.read_bytes()).hexdigest()
        for file in files if file.is_file()
    }


def implementation_fingerprint() -> dict[str, str]:
    files = [*sorted((ROOT / 'src/house_account').rglob('*.py')), ROOT / 'uv.lock', ROOT / 'pyproject.toml']
    return {str(file.relative_to(ROOT)): hashlib.sha256(file.read_bytes()).hexdigest() for file in files}


def database_fingerprint(path: Path) -> dict[str, str]:
    with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)) as connection:
        connection.execute('BEGIN')
        return {'logical_sha256': hashlib.sha256('\n'.join(connection.iterdump()).encode()).hexdigest()}


def group_alive(pid: int) -> bool:
    try:
        os.killpg(pid, 0)
        return True
    except ProcessLookupError:
        return False


def stop_group(pid: int, child: subprocess.Popen[str] | None = None) -> bool:
    if group_alive(pid):
        os.killpg(pid, signal.SIGTERM)
        if child is not None:
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pass
        deadline = time.monotonic() + 5
        while group_alive(pid) and time.monotonic() < deadline:
            time.sleep(0.1)
        if group_alive(pid):
            os.killpg(pid, signal.SIGKILL)
            if child is not None:
                child.wait(timeout=10)
    return not group_alive(pid)


def capture(command: list[str], evidence: Path, timeout: int) -> dict[str, Any]:
    save(evidence / "command.json", command)
    with (evidence / "codex.jsonl").open("w") as stdout, (
        evidence / "codex.stderr"
    ).open("w") as stderr:
        child = subprocess.Popen(
            command, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
            cwd=ROOT, start_new_session=True,
        )
        timed_out = False
        try:
            exit_code = child.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            stop_group(child.pid, child)
            exit_code = child.wait(timeout=10)
        except BaseException:
            stop_group(child.pid, child)
            child.wait(timeout=10)
            raise
        deadline = time.monotonic() + 5
        while group_alive(child.pid) and time.monotonic() < deadline:
            time.sleep(0.1)
        forced_cleanup = group_alive(child.pid)
        removed = stop_group(child.pid)
    receipt = {
        "pid": child.pid, "exit_code": exit_code, "timed_out": timed_out,
        "forced_cleanup": forced_cleanup, "process_group_removed": removed,
    }
    save(evidence / "process.json", receipt)
    return receipt


def successful_call(item: dict[str, Any]) -> bool:
    result = item.get("result")
    if item.get("status") != "completed" or item.get("error") or not isinstance(result, dict):
        return False
    if result.get("isError") or result.get("is_error"):
        return False
    payloads = [result.get("structured_content"), result.get("structuredContent")]
    for content in result.get("content", []):
        if content.get("type") == "text":
            try:
                payloads.append(json.loads(content["text"]))
            except (ValueError, KeyError):
                pass
    for payload in payloads:
        if isinstance(payload, dict) and (
            payload.get("isError") or payload.get("is_error") or payload.get("error")
        ):
            return False
    return bool(result.get("content") or any(payloads))


def inspect_events(evidence: Path, expected_tool: str | None = None) -> dict[str, Any]:
    events = [json.loads(line) for line in (evidence / "codex.jsonl").read_text().splitlines()]
    items = [event["item"] for event in events if event.get("type") == "item.completed"]
    calls = [item for item in items if item.get("type") == "mcp_tool_call"]
    messages = [item["text"] for item in items if item.get("type") == "agent_message"]
    forbidden = [item for item in items if item.get("type") in {"command_execution", "file_change"}]
    successful = [call for call in calls if call.get("server") == "house_account" and successful_call(call) and (expected_tool is None or call.get("tool") == expected_tool)]
    answer = messages[-1] if messages else ""
    (evidence / "answer.md").write_text(answer + "\n")
    return {
        "selected_tools": [call.get("tool") for call in calls],
        "tool_calls": calls, "successful_call_count": len(successful),
        "rejected_call_count": sum(not successful_call(call) for call in calls),
        "answer": answer,
        "turn_completed": any(event.get("type") == "turn.completed" for event in events),
        "forbidden_execution": forbidden,
        "transport_verified": bool(successful and answer and not forbidden)
        and all(call.get("server") == "house_account" for call in calls)
        and any(event.get("type") == "turn.completed" for event in events),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True, help="Existing disposable SQLite snapshot")
    parser.add_argument("--data", type=Path, default=ROOT / "data")
    parser.add_argument("--output", type=Path, required=True, help="New directory for retained evidence")
    parser.add_argument("--timeout", type=int, default=240, help="Deadline in seconds per question")
    parser.add_argument("--question", choices=[f"Q{i}" for i in range(1, 7)])
    args = parser.parse_args()
    database, data, output = args.database.resolve(), args.data.resolve(), args.output.resolve()
    if not database.is_file() or not data.is_dir() or args.timeout < 1:
        parser.error("Use an existing disposable database, source directory, and positive timeout")
    if database.is_relative_to(ROOT / "var"):
        parser.error("Copy the working database outside var before running the demo")
    codex = shutil.which("codex")
    if not codex:
        parser.error("Install Codex CLI and authenticate normally before running the demo")
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    questions = json.loads((ROOT / "evals/questions.json").read_text())
    questions = [q for q in questions if not args.question or q["id"] == args.question]
    before = {"sources": fingerprint(data), "database": database_fingerprint(database), "implementation": implementation_fingerprint()}
    save(output / "before.json", before)
    results = []
    with tempfile.TemporaryDirectory(prefix="house-account-codex-demo-") as temporary:
        scratch = Path(temporary)
        for question in questions:
            evidence = output / question["id"]
            evidence.mkdir(mode=0o700)
            prompt = (
                "Use the connected house_account MCP server to answer this question. "
                "Discover and select the appropriate callable tools yourself. This is the Dallas, Texas "
                "home-services dataset. The server exposes tools; empty resource lists do not mean "
                "its tools are unavailable. Follow the discovered input schemas and limits. Do not run shell commands, "
                "read files, use other servers, or use outside sources. Treat today as "
                "2026-11-02 in America/Chicago. Report the evidence, time window, provenance, "
                "and material limitations in your answer. Do not infer availability when it "
                "is unknown. Keep the answer concise enough for a demo.\n\n" + question["question"]
            )
            server_args = [
                "-m", "house_account.cli", "--data", str(data), "--database", str(database),
                "--ledger", str(scratch / "decisions.jsonl"), "--as-of", "2026-11-02",
            ]
            command = [
                codex, "--no-daemon", "exec", "--ignore-user-config", "--ephemeral",
                "--sandbox", "read-only", "--json", "--skip-git-repo-check", "--cd", str(scratch),
                "-c", "mcp_servers.house_account.command=" + json.dumps(str(ROOT / ".venv/bin/python")),
                "-c", "mcp_servers.house_account.args=" + json.dumps(server_args),
                "-c", "mcp_servers.house_account.cwd=" + json.dumps(str(ROOT)), prompt,
            ]
            process = capture(command, evidence, args.timeout)
            try:
                observation = inspect_events(evidence, question["expected_tool"])
            except (ValueError, KeyError, TypeError) as error:
                observation = {"transport_verified": False, "parse_error": str(error)}
            result = {**question, **process, **observation, "evidence": str(evidence)}
            result["status"] = "pass" if (
                result["transport_verified"] and process["exit_code"] == 0
                and not process["timed_out"] and not process["forced_cleanup"]
                and process["process_group_removed"]
            ) else "fail"
            results.append(result)
            save(evidence / "receipt.json", result)
            print(json.dumps({"question": question["id"], "status": result["status"]}), flush=True)
    after = {"sources": fingerprint(data), "database": database_fingerprint(database), "implementation": implementation_fingerprint()}
    save(output / "after.json", after)
    transcript = {
        "client": "Codex CLI", "as_of": "2026-11-02", "questions": results,
        "sources_unchanged": before["sources"] == after["sources"],
        "database_unchanged": before["database"] == after["database"],
        "implementation_unchanged": before["implementation"] == after["implementation"],
        "implementation_sha256": before["implementation"],
        "scratch_removed": not scratch.exists(),
        "semantic_review": "pending independent comparison with source-grounded expectations",
        "status": "pass" if all(result["status"] == "pass" for result in results)
        and before == after and not scratch.exists() else "fail",
    }
    save(output / "agent-transcript.json", transcript)
    print(json.dumps({"status": transcript["status"], "transcript": str(output / "agent-transcript.json")}))
    return 0 if transcript["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
