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
from constraint_dashboard import build_graph_view_data, render_dashboard  # noqa: E402
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
            # Dual-scope telemetry: hooks data becomes agent scope
            agent = record["telemetry"]["agent"]
            self.assertEqual(agent["source"], "hooks")
            self.assertEqual(agent["status"], "available")
            self.assertEqual(agent["tool_calls"], 5)
            self.assertIn("a.py", agent["read_paths"])
            self.assertIn("b.py", agent["read_paths"])
            self.assertEqual(agent["expansions"], ["b.py"])
            # No orchestrator data → unavailable
            self.assertEqual(record["telemetry"]["orchestrator"]["status"], "unavailable")

    def test_agent_aliases_match_live_package_ids(self) -> None:
        self.assertEqual(normalize_agent_name("backend"), "rex")
        self.assertEqual(normalize_agent_name("frontend"), "aria")
        self.assertEqual(normalize_agent_name("ai-engineer"), "nova")

    def test_finalize_orchestrator_scope_returns_none_when_no_active_scope(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = context_telemetry.finalize_orchestrator_scope("C30", root)
            self.assertIsNone(result)
            self.assertFalse(
                (root / ".context" / "telemetry" / "C30-orchestrator.json").exists()
            )

    def test_finalize_orchestrator_scope_rejects_stale_commit(self) -> None:
        """OI-13 regression: a scope opened for one commit must not be
        re-stamped and persisted under a later commit's filename when
        --start-orchestrator was never called for that later commit."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            context_telemetry.initialize_orchestrator_scope("C29A", root)
            first = context_telemetry.finalize_orchestrator_scope("C29A", root)
            self.assertIsNotNone(first)
            self.assertTrue(
                (root / ".context" / "telemetry" / "C29A-orchestrator.json").exists()
            )

            # No --start-orchestrator C29B call: orchestrator-active.json is
            # still the completed C29A scope.
            second = context_telemetry.finalize_orchestrator_scope("C29B", root)
            self.assertIsNone(second)
            self.assertFalse(
                (root / ".context" / "telemetry" / "C29B-orchestrator.json").exists()
            )

    def test_finalize_orchestrator_scope_accepts_matching_commit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            context_telemetry.initialize_orchestrator_scope("C30", root)
            result = context_telemetry.finalize_orchestrator_scope("C30", root)
            self.assertIsNotNone(result)
            self.assertEqual(result["status"], "completed")
            self.assertTrue(
                (root / ".context" / "telemetry" / "C30-orchestrator.json").exists()
            )


class ReconcileInvocationRecordsTests(unittest.TestCase):
    def _write_record(self, root: Path, name: str, payload: dict) -> None:
        path = root / ".context" / "telemetry" / "invocations" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def test_matching_sources_reconcile(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._write_record(root, "C31-adam-normal-self-report-1.json", {
                "commit": "C31", "agent": "adam", "kind": "normal",
                "record_type": "self-report", "tool_calls": 5,
            })
            self._write_record(root, "C31-adam-normal-hooks-1.json", {
                "commit": "C31", "agent": "adam", "kind": "normal",
                "record_type": "hooks", "tools": {"total": 5},
            })

            result = context_metrics.reconcile_invocation_records("31", "adam", root)

            self.assertEqual(result["total_tool_calls"], 5)
            self.assertTrue(result["total_tool_calls_complete"])
            self.assertEqual(result["contradictions"], [])
            self.assertEqual(result["unknown"], [])
            self.assertEqual(result["invocations"][0]["status"], "reconciled")

    def test_conflicting_and_absent_totals_remain_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            # Conflicting tool_calls between self-report and hooks.
            self._write_record(root, "C31-adam-normal-self-report-1.json", {
                "commit": "C31", "agent": "adam", "kind": "normal",
                "record_type": "self-report", "tool_calls": 3,
            })
            self._write_record(root, "C31-adam-normal-hooks-1.json", {
                "commit": "C31", "agent": "adam", "kind": "normal",
                "record_type": "hooks", "tools": {"total": 7},
            })
            # A repair invocation with no hooks record at all (C30 case).
            self._write_record(root, "C31-adam-repair-self-report-1.json", {
                "commit": "C31", "agent": "adam", "kind": "repair",
                "record_type": "self-report", "tool_calls": None,
            })

            result = context_metrics.reconcile_invocation_records("31", "adam", root)

            self.assertEqual(result["total_tool_calls"], 0)
            self.assertFalse(result["total_tool_calls_complete"])
            self.assertEqual(len(result["contradictions"]), 1)
            self.assertEqual(result["contradictions"][0]["self_report_tool_calls"], 3)
            self.assertEqual(result["contradictions"][0]["hooks_tool_calls"], 7)
            self.assertEqual(len(result["unknown"]), 1)
            self.assertEqual(result["unknown"][0]["kind"], "repair")


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
            graph_path = root / ".context" / "index" / "codebase-graph.json"
            graph_path.parent.mkdir(parents=True)
            graph_path.write_text(json.dumps({
                "schema_version": 1,
                "totals": {"files": 2, "edges": 1, "hubs": 1},
                "categories": {
                    "backend/app/core/config.py": "backend",
                    "backend/app/core/database.py": "backend",
                },
                "summaries": {
                    "backend/app/core/config.py": "Defines validated runtime settings.",
                    "backend/app/core/database.py": "Creates async database sessions.",
                },
                "imports": {
                    "backend/app/core/config.py": [],
                    "backend/app/core/database.py": ["backend/app/core/config.py"],
                },
                "hubs": [{
                    "path": "backend/app/core/config.py",
                    "category": "backend",
                    "in_degree": 1,
                    "domain_in_degree": 1,
                    "out_degree": 0,
                }],
            }), encoding="utf-8")
            run_path = root / ".context" / "runs" / "C24-rex-live.json"
            run_path.parent.mkdir(parents=True)
            spec_path = root / "commit-specs" / "commit-24.md"
            spec_path.parent.mkdir(parents=True)
            spec_path.write_text(
                "# Commit 24 - Runtime config\n\n"
                "## What\n\n"
                "Prepare provider runtime configuration for the next service commit.\n",
                encoding="utf-8",
            )
            run_path.write_text(json.dumps({
                "commit": "C24",
                "agent": "rex",
                "task_kind": "implementation",
                "spec": "commit-specs/commit-24.md",
                "budget": {"estimated_selected_chars": 630},
                "files": [{
                    "path": "backend/app/core/config.py",
                    "category": "primary",
                    "reasons": ["commit spec change table"],
                    "read_strategy": "full file",
                }],
                "excluded_candidates": [],
                "forbidden_edits": ["frontend/"],
            }), encoding="utf-8")

            output = root / "constraint-dashboard.html"
            document = render_dashboard(root, output)
            self.assertIn("Prepared next delegation", document)
            self.assertIn("Phase B context efficiency", document)
            self.assertIn("77.8%", document)
            self.assertIn("C24", document)
            self.assertIn("Commit measurements", document)
            self.assertIn("Codebase graph", document)
            self.assertIn("commitOverlay", document)
            self.assertNotIn("categoryFilters", document)
            self.assertIn("backend/app/core/config.py", document)
            self.assertIn('label.setAttribute("text-anchor","middle")', document)
            self.assertIn("label.textContent=n.name", document)
            self.assertIn("const categoryCenters=new Map", document)
            self.assertIn("function hubScore(n)", document)
            self.assertIn("nodes.sort((a,b)=>hubScore(b)-hubScore(a)", document)
            self.assertIn(
                "categories.forEach(category=>drawCategoryFrame(g,ns,category))",
                document,
            )
            self.assertIn('label.setAttribute("font-size","7")', document)
            self.assertIn("label.textContent=category.toUpperCase()", document)
            self.assertIn('id="graphTooltip"', document)
            self.assertIn("function showTooltip(n,e)", document)
            self.assertIn("function updateEdgeStyles()", document)
            self.assertIn('connected?".92"', document)
            self.assertIn('line.dataset.same==="1"?".12":".035"', document)
            self.assertIn("function nodeSummary(n,incoming,outgoing)", document)
            self.assertIn("if(n.summary)return n.summary", document)
            self.assertIn('class="tooltip-summary"', document)
            self.assertIn('id="commitSummary"', document)
            self.assertIn("function renderCommitSummary()", document)
            self.assertIn('class="commit-file-link"', document)
            self.assertIn("function focusGraphNode(path)", document)
            self.assertIn("panX=width*.62-node.x*scale", document)
            self.assertIn("hideTooltip();resize();focusedNode=node.id", document)
            self.assertNotIn("function showTooltipAtNode(n)", document)
            self.assertNotIn('stroke="#f8fafc";sw=5', document)
            self.assertIn("const activeNode=hoveredNode||focusedNode", document)
            self.assertIn("function startCategoryDrag(category,e)", document)
            self.assertIn('rect.style.cursor="move"', document)
            self.assertIn(
                "ai:[150,145],backend:[610,270],tests:[150,435]",
                document,
            )
            self.assertIn("frontend:[1050,710]", document)
            self.assertIn("function resetCategoryCenters()", document)
            self.assertIn("width:310px;max-height:540px", document)
            self.assertIn(
                'if(btn.dataset.tab==="graph")requestAnimationFrame(fitGraph)',
                document,
            )
            self.assertIn("Prepare provider runtime configuration", document)
            self.assertNotIn('id="graphDetails"', document)
            self.assertTrue(output.is_file())

            graph_data = build_graph_view_data(root)
            self.assertEqual(len(graph_data["nodes"]), 2)
            self.assertEqual(len(graph_data["edges"]), 1)
            self.assertIn("C24-rex", graph_data["overlays"])
            self.assertEqual(
                graph_data["overlays"]["C24-rex"]["title"],
                "Commit 24 - Runtime config",
            )
            config = next(
                node
                for node in graph_data["nodes"]
                if node["path"] == "backend/app/core/config.py"
            )
            self.assertEqual(config["in_degree"], 1)
            self.assertTrue(config["hub"])
            self.assertEqual(
                config["summary"],
                "Defines validated runtime settings.",
            )


def _preflight_report(
    commit: str,
    score: int,
    proceed: bool,
    blocking_violations: list[str],
    warnings: list[str],
    goal: str = "Build <widget> & stuff",
) -> dict:
    return {
        "compact": {
            "commit": commit,
            "score": score,
            "owner": {"id": "adam", "name": "Adam", "domain": "DevOps"},
            "goal": goal,
            "files": [{"action": "edit", "path": "hooks/x.py"}],
            "blocking_violations": blocking_violations,
            "warnings": warnings,
            "decision_required": bool(warnings),
            "proceed": proceed,
            "report_path": f".context/preflight/{commit}.json",
        },
        "hard_points": 100,
        "total_deductions": 100 - score,
        "categories": {
            "specification_validity": {
                "points_awarded": 15,
                "points_possible": 15,
                "passed": True,
                "evidence": {},
            },
        },
        "deductions": {
            "readiness": {"points": 100 - score, "warnings": warnings},
        },
        "raw_validators": {},
        "context_package": {"selected_files": 4, "estimated_chars": 14889},
        "dependencies": ["C49"],
        "verification_command": "pytest hooks/tests/test_x.py -q",
    }


class PreflightDashboardTests(unittest.TestCase):
    def test_ready_warning_blocked_render_with_distinct_labels(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            preflight_dir = root / ".context" / "preflight"
            preflight_dir.mkdir(parents=True)
            (preflight_dir / "C50.json").write_text(
                json.dumps(_preflight_report("C50", 95, True, [], [])),
                encoding="utf-8",
            )
            (preflight_dir / "C51.json").write_text(
                json.dumps(_preflight_report(
                    "C51", 70, False, [], ["Context expansion warning: extra read"]
                )),
                encoding="utf-8",
            )
            (preflight_dir / "C52.json").write_text(
                json.dumps(_preflight_report(
                    "C52", 40, False,
                    ["specification_validity: commit specification failed validation"],
                    [],
                )),
                encoding="utf-8",
            )

            document = render_dashboard(root, root / "constraint-dashboard.html")

            self.assertIn("Preflight readiness", document)
            self.assertIn('<span class="badge good">READY (95/100)</span>', document)
            self.assertIn('<span class="badge neutral">WARNING (70/100)</span>', document)
            self.assertIn('<span class="badge bad">BLOCKED (40/100)</span>', document)

    def test_row_expansion_exposes_breakdown_and_escaped_json(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            preflight_dir = root / ".context" / "preflight"
            preflight_dir.mkdir(parents=True)
            report = _preflight_report("C50", 95, True, [], [])
            (preflight_dir / "C50.json").write_text(json.dumps(report), encoding="utf-8")

            document = render_dashboard(root, root / "constraint-dashboard.html")

            self.assertIn('<details class="preflight-raw">', document)
            self.assertIn("Score breakdown", document)
            self.assertIn("specification_validity", document)
            self.assertIn("pytest hooks/tests/test_x.py -q", document)
            # The raw report is rendered verbatim, with HTML-sensitive
            # characters in the goal escaped rather than executed.
            self.assertIn("Build &lt;widget&gt; &amp; stuff", document)

    def test_missing_and_malformed_reports_degrade_safely(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)

            # No .context/preflight directory at all.
            document = render_dashboard(root, root / "constraint-dashboard.html")
            self.assertIn("No preflight reports have been generated yet.", document)

            # A report file that exists but is not valid JSON / lacks "compact".
            preflight_dir = root / ".context" / "preflight"
            preflight_dir.mkdir(parents=True)
            (preflight_dir / "C53.json").write_text("not json", encoding="utf-8")

            document = render_dashboard(root, root / "constraint-dashboard.html")
            self.assertIn("INVALID REPORT", document)
            self.assertIn('<span class="badge bad">invalid-report</span>', document)

    def test_dashboard_rendering_never_changes_persisted_report(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            preflight_dir = root / ".context" / "preflight"
            preflight_dir.mkdir(parents=True)
            report_path = preflight_dir / "C50.json"
            original = json.dumps(_preflight_report("C50", 95, True, [], []), indent=2, sort_keys=True)
            report_path.write_text(original, encoding="utf-8")

            render_dashboard(root, root / "constraint-dashboard.html")
            render_dashboard(root, root / "constraint-dashboard.html")

            self.assertEqual(report_path.read_text(encoding="utf-8"), original)


if __name__ == "__main__":
    unittest.main()
