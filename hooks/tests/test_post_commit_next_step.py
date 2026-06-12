#!/usr/bin/env python3

from __future__ import annotations

import sys
from pathlib import Path


HOOKS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HOOKS_DIR))

import post_commit_next_step as pcns  # noqa: E402


PROTOCOL_CONTENT = (
    "| 30 | some-feature | Rex | pending |\n"
    "| 31 | other-feature | Adam | pending |\n"
)

PROTOCOL_CONTENT_DONE = (
    "| 30 | some-feature | Rex | done . 2026-01-01 |\n"
    "| 31 | other-feature | Adam | pending |\n"
)


def _wire_paths(monkeypatch, tmp_path: Path, protocol_content: str | None) -> Path:
    protocol_file = tmp_path / "commit-protocol.md"
    if protocol_content is not None:
        protocol_file.write_text(protocol_content, encoding="utf-8")
    runtime_flag = tmp_path / ".context" / "runtime" / "last_protocol_commit.flag"
    monkeypatch.setattr(pcns, "PROTOCOL_FILE", protocol_file)
    monkeypatch.setattr(pcns, "RUNTIME_FLAG", runtime_flag)
    return runtime_flag


def test_chore_commit_with_no_commit_marker_is_silent(monkeypatch, tmp_path, capsys) -> None:
    runtime_flag = _wire_paths(monkeypatch, tmp_path, PROTOCOL_CONTENT)
    monkeypatch.setattr(
        pcns, "get_last_commit_message",
        lambda: "chore(state): advance state after C-30",
    )

    assert pcns.main() == 0
    captured = capsys.readouterr()
    assert captured.out == ""
    assert not runtime_flag.exists()


def test_commit_marker_with_pending_row_advances_and_writes_flag(monkeypatch, tmp_path, capsys) -> None:
    runtime_flag = _wire_paths(monkeypatch, tmp_path, PROTOCOL_CONTENT)
    monkeypatch.setattr(
        pcns, "get_last_commit_message",
        lambda: "feat(x): some change\n\nCommit #30\n",
    )

    assert pcns.main() == 0
    captured = capsys.readouterr()
    assert "Commit 30" in captured.out
    assert runtime_flag.exists()
    assert runtime_flag.read_text(encoding="utf-8") == "30"

    updated = pcns.PROTOCOL_FILE.read_text(encoding="utf-8")
    assert "pending" not in updated.splitlines()[0]


def test_commit_marker_with_already_done_row_is_silent(monkeypatch, tmp_path, capsys) -> None:
    runtime_flag = _wire_paths(monkeypatch, tmp_path, PROTOCOL_CONTENT_DONE)
    monkeypatch.setattr(
        pcns, "get_last_commit_message",
        lambda: "feat(x): some change\n\nCommit #30\n",
    )

    assert pcns.main() == 0
    captured = capsys.readouterr()
    assert captured.out == ""
    assert not runtime_flag.exists()


def test_missing_protocol_file_is_silent(monkeypatch, tmp_path, capsys) -> None:
    runtime_flag = _wire_paths(monkeypatch, tmp_path, None)
    monkeypatch.setattr(
        pcns, "get_last_commit_message",
        lambda: "feat(x): some change\n\nCommit #30\n",
    )

    assert pcns.main() == 0
    captured = capsys.readouterr()
    assert captured.out == ""
    assert not runtime_flag.exists()
