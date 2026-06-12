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
