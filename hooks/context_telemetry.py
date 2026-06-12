#!/usr/bin/env python3
"""Capture Phase B context-usage telemetry from Claude Code tool hooks."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
ACTIVE_PATH = REPO_ROOT / ".context" / "telemetry" / "active.json"
ORCHESTRATOR_ACTIVE_PATH = REPO_ROOT / ".context" / "telemetry" / "orchestrator-active.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def normalize_path(value: str) -> str:
    value = value.strip().replace("\\", "/")
    root = REPO_ROOT.as_posix().rstrip("/")
    if value.lower().startswith(root.lower() + "/"):
        value = value[len(root) + 1:]
    while value.startswith("./"):
        value = value[2:]
    return value


def initialize_telemetry(
    package: dict[str, Any],
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    selected = [item["path"] for item in package.get("files", [])]
    telemetry = {
        "schema_version": 1,
        "commit": package["commit"],
        "agent": package["agent"],
        "status": "prepared",
        "started_at": utc_now(),
        "ended_at": None,
        "selected_paths": selected,
        "forbidden_paths": package.get("forbidden_edits", []),
        "package": {
            "selected_files": package["budget"]["selected_files"],
            "estimated_chars": package["budget"]["estimated_selected_chars"],
            "usable_chars": package["budget"]["usable_chars_before_reserve"],
            "targeted_excerpt_files": sum(
                item.get("read_strategy", "").startswith("targeted excerpt")
                for item in package.get("files", [])
            ),
            "excluded_candidates": len(package.get("excluded_candidates", [])),
            "expansion_triggers": list(package.get("expansion_triggers", [])),
            "graph_source": package.get("graph", {}).get("source", "unknown"),
            "category_counts": {},
        },
        "tools": {
            "total": 0,
            "reads": 0,
            "searches": 0,
            "writes": 0,
            "tests_or_commands": 0,
        },
        "selected_read_paths": [],
        "outside_read_paths": [],
        "search_events": [],
        "write_paths": [],
    }
    for item in package.get("files", []):
        category = item.get("category", "unknown")
        telemetry["package"]["category_counts"][category] = (
            telemetry["package"]["category_counts"].get(category, 0) + 1
        )
    active_path = repo_root / ".context" / "telemetry" / "active.json"
    active_path.parent.mkdir(parents=True, exist_ok=True)
    active_path.write_text(json.dumps(telemetry, indent=2) + "\n", encoding="utf-8")
    return telemetry


def _commit_key(commit: str) -> str:
    return commit if str(commit).upper().startswith("C") else f"C{str(commit).zfill(2)}"


def initialize_orchestrator_scope(commit: str, repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    """Open an orchestrator telemetry scope for post-agent review and verification."""
    scope = {
        "commit": commit,
        "status": "running",
        "started_at": utc_now(),
        "ended_at": None,
        "tool_calls": 0,
        "read_paths": [],
        "write_paths": [],
        "searches": [],
        "commands": [],
    }
    path = repo_root / ".context" / "telemetry" / "orchestrator-active.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(scope, indent=2) + "\n", encoding="utf-8")
    return scope


def finalize_orchestrator_scope(commit: str, repo_root: Path = REPO_ROOT) -> dict[str, Any] | None:
    """Close the orchestrator scope and write a permanent commit-keyed file.

    Returns None — and writes nothing — if no scope is active, or the active
    scope belongs to a different commit. The latter happens when
    --start-orchestrator was never called for `commit`: a stale "completed"
    scope from a previous commit would otherwise be re-stamped with a new
    ended_at and persisted under the new commit's filename, duplicating the
    previous commit's tool-call history under the wrong commit (see OI-13).
    """
    path = repo_root / ".context" / "telemetry" / "orchestrator-active.json"
    try:
        scope = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    commit_key = _commit_key(commit)
    scope_commit_key = _commit_key(scope.get("commit", ""))
    if scope_commit_key.upper() != commit_key.upper():
        return None
    scope["status"] = "completed"
    scope["ended_at"] = utc_now()
    path.write_text(json.dumps(scope, indent=2) + "\n", encoding="utf-8")
    output = repo_root / ".context" / "telemetry" / f"{commit_key}-orchestrator.json"
    output.write_text(json.dumps(scope, indent=2) + "\n", encoding="utf-8")
    return scope


def _validate_self_report(report: dict[str, Any]) -> None:
    """Validate an agent self-report. Raises ValueError for any malformed field."""
    tool_calls = report.get("tool_calls")
    if tool_calls is None:
        raise ValueError("tool_calls is required in agent self-report")
    if isinstance(tool_calls, bool) or not isinstance(tool_calls, int):
        raise ValueError(
            f"tool_calls must be a non-negative integer, got {type(tool_calls).__name__!r}: {tool_calls!r}"
        )
    if tool_calls < 0:
        raise ValueError(f"tool_calls must be non-negative, got {tool_calls}")

    for key in ("read_paths", "write_paths", "commands", "expansions"):
        val = report.get(key)
        if val is None:
            continue
        if not isinstance(val, list):
            raise ValueError(
                f"{key} must be a list of strings or null, got {type(val).__name__!r}"
            )
        for i, item in enumerate(val):
            if not isinstance(item, str):
                raise ValueError(
                    f"{key}[{i}] must be a string, got {type(item).__name__!r}: {item!r}"
                )

    searches = report.get("searches")
    if searches is None:
        return
    if not isinstance(searches, list):
        raise ValueError(
            f"searches must be a list or null, got {type(searches).__name__!r}"
        )
    for i, item in enumerate(searches):
        if not isinstance(item, dict):
            raise ValueError(
                f"searches[{i}] must be a dict with tool/path/query keys, "
                f"got {type(item).__name__!r}"
            )
        for field in ("tool", "path", "query"):
            if field not in item:
                raise ValueError(f"searches[{i}] missing required field {field!r}")
            if not isinstance(item[field], str):
                raise ValueError(
                    f"searches[{i}].{field} must be a string, "
                    f"got {type(item[field]).__name__!r}"
                )


def record_agent_self_report(
    commit: str,
    agent: str,
    report: dict[str, Any],
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """Validate and persist a structured telemetry report returned by an agent."""
    _validate_self_report(report)
    tool_calls = report.get("tool_calls")
    read_paths = report.get("read_paths")
    write_paths = report.get("write_paths")
    searches = report.get("searches")
    commands = report.get("commands")
    expansions = report.get("expansions")

    # "available" when path-level arrays are present; "partial" when only counts are known
    status = "available" if read_paths is not None else "partial"

    scope = {
        "source": "self_report",
        "status": status,
        "tool_calls": tool_calls,
        "read_paths": read_paths,
        "write_paths": write_paths,
        "searches": searches,
        "commands": commands,
        "expansions": expansions,
    }
    commit_key = commit if str(commit).upper().startswith("C") else f"C{str(commit).zfill(2)}"
    output = repo_root / ".context" / "telemetry" / f"{commit_key}-{agent.lower()}-self-report.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(scope, indent=2) + "\n", encoding="utf-8")
    return scope


def _load_active() -> dict[str, Any] | None:
    try:
        return json.loads(ACTIVE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _load_orchestrator_active() -> dict[str, Any] | None:
    try:
        return json.loads(ORCHESTRATOR_ACTIVE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _active_agent() -> str:
    cap_path = REPO_ROOT / "hooks" / "tool_cap.json"
    try:
        cap = json.loads(cap_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    if not cap.get("active"):
        return ""
    return str(cap.get("agent") or "").lower()


def _tool_path(tool_input: dict[str, Any]) -> str:
    for key in ("file_path", "path", "notebook_path"):
        value = tool_input.get(key)
        if isinstance(value, str) and value.strip():
            return normalize_path(value)
    return ""


def _append_unique(items: list[Any], value: Any) -> None:
    if value not in items:
        items.append(value)


def record_tool_event(event: dict[str, Any]) -> dict[str, Any] | None:
    tool_name = str(event.get("tool_name", ""))
    if tool_name == "Agent":
        return None

    tool_input = event.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        tool_input = {}
    path = _tool_path(tool_input)

    # Route to orchestrator scope when it is active (opened by Claude during review phase)
    orch = _load_orchestrator_active()
    if orch and orch.get("status") == "running":
        orch["tool_calls"] = orch.get("tool_calls", 0) + 1
        if tool_name == "Read" and path:
            _append_unique(orch.setdefault("read_paths", []), path)
        elif tool_name in {"Grep", "Glob"}:
            orch.setdefault("searches", []).append({
                "tool": tool_name,
                "path": path or ".",
                "query": str(tool_input.get("pattern", "")),
            })
        elif tool_name in {"Write", "Edit", "MultiEdit", "NotebookEdit"} and path:
            _append_unique(orch.setdefault("write_paths", []), path)
        elif tool_name == "Bash":
            orch.setdefault("commands", []).append(str(tool_input.get("command", ""))[:120])
        ORCHESTRATOR_ACTIVE_PATH.write_text(json.dumps(orch, indent=2) + "\n", encoding="utf-8")
        return orch

    # Route to agent scope when tool_cap has the matching agent active
    telemetry = _load_active()
    if not telemetry or telemetry.get("status") not in {"prepared", "running"}:
        return telemetry

    active_agent = _active_agent()
    if not active_agent or active_agent != str(telemetry.get("agent", "")).lower():
        return telemetry

    telemetry["status"] = "running"
    telemetry["tools"]["total"] += 1
    selected = set(telemetry.get("selected_paths", []))

    if tool_name == "Read":
        telemetry["tools"]["reads"] += 1
        if path in selected:
            _append_unique(telemetry["selected_read_paths"], path)
        elif path:
            _append_unique(telemetry["outside_read_paths"], path)
    elif tool_name in {"Grep", "Glob"}:
        telemetry["tools"]["searches"] += 1
        search = {
            "tool": tool_name,
            "path": path or ".",
            "query": str(tool_input.get("pattern", "")),
        }
        telemetry["search_events"].append(search)
        if path in selected:
            _append_unique(telemetry["selected_read_paths"], path)
        elif path:
            _append_unique(telemetry["outside_read_paths"], path)
    elif tool_name in {"Write", "Edit", "MultiEdit", "NotebookEdit"}:
        telemetry["tools"]["writes"] += 1
        if path:
            _append_unique(telemetry["write_paths"], path)
    elif tool_name == "Bash":
        telemetry["tools"]["tests_or_commands"] += 1

    ACTIVE_PATH.write_text(json.dumps(telemetry, indent=2) + "\n", encoding="utf-8")
    return telemetry


def finalize_telemetry() -> dict[str, Any] | None:
    telemetry = _load_active()
    if not telemetry:
        return None
    telemetry["status"] = "completed"
    telemetry["ended_at"] = utc_now()
    ACTIVE_PATH.write_text(json.dumps(telemetry, indent=2) + "\n", encoding="utf-8")
    output = (
        REPO_ROOT
        / ".context"
        / "telemetry"
        / f"{telemetry['commit']}-{telemetry['agent']}.json"
    )
    output.write_text(json.dumps(telemetry, indent=2) + "\n", encoding="utf-8")
    return telemetry


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--finalize", action="store_true")
    parser.add_argument(
        "--start-orchestrator",
        metavar="COMMIT",
        help="Open orchestrator scope for the given commit (call before post-agent review)",
    )
    parser.add_argument(
        "--stop-orchestrator",
        metavar="COMMIT",
        help="Close and persist orchestrator scope (call after verification is complete)",
    )
    parser.add_argument(
        "--agent-report",
        nargs=3,
        metavar=("COMMIT", "AGENT", "JSON"),
        help="Persist an agent's structured self-report: COMMIT AGENT '{...}'",
    )
    args = parser.parse_args()

    if args.finalize:
        finalize_telemetry()
        return 0

    if args.start_orchestrator:
        initialize_orchestrator_scope(args.start_orchestrator)
        return 0

    if args.stop_orchestrator:
        scope = finalize_orchestrator_scope(args.stop_orchestrator)
        if scope is None:
            print(
                f"WARNING: no active orchestrator scope for {args.stop_orchestrator} "
                "(was --start-orchestrator called for this commit?). "
                "No orchestrator telemetry file was written.",
                file=sys.stderr,
            )
        return 0

    if args.agent_report:
        commit, agent, json_str = args.agent_report
        try:
            report = json.loads(json_str)
        except json.JSONDecodeError as exc:
            print(f"ERROR: invalid JSON for agent report: {exc}", file=sys.stderr)
            return 1
        try:
            record_agent_self_report(commit, agent, report)
        except ValueError as exc:
            print(f"ERROR: malformed agent report: {exc}", file=sys.stderr)
            return 1
        return 0

    try:
        raw = sys.stdin.read()
        event = json.loads(raw) if raw.strip() else {}
        record_tool_event(event)
    except Exception:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
