#!/usr/bin/env python3
"""Start a bounded Agent invocation without resetting commit-level totals."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 2
IMPLEMENTORS = {"rex", "adam", "aria", "nova"}
REVIEWERS = {"viktor", "sage", "quinn", "mira", "ryan"}
REVIEW_LIMITS = {"viktor": 15, "sage": 15, "quinn": 15, "mira": 10, "ryan": 5}
DEFAULT_LIMITS = {
    "max_agent_invocations": 1,
    "max_tool_calls": 18,
    "max_expansions": 2,
    "max_implementor_tokens": 45000,
    "max_total_tokens": 60000,
}
_AGENT_ALIASES = {
    "backend": "rex",
    "frontend": "aria",
    "devops": "adam",
    "ai-engineer": "nova",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def git_root() -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=True,
    )
    return Path(result.stdout.strip())


def read_stdin() -> dict[str, Any]:
    try:
        raw = sys.stdin.read()
        return json.loads(raw) if raw.strip() else {}
    except (OSError, json.JSONDecodeError):
        return {}


def normalize_agent_name(value: str) -> str:
    lowered = str(value).lower()
    return _AGENT_ALIASES.get(lowered, lowered)


def load_state(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if payload.get("schema_version") != SCHEMA_VERSION:
        return None
    return payload


def write_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def initialize_commit_state(
    commit: str,
    agent: str,
    selected_paths: list[str],
    limits: dict[str, int] | None = None,
    path: Path | None = None,
) -> dict[str, Any]:
    normalized_commit = commit if str(commit).upper().startswith("C") else f"C{int(commit):02d}"
    budget = {**DEFAULT_LIMITS, **(limits or {})}
    state = {
        "schema_version": SCHEMA_VERSION,
        "commit": normalized_commit.upper(),
        "agent": normalize_agent_name(agent),
        "status": "prepared",
        "active": False,
        "invocation_count": 0,
        "repair_invocation_count": 0,
        "review_invocations": [],
        "active_invocation": None,
        "count": 0,
        "limit": budget["max_tool_calls"],
        "tool_calls": 0,
        "expansions": 0,
        "expanded_paths": [],
        "selected_paths": sorted(set(selected_paths)),
        "write_started": False,
        "known_implementor_tokens": 0,
        "known_total_tokens": 0,
        "limits": budget,
        "repair_authorization": None,
        "stop_reason": None,
        "prepared_at": utc_now(),
    }
    if path is not None:
        write_state(path, state)
    return state


def authorize_repair(
    state: dict[str, Any],
    failing_command: str,
    evidence: str,
    allowed_files: list[str],
    delta_brief_chars: int,
) -> dict[str, Any]:
    limits = state.get("limits", DEFAULT_LIMITS)
    if not state.get("write_started"):
        raise ValueError("repair requires implementation writes")
    if not failing_command.strip() or not evidence.strip():
        raise ValueError("repair requires a failing verification command and evidence")
    if delta_brief_chars > 6000:
        raise ValueError("repair delta brief exceeds 6000 characters")
    if state.get("repair_invocation_count", 0) >= 1:
        raise ValueError("repair invocation already consumed")
    if state.get("known_implementor_tokens", 0) >= limits["max_implementor_tokens"]:
        raise ValueError("implementor token hard stop reached")
    if state.get("known_total_tokens", 0) >= limits["max_total_tokens"]:
        raise ValueError("absolute commit token stop reached")
    state["repair_authorization"] = {
        "failing_command": failing_command,
        "evidence": evidence,
        "allowed_files": sorted(set(allowed_files)),
        "delta_brief_chars": delta_brief_chars,
        "created_at": utc_now(),
        "consumed": False,
    }
    state["status"] = "repair_authorized"
    return state


def start_invocation(
    state: dict[str, Any],
    agent: str,
    kind: str,
) -> dict[str, Any]:
    agent = normalize_agent_name(agent)
    limits = state.get("limits", DEFAULT_LIMITS)
    if state.get("active"):
        raise ValueError("another invocation is already active")
    if state.get("stop_reason"):
        raise ValueError(f"commit is stopped: {state['stop_reason']}")
    if state.get("known_total_tokens", 0) >= limits["max_total_tokens"]:
        raise ValueError("absolute commit token stop reached")

    if kind == "normal":
        if agent not in IMPLEMENTORS:
            raise ValueError(f"{agent} is not an implementor")
        if agent != state.get("agent"):
            raise ValueError(f"prepared agent is {state.get('agent')}, requested {agent}")
        if state.get("invocation_count", 0) >= limits["max_agent_invocations"]:
            raise ValueError("normal implementor invocation already consumed")
        state["invocation_count"] = state.get("invocation_count", 0) + 1
        limit = limits["max_tool_calls"]
    elif kind == "repair":
        authorization = state.get("repair_authorization")
        if not authorization:
            raise ValueError("repair is not authorized")
        if authorization.get("consumed"):
            raise ValueError("repair authorization already consumed")
        if agent != state.get("agent"):
            raise ValueError(f"prepared agent is {state.get('agent')}, requested {agent}")
        if state.get("known_implementor_tokens", 0) >= limits["max_implementor_tokens"]:
            raise ValueError("implementor token hard stop reached")
        authorization["consumed"] = True
        state["repair_invocation_count"] = state.get("repair_invocation_count", 0) + 1
        limit = limits["max_tool_calls"]
    elif kind == "review":
        if agent not in REVIEWERS:
            raise ValueError(f"{agent} is not a reviewer")
        if agent in state.get("review_invocations", []):
            raise ValueError(f"{agent} review invocation already consumed")
        state.setdefault("review_invocations", []).append(agent)
        limit = REVIEW_LIMITS.get(agent, 15)
    else:
        raise ValueError(f"unknown invocation kind: {kind}")

    state["active"] = True
    state["active_invocation"] = {
        "agent": agent,
        "kind": kind,
        "tool_calls": 0,
        "started_at": utc_now(),
    }
    state["count"] = 0
    state["limit"] = limit
    state["status"] = f"{kind}_active"
    return state


def invocation_kind(agent: str, tool_input: dict[str, Any]) -> str:
    if agent in REVIEWERS:
        return "review"
    text = " ".join(
        str(tool_input.get(key, ""))
        for key in ("description", "prompt", "task")
    ).lower()
    return "repair" if "[repair]" in text or "repair invocation" in text else "normal"


def main() -> int:
    try:
        root = git_root()
    except (OSError, subprocess.SubprocessError):
        return 2
    state_path = root / "hooks" / "tool_cap.json"
    state = load_state(state_path)
    if state is None:
        sys.stderr.write("CIRCUIT BREAKER: no valid prepared commit state; Agent invocation blocked.\n")
        return 2

    event = read_stdin()
    tool_input = event.get("tool_input") or {}
    agent = normalize_agent_name(
        tool_input.get("subagent_type")
        or tool_input.get("description", "").split(" ", 1)[0]
        or "unknown"
    )
    kind = invocation_kind(agent, tool_input)
    try:
        start_invocation(state, agent, kind)
        write_state(state_path, state)
    except ValueError as exc:
        state["stop_reason"] = str(exc)
        state["status"] = "blocked"
        write_state(state_path, state)
        sys.stderr.write(f"CIRCUIT BREAKER: {exc}\n")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
