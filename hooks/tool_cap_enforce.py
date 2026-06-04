#!/usr/bin/env python3
"""
tool_cap_enforce.py — hard tool-use cap for subagent invocations.

Registered as PreToolUse hook on all tools ("*" matcher).
Counts tool calls while hooks/tool_cap.json has active=true.
Blocks the agent at the configured limit with exit code 2.

Orchestrator protocol (MUST follow):
  Before Agent():  Write tool_cap.json → {"active": true,  "agent": "<name>", "count": 0, "limit": 25}
  After  Agent():  Write tool_cap.json → {"active": false, "agent": null,    "count": 0, "limit": 25}

Excluded from counting (always allowed through):
  - Write calls targeting tool_cap.json itself  (orchestrator marker writes)
  - Agent tool calls                             (spawning is orchestrator action, not agent tool use)

Fail-open: any I/O or parse error → exit 0 (allow). Never block due to hook internals.
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


def read_stdin() -> dict:
    try:
        raw = sys.stdin.read()
        return json.loads(raw) if raw.strip() else {}
    except Exception:
        return {}


def main() -> int:
    try:
        cap_file = git_root() / "hooks" / "tool_cap.json"
    except Exception:
        return 0

    if not cap_file.exists():
        return 0

    try:
        cap = json.loads(cap_file.read_text(encoding="utf-8"))
    except Exception:
        return 0

    if not cap.get("active", False):
        return 0

    stdin_data = read_stdin()
    tool_name = stdin_data.get("tool_name", "")
    tool_input = stdin_data.get("tool_input", {})

    # Always allow: any access to tool_cap.json itself (orchestrator file management)
    # Covers Write (reset), Read (read-before-write safety check), Edit (partial update)
    for key in ("file_path", "path"):
        if "tool_cap.json" in str(tool_input.get(key, "")):
            return 0

    # Always allow: orchestrator spawning subagents (not a subagent tool use)
    if tool_name == "Agent":
        return 0

    count = cap.get("count", 0) + 1
    limit = cap.get("limit", 25)
    agent = cap.get("agent") or "unknown"

    cap["count"] = count
    try:
        cap_file.write_text(json.dumps(cap, indent=2), encoding="utf-8")
    except Exception:
        return 0  # fail open — never block due to I/O error

    if count > limit:
        sys.stderr.write(
            f"\n[31m\U0001f6ab TOOL CAP REACHED[0m\n"
            f"  Agent : {agent}\n"
            f"  Used  : {limit}/{limit} tools (this is call #{count})\n"
            f"  Action: STOP. Do not call any more tools.\n"
            f"          Report what you completed, what files changed, and what remains.\n\n"
        )
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
