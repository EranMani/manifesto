#!/usr/bin/env python3
"""
block_agent_commit.py — PreToolUse hook on Bash.

Intercepts any bash command containing 'git commit' or 'git push'.
Blocks agents from committing without Eran's explicit approval.

To commit as Eran (bypasses this hook):
    $env:ERAN_COMMIT="1"; git commit -m "..."  # PowerShell
    ERAN_COMMIT=1 git commit -m "..."          # bash/git-bash
    or set the env var in your shell: export ERAN_COMMIT=1

Agents never set ERAN_COMMIT, so they are always blocked.
Exit 2 = hard block. Exit 0 = allow through.
"""

import json
import os
import sys


def main() -> int:
    # If Eran is committing manually, allow through
    if os.environ.get("ERAN_COMMIT") == "1":
        return 0

    # If Claude is committing on Eran's behalf after explicit approval, allow through
    if os.environ.get("CLAUDE_COMMIT") == "1":
        return 0

    # Read the tool input from stdin
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except Exception:
        return 0  # fail open on parse error

    command = data.get("tool_input", {}).get("command", "") or data.get("command", "")

    # Block git commit and git push
    dangerous = ["git commit", "git push", "git merge", "git rebase"]
    for pattern in dangerous:
        if pattern in command:
            sys.stderr.write(
                f"\n\033[31m🚫 COMMIT BLOCKED\033[0m\n"
                f"  Command : {command[:120]}\n"
                f"  Reason  : Agents cannot commit without Eran's explicit approval.\n"
                f"  Action  : Present your diff summary and WAIT for Eran to approve.\n"
                f"            Eran commits manually with: ERAN_COMMIT=1 git commit -m '...'\n\n"
            )
            return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
