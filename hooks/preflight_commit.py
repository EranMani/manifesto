"""Build, score, and persist a deterministic commit-readiness ("preflight") report.

Standalone hook script: reuses existing validators and the context engine to produce
a repeatable proceed/block report for a single commit. Independent of the delegation
pipeline (`prepare_agent_delegation.py`) -- it does not call, edit, or gate it.

Usage:
    python hooks/preflight_commit.py --commit C30 --agent adam [--json]
    python hooks/preflight_commit.py --direct --commit C33 --agent rex [--json]

Exposes `evaluate(repo_root, commit, agent) -> dict` returning the compact result
(after persisting the full diagnostics report as a side effect).

Exposes `evaluate_direct(repo_root, commit, owner) -> dict` for Claude-direct
execution: a lean, ephemeral readiness check (spec validity, this commit's
dependencies, ownership agreement, planned/forbidden files, verification command
presence). It performs no persistence, builds no context package, and never
renders the dashboard. `owner` is the commit's domain owner (e.g. "rex"), not
the executor -- Claude-direct execution and commit ownership are separate
concepts.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import validate_commit_spec as vcs  # noqa: E402
import context_engine  # noqa: E402


HARD_CATEGORY_POINTS: dict[str, int] = {
    "specification_validity": 15,
    "pending_graph_validity": 10,
    "ownership_match": 10,
    "scope_forbidden_compliance": 10,
    "context_package_integrity": 15,
    "verification_command_present": 10,
    "acceptance_criteria_present": 10,
    "dependencies_satisfied": 20,
}

ROLE_TO_DOMAIN = {
    "devops": "DevOps",
    "backend": "Backend",
    "frontend": "Frontend",
    "ai-engineer": "AI/ML",
    "orchestrator": "Orchestration",
}

ENV_TOOL_PATTERNS: dict[str, str] = {
    "docker": r"\bdocker\b",
    "npm": r"\bnpm\b",
    "node": r"\bnode\b",
    "pytest": r"\bpytest\b",
    "python": r"\bpython\b",
    "pwsh": r"\b(?:pwsh|powershell)\b",
    "ollama": r"\bollama\b",
    "psql": r"\b(?:psql|postgres)\b",
    "alembic": r"\balembic\b",
    "git": r"\bgit\b",
}

SHELL_BUILTINS = {"cd", "pushd", "popd", "set", "export"}


# ---------------------------------------------------------------------------
# Spec parsing helpers (built on top of validate_commit_spec helpers)
# ---------------------------------------------------------------------------


def _read_spec(repo_root: Path, commit: str) -> str:
    key = vcs.commit_key(commit)
    num = key[1:].lower()
    path = repo_root / "commit-specs" / f"commit-{num}.md"
    return path.read_text(encoding="utf-8")


def _goal_from_primary_behavior(text: str) -> str:
    block = vcs.section(text, "Primary Behavior")
    lines: list[str] = []
    for line in block.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            if lines:
                break
            continue
        lines.append(stripped)
    paragraph = " ".join(lines)
    match = re.search(r"(.*?\.)(\s|$)", paragraph)
    if match:
        return match.group(1).strip()
    return paragraph


def _files_from_table(text: str) -> list[dict[str, str]]:
    block = vcs.section(text, "Files To Modify Or Add")
    files: list[dict[str, str]] = []
    for line in block.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 2:
            continue
        path_cell = cells[0].strip("`").strip()
        type_cell = cells[1].strip().lower()
        if not path_cell or path_cell.lower() == "file":
            continue
        if set(path_cell) <= {"-"}:
            continue
        if type_cell in ("new", "add"):
            action = "add"
        elif type_cell == "edit":
            action = "edit"
        elif type_cell in ("delete", "remove"):
            action = "delete"
        else:
            continue
        files.append({"action": action, "path": path_cell})
    return files


def _section_text(text: str, heading: str) -> str:
    return vcs.section(text, heading).strip()


def _verification_command_block(text: str) -> str:
    block = vcs.section(text, "Verification Command")
    match = re.search(r"```(?:[a-zA-Z0-9]*)\n(.*?)```", block, re.DOTALL)
    if match:
        return match.group(1).strip()
    return block.strip()


# ---------------------------------------------------------------------------
# Hard category evaluators
# ---------------------------------------------------------------------------


def _eval_specification_validity(repo_root: Path, commit: str, agent: str) -> dict[str, Any]:
    result = vcs.validate_commit_spec(repo_root, commit, agent)
    passed = result.get("status") == "valid"
    return {"passed": passed, "evidence": result}


def _trim_pending_graph_evidence(evidence: dict[str, Any], key: str) -> dict[str, Any]:
    """Reduce validate_pending_graph's evidence to the active commit's entry.

    validate_pending_graph() returns a full validate_commit_spec result for every
    pending commit in spec_results, which balloons the persisted preflight report
    (tens of KB) without being relevant to any single commit's readiness.
    """
    spec_results = evidence.get("spec_results", {})
    return {
        "status": evidence.get("status"),
        "pending_commit_count": len(evidence.get("pending_commits", [])),
        "violation_count": len(evidence.get("violations", [])),
        "violations": evidence.get("violations", []),
        "active_commit_spec_result": spec_results.get(key),
    }


def _eval_pending_graph_validity(repo_root: Path, key: str) -> dict[str, Any]:
    result = vcs.validate_pending_graph(repo_root)
    passed = result.get("status") == "valid"
    return {"passed": passed, "evidence": _trim_pending_graph_evidence(result, key)}


def _eval_ownership_match(
    repo_root: Path, commit: str, spec_owner: str | None
) -> dict[str, Any]:
    key = vcs.commit_key(commit)
    entries = vcs.protocol_entries(repo_root)
    protocol_entry = entries.get(key)
    protocol_owner = vcs.normalized_owner(protocol_entry["owner"]) if protocol_entry else None

    state_path = repo_root / "project-state.json"
    next_assignee = None
    if state_path.exists():
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
            next_assignee = vcs.normalized_owner(state.get("next_commit_assignee"))
        except (json.JSONDecodeError, OSError):
            next_assignee = None

    norm_spec_owner = vcs.normalized_owner(spec_owner)
    passed = (
        norm_spec_owner is not None
        and norm_spec_owner == protocol_owner
        and norm_spec_owner == next_assignee
    )
    return {
        "passed": passed,
        "evidence": {
            "spec_owner": norm_spec_owner,
            "protocol_owner": protocol_owner,
            "next_commit_assignee": next_assignee,
        },
    }


def _path_matches_any(normalized: str, entries: list[str]) -> str | None:
    for entry in entries:
        entry_norm = entry.replace("\\", "/")
        if normalized == entry_norm or normalized.startswith(entry_norm):
            return entry
    return None


def _eval_scope_forbidden_compliance(
    repo_root: Path, files: list[dict[str, str]], owner: str | None, forbidden: list[str]
) -> dict[str, Any]:
    universal: list[str] = []
    domains: list[str] = []
    paths_result = vcs.owner_paths(repo_root, owner)
    if paths_result is not None:
        universal, domains = paths_result
    allowed = universal + domains

    bad_files: list[dict[str, str]] = []
    for f in files:
        path = f["path"]
        normalized = path.replace("\\", "/")

        forbidden_hit = _path_matches_any(normalized, forbidden)
        if forbidden_hit:
            bad_files.append({"path": path, "reason": f"matches forbidden entry '{forbidden_hit}'"})
            continue

        if allowed and not _path_matches_any(normalized, allowed):
            bad_files.append({"path": path, "reason": "does not match any owner_paths allowed entry"})

    passed = not bad_files
    return {"passed": passed, "evidence": {"bad_files": bad_files}}


def _eval_context_package_integrity(
    repo_root: Path, commit: str, agent: str, spec_validation_budget: dict[str, int]
) -> dict[str, Any]:
    try:
        rules = context_engine.load_rules(repo_root / "hooks" / "context_rules.json")
        builder = context_engine.ContextPackageBuilder(
            repo_root, rules, graph_path=None, mode="preflight"
        )
        package = builder.build(commit, agent)
    except Exception as exc:  # noqa: BLE001
        return {
            "passed": False,
            "evidence": {"error": f"{type(exc).__name__}: {exc}"},
            "package": None,
        }

    excluded = package.get("excluded_candidates") or []
    unresolved = package.get("unresolved") or []
    package_budget = package.get("budget") or {}

    issues: list[str] = []
    if excluded:
        issues.append(f"excluded_candidates non-empty ({len(excluded)} items)")
    if unresolved:
        issues.append(f"unresolved non-empty ({len(unresolved)} items)")

    total_files = int(package_budget.get("selected_files", 0))
    total_chars = int(package_budget.get("estimated_selected_chars", 0))

    max_files = spec_validation_budget.get("max_context_files")
    max_chars = spec_validation_budget.get("max_context_chars")

    if isinstance(max_files, int) and total_files > max_files:
        issues.append(f"selected files {total_files} exceed budget max_context_files {max_files}")
    if isinstance(max_chars, int) and total_chars > max_chars:
        issues.append(f"selected chars {total_chars} exceed budget max_context_chars {max_chars}")

    passed = not issues
    return {
        "passed": passed,
        "evidence": {"issues": issues, "total_files": total_files, "total_chars": total_chars},
        "package": package,
    }


def _eval_verification_command_present(verification_block: str) -> dict[str, Any]:
    if not verification_block:
        return {"passed": False, "evidence": {"reason": "missing or empty Verification Command section"}}

    if re.fullmatch(r"<[^>]*>", verification_block) or "TODO" in verification_block or "*" in verification_block:
        return {"passed": False, "evidence": {"reason": "placeholder or wildcard only"}}

    if "<" in verification_block and ">" in verification_block:
        return {"passed": False, "evidence": {"reason": "contains placeholder tokens"}}

    return {"passed": True, "evidence": {"command": verification_block}}


def _eval_acceptance_criteria_present(text: str) -> dict[str, Any]:
    done_when = _section_text(text, "Done When")
    focused_tests = _section_text(text, "Focused Tests")
    required_tests = _section_text(text, "Required Tests")

    has_done_when = bool(done_when)
    has_tests = bool(focused_tests) or bool(required_tests)

    passed = has_done_when and has_tests
    return {
        "passed": passed,
        "evidence": {
            "done_when_present": has_done_when,
            "focused_tests_present": bool(focused_tests),
            "required_tests_present": bool(required_tests),
        },
    }


def _eval_dependencies_satisfied(repo_root: Path, dependencies: list[str]) -> dict[str, Any]:
    if not dependencies:
        return {"passed": True, "evidence": {"dependencies": [], "missing": []}}

    entries = vcs.protocol_entries(repo_root)
    missing = []
    for dep in dependencies:
        key = vcs.commit_key(dep)
        entry = entries.get(key)
        status = (entry or {}).get("status", "").strip().lower()
        if status not in ("done", "✅ done") and not status.startswith("✅"):
            missing.append({"commit": key, "status": status or "missing"})

    passed = not missing
    return {"passed": passed, "evidence": {"dependencies": dependencies, "missing": missing}}


# ---------------------------------------------------------------------------
# Non-blocking readiness deductions
# ---------------------------------------------------------------------------


def _deduction_expansion_warnings(package: dict[str, Any] | None) -> tuple[int, list[str]]:
    if not package:
        return 0, []
    triggers = package.get("expansion_triggers") or []
    if not triggers:
        return 0, []
    points = min(5 * len(triggers), 10)
    warnings = [f"Context expansion warning: {trigger}" for trigger in triggers]
    return points, warnings


def _deduction_environment_prerequisites(text: str) -> tuple[int, list[str]]:
    block = _section_text(text, "Environment Prerequisites")
    if not block:
        return 0, []

    found_missing: list[str] = []
    for tool, pattern in ENV_TOOL_PATTERNS.items():
        check_name = "pwsh" if tool == "pwsh" else ("psql" if tool == "psql" else tool)
        if re.search(pattern, block, re.IGNORECASE):
            if shutil.which(check_name) is None:
                found_missing.append(tool)

    if not found_missing:
        return 0, []

    points = min(5 * len(found_missing), 10)
    warnings = [
        f"Environment prerequisite tooling unavailable: '{tool}' not found on PATH"
        for tool in found_missing
    ]
    return points, warnings


def _deduction_dependency_artifacts(repo_root: Path, dependencies: list[str]) -> tuple[int, list[str]]:
    missing_paths: list[tuple[str, str]] = []
    for dep in dependencies:
        key = vcs.commit_key(dep)
        num = key[1:].lower()
        spec_path = repo_root / "commit-specs" / f"commit-{num}.md"
        if not spec_path.exists():
            continue
        try:
            dep_text = spec_path.read_text(encoding="utf-8")
        except OSError:
            continue
        for f in _files_from_table(dep_text):
            if f["action"] in ("add", "edit"):
                target = repo_root / f["path"]
                if not target.exists():
                    missing_paths.append((key, f["path"]))

    if not missing_paths:
        return 0, []

    points = min(5 * len(missing_paths), 10)
    warnings = [
        f"Dependency artifact missing: {dep} expects '{path}' but it does not exist"
        for dep, path in missing_paths
    ]
    return points, warnings


def _resolve_host_executable(verification_block: str) -> str | None:
    if not verification_block:
        return None

    statements = re.split(r"[;\n]", verification_block)
    statements = [s.strip() for s in statements if s.strip()]
    if not statements:
        return None

    while len(statements) > 1:
        first_token = statements[0].split()[0] if statements[0].split() else ""
        first_token_lower = first_token.lower()
        if first_token_lower in SHELL_BUILTINS or re.match(r"^\$env:", statements[0], re.IGNORECASE):
            statements.pop(0)
        else:
            break

    statement = statements[-1]
    tokens = statement.split()
    if not tokens:
        return None

    if len(tokens) >= 2 and tokens[0] == "docker" and tokens[1] == "compose":
        return "__docker_compose__"
    if tokens[0] == "docker-compose":
        return "__docker_compose__"

    first = tokens[0]
    first_lower = first.lower()
    if first_lower in ("powershell", "pwsh", "python", "pytest", "npm"):
        return first_lower

    if first_lower.endswith(".ps1"):
        return "pwsh"

    stripped = re.sub(r"^(\./|\.\\)", "", first)
    return stripped


def _deduction_verification_tool_availability(verification_block: str) -> tuple[int, list[str]]:
    executable = _resolve_host_executable(verification_block)
    if executable is None:
        return 0, []

    if executable == "__docker_compose__":
        available = shutil.which("docker") is not None or shutil.which("docker-compose") is not None
        name = "docker/docker-compose"
    else:
        available = shutil.which(executable) is not None
        name = executable

    if available:
        return 0, []

    return 10, [f"Verification tool unavailable: '{name}' not found on PATH"]


# ---------------------------------------------------------------------------
# Main evaluation
# ---------------------------------------------------------------------------


def _build_owner_info(repo_root: Path, agent: str) -> dict[str, str]:
    config_path = repo_root / "hooks" / "agent-config.json"
    name = agent
    domain = ""
    if config_path.exists():
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            config = {}
        for entry in (config.get("agents") or {}).values():
            if str(entry.get("name", "")).lower() == agent.lower():
                name = entry.get("name", agent)
                role = entry.get("role", "")
                domain = ROLE_TO_DOMAIN.get(role, role)
                break
    return {"id": agent, "name": name, "domain": domain}


VIOLATION_MESSAGES = {
    "specification_validity": "Commit specification or its validation failed (validate_commit_spec status != 'valid'). Repair the spec until validate_commit_spec reports 'valid'.",
    "pending_graph_validity": "Pending commit dependency graph is invalid (validate_pending_graph status != 'valid'). Resolve the reported graph violations.",
    "ownership_match": "Ownership mismatch between the spec's Owner field, commit-protocol.md, and project-state.json next_commit_assignee. Align all three to the same owner.",
    "scope_forbidden_compliance": "One or more planned files fail owner_paths or match a forbidden entry. Remove or reassign the offending files.",
    "context_package_integrity": "Context package build failed, or has non-empty excluded_candidates/unresolved, or exceeds the context budget. Fix the context package or rules.",
    "verification_command_present": "Verification Command section is missing, empty, or contains only placeholders/wildcards. Add a concrete, runnable verification command.",
    "acceptance_criteria_present": "Done When section, or both Focused Tests and Required Tests sections, are missing or empty. Add concrete acceptance criteria and tests.",
    "dependencies_satisfied": "One or more 'Depends on' commits are not marked done in commit-protocol.md. Complete and mark those dependencies done first.",
}


def evaluate_direct(repo_root: Path, commit: str, owner: str) -> dict[str, Any]:
    """Lean Claude-direct readiness check.

    Validates only the active spec, this commit's own dependencies (not the
    full pending graph), ownership agreement, planned/forbidden files, and
    verification command presence. Returns an ephemeral result -- no
    `.context/preflight/*.json`, no dashboard render. The caller may then use
    `prepare_claude_direct.py` to build the deterministic execution package.
    """
    repo_root = Path(repo_root)
    key = vcs.commit_key(commit)
    spec_text = _read_spec(repo_root, commit)

    spec_owner = vcs.metadata_value(spec_text, "Owner")
    dependencies = vcs.dependency_keys(spec_text)
    files = _files_from_table(spec_text)
    verification_block = _verification_command_block(spec_text)

    forbidden_block = vcs.section(spec_text, "Context")
    forbidden = vcs.yaml_list(forbidden_block, "forbidden")

    checks = {
        "specification_validity": _eval_specification_validity(repo_root, commit, owner),
        "dependencies_satisfied": _eval_dependencies_satisfied(repo_root, dependencies),
        "ownership_match": _eval_ownership_match(repo_root, commit, spec_owner),
        "scope_forbidden_compliance": _eval_scope_forbidden_compliance(repo_root, files, spec_owner, forbidden),
        "verification_command_present": _eval_verification_command_present(verification_block),
    }

    violations: list[str] = []
    for cat_name, result in checks.items():
        if not result["passed"]:
            violations.append(f"{cat_name}: {VIOLATION_MESSAGES[cat_name]}")

    return {
        "commit": key,
        "owner": owner,
        "status": "ready" if not violations else "blocked",
        "proceed": not violations,
        "violations": violations,
    }


def evaluate(repo_root: Path, commit: str, agent: str) -> dict[str, Any]:
    repo_root = Path(repo_root)
    key = vcs.commit_key(commit)
    spec_text = _read_spec(repo_root, commit)

    spec_owner = vcs.metadata_value(spec_text, "Owner")
    dependencies = vcs.dependency_keys(spec_text)
    files = _files_from_table(spec_text)
    goal = _goal_from_primary_behavior(spec_text)
    verification_block = _verification_command_block(spec_text)

    forbidden_block = vcs.section(spec_text, "Context")
    forbidden = vcs.yaml_list(forbidden_block, "forbidden")

    # --- Hard categories ---
    spec_validity = _eval_specification_validity(repo_root, commit, agent)
    graph_validity = _eval_pending_graph_validity(repo_root, key)
    ownership = _eval_ownership_match(repo_root, commit, spec_owner)
    scope_compliance = _eval_scope_forbidden_compliance(repo_root, files, spec_owner, forbidden)
    spec_validation_budget = (spec_validity["evidence"] or {}).get("budget") or {}
    context_integrity = _eval_context_package_integrity(repo_root, commit, agent, spec_validation_budget)
    verification_present = _eval_verification_command_present(verification_block)
    acceptance_present = _eval_acceptance_criteria_present(spec_text)
    dependencies_satisfied = _eval_dependencies_satisfied(repo_root, dependencies)

    categories = {
        "specification_validity": spec_validity,
        "pending_graph_validity": graph_validity,
        "ownership_match": ownership,
        "scope_forbidden_compliance": scope_compliance,
        "context_package_integrity": context_integrity,
        "verification_command_present": verification_present,
        "acceptance_criteria_present": acceptance_present,
        "dependencies_satisfied": dependencies_satisfied,
    }

    blocking_violations: list[str] = []
    category_breakdown: dict[str, Any] = {}
    hard_points = 0

    for cat_name, points in HARD_CATEGORY_POINTS.items():
        result = categories[cat_name]
        passed = result["passed"]
        awarded = points if passed else 0
        hard_points += awarded
        category_breakdown[cat_name] = {
            "points_awarded": awarded,
            "points_possible": points,
            "passed": passed,
            "evidence": result["evidence"],
        }
        if not passed:
            blocking_violations.append(f"{cat_name}: {VIOLATION_MESSAGES[cat_name]}")

    # --- Non-blocking readiness deductions ---
    package = context_integrity.get("package")

    exp_points, exp_warnings = _deduction_expansion_warnings(package)
    env_points, env_warnings = _deduction_environment_prerequisites(spec_text)
    dep_points, dep_warnings = _deduction_dependency_artifacts(repo_root, dependencies)
    verify_points, verify_warnings = _deduction_verification_tool_availability(verification_block)

    deductions = {
        "context_expansion_warnings": {"points": exp_points, "warnings": exp_warnings},
        "environment_prerequisite_tooling": {"points": env_points, "warnings": env_warnings},
        "dependency_artifact_existence": {"points": dep_points, "warnings": dep_warnings},
        "verification_tool_availability": {"points": verify_points, "warnings": verify_warnings},
    }

    total_deductions = exp_points + env_points + dep_points + verify_points
    score = max(0, hard_points - total_deductions)

    warnings: list[str] = []
    for d in deductions.values():
        warnings.extend(d["warnings"])

    proceed = score >= 80 and not blocking_violations
    decision_required = not proceed

    owner_info = _build_owner_info(repo_root, agent)

    report_path_rel = f".context/preflight/{key}.json"
    report_path_abs = repo_root / ".context" / "preflight" / f"{key}.json"

    compact = {
        "commit": key,
        "score": score,
        "owner": owner_info,
        "goal": goal,
        "files": files,
        "blocking_violations": blocking_violations,
        "warnings": warnings,
        "decision_required": decision_required,
        "proceed": proceed,
        "report_path": report_path_rel,
    }

    full_report = {
        "compact": compact,
        "hard_points": hard_points,
        "total_deductions": total_deductions,
        "categories": category_breakdown,
        "deductions": deductions,
        "raw_validators": {
            "validate_commit_spec": spec_validity["evidence"],
            "validate_pending_graph": graph_validity["evidence"],
        },
        "context_package": package,
        "spec_owner": spec_owner,
        "dependencies": dependencies,
        "verification_command": verification_block,
    }

    report_path_abs.parent.mkdir(parents=True, exist_ok=True)
    report_path_abs.write_text(json.dumps(full_report, indent=2, sort_keys=True), encoding="utf-8")

    return compact


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _render_human(result: dict[str, Any]) -> str:
    lines = []
    status = "READY" if result["proceed"] else "BLOCKED"
    lines.append(f"{result['commit']} PREFLIGHT: {status} ({result['score']}/100)")
    lines.append("")
    owner = result["owner"]
    lines.append(f"Owner: {owner['name']} ({owner['domain']})")
    lines.append(f"Goal: {result['goal']}")
    lines.append("")
    lines.append("Files:")
    for f in result["files"]:
        action = f["action"].capitalize()
        lines.append(f"- {action}: {f['path']}")
    lines.append("")
    if result["blocking_violations"]:
        lines.append("Blocking violations:")
        for v in result["blocking_violations"]:
            lines.append(f"- {v}")
        lines.append("")
    lines.append("Warnings:")
    if result["warnings"]:
        for w in result["warnings"]:
            lines.append(f"- {w}")
    else:
        lines.append("- None.")
    lines.append(f"- Decision required: {'Yes' if result['decision_required'] else 'No'}")
    lines.append("")
    lines.append(f"Proceed? {'yes' if result['proceed'] else 'no'}")
    lines.append(f"Report: {result['report_path']}")
    return "\n".join(lines)


def _render_human_direct(result: dict[str, Any]) -> str:
    lines = []
    lines.append(f"{result['commit']} PREFLIGHT: {result['status'].upper()}")
    lines.append("")
    lines.append(f"Owner: {result['owner']}")
    lines.append("")
    if result["violations"]:
        lines.append("Violations:")
        for v in result["violations"]:
            lines.append(f"- {v}")
    else:
        lines.append("Violations: None.")
    lines.append("")
    lines.append(f"Proceed? {'yes' if result['proceed'] else 'no'}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build, score, and persist a commit preflight report.")
    parser.add_argument("--commit", required=True, help="Commit ID, e.g. C30")
    parser.add_argument("--agent", required=True, help="Agent id, e.g. adam. For --direct, the commit owner.")
    parser.add_argument("--json", action="store_true", help="Print compact JSON instead of human-readable text")
    parser.add_argument(
        "--direct", action="store_true",
        help="Run the lean Claude-direct readiness check (ephemeral, no persistence "
             "or dashboard render) instead of the full scored preflight.",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent

    if args.direct:
        result = evaluate_direct(repo_root, args.commit, args.agent)
        if args.json:
            print(json.dumps(result))
        else:
            print(_render_human_direct(result))
        return 0 if result["proceed"] else 1

    result = evaluate(repo_root, args.commit, args.agent)

    if args.json:
        print(json.dumps(result))
    else:
        print(_render_human(result))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
