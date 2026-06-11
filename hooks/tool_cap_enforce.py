#!/usr/bin/env python3
"""Enforce tool, expansion, and token limits for the active commit invocation."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from tool_cap_start import git_root, load_state, read_stdin, write_state


WRITE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
PATH_KEYS = ("file_path", "path")


def normalize_path(path: str, repo_root: Path | None = None) -> str:
    normalized = str(path).strip().replace("\\", "/")
    if repo_root is not None:
        root = repo_root.resolve().as_posix().rstrip("/")
        if normalized.casefold() == root.casefold():
            return ""
        prefix = root + "/"
        if normalized.casefold().startswith(prefix.casefold()):
            normalized = normalized[len(prefix):]
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def tool_path(
    tool_input: dict[str, Any],
    repo_root: Path | None = None,
) -> str:
    for key in PATH_KEYS:
        value = tool_input.get(key)
        if value:
            return normalize_path(str(value), repo_root)
    return ""


def selected(
    path: str,
    selected_paths: list[str],
    repo_root: Path | None = None,
) -> bool:
    normalized = normalize_path(path, repo_root)
    return any(
        normalized == normalize_path(allowed, repo_root)
        or normalized.startswith(normalize_path(allowed, repo_root).rstrip("/") + "/")
        for allowed in selected_paths
    )


def enforce_tool_event(
    state: dict[str, Any],
    tool_name: str,
    tool_input: dict[str, Any],
    repo_root: Path | None = None,
) -> tuple[bool, str | None]:
    if not state.get("active") or not state.get("active_invocation"):
        return True, None
    if tool_name == "Agent":
        return True, None

    path = tool_path(tool_input, repo_root)
    if path.endswith("hooks/tool_cap.json") or path == "hooks/tool_cap.json":
        return True, None

    invocation = state["active_invocation"]
    next_call = int(invocation.get("tool_calls", 0)) + 1
    limit = int(state.get("limit", 18))
    limits = state.get("limits", {})
    greenfield = int(limits.get("max_tool_calls", 18)) > 18
    if next_call > limit:
        state["stop_reason"] = f"tool_call_limit:{limit}"
        state["status"] = "blocked"
        return False, f"tool call {next_call} exceeds the limit of {limit}"

    if (
        greenfield
        and next_call == 6
        and tool_name not in WRITE_TOOLS
        and not state.get("write_started")
        and invocation.get("kind") == "normal"
    ):
        state["stop_reason"] = "greenfield_implementation_not_started:6"
        state["status"] = "blocked"
        return False, "call 6: implementation must have started (greenfield budget)"

    if invocation.get("kind") in {"normal", "repair"}:
        if state.get("known_implementor_tokens", 0) >= limits.get("max_implementor_tokens", 45000):
            state["stop_reason"] = "implementor_token_hard_stop"
            state["status"] = "blocked"
            return False, "implementor token hard stop reached"
        if state.get("known_total_tokens", 0) >= limits.get("max_total_tokens", 60000):
            state["stop_reason"] = "absolute_commit_token_stop"
            state["status"] = "blocked"
            return False, "absolute commit token stop reached"

    if tool_name in WRITE_TOOLS:
        if invocation.get("kind") == "repair":
            allowed = (state.get("repair_authorization") or {}).get("allowed_files", [])
            if path and not selected(path, allowed, repo_root):
                state["stop_reason"] = f"repair_path_not_authorized:{path}"
                state["status"] = "blocked"
                return False, f"repair write is outside authorized files: {path}"
        state["write_started"] = True

    expansion_tools = {"Read", "Grep", "Glob"}
    if (
        tool_name in expansion_tools
        and path
        and not selected(path, state.get("selected_paths", []), repo_root)
    ):
        expanded = state.setdefault("expanded_paths", [])
        if path not in expanded:
            next_expansion = len(expanded) + 1
            max_expansions = state.get("limits", {}).get("max_expansions", 2)
            if next_expansion > max_expansions:
                state["stop_reason"] = f"expansion_limit:{max_expansions}"
                state["status"] = "blocked"
                return False, f"context expansion {next_expansion} exceeds the limit of {max_expansions}"
            expanded.append(path)
            state["expansions"] = len(expanded)

    invocation["tool_calls"] = next_call
    state["count"] = next_call
    if invocation.get("kind") in {"normal", "repair"}:
        state["tool_calls"] = int(state.get("tool_calls", 0)) + 1

    warning = None
    if next_call in {6, 7, 8} and not state.get("write_started") and invocation.get("kind") == "normal":
        warning = f"call {next_call}: implementation has not started; prepare to split"
    elif greenfield and next_call == 22:
        warning = "call 22: report budget status and remaining acceptance criteria"
    elif greenfield and next_call == 26:
        warning = "call 26: finish or return SPLIT_REQUIRED"
    elif not greenfield and next_call == 12:
        warning = "call 12: report budget status and remaining acceptance criteria"
    elif not greenfield and next_call == 16:
        warning = "call 16: finish by call 18 or return SPLIT_REQUIRED"
    elif next_call == limit:
        warning = f"call {next_call}: final allowed tool call"
    return True, warning


def main() -> int:
    try:
        state_path: Path = git_root() / "hooks" / "tool_cap.json"
    except Exception:
        return 0
    state = load_state(state_path)
    if state is None or not state.get("active"):
        return 0
    event = read_stdin()
    allowed, message = enforce_tool_event(
        state,
        str(event.get("tool_name", "")),
        event.get("tool_input") or {},
        state_path.parent.parent,
    )
    write_state(state_path, state)
    if message:
        sys.stderr.write(f"CIRCUIT BREAKER: {message}\n")
    return 0 if allowed else 2


if __name__ == "__main__":
    sys.exit(main())
