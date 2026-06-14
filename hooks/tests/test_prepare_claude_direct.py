#!/usr/bin/env python3

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from unittest.mock import patch


HOOKS_DIR = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures" / "context_repo"
sys.path.insert(0, str(HOOKS_DIR))

from context_engine import load_rules  # noqa: E402
from prepare_claude_direct import (  # noqa: E402
    DirectPreflightBlocked,
    prepare_direct,
)


VALIDATION = {
    "status": "valid",
    "budget": {
        "max_context_files": 6,
        "max_context_chars": 15000,
    },
}


def test_prepare_direct_writes_bounded_package_and_brief(tmp_path):
    root = tmp_path / "repo"
    shutil.copytree(FIXTURE_ROOT, root)
    rules = load_rules(HOOKS_DIR / "context_rules.json")

    with patch(
        "prepare_claude_direct.evaluate_direct",
        return_value={"proceed": True},
    ), patch(
        "prepare_claude_direct.require_valid_commit_spec",
        return_value=VALIDATION,
    ), patch(
        "prepare_claude_direct.initialize_execution_scope"
    ) as start_scope:
        package, package_path, brief_path, _ = prepare_direct(
            root, rules, "1", "aria"
        )

    assert package["mode"] == "claude-direct"
    assert package["executor"] == "claude"
    assert package["selection_policy"] == "deterministic-graph-v1"
    assert package["budget"]["selected_files"] <= 6
    assert package["budget"]["estimated_selected_chars"] <= 15000
    assert package_path.name == "C01-claude-direct.json"
    assert brief_path.name == "C01.md"
    brief = brief_path.read_text(encoding="utf-8")
    assert "Preselected Supporting Context" in brief
    assert "Do not scan directories" in brief
    assert not any(item["category"] == "worklog" for item in package["files"])
    start_scope.assert_called_once()
    assert start_scope.call_args.kwargs["package"] == package


def test_prepare_direct_preview_does_not_start_capture(tmp_path):
    root = tmp_path / "repo"
    shutil.copytree(FIXTURE_ROOT, root)
    rules = load_rules(HOOKS_DIR / "context_rules.json")

    with patch(
        "prepare_claude_direct.evaluate_direct",
        return_value={"proceed": True},
    ), patch(
        "prepare_claude_direct.require_valid_commit_spec",
        return_value=VALIDATION,
    ), patch(
        "prepare_claude_direct.initialize_execution_scope"
    ) as start_scope:
        prepare_direct(root, rules, "1", "aria", activate=False)

    start_scope.assert_not_called()


def test_prepare_direct_blocks_before_writing_artifacts(tmp_path):
    root = tmp_path / "repo"
    shutil.copytree(FIXTURE_ROOT, root)
    rules = load_rules(HOOKS_DIR / "context_rules.json")

    with patch(
        "prepare_claude_direct.evaluate_direct",
        return_value={"proceed": False, "violations": ["blocked"]},
    ):
        try:
            prepare_direct(root, rules, "1", "aria")
        except DirectPreflightBlocked:
            pass
        else:
            raise AssertionError("expected DirectPreflightBlocked")

    assert not (root / ".context" / "direct").exists()
    assert not (root / ".context" / "runs" / "C01-claude-direct.json").exists()


def test_execution_scope_persists_selected_paths(tmp_path):
    package = {
        "commit": "C46",
        "selection_policy": "deterministic-graph-v1",
        "budget": {"selected_files": 2, "estimated_selected_chars": 1000},
        "files": [
            {"path": "backend/seed.py", "category": "primary"},
            {"path": "backend/app/models/policy.py", "category": "contract"},
        ],
    }
    transcript = tmp_path / "session.jsonl"
    transcript.write_text("", encoding="utf-8")
    with patch.dict(
        "os.environ", {"CLAUDE_TRANSCRIPT_PATH": str(transcript)}
    ):
        from context_telemetry import initialize_execution_scope

        scope = initialize_execution_scope(
            "C46", "rex", tmp_path, package=package
        )

    assert scope["context_package"]["selected_paths"] == [
        "backend/seed.py",
        "backend/app/models/policy.py",
    ]
    assert scope["context_package"]["planned_paths"] == ["backend/seed.py"]
    persisted = json.loads(
        (
            tmp_path / ".context" / "telemetry" / "orchestrator-active.json"
        ).read_text(encoding="utf-8")
    )
    assert persisted["context_package"]["selection_policy"] == (
        "deterministic-graph-v1"
    )
