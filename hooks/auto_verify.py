#!/usr/bin/env python3
"""
auto_verify.py - Stop hook wrapper for verify_constraints.py.

Only runs if CLAUDE_COMMIT=1 is set in the environment.
Reads project-state.json to get the last completed commit and agent,
then calls verify_constraints.py automatically.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent


def get_agent_from_spec(commit):
    spec_path = REPO_ROOT / "commit-specs" / f"commit-{str(commit).zfill(2)}.md"
    if not spec_path.exists():
        return None
    for line in spec_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("**Assignee:**"):
            return line.split(":**")[1].strip().split()[0].lower()
    return None


def main():
    if not os.environ.get("CLAUDE_COMMIT"):
        sys.exit(0)

    state_path = REPO_ROOT / "project-state.json"
    if not state_path.exists():
        sys.exit(0)

    state = json.loads(state_path.read_text(encoding="utf-8"))
    commit = state.get("last_completed_commit")
    if not commit:
        sys.exit(0)

    agent = get_agent_from_spec(commit) or state.get("next_commit_assignee", "unknown")

    script = REPO_ROOT / "hooks" / "verify_constraints.py"
    result = subprocess.run(
        [sys.executable, str(script), "--commit", str(commit), "--agent", agent],
        cwd=REPO_ROOT
    )
    # Only block on hard failures (exit 2), not warnings (exit 1)
    sys.exit(0 if result.returncode <= 1 else 2)


if __name__ == "__main__":
    main()
