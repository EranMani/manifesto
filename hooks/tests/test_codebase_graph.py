#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


HOOKS_DIR = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures" / "context_repo"
sys.path.insert(0, str(HOOKS_DIR))

from codebase_graph import build_codebase_graph  # noqa: E402
from context_engine import ContextPackageBuilder, load_rules  # noqa: E402


class CodebaseGraphTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rules = load_rules(HOOKS_DIR / "context_rules.json")

    def test_graph_is_deterministic_and_resolves_edges(self) -> None:
        first = build_codebase_graph(FIXTURE_ROOT, self.rules)
        second = build_codebase_graph(FIXTURE_ROOT, self.rules)
        self.assertEqual(first, second)
        self.assertIn(
            "backend/app/schemas/auth.py",
            first["imports"]["backend/app/api/v1/auth.py"],
        )
        self.assertIn(
            "frontend/src/api/auth.ts",
            first["imported_by"]["frontend/src/api/client.ts"],
        )
        self.assertEqual(
            first["categories"]["frontend/src/api/auth.ts"],
            "frontend",
        )

    def test_context_builder_uses_valid_cache(self) -> None:
        graph = build_codebase_graph(FIXTURE_ROOT, self.rules)
        with tempfile.TemporaryDirectory() as temporary:
            graph_path = Path(temporary) / "codebase-graph.json"
            graph_path.write_text(json.dumps(graph), encoding="utf-8")
            package = ContextPackageBuilder(
                FIXTURE_ROOT,
                self.rules,
                graph_path=graph_path,
            ).build("1", "aria")
        self.assertEqual(package["graph"]["source"], "cache")
        selected = {item["path"] for item in package["files"]}
        self.assertIn("frontend/src/api/client.ts", selected)
        self.assertIn("frontend/src/pages/Login.tsx", selected)

    def test_invalid_cache_falls_back_safely(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            graph_path = Path(temporary) / "codebase-graph.json"
            graph_path.write_text("{not-json", encoding="utf-8")
            package = ContextPackageBuilder(
                FIXTURE_ROOT,
                self.rules,
                graph_path=graph_path,
            ).build("1", "aria")
        self.assertEqual(package["graph"]["source"], "fallback")
        selected = {item["path"] for item in package["files"]}
        self.assertIn("frontend/src/api/client.ts", selected)


if __name__ == "__main__":
    unittest.main()
