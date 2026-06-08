#!/usr/bin/env python3

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


HOOKS_DIR = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures" / "context_repo"
sys.path.insert(0, str(HOOKS_DIR))

from context_engine import load_rules  # noqa: E402
from prepare_agent_delegation import prepare  # noqa: E402


class PrepareAgentDelegationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rules = load_rules(HOOKS_DIR / "context_rules.json")

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
            worklog = next(
                item for item in package["files"] if item["category"] == "worklog"
            )
            self.assertEqual(worklog["read_strategy"], "first 50 lines only")

            _package, _package_path, _brief_path, refreshed_again = prepare(
                root,
                self.rules,
                "1",
                "aria",
            )
            self.assertFalse(refreshed_again)

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


if __name__ == "__main__":
    unittest.main()
