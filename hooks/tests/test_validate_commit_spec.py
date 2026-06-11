#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


HOOKS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HOOKS_DIR))

from validate_commit_spec import commit_key, validate_commit_spec, validate_pending_graph  # noqa: E402


def valid_spec(
    *,
    commit: int | str = 30,
    name: str = "small-change",
    depends_on: str = "C29",
    budget_override: str = "",
    extra_files: str = "",
    owner: str = "rex",
    milestone: str = "no",
    checkpoint: str = "**Next milestone:** C31.",
    primary_behavior: str = "Implement one small behavior.",
    behavior_count: str = "1",
) -> str:
    return f"""\
# Commit {commit} - `{name}` - Rex

**Phase:** Test
**Owner:** {owner}
**Depends on:** {depends_on}
**Estimated diff lines:** 120
**Primary behavior count:** {behavior_count}
**Developer test milestone:** {milestone}

## Primary Behavior

{primary_behavior}

## Semantic Fit Review

- **Atomic outcome:** One independently testable result.
- **Failure boundary:** Failure does not reopen deferred work.
- **Budget rationale:** Two files and one focused command fit one invocation.

## Execution Budget

```yaml
execution_budget:
  max_primary_files: 2
  max_changed_files: 4
  max_context_files: 6
  max_context_chars: 15000
  max_estimated_diff_lines: 350
  max_agent_invocations: 1
  max_tool_calls: 18
  max_expansions: 2
  max_implementor_tokens: 45000
{budget_override}```

## Context

```yaml
primary_files:
  - app.py
initial_context:
  - commit-specs/commit-30.md
  - app.py
  - test_app.py
forbidden:
  - frontend/
```

## Files To Modify Or Add

| File | Type | Purpose |
|---|---|---|
| `app.py` | edit | behavior |
| `test_app.py` | edit | tests |
{extra_files}

## Contract

Input and output behavior are exact.

## Environment Prerequisites

- Python available.

## Verification Command

```powershell
python -m pytest test_app.py -q
```

## Focused Tests

- Happy path and rejection path.

## Done When

- [ ] The behavior is implemented.
- [ ] The verification command passes.

## Developer Test Checkpoint

{checkpoint}

## Not In This Commit

- Deferred behavior.

## Return Contract

Return the required Human Summary and telemetry.
"""


class ValidateCommitSpecTests(unittest.TestCase):
    def make_repo(self, spec: str, owner: str = "rex") -> Path:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        (root / "commit-specs").mkdir()
        (root / "commit-specs" / "commit-30.md").write_text(spec, encoding="utf-8")
        (root / "commit-protocol.md").write_text(
            "| # | Name | Assignee | Status |\n"
            "|---|---|---|---|\n"
            "| 29 | completed | rex | done |\n"
            f"| 30 | small-change | {owner} | pending |\n",
            encoding="utf-8",
        )
        (root / "project-state.json").write_text(
            json.dumps({
                "next_commit": "30",
                "next_commit_name": "small-change",
                "next_commit_assignee": owner,
            }),
            encoding="utf-8",
        )
        return root

    def make_graph_repo(
        self,
        specs: dict[int | str, str],
        rows: list[tuple[int | str, str, str]],
    ) -> Path:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        (root / "commit-specs").mkdir()
        for commit, spec in specs.items():
            filename = f"commit-{commit_key(commit)[1:].lower()}.md"
            (root / "commit-specs" / filename).write_text(
                spec,
                encoding="utf-8",
            )
        protocol = [
            "| # | Name | Assignee | Status |",
            "|---|---|---|---|",
            "| 29 | completed | rex | done |",
        ]
        protocol.extend(
            f"| {commit} | {name} | {owner} | pending |"
            for commit, name, owner in rows
        )
        (root / "commit-protocol.md").write_text(
            "\n".join(protocol) + "\n",
            encoding="utf-8",
        )
        (root / "project-state.json").write_text(
            json.dumps({
                "next_commit": str(rows[0][0]),
                "next_commit_name": rows[0][1],
                "next_commit_assignee": rows[0][2],
            }),
            encoding="utf-8",
        )
        return root

    def test_valid_spec_passes(self) -> None:
        root = self.make_repo(valid_spec())
        result = validate_commit_spec(root, "30", "rex")
        self.assertEqual(result["status"], "valid")
        self.assertEqual(result["violations"], [])

    def test_budget_overflow_requires_split(self) -> None:
        root = self.make_repo(
            valid_spec().replace("max_tool_calls: 18", "max_tool_calls: 19")
        )
        result = validate_commit_spec(root, "30", "rex")
        self.assertEqual(result["status"], "split_required")
        self.assertIn("max_tool_calls", {item["rule"] for item in result["violations"]})

    def test_default_effective_budget_includes_max_total_tokens(self) -> None:
        root = self.make_repo(valid_spec())
        result = validate_commit_spec(root, "30", "rex")
        self.assertEqual(result["status"], "valid")
        self.assertEqual(result["budget"]["max_total_tokens"], 60000)

    def test_bootstrap_exception_overrides_effective_budget(self) -> None:
        override = (
            "bootstrap_exception:\n"
            '  reason: "greenfield-module"\n'
            "  max_tool_calls: 28\n"
            "  max_expansions: 2\n"
            "  max_implementor_tokens: 55000\n"
            "  max_total_tokens: 70000\n"
            "  max_agent_invocations: 1\n"
        )
        root = self.make_repo(valid_spec(budget_override=override))
        result = validate_commit_spec(root, "30", "rex")
        self.assertEqual(result["status"], "valid")
        self.assertEqual(result["budget"]["max_tool_calls"], 28)
        self.assertEqual(result["budget"]["max_expansions"], 2)
        self.assertEqual(result["budget"]["max_implementor_tokens"], 55000)
        self.assertEqual(result["budget"]["max_total_tokens"], 70000)
        self.assertEqual(result["budget"]["max_agent_invocations"], 1)

    def test_bootstrap_exception_unrecognized_field_fails(self) -> None:
        override = (
            "bootstrap_exception:\n"
            '  reason: "greenfield-module"\n'
            "  max_tool_calls: 28\n"
            "  max_funky_field: 5\n"
        )
        root = self.make_repo(valid_spec(budget_override=override))
        result = validate_commit_spec(root, "30", "rex")
        self.assertEqual(result["status"], "split_required")
        self.assertIn(
            "bootstrap_exception_field",
            {item["rule"] for item in result["violations"]},
        )

    def test_bootstrap_exception_ceiling_exceeded_fails(self) -> None:
        override = (
            "bootstrap_exception:\n"
            '  reason: "greenfield-module"\n'
            "  max_tool_calls: 29\n"
        )
        root = self.make_repo(valid_spec(budget_override=override))
        result = validate_commit_spec(root, "30", "rex")
        self.assertEqual(result["status"], "split_required")
        self.assertIn(
            "bootstrap_exception_ceiling",
            {item["rule"] for item in result["violations"]},
        )

    def test_missing_not_in_commit_fails(self) -> None:
        spec = valid_spec().split("## Not In This Commit", 1)[0]
        root = self.make_repo(spec)
        result = validate_commit_spec(root, "30", "rex")
        self.assertIn("not_in_commit", {item["rule"] for item in result["violations"]})

    def test_owner_mismatch_fails(self) -> None:
        root = self.make_repo(valid_spec(owner="nova"), owner="rex")
        result = validate_commit_spec(root, "30", "rex")
        self.assertIn("owner_state", {item["rule"] for item in result["violations"]})

    def test_too_many_changed_files_fails(self) -> None:
        rows = "".join(
            f"| `extra{i}.py` | edit | extra |\n"
            for i in range(3)
        )
        root = self.make_repo(valid_spec(extra_files=rows))
        result = validate_commit_spec(root, "30", "rex")
        self.assertIn("max_changed_files", {item["rule"] for item in result["violations"]})

    def test_primary_behavior_count_must_be_one(self) -> None:
        root = self.make_repo(valid_spec(behavior_count="2"))
        result = validate_commit_spec(root, "30", "rex")
        self.assertIn(
            "primary_behavior_count",
            {item["rule"] for item in result["violations"]},
        )

    def test_semantic_fit_review_requires_all_fields(self) -> None:
        spec = valid_spec().replace(
            "- **Budget rationale:** Two files and one focused command fit one invocation.\n",
            "",
        )
        root = self.make_repo(spec)
        result = validate_commit_spec(root, "30", "rex")
        self.assertIn(
            "semantic_fit_review",
            {item["rule"] for item in result["violations"]},
        )

    def test_multiple_primary_behavior_items_require_split(self) -> None:
        root = self.make_repo(
            valid_spec(primary_behavior="- First behavior.\n- Second behavior.")
        )
        result = validate_commit_spec(root, "30", "rex")
        self.assertIn(
            "primary_behavior_structure",
            {item["rule"] for item in result["violations"]},
        )

    def test_milestone_requires_manual_test_fields(self) -> None:
        root = self.make_repo(
            valid_spec(
                milestone="yes",
                checkpoint="**Ready now:** Dashboard is visible.",
            )
        )
        result = validate_commit_spec(root, "30", "rex")
        self.assertIn(
            "developer_test_checkpoint",
            {item["rule"] for item in result["violations"]},
        )

    def test_complete_milestone_passes(self) -> None:
        checkpoint = """\
**Ready now:** Dashboard is visible.
**How to test:** Run the server and open `/dashboard`.
**Expected result:** Invocation rows are visible.
**Still incomplete:** Product UI work."""
        root = self.make_repo(valid_spec(milestone="yes", checkpoint=checkpoint))
        result = validate_commit_spec(root, "30", "rex")
        self.assertEqual(result["status"], "valid")

    def test_missing_dependency_fails(self) -> None:
        root = self.make_repo(valid_spec(depends_on="C99"))
        result = validate_commit_spec(root, "30", "rex")
        self.assertIn(
            "dependency_missing",
            {item["rule"] for item in result["violations"]},
        )

    def test_placeholder_dependency_fails(self) -> None:
        root = self.make_repo(valid_spec(depends_on="CXX"))
        result = validate_commit_spec(root, "30", "rex")
        self.assertIn(
            "dependency_format",
            {item["rule"] for item in result["violations"]},
        )

    def test_changed_file_outside_owner_domain_fails(self) -> None:
        root = self.make_repo(valid_spec())
        (root / "hooks").mkdir()
        (root / "hooks" / "agent-config.json").write_text(
            json.dumps({
                "universal_allowed": [],
                "agents": {
                    "rex@example.com": {
                        "name": "Rex",
                        "domains": ["backend/"],
                    },
                },
            }),
            encoding="utf-8",
        )
        result = validate_commit_spec(root, "30", "rex")
        self.assertIn(
            "file_ownership",
            {item["rule"] for item in result["violations"]},
        )

    def test_valid_pending_graph_passes(self) -> None:
        specs = {
            30: valid_spec(commit=30, name="first", depends_on="C29"),
            31: valid_spec(
                commit=31,
                name="second",
                depends_on="C30",
                checkpoint="**Next milestone:** C32.",
            ),
        }
        root = self.make_graph_repo(
            specs,
            [(30, "first", "rex"), (31, "second", "rex")],
        )
        result = validate_pending_graph(root)
        self.assertEqual(result["status"], "valid")

    def test_pending_graph_accepts_letter_suffixed_insertion(self) -> None:
        specs = {
            "29A": valid_spec(
                commit="29A",
                name="preflight",
                depends_on="C29",
                owner="adam",
            ),
            30: valid_spec(commit=30, name="first", depends_on="C29A"),
        }
        root = self.make_graph_repo(
            specs,
            [("29A", "preflight", "adam"), (30, "first", "rex")],
        )
        result = validate_pending_graph(root)
        self.assertEqual(result["status"], "valid")
        self.assertEqual(result["pending_commits"], ["C29A", "C30"])

    def test_pending_graph_rejects_future_dependency_and_cycle(self) -> None:
        specs = {
            30: valid_spec(commit=30, name="first", depends_on="C31"),
            31: valid_spec(
                commit=31,
                name="second",
                depends_on="C30",
                checkpoint="**Next milestone:** C32.",
            ),
        }
        root = self.make_graph_repo(
            specs,
            [(30, "first", "rex"), (31, "second", "rex")],
        )
        result = validate_pending_graph(root)
        rules = {item["rule"] for item in result["violations"]}
        self.assertIn("dependency_order", rules)
        self.assertIn("dependency_cycle", rules)


if __name__ == "__main__":
    unittest.main()
