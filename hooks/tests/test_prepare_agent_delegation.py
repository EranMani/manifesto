#!/usr/bin/env python3

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


HOOKS_DIR = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures" / "context_repo"
sys.path.insert(0, str(HOOKS_DIR))

from context_engine import load_rules  # noqa: E402
from prepare_agent_delegation import PreflightBlocked, main, prepare  # noqa: E402


_PASSING_PREFLIGHT: dict = {
    "commit": "1",
    "score": 100,
    "owner": "aria",
    "goal": "test",
    "files": [],
    "blocking_violations": [],
    "warnings": [],
    "decision_required": False,
    "proceed": True,
    "report_path": ".context/preflight/C1.json",
}

_BLOCKED_PREFLIGHT: dict = {
    "commit": "1",
    "score": 40,
    "owner": "aria",
    "goal": "test",
    "files": [],
    "blocking_violations": ["context package exceeds max_context_chars"],
    "warnings": [],
    "decision_required": True,
    "proceed": False,
    "report_path": ".context/preflight/C1.json",
}


class PrepareAgentDelegationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rules = load_rules(HOOKS_DIR / "context_rules.json")

    @staticmethod
    def _validation() -> dict:
        return {
            "status": "valid",
            "budget": {
                "max_context_files": 6,
                "max_context_chars": 15000,
                "max_agent_invocations": 1,
                "max_tool_calls": 18,
                "max_expansions": 2,
                "max_implementor_tokens": 45000,
                "max_total_tokens": 60000,
            },
        }

    def test_prepare_writes_live_package_and_surgical_brief(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "repo"
            shutil.copytree(FIXTURE_ROOT, root)
            (root / "project-state.json").write_text(
                json.dumps({
                    "next_commit": "1",
                    "next_commit_assignee": "aria",
                    "open_handoffs": [],
                }),
                encoding="utf-8",
            )
            with patch(
                "prepare_agent_delegation.require_valid_pending_graph",
                return_value={"status": "valid"},
            ), patch(
                "prepare_agent_delegation.require_valid_commit_spec",
                return_value=self._validation(),
            ), patch(
                "prepare_agent_delegation.preflight_evaluate",
                return_value=_PASSING_PREFLIGHT,
            ):
                package, package_path, brief_path, refreshed = prepare(
                    root,
                    self.rules,
                    "1",
                    "aria",
                )
            self.assertTrue(refreshed)
            self.assertTrue(package_path.is_file())
            self.assertTrue(brief_path.is_file())
            self.assertEqual(package["mode"], "live")
            brief = brief_path.read_text(encoding="utf-8")
            self.assertIn("## Objective", brief)
            self.assertIn("Fixture objective", brief)
            self.assertIn("## Authoritative Contract", brief)
            self.assertIn("Do not scan directories", brief)
            self.assertIn("Before each expansion", brief)
            self.assertIn("tradeoffs", brief)
            self.assertIn("## Human Summary", brief)
            self.assertIn("**What I completed:**", brief)
            self.assertIn("**What changed:**", brief)
            self.assertIn("**What went wrong:**", brief)
            self.assertIn("**What remains:**", brief)
            self.assertIn("**Recommended next commit:**", brief)
            self.assertIn("**Developer attention:**", brief)
            self.assertLess(
                brief.index("## Human Summary"),
                brief.index('"tool_calls": <total count>'),
            )
            worklog = next(
                item for item in package["files"] if item["category"] == "worklog"
            )
            self.assertEqual(worklog["read_strategy"], "first 50 lines only")
            tool_cap = json.loads(
                (root / "hooks" / "tool_cap.json").read_text(encoding="utf-8")
            )
            self.assertIn(
                ".claude/agents/frontend.md",
                tool_cap["selected_paths"],
            )

    def test_preview_does_not_activate_runtime_state(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "repo"
            shutil.copytree(FIXTURE_ROOT, root)
            (root / "project-state.json").write_text(
                json.dumps({
                    "next_commit": "1",
                    "next_commit_assignee": "aria",
                    "open_handoffs": [],
                }),
                encoding="utf-8",
            )
            with patch(
                "prepare_agent_delegation.require_valid_pending_graph",
                return_value={"status": "valid"},
            ), patch(
                "prepare_agent_delegation.require_valid_commit_spec",
                return_value=self._validation(),
            ), patch(
                "prepare_agent_delegation.preflight_evaluate",
                return_value=_PASSING_PREFLIGHT,
            ), patch(
                "prepare_agent_delegation.initialize_commit_state"
            ) as initialize_state, patch(
                "prepare_agent_delegation.initialize_telemetry"
            ) as initialize_telemetry_mock:
                package, package_path, brief_path, _ = prepare(
                    root,
                    self.rules,
                    "1",
                    "aria",
                    activate=False,
                )

            self.assertEqual(package["commit"], "C01")
            self.assertTrue(package_path.is_file())
            self.assertTrue(brief_path.is_file())
            initialize_state.assert_not_called()
            initialize_telemetry_mock.assert_not_called()
            self.assertFalse((root / "constraint-dashboard.html").exists())

            with patch(
                "prepare_agent_delegation.require_valid_pending_graph",
                return_value={"status": "valid"},
            ), patch(
                "prepare_agent_delegation.require_valid_commit_spec",
                return_value=self._validation(),
            ), patch(
                "prepare_agent_delegation.preflight_evaluate",
                return_value=_PASSING_PREFLIGHT,
            ):
                _package, _package_path, _brief_path, refreshed_again = prepare(
                    root,
                    self.rules,
                    "1",
                    "aria",
                )
            self.assertFalse(refreshed_again)

            # activate=True (default) initializes tool-cap/telemetry but must not
            # render the dashboard -- rendering is opt-in via verify_constraints
            # --render-dashboard.
            self.assertFalse((root / "constraint-dashboard.html").exists())

    @staticmethod
    def _greenfield_validation() -> dict:
        return {
            "status": "valid",
            "budget": {
                "max_context_files": 6,
                "max_context_chars": 15000,
                "max_agent_invocations": 1,
                "max_tool_calls": 28,
                "max_expansions": 2,
                "max_implementor_tokens": 55000,
                "max_total_tokens": 70000,
            },
        }

    def test_prepare_propagates_greenfield_budget_without_manual_edit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "repo"
            shutil.copytree(FIXTURE_ROOT, root)
            (root / "project-state.json").write_text(
                json.dumps({
                    "next_commit": "1",
                    "next_commit_assignee": "aria",
                    "open_handoffs": [],
                }),
                encoding="utf-8",
            )
            with patch(
                "prepare_agent_delegation.require_valid_pending_graph",
                return_value={"status": "valid"},
            ), patch(
                "prepare_agent_delegation.require_valid_commit_spec",
                return_value=self._greenfield_validation(),
            ), patch(
                "prepare_agent_delegation.preflight_evaluate",
                return_value=_PASSING_PREFLIGHT,
            ):
                prepare(root, self.rules, "1", "aria")

            tool_cap = json.loads(
                (root / "hooks" / "tool_cap.json").read_text(encoding="utf-8")
            )
            expected_limits = {
                "max_context_files": 6,
                "max_context_chars": 15000,
                "max_agent_invocations": 1,
                "max_tool_calls": 28,
                "max_expansions": 2,
                "max_implementor_tokens": 55000,
                "max_total_tokens": 70000,
            }
            for key, value in expected_limits.items():
                if key in tool_cap["limits"]:
                    self.assertEqual(tool_cap["limits"][key], value)
            self.assertEqual(tool_cap["limit"], 28)

            # Regeneration must preserve the same effective budget without manual edits.
            with patch(
                "prepare_agent_delegation.require_valid_pending_graph",
                return_value={"status": "valid"},
            ), patch(
                "prepare_agent_delegation.require_valid_commit_spec",
                return_value=self._greenfield_validation(),
            ), patch(
                "prepare_agent_delegation.preflight_evaluate",
                return_value=_PASSING_PREFLIGHT,
            ):
                prepare(root, self.rules, "1", "aria", force_refresh=True)

            tool_cap_again = json.loads(
                (root / "hooks" / "tool_cap.json").read_text(encoding="utf-8")
            )
            for key, value in expected_limits.items():
                if key in tool_cap_again["limits"]:
                    self.assertEqual(tool_cap_again["limits"][key], value)
            self.assertEqual(tool_cap_again["limit"], 28)

    def test_brief_execution_constraints_match_default_budget(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "repo"
            shutil.copytree(FIXTURE_ROOT, root)
            (root / "project-state.json").write_text(
                json.dumps({
                    "next_commit": "1",
                    "next_commit_assignee": "aria",
                    "open_handoffs": [],
                }),
                encoding="utf-8",
            )
            with patch(
                "prepare_agent_delegation.require_valid_pending_graph",
                return_value={"status": "valid"},
            ), patch(
                "prepare_agent_delegation.require_valid_commit_spec",
                return_value=self._validation(),
            ), patch(
                "prepare_agent_delegation.preflight_evaluate",
                return_value=_PASSING_PREFLIGHT,
            ):
                _package, _package_path, brief_path, _refreshed = prepare(
                    root,
                    self.rules,
                    "1",
                    "aria",
                )
            brief = brief_path.read_text(encoding="utf-8")
            self.assertIn("Total cap: 18 tool uses. Call 19 is mechanically blocked.", brief)
            self.assertIn(
                "At call 12, report budget status. By call 16, finish or return SPLIT_REQUIRED.",
                brief,
            )
            self.assertIn("Maximum 2 context expansions. Expansion 3 is mechanically blocked.", brief)
            self.assertIn("Implementor token budget: 45000. Absolute commit token budget: 60000.", brief)
            self.assertIn("If the work cannot finish by call 18, also return:", brief)
            self.assertNotIn("By call 6, implementation must have started", brief)

    def test_brief_execution_constraints_match_greenfield_budget(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "repo"
            shutil.copytree(FIXTURE_ROOT, root)
            (root / "project-state.json").write_text(
                json.dumps({
                    "next_commit": "1",
                    "next_commit_assignee": "aria",
                    "open_handoffs": [],
                }),
                encoding="utf-8",
            )
            with patch(
                "prepare_agent_delegation.require_valid_pending_graph",
                return_value={"status": "valid"},
            ), patch(
                "prepare_agent_delegation.require_valid_commit_spec",
                return_value=self._greenfield_validation(),
            ), patch(
                "prepare_agent_delegation.preflight_evaluate",
                return_value=_PASSING_PREFLIGHT,
            ):
                _package, _package_path, brief_path, _refreshed = prepare(
                    root,
                    self.rules,
                    "1",
                    "aria",
                )
            brief = brief_path.read_text(encoding="utf-8")
            self.assertIn("Total cap: 28 tool uses. Call 29 is mechanically blocked.", brief)
            self.assertIn(
                "At call 22, report budget status. By call 26, finish or return SPLIT_REQUIRED.",
                brief,
            )
            self.assertIn("Maximum 2 context expansions. Expansion 3 is mechanically blocked.", brief)
            self.assertIn("Implementor token budget: 55000. Absolute commit token budget: 70000.", brief)
            self.assertIn("If the work cannot finish by call 28, also return:", brief)
            self.assertIn(
                "By call 6, implementation must have started; otherwise call 6 is blocked.",
                brief,
            )

    def test_rejected_spec_writes_no_delegation_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "repo"
            shutil.copytree(FIXTURE_ROOT, root)
            (root / "project-state.json").write_text(
                json.dumps({
                    "next_commit": "1",
                    "next_commit_assignee": "aria",
                    "open_handoffs": [],
                }),
                encoding="utf-8",
            )
            with patch(
                "prepare_agent_delegation.require_valid_pending_graph",
                return_value={"status": "valid"},
            ), patch(
                "prepare_agent_delegation.require_valid_commit_spec",
                side_effect=ValueError("commit spec validation failed"),
            ), patch(
                "prepare_agent_delegation.preflight_evaluate",
                return_value=_PASSING_PREFLIGHT,
            ):
                with self.assertRaisesRegex(ValueError, "validation failed"):
                    prepare(root, self.rules, "1", "aria")
            self.assertFalse((root / ".context" / "delegations").exists())
            self.assertFalse((root / ".context" / "runs").exists())
            self.assertFalse((root / ".context" / "telemetry").exists())

    def test_prepare_rejects_state_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "repo"
            shutil.copytree(FIXTURE_ROOT, root)
            (root / "project-state.json").write_text(
                json.dumps({
                    "next_commit": "2",
                    "next_commit_assignee": "rex",
                    "open_handoffs": [],
                }),
                encoding="utf-8",
            )
            with patch(
                "prepare_agent_delegation.preflight_evaluate",
                return_value=_PASSING_PREFLIGHT,
            ):
                with self.assertRaisesRegex(ValueError, "Commit mismatch"):
                    prepare(root, self.rules, "1", "aria")

    def test_rejected_pending_graph_writes_no_delegation_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "repo"
            shutil.copytree(FIXTURE_ROOT, root)
            (root / "project-state.json").write_text(
                json.dumps({
                    "next_commit": "1",
                    "next_commit_assignee": "aria",
                    "open_handoffs": [],
                }),
                encoding="utf-8",
            )
            with patch(
                "prepare_agent_delegation.require_valid_pending_graph",
                side_effect=ValueError("pending commit graph validation failed"),
            ), patch(
                "prepare_agent_delegation.preflight_evaluate",
                return_value=_PASSING_PREFLIGHT,
            ):
                with self.assertRaisesRegex(ValueError, "graph validation failed"):
                    prepare(root, self.rules, "1", "aria")
            self.assertFalse((root / ".context" / "delegations").exists())
            self.assertFalse((root / ".context" / "runs").exists())
            self.assertFalse((root / ".context" / "telemetry").exists())

    def test_blocked_preflight_raises_and_writes_no_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "repo"
            shutil.copytree(FIXTURE_ROOT, root)
            (root / "project-state.json").write_text(
                json.dumps({
                    "next_commit": "1",
                    "next_commit_assignee": "aria",
                    "open_handoffs": [],
                }),
                encoding="utf-8",
            )
            with patch(
                "prepare_agent_delegation.preflight_evaluate",
                return_value=_BLOCKED_PREFLIGHT,
            ):
                with self.assertRaises(PreflightBlocked) as cm:
                    prepare(root, self.rules, "1", "aria")
            self.assertEqual(cm.exception.result, _BLOCKED_PREFLIGHT)
            self.assertFalse((root / ".context" / "delegations").exists())
            self.assertFalse((root / ".context" / "runs").exists())
            self.assertFalse((root / ".context" / "telemetry").exists())

    def test_main_handles_blocked_preflight(self) -> None:
        with patch(
            "prepare_agent_delegation.prepare",
            side_effect=PreflightBlocked(_BLOCKED_PREFLIGHT),
        ), patch(
            "sys.argv",
            ["prepare_agent_delegation.py", "--commit", "1", "--agent", "aria"],
        ), patch("builtins.print") as mock_print:
            result = main()

        self.assertEqual(result, 1)
        output = "\n".join(
            " ".join(str(arg) for arg in call.args) for call in mock_print.call_args_list
        )
        self.assertIn('"proceed": false', output)
        self.assertIn('"blocking_violations"', output)


if __name__ == "__main__":
    unittest.main()
