#!/usr/bin/env python3
"""Tests for hooks/constraint_dashboard.py -- Claude-direct vs delegated rendering."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import constraint_dashboard as cd  # noqa: E402


# ---------------------------------------------------------------------------
# _package_cell
# ---------------------------------------------------------------------------


def test_package_cell_claude_direct_not_created():
    assert "Not created (Claude-direct)" in cd._package_cell({}, "claude-direct")


def test_package_cell_claude_direct_legacy_preview():
    pkg = {"budget_utilization_percent": None}
    assert "Legacy preview package (unused)" in cd._package_cell(pkg, "claude-direct")


def test_package_cell_delegated_with_data():
    pkg = {"selected_files": 4, "estimated_chars": 14889}
    rendered = cd._package_cell(pkg, "delegated")
    assert "4" in rendered
    assert "14,889" in rendered


def test_package_cell_delegated_unknown_falls_back():
    rendered = cd._package_cell({}, "delegated")
    assert "Unknown" in rendered


# ---------------------------------------------------------------------------
# _claude_direct_orch_cell
# ---------------------------------------------------------------------------


def test_claude_direct_orch_cell_not_tracked_when_missing():
    assert "Not tracked" in cd._claude_direct_orch_cell(None)


def test_claude_direct_orch_cell_not_tracked_when_unavailable():
    assert "Not tracked" in cd._claude_direct_orch_cell({"status": "unavailable"})


def test_claude_direct_orch_cell_renders_measured_scope():
    scope = {"status": "available", "tool_calls": 5}
    rendered = cd._claude_direct_orch_cell(scope)
    assert "Not tracked" not in rendered
    assert "5" in rendered


# ---------------------------------------------------------------------------
# _preflight_detail_html -- budget nesting fix
# ---------------------------------------------------------------------------


def test_preflight_detail_html_reads_nested_budget():
    entry = {
        "valid": True,
        "report": {
            "compact": {"proceed": True, "score": 100, "blocking_violations": []},
            "context_package": {
                "budget": {"selected_files": 3, "estimated_selected_chars": 11094},
            },
            "dependencies": [],
            "verification_command": "pytest -q",
        },
    }
    html_out = cd._preflight_detail_html("C30", entry)
    assert "3 files selected" in html_out
    assert "11094 estimated chars" in html_out


def test_preflight_detail_html_handles_missing_context_package():
    entry = {
        "valid": True,
        "report": {
            "compact": {"proceed": True, "score": 100, "blocking_violations": []},
            "dependencies": [],
            "verification_command": "pytest -q",
        },
    }
    html_out = cd._preflight_detail_html("C30", entry)
    assert "No context package recorded." in html_out


# ---------------------------------------------------------------------------
# render_dashboard -- metric_rows claude-direct vs delegated/unknown
# ---------------------------------------------------------------------------


def _write_metrics(repo: Path, records: list[dict]) -> None:
    (repo / "CONTEXT_METRICS.json").write_text(
        json.dumps({"schema_version": 1, "records": records}), encoding="utf-8"
    )


def test_render_dashboard_claude_direct_row_not_created(tmp_path):
    record = {
        "commit": "C30",
        "agent": "claude",
        "execution": "claude-direct",
        "tokens": None,
        "package": {},
        "telemetry": {
            "agent": {"status": "unavailable"},
            "orchestrator": {"status": "unavailable"},
        },
        "usage": {},
        "boundaries": {"forbidden_clean": True, "changed_files": []},
        "result": "PASS",
    }
    _write_metrics(tmp_path, [record])

    out_path = tmp_path / "constraint-dashboard.html"
    cd.render_dashboard(tmp_path, output_path=out_path)
    html_out = out_path.read_text(encoding="utf-8")

    assert "Not created (Claude-direct)" in html_out
    assert "Not delegated" in html_out
    assert "Not tracked" in html_out


def test_render_dashboard_legacy_preview_package_label(tmp_path):
    record = {
        "commit": "C29",
        "agent": "claude",
        "execution": "claude-direct",
        "tokens": None,
        "package": {"budget_utilization_percent": None},
        "telemetry": {
            "agent": {"status": "unavailable"},
            "orchestrator": {"status": "unavailable"},
        },
        "usage": {},
        "boundaries": {"forbidden_clean": True, "changed_files": []},
        "result": "PASS",
    }
    _write_metrics(tmp_path, [record])

    out_path = tmp_path / "constraint-dashboard.html"
    cd.render_dashboard(tmp_path, output_path=out_path)
    html_out = out_path.read_text(encoding="utf-8")

    assert "Legacy preview package (unused)" in html_out


def test_render_dashboard_delegated_row_shows_tokens_and_package(tmp_path):
    record = {
        "commit": "C28",
        "agent": "nova",
        "execution": "delegated",
        "tokens": 348889,
        "package": {"selected_files": 5, "estimated_chars": 20000},
        "telemetry": {
            "agent": {"status": "unavailable"},
            "orchestrator": {"status": "unavailable"},
        },
        "usage": {"selected_files_read": 3, "selected_utilization_percent": 60.0},
        "boundaries": {"forbidden_clean": True, "changed_files": []},
        "result": "PASS",
    }
    _write_metrics(tmp_path, [record])

    out_path = tmp_path / "constraint-dashboard.html"
    cd.render_dashboard(tmp_path, output_path=out_path)
    html_out = out_path.read_text(encoding="utf-8")

    assert "348889" in html_out
    assert "5" in html_out
    assert "20,000" in html_out


def test_render_dashboard_unknown_execution_treated_as_delegated(tmp_path):
    """Legacy records without an 'execution' field default to 'unknown' and render
    on the normal/delegated path, not the Claude-direct path."""
    record = {
        "commit": "C24",
        "agent": "nova",
        "tokens": 37486,
        "package": {"selected_files": 2, "estimated_chars": 5000},
        "telemetry": {
            "agent": {"status": "unavailable"},
            "orchestrator": {"status": "unavailable"},
        },
        "usage": {},
        "boundaries": {"forbidden_clean": True, "changed_files": []},
        "result": "PASS",
    }
    _write_metrics(tmp_path, [record])

    out_path = tmp_path / "constraint-dashboard.html"
    cd.render_dashboard(tmp_path, output_path=out_path)
    html_out = out_path.read_text(encoding="utf-8")

    assert "37486" in html_out
    assert "Not created (Claude-direct)" not in html_out
