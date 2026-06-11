#!/usr/bin/env python3
"""Close an Agent invocation while preserving commit-level budget state."""

from __future__ import annotations

import sys
from typing import Any

from tool_cap_start import git_root, load_state, read_stdin, utc_now, write_state


def extract_tokens(payload: Any) -> int | None:
    if isinstance(payload, dict):
        for key in ("total_tokens", "tokens"):
            value = payload.get(key)
            if isinstance(value, int) and not isinstance(value, bool):
                return value
        usage = payload.get("usage")
        if isinstance(usage, dict):
            total = usage.get("total_tokens")
            if isinstance(total, int) and not isinstance(total, bool):
                return total
            input_tokens = usage.get("input_tokens")
            output_tokens = usage.get("output_tokens")
            if isinstance(input_tokens, int) and isinstance(output_tokens, int):
                cache_creation = usage.get("cache_creation_input_tokens", 0)
                cache_read = usage.get("cache_read_input_tokens", 0)
                if not isinstance(cache_creation, int) or isinstance(cache_creation, bool):
                    cache_creation = 0
                if not isinstance(cache_read, int) or isinstance(cache_read, bool):
                    cache_read = 0
                return input_tokens + output_tokens + cache_creation + cache_read
        for value in payload.values():
            found = extract_tokens(value)
            if found is not None:
                return found
    elif isinstance(payload, list):
        for value in payload:
            found = extract_tokens(value)
            if found is not None:
                return found
    return None


def close_invocation(state: dict[str, Any], tokens: int | None = None) -> dict[str, Any]:
    invocation = state.get("active_invocation")
    if not state.get("active") or not invocation:
        return state
    invocation["ended_at"] = utc_now()
    if tokens is not None:
        invocation["tokens"] = tokens
        state["known_total_tokens"] = int(state.get("known_total_tokens", 0)) + tokens
        if invocation.get("kind") in {"normal", "repair"}:
            state["known_implementor_tokens"] = int(state.get("known_implementor_tokens", 0)) + tokens
    state.setdefault("invocations", []).append(invocation)
    kind = invocation.get("kind", "unknown")
    state["active"] = False
    state["active_invocation"] = None
    state["count"] = 0
    state["status"] = f"{kind}_completed"
    limits = state.get("limits", {})
    if state.get("known_implementor_tokens", 0) >= limits.get("max_implementor_tokens", 45000):
        state["stop_reason"] = "implementor_token_hard_stop"
        state["status"] = "blocked"
    if state.get("known_total_tokens", 0) >= limits.get("max_total_tokens", 60000):
        state["stop_reason"] = "absolute_commit_token_stop"
        state["status"] = "blocked"
    return state


def main() -> int:
    try:
        state_path = git_root() / "hooks" / "tool_cap.json"
    except Exception:
        return 0
    state = load_state(state_path)
    if state is None:
        sys.stderr.write("CIRCUIT BREAKER: commit state is missing or corrupt.\n")
        return 2
    event = read_stdin()
    close_invocation(state, extract_tokens(event))
    write_state(state_path, state)
    return 0


if __name__ == "__main__":
    sys.exit(main())
