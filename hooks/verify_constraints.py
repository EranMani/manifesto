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


def git_files_changed(commit_ref: str = "HEAD", worktree: bool = False) -> list:
    if worktree:
        result = subprocess.run(
            ["git", "diff", "HEAD", "--name-only"],
            capture_output=True, text=True, cwd=REPO_ROOT
        )
    else:
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

    _num_match = re.match(r"(\d+)", commit_num)
    _base = int(_num_match.group(1)) if _num_match else None
    _int_alts = rf"Commit {_base}|C{_base:02d}|" if _base is not None else ""
    commit_section = re.search(
        rf"(?:{_int_alts}C{commit_num}).*?(?=\n## |\Z)",
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
    parser.add_argument("--ref",      default="HEAD", help="Git ref to check (default: HEAD)")
    parser.add_argument("--worktree", action="store_true", help="Check working-tree changes vs HEAD instead of a committed ref")
    parser.add_argument("--json",     action="store_true", help="Output as JSON")
    args = parser.parse_args()

    spec_text    = load_spec(args.commit)
    worklog_text = load_worklog(args.agent)
    changed      = git_files_changed(args.ref, worktree=args.worktree)

    ok1, msg1          = check_context_block(spec_text, args.commit)
    ok2, msg2          = check_forbidden_paths(spec_text, changed)
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

    tokens = args.tokens if args.tokens is not None else get_tokens_from_records(args.commit)
    append_to_log(args.commit, args.agent, results, all_pass, tokens)
    embed_into_dashboard()
    sys.exit(0 if all_pass else 1)


# ----------------------------------------------
# Token lookup from TOKEN_RECORDS.md
# ----------------------------------------------

def get_tokens_from_records(commit_num: str):
    path = REPO_ROOT / "TOKEN_RECORDS.md"
    if not path.exists(): return None
    padded = "C" + str(commit_num).zfill(2)
    best = None
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"): continue
        cells = [c.strip() for c in line.split("|") if c.strip()]
        if not cells or cells[0] != padded: continue
        for cell in cells[1:]:
            clean = cell.replace(",", "")
            if clean.isdigit():
                val = int(clean)
                if best is None or val > best:
                    best = val
                break
    return best


# ----------------------------------------------
# Log writer
# ----------------------------------------------

def append_to_log(commit_num: str, agent: str, results: dict, all_pass: bool, tokens=None):
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

    date         = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    tokens_str   = f"{tokens:,}" if tokens else "-"
    context      = icon("context_block")
    forbidden    = icon("forbidden_paths")
    budget       = icon("phase_budget")
    counts       = results["phase_budget"].get("counts")
    budget_detail = f" r={counts['reads']} w={counts['writes']} t={counts['total']}" if counts else ""
    result       = "PASS" if all_pass else "FAIL"
    commit_key   = "C" + commit_num.zfill(2)

    # Skip if already logged for this commit+agent
    for line in log_path.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.split("|") if c.strip()]
        if len(cells) >= 3 and cells[1] == commit_key and cells[2] == agent:
            return

    row = "| " + date + " | " + commit_key + " | " + agent + " | " + tokens_str + " | " + context + " | " + forbidden + " | " + budget + budget_detail + " | " + result + " |\n"
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(row)


# ----------------------------------------------
# Dashboard embedder
# ----------------------------------------------

def embed_into_dashboard():
    dashboard_path = REPO_ROOT / "constraint-dashboard.html"
    log_path       = REPO_ROOT / "CONSTRAINT_LOG.md"
    if not log_path.exists(): return

    TOOLTIPS = {
        "context":   {
            "PASS": "Context block present in spec — agent had an explicit file list before starting.",
            "FAIL": "No context block in spec — agent had to discover files speculatively.",
            "WARN": "Context block incomplete — missing tier0, forbidden, or estimated_reads.",
        },
        "forbidden": {
            "PASS": "No forbidden-path files touched — agent stayed within its domain.",
            "FAIL": "Agent touched files outside its allowed domain.",
            "WARN": "No forbidden paths defined in spec — boundary check skipped.",
        },
        "budget": {
            "PASS": "Agent self-reported tool usage within phase caps (reads<=10, writes<=12, total<=25).",
            "FAIL": "Agent exceeded a phase budget cap.",
            "WARN": "Agent did not write a Tool usage line in worklog — budget unverified.",
        },
        "result": {
            "PASS": "All three checks passed.",
            "FAIL": "One or more checks failed — see individual columns.",
            "WARN": "Passed with warnings — review budget and context columns.",
        },
    }

    def badge(val, check):
        v = val.upper().split()[0]
        tip = TOOLTIPS.get(check, {}).get(v, val)
        if v == "PASS":   color, bg, icon = "#16a34a", "#f0fdf4", "pass"
        elif v == "FAIL": color, bg, icon = "#dc2626", "#fef2f2", "fail"
        elif v == "WARN": color, bg, icon = "#d97706", "#fffbeb", "warn"
        else: return val
        return (
            '<span class="tip-wrap">'
            '<span style="background:' + bg + ';color:' + color + ';border-radius:4px;'
            'padding:2px 8px;font-size:12px;font-weight:500;cursor:default">' + icon + '</span>'
            '<span class="tooltip">' + tip + '</span>'
            '</span>'
        )

    rows = []
    for line in log_path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"): continue
        cells = [c.strip() for c in line.split("|") if c.strip()]
        if not cells or cells[0] == "Date": continue
        if all(set(c) <= set("-") for c in cells): continue
        if len(cells) >= 8: rows.append(cells)

    if not rows: return

    total   = len(rows)
    passed  = sum(1 for r in rows if r[7].upper() == "PASS")
    failed  = sum(1 for r in rows if r[7].upper() == "FAIL")
    warned  = sum(1 for r in rows if any(c.upper() == "WARN" for c in r[4:7]))
    tnums   = [int(r[3].replace(",", "")) for r in rows if r[3].replace(",", "").isdigit() and int(r[3].replace(",", "")) > 0]
    avg_tok = f"{round(sum(tnums)/len(tnums)):,}" if tnums else "-"
    last_dt = rows[-1][0]

    trows = ""
    for r in rows:
        tok = r[3]
        tcell = (
            '<span style="background:#f0f9ff;color:#0369a1;border-radius:4px;'
            'padding:2px 8px;font-size:12px;font-weight:500">' + tok + '</span>'
            if tok not in ("-", "0") else
            '<span style="color:#94a3b8">-</span>'
        )
        trows += (
            "<tr>"
            "<td>" + r[0] + "</td>"
            '<td><span style="background:#eff6ff;color:#1d4ed8;border-radius:4px;padding:2px 8px;font-size:12px;font-weight:500">' + r[1] + "</span></td>"
            '<td><span style="background:#f3f4f6;color:#374151;border-radius:4px;padding:2px 8px;font-size:12px">' + r[2] + "</span></td>"
            "<td>" + tcell + "</td>"
            "<td>" + badge(r[4], "context") + "</td>"
            "<td>" + badge(r[5], "forbidden") + "</td>"
            "<td>" + badge(r[6], "budget") + "</td>"
            "<td>" + badge(r[7], "result") + "</td>"
            "</tr>"
        )

    css = (
        "*{box-sizing:border-box;margin:0;padding:0}"
        "body{font-family:Inter,-apple-system,sans-serif;background:#f8fafc;color:#1e293b;padding:32px 24px;line-height:1.5}"
        ".container{max-width:920px;margin:0 auto}"
        "h1{font-size:22px;font-weight:600;color:#0f172a;margin-bottom:4px}"
        ".subtitle{font-size:13px;color:#64748b;margin-bottom:28px}"
        ".summary-row{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin-bottom:28px}"
        ".stat-card{background:#fff;border:0.5px solid #e2e8f0;border-radius:10px;padding:14px 16px}"
        ".stat-label{font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:.04em;margin-bottom:6px}"
        ".stat-value{font-size:26px;font-weight:600}"
        ".table-wrap{background:#fff;border:0.5px solid #e2e8f0;border-radius:10px;overflow:hidden;margin-bottom:20px}"
        "table{width:100%;border-collapse:collapse;font-size:13px}"
        "thead th{padding:10px 14px;text-align:left;font-size:11px;font-weight:600;text-transform:uppercase;"
        "letter-spacing:.04em;color:#64748b;background:#f8fafc;border-bottom:0.5px solid #e2e8f0}"
        "tbody tr{border-bottom:0.5px solid #f1f5f9}"
        "tbody tr:last-child{border-bottom:none}"
        "tbody tr:hover{background:#f8fafc}"
        "tbody td{padding:10px 14px;color:#334155}"
        ".hint{background:#f0f9ff;border:0.5px solid #bae6fd;border-radius:8px;padding:12px 16px;font-size:13px;color:#0369a1}"
        ".hint code{background:#e0f2fe;padding:1px 5px;border-radius:3px;font-size:12px}"
        ".tip-wrap{position:relative;display:inline-block}"
        ".tooltip{visibility:hidden;opacity:0;position:absolute;bottom:calc(100% + 6px);left:50%;"
        "transform:translateX(-50%);background:#1e293b;color:#f8fafc;font-size:12px;line-height:1.4;"
        "padding:7px 10px;border-radius:6px;white-space:normal;width:220px;z-index:10;"
        "pointer-events:none;transition:opacity .15s}"
        ".tooltip::after{content:'';position:absolute;top:100%;left:50%;transform:translateX(-50%);"
        "border:5px solid transparent;border-top-color:#1e293b}"
        ".tip-wrap:hover .tooltip{visibility:visible;opacity:1}"
    )

    html = (
        '<!DOCTYPE html>\n<html lang="en"><head><meta charset="utf-8">'
        '<title>Constraint Dashboard - Manifesto</title>'
        '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">'
        '<style>' + css + '</style></head><body><div class="container">'
        '<h1>Constraint Dashboard</h1>'
        '<p class="subtitle">Manifesto &middot; ' + str(total) + ' commits verified &middot; last updated ' + last_dt + '</p>'
        '<div class="summary-row">'
        '<div class="stat-card"><div class="stat-label">Commits checked</div><div class="stat-value" style="color:#0f172a">' + str(total) + '</div></div>'
        '<div class="stat-card"><div class="stat-label">All passed</div><div class="stat-value" style="color:#16a34a">' + str(passed) + '</div></div>'
        '<div class="stat-card"><div class="stat-label">Failed</div><div class="stat-value" style="color:#dc2626">' + str(failed) + '</div></div>'
        '<div class="stat-card"><div class="stat-label">Warnings</div><div class="stat-value" style="color:#d97706">' + str(warned) + '</div></div>'
        '<div class="stat-card"><div class="stat-label">Avg tokens</div><div class="stat-value" style="color:#2563eb">' + avg_tok + '</div></div>'
        '</div>'
        '<div class="table-wrap"><table>'
        '<thead><tr><th>Date</th><th>Commit</th><th>Agent</th><th>Tokens</th>'
        '<th>Context</th><th>Forbidden</th><th>Budget</th><th>Result</th></tr></thead>'
        '<tbody>' + trows + '</tbody></table></div>'
        '<div class="hint">Regenerated by <code>hooks/verify_constraints.py</code> after each commit. Hover any badge for details.</div>'
        '</div></body></html>'
    )

    dashboard_path.write_text(html, encoding="utf-8")


if __name__ == "__main__":
    main()
