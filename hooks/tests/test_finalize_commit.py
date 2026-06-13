#!/usr/bin/env python3
"""Tests for hooks/finalize_commit.py and the pre_commit_check.py finalize-marker gate."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

HOOKS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HOOKS_DIR))

import finalize_commit  # noqa: E402

PRE_COMMIT_CHECK = HOOKS_DIR / "pre_commit_check.py"


# ---------------------------------------------------------------------------
# finalize_commit.py pipeline ordering
# ---------------------------------------------------------------------------

def _patch_steps(monkeypatch, calls, verify_result=(True, {"spec_validation": "ok"})):
    monkeypatch.setattr(finalize_commit, "step_verify",
                         lambda *a, **k: (calls.append("verify"), verify_result)[1])
    monkeypatch.setattr(finalize_commit, "step_render_dashboard",
                         lambda *a, **k: calls.append("render"))
    monkeypatch.setattr(finalize_commit, "step_write_notify",
                         lambda *a, **k: calls.append("notify"))
    monkeypatch.setattr(finalize_commit, "step_write_marker",
                         lambda *a, **k: (calls.append("marker"), {})[1])


def _run_main(monkeypatch, argv):
    monkeypatch.setattr(sys, "argv", ["finalize_commit.py"] + argv)
    return finalize_commit.main()


def test_passing_pipeline_runs_in_order_skipping_dashboard(monkeypatch, capsys):
    calls = []
    _patch_steps(monkeypatch, calls)

    rc = _run_main(monkeypatch, [
        "--commit", "33B", "--agent", "claude", "--execution", "claude-direct",
        "--notify-what", "did stuff", "--notify-why", "because",
    ])

    assert rc == 0
    assert calls == ["verify", "notify", "marker"]

    summary = json.loads(capsys.readouterr().out)
    assert summary["status"] == "ready"
    assert summary["dashboard_rendered"] is False
    assert summary["notify_written"] is True
    assert summary["marker_written"] is True


def test_failing_verify_stops_before_render_notify_marker(monkeypatch, capsys):
    calls = []
    _patch_steps(monkeypatch, calls, verify_result=(False, {"forbidden_paths": "violation"}))

    rc = _run_main(monkeypatch, [
        "--commit", "33B", "--agent", "claude", "--execution", "claude-direct",
        "--notify-what", "did stuff", "--notify-why", "because",
    ])

    assert rc == 1
    assert calls == ["verify"]

    summary = json.loads(capsys.readouterr().out)
    assert summary["status"] == "blocked"
    assert summary["dashboard_rendered"] is False
    assert summary["notify_written"] is False
    assert summary["marker_written"] is False


def test_render_dashboard_flag_forces_render_on_non_fifth_commit(monkeypatch, capsys):
    calls = []
    _patch_steps(monkeypatch, calls)

    rc = _run_main(monkeypatch, [
        "--commit", "33B", "--agent", "claude", "--execution", "claude-direct",
        "--render-dashboard", "--notify-what", "did stuff", "--notify-why", "because",
    ])

    assert rc == 0
    assert calls == ["verify", "render", "notify", "marker"]
    summary = json.loads(capsys.readouterr().out)
    assert summary["dashboard_rendered"] is True


def test_fifth_commit_renders_dashboard_without_flag(monkeypatch, capsys):
    calls = []
    _patch_steps(monkeypatch, calls)

    rc = _run_main(monkeypatch, [
        "--commit", "35", "--agent", "claude", "--execution", "claude-direct",
        "--notify-what", "did stuff", "--notify-why", "because",
    ])

    assert rc == 0
    assert calls == ["verify", "render", "notify", "marker"]


def test_step_write_marker_matches_documented_schema(tmp_path, monkeypatch):
    monkeypatch.setattr(finalize_commit, "FINALIZE_DIR", tmp_path / ".context" / "finalize")

    marker = finalize_commit.step_write_marker("33B", "claude", "claude-direct")

    assert marker["commit"] == "33B"
    assert marker["agent"] == "claude"
    assert marker["execution"] == "claude-direct"
    assert marker["checks_passed"] is True
    assert "timestamp" in marker

    written = json.loads((tmp_path / ".context" / "finalize" / "C33B.json").read_text(encoding="utf-8"))
    assert written == marker


def test_step_verify_checks_worktree_not_committed_ref(monkeypatch):
    """This pipeline always runs pre-commit, so it must check the working tree
    (--worktree), not auto-resolve a committed ref that doesn't exist yet."""
    captured = {}

    def fake_main():
        captured["argv"] = list(sys.argv)
        print(json.dumps({"all_pass": True, "checks": {}}))

    monkeypatch.setattr(finalize_commit.verify_constraints, "main", fake_main)

    finalize_commit.step_verify("33B", "claude", "claude-direct", None)

    assert "--worktree" in captured["argv"]


# ---------------------------------------------------------------------------
# pre_commit_check.py finalize-marker gate (end-to-end)
# ---------------------------------------------------------------------------

CONFIG = {
    "initialized": True,
    "universal_allowed": ["project-state.json"],
    "agents": {
        "claude@anthropic.com": {
            "name": "Claude",
            "domains": [
                "hooks/finalize_commit.py",
                "hooks/tests/test_finalize_commit.py",
                ".context/finalize/",
            ],
        }
    },
}

SPEC = """\
# Commit 33B - finalize-commit-pipeline - Claude

**Owner:** claude

## Files To Modify Or Add

| File | Type | Purpose |
|---|---|---|
| `hooks/finalize_commit.py` | new | Pipeline entrypoint |

## Contract

Example.
"""

PRIMARY_MESSAGE = (
    "feat(hooks): add finalize pipeline\n\n"
    "Commit #33B\n\n"
    "Execution: Claude-direct\n\n"
    "Co-Authored-By: Claude <claude@anthropic.com>"
)

CHORE_MESSAGE = "chore(state): advance state after C-33B"


def _init_repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    (tmp_path / "hooks").mkdir()
    (tmp_path / "hooks" / "agent-config.json").write_text(json.dumps(CONFIG), encoding="utf-8")
    (tmp_path / "commit-specs").mkdir()
    (tmp_path / "commit-specs" / "commit-33B.md").write_text(SPEC, encoding="utf-8")
    return tmp_path


def _stage(repo: Path, rel_path: str, content: str = "x") -> None:
    target = repo / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    subprocess.run(["git", "add", rel_path], cwd=repo, check=True)


def _write_marker(repo: Path, name: str, payload: dict) -> None:
    marker_dir = repo / ".context" / "finalize"
    marker_dir.mkdir(parents=True, exist_ok=True)
    (marker_dir / name).write_text(json.dumps(payload), encoding="utf-8")


def _run_check(repo: Path, message: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env.pop("ERAN_COMMIT", None)
    env.pop("CLAUDE_COMMIT", None)
    env["GIT_MESSAGE"] = message
    return subprocess.run(
        [sys.executable, str(PRE_COMMIT_CHECK)],
        cwd=repo, env=env, capture_output=True, text=True,
    )


def test_blocks_primary_commit_without_marker(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    _stage(repo, "hooks/finalize_commit.py")

    result = _run_check(repo, PRIMARY_MESSAGE)

    assert result.returncode == 2
    assert "no fresh finalize marker found" in result.stdout


def test_allows_primary_commit_with_matching_marker(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    _stage(repo, "hooks/finalize_commit.py")
    _write_marker(repo, "C33B.json", {
        "commit": "33B", "agent": "claude", "execution": "claude-direct",
        "checks_passed": True, "timestamp": "2026-06-13T00:00:00+00:00",
    })

    result = _run_check(repo, PRIMARY_MESSAGE)

    assert result.returncode == 0
    assert "Pre-commit check passed" in result.stdout


def test_exempts_chore_state_commit_regardless_of_marker(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    _stage(repo, "project-state.json", "{}")

    result = _run_check(repo, CHORE_MESSAGE)

    assert result.returncode == 0
    assert "Pre-commit check passed" in result.stdout


def test_mismatched_marker_commit_blocks(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    _stage(repo, "hooks/finalize_commit.py")
    _write_marker(repo, "C33B.json", {
        "commit": "33A", "agent": "claude", "execution": "claude-direct",
        "checks_passed": True, "timestamp": "2026-06-13T00:00:00+00:00",
    })

    result = _run_check(repo, PRIMARY_MESSAGE)

    assert result.returncode == 2
    assert "no fresh finalize marker found" in result.stdout


def test_mismatched_marker_agent_blocks(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    _stage(repo, "hooks/finalize_commit.py")
    _write_marker(repo, "C33B.json", {
        "commit": "33B", "agent": "rex", "execution": "claude-direct",
        "checks_passed": True, "timestamp": "2026-06-13T00:00:00+00:00",
    })

    result = _run_check(repo, PRIMARY_MESSAGE)

    assert result.returncode == 2
    assert "no fresh finalize marker found" in result.stdout
