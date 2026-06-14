#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
finalize_commit.py - Deterministic post-test-pass pipeline.

Runs the steps Claude already performs manually after tests pass, in one
fixed order, stopping at the first failure:

  1. Verify constraints (hooks/verify_constraints.py --worktree, since this
     pipeline always runs pre-commit against the staged/working tree)
  2. Conditional dashboard render (constraint-dashboard.html)
  3. Write the pending-notify flag (hooks/notify_agent_done.py)
  4. Write a finalize marker (.context/finalize/C<NN>.json)

`pre_commit_check.py` requires a fresh, matching marker before a primary
commit (Commit #NN + Execution: Claude-direct / Co-Authored-By:) can land.

Usage:
  python hooks/finalize_commit.py --commit NN --agent OWNER \
      --execution {claude-direct,delegated} [--tokens N] [--render-dashboard] \
      --notify-what "..." --notify-why "..."
"""

import argparse
import contextlib
import io
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# notify_agent_done's get_diff_files() branches on whether PRE_COMMIT is True
# (computed once at import time from sys.argv) to read working-tree state via
# `git status --porcelain` instead of `git diff-tree HEAD`. Append --write-flag
# to sys.argv before importing so the module-level constant comes out True,
# matching the pre-commit context this pipeline always runs in.
_argv_for_import = sys.argv
sys.argv = list(sys.argv) + ["--write-flag"]
import notify_agent_done  # noqa: E402
sys.argv = _argv_for_import

import verify_constraints  # noqa: E402
from context_telemetry import finalize_orchestrator_scope  # noqa: E402
from constraint_dashboard import render_dashboard  # noqa: E402

REPO_ROOT = Path(__file__).parent.parent
FINALIZE_DIR = REPO_ROOT / ".context" / "finalize"
TELEMETRY_DIR = REPO_ROOT / ".context" / "telemetry"


def marker_name(commit: str) -> str:
    return "C" + commit.zfill(2).upper() + ".json"


def step_verify(commit: str, agent: str, execution: str, tokens: int | None):
    """Run verify_constraints.py in-process. Returns (all_pass, checks_dict)."""
    argv = ["verify_constraints.py", "--commit", commit, "--agent", agent,
            "--execution", execution, "--json", "--worktree"]
    if tokens is not None:
        argv += ["--tokens", str(tokens)]

    old_argv = sys.argv
    buf = io.StringIO()
    exit_code = 0
    try:
        sys.argv = argv
        with contextlib.redirect_stdout(buf):
            try:
                verify_constraints.main()
            except SystemExit as exc:
                exit_code = exc.code or 0
    finally:
        sys.argv = old_argv

    output = buf.getvalue().strip()
    result = json.loads(output) if output else {}
    checks = {name: chk.get("message", "") for name, chk in result.get("checks", {}).items()}
    all_pass = bool(result.get("all_pass", False)) and exit_code == 0
    return all_pass, checks


def step_render_dashboard():
    render_dashboard()


def step_close_capture(commit: str) -> tuple[bool, str]:
    """Close the matching active Claude scope as the first finalize action."""
    scope = finalize_orchestrator_scope(commit, REPO_ROOT)
    if scope is not None:
        return True, "closed"

    commit_key = "C" + commit.zfill(2).upper()
    completed_path = TELEMETRY_DIR / f"{commit_key}-orchestrator.json"
    try:
        completed = json.loads(completed_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False, "no matching active or completed Claude scope"
    if completed.get("commit") == commit_key and completed.get("status") == "completed":
        return True, "already closed"
    return False, "no matching active or completed Claude scope"


def step_validate_capture(commit: str, agent: str, execution: str) -> tuple[bool, str]:
    """Fail closed when the current commit lacks the required Claude scope."""
    commit_key = "C" + commit.zfill(2).upper()
    path = TELEMETRY_DIR / f"{commit_key}-orchestrator.json"
    try:
        scope = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False, f"missing completed Claude telemetry scope: {path}"
    if scope.get("status") != "completed" or scope.get("commit") != commit_key:
        return False, "Claude telemetry scope is incomplete or belongs to another commit"
    if execution == "claude-direct":
        required = {
            "owner": agent.lower(),
            "executor": "claude",
            "execution_mode": "claude-direct",
            "scope_kind": "execution",
            "capture_window": "full-execution",
        }
    else:
        required = {
            "owner": agent.lower(),
            "executor": "claude",
            "execution_mode": "delegated",
            "scope_kind": "review",
            "capture_window": "review-only",
        }
    mismatches = [
        f"{key}={scope.get(key)!r} (expected {value!r})"
        for key, value in required.items()
        if str(scope.get(key, "")).lower() != value
    ]
    if mismatches:
        return False, "Claude telemetry metadata mismatch: " + ", ".join(mismatches)
    if execution == "claude-direct":
        token_usage = scope.get("token_usage", {})
        if token_usage.get("status") != "complete":
            reason = token_usage.get("reason", "token snapshot did not complete")
            return False, f"Claude-direct token capture unavailable: {reason}"
        if token_usage.get("assistant_turns", 0) < 1 or scope.get("tool_calls", 0) < 1:
            return False, "Claude-direct capture is empty; execution scope started too late"
    return True, "complete"


def step_write_notify(what: str, why: str, commit: str, agent: str):
    notify_agent_done.write_pending_notify(what, why, num=commit, agent=agent)


def step_write_marker(commit: str, agent: str, execution: str) -> dict:
    FINALIZE_DIR.mkdir(parents=True, exist_ok=True)
    marker = {
        "commit": commit,
        "agent": agent,
        "execution": execution,
        "checks_passed": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    (FINALIZE_DIR / marker_name(commit)).write_text(
        json.dumps(marker, indent=2), encoding="utf-8"
    )
    return marker


def main():
    parser = argparse.ArgumentParser(description="Run the post-test finalize pipeline for a commit.")
    parser.add_argument("--commit", required=True, help="Commit number, e.g. 08 or 33B")
    parser.add_argument("--agent", required=True, help="Commit owner agent name")
    parser.add_argument("--execution", required=True, choices=["claude-direct", "delegated"])
    parser.add_argument("--tokens", type=int, default=None)
    parser.add_argument(
        "--render-dashboard",
        action="store_true",
        help="Deprecated compatibility flag; the dashboard now renders after every successful commit.",
    )
    parser.add_argument("--notify-what", required=True)
    parser.add_argument("--notify-why", required=True)
    args = parser.parse_args()

    summary = {
        "commit": args.commit,
        "status": "blocked",
        "checks": {},
        "dashboard_rendered": False,
        "notify_written": False,
        "marker_written": False,
        "capture": "unchecked",
        "capture_closed": False,
    }

    closed, close_message = step_close_capture(args.commit)
    summary["capture_closed"] = closed
    if not closed:
        summary["capture"] = close_message
        print(json.dumps(summary, indent=2))
        return 1

    capture_ok, capture_message = step_validate_capture(
        args.commit, args.agent, args.execution
    )
    summary["capture"] = capture_message
    if not capture_ok:
        print(json.dumps(summary, indent=2))
        return 1

    all_pass, checks = step_verify(args.commit, args.agent, args.execution, args.tokens)
    summary["checks"] = checks

    if not all_pass:
        print(json.dumps(summary, indent=2))
        return 1

    step_render_dashboard()
    summary["dashboard_rendered"] = True

    step_write_notify(args.notify_what, args.notify_why, args.commit, args.agent)
    summary["notify_written"] = True

    step_write_marker(args.commit, args.agent, args.execution)
    summary["marker_written"] = True

    summary["status"] = "ready"
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
