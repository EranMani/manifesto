#!/usr/bin/env python3
"""Deterministically activate Claude-direct telemetry before implementation work."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

from context_telemetry import _commit_key, utc_now
from prepare_claude_direct import prepare_direct
from context_engine import load_rules


REPO_ROOT = Path(__file__).resolve().parent.parent
RULES_PATH = Path(__file__).resolve().parent / "context_rules.json"
ACTIVE_PATH = REPO_ROOT / ".context" / "telemetry" / "orchestrator-active.json"
IMPLEMENTATION_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
PATH_KEYS = ("file_path", "path", "notebook_path")
CONTROL_COMMANDS = (
    "hooks/context_telemetry.py",
    "hooks/finalize_commit.py",
    "hooks/prepare_claude_direct.py",
    "hooks/verify_constraints.py",
)

OVERRIDE_PATH = REPO_ROOT / ".context" / "direct"

DIRECT_SCOPE = {
    "execution_mode": "claude-direct",
    "scope_kind": "execution",
    "capture_window": "full-execution",
}


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
    matches = re.findall(
        r"^## (?:Updated )?Files To Modify Or Add\s*$\n(.*?)(?=^## |\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    if not matches:
        return []
    return [
        _normalize_path(path, repo_root)
        for path in re.findall(r"\|\s*`([^`]+)`\s*\|", matches[-1])
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
    return False


def _is_running_direct_scope(active: dict[str, Any]) -> bool:
    return (
        active.get("status") == "running"
        and active.get("execution_mode") == DIRECT_SCOPE["execution_mode"]
        and active.get("scope_kind", DIRECT_SCOPE["scope_kind"])
        == DIRECT_SCOPE["scope_kind"]
        and active.get("capture_window", DIRECT_SCOPE["capture_window"])
        == DIRECT_SCOPE["capture_window"]
    )


def _is_stale_transcript_scope(active: dict[str, Any]) -> bool:
    """Return true when a running scope belongs to an earlier Claude session."""
    current = os.environ.get("CLAUDE_TRANSCRIPT_PATH")
    recorded = (active.get("token_usage") or {}).get("transcript_path")
    if not current or not recorded:
        return False
    return str(current).lower() != str(recorded).lower()


def _archive_mismatched_scope(
    active: dict[str, Any], active_path: Path, commit: str
) -> Path:
    active["status"] = "completed"
    active["ended_at"] = utc_now()
    active["replacement_reason"] = (
        "replaced mismatched telemetry scope before Claude-direct product write"
    )
    suffix = (
        f"{active.get('execution_mode', 'unknown')}-"
        f"{active.get('scope_kind', 'unknown')}-replaced"
    ).replace("/", "-")
    archive = active_path.parent / f"{commit}-{suffix}.json"
    archive.write_text(json.dumps(active, indent=2) + "\n", encoding="utf-8")
    active_path.unlink(missing_ok=True)
    return archive


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
        if _is_running_direct_scope(active) and not _is_stale_transcript_scope(active):
            return True, None
        if active.get("status") == "running":
            archive = _archive_mismatched_scope(
                active,
                repo_root / ".context" / "telemetry" / "orchestrator-active.json",
                commit,
            )
        else:
            return True, None
    else:
        archive = None
    override_file = (repo_root / ".context" / "direct" / f"{commit}-override.json")
    override_justification = None
    if override_file.exists():
        try:
            override_justification = json.loads(
                override_file.read_text(encoding="utf-8")
            ).get("justification")
        except Exception:
            pass
    try:
        prepare_direct(
            repo_root,
            load_rules(repo_root / "hooks" / "context_rules.json"),
            commit,
            owner,
            activate=True,
            override_justification=override_justification,
        )
    except Exception as exc:
        return False, f"cannot activate {commit} Claude-direct capture: {exc}"

    active = _load_json(repo_root / ".context" / "telemetry" / "orchestrator-active.json")
    if not active or active.get("status") != "running":
        return False, f"{commit} capture did not become active"
    message = f"activated {commit} deterministic direct package and telemetry"
    if archive:
        message += f"; archived mismatched scope at {archive.relative_to(repo_root)}"
    return True, message


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
