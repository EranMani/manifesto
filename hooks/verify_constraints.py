#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_constraints.py - Post-commit constraint verifier.

Checks three things after a commit lands:
  1. Context block existed in the commit spec (enforced upfront)
  2. No forbidden-path files were touched in the commit (git diff check)
  3. Agent self-reported tool usage is within phase budgets (worklog check)

Usage:
  python hooks/verify_constraints.py --commit 08 --agent rex
  python hooks/verify_constraints.py --commit 08 --agent rex --tokens 45000

Exits 0 if all checks pass, 1 if any fail.
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

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

# ----------------------------------------------
# Helpers
# ----------------------------------------------

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


def git_files_changed(commit_ref: str = "HEAD") -> list:
    result = subprocess.run(
        ["git", "diff-tree", "--no-commit-id", "-r", "--name-only", commit_ref],
        capture_output=True, text=True, cwd=REPO_ROOT
    )
    return [f.strip() for f in result.stdout.splitlines() if f.strip()]


# ----------------------------------------------
# Check 1 - Context block present in spec
# ----------------------------------------------

def check_context_block(spec_text: str, commit_num: str):
    if "## context" in spec_text:
        has_tier0     = "tier0:" in spec_text
        has_forbidden = "forbidden:" in spec_text
        has_estimate  = "estimated_reads:" in spec_text
        if has_tier0 and has_forbidden and has_estimate:
            return True, "context block present (tier0, forbidden, estimated_reads all found)"
        missing = []
        if not has_tier0:     missing.append("tier0")
        if not has_forbidden: missing.append("forbidden")
        if not has_estimate:  missing.append("estimated_reads")
        return False, f"context block incomplete - missing: {', '.join(missing)}"
    return False, f"no context block in commit-{commit_num}.md - agent had no upfront file list"


# ----------------------------------------------
# Check 2 - No forbidden paths touched
# ----------------------------------------------

def extract_forbidden_paths(spec_text: str) -> list:
    forbidden = []
    in_forbidden = False
    for line in spec_text.splitlines():
        if line.strip().startswith("forbidden:"):
            in_forbidden = True
            continue
        if in_forbidden:
            if re.match(r"^\s{0,2}\w+:", line) or line.strip() == "```":
                break
            match = re.match(r"\s+-\s+([\w./]+)", line)
            if match:
                forbidden.append(match.group(1).rstrip("/"))
    return forbidden


def check_forbidden_paths(spec_text: str, changed_files: list):
    forbidden = extract_forbidden_paths(spec_text)
    if not forbidden:
        return True, "WARN: no forbidden paths defined in spec (skipped)"

    violations = []
    for changed in changed_files:
        for fp in forbidden:
            if changed.startswith(fp):
                violations.append(f"{changed} (forbidden prefix: {fp})")

    if violations:
        return False, "forbidden path violations: " + "; ".join(violations)
    return True, f"no forbidden paths touched (checked: {', '.join(forbidden)})"


# ----------------------------------------------
# Check 3 - Phase budget from worklog
# ----------------------------------------------

def check_phase_budget(worklog_text: str, commit_num: str):
    if not worklog_text:
        return True, None, "WARN: no worklog found - cannot verify phase budget"

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
        return True, None, "WARN: no 'Tool usage: reads=N, writes=N, total=N' line found in worklog"

    reads, writes, total = int(match.group(1)), int(match.group(2)), int(match.group(3))
    counts = {"reads": reads, "writes": writes, "total": total}
    failures = []
    if reads  > PHASE_BUDGETS["reads"]:  failures.append(f"reads={reads} exceeds cap of {PHASE_BUDGETS['reads']}")
    if writes > PHASE_BUDGETS["writes"]: failures.append(f"writes={writes} exceeds cap of {PHASE_BUDGETS['writes']}")
    if total  > PHASE_BUDGETS["total"]:  failures.append(f"total={total} exceeds cap of {PHASE_BUDGETS['total']}")

    if failures:
        return False, counts, f"phase budget exceeded: {'; '.join(failures)}"
    return True, counts, f"budget ok: reads={reads}/{PHASE_BUDGETS['reads']}, writes={writes}/{PHASE_BUDGETS['writes']}, total={total}/{PHASE_BUDGETS['total']}"


# ----------------------------------------------
# Main
# ----------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Verify agent constraints for a commit.")
    parser.add_argument("--commit",  required=True, help="Commit number, e.g. 08")
    parser.add_argument("--agent",   required=True, help="Agent name, e.g. rex, aria, adam")
    parser.add_argument("--tokens",  type=int, default=None, help="Token count for this commit (optional)")
    parser.add_argument("--ref",     default="HEAD", help="Git ref to check (default: HEAD)")
    parser.add_argument("--json",    action="store_true", help="Output as JSON")
    args = parser.parse_args()

    spec_text    = load_spec(args.commit)
    worklog_text = load_worklog(args.agent)
    changed      = git_files_changed(args.ref)

    ok1, msg1         = check_context_block(spec_text, args.commit)
    ok2, msg2         = check_forbidden_paths(spec_text, changed)
    ok3, counts3, msg3 = check_phase_budget(worklog_text, args.commit)

    results = {
        "context_block":   {"pass": ok1, "message": msg1},
        "forbidden_paths": {"pass": ok2, "message": msg2},
        "phase_budget":    {"pass": ok3, "message": msg3, "counts": counts3},
    }

    all_pass = all(r["pass"] for r in results.values())

    if args.json:
        print(json.dumps({
            "commit": args.commit, "agent": args.agent,
            "tokens": args.tokens, "all_pass": all_pass, "checks": results
        }, indent=2))
    else:
        status = lambda ok, msg: ("PASS" if ok else ("WARN" if msg.startswith("WARN") else "FAIL"))
        print(f"\n-- Constraint Verification: C{args.commit.zfill(2)} ({args.agent}) --\n")
        print(f"  [1] Context block    [{status(ok1, msg1)}] {msg1}")
        print(f"  [2] Forbidden paths  [{status(ok2, msg2)}] {msg2}")
        print(f"  [3] Phase budget     [{status(ok3, msg3)}] {msg3}")
        if args.tokens:
            print(f"  [4] Tokens used      {args.tokens:,}")
        print()
        print(f"  RESULT: {'ALL CHECKS PASSED' if all_pass else 'FAILED - ' + ', '.join(k for k,v in results.items() if not v['pass'])}")
        print()

    append_to_log(args.commit, args.agent, results, all_pass, args.tokens)
    embed_into_dashboard(args.commit, args.agent, results, all_pass, args.tokens)
    sys.exit(0 if all_pass else 1)


# ----------------------------------------------
# Log writer
# ----------------------------------------------

def append_to_log(commit_num: str, agent: str, results: dict, all_pass: bool, tokens: int = None):
    log_path = REPO_ROOT / "CONSTRAINT_LOG.md"

    if not log_path.exists():
        log_path.write_text(
            "# Constraint Log\n\n"
            "Automatically updated by `hooks/verify_constraints.py` after each commit.\n"
            "View the live dashboard: open `constraint-dashboard.html` in your browser.\n\n"
            "| Date | Commit | Agent | Tokens | Context | Forbidden | Budget | Result |\n"
            "|------|--------|-------|--------|---------|-----------|--------|--------|\n",
            encoding="utf-8"
        )

    def icon(key):
        r = results[key]
        if r["pass"]: return "PASS"
        if r["message"].startswith("WARN"): return "WARN"
        return "FAIL"

    date      = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    tokens_str = f"{tokens:,}" if tokens else "-"
    context   = icon("context_block")
    forbidden = icon("forbidden_paths")
    budget    = icon("phase_budget")
    counts    = results["phase_budget"].get("counts")
    budget_detail = f" r={counts['reads']} w={counts['writes']} t={counts['total']}" if counts else ""
    result    = "PASS" if all_pass else "FAIL"

    row = f"| {date} | C{commit_num.zfill(2)} | {agent} | {tokens_str} | {context} | {forbidden} | {budget}{budget_detail} | {result} |\n"

    with open(log_path, "a", encoding="utf-8") as f:
        f.write(row)


# ----------------------------------------------
# Dashboard embedder (no server needed)
# ----------------------------------------------

def embed_into_dashboard(commit_num: str, agent: str, results: dict, all_pass: bool, tokens: int = None):
    """Read all rows from CONSTRAINT_LOG.md and inject as JS data into the HTML dashboard."""
    dashboard_path = REPO_ROOT / "constraint-dashboard.html"
    log_path       = REPO_ROOT / "CONSTRAINT_LOG.md"

    if not dashboard_path.exists() or not log_path.exists():
        return

    # Parse log into row dicts
    rows = []
    for line in log_path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"): continue
        cells = [c.strip() for c in line.split("|") if c.strip()]
        # skip header and separator rows
        if not cells or cells[0] in ("Date", "---", "----"):
            continue
        if len(cells) >= 8:
            rows.append({
                "date":      cells[0],
                "commit":    cells[1],
                "agent":     cells[2],
                "tokens":    cells[3],
                "context":   cells[4],
                "forbidden": cells[5],
                "budget":    cells[6],
                "result":    cells[7],
            })

    js_data = json.dumps(rows, indent=2)

    html = dashboard_path.read_text(encoding="utf-8")

    # Replace the embedded data block
    marker_start = "/* CONSTRAINT_DATA_START */"
    marker_end   = "/* CONSTRAINT_DATA_END */"
    new_block    = f"{marker_start}\nconst EMBEDDED_DATA = {js_data};\n{marker_end}"

    if marker_start in html:
        html = re.sub(
            re.escape(marker_start) + r".*?" + re.escape(marker_end),
            new_block, html, flags=re.DOTALL
        )
    else:
        # First time: insert before closing </script>
        html = html.replace("loadLog();", f"{new_block}\nloadLog();")

    dashboard_path.write_text(html, encoding="utf-8")


if __name__ == "__main__":
    main()
