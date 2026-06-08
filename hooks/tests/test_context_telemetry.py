#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


HOOKS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HOOKS_DIR))

import context_telemetry  # noqa: E402
import context_metrics  # noqa: E402
from constraint_dashboard import render_dashboard  # noqa: E402
from context_metrics import upsert_metric  # noqa: E402
from tool_cap_start import normalize_agent_name  # noqa: E402


class ContextTelemetryTests(unittest.TestCase):
    def test_records_selected_reads_and_expansions(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            active = root / ".context" / "telemetry" / "active.json"
            cap = root / "hooks" / "tool_cap.json"
            cap.parent.mkdir(parents=True)
            package = {
                "commit": "C24",
                "agent": "rex",
                "files": [
                    {
                        "path": "backend/app/core/config.py",
                        "category": "primary",
                        "read_strategy": "full file",
                    }
                ],
                "forbidden_edits": ["frontend/"],
                "budget": {
                    "selected_files": 1,
                    "estimated_selected_chars": 900,
                    "usable_chars_before_reserve": 24000,
                },
                "excluded_candidates": [],
                "expansion_triggers": [],
                "graph": {"source": "cache"},
            }
            context_telemetry.initialize_telemetry(package, root)
            cap.write_text(
                json.dumps({
                    "active": True,
                    "agent": "rex",
                    "count": 0,
                    "limit": 25,
                }),
                encoding="utf-8",
            )
            with (
                patch.object(context_telemetry, "REPO_ROOT", root),
                patch.object(context_telemetry, "ACTIVE_PATH", active),
            ):
                context_telemetry.record_tool_event({
                    "tool_name": "Read",
                    "tool_input": {"file_path": str(root / "backend/app/core/config.py")},
                })
                context_telemetry.record_tool_event({
                    "tool_name": "Grep",
                    "tool_input": {"path": "backend/app", "pattern": "Settings"},
                })
                final = context_telemetry.finalize_telemetry()

            self.assertEqual(final["tools"]["reads"], 1)
            self.assertEqual(final["tools"]["searches"], 1)
            self.assertEqual(
                final["selected_read_paths"],
                ["backend/app/core/config.py"],
            )
            self.assertEqual(final["outside_read_paths"], ["backend/app"])

    def test_builds_commit_metric_from_run_telemetry(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            telemetry_path = root / ".context" / "telemetry" / "C24-rex.json"
            package_path = root / ".context" / "runs" / "C24-rex-live.json"
            telemetry_path.parent.mkdir(parents=True)
            package_path.parent.mkdir(parents=True)
            telemetry_path.write_text(json.dumps({
                "status": "completed",
                "package": {
                    "selected_files": 2,
                    "estimated_chars": 1000,
                    "usable_chars": 24000,
                },
                "tools": {"total": 5, "reads": 2, "searches": 1, "writes": 1},
                "selected_read_paths": ["a.py"],
                "outside_read_paths": ["b.py"],
            }), encoding="utf-8")
            package_path.write_text("{}", encoding="utf-8")
            results = {
                "context_block": {"pass": True},
                "forbidden_paths": {"pass": True},
                "phase_budget": {"pass": True},
            }
            with patch.object(context_metrics, "REPO_ROOT", root):
                record = context_metrics.build_metric_record(
                    "24",
                    "rex",
                    20000,
                    results,
                    ["a.py"],
                )
            self.assertEqual(record["usage"]["selected_utilization_percent"], 50.0)
            self.assertEqual(record["usage"]["expansions"], 1)
            self.assertTrue(record["boundaries"]["forbidden_clean"])

    def test_agent_aliases_match_live_package_ids(self) -> None:
        self.assertEqual(normalize_agent_name("backend"), "rex")
        self.assertEqual(normalize_agent_name("frontend"), "aria")
        self.assertEqual(normalize_agent_name("ai-engineer"), "nova")


class ConstraintDashboardTests(unittest.TestCase):
    def test_renders_phase_b_metrics_and_prepared_package(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "CONSTRAINT_LOG.md").write_text(
                "| Date | Commit | Agent | Tokens | Context | Forbidden | Budget | Result |\n"
                "|---|---|---|---|---|---|---|---|\n"
                "| 2026-06-08 | C24 | rex | 20,000 | PASS | PASS | PASS | PASS |\n",
                encoding="utf-8",
            )
            metrics_path = root / "CONTEXT_METRICS.json"
            metrics_path.write_text(
                json.dumps({"schema_version": 1, "records": []}),
                encoding="utf-8",
            )
            upsert_metric({
                "date": "2026-06-08",
                "commit": "C24",
                "agent": "rex",
                "tokens": 20000,
                "package": {"selected_files": 9, "estimated_chars": 19000},
                "usage": {
                    "selected_files_read": 7,
                    "selected_utilization_percent": 77.8,
                    "searches": 1,
                    "expansions": 0,
                },
                "boundaries": {"forbidden_clean": True},
                "result": "PASS",
            }, metrics_path)
            active = root / ".context" / "telemetry" / "active.json"
            active.parent.mkdir(parents=True)
            active.write_text(json.dumps({
                "commit": "C25",
                "agent": "nova",
                "status": "prepared",
                "package": {
                    "selected_files": 7,
                    "estimated_chars": 12000,
                    "targeted_excerpt_files": 1,
                    "expansion_triggers": [],
                },
            }), encoding="utf-8")

            output = root / "constraint-dashboard.html"
            document = render_dashboard(root, output)
            self.assertIn("Prepared next delegation", document)
            self.assertIn("Phase B context efficiency", document)
            self.assertIn("77.8%", document)
            self.assertIn("C24", document)
            self.assertTrue(output.is_file())


if __name__ == "__main__":
    unittest.main()
