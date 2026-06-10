#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


HOOKS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HOOKS_DIR))

from validate_commit_spec import validate_commit_spec  # noqa: E402


def valid_spec(
    *,
    budget_override: str = "",
    extra_files: str = "",
    owner: str = "rex",
) -> str:
    return f"""\
# Commit 30 - `small-change` - Rex

**Phase:** Test
**Owner:** {owner}
**Depends on:** C29
**Estimated diff lines:** 120

## Primary Behavior

Implement one small behavior.

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

## Environment Prerequisites

- Python available.

## Verification Command

```powershell
python -m pytest test_app.py -q
```

## Focused Tests

- Happy path and rejection path.

## Not In This Commit

- Deferred behavior.
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


if __name__ == "__main__":
    unittest.main()
