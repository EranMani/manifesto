#!/usr/bin/env python3
"""
verify_constraints.py — Post-commit constraint verifier.

Checks three things after a commit lands:
  1. Context block existed in the commit spec (enforced upfront)
  2. No forbidden-path files were touched in the commit (git diff check)
  3. Agent self-reported tool usage is within phase budgets (worklog check)

Usage:
  python hooks/verify_constraints.py --commit 08 --agent rex
  python hooks/verify_constraints.py --commit 17 --agent aria

Exits 0 if all checks pass, 1 if any fail.
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
SPECS_DIR = REPO_ROOT / "commit-specs"
AGENTS_DIR = REPO_ROOT / ".claude" / "agents"
LOGS_DIR = AGENTS_DIR / "logs"

PHASE_BUDGETS = {
    "reads":   10,
    "writes":  12,
    "reserve": 3,
    "total":   25,
}

# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def load_spec(commit_num: str) -> str:
    padded = commit_num.zfill(2)
    path = SPECS_DIR / f"commit-{padded}.md"
    if not path.exists():
        sys.exit(f"ERROR: spec not found at {path}")
    return path.read_text(encoding="utf-8")


def load_worklog(agent: str) -> str:
    path = LOGS_DIR / f"{agent}-worklog.md"
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def git_files_changed(commit_ref: str = "HEAD") -> list[str]:
    """Return list of files changed in the given commit."""
    result = subprocess.run(
        ["git", "diff-tree", "--no-commit-id", "-r", "--name-only", commit_ref],
        capture_output=True, text=True, cwd=REPO_ROOT
    )
    return [f.strip() for f in result.stdout.splitlines() if f.strip()]


# ──────────────────────────────────────────────
# Check 1 — Context block present in spec
# ──────────────────────────────────────────────

def check_context_block(spec_text: str, commit_num: str) -> tuple[bool, str]:
    if "## context" in spec_text:
        # Also verify it has the key sub-fields
        has_tier0   = "tier0:" in spec_text
        has_forbidden = "forbidden:" in spec_text
        has_estimate  = "estimated_reads:" in spec_text
        if has_tier0 and has_forbidden and has_estimate:
            return True, "✅ context block present (tier0, forbidden, estimated_reads all found)"
        missing = []
        if not has_tier0:    missing.append("tier0")
        if not has_forbidden: missing.append("forbidden")
        if not has_estimate:  missing.append("estimated_reads")
        return False, f"❌ context block incomplete — missing: {', '.join(missing)}"
    return False, f"❌ no context block in commit-{commit_num}.md — agent had no upfront file list"


# ──────────────────────────────────────────────
# Check 2 — No forbidden paths touched
# ──────────────────────────────────────────────

def extract_forbidden_paths(spec_text: str) -> list[str]:
    """Parse the forbidden: block from the context section."""
    forbidden = []
    in_forbidden = False
    for line in spec_text.splitlines():
        if line.strip().startswith("forbidden:"):
            in_forbidden = True
            continue
        if in_forbidden:
            # stop at next yaml key or end of code block
            if re.match(r"^\s{0,2}\w+:", line) or line.strip() == "```":
                break
            # extract path — strip leading dashes, spaces, comments
            match = re.match(r"\s+-\s+([\w./]+)", line)
            if match:
                forbidden.append(match.group(1).rstrip("/"))
    return forbidden


def check_forbidden_paths(spec_text: str, changed_files: list[str]) -> tuple[bool, str]:
    forbidden = extract_forbidden_paths(spec_text)
    if not forbidden:
        return True, "⚠️  no forbidden paths defined in spec (skipped)"

    violations = []
    for changed in changed_files:
        for fp in forbidden:
            if changed.startswith(fp):
                violations.append(f"  {changed}  (forbidden prefix: {fp})")

    if violations:
        return False, "❌ forbidden path violations:\n" + "\n".join(violations)
    return True, f"✅ no forbidden paths touched  (checked against: {', '.join(forbidden)})"


# ──────────────────────────────────────────────
# Check 3 — Phase budget from worklog
# ──────────────────────────────────────────────

def check_phase_budget(worklog_text: str, commit_num: str) -> tuple[bool, str]:
    """
    Look for a tool-use report in the worklog for this commit.
    Agents are expected to self-report in the format:
      Tool usage: reads=N, writes=N, total=N
    If no report is found, return a warning (not a failure).
    """
    if not worklog_text:
        return True, "⚠️  no worklog found — cannot verify phase budget"

    # Search for the commit section then the tool usage line
    commit_section = re.search(
        rf"(?:Commit {int(commit_num)}|C{int(commit_num):02d}|C{commit_num}).*?(?=\n## |\Z)",
        worklog_text, re.DOTALL | re.IGNORECASE
    )
    section = commit_section.group(0) if commit_section else worklog_text

    match = re.search(
        r"[Tt]ool usage[:\s]+reads?\s*=\s*(\d+)[,\s]+writes?\s*=\s*(\d+)[,\s]+total\s*=\s*(\d+)",
        section
    )
    if not match:
        return True, "⚠️  no 'Tool usage: reads=N, writes=N, total=N' line found in worklog — agent didn't self-report"

    reads, writes, total = int(match.group(1)), int(match.group(2)), int(match.group(3))
    failures = []
    if reads > PHASE_BUDGETS["reads"]:
        failures.append(f"reads={reads} exceeds cap of {PHASE_BUDGETS['reads']}")
    if writes > PHASE_BUDGETS["writes"]:
        failures.append(f"writes={writes} exceeds cap of {PHASE_BUDGETS['writes']}")
    if total > PHASE_BUDGETS["total"]:
        failures.append(f"total={total} exceeds cap of {PHASE_BUDGETS['total']}")

    if failures:
        return False, f"❌ phase budget exceeded: {'; '.join(failures)}  (reported: reads={reads}, writes={writes}, total={total})"
    return True, f"✅ phase budget respected  (reads={reads}/{PHASE_BUDGETS['reads']}, writes={writes}/{PHASE_BUDGETS['writes']}, total={total}/{PHASE_BUDGETS['total']})"


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Verify agent constraints for a commit.")
    parser.add_argument("--commit", required=True, help="Commit number, e.g. 08")
    parser.add_argument("--agent", required=True, help="Agent name, e.g. rex, aria, adam")
    parser.add_argument("--ref", default="HEAD", help="Git ref to check (default: HEAD)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    spec_text    = load_spec(args.commit)
    worklog_text = load_worklog(args.agent)
    changed      = git_files_changed(args.ref)

    results = {}

    ok1, msg1 = check_context_block(spec_text, args.commit)
    ok2, msg2 = check_forbidden_paths(spec_text, changed)
    ok3, msg3 = check_phase_budget(worklog_text, args.commit)

    results["context_block"]   = {"pass": ok1, "message": msg1}
    results["forbidden_paths"] = {"pass": ok2, "message": msg2}
    results["phase_budget"]    = {"pass": ok3, "message": msg3}

    all_pass = all(r["pass"] for r in results.values())

    if args.json:
        print(json.dumps({"commit": args.commit, "agent": args.agent, "all_pass": all_pass, "checks": results}, indent=2))
    else:
        print(f"\n── Constraint Verification: C{args.commit.zfill(2)} ({args.agent}) ──\n")
        print(f"  [1] Context block    {msg1}")
        print(f"  [2] Forbidden paths  {msg2}")
        print(f"  [3] Phase budget     {msg3}")
        print()
        if all_pass:
            print("  RESULT: ALL CHECKS PASSED ✅")
        else:
            failed = [k for k, v in results.items() if not v["pass"]]
            print(f"  RESULT: FAILED — {', '.join(failed)} ❌")
        print()

    append_to_log(args.commit, args.agent, results, all_pass)
    sys.exit(0 if all_pass else 1)


# ──────────────────────────────────────────────
# Log writer
# ──────────────────────────────────────────────

def append_to_log(commit_num: str, agent: str, results: dict, all_pass: bool):
    """Append one row to CONSTRAINT_LOG.md."""
    log_path = REPO_ROOT / "CONSTRAINT_LOG.md"

    # Create file with header if it doesn't exist
    if not log_path.exists():
        log_path.write_text(
            "# Constraint Log\n\n"
            "| Date | Commit | Agent | Context | Forbidden | Budget | Result |\n"
            "|------|--------|-------|---------|-----------|--------|--------|\n",
            encoding="utf-8"
        )

    def icon(check_key):
        r = results[check_key]
        if r["pass"]:
            return "✅"
        msg = r["message"]
        if msg.startswith("⚠️"):
            return "⚠️"
        return "❌"

    date     = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    context  = icon("context_block")
    forbidden = icon("forbidden_paths")
    budget   = icon("phase_budget")
    result   = "PASS ✅" if all_pass else "FAIL ❌"

    # Extract budget numbers if available
    budget_detail = ""
    bm = re.search(r"reads=(\d+)/\d+.*?writes=(\d+)/\d+.*?total=(\d+)/\d+", results["phase_budget"]["message"])
    if bm:
        budget_detail = f" r={bm.group(1)} w={bm.group(2)} t={bm.group(3)}"

    row = f"| {date} | C{commit_num.zfill(2)} | {agent} | {context} | {forbidden} | {budget}{budget_detail} | {result} |\n"

    with open(log_path, "a", encoding="utf-8") as f:
        f.write(row)


if __name__ == "__main__":
    main()
