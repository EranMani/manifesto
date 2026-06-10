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


def commit_key(value: str | int) -> str:
    raw = str(value).strip().upper()
    if raw.startswith("C"):
        raw = raw[1:]
    if not raw.isdigit():
        raise ValueError(f"commit identifier must be an integer, got {value!r}")
    return f"C{int(raw):02d}"


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


def protocol_entry(repo_root: Path, key: str) -> tuple[str, str] | None:
    path = repo_root / "commit-protocol.md"
    if not path.exists():
        return None
    number = str(int(key[1:]))
    for line in path.read_text(encoding="utf-8").splitlines():
        cells = [cell.strip() for cell in line.split("|") if cell.strip()]
        if len(cells) >= 3 and cells[0] in {number, key[1:]}:
            return cells[1], cells[2].lower()
    return None


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

    spec_path = repo_root / "commit-specs" / f"commit-{key[1:]}.md"
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

    if not section(text, "Primary Behavior"):
        add_violation(violations, "primary_behavior", "missing Primary Behavior section")

    budget = yaml_ints(section(text, "Execution Budget"), "execution_budget")
    for name, limit in LOCKED_BUDGET.items():
        value = budget.get(name)
        if value is None:
            add_violation(violations, name, f"missing execution_budget.{name}")
        elif value > limit:
            add_violation(violations, name, f"{name} exceeds locked maximum", value, limit)

    bootstrap = yaml_ints(section(text, "Execution Budget"), "bootstrap_exception")
    files = changed_file_rows(text)
    file_limit = bootstrap.get("max_changed_files", LOCKED_BUDGET["max_changed_files"])
    if len(files) > file_limit:
        add_violation(violations, "max_changed_files", "changed-file plan exceeds limit", len(files), file_limit)
    for path in files:
        if any(char in path for char in "*?[]") or "related" in path.lower():
            add_violation(violations, "exact_file_paths", f"non-exact file entry: {path}")

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
        "verification_command": "Verification Command",
        "environment_prerequisites": "Environment Prerequisites",
        "not_in_commit": "Not In This Commit",
    }
    for rule, heading_name in required_sections.items():
        if not section(text, heading_name):
            add_violation(violations, rule, f"missing {heading_name} section")
    if not (section(text, "Required Tests") or section(text, "Focused Tests")):
        add_violation(violations, "focused_tests", "missing Required Tests or Focused Tests section")

    status = "valid" if not violations else "split_required"
    return {
        "status": status,
        "commit": key,
        "owner": owner,
        "budget": budget,
        "planned_changed_files": files,
        "violations": violations,
    }


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
    parser.add_argument("--commit", required=True)
    parser.add_argument("--owner")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = validate_commit_spec(REPO_ROOT, args.commit, args.owner)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"{result['commit']}: {result['status']}")
        for violation in result["violations"]:
            print(f"- {violation['rule']}: {violation['message']}")
    return 0 if result["status"] == "valid" else 1


if __name__ == "__main__":
    sys.exit(main())
