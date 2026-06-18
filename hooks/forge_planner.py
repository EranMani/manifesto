#!/usr/bin/env python3
"""
forge_planner.py — Commit decomposition engine for the /forge command.

Takes a forge scan report + task analysis and produces a commit plan:
- Groups changes by owner, respecting the 4-file limit
- Topological sort for dependency ordering
- Assigns scope estimates (XS/S/M/L)
- Determines execution route (Claude-direct vs. delegated)
- Computes next available commit numbers from commit-protocol.md

Pure deterministic logic — no LLM calls.

Usage:
    python hooks/forge_planner.py --report .forge/report.json \\
        --task "Add rate limiting to the API" \\
        --files backend/app/api/v1/auth.py,backend/app/middleware/rate_limit.py \\
        --out .forge/plan.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parent.parent

LOCKED_BUDGET = {
    "max_primary_files": 2,
    "max_changed_files": 4,
    "max_context_files": 6,
    "max_context_chars": 15000,
    "max_estimated_diff_lines": 350,
    "max_agent_invocations": 1,
    "max_tool_calls": 18,
    "max_expansions": 2,
    "max_implementor_tokens": 45000,
}

LAYER_ORDER = {
    "ai": 0,
    "backend": 1,
    "devops": 2,
    "frontend": 3,
    "docs": 4,
    "config": 5,
    "other": 6,
}


# ---------------------------------------------------------------------------
# Commit number resolution
# ---------------------------------------------------------------------------

def find_next_commit_number(repo_root: Path) -> int:
    """Parse commit-protocol.md to find the next available commit number."""
    protocol_path = repo_root / "commit-protocol.md"
    if not protocol_path.exists():
        return 1

    content = protocol_path.read_text(encoding="utf-8")
    numbers: list[int] = []
    for match in re.finditer(r"^\|\s*(\d+[A-Z]?)\s*\|", content, re.MULTILINE):
        raw = match.group(1)
        num_match = re.match(r"(\d+)", raw)
        if num_match:
            numbers.append(int(num_match.group(1)))

    return max(numbers) + 1 if numbers else 1


def find_last_completed_commit(repo_root: Path) -> int | None:
    """Read project-state.json for the last completed commit."""
    state_path = repo_root / "project-state.json"
    if not state_path.exists():
        return None
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
        lc = state.get("last_completed_commit")
        return int(lc) if lc else None
    except (json.JSONDecodeError, ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# File grouping by owner
# ---------------------------------------------------------------------------

def group_files_by_owner(
    files: list[str],
    ownership_map: dict[str, str],
) -> dict[str, list[str]]:
    """Group files by their owning agent."""
    groups: dict[str, list[str]] = {}
    for f in files:
        owner = ownership_map.get(f, "claude")
        groups.setdefault(owner, []).append(f)
    return groups


def split_by_budget(
    files: list[str],
    max_files: int = 4,
) -> list[list[str]]:
    """Split a file list into chunks that respect the max_changed_files budget."""
    if len(files) <= max_files:
        return [files]
    chunks: list[list[str]] = []
    for i in range(0, len(files), max_files):
        chunks.append(files[i : i + max_files])
    return chunks


# ---------------------------------------------------------------------------
# Scope estimation
# ---------------------------------------------------------------------------

def estimate_scope(
    files: list[str],
    hubs: list[dict[str, Any]],
) -> str:
    """Estimate commit scope: XS / S / M / L based on file count and hub involvement."""
    hub_paths = {h["path"] for h in hubs}
    touches_hub = any(f in hub_paths for f in files)
    count = len(files)

    if count <= 1 and not touches_hub:
        return "XS"
    elif count <= 2 and not touches_hub:
        return "S"
    elif count <= 3 or (count <= 2 and touches_hub):
        return "M"
    else:
        return "L"


# ---------------------------------------------------------------------------
# Execution route decision
# ---------------------------------------------------------------------------

def decide_execution(
    owner: str,
    files: list[str],
    hubs: list[dict[str, Any]],
    task_type: str,
) -> tuple[str, str]:
    """Decide Claude-direct vs. delegated execution.

    Returns (execution_mode, justification).
    """
    hub_paths = {h["path"] for h in hubs}
    touches_hub = any(f in hub_paths for f in files)

    if owner == "claude":
        return "claude-direct", "Workflow/orchestration — Claude's domain"

    if task_type in ("fix", "refactor") and len(files) <= 2 and not touches_hub:
        return (
            "claude-direct",
            f"Mechanical {task_type}: {len(files)} files, no hub involvement, "
            f"follows existing patterns",
        )

    if touches_hub and len(files) >= 3:
        return (
            "delegated",
            f"Bounded specialist unit: touches hub file(s) in {owner}'s domain, "
            f"{len(files)} files require domain expertise",
        )

    if task_type == "feature" and len(files) >= 3:
        return (
            "delegated",
            f"New feature with {len(files)} files in {owner}'s domain — "
            f"specialist expertise exceeds invocation overhead",
        )

    return (
        "claude-direct",
        f"Known pattern: {len(files)} files in {owner}'s domain, "
        f"no specialist uncertainty",
    )


# ---------------------------------------------------------------------------
# Dependency ordering
# ---------------------------------------------------------------------------

def infer_layer(files: list[str], categories: dict[str, list[str]]) -> str:
    """Determine the dominant layer for a set of files."""
    layer_counts: dict[str, int] = {}
    for f in files:
        for cat, cat_files in categories.items():
            if f in cat_files:
                layer_counts[cat] = layer_counts.get(cat, 0) + 1
                break
    if not layer_counts:
        return "other"
    return max(layer_counts, key=lambda c: layer_counts[c])


def order_commits(
    commits: list[dict[str, Any]],
    categories: dict[str, list[str]],
) -> list[dict[str, Any]]:
    """Order commits by layer dependency: ai → backend → devops → frontend → docs."""
    for c in commits:
        c["_layer"] = infer_layer(c["files"], categories)
        c["_layer_order"] = LAYER_ORDER.get(c["_layer"], 99)

    commits.sort(key=lambda c: c["_layer_order"])

    for i, c in enumerate(commits):
        if i == 0:
            c["depends_on"] = None
        else:
            prev = commits[i - 1]
            if prev["_layer_order"] < c["_layer_order"]:
                c["depends_on"] = prev["number"]
            else:
                c["depends_on"] = None

    for c in commits:
        c.pop("_layer", None)
        c.pop("_layer_order", None)

    return commits


# ---------------------------------------------------------------------------
# Agent routing
# ---------------------------------------------------------------------------

def determine_agents_needed(
    owner_groups: dict[str, list[str]],
) -> list[dict[str, str]]:
    """Determine which agents should be consulted for design input."""
    agent_purposes = {
        "rex": "Backend architecture and service layer design",
        "aria": "Frontend component design and layout",
        "nova": "AI/ML pipeline and prompt engineering",
        "adam": "Infrastructure and deployment configuration",
        "mira": "Product review of user-facing behavior",
    }

    agents: list[dict[str, str]] = []
    for owner in owner_groups:
        if owner in agent_purposes:
            agents.append({
                "agent": owner,
                "purpose": agent_purposes[owner],
            })

    has_frontend = "aria" in owner_groups
    has_backend = "rex" in owner_groups or "nova" in owner_groups
    if has_frontend or has_backend:
        if not any(a["agent"] == "mira" for a in agents):
            agents.append({
                "agent": "mira",
                "purpose": "Product review — task affects user-facing behavior",
            })

    return agents


# ---------------------------------------------------------------------------
# Plan generation
# ---------------------------------------------------------------------------

def generate_plan(
    task: str,
    task_type: str,
    target_files: list[str],
    report: dict[str, Any],
    repo_root: Path,
) -> dict[str, Any]:
    """Generate a full commit plan from task + scan report."""
    ownership_map = report.get("domain_ownership", {})
    categories = report.get("categories", {})
    hubs = report.get("hubs", [])

    owner_groups = group_files_by_owner(target_files, ownership_map)
    next_num = find_next_commit_number(repo_root)

    commits: list[dict[str, Any]] = []
    commit_num = next_num

    for owner, files in sorted(owner_groups.items()):
        chunks = split_by_budget(files, LOCKED_BUDGET["max_changed_files"])

        for chunk_idx, chunk in enumerate(chunks):
            execution, justification = decide_execution(
                owner, chunk, hubs, task_type,
            )
            scope = estimate_scope(chunk, hubs)

            primary = chunk[:LOCKED_BUDGET["max_primary_files"]]

            commits.append({
                "number": commit_num,
                "name": None,
                "owner": owner,
                "depends_on": None,
                "files": chunk,
                "primary_files": primary,
                "scope": scope,
                "execution": execution,
                "execution_justification": justification,
                "budget": dict(LOCKED_BUDGET),
            })
            commit_num += 1

    commits = order_commits(commits, categories)

    for i, c in enumerate(commits):
        c["number"] = next_num + i

    agents_needed = determine_agents_needed(owner_groups)

    dep_parts = []
    for c in commits:
        dep_parts.append(f"C{c['number']}")
    dependency_chain = " → ".join(dep_parts)

    est_tokens = sum(
        LOCKED_BUDGET["max_implementor_tokens"]
        if c["execution"] == "delegated"
        else 15000
        for c in commits
    )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "task": task,
        "task_type": task_type,
        "target_files": target_files,
        "commits": commits,
        "dependency_chain": dependency_chain,
        "agents_needed": agents_needed,
        "total_estimated_tokens": est_tokens,
        "next_commit_start": next_num,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Forge commit planner")
    parser.add_argument("--report", required=True, help="Path to .forge/report.json")
    parser.add_argument("--task", required=True, help="Task description")
    parser.add_argument("--task-type", default="feature",
                        choices=["feature", "fix", "refactor"],
                        help="Task type")
    parser.add_argument("--files", required=True,
                        help="Comma-separated list of target files")
    parser.add_argument("--out", default=".forge/plan.json",
                        help="Output path for plan JSON")
    parser.add_argument("--json", action="store_true",
                        help="Print JSON to stdout")
    args = parser.parse_args()

    report_path = Path(args.report)
    if not report_path.exists():
        print(f"ERROR: report not found: {report_path}", file=sys.stderr)
        return 1

    report = json.loads(report_path.read_text(encoding="utf-8"))
    target_files = [f.strip() for f in args.files.split(",") if f.strip()]

    repo_root = Path(report.get("repo_root", ".")).resolve()
    if not repo_root.exists():
        repo_root = REPO_ROOT

    plan = generate_plan(
        task=args.task,
        task_type=args.task_type,
        target_files=target_files,
        report=report,
        repo_root=repo_root,
    )

    if args.json:
        print(json.dumps(plan, indent=2))
        return 0

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(plan, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    n = len(plan["commits"])
    agents = len(plan["agents_needed"])
    tokens = plan["total_estimated_tokens"]
    print(
        f"Plan: {n} commits, {agents} agents to consult, "
        f"~{tokens:,} estimated tokens. Written to {out_path}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
