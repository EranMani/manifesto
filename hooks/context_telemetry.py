#!/usr/bin/env python3
"""Capture Phase B context-usage telemetry from Claude Code tool hooks."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
ACTIVE_PATH = REPO_ROOT / ".context" / "telemetry" / "active.json"
ORCHESTRATOR_ACTIVE_PATH = REPO_ROOT / ".context" / "telemetry" / "orchestrator-active.json"
TOKEN_FIELDS = (
    "input_tokens",
    "output_tokens",
    "cache_creation_input_tokens",
    "cache_read_input_tokens",
)


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


def _find_transcript(repo_root: Path = REPO_ROOT) -> Path | None:
    """Find the active Claude transcript for this repository."""
    explicit = os.environ.get("CLAUDE_TRANSCRIPT_PATH")
    if explicit:
        path = Path(explicit)
        return path if path.is_file() else None

    projects = Path.home() / ".claude" / "projects"
    try:
        candidates = sorted(
            projects.glob("*/*.jsonl"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
    except OSError:
        return None
    expected = json.dumps(str(repo_root), ensure_ascii=True)[1:-1].lower()
    for path in candidates[:50]:
        try:
            size = path.stat().st_size
            with path.open("rb") as handle:
                handle.seek(max(0, size - 131072))
                tail = handle.read().decode("utf-8", errors="replace").lower()
        except OSError:
            continue
        if f'"cwd":"{expected}"' in tail:
            return path
    return None


def _token_snapshot(repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    transcript = _find_transcript(repo_root)
    if transcript is None:
        return {
            "status": "unavailable",
            "reason": "Claude transcript not found",
            "source": "claude-transcript-jsonl",
        }
    try:
        offset = transcript.stat().st_size
    except OSError:
        return {
            "status": "unavailable",
            "reason": "Claude transcript could not be read",
            "source": "claude-transcript-jsonl",
        }
    return {
        "status": "running",
        "source": "claude-transcript-jsonl",
        "transcript_path": str(transcript),
        "start_offset": offset,
        "formula": "input + output + cache_creation_input + cache_read_input",
        "excludes": "sidechain and separate delegated-agent transcripts",
    }


def _finalize_token_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    if snapshot.get("status") != "running":
        return snapshot
    path = Path(str(snapshot.get("transcript_path", "")))
    start_offset = snapshot.get("start_offset")
    if not isinstance(start_offset, int):
        return {**snapshot, "status": "unavailable", "reason": "invalid start offset"}
    try:
        end_offset = path.stat().st_size
        if end_offset < start_offset:
            raise OSError("transcript was truncated")
        with path.open("rb") as handle:
            handle.seek(start_offset)
            raw = handle.read(end_offset - start_offset)
    except OSError as exc:
        return {**snapshot, "status": "unavailable", "reason": str(exc)}

    totals = {field: 0 for field in TOKEN_FIELDS}
    assistant_turns = 0
    malformed_lines = 0
    for raw_line in raw.splitlines():
        try:
            entry = json.loads(raw_line.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            malformed_lines += 1
            continue
        if entry.get("type") != "assistant" or entry.get("isSidechain") is True:
            continue
        usage = (entry.get("message") or {}).get("usage")
        if not isinstance(usage, dict):
            continue
        values: dict[str, int] = {}
        valid = True
        for field in TOKEN_FIELDS:
            value = usage.get(field, 0)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                valid = False
                break
            values[field] = value
        if not valid:
            malformed_lines += 1
            continue
        assistant_turns += 1
        for field, value in values.items():
            totals[field] += value

    if malformed_lines:
        return {
            **snapshot,
            "status": "unavailable",
            "reason": f"{malformed_lines} malformed usage record(s)",
            "end_offset": end_offset,
        }
    return {
        **snapshot,
        "status": "complete",
        "end_offset": end_offset,
        "assistant_turns": assistant_turns,
        "components": totals,
        "total_tokens": sum(totals.values()),
    }


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


class NoMatchingInvocationError(ValueError):
    """Raised when --agent-report has no matching tool_cap.json invocation."""


def _require_matching_invocation(repo_root: Path, commit: str, agent: str) -> None:
    """Guard against fabricated self-reports for commits where no agent ran.

    --agent-report (CLAUDE.md step 5a) is valid only after a delegated agent
    invocation, which activates hooks/tool_cap.json with this commit's key and
    agent name (tool_cap_start.py). For Claude-direct commits no agent runs, so
    tool_cap.json reflects a stale, unrelated invocation. Persisting a self-report
    in that case fabricates agent telemetry and mislabels the invocation kind
    (see COMMIT_HEALTH_RUBRIC.md C37). Refuse rather than guess.
    """
    cap_path = repo_root / "hooks" / "tool_cap.json"
    try:
        cap = json.loads(cap_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        cap = {}
    cap_commit = _commit_key(str(cap.get("commit", "")))
    cap_agent = str(cap.get("agent", "")).lower()
    if cap_commit != _commit_key(commit) or cap_agent != agent.lower():
        raise NoMatchingInvocationError(
            f"tool_cap.json shows no invocation for {agent} on {_commit_key(commit)} "
            f"(tool_cap commit={cap_commit or '<none>'}, agent={cap_agent or '<none>'}). "
            "--agent-report is valid only after a delegated agent invocation. For "
            "Claude-direct commits, do not call --agent-report at all -- "
            "telemetry.agent will correctly record as 'unavailable'."
        )


def _resolve_invocation_kind(repo_root: Path) -> str:
    """Read the relevant invocation's kind (normal/repair/review) from tool_cap.json.

    Prefers the still-open active_invocation (finalize_telemetry runs while it is
    set). Falls back to the most recently closed invocation (record_agent_self_report
    runs after tool_cap_end has already moved active_invocation into the
    invocations history).
    """
    cap_path = repo_root / "hooks" / "tool_cap.json"
    try:
        cap = json.loads(cap_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "normal"
    invocation = cap.get("active_invocation")
    if not invocation:
        history = cap.get("invocations") or []
        invocation = history[-1] if history else {}
    kind = invocation.get("kind")
    return kind if kind in {"normal", "repair", "review"} else "normal"


def _next_invocation_record_path(
    repo_root: Path, commit: str, agent: str, kind: str, record_type: str
) -> Path:
    """Return the next unused immutable record path for this invocation."""
    inv_dir = repo_root / ".context" / "telemetry" / "invocations"
    inv_dir.mkdir(parents=True, exist_ok=True)
    commit_key = _commit_key(commit)
    seq = 1
    while True:
        path = inv_dir / f"{commit_key}-{agent.lower()}-{kind}-{record_type}-{seq}.json"
        if not path.exists():
            return path
        seq += 1


def _write_invocation_record(
    repo_root: Path,
    commit: str,
    agent: str,
    kind: str,
    record_type: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Persist one immutable record for a normal, repair, or review invocation.

    Each call appends a new file (never overwrites a prior one), so the full
    history of invocations for a commit/agent/kind is preserved for C31's
    aggregation.
    """
    path = _next_invocation_record_path(repo_root, commit, agent, kind, record_type)
    record = {
        "commit": _commit_key(commit),
        "agent": agent.lower(),
        "kind": kind,
        "record_type": record_type,
        "recorded_at": utc_now(),
        **payload,
    }
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return record


def initialize_orchestrator_scope(
    commit: str,
    repo_root: Path = REPO_ROOT,
    *,
    owner: str | None = None,
    execution_mode: str = "delegated",
    scope_kind: str = "review",
    capture_window: str = "review-only",
) -> dict[str, Any]:
    """Open a Claude telemetry scope with explicit execution semantics."""
    path = repo_root / ".context" / "telemetry" / "orchestrator-active.json"
    try:
        existing = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        existing = None
    commit_key = _commit_key(commit)
    if existing:
        existing_commit = _commit_key(existing.get("commit", ""))
        existing_status = existing.get("status")
        if existing_commit.upper() == commit_key.upper():
            raise ValueError(
                f"{commit_key} telemetry scope already exists with status "
                f"{existing_status!r}"
            )
        if existing_status == "running":
            raise ValueError(
                f"cannot replace running {existing_commit} telemetry scope"
            )
    scope = {
        "schema_version": 2,
        "commit": commit_key,
        "owner": owner.lower() if owner else None,
        "executor": "claude",
        "execution_mode": execution_mode,
        "scope_kind": scope_kind,
        "capture_window": capture_window,
        "status": "running",
        "started_at": utc_now(),
        "ended_at": None,
        "tool_calls": 0,
        "read_paths": [],
        "write_paths": [],
        "searches": [],
        "commands": [],
        "token_usage": _token_snapshot(repo_root),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(scope, indent=2) + "\n", encoding="utf-8")
    return scope


def initialize_execution_scope(
    commit: str,
    owner: str,
    repo_root: Path = REPO_ROOT,
    *,
    package: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Open full Claude-direct capture before implementation begins."""
    scope = initialize_orchestrator_scope(
        commit,
        repo_root,
        owner=owner,
        execution_mode="claude-direct",
        scope_kind="execution",
        capture_window="full-execution",
    )
    if package:
        selected = [item["path"] for item in package.get("files", [])]
        planned = [
            item["path"]
            for item in package.get("files", [])
            if item.get("category") in {"primary", "test"}
        ]
        scope["context_package"] = {
            "path": f".context/runs/{package['commit']}-claude-direct.json",
            "brief_path": f".context/direct/{package['commit']}.md",
            "selection_policy": package.get("selection_policy"),
            "selected_paths": selected,
            "planned_paths": planned,
            "selected_files": package.get("budget", {}).get("selected_files"),
            "estimated_chars": package.get("budget", {}).get(
                "estimated_selected_chars"
            ),
        }
        scope["selected_read_paths"] = []
        scope["outside_read_paths"] = []
        path = repo_root / ".context" / "telemetry" / "orchestrator-active.json"
        path.write_text(json.dumps(scope, indent=2) + "\n", encoding="utf-8")
    return scope


def initialize_review_scope(
    commit: str, owner: str, repo_root: Path = REPO_ROOT
) -> dict[str, Any]:
    """Open Claude review capture after a delegated implementor returns."""
    return initialize_orchestrator_scope(
        commit,
        repo_root,
        owner=owner,
        execution_mode="delegated",
        scope_kind="review",
        capture_window="review-only",
    )


def finalize_orchestrator_scope(commit: str, repo_root: Path = REPO_ROOT) -> dict[str, Any] | None:
    """Close the active Claude scope and write a permanent commit-keyed file.

    Returns None — and writes nothing — if no scope is active, or the active
    scope belongs to a different commit. The latter happens when
    no matching start command was called for `commit`: a stale "completed"
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
    if scope.get("status") != "running":
        return None
    scope["status"] = "completed"
    scope["ended_at"] = utc_now()
    scope["token_usage"] = _finalize_token_snapshot(scope.get("token_usage", {}))
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
    invocation_kind: str | None = None,
) -> dict[str, Any]:
    """Validate and persist a structured telemetry report returned by an agent."""
    _validate_self_report(report)
    _require_matching_invocation(repo_root, commit, agent)
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

    kind = invocation_kind or _resolve_invocation_kind(repo_root)
    _write_invocation_record(repo_root, commit, agent, kind, "self-report", scope)
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

    # Route to the active Claude execution or review scope.
    orch = _load_orchestrator_active()
    if orch and orch.get("status") == "running":
        orch["tool_calls"] = orch.get("tool_calls", 0) + 1
        if tool_name == "Read" and path:
            _append_unique(orch.setdefault("read_paths", []), path)
            selected = set(
                orch.get("context_package", {}).get("selected_paths", [])
            )
            if selected:
                target = (
                    orch.setdefault("selected_read_paths", [])
                    if path in selected
                    else orch.setdefault("outside_read_paths", [])
                )
                _append_unique(target, path)
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

    kind = _resolve_invocation_kind(REPO_ROOT)
    _write_invocation_record(REPO_ROOT, telemetry["commit"], telemetry["agent"], kind, "hooks", telemetry)
    return telemetry


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--finalize", action="store_true")
    parser.add_argument(
        "--start-orchestrator",
        metavar="COMMIT",
        help="Legacy alias: open a delegated review-only Claude scope",
    )
    parser.add_argument(
        "--start-execution",
        nargs=2,
        metavar=("COMMIT", "OWNER"),
        help="Open full Claude-direct capture before implementation begins",
    )
    parser.add_argument(
        "--start-review",
        nargs=2,
        metavar=("COMMIT", "OWNER"),
        help="Open Claude review capture after delegated implementation",
    )
    parser.add_argument(
        "--stop-orchestrator",
        metavar="COMMIT",
        help="Close and persist the active Claude scope after verification",
    )
    parser.add_argument(
        "--agent-report",
        nargs=3,
        metavar=("COMMIT", "AGENT", "JSON"),
        help="Persist an agent's structured self-report: COMMIT AGENT '{...}'",
    )
    parser.add_argument(
        "--invocation-kind",
        choices=["normal", "repair", "review"],
        default=None,
        help="Override the invocation kind for --agent-report (default: read from tool_cap.json)",
    )
    args = parser.parse_args()

    if args.finalize:
        finalize_telemetry()
        return 0

    if args.start_orchestrator:
        initialize_orchestrator_scope(args.start_orchestrator)
        return 0

    if args.start_execution:
        commit, owner = args.start_execution
        initialize_execution_scope(commit, owner)
        return 0

    if args.start_review:
        commit, owner = args.start_review
        initialize_review_scope(commit, owner)
        return 0

    if args.stop_orchestrator:
        scope = finalize_orchestrator_scope(args.stop_orchestrator)
        if scope is None:
            print(
                f"WARNING: no active Claude scope for {args.stop_orchestrator}. "
                "No Claude telemetry file was written.",
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
            record_agent_self_report(commit, agent, report, invocation_kind=args.invocation_kind)
        except NoMatchingInvocationError as exc:
            print(f"ERROR: no matching agent invocation: {exc}", file=sys.stderr)
            return 1
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
