#!/usr/bin/env python3
"""Enforce live action, turn, and active-token budgets for Claude scopes."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from context_telemetry import _finalize_token_snapshot


REPO_ROOT = Path(__file__).resolve().parent.parent
ACTIVE_PATH = REPO_ROOT / ".context" / "telemetry" / "orchestrator-active.json"

PROFILES = {
    "direct": {
        "warn": {"actions": 25, "turns": 25, "active_tokens": 100_000},
        "stop": {"actions": 40, "turns": 40, "active_tokens": 150_000},
    },
    "review": {
        "warn": {"actions": 15, "turns": 20, "active_tokens": 75_000},
        "stop": {"actions": 20, "turns": 25, "active_tokens": 100_000},
    },
}

EDIT_TOOLS = {"Edit", "MultiEdit", "NotebookEdit", "Write", "Grep", "Glob", "Read"}
CONTROL_COMMANDS = (
    "hooks/finalize_commit.py",
    "hooks/verify_constraints.py",
    "hooks/context_telemetry.py",
    "hooks/claude_budget.py",
    "git status",
    "git diff",
)


def _profile(scope: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    name = "direct" if scope.get("execution_mode") == "claude-direct" else "review"
    return name, PROFILES[name]


def measure(scope: dict[str, Any]) -> dict[str, int]:
    usage = _finalize_token_snapshot(scope.get("token_usage", {}))
    components = usage.get("components", {}) if usage.get("status") == "complete" else {}
    active = sum(
        int(components.get(key, 0))
        for key in ("input_tokens", "output_tokens", "cache_creation_input_tokens")
    )
    return {
        "actions": int(scope.get("tool_calls", 0)),
        "turns": int(usage.get("assistant_turns", 0)),
        "active_tokens": active,
        "cache_read_tokens": int(components.get("cache_read_input_tokens", 0)),
    }


def level(metrics: dict[str, int], profile: dict[str, Any]) -> tuple[str, list[str]]:
    stopped = [
        key for key, limit in profile["stop"].items() if metrics[key] >= limit
    ]
    if stopped:
        return "stop", stopped
    warned = [
        key for key, limit in profile["warn"].items() if metrics[key] >= limit
    ]
    return ("warn", warned) if warned else ("ok", [])


def allowed_after_stop(event: dict[str, Any]) -> bool:
    if event.get("tool_name") != "Bash":
        return False
    command = str((event.get("tool_input") or {}).get("command", "")).lower()
    return any(item.lower() in command for item in CONTROL_COMMANDS)


def evaluate(event: dict[str, Any], active_path: Path = ACTIVE_PATH) -> tuple[bool, str]:
    try:
        scope = json.loads(active_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return True, ""
    if scope.get("status") != "running":
        return True, ""

    name, profile = _profile(scope)
    metrics = measure(scope)
    metrics["actions"] += 1
    state, reasons = level(metrics, profile)
    scope["live_budget"] = {
        "profile": name,
        "state": state,
        "reasons": reasons,
        "metrics": metrics,
        "limits": profile,
        "active_token_formula": "input + output + cache_creation_input",
        "cache_read_policy": "observational only",
    }

    override = scope.get("budget_override") or {}
    if state == "stop" and override.get("uses_remaining", 0) > 0:
        override["uses_remaining"] -= 1
        scope["budget_override"] = override
        state = "warn"
        scope["live_budget"]["state"] = "override-used"

    active_path.write_text(json.dumps(scope, indent=2) + "\n", encoding="utf-8")
    message = (
        f"Claude {name} budget {state}: "
        f"{metrics['actions']} actions, {metrics['turns']} turns, "
        f"{metrics['active_tokens']:,} active tokens, "
        f"{metrics['cache_read_tokens']:,} cached tokens."
    )
    if state == "stop" and not allowed_after_stop(event):
        return False, message + " Split the work or request an explicit one-use override."
    return True, message if state != "ok" else ""


def authorize_override(reason: str, active_path: Path = ACTIVE_PATH) -> None:
    scope = json.loads(active_path.read_text(encoding="utf-8"))
    scope["budget_override"] = {"uses_remaining": 1, "reason": reason}
    active_path.write_text(json.dumps(scope, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    if len(sys.argv) >= 3 and sys.argv[1] == "--authorize-override":
        authorize_override(" ".join(sys.argv[2:]))
        return 0
    try:
        event = json.loads(sys.stdin.read() or "{}")
        allowed, message = evaluate(event)
        if message:
            print(message, file=sys.stderr)
        return 0 if allowed else 2
    except Exception:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
