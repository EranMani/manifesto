#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


HOOKS_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = HOOKS_DIR.parent
FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures" / "context_repo"
sys.path.insert(0, str(HOOKS_DIR))

from context_engine import (  # noqa: E402
    ContextPackageBuilder,
    _parse_context_block,
    build_dependency_graph,
    load_rules,
    normalize_commit_number,
    safe_repo_path,
)


class ContextEngineUnitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rules = load_rules(HOOKS_DIR / "context_rules.json")

    def test_rejects_path_escape(self) -> None:
        self.assertIsNone(safe_repo_path(FIXTURE_ROOT, "../outside.py"))

    def test_normalizes_letter_suffixed_commit(self) -> None:
        self.assertEqual(normalize_commit_number("c29a"), "29A")

    def test_resolves_python_and_typescript_imports(self) -> None:
        graph = build_dependency_graph(FIXTURE_ROOT, self.rules)
        self.assertIn(
            "backend/app/schemas/auth.py",
            graph["backend/app/api/v1/auth.py"],
        )
        self.assertIn(
            "frontend/src/api/client.ts",
            graph["frontend/src/api/auth.ts"],
        )

    def test_context_parser_keeps_first_list_item(self) -> None:
        spec = """
## context
```
initial_context:
  - first.md
  - second.md
forbidden:
  - backend/
  - frontend/
```
"""
        parsed = _parse_context_block(spec)
        self.assertEqual(parsed["tier0"], ["first.md", "second.md"])
        self.assertEqual(parsed["forbidden"], ["backend/", "frontend/"])

    def test_context_parser_accepts_legacy_tier0_key(self) -> None:
        spec = """
## context
```
tier0:
  - legacy.md
```
"""
        parsed = _parse_context_block(spec)
        self.assertEqual(parsed["tier0"], ["legacy.md"])

    def test_explicit_change_context_suppresses_graph_expansion(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "commit-specs").mkdir()
            (root / "src").mkdir()
            (root / "src" / "primary.py").write_text(
                "from src import dependency\n",
                encoding="utf-8",
            )
            (root / "src" / "dependency.py").write_text("VALUE = 1\n", encoding="utf-8")
            (root / "commit-specs" / "commit-01.md").write_text(
                """
# Commit 01 - explicit-context

## Context

```yaml
initial_context:
  - src/primary.py
```

## Files To Modify Or Add

| File | Type | Purpose |
|---|---|---|
| `src/primary.py` | edit | Update behavior |
""".strip(),
                encoding="utf-8",
            )
            rules = {
                "agents": {"rex": {"structural_by_area": {}}},
                "graph": {"agent_categories": {}, "max_hubs_per_package": 0},
                "budget": {
                    "max_files": 6,
                    "max_chars_per_file": 3900,
                    "max_total_chars": 18000,
                    "reserve_chars": 3000,
                },
            }
            builder = ContextPackageBuilder(root, rules, graph_path=None)
            builder.graph = {"src/primary.py": {"src/dependency.py"}}
            builder.reverse = {"src/dependency.py": {"src/primary.py"}}

            package = builder.build("1", "rex")

            selected = {item["path"] for item in package["files"]}
            self.assertIn("src/primary.py", selected)
            self.assertNotIn("src/dependency.py", selected)

    def test_contract_bridge_and_dependency_expansion(self) -> None:
        package = ContextPackageBuilder(FIXTURE_ROOT, self.rules).build("1", "aria")
        selected = {item["path"] for item in package["files"]}
        self.assertIn("frontend/src/api/auth.ts", selected)
        self.assertIn("frontend/src/api/client.ts", selected)
        self.assertIn("backend/app/schemas/auth.py", selected)
        self.assertIn("backend/app/api/v1/auth.py", selected)
        self.assertNotIn("backend/app/services/auth.py", selected)
        self.assertEqual(package["mode"], "shadow")


class ManifestoHistoricalCases(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rules = load_rules(HOOKS_DIR / "context_rules.json")
        cls.builder = ContextPackageBuilder(REPO_ROOT, cls.rules)
        cls.cases = json.loads(
            (Path(__file__).resolve().parent / "context_cases.json").read_text(
                encoding="utf-8"
            )
        )

    def test_required_context_recall(self) -> None:
        failures: list[str] = []
        for case in self.cases:
            with self.subTest(case=case["name"]):
                package = self.builder.build(case["commit"], case["agent"])
                selected = {item["path"] for item in package["files"]}
                missing = sorted(set(case["required"]) - selected)
                leaked = sorted(set(case["irrelevant"]) & selected)
                if missing:
                    failures.append(f"{case['name']} missing {missing}")
                if leaked:
                    failures.append(f"{case['name']} included irrelevant {leaked}")
                self.assertLessEqual(
                    len(selected),
                    int(self.rules["budget"]["max_files"]),
                )
        self.assertEqual(failures, [], "\n".join(failures))

    def test_cache_and_fallback_preserve_required_context(self) -> None:
        graph_path = REPO_ROOT / ".context" / "index" / "codebase-graph.json"
        if not graph_path.is_file():
            self.skipTest("Run hooks/build_codebase_graph.py first")
        cached_builder = ContextPackageBuilder(
            REPO_ROOT,
            self.rules,
            graph_path=graph_path,
        )
        fallback_builder = ContextPackageBuilder(
            REPO_ROOT,
            self.rules,
            graph_path=REPO_ROOT / ".context" / "index" / "missing-graph.json",
        )
        with self.subTest(graph="cache"):
            self.assertEqual(cached_builder.graph_metadata["source"], "cache")
        with self.subTest(graph="fallback"):
            self.assertEqual(fallback_builder.graph_metadata["source"], "fallback")
        for case in self.cases:
            with self.subTest(case=case["name"]):
                cached = cached_builder.build(case["commit"], case["agent"])
                fallback = fallback_builder.build(case["commit"], case["agent"])
                required = set(case["required"])
                cached_paths = {item["path"] for item in cached["files"]}
                fallback_paths = {item["path"] for item in fallback["files"]}
                self.assertFalse(required - cached_paths)
                self.assertFalse(required - fallback_paths)


if __name__ == "__main__":
    unittest.main()
