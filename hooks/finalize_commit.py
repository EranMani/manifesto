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
import re
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
from constraint_dashboard import render_dashboard  # noqa: E402

REPO_ROOT = Path(__file__).parent.parent
FINALIZE_DIR = REPO_ROOT / ".context" / "finalize"


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
    parser.add_argument("--render-dashboard", action="store_true",
                         help="Force constraint-dashboard.html render regardless of cadence")
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
    }

    all_pass, checks = step_verify(args.commit, args.agent, args.execution, args.tokens)
    summary["checks"] = checks

    if not all_pass:
        print(json.dumps(summary, indent=2))
        return 1

    numeric = re.match(r"\d+", args.commit)
    is_fifth = bool(numeric) and int(numeric.group(0)) % 5 == 0
    if args.render_dashboard or is_fifth:
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
