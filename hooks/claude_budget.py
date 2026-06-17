#!/usr/bin/env python3
"""Enforce live action, turn, and active-token budgets for Claude scopes."""

from __future__ import annotations

import json
import os
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

WRITE_TOOLS = {"Edit", "MultiEdit", "NotebookEdit", "Write"}
CONTROL_COMMANDS = (
    "hooks/finalize_commit.py",
    "hooks/verify_constraints.py",
    "hooks/context_telemetry.py",
    "hooks/claude_budget.py",
    "hooks/tool_cap_reset.py",
    "hooks/preflight_commit.py",
    "hooks/prepare_agent_delegation.py",
    "git status",
    "git diff",
    "pytest",
)

CLOSEOUT_EDIT_HINTS = (
    ".context/telemetry",
    ".context/direct",
    "commit-protocol.md",
    "project-state.json",
    "/tests/",
)

READ_ONLY_TOOLS = {"Read", "Grep", "Glob"}
RECOVERY_TOOLS = {"Agent"}


def stale_transcript_scope(scope: dict[str, Any]) -> bool:
    """A running scope from a prior Claude transcript must not block a new session."""
    current = os.environ.get("CLAUDE_TRANSCRIPT_PATH")
    recorded = (scope.get("token_usage") or {}).get("transcript_path")
    if not current or not recorded:
        return False
    return str(current).lower() != str(recorded).lower()


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
    if event.get("tool_name") not in {"Bash", "PowerShell"}:
        return False
    command = str((event.get("tool_input") or {}).get("command", "")).lower()
    return any(item.lower() in command for item in CONTROL_COMMANDS)


def is_closeout_action(event: dict[str, Any]) -> bool:
    """Closeout actions cover telemetry correction, verification, and finalization."""
    tool_name = event.get("tool_name")
    if tool_name in {"Bash", "PowerShell"}:
        return allowed_after_stop(event)
    if tool_name in READ_ONLY_TOOLS:
        return True
    tool_input = event.get("tool_input") or {}
    path = str(tool_input.get("file_path") or tool_input.get("path") or "").replace("\\", "/")
    return any(hint in path for hint in CLOSEOUT_EDIT_HINTS)


def is_recovery_action(event: dict[str, Any]) -> bool:
    """Recovery allows a bounded re-invocation/reset path after budget corruption."""
    if event.get("tool_name") in RECOVERY_TOOLS:
        return True
    return is_closeout_action(event)


def is_product_write(event: dict[str, Any]) -> bool:
    """Only product writes remain blocking after Claude's orchestration budget stops."""
    tool_name = event.get("tool_name")
    if tool_name not in WRITE_TOOLS:
        return False
    if is_closeout_action(event):
        return False
    return True


def evaluate(event: dict[str, Any], active_path: Path = ACTIVE_PATH) -> tuple[bool, str]:
    try:
        scope = json.loads(active_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return True, ""
    if scope.get("status") != "running":
        return True, ""
    if stale_transcript_scope(scope):
        return True, "Claude budget: ignoring stale running scope from a prior transcript."

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

    message = (
        f"Claude {name} budget {state}: "
        f"{metrics['actions']} actions, {metrics['turns']} turns, "
        f"{metrics['active_tokens']:,} active tokens, "
        f"{metrics['cache_read_tokens']:,} cached tokens."
    )

    allowed = True
    if state == "stop":
        if not is_product_write(event):
            scope["live_budget"]["state"] = "advisory-stop"
            message += " Advisory only for orchestration; continuing."
        elif allowed_after_stop(event):
            pass
        else:
            override = scope.get("budget_override") or {}
            action_allowed = (
                is_recovery_action(event)
                if override.get("mode") == "recovery"
                else is_closeout_action(event)
            )
            if override.get("uses_remaining", 0) > 0 and action_allowed:
                override["uses_remaining"] -= 1
                scope["budget_override"] = override
                scope["live_budget"]["state"] = "override-used"
                message += f" Override applied to {override.get('mode', 'closeout')} action."
            else:
                allowed = False
                message += (
                    " Split the work or request an override for closeout"
                    " actions (telemetry correction, verification, finalization)."
                )

    active_path.write_text(json.dumps(scope, indent=2) + "\n", encoding="utf-8")
    if not allowed:
        return False, message
    return True, message if state != "ok" else ""


def authorize_override(
    reason: str,
    active_path: Path = ACTIVE_PATH,
    *,
    mode: str = "closeout",
) -> None:
    scope = json.loads(active_path.read_text(encoding="utf-8"))
    uses = 10 if mode == "recovery" else 5
    scope["budget_override"] = {
        "uses_remaining": uses,
        "reason": reason,
        "mode": mode,
    }
    active_path.write_text(json.dumps(scope, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    if len(sys.argv) >= 3 and sys.argv[1] == "--authorize-override":
        args = sys.argv[2:]
        mode = "closeout"
        if "--mode" in args:
            index = args.index("--mode")
            if index + 1 < len(args):
                mode = args[index + 1]
            del args[index:index + 2]
        if mode not in {"closeout", "recovery"}:
            print("ERROR: --mode must be closeout or recovery", file=sys.stderr)
            return 2
        authorize_override(" ".join(args), mode=mode)
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
