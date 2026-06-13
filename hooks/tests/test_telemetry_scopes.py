#!/usr/bin/env python3
"""Tests for dual-scope (agent + orchestrator) telemetry recording and rendering."""

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
from context_metrics import upsert_metric  # noqa: E402
from constraint_dashboard import render_dashboard  # noqa: E402


def _empty_graph(root: Path) -> None:
    idx = root / ".context" / "index"
    idx.mkdir(parents=True, exist_ok=True)
    (idx / "codebase-graph.json").write_text(
        json.dumps({
            "schema_version": 1, "totals": {}, "categories": {},
            "summaries": {}, "imports": {}, "hubs": [],
        }),
        encoding="utf-8",
    )
    (root / ".context" / "telemetry").mkdir(parents=True, exist_ok=True)


def _constraint_log(root: Path, commits: list[str]) -> None:
    lines = [
        "| Date | Commit | Agent | Tokens | Context | Forbidden | Budget | Result |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for c in commits:
        lines.append(f"| 2026-06-09 | {c} | rex | 20,000 | PASS | PASS | PASS | PASS |")
    (root / "CONSTRAINT_LOG.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _empty_metrics(root: Path) -> Path:
    p = root / "CONTEXT_METRICS.json"
    p.write_text(json.dumps({"schema_version": 1, "records": []}), encoding="utf-8")
    return p


def _write_matching_tool_cap(root: Path, commit: str, agent: str) -> None:
    """Make tool_cap.json show an active invocation for commit/agent.

    record_agent_self_report (C37 guard) refuses to persist a self-report
    unless tool_cap.json shows a matching invocation, so tests that record a
    self-report must set this up first.
    """
    cap = root / "hooks" / "tool_cap.json"
    cap.parent.mkdir(parents=True, exist_ok=True)
    commit_key = commit if str(commit).upper().startswith("C") else f"C{str(commit).zfill(2)}"
    cap.write_text(json.dumps({"commit": commit_key, "agent": agent.lower()}), encoding="utf-8")


# ---------------------------------------------------------------------------
# Scenario 1 — Complete agent self-report: all fields available
# ---------------------------------------------------------------------------

class TestCompleteAgentSelfReport(unittest.TestCase):
    def test_status_is_available_with_all_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = {
                "tool_calls": 18,
                "read_paths": ["backend/app/core/config.py", "backend/pyproject.toml"],
                "write_paths": ["backend/app/core/config.py"],
                "searches": [{"tool": "Grep", "path": ".", "query": "Settings"}],
                "commands": ["pytest backend/tests/test_config.py"],
                "expansions": [],
            }
            _write_matching_tool_cap(root, "24", "rex")
            scope = context_telemetry.record_agent_self_report("24", "rex", report, root)
            self.assertEqual(scope["status"], "available")
            self.assertEqual(scope["tool_calls"], 18)
            self.assertEqual(scope["read_paths"], report["read_paths"])
            self.assertEqual(scope["expansions"], [])
            self.assertEqual(scope["source"], "self_report")

            stored_path = root / ".context" / "telemetry" / "C24-rex-self-report.json"
            stored = json.loads(stored_path.read_text(encoding="utf-8"))
            self.assertEqual(stored["tool_calls"], 18)
            self.assertEqual(stored["status"], "available")
            self.assertEqual(stored["read_paths"], report["read_paths"])

    def test_self_report_priority_over_hooks(self):
        """When both self-report and hooks telemetry exist, self-report wins."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # Write hooks telemetry (lower priority)
            tdir = root / ".context" / "telemetry"
            tdir.mkdir(parents=True)
            (tdir / "C24-rex.json").write_text(json.dumps({
                "status": "completed",
                "package": {"selected_files": 2, "estimated_chars": 1000, "usable_chars": 24000},
                "tools": {"total": 99, "reads": 5, "searches": 0, "writes": 1},
                "selected_read_paths": ["a.py"],
                "outside_read_paths": [],
                "search_events": [],
                "write_paths": [],
            }), encoding="utf-8")
            # Self-report with different counts
            _write_matching_tool_cap(root, "24", "rex")
            context_telemetry.record_agent_self_report("24", "rex", {
                "tool_calls": 18,
                "read_paths": ["backend/app/core/config.py"],
                "write_paths": [],
                "searches": [],
                "commands": [],
                "expansions": [],
            }, root)
            results = {
                "context_block": {"pass": True},
                "forbidden_paths": {"pass": True},
                "phase_budget": {"pass": True},
            }
            with patch.object(context_metrics, "REPO_ROOT", root):
                record = context_metrics.build_metric_record("24", "rex", 20000, results, [])
            agent = record["telemetry"]["agent"]
            self.assertEqual(agent["source"], "self_report")
            self.assertEqual(agent["tool_calls"], 18)  # self-report, not 99 from hooks


# ---------------------------------------------------------------------------
# Scenario 2 — Missing agent self-report: scope unavailable, never zero
# ---------------------------------------------------------------------------

class TestMissingAgentSelfReport(unittest.TestCase):
    def test_unavailable_not_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            results = {
                "context_block": {"pass": True},
                "forbidden_paths": {"pass": True},
                "phase_budget": {"pass": True},
            }
            with patch.object(context_metrics, "REPO_ROOT", root):
                record = context_metrics.build_metric_record("24", "rex", None, results, [])
            agent = record["telemetry"]["agent"]
            self.assertEqual(agent["status"], "unavailable")
            self.assertIsNone(agent["tool_calls"])
            self.assertIsNone(agent["read_paths"])
            self.assertIsNone(agent["expansions"])
            # Critical: zeros must not appear
            self.assertNotEqual(agent["tool_calls"], 0)
            self.assertNotEqual(agent["read_paths"], [])

    def test_orchestrator_also_unavailable_when_nothing_captured(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            results = {
                "context_block": {"pass": True},
                "forbidden_paths": {"pass": True},
                "phase_budget": {"pass": True},
            }
            with patch.object(context_metrics, "REPO_ROOT", root):
                record = context_metrics.build_metric_record("24", "rex", None, results, [])
            orch = record["telemetry"]["orchestrator"]
            self.assertEqual(orch["status"], "unavailable")
            self.assertIsNone(orch["tool_calls"])


# ---------------------------------------------------------------------------
# Scenario 3 — Orchestrator-only correction pass
# ---------------------------------------------------------------------------

class TestOrchestratorOnlyCorrectionPass(unittest.TestCase):
    def test_orchestrator_available_agent_unavailable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tdir = root / ".context" / "telemetry"
            tdir.mkdir(parents=True)
            (tdir / "C25-orchestrator.json").write_text(json.dumps({
                "commit": "C25",
                "status": "completed",
                "tool_calls": 8,
                "read_paths": ["backend/app/core/config.py", "commit-specs/commit-25.md"],
                "write_paths": ["CONTEXT_METRICS.json", "CONSTRAINT_LOG.md"],
                "searches": [],
                "commands": ["python hooks/verify_constraints.py --commit 25 --agent rex"],
            }), encoding="utf-8")
            results = {
                "context_block": {"pass": True},
                "forbidden_paths": {"pass": True},
                "phase_budget": {"pass": True},
            }
            with patch.object(context_metrics, "REPO_ROOT", root):
                record = context_metrics.build_metric_record("25", "rex", None, results, [])
            self.assertEqual(record["telemetry"]["agent"]["status"], "unavailable")
            orch = record["telemetry"]["orchestrator"]
            self.assertEqual(orch["status"], "available")
            self.assertEqual(orch["source"], "hooks")
            self.assertEqual(orch["tool_calls"], 8)
            self.assertIn("backend/app/core/config.py", orch["read_paths"])
            self.assertIn("CONTEXT_METRICS.json", orch["write_paths"])

    def test_orchestrator_scope_lifecycle(self):
        """initialize → record event → finalize produces the correct file."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            orch_active = root / ".context" / "telemetry" / "orchestrator-active.json"

            context_telemetry.initialize_orchestrator_scope("C25", root)
            scope = json.loads(orch_active.read_text(encoding="utf-8"))
            self.assertEqual(scope["status"], "running")
            self.assertEqual(scope["tool_calls"], 0)

            # Simulate a tool event routed to orchestrator
            with (
                patch.object(context_telemetry, "ORCHESTRATOR_ACTIVE_PATH", orch_active),
                patch.object(context_telemetry, "ACTIVE_PATH", root / ".context" / "telemetry" / "active.json"),
            ):
                context_telemetry.record_tool_event({
                    "tool_name": "Read",
                    "tool_input": {"file_path": str(root / "backend/app/core/config.py")},
                })

            scope = json.loads(orch_active.read_text(encoding="utf-8"))
            self.assertEqual(scope["tool_calls"], 1)

            result = context_telemetry.finalize_orchestrator_scope("C25", root)
            self.assertEqual(result["status"], "completed")
            final_path = root / ".context" / "telemetry" / "C25-orchestrator.json"
            self.assertTrue(final_path.is_file())


# ---------------------------------------------------------------------------
# Scenario 4 — Agent + orchestrator both present: combined total correct
# ---------------------------------------------------------------------------

class TestAgentAndOrchestratorCombined(unittest.TestCase):
    def test_combined_total(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tdir = root / ".context" / "telemetry"
            tdir.mkdir(parents=True)
            _write_matching_tool_cap(root, "26", "rex")
            context_telemetry.record_agent_self_report("26", "rex", {
                "tool_calls": 20,
                "read_paths": ["a.py", "b.py"],
                "write_paths": ["c.py"],
                "searches": [],
                "commands": ["pytest"],
                "expansions": [],
            }, root)
            (tdir / "C26-orchestrator.json").write_text(json.dumps({
                "commit": "C26", "status": "completed",
                "tool_calls": 7,
                "read_paths": ["d.py"],
                "write_paths": ["CONTEXT_METRICS.json"],
                "searches": [],
                "commands": [],
            }), encoding="utf-8")
            results = {
                "context_block": {"pass": True},
                "forbidden_paths": {"pass": True},
                "phase_budget": {"pass": True},
            }
            with patch.object(context_metrics, "REPO_ROOT", root):
                record = context_metrics.build_metric_record("26", "rex", None, results, [])
            agent = record["telemetry"]["agent"]
            orch = record["telemetry"]["orchestrator"]
            self.assertEqual(agent["tool_calls"], 20)
            self.assertEqual(orch["tool_calls"], 7)
            combined = (agent["tool_calls"] or 0) + (orch["tool_calls"] or 0)
            self.assertEqual(combined, 27)


# ---------------------------------------------------------------------------
# Scenario 5 — Missing values render as N/A, never zero
# ---------------------------------------------------------------------------

class TestMissingValuesRenderAsNA(unittest.TestCase):
    def test_dashboard_na_not_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _empty_graph(root)
            _constraint_log(root, ["C24"])
            mp = _empty_metrics(root)
            upsert_metric({
                "date": "2026-06-09",
                "commit": "C24",
                "agent": "rex",
                "tokens": 37486,
                "package": {"selected_files": 9, "estimated_chars": 19796},
                "telemetry": {
                    "agent": {
                        "source": "self_report",
                        "status": "partial",
                        "tool_calls": 26,
                        "read_paths": None,
                        "write_paths": None,
                        "searches": None,
                        "commands": None,
                        "expansions": None,
                    },
                    "orchestrator": {
                        "source": "hooks",
                        "status": "unavailable",
                        "tool_calls": None,
                        "read_paths": None,
                        "write_paths": None,
                        "searches": None,
                        "commands": None,
                    },
                },
                "usage": {
                    "selected_files_read": None,
                    "selected_utilization_percent": None,
                    "searches": None,
                    "expansions": None,
                },
                "boundaries": {"forbidden_clean": True},
                "result": "PASS",
            }, mp)
            doc = render_dashboard(root, root / "out.html")
            # Agent reported 26 calls — must appear
            self.assertIn("26", doc)
            # Orchestrator is unavailable — N/A must appear
            self.assertIn("N/A", doc)
            # Neither scope should show "0" as its tool-call count
            self.assertNotIn(">0<", doc)

    def test_partial_self_report_shows_count_with_na_paths(self):
        """Partial self-report shows tool_calls but N/A for path columns."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _empty_graph(root)
            _constraint_log(root, ["C24"])
            mp = _empty_metrics(root)
            upsert_metric({
                "date": "2026-06-09",
                "commit": "C24",
                "agent": "rex",
                "tokens": 37486,
                "package": {"selected_files": 9, "estimated_chars": 19796},
                "telemetry": {
                    "agent": {
                        "source": "self_report",
                        "status": "partial",
                        "tool_calls": 26,
                        "read_paths": None,
                        "expansions": None,
                    },
                    "orchestrator": {
                        "source": "hooks",
                        "status": "available",
                        "tool_calls": 5,
                        "read_paths": ["CONTEXT_METRICS.json"],
                        "write_paths": [],
                        "searches": [],
                        "commands": [],
                    },
                },
                "usage": {},
                "boundaries": {"forbidden_clean": True},
                "result": "PASS",
            }, mp)
            doc = render_dashboard(root, root / "out.html")
            self.assertIn("26", doc)   # agent calls visible
            self.assertIn("5", doc)    # orch calls visible
            self.assertIn("N/A", doc)  # orchestrator badge or unavailable marker


# ---------------------------------------------------------------------------
# Scenario 6 — Unknown expansion status not counted as expansion-free
# ---------------------------------------------------------------------------

class TestUnknownExpansionNotCountedExpansionFree(unittest.TestCase):
    def test_expansion_free_card_excludes_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _empty_graph(root)
            _constraint_log(root, ["C24", "C25"])
            mp = _empty_metrics(root)
            # C24: partial self-report → expansion status Unknown
            upsert_metric({
                "date": "2026-06-09", "commit": "C24", "agent": "rex", "tokens": 37486,
                "package": {"selected_files": 9, "estimated_chars": 19796},
                "telemetry": {
                    "agent": {"source": "self_report", "status": "partial",
                               "tool_calls": 26, "read_paths": None, "expansions": None},
                    "orchestrator": {"source": "hooks", "status": "unavailable", "tool_calls": None},
                },
                "usage": {},
                "boundaries": {"forbidden_clean": True},
                "result": "PASS",
            }, mp)
            # C25: hooks data → expansion status Known (zero)
            upsert_metric({
                "date": "2026-06-09", "commit": "C25", "agent": "rex", "tokens": 20000,
                "package": {"selected_files": 7, "estimated_chars": 12000},
                "telemetry": {
                    "agent": {"source": "hooks", "status": "available",
                               "tool_calls": 15, "read_paths": ["a.py"],
                               "write_paths": [], "searches": [], "commands": [],
                               "expansions": []},
                    "orchestrator": {"source": "hooks", "status": "available",
                                     "tool_calls": 5, "read_paths": [], "write_paths": [],
                                     "searches": [], "commands": []},
                },
                "usage": {"selected_files_read": 6, "selected_utilization_percent": 85.7,
                          "searches": 0, "expansions": 0},
                "boundaries": {"forbidden_clean": True},
                "result": "PASS",
            }, mp)
            doc = render_dashboard(root, root / "out.html")
            # Only C25 is expansion-free (known). C24 is Unknown — not counted.
            self.assertIn("1/2", doc)
            self.assertIn("1 unknown", doc)
            # C24 expansion column should say Unknown
            self.assertIn("Unknown", doc)
            # C25 expansion column shows 0
            self.assertIn(">0<", doc)

    def test_zero_expansions_known_counted(self):
        """A record with empty expansions list is positively counted as expansion-free."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _empty_graph(root)
            _constraint_log(root, ["C25"])
            mp = _empty_metrics(root)
            upsert_metric({
                "date": "2026-06-09", "commit": "C25", "agent": "rex", "tokens": 20000,
                "package": {"selected_files": 7, "estimated_chars": 12000},
                "telemetry": {
                    "agent": {"source": "hooks", "status": "available",
                               "tool_calls": 10, "read_paths": ["a.py"],
                               "write_paths": [], "searches": [], "commands": [],
                               "expansions": []},
                    "orchestrator": {"source": "hooks", "status": "unavailable", "tool_calls": None},
                },
                "usage": {"selected_files_read": 5, "selected_utilization_percent": 71.4,
                          "searches": 0, "expansions": 0},
                "boundaries": {"forbidden_clean": True},
                "result": "PASS",
            }, mp)
            doc = render_dashboard(root, root / "out.html")
            self.assertIn("1/1", doc)
            self.assertNotIn("unknown", doc)


# ---------------------------------------------------------------------------
# Scenario 7 — Invocation record storage (C30)
# ---------------------------------------------------------------------------

class TestInvocationRecordStorage(unittest.TestCase):
    _REPORT = {
        "tool_calls": 5,
        "read_paths": ["a.py"],
        "write_paths": [],
        "searches": [],
        "commands": [],
        "expansions": [],
    }

    def test_normal_repair_review_records_append_independently(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_matching_tool_cap(root, "30", "adam")
            context_telemetry.record_agent_self_report(
                "30", "adam", self._REPORT, root, invocation_kind="normal"
            )
            context_telemetry.record_agent_self_report(
                "30", "adam", self._REPORT, root, invocation_kind="repair"
            )
            _write_matching_tool_cap(root, "30", "viktor")
            context_telemetry.record_agent_self_report(
                "30", "viktor", self._REPORT, root, invocation_kind="review"
            )

            inv_dir = root / ".context" / "telemetry" / "invocations"
            self.assertTrue((inv_dir / "C30-adam-normal-self-report-1.json").is_file())
            self.assertTrue((inv_dir / "C30-adam-repair-self-report-1.json").is_file())
            self.assertTrue((inv_dir / "C30-viktor-review-self-report-1.json").is_file())

    def test_repeated_self_report_does_not_overwrite_prior_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_matching_tool_cap(root, "30", "adam")
            context_telemetry.record_agent_self_report(
                "30", "adam", {**self._REPORT, "tool_calls": 3}, root, invocation_kind="normal"
            )
            context_telemetry.record_agent_self_report(
                "30", "adam", {**self._REPORT, "tool_calls": 9}, root, invocation_kind="normal"
            )

            inv_dir = root / ".context" / "telemetry" / "invocations"
            first = json.loads((inv_dir / "C30-adam-normal-self-report-1.json").read_text(encoding="utf-8"))
            second = json.loads((inv_dir / "C30-adam-normal-self-report-2.json").read_text(encoding="utf-8"))
            self.assertEqual(first["tool_calls"], 3)
            self.assertEqual(second["tool_calls"], 9)

    def test_finalize_does_not_overwrite_prior_invocation_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            active = root / ".context" / "telemetry" / "active.json"
            active.parent.mkdir(parents=True)
            cap_path = root / "hooks" / "tool_cap.json"
            cap_path.parent.mkdir(parents=True)
            cap_path.write_text(
                json.dumps({"active": True, "agent": "adam", "active_invocation": {"kind": "normal"}}),
                encoding="utf-8",
            )
            telemetry = {
                "schema_version": 1,
                "commit": "C30",
                "agent": "adam",
                "status": "running",
                "started_at": "2026-06-12T00:00:00+00:00",
                "ended_at": None,
                "selected_paths": [],
                "forbidden_paths": [],
                "package": {},
                "tools": {"total": 0, "reads": 0, "searches": 0, "writes": 0, "tests_or_commands": 0},
                "selected_read_paths": [],
                "outside_read_paths": [],
                "search_events": [],
                "write_paths": [],
            }

            with (
                patch.object(context_telemetry, "REPO_ROOT", root),
                patch.object(context_telemetry, "ACTIVE_PATH", active),
            ):
                active.write_text(json.dumps(telemetry), encoding="utf-8")
                context_telemetry.finalize_telemetry()

                active.write_text(json.dumps(telemetry), encoding="utf-8")
                context_telemetry.finalize_telemetry()

            inv_dir = root / ".context" / "telemetry" / "invocations"
            self.assertTrue((inv_dir / "C30-adam-normal-hooks-1.json").is_file())
            self.assertTrue((inv_dir / "C30-adam-normal-hooks-2.json").is_file())


if __name__ == "__main__":
    unittest.main()
