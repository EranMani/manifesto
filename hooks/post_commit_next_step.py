#!/usr/bin/env python3
"""
post_commit_next_step.py — Universal Agentic Workflow post-commit automation.

Runs after every successful `git commit`. Does three things:
  1. Marks the committed step as done in commit-protocol.md (status column)
  2. Updates project-state.json with the new state
  3. Prints the next pending commit step with its assignee

This script is what keeps project-state.json accurate without manual updates.
"""

import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

# Ensure stdout/stderr use UTF-8 on Windows.
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

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


RUNTIME_FLAG = ROOT / ".context" / "runtime" / "last_protocol_commit.flag"


def main() -> int:
    today = date.today().isoformat()
    last_message = get_last_commit_message()
    commit_number = extract_commit_number_from_message(last_message)

    # No commit step marker (e.g. a `chore(state)` sweep) — nothing to advance.
    if not commit_number:
        return 0

    if not PROTOCOL_FILE.exists():
        return 0

    # ── Step 1: Update commit-protocol.md ────────────────────────────────────
    protocol_text = PROTOCOL_FILE.read_text(encoding="utf-8")
    updated_protocol = update_protocol_status(protocol_text, commit_number, today)
    if updated_protocol == protocol_text:
        # commit_number present but no matching pending row — nothing advanced.
        return 0

    PROTOCOL_FILE.write_text(updated_protocol, encoding="utf-8")
    print(f">> commit-protocol.md: Commit {commit_number} marked done - {today}")

    # Auto-stage governance artifacts written by finalize_commit.py so the
    # chore(state) sweep cannot miss them.
    _GOVERNANCE_ARTIFACTS = [
        "CONSTRAINT_LOG.md",
        "CONTEXT_METRICS.json",
        "constraint-dashboard.html",
    ]
    finalize_marker = ROOT / ".context" / "finalize" / f"C{commit_number}.json"
    to_stage = [f for f in _GOVERNANCE_ARTIFACTS if (ROOT / f).exists()]
    if finalize_marker.exists():
        to_stage.append(str(finalize_marker.relative_to(ROOT)))
    if to_stage:
        subprocess.run(["git", "add"] + to_stage, cwd=ROOT)

    # Consume-once signal for generate_domain_map.py: only regenerate domain
    # maps after a real protocol step advances.
    RUNTIME_FLAG.parent.mkdir(parents=True, exist_ok=True)
    RUNTIME_FLAG.write_text(commit_number, encoding="utf-8")

    commits = parse_commit_index(updated_protocol)

    # ── Step 2: Derive next pending from protocol (read-only — no state file write) ──
    # project-state.json is maintained by Claude (the orchestrator) with full quality
    # gate results, decision logs, and handoff history. The hook does not touch it.
    done_in_protocol = {c["number"] for c in commits if "done" in c["status"]}
    next_commit = find_next_pending(commits, done_in_protocol)

    # ── Step 3: Print next step ───────────────────────────────────────────────
    print()
    committed = next((c for c in commits if c["number"] == commit_number), None)
    if committed:
        print(f"[OK] Commit {commit_number} `{committed['name']}` complete. "
              f"Assignee: {committed['assignee'].title()}")
    else:
        print(f"[OK] Commit {commit_number} complete.")

    if next_commit:
        print()
        print(f"--------------------------------------------------------------")
        print(f"  NEXT: Commit {next_commit['number']} - `{next_commit['name']}`")
        print(f"  Assignee: {next_commit['assignee'].title()}")
        print(f"  Run /next-step to proceed or /status for a full project overview.")
        print(f"--------------------------------------------------------------")
    else:
        print()
        print("[DONE] All commits in commit-protocol.md are complete!")
        print("   Run /status to confirm and review the final project state.")

    # ── Context hygiene reminder ──────────────────────────────────────────────
    print()
    print("=============================================================")
    print("  TYPE /clear NOW -- all state is saved in project files.")
    print("  Start the next commit in a fresh context window.")
    print("  Mid-commit if session grows heavy: type /compact instead.")
    print("=============================================================")

    return 0


if __name__ == "__main__":
    sys.exit(main())
