#!/usr/bin/env python3
"""
post_commit_next_step.py — Universal Agentic Workflow post-commit automation.

Runs after every successful `git commit`. Does three things:
  1. Marks the committed step as done in commit-protocol.md (status column)
  2. Updates project-state.json with the new state
  3. Prints the next pending commit step with its assignee

This script is what keeps project-state.json accurate without manual updates.
"""

import io
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

# Ensure stdout/stderr use UTF-8 on Windows (emoji in print statements).
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "buffer"):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ── Paths ────────────────────────────────────────────────────────────────────
ROOT = Path(subprocess.check_output(
    ["git", "rev-parse", "--show-toplevel"], text=True
).strip())
STATE_FILE = ROOT / "project-state.json"
PROTOCOL_FILE = ROOT / "commit-protocol.md"


def get_last_commit_message() -> str:
    """Return the message of the most recent commit."""
    result = subprocess.run(
        ["git", "log", "-1", "--pretty=%B"],
        capture_output=True, text=True
    )
    return result.stdout.strip()


def extract_commit_number_from_message(message: str) -> str | None:
    """
    Try to find a commit step number in the message.
    Requires an explicit marker on its own line: "Commit #NN" or "Step #NN".
    Bare "#NN" anywhere in the body is intentionally NOT matched — too ambiguous.
    Returns zero-padded two-digit string, or None.
    """
    # Only match "Commit #NN" or "Step #NN" as a dedicated line/phrase
    patterns = [
        r"(?:^|\n)\s*[Cc]ommit\s+#0*(\d{1,2})\b",
        r"(?:^|\n)\s*[Ss]tep\s+#0*(\d{1,2})\b",
    ]
    for pat in patterns:
        m = re.search(pat, message, re.IGNORECASE)
        if m:
            return m.group(1).zfill(2)
    return None


def parse_commit_index(protocol_text: str) -> list[dict]:
    """
    Parse the commit index table from commit-protocol.md.
    Returns list of dicts: {number, name, assignee, status}
    """
    commits = []
    # Match table rows like: | 01 | name | Assignee | status |
    row_pattern = re.compile(
        r"\|\s*(\d{1,2})\s*\|\s*`?([^|`]+?)`?\s*\|\s*([\w][\w\s\+\-]*?)\s*\|\s*([^|]+?)\s*\|"
    )
    for line in protocol_text.splitlines():
        m = row_pattern.match(line.strip())
        if m:
            commits.append({
                "number": m.group(1).zfill(2),
                "name": m.group(2).strip(),
                "assignee": m.group(3).strip().lower(),
                "status": m.group(4).strip().lower(),
            })
    return commits


def update_protocol_status(protocol_text: str, commit_number: str, today: str) -> str:
    """
    Replace the status cell for a given commit number from 'pending' to
    '✅ done · [date]' in the commit index table.
    Returns the updated protocol text.
    """
    # Match a table row starting with the commit number
    pattern = re.compile(
        r"(\|\s*0*" + str(int(commit_number)) + r"\s*\|[^|]+\|[^|]+\|)\s*pending\s*(\|)",
        re.IGNORECASE
    )
    replacement = rf"\1 ✅ done · {today} \2"
    updated = pattern.sub(replacement, protocol_text)
    return updated


def load_or_init_state() -> dict:
    """Load project-state.json or return a minimal default structure."""
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass

    return {
        "project": "unknown",
        "last_updated": "",
        "current_commit": {"number": "01", "name": "unknown", "status": "pending", "assignee": "unknown"},
        "commits_done": [],
        "commits_pending": [],
        "open_handoffs": [],
        "blockers": [],
        "quality_gate_results": {},
        "parallel_groups_available": [],
        "session_token_usage": {"total_this_session": 0, "by_agent": {}},
    }


def find_next_pending(commits: list[dict], done_set: set[str]) -> dict | None:
    """Return the first commit in the index that is not yet done."""
    for c in commits:
        if c["number"] not in done_set and "done" not in c["status"]:
            return c
    return None


def main() -> int:
    today = date.today().isoformat()
    last_message = get_last_commit_message()
    commit_number = extract_commit_number_from_message(last_message)

    # ── Step 1: Update commit-protocol.md ────────────────────────────────────
    if PROTOCOL_FILE.exists():
        protocol_text = PROTOCOL_FILE.read_text(encoding="utf-8")
        commits = parse_commit_index(protocol_text)

        if commit_number:
            updated_protocol = update_protocol_status(protocol_text, commit_number, today)
            if updated_protocol != protocol_text:
                PROTOCOL_FILE.write_text(updated_protocol, encoding="utf-8")
                print(f"📋 commit-protocol.md: Commit {commit_number} marked ✅ done · {today}")
            else:
                print(f"⚠️  commit-protocol.md: Could not find 'pending' row for commit {commit_number}. Update manually.")
        else:
            print("⚠️  post_commit: Could not detect commit step number from message. commit-protocol.md not updated.")
            commits = parse_commit_index(protocol_text)
    else:
        print("⚠️  post_commit: commit-protocol.md not found. Skipping protocol update.")
        commits = []

    # ── Step 2: Derive next pending from protocol (read-only — no state file write) ──
    # project-state.json is maintained by Claude (the orchestrator) with full quality
    # gate results, decision logs, and handoff history. The hook does not touch it.
    done_in_protocol = {c["number"] for c in commits if "done" in c["status"]}
    next_commit = find_next_pending(commits, done_in_protocol)

    # ── Step 3: Print next step ───────────────────────────────────────────────
    print()
    if commit_number:
        committed = next((c for c in commits if c["number"] == commit_number), None)
        if committed:
            print(f"✅  Commit {commit_number} `{committed['name']}` complete. "
                  f"Assignee: {committed['assignee'].title()}")
        else:
            print(f"✅  Commit {commit_number} complete.")

    if next_commit:
        print()
        print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"  NEXT: Commit {next_commit['number']} — `{next_commit['name']}`")
        print(f"  Assignee: {next_commit['assignee'].title()}")
        print(f"  Run /next-step to proceed or /status for a full project overview.")
        print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    else:
        print()
        print("🎉 All commits in commit-protocol.md are complete!")
        print("   Run /status to confirm and review the final project state.")

    # ── Context hygiene reminder ──────────────────────────────────────────────
    print()
    print("┌─────────────────────────────────────────────────────────────┐")
    print("│  TYPE /clear NOW — all state is saved in project files.    │")
    print("│  Start the next commit in a fresh context window.          │")
    print("│  Mid-commit if session grows heavy: type /compact instead. │")
    print("└─────────────────────────────────────────────────────────────┘")

    return 0


if __name__ == "__main__":
    sys.exit(main())
