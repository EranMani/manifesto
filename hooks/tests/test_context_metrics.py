#!/usr/bin/env python3
"""Tests for hooks/context_metrics.py -- execution field and package truthiness."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import context_metrics as cm  # noqa: E402


_RESULTS = {
    "spec_validation": {"pass": True, "message": "ok"},
    "context_block": {"pass": True, "message": "ok"},
    "forbidden_paths": {"pass": True, "message": "ok"},
    "phase_budget": {"pass": True, "message": "ok", "counts": {}},
    "actual_scope": {"pass": True, "message": "ok", "counts": {}},
}


def test_build_metric_record_execution_field_claude_direct(tmp_path, monkeypatch):
    monkeypatch.setattr(cm, "REPO_ROOT", tmp_path)

    record = cm.build_metric_record(
        "33", "rex", None, _RESULTS, ["backend/app/main.py"], execution="claude-direct"
    )

    assert record["execution"] == "claude-direct"
    assert record["tokens"] is None


def test_build_metric_record_execution_field_defaults_to_unknown(tmp_path, monkeypatch):
    monkeypatch.setattr(cm, "REPO_ROOT", tmp_path)

    record = cm.build_metric_record("33", "rex", 1000, _RESULTS, [])

    assert record["execution"] == "unknown"


def test_build_metric_record_package_empty_when_no_data(tmp_path, monkeypatch):
    """No live package, no hooks telemetry -> package is {} (falsy), distinguishing
    'Not created (Claude-direct)' from any commit that actually built a package."""
    monkeypatch.setattr(cm, "REPO_ROOT", tmp_path)

    record = cm.build_metric_record(
        "33", "rex", None, _RESULTS, [], execution="claude-direct"
    )

    assert record["package"] == {}
    assert not record["package"]


def test_build_metric_record_package_populated_from_live_package(tmp_path, monkeypatch):
    monkeypatch.setattr(cm, "REPO_ROOT", tmp_path)

    live_package = {
        "files": [{"path": "backend/app/main.py", "read_strategy": "targeted excerpt"}],
        "excluded_candidates": ["backend/app/unused.py"],
        "expansion_triggers": [],
        "graph": {"source": "cache"},
        "budget": {
            "selected_files": 1,
            "estimated_selected_chars": 5000,
            "usable_chars_before_reserve": 10000,
        },
    }
    runs_dir = tmp_path / ".context" / "runs"
    runs_dir.mkdir(parents=True)
    (runs_dir / "C33-rex-live.json").write_text(json.dumps(live_package), encoding="utf-8")

    record = cm.build_metric_record(
        "33", "rex", 5000, _RESULTS, ["backend/app/main.py"], execution="delegated"
    )

    assert record["package"]
    assert record["package"]["selected_files"] == 1
    assert record["package"]["estimated_chars"] == 5000
    assert record["package"]["budget_utilization_percent"] == 50.0


def test_build_metric_record_persists_canonical_direct_evidence(tmp_path, monkeypatch):
    monkeypatch.setattr(cm, "REPO_ROOT", tmp_path)
    specs = tmp_path / "commit-specs"
    specs.mkdir()
    (specs / "commit-46.md").write_text(
        "## Files To Modify Or Add\n\n"
        "| File | Type | Purpose |\n|---|---|---|\n"
        "| `backend/app/example.py` | edit | Example |\n",
        encoding="utf-8",
    )
    telemetry = tmp_path / ".context" / "telemetry"
    telemetry.mkdir(parents=True)
    (telemetry / "C46-orchestrator.json").write_text(json.dumps({
        "schema_version": 2,
        "commit": "C46",
        "owner": "rex",
        "executor": "claude",
        "execution_mode": "claude-direct",
        "scope_kind": "execution",
        "capture_window": "full-execution",
        "status": "completed",
        "started_at": "2026-06-14T10:00:00+00:00",
        "ended_at": "2026-06-14T10:05:00+00:00",
        "tool_calls": 0,
        "read_paths": [],
        "write_paths": ["backend/app/example.py"],
        "searches": [],
        "commands": [],
    }), encoding="utf-8")

    record = cm.build_metric_record(
        "46", "rex", None, _RESULTS, ["backend/app/example.py"],
        execution="claude-direct",
    )

    assert record["identity"] == {
        "owner": "rex",
        "executor": "claude",
        "execution_mode": "claude-direct",
        "domain": "Unknown",
        "source": "spec-and-runtime",
    }
    assert record["evidence"]["planned_files"] == ["backend/app/example.py"]
    assert record["evidence"]["written_files"] == ["backend/app/example.py"]
    assert record["evidence"]["changed_files"] == ["backend/app/example.py"]
    assert record["evidence"]["coverage"]["planned_change_percent"] == 100.0
    assert record["scope"]["planned_read_percent"] == 0.0
    assert record["capture"]["status"] == "complete"
    assert record["capture"]["zero_is_measured"] is True


def test_execution_evidence_separates_preselected_support_from_expansion():
    scope, _ = cm._execution_evidence(
        ["backend/seed.py"],
        [
            "backend/seed.py",
            "backend/app/models/policy.py",
            "backend/app/unplanned.py",
        ],
        ["backend/seed.py"],
        "claude-direct",
        ["backend/seed.py", "backend/app/models/policy.py"],
    )

    assert scope["supporting_reads"] == ["backend/app/models/policy.py"]
    assert scope["expansion_reads"] == ["backend/app/unplanned.py"]


def test_migrate_metrics_marks_legacy_zero_as_not_measured(tmp_path):
    path = tmp_path / "CONTEXT_METRICS.json"
    path.write_text(json.dumps({
        "schema_version": 1,
        "records": [{
            "commit": "C41", "agent": "rex", "execution": "claude-direct",
            "telemetry": {
                "agent": {"status": "unavailable"},
                "orchestrator": {
                    "status": "available", "tool_calls": 0,
                    "read_paths": [], "write_paths": [],
                },
            },
            "boundaries": {"changed_files": ["backend/app/example.py"]},
        }],
    }), encoding="utf-8")

    migrated = cm.migrate_metrics(path, tmp_path)
    record = migrated["records"][0]

    assert record["record_schema_version"] == 2
    assert record["identity"]["executor"] == "claude"
    assert record["capture"]["status"] == "incomplete"
    assert record["capture"]["zero_is_measured"] is False
