#!/usr/bin/env python3

from __future__ import annotations

import sys
from pathlib import Path


HOOKS_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = HOOKS_DIR.parent
sys.path.insert(0, str(HOOKS_DIR))

from context_engine import ContextPackageBuilder, load_rules  # noqa: E402
from validate_commit_spec import protocol_entries, validate_commit_spec  # noqa: E402


def test_pending_context_packages_fit_validated_budgets() -> None:
    rules = load_rules(HOOKS_DIR / "context_rules.json")
    builder = ContextPackageBuilder(
        REPO_ROOT,
        rules,
        graph_path=None,
        mode="preflight",
    )
    failures: list[str] = []
    prior_planned_paths: set[str] = set()

    for commit, entry in protocol_entries(REPO_ROOT).items():
        if entry["status"] != "pending":
            continue

        validation = validate_commit_spec(REPO_ROOT, commit, entry["owner"])
        assert validation["status"] == "valid", validation

        package = builder.build(commit[1:], entry["owner"])
        package_budget = package["budget"]
        validated_budget = validation["budget"]
        issues: list[str] = []

        if package["excluded_candidates"]:
            issues.append(
                f"{len(package['excluded_candidates'])} excluded candidate(s)"
            )
        unexpected_unresolved = sorted(
            item["path"]
            for item in package["unresolved"]
            if item["path"] not in prior_planned_paths
        )
        if unexpected_unresolved:
            issues.append(
                "unresolved path(s) not produced by an earlier pending commit: "
                + ", ".join(unexpected_unresolved)
            )
        if package_budget["selected_files"] > validated_budget["max_context_files"]:
            issues.append(
                f"{package_budget['selected_files']} files > "
                f"{validated_budget['max_context_files']}"
            )
        if (
            package_budget["estimated_selected_chars"]
            > validated_budget["max_context_chars"]
        ):
            issues.append(
                f"{package_budget['estimated_selected_chars']} chars > "
                f"{validated_budget['max_context_chars']}"
            )

        if issues:
            failures.append(f"{commit}: {', '.join(issues)}")

        prior_planned_paths.update(validation["planned_changed_files"])

    assert not failures, "\n".join(failures)
