#!/usr/bin/env python3
"""Validate a Manifesto commit specification before delegation."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


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

DEFAULT_MAX_TOTAL_TOKENS = 60000

GREENFIELD_BUDGET_CEILINGS = {
    "max_tool_calls": 28,
    "max_expansions": 2,
    "max_implementor_tokens": 55000,
    "max_total_tokens": 70000,
    "max_agent_invocations": 1,
    "max_changed_files": LOCKED_BUDGET["max_changed_files"],
    "max_estimated_diff_lines": LOCKED_BUDGET["max_estimated_diff_lines"],
}

BOOTSTRAP_EXCEPTION_FIELDS = {"reason", *GREENFIELD_BUDGET_CEILINGS}


def commit_key(value: str | int) -> str:
    raw = str(value).strip().upper()
    if raw.startswith("C"):
        raw = raw[1:]
    match = re.fullmatch(r"(\d+)([A-Z]?)", raw)
    if not match:
        raise ValueError(
            f"commit identifier must be an integer with an optional letter suffix, got {value!r}"
        )
    return f"C{int(match.group(1)):02d}{match.group(2)}"


def commit_order(value: str | int) -> tuple[int, int]:
    key = commit_key(value)
    match = re.fullmatch(r"C(\d+)([A-Z]?)", key)
    if not match:
        raise ValueError(f"invalid canonical commit identifier {key!r}")
    suffix = match.group(2)
    return int(match.group(1)), 0 if not suffix else ord(suffix) - ord("A") + 1


def section(text: str, heading: str) -> str:
    match = re.search(
        rf"^##\s+{re.escape(heading)}\s*$\n(.*?)(?=^##\s+|\Z)",
        text,
        re.MULTILINE | re.DOTALL | re.IGNORECASE,
    )
    return match.group(1).strip() if match else ""


def metadata_value(text: str, field: str) -> str | None:
    match = re.search(
        rf"^\*\*{re.escape(field)}:\*\*\s*(.+?)\s*$",
        text,
        re.MULTILINE | re.IGNORECASE,
    )
    return match.group(1).strip() if match else None


def normalized_owner(value: str | None) -> str | None:
    if not value:
        return None
    first = re.split(r"[\s(]", value.strip(), maxsplit=1)[0].lower()
    aliases = {
        "backend": "rex",
        "frontend": "aria",
        "devops": "adam",
        "ai/ml": "nova",
        "ai-engineer": "nova",
    }
    return aliases.get(first, first)


def yaml_ints(block: str, name: str) -> dict[str, int]:
    match = re.search(
        rf"^\s*{re.escape(name)}:\s*$\n(.*?)(?=^\S|\Z)",
        block,
        re.MULTILINE | re.DOTALL,
    )
    if not match:
        return {}
    values: dict[str, int] = {}
    for key, value in re.findall(r"^\s{2,}([a-z_]+):\s*(\d+)\s*$", match.group(1), re.MULTILINE):
        values[key] = int(value)
    return values


def yaml_keys(block: str, name: str) -> list[str]:
    match = re.search(
        rf"^\s*{re.escape(name)}:\s*$\n(.*?)(?=^\S|\Z)",
        block,
        re.MULTILINE | re.DOTALL,
    )
    if not match:
        return []
    return re.findall(r"^\s{2,}([a-z_]+):", match.group(1), re.MULTILINE)


def yaml_list(block: str, name: str) -> list[str]:
    match = re.search(
        rf"^\s*{re.escape(name)}:\s*$\n(.*?)(?=^\S|\Z)",
        block,
        re.MULTILINE | re.DOTALL,
    )
    if not match:
        return []
    return [
        item.strip().split("#", 1)[0].strip()
        for item in re.findall(r"^\s{2,}-\s+(.+?)\s*$", match.group(1), re.MULTILINE)
    ]


def changed_file_rows(text: str) -> list[str]:
    files = section(text, "Files To Modify Or Add") or section(text, "Files to Create / Change")
    return re.findall(r"^\|\s*`([^`]+)`\s*\|", files, re.MULTILINE)


def dependency_keys(text: str) -> list[str]:
    value = metadata_value(text, "Depends on")
    if not value or value.strip().lower() in {"none", "n/a"}:
        return []
    return [
        commit_key(item)
        for item in re.findall(r"\bC?\d+[A-Z]?\b", value, re.IGNORECASE)
    ]


def protocol_entries(repo_root: Path) -> dict[str, dict[str, str]]:
    path = repo_root / "commit-protocol.md"
    if not path.exists():
        return {}
    entries: dict[str, dict[str, str]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        cells = [cell.strip() for cell in line.split("|") if cell.strip()]
        if len(cells) < 4 or not re.fullmatch(r"\d+[A-Za-z]?", cells[0]):
            continue
        key = commit_key(cells[0])
        entries[key] = {
            "name": cells[1],
            "owner": normalized_owner(cells[2]) or "",
            "status": cells[3].lower(),
        }
    return entries


def owner_paths(repo_root: Path, owner: str | None) -> tuple[list[str], list[str]] | None:
    path = repo_root / "hooks" / "agent-config.json"
    if not path.exists() or not owner:
        return None
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    universal = config.get("universal_allowed", [])
    for agent in config.get("agents", {}).values():
        if str(agent.get("name", "")).lower() == owner:
            return universal, agent.get("domains", [])
    return universal, []


def protocol_entry(repo_root: Path, key: str) -> tuple[str, str] | None:
    entry = protocol_entries(repo_root).get(key)
    if not entry:
        return None
    return entry["name"], entry["owner"]


def add_violation(
    violations: list[dict[str, Any]],
    rule: str,
    message: str,
    actual: Any = None,
    limit: Any = None,
) -> None:
    item: dict[str, Any] = {"rule": rule, "message": message}
    if actual is not None:
        item["actual"] = actual
    if limit is not None:
        item["limit"] = limit
    violations.append(item)


def validate_commit_spec(
    repo_root: Path,
    commit: str | int,
    expected_owner: str | None = None,
) -> dict[str, Any]:
    try:
        key = commit_key(commit)
    except ValueError as exc:
        return {"status": "split_required", "commit": str(commit), "violations": [
            {"rule": "commit_identifier", "message": str(exc)}
        ]}

    spec_path = repo_root / "commit-specs" / f"commit-{key[1:].lower()}.md"
    violations: list[dict[str, Any]] = []
    if not spec_path.exists():
        add_violation(violations, "spec_exists", f"missing {spec_path.relative_to(repo_root)}")
        return {"status": "split_required", "commit": key, "violations": violations}

    text = spec_path.read_text(encoding="utf-8")
    heading = re.search(r"^#\s+Commit\s+([^\s]+)\s+[-—]", text, re.MULTILINE)
    if not heading:
        add_violation(violations, "heading", "missing '# Commit NN - name' heading")
    else:
        try:
            heading_key = commit_key(heading.group(1))
        except ValueError:
            heading_key = None
        if heading_key != key:
            add_violation(violations, "heading_commit", "heading and filename disagree", heading.group(1), key)

    owner = normalized_owner(metadata_value(text, "Owner") or metadata_value(text, "Assignee"))
    if not owner:
        add_violation(violations, "owner", "missing Owner or Assignee metadata")
    if expected_owner and owner != normalized_owner(expected_owner):
        add_violation(violations, "owner_state", "spec owner and requested owner disagree", owner, normalized_owner(expected_owner))

    state_path = repo_root / "project-state.json"
    if state_path.exists():
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
            if commit_key(state.get("next_commit", "")) == key:
                state_owner = normalized_owner(str(state.get("next_commit_assignee", "")))
                if owner and state_owner != owner:
                    add_violation(violations, "owner_state", "spec owner and project state disagree", owner, state_owner)
        except (ValueError, json.JSONDecodeError):
            add_violation(violations, "project_state", "project-state.json is invalid")

    entry = protocol_entry(repo_root, key)
    if entry:
        title_line = text.splitlines()[0]
        spec_name_match = re.search(r"`([^`]+)`", title_line)
        spec_name = spec_name_match.group(1) if spec_name_match else ""
        if spec_name and entry[0] != spec_name:
            add_violation(violations, "protocol_name", "spec and protocol names disagree", spec_name, entry[0])
        if owner and normalized_owner(entry[1]) != owner:
            add_violation(violations, "protocol_owner", "spec and protocol owners disagree", owner, normalized_owner(entry[1]))
    else:
        add_violation(violations, "protocol_entry", f"{key} is missing from commit-protocol.md")

    primary_behavior = section(text, "Primary Behavior")
    if not primary_behavior:
        add_violation(violations, "primary_behavior", "missing Primary Behavior section")
    behavior_count = metadata_value(text, "Primary behavior count")
    if behavior_count != "1":
        add_violation(
            violations,
            "primary_behavior_count",
            "Primary behavior count must be exactly 1",
            behavior_count,
            "1",
        )
    behavior_items = re.findall(r"^\s*(?:[-*]|\d+\.)\s+", primary_behavior, re.MULTILINE)
    if len(behavior_items) > 1:
        add_violation(
            violations,
            "primary_behavior_structure",
            "Primary Behavior contains multiple list items; split independently testable outcomes",
            len(behavior_items),
            1,
        )
    semantic_fit = section(text, "Semantic Fit Review")
    for label in ("Atomic outcome", "Failure boundary", "Budget rationale"):
        if not re.search(
            rf"^\s*[-*]?\s*\*\*{re.escape(label)}:\*\*\s*\S",
            semantic_fit,
            re.MULTILINE,
        ):
            add_violation(
                violations,
                "semantic_fit_review",
                f"Semantic Fit Review is missing a non-empty '{label}' field",
            )

    budget = yaml_ints(section(text, "Execution Budget"), "execution_budget")
    for name, limit in LOCKED_BUDGET.items():
        value = budget.get(name)
        if value is None:
            add_violation(violations, name, f"missing execution_budget.{name}")
        elif value > limit:
            add_violation(violations, name, f"{name} exceeds locked maximum", value, limit)

    bootstrap = yaml_ints(section(text, "Execution Budget"), "bootstrap_exception")
    bootstrap_keys = yaml_keys(section(text, "Execution Budget"), "bootstrap_exception")
    for bootstrap_key in bootstrap_keys:
        if bootstrap_key not in BOOTSTRAP_EXCEPTION_FIELDS:
            add_violation(
                violations,
                "bootstrap_exception_field",
                f"unrecognized bootstrap_exception field: {bootstrap_key}",
            )
    for bootstrap_key, ceiling in GREENFIELD_BUDGET_CEILINGS.items():
        value = bootstrap.get(bootstrap_key)
        if value is not None and value > ceiling:
            add_violation(
                violations,
                "bootstrap_exception_ceiling",
                f"bootstrap_exception.{bootstrap_key} exceeds greenfield ceiling",
                value,
                ceiling,
            )

    files = changed_file_rows(text)
    file_limit = bootstrap.get("max_changed_files", LOCKED_BUDGET["max_changed_files"])
    if len(files) > file_limit:
        add_violation(violations, "max_changed_files", "changed-file plan exceeds limit", len(files), file_limit)
    for path in files:
        if any(char in path for char in "*?[]") or "related" in path.lower():
            add_violation(violations, "exact_file_paths", f"non-exact file entry: {path}")
    allowed_paths = owner_paths(repo_root, owner)
    if allowed_paths:
        universal, owned = allowed_paths
        for path in files:
            if not any(
                path == allowed or path.startswith(allowed)
                for allowed in [*universal, *owned]
            ):
                add_violation(
                    violations,
                    "file_ownership",
                    f"{owner} does not own planned file {path}",
                )

    entries = protocol_entries(repo_root)
    dependency_value = metadata_value(text, "Depends on")
    dependencies = dependency_keys(text)
    if not dependency_value:
        add_violation(violations, "dependencies", "missing Depends on metadata")
    elif (
        dependency_value.strip().lower() not in {"none", "n/a"}
        and not dependencies
    ):
        add_violation(
            violations,
            "dependency_format",
            "Depends on must contain concrete commit IDs or 'None'",
            dependency_value,
        )
    for dependency in dependencies:
        if dependency == key:
            add_violation(violations, "dependency_self", f"{key} cannot depend on itself")
        elif dependency not in entries:
            add_violation(
                violations,
                "dependency_missing",
                f"{dependency} is missing from commit-protocol.md",
            )

    context = section(text, "Context")
    primary_files = yaml_list(context, "primary_files")
    if len(primary_files) > LOCKED_BUDGET["max_primary_files"]:
        add_violation(
            violations, "max_primary_files", "primary-file plan exceeds limit",
            len(primary_files), LOCKED_BUDGET["max_primary_files"],
        )
    initial_context = yaml_list(context, "initial_context")
    if len(initial_context) > LOCKED_BUDGET["max_context_files"]:
        add_violation(
            violations, "max_context_files", "initial context exceeds limit",
            len(initial_context), LOCKED_BUDGET["max_context_files"],
        )

    estimate_match = re.search(r"^\*\*Estimated diff lines:\*\*\s*(\d+)\s*$", text, re.MULTILINE | re.IGNORECASE)
    if not estimate_match:
        add_violation(violations, "estimated_diff_lines", "missing Estimated diff lines metadata")
    else:
        estimate_limit = bootstrap.get(
            "max_estimated_diff_lines",
            LOCKED_BUDGET["max_estimated_diff_lines"],
        )
        estimate = int(estimate_match.group(1))
        if estimate > estimate_limit:
            add_violation(
                violations, "max_estimated_diff_lines", "estimated diff exceeds limit",
                estimate, estimate_limit,
            )

    required_sections = {
        "contract": "Contract",
        "semantic_fit_review": "Semantic Fit Review",
        "verification_command": "Verification Command",
        "environment_prerequisites": "Environment Prerequisites",
        "done_when": "Done When",
        "developer_test_checkpoint": "Developer Test Checkpoint",
        "not_in_commit": "Not In This Commit",
        "return_contract": "Return Contract",
    }
    for rule, heading_name in required_sections.items():
        if not section(text, heading_name):
            add_violation(violations, rule, f"missing {heading_name} section")
    if not (section(text, "Required Tests") or section(text, "Focused Tests")):
        add_violation(violations, "focused_tests", "missing Required Tests or Focused Tests section")

    milestone = (metadata_value(text, "Developer test milestone") or "").lower()
    checkpoint = section(text, "Developer Test Checkpoint")
    if milestone not in {"yes", "no"}:
        add_violation(
            violations,
            "developer_test_milestone",
            "Developer test milestone metadata must be yes or no",
            milestone or None,
        )
    elif milestone == "yes":
        for label in ("Ready now", "How to test", "Expected result", "Still incomplete"):
            if not re.search(rf"^\s*[-*]?\s*\*\*{re.escape(label)}:\*\*\s*\S", checkpoint, re.MULTILINE):
                add_violation(
                    violations,
                    "developer_test_checkpoint",
                    f"milestone checkpoint is missing a non-empty '{label}' field",
                )
    elif not re.search(r"^\s*[-*]?\s*\*\*Next milestone:\*\*\s*\S", checkpoint, re.MULTILINE):
        add_violation(
            violations,
            "developer_test_checkpoint",
            "non-milestone checkpoint must name the next milestone commit",
        )

    effective_budget = dict(budget)
    effective_budget.setdefault("max_total_tokens", DEFAULT_MAX_TOTAL_TOKENS)
    for bootstrap_key in GREENFIELD_BUDGET_CEILINGS:
        if bootstrap_key in bootstrap:
            effective_budget[bootstrap_key] = bootstrap[bootstrap_key]

    status = "valid" if not violations else "split_required"
    return {
        "status": status,
        "commit": key,
        "owner": owner,
        "budget": effective_budget,
        "dependencies": dependencies,
        "planned_changed_files": files,
        "violations": violations,
    }


def validate_pending_graph(repo_root: Path) -> dict[str, Any]:
    entries = protocol_entries(repo_root)
    pending = {
        key: entry
        for key, entry in entries.items()
        if "pending" in entry["status"] or "active" in entry["status"]
    }
    violations: list[dict[str, Any]] = []
    results: dict[str, dict[str, Any]] = {}
    graph: dict[str, list[str]] = {}

    for key, entry in sorted(pending.items(), key=lambda item: commit_order(item[0])):
        result = validate_commit_spec(repo_root, key, entry["owner"])
        results[key] = result
        if result["status"] != "valid":
            add_violation(
                violations,
                "pending_spec_invalid",
                f"{key} failed commit-spec validation",
                [item["rule"] for item in result["violations"]],
            )
        dependencies = result.get("dependencies", [])
        graph[key] = [dependency for dependency in dependencies if dependency in pending]
        for dependency in dependencies:
            if dependency in pending and commit_order(dependency) >= commit_order(key):
                add_violation(
                    violations,
                    "dependency_order",
                    f"{key} depends on non-earlier pending commit {dependency}",
                )

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str, path: list[str]) -> None:
        if node in visiting:
            cycle_start = path.index(node) if node in path else 0
            cycle = path[cycle_start:] + [node]
            add_violation(
                violations,
                "dependency_cycle",
                "pending dependency graph contains a cycle",
                cycle,
            )
            return
        if node in visited:
            return
        visiting.add(node)
        for dependency in graph.get(node, []):
            visit(dependency, path + [node])
        visiting.remove(node)
        visited.add(node)

    for key in graph:
        visit(key, [])

    return {
        "status": "valid" if not violations else "split_required",
        "pending_commits": sorted(pending, key=commit_order),
        "spec_results": results,
        "violations": violations,
    }


def require_valid_pending_graph(repo_root: Path) -> dict[str, Any]:
    result = validate_pending_graph(repo_root)
    if result["status"] != "valid":
        messages = "; ".join(item["message"] for item in result["violations"])
        raise ValueError(f"pending commit graph validation failed: {messages}")
    return result


def require_valid_commit_spec(
    repo_root: Path,
    commit: str | int,
    expected_owner: str | None = None,
) -> dict[str, Any]:
    result = validate_commit_spec(repo_root, commit, expected_owner)
    if result["status"] != "valid":
        messages = "; ".join(item["message"] for item in result["violations"])
        raise ValueError(f"commit spec validation failed: {messages}")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commit")
    parser.add_argument("--all-pending", action="store_true")
    parser.add_argument("--owner")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if args.all_pending:
        result = validate_pending_graph(REPO_ROOT)
    elif args.commit:
        result = validate_commit_spec(REPO_ROOT, args.commit, args.owner)
    else:
        parser.error("provide --commit or --all-pending")
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        subject = result.get("commit", "pending graph")
        print(f"{subject}: {result['status']}")
        for violation in result["violations"]:
            print(f"- {violation['rule']}: {violation['message']}")
    return 0 if result["status"] == "valid" else 1


if __name__ == "__main__":
    sys.exit(main())
