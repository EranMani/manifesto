#!/usr/bin/env python3
"""Deterministically activate Claude-direct telemetry before implementation work."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

from context_telemetry import _commit_key
from prepare_claude_direct import prepare_direct
from context_engine import load_rules


REPO_ROOT = Path(__file__).resolve().parent.parent
RULES_PATH = Path(__file__).resolve().parent / "context_rules.json"
ACTIVE_PATH = REPO_ROOT / ".context" / "telemetry" / "orchestrator-active.json"
IMPLEMENTATION_TOOLS = {"Read", "Grep", "Glob", "Write", "Edit", "MultiEdit", "NotebookEdit", "Bash"}
PATH_KEYS = ("file_path", "path", "notebook_path")
CONTROL_COMMANDS = (
    "hooks/context_telemetry.py",
    "hooks/finalize_commit.py",
    "hooks/prepare_claude_direct.py",
    "hooks/verify_constraints.py",
)


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _normalize_path(value: str, repo_root: Path = REPO_ROOT) -> str:
    value = value.strip().replace("\\", "/")
    root = repo_root.resolve().as_posix().rstrip("/")
    if value.lower().startswith(root.lower() + "/"):
        value = value[len(root) + 1 :]
    return value.removeprefix("./")


def _pending_commit(repo_root: Path = REPO_ROOT) -> tuple[str, str] | None:
    state = _load_json(repo_root / "project-state.json") or {}
    commit = str(state.get("next_commit", "")).strip()
    owner = str(state.get("next_commit_assignee", "")).strip().lower()
    if not commit or not owner or state.get("status") in {"complete", "blocked"}:
        return None
    return _commit_key(commit), owner


def _planned_files(repo_root: Path, commit: str) -> list[str]:
    match = re.fullmatch(r"C(\d+)([A-Z]?)", commit.upper())
    if not match:
        return []
    number, suffix = match.groups()
    spec = repo_root / "commit-specs" / f"commit-{int(number):02d}{suffix.lower()}.md"
    try:
        text = spec.read_text(encoding="utf-8")
    except OSError:
        return []
    section = re.search(
        r"^## Files To Modify Or Add\s*$\n(.*?)(?=^## |\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    if not section:
        return []
    return [
        _normalize_path(path, repo_root)
        for path in re.findall(r"\|\s*`([^`]+)`\s*\|", section.group(1))
    ]


def _event_path(event: dict[str, Any], repo_root: Path = REPO_ROOT) -> str:
    tool_input = event.get("tool_input") or {}
    for key in PATH_KEYS:
        value = tool_input.get(key)
        if isinstance(value, str) and value.strip():
            return _normalize_path(value, repo_root)
    return ""


def _targets_commit(
    event: dict[str, Any], planned: list[str], repo_root: Path = REPO_ROOT
) -> bool:
    tool_name = str(event.get("tool_name", ""))
    if tool_name not in IMPLEMENTATION_TOOLS:
        return False
    path = _event_path(event, repo_root)
    if path:
        normalized = path.rstrip("/")
        return any(
            normalized == item
            or item.startswith(normalized + "/")
            or normalized.startswith(item + "/")
            for item in planned
        )
    if tool_name == "Bash":
        command = str((event.get("tool_input") or {}).get("command", "")).replace(
            "\\", "/"
        )
        if any(control in command.lower() for control in CONTROL_COMMANDS):
            return False
        return any(path in command or Path(path).name in command for path in planned)
    return False


def ensure_direct_scope(
    event: dict[str, Any], repo_root: Path = REPO_ROOT
) -> tuple[bool, str | None]:
    pending = _pending_commit(repo_root)
    if pending is None:
        return True, None
    commit, owner = pending
    planned = _planned_files(repo_root, commit)
    if not planned or not _targets_commit(event, planned, repo_root):
        return True, None

    active = _load_json(repo_root / ".context" / "telemetry" / "orchestrator-active.json")
    if active and str(active.get("commit", "")).upper() == commit:
        if (
            active.get("status") == "running"
            and active.get("execution_mode") == "claude-direct"
        ):
            return True, None
        # Preserve existing evidence without trapping later tools. Explicit
        # initialization remains protected by the lower-level overwrite guard.
        return True, None
    try:
        prepare_direct(
            repo_root,
            load_rules(repo_root / "hooks" / "context_rules.json"),
            commit,
            owner,
            activate=True,
        )
    except Exception as exc:
        return False, f"cannot activate {commit} Claude-direct capture: {exc}"

    active = _load_json(repo_root / ".context" / "telemetry" / "orchestrator-active.json")
    if not active or active.get("status") != "running":
        return False, f"{commit} capture did not become active"
    return True, f"activated {commit} deterministic direct package and telemetry"


def main() -> int:
    try:
        raw = sys.stdin.read()
        event = json.loads(raw) if raw.strip() else {}
    except Exception:
        sys.stderr.write("DIRECT LIFECYCLE: invalid PreToolUse payload\n")
        return 2
    allowed, message = ensure_direct_scope(event)
    if message:
        sys.stderr.write(f"DIRECT LIFECYCLE: {message}\n")
    return 0 if allowed else 2


if __name__ == "__main__":
    raise SystemExit(main())
