#!/usr/bin/env python3
"""Tests for verify_constraints.py: command resolution, --no-persist, malformed telemetry."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

HOOKS_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = HOOKS_DIR.parent
sys.path.insert(0, str(HOOKS_DIR))

import context_telemetry  # noqa: E402
import verify_constraints  # noqa: E402


MINIMAL_SPEC = """\
# Commit 25 — llm-service-impl

## context
```yaml
tier0:
  - backend/app/services/llm.py
forbidden:
  - frontend/
estimated_reads: 5
```

## What

Implement the LLMService class.
"""


# ---------------------------------------------------------------------------
# Task 1 — Command resolution: verify-commit.md uses next_commit fields
# ---------------------------------------------------------------------------

class TestCommandResolution(unittest.TestCase):
    """verify-commit.md must reference next_commit/next_commit_assignee with --no-persist."""

    def _content(self) -> str:
        cmd_path = REPO_ROOT / ".claude" / "commands" / "verify-commit.md"
        self.assertTrue(cmd_path.is_file(),
                        f"verify-commit.md must exist at {cmd_path}")
        return cmd_path.read_text(encoding="utf-8")

    def test_file_exists_at_correct_path(self):
        cmd_path = REPO_ROOT / ".claude" / "commands" / "verify-commit.md"
        self.assertTrue(cmd_path.is_file())

    def test_uses_next_commit_not_last_completed(self):
        content = self._content()
        self.assertIn("next_commit", content,
                      "verify-commit.md must read next_commit from project-state.json")
        self.assertIn("next_commit_assignee", content,
                      "verify-commit.md must read next_commit_assignee")
        self.assertNotIn("last_completed_commit", content,
                         "verify-commit.md must NOT use last_completed_commit")

    def test_passes_worktree_and_no_persist(self):
        content = self._content()
        self.assertIn("--worktree", content,
                      "verify-commit.md must pass --worktree")
        self.assertIn("--no-persist", content,
                      "verify-commit.md must pass --no-persist")

    def test_old_command_file_removed(self):
        old_path = REPO_ROOT / ".claude" / "commands" / "verify-commit-command.md"
        self.assertFalse(old_path.is_file(),
                         "verify-commit-command.md must be removed (renamed to verify-commit.md)")


# ---------------------------------------------------------------------------
# Task 2 — Pre-commit --worktree --no-persist: no files written
# ---------------------------------------------------------------------------

class TestNoPersistFlag(unittest.TestCase):
    """--no-persist skips append_to_log, upsert_metric, and render_dashboard."""

    def _run(self, extra_args: list[str]) -> None:
        old_argv = sys.argv[:]
        try:
            sys.argv = ["verify_constraints.py", "--commit", "25", "--agent", "nova"] + extra_args
            try:
                verify_constraints.main()
            except SystemExit:
                pass
        finally:
            sys.argv = old_argv

    def test_no_persist_skips_all_write_calls(self):
        with (
            patch("verify_constraints.load_spec", return_value=MINIMAL_SPEC),
            patch("verify_constraints.load_worklog", return_value=""),
            patch("verify_constraints.git_files_changed", return_value=[]),
            patch("verify_constraints.append_to_log") as mock_log,
            patch("verify_constraints.upsert_metric") as mock_metric,
            patch("verify_constraints.render_dashboard") as mock_dash,
        ):
            self._run(["--worktree", "--no-persist"])
            mock_log.assert_not_called()
            mock_metric.assert_not_called()
            mock_dash.assert_not_called()

    def test_no_persist_produces_pass_output(self):
        output_lines: list[str] = []

        def capture_print(*args, **kwargs):
            output_lines.append(" ".join(str(a) for a in args))

        with (
            patch("verify_constraints.load_spec", return_value=MINIMAL_SPEC),
            patch("verify_constraints.load_worklog", return_value=""),
            patch("verify_constraints.git_files_changed", return_value=[]),
            patch("builtins.print", side_effect=capture_print),
        ):
            self._run(["--worktree", "--no-persist"])

        combined = "\n".join(output_lines)
        self.assertIn("PASS", combined,
                      "verify should report at least one PASS for a clean minimal spec")


# ---------------------------------------------------------------------------
# Task 3 — Post-commit persistence: files written without --no-persist
# ---------------------------------------------------------------------------

class TestPostCommitPersistence(unittest.TestCase):
    """Without --no-persist, all three write functions are called exactly once."""

    def _run(self, extra_args: list[str]) -> None:
        old_argv = sys.argv[:]
        try:
            sys.argv = ["verify_constraints.py", "--commit", "25", "--agent", "nova"] + extra_args
            try:
                verify_constraints.main()
            except SystemExit:
                pass
        finally:
            sys.argv = old_argv

    def test_persist_calls_all_write_functions(self):
        with (
            patch("verify_constraints.load_spec", return_value=MINIMAL_SPEC),
            patch("verify_constraints.load_worklog", return_value=""),
            patch("verify_constraints.git_files_changed", return_value=[]),
            patch("verify_constraints.get_tokens_from_records", return_value=None),
            patch("verify_constraints.build_metric_record",
                  return_value={"commit": "C25", "agent": "nova"}),
            patch("verify_constraints.append_to_log") as mock_log,
            patch("verify_constraints.upsert_metric") as mock_metric,
            patch("verify_constraints.render_dashboard") as mock_dash,
        ):
            self._run(["--worktree"])
            mock_log.assert_called_once()
            mock_metric.assert_called_once()
            mock_dash.assert_called_once()

    def test_no_persist_and_persist_are_mutually_exclusive(self):
        """The same invocation cannot both skip and apply writes."""
        log_calls_no_persist: list = []
        log_calls_persist: list = []

        base_patches = [
            patch("verify_constraints.load_spec", return_value=MINIMAL_SPEC),
            patch("verify_constraints.load_worklog", return_value=""),
            patch("verify_constraints.git_files_changed", return_value=[]),
            patch("verify_constraints.get_tokens_from_records", return_value=None),
            patch("verify_constraints.build_metric_record",
                  return_value={"commit": "C25", "agent": "nova"}),
            patch("verify_constraints.render_dashboard"),
            patch("verify_constraints.upsert_metric"),
        ]

        with (
            patch("verify_constraints.load_spec", return_value=MINIMAL_SPEC),
            patch("verify_constraints.load_worklog", return_value=""),
            patch("verify_constraints.git_files_changed", return_value=[]),
            patch("verify_constraints.append_to_log",
                  side_effect=lambda *a, **kw: log_calls_no_persist.append(a)),
            patch("verify_constraints.upsert_metric"),
            patch("verify_constraints.render_dashboard"),
        ):
            old_argv = sys.argv[:]
            sys.argv = ["vc", "--commit", "25", "--agent", "nova", "--worktree", "--no-persist"]
            try:
                verify_constraints.main()
            except SystemExit:
                pass
            finally:
                sys.argv = old_argv

        with (
            patch("verify_constraints.load_spec", return_value=MINIMAL_SPEC),
            patch("verify_constraints.load_worklog", return_value=""),
            patch("verify_constraints.git_files_changed", return_value=[]),
            patch("verify_constraints.get_tokens_from_records", return_value=None),
            patch("verify_constraints.build_metric_record",
                  return_value={"commit": "C25", "agent": "nova"}),
            patch("verify_constraints.append_to_log",
                  side_effect=lambda *a, **kw: log_calls_persist.append(a)),
            patch("verify_constraints.upsert_metric"),
            patch("verify_constraints.render_dashboard"),
        ):
            old_argv = sys.argv[:]
            sys.argv = ["vc", "--commit", "25", "--agent", "nova", "--worktree"]
            try:
                verify_constraints.main()
            except SystemExit:
                pass
            finally:
                sys.argv = old_argv

        self.assertEqual(len(log_calls_no_persist), 0, "--no-persist must not call append_to_log")
        self.assertEqual(len(log_calls_persist), 1, "without --no-persist, append_to_log must be called once")


# ---------------------------------------------------------------------------
# Task 4 — Malformed telemetry rejection
# ---------------------------------------------------------------------------

class TestMalformedTelemetryRejection(unittest.TestCase):
    """record_agent_self_report rejects invalid reports instead of recording misleading data."""

    def test_rejects_missing_tool_calls(self):
        with self.assertRaises(ValueError) as ctx:
            context_telemetry.record_agent_self_report("25", "nova", {
                "read_paths": ["backend/app/services/llm.py"],
                "write_paths": [],
                "searches": [],
                "commands": [],
                "expansions": [],
            })
        self.assertIn("tool_calls", str(ctx.exception))

    def test_rejects_negative_tool_calls(self):
        with self.assertRaises(ValueError) as ctx:
            context_telemetry.record_agent_self_report("25", "nova", {"tool_calls": -1})
        self.assertIn("-1", str(ctx.exception))

    def test_rejects_string_tool_calls(self):
        with self.assertRaises(ValueError):
            context_telemetry.record_agent_self_report("25", "nova", {"tool_calls": "eighteen"})

    def test_rejects_float_tool_calls(self):
        with self.assertRaises(ValueError):
            context_telemetry.record_agent_self_report("25", "nova", {"tool_calls": 18.5})

    def test_rejects_bool_tool_calls(self):
        with self.assertRaises(ValueError):
            context_telemetry.record_agent_self_report("25", "nova", {"tool_calls": True})

    def test_rejects_string_read_paths(self):
        with self.assertRaises(ValueError) as ctx:
            context_telemetry.record_agent_self_report("25", "nova", {
                "tool_calls": 5,
                "read_paths": "backend/app/services/llm.py",
            })
        self.assertIn("read_paths", str(ctx.exception))

    def test_rejects_integer_item_in_write_paths(self):
        with self.assertRaises(ValueError) as ctx:
            context_telemetry.record_agent_self_report("25", "nova", {
                "tool_calls": 5,
                "write_paths": [123, "valid.py"],
            })
        self.assertIn("write_paths", str(ctx.exception))

    def test_rejects_non_list_searches(self):
        with self.assertRaises(ValueError) as ctx:
            context_telemetry.record_agent_self_report("25", "nova", {
                "tool_calls": 5,
                "searches": {"tool": "Grep", "path": ".", "query": "x"},
            })
        self.assertIn("searches", str(ctx.exception))

    def test_rejects_non_dict_search_entry(self):
        with self.assertRaises(ValueError) as ctx:
            context_telemetry.record_agent_self_report("25", "nova", {
                "tool_calls": 5,
                "searches": ["should be a dict"],
            })
        self.assertIn("searches", str(ctx.exception))

    def test_rejects_search_entry_missing_field(self):
        with self.assertRaises(ValueError) as ctx:
            context_telemetry.record_agent_self_report("25", "nova", {
                "tool_calls": 5,
                "searches": [{"tool": "Grep", "missing_path": ".", "query": "x"}],
            })
        self.assertIn("path", str(ctx.exception))

    def test_rejects_non_string_search_field(self):
        with self.assertRaises(ValueError):
            context_telemetry.record_agent_self_report("25", "nova", {
                "tool_calls": 5,
                "searches": [{"tool": "Grep", "path": 42, "query": "x"}],
            })

    def test_accepts_valid_complete_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scope = context_telemetry.record_agent_self_report("25", "nova", {
                "tool_calls": 18,
                "read_paths": ["backend/app/services/llm.py"],
                "write_paths": ["backend/app/services/llm.py"],
                "searches": [{"tool": "Grep", "path": ".", "query": "LLMService"}],
                "commands": ["pytest backend/tests/test_llm.py"],
                "expansions": [],
            }, root)
        self.assertEqual(scope["tool_calls"], 18)
        self.assertEqual(scope["status"], "available")

    def test_accepts_null_optional_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scope = context_telemetry.record_agent_self_report("25", "nova", {
                "tool_calls": 10,
                "read_paths": None,
                "write_paths": None,
                "searches": None,
                "commands": None,
                "expansions": None,
            }, root)
        self.assertEqual(scope["tool_calls"], 10)
        self.assertEqual(scope["status"], "partial")

    def test_accepts_zero_tool_calls(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scope = context_telemetry.record_agent_self_report("25", "nova", {
                "tool_calls": 0,
                "read_paths": [],
                "write_paths": [],
                "searches": [],
                "commands": [],
                "expansions": [],
            }, root)
        self.assertEqual(scope["tool_calls"], 0)


if __name__ == "__main__":
    unittest.main()
