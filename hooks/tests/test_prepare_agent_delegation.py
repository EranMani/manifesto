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
from prepare_agent_delegation import prepare  # noqa: E402


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

            with patch(
                "prepare_agent_delegation.require_valid_pending_graph",
                return_value={"status": "valid"},
            ), patch(
                "prepare_agent_delegation.require_valid_commit_spec",
                return_value=self._validation(),
            ):
                _package, _package_path, _brief_path, refreshed_again = prepare(
                    root,
                    self.rules,
                    "1",
                    "aria",
                )
            self.assertFalse(refreshed_again)

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
            ):
                with self.assertRaisesRegex(ValueError, "graph validation failed"):
                    prepare(root, self.rules, "1", "aria")
            self.assertFalse((root / ".context" / "delegations").exists())
            self.assertFalse((root / ".context" / "runs").exists())
            self.assertFalse((root / ".context" / "telemetry").exists())


if __name__ == "__main__":
    unittest.main()
