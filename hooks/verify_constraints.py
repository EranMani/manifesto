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

from constraint_dashboard import render_dashboard
from context_metrics import build_metric_record, upsert_metric
from validate_commit_spec import validate_commit_spec

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).parent.parent
SPECS_DIR = REPO_ROOT / "commit-specs"
AGENTS_DIR = REPO_ROOT / ".claude" / "agents"
LOGS_DIR = AGENTS_DIR / "logs"

PHASE_BUDGETS = {
    "reads":   10,
    "writes":  12,
    "reserve": 0,
    "total":   18,
}

# Files written by the harness itself on every invocation, never part of an
# implementor's planned scope. Excluded from actual_scope's unplanned-files
# and diff-line accounting.
RUNTIME_TELEMETRY_FILES = {"hooks/tool_cap.json"}


def _effective_phase_budgets(spec_result: dict) -> dict:
    """Scale reads/writes/total caps to a spec's effective max_tool_calls.

    A bootstrap_exception (e.g. greenfield budget) raises max_tool_calls in the
    effective budget returned by validate_commit_spec. reads/writes are scaled
    by the same ratio as the locked default (10/18 and 12/18) so a wider total
    cap proportionally widens the read/write sub-caps.
    """
    effective_total = int((spec_result.get("budget") or {}).get("max_tool_calls", PHASE_BUDGETS["total"]))
    if effective_total == PHASE_BUDGETS["total"]:
        return PHASE_BUDGETS
    scale = effective_total / PHASE_BUDGETS["total"]
    return {
        "reads":  round(PHASE_BUDGETS["reads"] * scale),
        "writes": round(PHASE_BUDGETS["writes"] * scale),
        "reserve": PHASE_BUDGETS["reserve"],
        "total":  effective_total,
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


def git_files_changed(commit_ref: str = "HEAD", worktree: bool = False, root: Path = REPO_ROOT) -> list:
    if worktree:
        diff = subprocess.run(
            ["git", "diff", "HEAD", "--name-only"],
            capture_output=True, text=True, cwd=root,
        )
        untracked = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            capture_output=True, text=True, cwd=root,
        )
        lines = diff.stdout.splitlines() + untracked.stdout.splitlines()
    else:
        result = subprocess.run(
            ["git", "diff-tree", "--no-commit-id", "-r", "--name-only", commit_ref],
            capture_output=True, text=True, cwd=root,
        )
        lines = result.stdout.splitlines()
    return [f.strip() for f in lines if f.strip()]


# ----------------------------------------------
# Check 1 - Context block present in spec
# ----------------------------------------------

def check_context_block(spec_text: str, commit_num: str):
    lowered = spec_text.lower()
    if "## context" in lowered:
        if (
            "initial_context:" in spec_text
            and "forbidden:" in spec_text
            and "execution_budget:" in spec_text
        ):
            return True, "context block present (initial_context, forbidden, execution_budget)"
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


def extract_authorized_new_files(spec_text: str) -> list:
    """Files the spec's 'Files to Create/Modify' table marks as `new` are explicitly
    authorized even if they fall under a forbidden directory prefix (e.g. a new page
    added to a `pages/` dir whose existing siblings are off-limits)."""
    authorized = []
    for line in spec_text.splitlines():
        match = re.match(r"\|\s*`([\w./]+)`\s*\|\s*new\s*\|", line)
        if match:
            authorized.append(match.group(1))
    return authorized


def check_forbidden_paths(spec_text: str, changed_files: list):
    forbidden = extract_forbidden_paths(spec_text)
    if not forbidden:
        return True, "WARN: no forbidden paths defined in spec (skipped)"

    authorized_new = extract_authorized_new_files(spec_text)

    violations = []
    for changed in changed_files:
        if changed in authorized_new:
            continue
        for fp in forbidden:
            if changed.startswith(fp):
                violations.append(f"{changed} (forbidden prefix: {fp})")

    if violations:
        return False, "forbidden path violations: " + "; ".join(violations)
    return True, f"no forbidden paths touched (checked: {', '.join(forbidden)})"


# ----------------------------------------------
# Check 3 - Phase budget from worklog
# ----------------------------------------------

def check_phase_budget(worklog_text: str, commit_num: str, agent: str, spec_result: dict, execution: str = "delegated"):
    if execution == "claude-direct" or agent.lower() == "claude":
        return True, {"reads": 0, "writes": 0, "total": 0}, (
            "Claude-direct execution: owner agent worklog not inspected and the "
            "18-call implementor limit does not apply; the orchestrator debugging "
            "circuit breaker (CLAUDE.md D37) applies instead"
        )
    numeric = re.match(r"\d+", str(commit_num))
    legacy = bool(numeric and int(numeric.group(0)) <= 28)
    if not worklog_text:
        if legacy:
            return True, None, "WARN: legacy commit has no worklog budget evidence"
        return False, None, "missing worklog - implementor budget cannot be verified"

    _num_match = re.match(r"(\d+)", commit_num)
    _base = int(_num_match.group(1)) if _num_match else None
    # Negative lookahead prevents "C29" or "Commit 29" matching as a prefix of a
    # letter-suffixed commit like "C29A"/"Commit 29A" (e.g. "Commit 290").
    _alts = []
    if _base is not None:
        _alts.append(rf"Commit {_base}(?![A-Za-z0-9])")
        _alts.append(rf"C{_base:02d}(?![A-Za-z0-9])")
    _alts.append(rf"Commit {commit_num}(?![A-Za-z0-9])")
    _alts.append(rf"C{commit_num}(?![A-Za-z0-9])")
    _alt_pattern = "|".join(_alts)
    # Anchor to a "## " session heading containing the commit reference, then
    # capture through the following lines up to the next "## " heading. This
    # avoids matching earlier non-heading mentions (Current State summary,
    # Session Index table rows) that precede the real session entry.
    commit_section = re.search(
        rf"^##[ \t].*(?:{_alt_pattern}).*$(?:\n(?!## ).*)*",
        worklog_text, re.MULTILINE | re.IGNORECASE
    )
    if not commit_section:
        if legacy:
            return True, None, "WARN: legacy commit has no structured tool-usage evidence"
        # Delegated execution requires an exact commit-session match. Do not fall
        # back to scanning the whole worklog - that risks matching an unrelated
        # historical "Tool usage" line from a different commit's session.
        return False, None, (
            f"no '## ... Commit {commit_num} ...' session found in {agent}'s "
            f"worklog - delegated execution requires an exact commit-session match"
        )
    section = commit_section.group(0)

    match = re.search(
        r"[Tt]ool usage[:\s]+reads?\s*=\s*(\d+)[,\s]+writes?\s*=\s*(\d+)[,\s]+total\s*=\s*(\d+)",
        section
    )
    if not match:
        if legacy:
            return True, None, "WARN: legacy commit has no structured tool-usage evidence"
        return False, None, "missing 'Tool usage: reads=N, writes=N, total=N' evidence"

    reads, writes, total = int(match.group(1)), int(match.group(2)), int(match.group(3))
    counts = {"reads": reads, "writes": writes, "total": total}
    budgets = _effective_phase_budgets(spec_result)
    failures = []
    if reads  > budgets["reads"]:  failures.append(f"reads={reads} exceeds cap of {budgets['reads']}")
    if writes > budgets["writes"]: failures.append(f"writes={writes} exceeds cap of {budgets['writes']}")
    if total  > budgets["total"]:  failures.append(f"total={total} exceeds cap of {budgets['total']}")

    if failures:
        return False, counts, f"phase budget exceeded: {'; '.join(failures)}"
    return True, counts, f"budget ok: reads={reads}/{budgets['reads']}, writes={writes}/{budgets['writes']}, total={total}/{budgets['total']}"


def check_spec_validation(commit_num: str, agent: str):
    numeric = re.match(r"\d+", str(commit_num))
    if numeric and int(numeric.group(0)) <= 28:
        return True, "legacy completed commit: new spec schema not required", {
            "status": "valid",
            "commit": f"C{int(numeric.group(0)):02d}",
            "budget": {},
            "planned_changed_files": [],
            "legacy": True,
        }
    result = validate_commit_spec(REPO_ROOT, commit_num, expected_owner=agent)
    if result["status"] == "valid":
        return True, "commit specification is valid", result
    detail = "; ".join(item["message"] for item in result["violations"])
    return False, f"commit specification invalid: {detail}", result


def check_actual_scope(spec_result: dict, changed_files: list[str], worktree: bool, commit_ref: str, agent: str = ""):
    if spec_result.get("legacy"):
        return True, None, "legacy completed commit: actual micro-scope check not applied"
    changed_files = [f for f in changed_files if f not in RUNTIME_TELEMETRY_FILES]
    planned = set(spec_result.get("planned_changed_files", []))
    # The implementor's own worklog update is mandated every commit (CLAUDE.md
    # Post-Commit File Checklist) and is never listed in a spec's
    # "Files To Modify Or Add" table - treat it as always-planned, not unplanned.
    if agent:
        planned.add(f".claude/agents/logs/{agent}-worklog.md")
    unplanned = sorted(path for path in changed_files if path not in planned)
    # spec_result["budget"] is the effective budget: validate_commit_spec already
    # merges any bootstrap_exception overrides for max_changed_files and
    # max_estimated_diff_lines, so no separate regex parse is needed here.
    budget = spec_result.get("budget", {})
    max_changed = int(budget.get("max_changed_files", 4))
    failures = []
    if len(changed_files) > max_changed:
        failures.append(f"changed_files={len(changed_files)} exceeds cap of {max_changed}")
    if unplanned:
        failures.append("unplanned files: " + ", ".join(unplanned))

    command = ["git", "diff", "--numstat", "HEAD"] if worktree else [
        "git", "show", "--numstat", "--format=", commit_ref
    ]
    result = subprocess.run(command, capture_output=True, text=True, cwd=REPO_ROOT)
    diff_lines = 0
    for line in result.stdout.splitlines():
        cells = line.split("\t")
        if len(cells) >= 3 and cells[0].isdigit() and cells[1].isdigit():
            if cells[2] in RUNTIME_TELEMETRY_FILES:
                continue
            diff_lines += int(cells[0]) + int(cells[1])
    if worktree:
        untracked = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
        )
        for relative in untracked.stdout.splitlines():
            relative = relative.strip()
            if relative in RUNTIME_TELEMETRY_FILES:
                continue
            path = REPO_ROOT / relative
            try:
                diff_lines += len(path.read_text(encoding="utf-8").splitlines())
            except (OSError, UnicodeDecodeError):
                failures.append(f"cannot count untracked text lines: {relative}")
    diff_limit = int(budget.get("max_estimated_diff_lines", 350))
    if diff_lines > diff_limit:
        failures.append(f"diff_lines={diff_lines} exceeds cap of {diff_limit}")
    counts = {
        "changed_files": len(changed_files),
        "max_changed_files": max_changed,
        "diff_lines": diff_lines,
        "max_diff_lines": diff_limit,
        "unplanned_files": unplanned,
    }
    if failures:
        return False, counts, "actual scope exceeded: " + "; ".join(failures)
    return True, counts, f"actual scope ok: files={len(changed_files)}/{max_changed}, diff_lines={diff_lines}/{diff_limit}"


# ----------------------------------------------
# Main
# ----------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Verify agent constraints for a commit.")
    parser.add_argument("--commit",  required=True, help="Commit number, e.g. 08")
    parser.add_argument("--agent",   required=True, help="Commit owner agent name, e.g. rex, aria, adam")
    parser.add_argument(
        "--execution", choices=["claude-direct", "delegated"], default="delegated",
        help="Who executed this commit: 'claude-direct' (no implementor invocation, "
             "owner worklog not inspected) or 'delegated' (--agent's worklog must "
             "contain an exact commit-session match). Default: delegated.",
    )
    parser.add_argument("--tokens",  type=int, default=None, help="Token count for this commit (optional)")
    parser.add_argument("--ref",        default="HEAD", help="Git ref to check (default: HEAD)")
    parser.add_argument("--worktree",   action="store_true", help="Check working-tree changes vs HEAD instead of a committed ref")
    parser.add_argument("--json",       action="store_true", help="Output as JSON")
    parser.add_argument("--no-persist", action="store_true",
                        help="Run checks and return PASS/FAIL without writing "
                             "CONSTRAINT_LOG.md, CONTEXT_METRICS.json, or constraint-dashboard.html")
    parser.add_argument("--render-dashboard", action="store_true",
                        help="Also regenerate constraint-dashboard.html. Default off -- "
                             "use manually or during the every-five-commit review wave.")
    args = parser.parse_args()

    spec_text    = load_spec(args.commit)
    worklog_text = load_worklog(args.agent)
    changed      = git_files_changed(args.ref, worktree=args.worktree)

    ok0, msg0, spec_result = check_spec_validation(args.commit, args.agent)
    ok1, msg1          = check_context_block(spec_text, args.commit)
    ok2, msg2          = check_forbidden_paths(spec_text, changed)
    ok3, counts3, msg3 = check_phase_budget(worklog_text, args.commit, args.agent, spec_result, args.execution)
    ok4, counts4, msg4 = check_actual_scope(spec_result, changed, args.worktree, args.ref, args.agent)

    results = {
        "spec_validation": {"pass": ok0, "message": msg0},
        "context_block":   {"pass": ok1, "message": msg1},
        "forbidden_paths": {"pass": ok2, "message": msg2},
        "phase_budget":    {"pass": ok3, "message": msg3, "counts": counts3},
        "actual_scope":    {"pass": ok4, "message": msg4, "counts": counts4},
    }

    all_pass = all(r["pass"] for r in results.values())

    if args.json:
        print(json.dumps({
            "commit": args.commit, "agent": args.agent, "execution": args.execution,
            "tokens": args.tokens, "all_pass": all_pass, "checks": results
        }, indent=2))
    else:
        status = lambda ok, msg: ("WARN" if msg and msg.startswith("WARN") else ("PASS" if ok else "FAIL"))
        print(f"\n-- Constraint Verification: C{args.commit.zfill(2)} ({args.agent}, {args.execution}) --\n")
        print(f"  [0] Commit spec      [{status(ok0, msg0)}] {msg0}")
        print(f"  [1] Context block    [{status(ok1, msg1)}] {msg1}")
        print(f"  [2] Forbidden paths  [{status(ok2, msg2)}] {msg2}")
        print(f"  [3] Phase budget     [{status(ok3, msg3)}] {msg3}")
        print(f"  [4] Actual scope     [{status(ok4, msg4)}] {msg4}")
        if args.tokens:
            print(f"  [5] Tokens used      {args.tokens:,}")
        print()
        print(f"  RESULT: {'ALL CHECKS PASSED' if all_pass else 'FAILED - ' + ', '.join(k for k,v in results.items() if not v['pass'])}")
        print()

    if not args.no_persist:
        if args.execution == "claude-direct":
            tokens = None
        else:
            tokens = args.tokens if args.tokens is not None else get_tokens_from_records(args.commit)
        append_to_log(args.commit, args.agent, results, all_pass, tokens)
        upsert_metric(
            build_metric_record(
                args.commit,
                args.agent,
                tokens,
                results,
                changed,
                execution=args.execution,
            )
        )
        if args.render_dashboard:
            render_dashboard()
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
        msg = r["message"] or ""
        if msg.startswith("WARN"): return "WARN"
        if r["pass"]: return "PASS"
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
        if len(cells) >= 3 and cells[1] == commit_key and cells[2].lower() == agent.lower():
            return

    row = "| " + date + " | " + commit_key + " | " + agent + " | " + tokens_str + " | " + context + " | " + forbidden + " | " + budget + budget_detail + " | " + result + " |\n"
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(row)


# ----------------------------------------------
# Dashboard embedder
# ----------------------------------------------

def embed_into_dashboard():
    render_dashboard()
    return

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
