#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


HOOKS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HOOKS_DIR))

from pre_commit_check import (  # noqa: E402
    DirectExecutionResolutionError,
    check_domain_boundaries,
    planned_files_for_commit,
)


PRE_COMMIT_CHECK = HOOKS_DIR / "pre_commit_check.py"


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


def test_claude_direct_without_commit_number_hard_fails(tmp_path: Path) -> None:
    _write_spec(tmp_path)
    message = "fix(example): implement behavior\n\nExecution: Claude-direct"

    with pytest.raises(DirectExecutionResolutionError, match="Commit #NN"):
        planned_files_for_commit(tmp_path, message)


def test_claude_direct_with_missing_spec_hard_fails(tmp_path: Path) -> None:
    _write_spec(tmp_path)
    message = "fix(example): implement behavior\n\nCommit #99\nExecution: Claude-direct"

    with pytest.raises(DirectExecutionResolutionError, match="commit-99.md does not exist"):
        planned_files_for_commit(tmp_path, message)


def test_claude_direct_with_missing_files_table_hard_fails(tmp_path: Path) -> None:
    specs = tmp_path / "commit-specs"
    specs.mkdir()
    (specs / "commit-31.md").write_text(
        """
# Commit 31 - example

## Contract

No Files To Modify Or Add section here.
""".strip(),
        encoding="utf-8",
    )
    message = "fix(example): implement behavior\n\nCommit #31\nExecution: Claude-direct"

    with pytest.raises(DirectExecutionResolutionError, match="Files To Modify Or Add"):
        planned_files_for_commit(tmp_path, message)


def test_claude_direct_with_empty_files_table_hard_fails(tmp_path: Path) -> None:
    specs = tmp_path / "commit-specs"
    specs.mkdir()
    (specs / "commit-32.md").write_text(
        """
# Commit 32 - example

## Files To Modify Or Add

| File | Type | Purpose |
|---|---|---|

## Contract

Example.
""".strip(),
        encoding="utf-8",
    )
    message = "fix(example): implement behavior\n\nCommit #32\nExecution: Claude-direct"

    with pytest.raises(DirectExecutionResolutionError, match="no file rows"):
        planned_files_for_commit(tmp_path, message)


def test_claude_domain_includes_pre_commit_check_exception() -> None:
    """hooks/agent-config.json must list pre_commit_check.py and its test file as
    Claude's narrow exception inside Adam's hooks/ domain (CLAUDE.md "Files You Own")."""
    config = json.loads((HOOKS_DIR / "agent-config.json").read_text(encoding="utf-8"))
    domains = config["agents"]["claude@anthropic.com"]["domains"]

    assert "hooks/pre_commit_check.py" in domains
    assert "hooks/tests/test_pre_commit_check.py" in domains


# --- End-to-end bypass-env-var regression tests --------------------------------


def _init_repo(tmp_path: Path, config: dict) -> Path:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    (tmp_path / "hooks").mkdir()
    (tmp_path / "hooks" / "agent-config.json").write_text(json.dumps(config), encoding="utf-8")
    return tmp_path


def _stage(repo: Path, rel_path: str, content: str = "x") -> None:
    target = repo / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    subprocess.run(["git", "add", rel_path], cwd=repo, check=True)


def _run_check(repo: Path, message: str, env_overrides: dict) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env.pop("ERAN_COMMIT", None)
    env.pop("CLAUDE_COMMIT", None)
    env["GIT_MESSAGE"] = message
    env.update(env_overrides)
    return subprocess.run(
        [sys.executable, str(PRE_COMMIT_CHECK)],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
    )


DOMAIN_VIOLATION_CONFIG = {
    "initialized": True,
    "universal_allowed": ["project-state.json"],
    "agents": {
        "claude@anthropic.com": {
            "name": "Claude",
            "domains": ["CLAUDE.md"],
        }
    },
}

DOMAIN_VIOLATION_MESSAGE = (
    "fix(workflow): edit unrelated hooks file\n\n"
    "Co-Authored-By: Claude <claude@anthropic.com>"
)


def test_claude_commit_env_does_not_bypass_validation(tmp_path: Path) -> None:
    """CLAUDE_COMMIT=1 must not skip pre_commit_check.py — a domain violation
    still hard-fails the commit."""
    repo = _init_repo(tmp_path, DOMAIN_VIOLATION_CONFIG)
    _stage(repo, "hooks/unrelated_script.py")

    result = _run_check(repo, DOMAIN_VIOLATION_MESSAGE, {"CLAUDE_COMMIT": "1"})

    assert result.returncode == 2
    assert "Domain boundary violation" in result.stdout


def test_eran_commit_env_bypasses_validation(tmp_path: Path) -> None:
    """ERAN_COMMIT=1 is the only full bypass — the same domain violation passes."""
    repo = _init_repo(tmp_path, DOMAIN_VIOLATION_CONFIG)
    _stage(repo, "hooks/unrelated_script.py")

    result = _run_check(repo, DOMAIN_VIOLATION_MESSAGE, {"ERAN_COMMIT": "1"})

    assert result.returncode == 0
    assert "ERAN_COMMIT=1" in result.stdout


def test_valid_claude_direct_commit_passes_normally(tmp_path: Path) -> None:
    """A CLAUDE_COMMIT=1 commit whose staged files match the spec's
    'Files To Modify Or Add' table passes full validation."""
    config = {
        "initialized": True,
        "universal_allowed": ["project-state.json"],
        "agents": {
            "claude@anthropic.com": {
                "name": "Claude",
                "domains": ["CLAUDE.md"],
            }
        },
    }
    repo = _init_repo(tmp_path, config)
    (repo / "commit-specs").mkdir()
    (repo / "commit-specs" / "commit-50.md").write_text(
        """
# Commit 50 - example

## Files To Modify Or Add

| File | Type | Purpose |
|---|---|---|
| `backend/app/example.py` | edit | Implement behavior |

## Contract

Example.
""".strip(),
        encoding="utf-8",
    )
    _stage(repo, "backend/app/example.py")

    finalize_dir = repo / ".context" / "finalize"
    finalize_dir.mkdir(parents=True)
    (finalize_dir / "C50.json").write_text(json.dumps({
        "commit": "50", "agent": "claude", "execution": "claude-direct",
        "checks_passed": True, "timestamp": "2026-06-13T00:00:00+00:00",
    }), encoding="utf-8")

    telemetry_dir = repo / ".context" / "telemetry"
    telemetry_dir.mkdir(parents=True)
    (telemetry_dir / "C50-orchestrator.json").write_text(json.dumps({
        "commit": "C50", "status": "completed",
        "owner": "claude", "executor": "claude",
        "execution_mode": "claude-direct", "scope_kind": "execution",
        "capture_window": "full-execution",
        "started_at": "2026-06-13T00:00:00+00:00", "ended_at": "2026-06-13T00:05:00+00:00",
        "tool_calls": 3, "read_paths": [], "write_paths": [], "searches": [], "commands": [],
    }), encoding="utf-8")

    message = (
        "fix(example): implement behavior here\n\n"
        "Commit #50\n\n"
        "Execution: Claude-direct\n\n"
        "Co-Authored-By: Claude <claude@anthropic.com>"
    )

    result = _run_check(repo, message, {"CLAUDE_COMMIT": "1"})

    assert result.returncode == 0
    assert "Pre-commit check passed" in result.stdout


# --- Orchestrator telemetry marker gate (C38A) ----------------------------------


def _setup_valid_c50_commit(tmp_path: Path) -> tuple[Path, str]:
    """Build a repo staged for a valid Commit #50 with a passing finalize marker
    (but no orchestrator telemetry marker yet)."""
    config = {
        "initialized": True,
        "universal_allowed": ["project-state.json"],
        "agents": {
            "claude@anthropic.com": {
                "name": "Claude",
                "domains": ["CLAUDE.md"],
            }
        },
    }
    repo = _init_repo(tmp_path, config)
    (repo / "commit-specs").mkdir()
    (repo / "commit-specs" / "commit-50.md").write_text(
        """
# Commit 50 - example

## Files To Modify Or Add

| File | Type | Purpose |
|---|---|---|
| `backend/app/example.py` | edit | Implement behavior |

## Contract

Example.
""".strip(),
        encoding="utf-8",
    )
    _stage(repo, "backend/app/example.py")

    finalize_dir = repo / ".context" / "finalize"
    finalize_dir.mkdir(parents=True)
    (finalize_dir / "C50.json").write_text(json.dumps({
        "commit": "50", "agent": "claude", "execution": "claude-direct",
        "checks_passed": True, "timestamp": "2026-06-13T00:00:00+00:00",
    }), encoding="utf-8")

    message = (
        "fix(example): implement behavior here\n\n"
        "Commit #50\n\n"
        "Execution: Claude-direct\n\n"
        "Co-Authored-By: Claude <claude@anthropic.com>"
    )
    return repo, message


def test_missing_orchestrator_marker_blocks(tmp_path: Path) -> None:
    repo, message = _setup_valid_c50_commit(tmp_path)

    result = _run_check(repo, message, {"CLAUDE_COMMIT": "1"})

    assert result.returncode == 2
    assert "prepare_claude_direct.py --commit C50 --owner OWNER" in result.stdout
    assert "finalize_commit.py" in result.stdout


def test_completed_matching_orchestrator_marker_passes(tmp_path: Path) -> None:
    repo, message = _setup_valid_c50_commit(tmp_path)

    telemetry_dir = repo / ".context" / "telemetry"
    telemetry_dir.mkdir(parents=True)
    (telemetry_dir / "C50-orchestrator.json").write_text(json.dumps({
        "commit": "C50", "status": "completed",
        "owner": "claude", "executor": "claude",
        "execution_mode": "claude-direct", "scope_kind": "execution",
        "capture_window": "full-execution",
        "started_at": "2026-06-13T00:00:00+00:00", "ended_at": "2026-06-13T00:05:00+00:00",
        "tool_calls": 3, "read_paths": [], "write_paths": [], "searches": [], "commands": [],
    }), encoding="utf-8")

    result = _run_check(repo, message, {"CLAUDE_COMMIT": "1"})

    assert result.returncode == 0
    assert "Pre-commit check passed" in result.stdout


def test_completed_legacy_scope_blocks_direct_commit(tmp_path: Path) -> None:
    repo, message = _setup_valid_c50_commit(tmp_path)
    telemetry_dir = repo / ".context" / "telemetry"
    telemetry_dir.mkdir(parents=True)
    (telemetry_dir / "C50-orchestrator.json").write_text(json.dumps({
        "commit": "C50", "status": "completed", "tool_calls": 0,
    }), encoding="utf-8")

    result = _run_check(repo, message, {"CLAUDE_COMMIT": "1"})

    assert result.returncode == 2
    assert "prepare_claude_direct.py --commit C50 --owner OWNER" in result.stdout


def test_running_orchestrator_marker_blocks(tmp_path: Path) -> None:
    """A scope file left in 'running' status (stop-orchestrator never ran) blocks,
    same as missing."""
    repo, message = _setup_valid_c50_commit(tmp_path)

    telemetry_dir = repo / ".context" / "telemetry"
    telemetry_dir.mkdir(parents=True)
    (telemetry_dir / "C50-orchestrator.json").write_text(json.dumps({
        "commit": "C50", "status": "running",
        "started_at": "2026-06-13T00:00:00+00:00", "ended_at": None,
        "tool_calls": 1, "read_paths": [], "write_paths": [], "searches": [], "commands": [],
    }), encoding="utf-8")

    result = _run_check(repo, message, {"CLAUDE_COMMIT": "1"})

    assert result.returncode == 2
    assert "prepare_claude_direct.py --commit C50 --owner OWNER" in result.stdout


def test_orchestrator_marker_commit_mismatch_blocks(tmp_path: Path) -> None:
    """A scope file whose 'commit' field doesn't match the staged commit blocks,
    same as missing."""
    repo, message = _setup_valid_c50_commit(tmp_path)

    telemetry_dir = repo / ".context" / "telemetry"
    telemetry_dir.mkdir(parents=True)
    (telemetry_dir / "C50-orchestrator.json").write_text(json.dumps({
        "commit": "C49", "status": "completed",
        "started_at": "2026-06-13T00:00:00+00:00", "ended_at": "2026-06-13T00:05:00+00:00",
        "tool_calls": 3, "read_paths": [], "write_paths": [], "searches": [], "commands": [],
    }), encoding="utf-8")

    result = _run_check(repo, message, {"CLAUDE_COMMIT": "1"})

    assert result.returncode == 2
    assert "prepare_claude_direct.py --commit C50 --owner OWNER" in result.stdout


def test_chore_state_commit_exempt_from_orchestrator_marker(tmp_path: Path) -> None:
    """A chore(state) commit with no Commit #NN + execution marker pair is exempt
    regardless of telemetry scope state."""
    config = {
        "initialized": True,
        "universal_allowed": ["project-state.json"],
        "agents": {
            "claude@anthropic.com": {
                "name": "Claude",
                "domains": ["CLAUDE.md"],
            }
        },
    }
    repo = _init_repo(tmp_path, config)
    _stage(repo, "project-state.json", "{}")

    message = "chore(state): advance state after C-50"

    result = _run_check(repo, message, {"CLAUDE_COMMIT": "1"})

    assert result.returncode == 0
    assert "Pre-commit check passed" in result.stdout
