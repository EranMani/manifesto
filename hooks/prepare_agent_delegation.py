#!/usr/bin/env python3
"""Prepare a bounded live delegation brief for a Manifesto implementor."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from codebase_graph import graph_cache_is_stale, write_codebase_graph
from constraint_dashboard import render_dashboard
from context_engine import ContextPackageBuilder, load_rules
from context_telemetry import initialize_telemetry
from tool_cap_start import initialize_commit_state
from validate_commit_spec import require_valid_commit_spec, require_valid_pending_graph


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RULES = Path(__file__).resolve().parent / "context_rules.json"
AGENT_FILES = {
    "rex": ".claude/agents/backend.md",
    "nova": ".claude/agents/ai-engineer.md",
    "aria": ".claude/agents/frontend.md",
    "adam": ".claude/agents/devops.md",
}
WORKLOG_FILES = {
    "rex": ".claude/agents/logs/rex-worklog.md",
    "nova": ".claude/agents/logs/nova-worklog.md",
    "aria": ".claude/agents/logs/aria-worklog.md",
    "adam": ".claude/agents/logs/adam-worklog.md",
}


def section(text: str, heading: str) -> str:
    match = re.search(
        rf"^##\s+{re.escape(heading)}\s*$\n(.*?)(?=^##\s+|\Z)",
        text,
        re.MULTILINE | re.DOTALL | re.IGNORECASE,
    )
    return match.group(1).strip() if match else ""


def compact_lines(text: str, limit: int = 12) -> list[str]:
    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip() and not line.strip().startswith("---")
    ]
    return lines[:limit]


def relevant_handoffs(state: dict[str, Any], agent: str) -> list[dict[str, Any]]:
    return [
        handoff
        for handoff in state.get("open_handoffs", [])
        if str(handoff.get("to", "")).lower() == agent
    ]


def render_brief(
    repo_root: Path,
    package: dict[str, Any],
    spec: str,
    state: dict[str, Any],
) -> str:
    agent = package["agent"]
    commit = package["commit"]
    title = spec.splitlines()[0].lstrip("# ").strip()
    what = compact_lines(section(spec, "What"), 6)
    done = compact_lines(section(spec, "Done When"), 12)
    handoffs = relevant_handoffs(state, agent)
    primary = [item for item in package["files"] if item["category"] == "primary"]
    support = [item for item in package["files"] if item["category"] != "primary"]

    lines = [
        f"# Live Delegation Brief — {commit} · {agent.title()}",
        "",
        f"**Task:** {title}",
        f"**Context mode:** `{package['mode']}` via `{package['graph']['source']}` graph",
        f"**Budget:** {package['budget']['selected_files']} files · "
        f"~{package['budget']['estimated_selected_chars']} estimated characters",
        "",
        "## Objective",
        *what,
        "",
        "## Primary Work",
    ]
    for item in primary:
        lines.append(
            f"- `{item['path']}` — {'; '.join(item['reasons'])}; "
            f"read: {item['read_strategy']}"
        )
    lines.extend(["", "## Supporting Context"])
    for item in support:
        lines.append(
            f"- `{item['path']}` [{item['category']}] — "
            f"{'; '.join(item['reasons'])}; read: {item['read_strategy']}"
        )
    lines.extend(["", "## Boundaries"])
    for forbidden in package["forbidden_edits"]:
        lines.append(f"- Do not edit `{forbidden}`")
    lines.extend(["", "## Relevant Handoffs"])
    if handoffs:
        for handoff in handoffs:
            lines.append(
                f"- {handoff.get('from', 'unknown')} → {agent}: "
                f"{handoff.get('regarding', '')} — {handoff.get('detail', '')}"
            )
    else:
        lines.append("- None.")
    lines.extend(["", "## Acceptance"])
    lines.extend(done or ["- Follow the commit specification's Done When section."])
    lines.extend([
        "",
        "## Surgical Execution Protocol",
        "- Read the primary and supporting files above first. Do not scan directories.",
        "- For targeted-excerpt files, search the named section or symbol; never load the whole file.",
        "- Do not reread unchanged files.",
        "- Search only when an unresolved symbol, missing contract, failing test, or contradictory implementation evidence requires expansion.",
        "- Before each expansion, state: reason, exact query/path, expected decision, and tradeoff.",
        "- Keep expansion inside owned paths unless reporting a cross-domain finding.",
        "- Stop exploring once the acceptance criteria are supported.",
        "- Record decisions, corrections, handoffs, tradeoffs, and context expansions in the worklog.",
    ])
    if package["expansion_triggers"]:
        lines.extend(["", "## Known Expansion Triggers"])
        lines.extend(f"- {trigger}" for trigger in package["expansion_triggers"])
    lines.extend([
        "",
        "## Return Contract",
        "Start your final message with this concise plain-language report:",
        "",
        "## Human Summary",
        "**What I completed:** Describe the finished behavior in plain language.",
        "**What changed:** Name the important files, interfaces, or behavior changed.",
        "**What went wrong:** Describe problems encountered, or write `None`.",
        "**What remains:** Describe unfinished or deferred work, or write `None`.",
        "**Recommended next commit:** Suggest focused follow-up scope, or write `None`.",
        "**Developer attention:** State decisions, risks, or manual checks requiring attention, or write `None`.",
        "",
        "Then include this structured telemetry report (required for automation and dashboard):",
        "```json",
        "{",
        '  "tool_calls": <total count>,',
        '  "read_paths": ["path/a.py", "path/b.py"],',
        '  "write_paths": ["path/c.py"],',
        '  "searches": [{"tool": "Grep", "path": ".", "query": "pattern"}],',
        '  "commands": ["pytest backend/tests/"],',
        '  "expansions": ["path/outside-package.py"]',
        "}",
        "```",
        'Set any array to `null` if you cannot supply path-level detail (e.g. after a context gap).',
        "Claude validates and persists this report before running the verification gate.",
        "",
        "If the work cannot finish by call 18, also return:",
        "```json",
        "{",
        '  "status": "split_required",',
        '  "completed_scope": ["atomic behavior completed"],',
        '  "remaining_scope": ["unfinished behavior"],',
        '  "reason": "scope_exceeds_budget",',
        '  "suggested_commit_name": "focused-kebab-name",',
        '  "suggested_owner": "' + agent + '",',
        '  "required_files": ["path/to/file.py"],',
        '  "acceptance_criteria": ["observable result"],',
        '  "verification_command": "pytest path/to/test.py -q",',
        f'  "dependencies": ["{commit}"],',
        '  "tool_calls": 16',
        "}",
        "```",
        "You may propose this split, but you may not edit specs, assign numbers, or continue.",
        "",
        "## Invocation",
        f"Identity: `{AGENT_FILES.get(agent, 'unknown')}`",
        f"Worklog header: `{WORKLOG_FILES.get(agent, 'unknown')}` (first 50 lines only)",
        f"Commit spec: `{package['spec']}`",
        "",
        "EXECUTION CONSTRAINTS:",
        "- One normal implementor invocation for this commit.",
        "- Total cap: 18 tool uses. Call 19 is mechanically blocked.",
        "- At call 12, report budget status. By call 16, finish or return SPLIT_REQUIRED.",
        "- Maximum two context expansions. Expansion 3 is mechanically blocked.",
        "- Initial reads are limited to this brief's selected files.",
        "- Use targeted symbol searches before any additional full-file read.",
        "- No commits. Claude handles staging and commits after Eran's approval.",
    ])
    return "\n".join(lines).strip() + "\n"


def prepare(
    repo_root: Path,
    rules: dict[str, Any],
    commit: str,
    agent: str,
    force_refresh: bool = False,
) -> tuple[dict[str, Any], Path, Path, bool]:
    state_path = repo_root / "project-state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    expected_commit = str(state.get("next_commit", "")).zfill(2)
    expected_agent = str(state.get("next_commit_assignee", "")).lower()
    requested_commit = str(commit).zfill(2)
    if expected_commit and expected_commit != requested_commit:
        raise ValueError(
            f"Commit mismatch: project-state expects C{expected_commit}, "
            f"requested C{requested_commit}"
        )
    if expected_agent and expected_agent != agent:
        raise ValueError(
            f"Agent mismatch: project-state expects {expected_agent}, requested {agent}"
        )

    require_valid_pending_graph(repo_root)
    validation = require_valid_commit_spec(
        repo_root,
        requested_commit,
        expected_owner=agent,
    )
    graph_relative = rules.get("graph", {}).get(
        "cache_path",
        ".context/index/codebase-graph.json",
    )
    graph_path = (repo_root / graph_relative).resolve()
    refreshed = force_refresh or graph_cache_is_stale(repo_root, rules, graph_path)
    if refreshed:
        write_codebase_graph(repo_root, rules, graph_path)

    live_rules = json.loads(json.dumps(rules))
    live_budget = live_rules.setdefault("budget", {})
    live_budget["max_files"] = int(
        live_budget.get("live_max_files", validation["budget"]["max_context_files"])
    )
    live_budget["max_chars_per_file"] = int(
        live_budget.get("live_max_chars_per_file", 5000)
    )
    live_budget["max_total_chars"] = int(
        live_budget.get(
            "live_max_total_chars",
            validation["budget"]["max_context_chars"] + 3000,
        )
    )
    live_budget["reserve_chars"] = int(
        live_budget.get("live_reserve_chars", 3000)
    )
    package = ContextPackageBuilder(
        repo_root,
        live_rules,
        graph_path=graph_path,
        mode="live",
    ).build(commit, agent)
    budget = package["budget"]
    required_exclusions = [
        item
        for item in package.get("excluded_candidates", [])
        if item.get("category") in {"primary", "identity", "worklog", "contract", "test"}
    ]
    if (
        budget["selected_files"] > validation["budget"]["max_context_files"]
        or budget["estimated_selected_chars"] > validation["budget"]["max_context_chars"]
        or required_exclusions
    ):
        raise ValueError(
            "context package exceeds the validated budget or excludes required candidates"
        )
    package_path = (
        repo_root / ".context" / "runs" / f"{package['commit']}-{agent}-live.json"
    )
    package_path.parent.mkdir(parents=True, exist_ok=True)
    package_path.write_text(json.dumps(package, indent=2) + "\n", encoding="utf-8")

    spec_path = repo_root / package["spec"]
    brief = render_brief(
        repo_root,
        package,
        spec_path.read_text(encoding="utf-8"),
        state,
    )
    brief_path = (
        repo_root / ".context" / "delegations" / f"{package['commit']}-{agent}.md"
    )
    brief_path.parent.mkdir(parents=True, exist_ok=True)
    brief_path.write_text(brief, encoding="utf-8")
    initialize_commit_state(
        package["commit"],
        agent,
        [item["path"] for item in package["files"]],
        {
            "max_agent_invocations": validation["budget"]["max_agent_invocations"],
            "max_tool_calls": validation["budget"]["max_tool_calls"],
            "max_expansions": validation["budget"]["max_expansions"],
            "max_implementor_tokens": validation["budget"]["max_implementor_tokens"],
        },
        repo_root / "hooks" / "tool_cap.json",
    )
    initialize_telemetry(package, repo_root)
    render_dashboard(repo_root)
    return package, package_path, brief_path, refreshed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--agent", required=True, choices=sorted(AGENT_FILES))
    parser.add_argument("--rules", type=Path, default=DEFAULT_RULES)
    parser.add_argument("--force-refresh", action="store_true")
    args = parser.parse_args()

    package, package_path, brief_path, refreshed = prepare(
        REPO_ROOT,
        load_rules(args.rules),
        args.commit,
        args.agent,
        args.force_refresh,
    )
    print(f"Delegation brief: {brief_path.relative_to(REPO_ROOT)}")
    print(f"Live package: {package_path.relative_to(REPO_ROOT)}")
    print(f"Graph: {'refreshed' if refreshed else 'cache current'}")
    print(
        f"Selected {package['budget']['selected_files']} files, "
        f"~{package['budget']['estimated_selected_chars']} chars"
    )
    if package["expansion_triggers"]:
        print("Expansion triggers:")
        for trigger in package["expansion_triggers"]:
            print(f"- {trigger}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
