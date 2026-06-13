#!/usr/bin/env python3
"""
bash_command_lint.py — PreToolUse hook on Bash.

Deterministically rejects two token-wasting command patterns documented in
OI-13 / OI-14 / DECISIONS.md D38:

1. Any `cd` as a command (including inside subshells like `(cd path && ...)`).
   `cd` silently shifts the persistent CWD for every later Bash call in the
   session, breaking repo-relative paths (e.g. `python hooks/...`).

2. `2>/dev/null` immediately followed by `&&` or `;`. This hides stderr but
   not the exit code, so a missing-but-harmless path makes the whole chain
   report a false "Error: Exit code N" even when earlier commands succeeded.

Exit 2 = hard block (message on stderr is surfaced to Claude). Exit 0 = allow.
Fails open (exit 0) on any input it cannot parse.
"""

import json
import re
import sys


_CD_SPLIT_RE = re.compile(r"&&|\|\||[;&|()]")
# `2>/dev/null &&` always propagates a hidden-stderr exit code into a
# short-circuiting chain. `2>/dev/null;` only propagates if the next command
# isn't `true` — `; true` is the documented neutralization, so allow it.
_EXIT_CODE_AND_CHAIN_RE = re.compile(r"2>\s*/dev/null\s*&&")
_EXIT_CODE_SEMI_CHAIN_RE = re.compile(r"2>\s*/dev/null\s*;(?!\s*true\b)")


def contains_cd_command(command: str) -> bool:
    for segment in _CD_SPLIT_RE.split(command):
        words = segment.split()
        if words and words[0] == "cd":
            return True
    return False


def contains_exit_code_propagating_chain(command: str) -> bool:
    return bool(
        _EXIT_CODE_AND_CHAIN_RE.search(command) or _EXIT_CODE_SEMI_CHAIN_RE.search(command)
    )


def main() -> int:
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except Exception:
        return 0  # fail open on parse error

    command = data.get("tool_input", {}).get("command", "") or data.get("command", "")
    if not command:
        return 0

    if contains_cd_command(command):
        sys.stderr.write(
            "\n\033[31m🚫 BASH COMMAND BLOCKED\033[0m\n"
            f"  Command : {command[:160]}\n"
            "  Reason  : `cd` silently shifts the persistent working directory\n"
            "            for every later Bash call (OI-13/OI-14, DECISIONS.md D38).\n"
            "  Action  : Write the command relative to the repo root instead, e.g.\n"
            "            python -m pytest hooks/tests/ -q   (not: cd hooks && pytest tests/ -q)\n"
        )
        return 2

    if contains_exit_code_propagating_chain(command):
        sys.stderr.write(
            "\n\033[31m🚫 BASH COMMAND BLOCKED\033[0m\n"
            f"  Command : {command[:160]}\n"
            "  Reason  : `2>/dev/null` followed by `&&`/`;` hides stderr but not the\n"
            "            exit code, so a missing-but-harmless path reports a false\n"
            "            'Error: Exit code N' (OI-13/OI-14, DECISIONS.md D38).\n"
            "  Action  : Use the Glob tool for existence checks, or neutralize the\n"
            "            exit code: ls .context/finalize 2>/dev/null; true\n"
        )
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
