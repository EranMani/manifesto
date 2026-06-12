#!/usr/bin/env python3

from __future__ import annotations

import sys
from pathlib import Path


HOOKS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HOOKS_DIR))

from pre_commit_check import (  # noqa: E402
    check_domain_boundaries,
    planned_files_for_commit,
)


CONFIG = {
    "universal_allowed": ["project-state.json"],
    "agents": {
        "claude@anthropic.com": {
            "name": "Claude",
            "domains": ["CLAUDE.md", ".claude/commands/"],
        }
    },
}


def _write_spec(root: Path) -> None:
    specs = root / "commit-specs"
    specs.mkdir()
    (specs / "commit-30.md").write_text(
        """
# Commit 30 - example

## Files To Modify Or Add

| File | Type | Purpose |
|---|---|---|
| `backend/app/example.py` | edit | Implement behavior |
| `backend/tests/test_example.py` | edit | Verify behavior |

## Contract

Example.
""".strip(),
        encoding="utf-8",
    )


def test_claude_direct_allows_only_planned_files(tmp_path: Path) -> None:
    _write_spec(tmp_path)
    message = "fix(example): implement behavior\n\nCommit #30\nExecution: Claude-direct"

    allowed = planned_files_for_commit(tmp_path, message)

    assert allowed == {
        "backend/app/example.py",
        "backend/tests/test_example.py",
    }
    assert check_domain_boundaries(
        ["backend/app/example.py", "project-state.json"],
        "claude@anthropic.com",
        CONFIG,
        direct_allowed=allowed,
    ) == []
    errors = check_domain_boundaries(
        ["backend/app/unplanned.py"],
        "claude@anthropic.com",
        CONFIG,
        direct_allowed=allowed,
    )
    assert errors


def test_claude_direct_requires_explicit_marker(tmp_path: Path) -> None:
    _write_spec(tmp_path)

    allowed = planned_files_for_commit(tmp_path, "fix(example): implement\n\nCommit #30")

    assert allowed == set()
