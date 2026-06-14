#!/usr/bin/env python3
"""Build and activate a deterministic context package for Claude-direct work."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from codebase_graph import graph_cache_is_stale, write_codebase_graph
from context_engine import ContextPackageBuilder, load_rules
from context_telemetry import initialize_execution_scope
from preflight_commit import evaluate_direct
from validate_commit_spec import require_valid_commit_spec


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RULES = Path(__file__).resolve().parent / "context_rules.json"


class DirectPreflightBlocked(ValueError):
    def __init__(self, result: dict[str, Any]) -> None:
        super().__init__(result)
        self.result = result


def _section(text: str, heading: str) -> list[str]:
    import re

    match = re.search(
        rf"^##\s+{re.escape(heading)}\s*$\n(.*?)(?=^##\s+|\Z)",
        text,
        re.MULTILINE | re.DOTALL | re.IGNORECASE,
    )
    if not match:
        return []
    return [
        line.strip()
        for line in match.group(1).splitlines()
        if line.strip() and not line.strip().startswith("```")
    ]


def _direct_rules(
    rules: dict[str, Any], owner: str, validation: dict[str, Any]
) -> dict[str, Any]:
    direct = json.loads(json.dumps(rules))
    budget = direct.setdefault("budget", {})
    direct_budget = rules.get("direct_budget", {})
    validated = validation["budget"]
    budget["max_files"] = min(
        int(direct_budget.get("max_files", 6)),
        int(validated["max_context_files"]),
    )
    budget["max_chars_per_file"] = int(
        direct_budget.get("max_chars_per_file", 3000)
    )
    budget["max_total_chars"] = min(
        int(direct_budget.get("max_total_chars", 15000)),
        int(validated["max_context_chars"]),
    )
    budget["reserve_chars"] = min(
        int(direct_budget.get("reserve_chars", 1500)),
        max(0, budget["max_total_chars"] // 4),
    )
    direct.setdefault("agents", {}).setdefault(owner, {})["worklog"] = None
    return direct


def render_direct_brief(package: dict[str, Any], spec: str) -> str:
    primary = [
        item for item in package["files"] if item["category"] in {"primary", "test"}
    ]
    supporting = [
        item for item in package["files"] if item["category"] not in {"primary", "test"}
    ]
    lines = [
        f"# Claude-Direct Execution Brief - {package['commit']}",
        "",
        f"**Owner:** {package['agent'].title()}",
        f"**Graph:** `{package['graph']['source']}`",
        f"**Initial context:** {package['budget']['selected_files']} files, "
        f"~{package['budget']['estimated_selected_chars']} characters",
        "",
        "## Goal",
        *(_section(spec, "Primary Behavior")[:4] or ["Follow the commit specification."]),
        "",
        "## Planned Files",
    ]
    for item in primary:
        lines.append(
            f"- `{item['path']}` - {'; '.join(item['reasons'])}; "
            f"read: {item['read_strategy']}"
        )
    lines.extend(["", "## Preselected Supporting Context"])
    if supporting:
        for item in supporting:
            lines.append(
                f"- `{item['path']}` [{item['category']}] - "
                f"{'; '.join(item['reasons'])}; read: {item['read_strategy']}"
            )
    else:
        lines.append("- None.")
    lines.extend(["", "## Contract"])
    lines.extend(_section(spec, "Contract")[:10] or ["- Follow the specification contract."])
    lines.extend(["", "## Verification"])
    lines.extend(_section(spec, "Verification Command")[:6] or ["- Use the specification command."])
    lines.extend(["", "## Boundaries"])
    for path in package.get("forbidden_edits", []):
        lines.append(f"- Do not edit `{path}`")
    lines.extend([
        "",
        "## Context Rules",
        "- Start with this brief and the selected files. Do not scan directories.",
        "- Use targeted excerpts exactly where specified.",
        "- Expand only for an unresolved symbol, missing contract, failing test, or contradictory evidence.",
        "- Before expansion, record the reason, exact query or path, and expected decision.",
        "- Stop reading when the contract and verification path are sufficiently supported.",
    ])
    return "\n".join(lines).strip() + "\n"


def prepare_direct(
    repo_root: Path,
    rules: dict[str, Any],
    commit: str,
    owner: str,
    *,
    force_refresh: bool = False,
    activate: bool = True,
) -> tuple[dict[str, Any], Path, Path, bool]:
    result = evaluate_direct(repo_root, commit, owner)
    if not result.get("proceed"):
        raise DirectPreflightBlocked(result)

    validation = require_valid_commit_spec(
        repo_root, commit, expected_owner=owner
    )
    graph_relative = rules.get("graph", {}).get(
        "cache_path", ".context/index/codebase-graph.json"
    )
    graph_path = (repo_root / graph_relative).resolve()
    refreshed = force_refresh or graph_cache_is_stale(repo_root, rules, graph_path)
    if refreshed:
        write_codebase_graph(repo_root, rules, graph_path)

    package = ContextPackageBuilder(
        repo_root,
        _direct_rules(rules, owner, validation),
        graph_path=graph_path,
        mode="claude-direct",
    ).build(commit, owner)
    package["files"] = [
        item
        for item in package["files"]
        if item.get("category") not in {"identity", "worklog"}
    ]
    retained = {item["path"] for item in package["files"]}
    package["unresolved"] = [
        item
        for item in package.get("unresolved", [])
        if item.get("path") in retained
    ]
    package["budget"]["selected_files"] = len(package["files"])
    package["budget"]["estimated_selected_chars"] = sum(
        int(item.get("estimated_chars", 0)) for item in package["files"]
    )
    required_exclusions = [
        item
        for item in package.get("excluded_candidates", [])
        if item.get("category") in {"primary", "test", "contract"}
    ]
    if required_exclusions:
        raise ValueError(
            "direct context package excludes required planned or contract files"
        )
    package["executor"] = "claude"
    package["selection_policy"] = "deterministic-graph-v1"

    package_path = (
        repo_root / ".context" / "runs" / f"{package['commit']}-claude-direct.json"
    )
    package_path.parent.mkdir(parents=True, exist_ok=True)
    package_path.write_text(json.dumps(package, indent=2) + "\n", encoding="utf-8")

    spec_path = repo_root / package["spec"]
    brief_path = repo_root / ".context" / "direct" / f"{package['commit']}.md"
    brief_path.parent.mkdir(parents=True, exist_ok=True)
    brief_path.write_text(
        render_direct_brief(package, spec_path.read_text(encoding="utf-8")),
        encoding="utf-8",
    )
    if activate:
        initialize_execution_scope(commit, owner, repo_root, package=package)
    return package, package_path, brief_path, refreshed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--owner", required=True)
    parser.add_argument("--rules", type=Path, default=DEFAULT_RULES)
    parser.add_argument("--force-refresh", action="store_true")
    parser.add_argument("--preview", action="store_true")
    args = parser.parse_args()
    try:
        package, package_path, brief_path, refreshed = prepare_direct(
            REPO_ROOT,
            load_rules(args.rules),
            args.commit,
            args.owner.lower(),
            force_refresh=args.force_refresh,
            activate=not args.preview,
        )
    except DirectPreflightBlocked as exc:
        print(json.dumps(exc.result, indent=2))
        return 1
    label = "Preview" if args.preview else "Active"
    print(f"{label} direct brief: {brief_path.relative_to(REPO_ROOT)}")
    print(f"Direct package: {package_path.relative_to(REPO_ROOT)}")
    print(f"Graph: {'refreshed' if refreshed else 'cache current'}")
    print(
        f"Selected {package['budget']['selected_files']} files, "
        f"~{package['budget']['estimated_selected_chars']} chars"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
