#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import direct_execution_lifecycle as lifecycle  # noqa: E402


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path
    (repo / "hooks").mkdir()
    (repo / "hooks" / "context_rules.json").write_text("{}", encoding="utf-8")
    (repo / "project-state.json").write_text(json.dumps({
        "next_commit": "48",
        "next_commit_assignee": "nova",
        "status": "phase-2-active",
    }), encoding="utf-8")
    specs = repo / "commit-specs"
    specs.mkdir()
    (specs / "commit-48.md").write_text(
        "## Files To Modify Or Add\n"
        "| File | Type | Purpose |\n|---|---|---|\n"
        "| `backend/app/services/rag_logistics.py` | edit | behavior |\n",
        encoding="utf-8",
    )
    return repo


def test_unrelated_read_does_not_activate(tmp_path):
    repo = _repo(tmp_path)
    with patch("direct_execution_lifecycle.prepare_direct") as prepare:
        allowed, message = lifecycle.ensure_direct_scope({
            "tool_name": "Read",
            "tool_input": {"file_path": "DECISIONS.md"},
        }, repo)
    assert allowed is True
    assert message is None
    prepare.assert_not_called()


def test_first_planned_read_activates_before_tool_runs(tmp_path):
    repo = _repo(tmp_path)

    def activate(*args, **kwargs):
        path = repo / ".context" / "telemetry" / "orchestrator-active.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({
            "commit": "C48",
            "status": "running",
            "execution_mode": "claude-direct",
        }), encoding="utf-8")

    with patch(
        "direct_execution_lifecycle.prepare_direct", side_effect=activate
    ) as prepare:
        allowed, message = lifecycle.ensure_direct_scope({
            "tool_name": "Read",
            "tool_input": {
                "file_path": str(repo / "backend/app/services/rag_logistics.py")
            },
        }, repo)

    assert allowed is True
    assert "activated C48" in message
    prepare.assert_called_once()


def test_existing_matching_scope_is_reused(tmp_path):
    repo = _repo(tmp_path)
    active = repo / ".context" / "telemetry" / "orchestrator-active.json"
    active.parent.mkdir(parents=True)
    active.write_text(json.dumps({
        "commit": "C48",
        "status": "running",
        "execution_mode": "claude-direct",
    }), encoding="utf-8")
    with patch("direct_execution_lifecycle.prepare_direct") as prepare:
        allowed, message = lifecycle.ensure_direct_scope({
            "tool_name": "Edit",
            "tool_input": {"file_path": "backend/app/services/rag_logistics.py"},
        }, repo)
    assert allowed is True
    assert message is None
    prepare.assert_not_called()


def test_activation_failure_blocks_implementation_tool(tmp_path):
    repo = _repo(tmp_path)
    with patch(
        "direct_execution_lifecycle.prepare_direct",
        side_effect=ValueError("preflight blocked"),
    ):
        allowed, message = lifecycle.ensure_direct_scope({
            "tool_name": "Edit",
            "tool_input": {"file_path": "backend/app/services/rag_logistics.py"},
        }, repo)
    assert allowed is False
    assert "preflight blocked" in message
