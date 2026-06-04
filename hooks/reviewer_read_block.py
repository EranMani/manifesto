#!/usr/bin/env python3
"""
reviewer_read_block.py — hard block on Read/Glob/Grep calls from reviewer agents.

Registered as PreToolUse hook on Read, Glob, and Grep tools.

Reviewers (viktor, sage, quinn, mira, ryan) receive all necessary context
inline in their invocation prompt. They have no legitimate reason to make
file-system reads. Allowing reads lets them silently bypass the context
package discipline and run up token costs by reading the entire codebase.

Exception: ryan may Read LEARNING_LOG.md and LEARNING_LOG_SUMMARY.md only.
Both files are Ryan's documentation domain; Edit requires a prior Read of the
target file, and Ryan appends entries to both files each commit.

Agent identity is read from hooks/tool_cap.json (set by tool_cap_start.py).
If no agent session is active (active=false), allow through — the orchestrator
reads files freely.

Fail-open: any I/O or parse error → exit 0. Never block due to hook internals.
"""

import json
import subprocess
import sys
from pathlib import Path

# Agents whose Read/Glob/Grep calls are blocked.
# All context must arrive via the orchestrator's invocation prompt.
_BLOCKED_AGENTS = {"viktor", "sage", "quinn", "mira", "ryan"}

# Ryan may read these files only (Edit requires a prior Read of the target file).
_RYAN_ALLOWED_FILES = {"LEARNING_LOG.md", "LEARNING_LOG_SUMMARY.md"}


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
        return 0  # orchestrator context — allow all reads

    agent = (cap.get("agent") or "").lower()
    if agent not in _BLOCKED_AGENTS:
        return 0  # implementor — reads allowed

    stdin_data = read_stdin()
    tool_name = stdin_data.get("tool_name", "")

    # Ryan exception: allow Read of LEARNING_LOG.md and LEARNING_LOG_SUMMARY.md.
    # Edit requires a prior Read; Ryan appends entries to both files each commit.
    if agent == "ryan" and tool_name == "Read":
        file_path = stdin_data.get("tool_input", {}).get("file_path", "")
        if Path(file_path).name in _RYAN_ALLOWED_FILES:
            return 0

    sys.stderr.write(
        f"\n\033[31m\U0001f6ab READ BLOCKED\033[0m\n"
        f"  Agent  : {agent}\n"
        f"  Tool   : {tool_name}\n"
        f"  Reason : Reviewer agents cannot make file-system reads.\n"
        f"           All context is provided in your invocation prompt.\n"
        f"           If you need information not in the prompt, note the gap\n"
        f"           in your findings and continue without reading.\n\n"
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
