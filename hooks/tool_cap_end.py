#!/usr/bin/env python3
"""
tool_cap_end.py — PostToolUse hook on Agent tool.

Fires automatically after every Agent() invocation completes (success or error).
Resets tool_cap.json to active=false and clears the counter.
"""

import json
import subprocess
import sys
from pathlib import Path


def git_root() -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True, text=True
    )
    return Path(result.stdout.strip())


def main() -> int:
    try:
        cap_file = git_root() / "hooks" / "tool_cap.json"
    except Exception:
        return 0

    cap = {
        "active": False,
        "agent": None,
        "count": 0,
        "limit": 25,
    }

    try:
        cap_file.write_text(json.dumps(cap, indent=2), encoding="utf-8")
    except Exception:
        pass  # fail open

    return 0


if __name__ == "__main__":
    sys.exit(main())
