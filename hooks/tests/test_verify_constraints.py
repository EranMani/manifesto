#!/usr/bin/env python3
"""Tests for verify_constraints.py: command resolution, --no-persist, malformed telemetry."""

from __future__ import annotations

import json
import subprocess
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

    def test_persist_calls_log_and_metric_but_not_dashboard_by_default(self):
        """Dashboard rendering is opt-in (--render-dashboard); default off."""
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
            mock_dash.assert_not_called()

    def test_render_dashboard_flag_triggers_render(self):
        with (
            patch("verify_constraints.load_spec", return_value=MINIMAL_SPEC),
            patch("verify_constraints.load_worklog", return_value=""),
            patch("verify_constraints.git_files_changed", return_value=[]),
            patch("verify_constraints.get_tokens_from_records", return_value=None),
            patch("verify_constraints.build_metric_record",
                  return_value={"commit": "C25", "agent": "nova"}),
            patch("verify_constraints.append_to_log"),
            patch("verify_constraints.upsert_metric"),
            patch("verify_constraints.render_dashboard") as mock_dash,
        ):
            self._run(["--worktree", "--render-dashboard"])
            mock_dash.assert_called_once()

    def test_claude_direct_execution_uses_captured_scope_tokens(self):
        """Claude-direct tokens come only from the completed transcript scope."""
        with (
            patch("verify_constraints.load_spec", return_value=MINIMAL_SPEC),
            patch("verify_constraints.load_worklog", return_value=""),
            patch("verify_constraints.git_files_changed", return_value=[]),
            patch("verify_constraints.get_tokens_from_records", return_value=12345),
            patch("verify_constraints.load_orchestrator_telemetry", return_value={
                "token_usage": {"status": "complete", "total_tokens": 54321}
            }),
            patch("verify_constraints.build_metric_record",
                  return_value={"commit": "C25", "agent": "nova"}) as mock_build,
            patch("verify_constraints.append_to_log") as mock_log,
            patch("verify_constraints.upsert_metric"),
            patch("verify_constraints.render_dashboard"),
        ):
            self._run(["--worktree", "--execution", "claude-direct"])

            _, _, tokens_arg, *_ = mock_build.call_args[0]
            self.assertEqual(tokens_arg, 54321)
            self.assertEqual(mock_build.call_args.kwargs.get("execution"), "claude-direct")

            log_args = mock_log.call_args[0]
            self.assertEqual(log_args[-1], 54321)

    def test_delegated_execution_uses_tokens_from_records(self):
        with (
            patch("verify_constraints.load_spec", return_value=MINIMAL_SPEC),
            patch("verify_constraints.load_worklog", return_value=""),
            patch("verify_constraints.git_files_changed", return_value=[]),
            patch("verify_constraints.get_tokens_from_records", return_value=12345),
            patch("verify_constraints.build_metric_record",
                  return_value={"commit": "C25", "agent": "nova"}) as mock_build,
            patch("verify_constraints.append_to_log"),
            patch("verify_constraints.upsert_metric"),
            patch("verify_constraints.render_dashboard"),
        ):
            self._run(["--worktree", "--execution", "delegated"])

            _, _, tokens_arg, *_ = mock_build.call_args[0]
            self.assertEqual(tokens_arg, 12345)
            self.assertEqual(mock_build.call_args.kwargs.get("execution"), "delegated")

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

    @staticmethod
    def _write_matching_tool_cap(root: Path, commit: str, agent: str) -> None:
        cap = root / "hooks" / "tool_cap.json"
        cap.parent.mkdir(parents=True, exist_ok=True)
        cap.write_text(json.dumps({"commit": f"C{commit}", "agent": agent.lower()}), encoding="utf-8")

    def test_accepts_valid_complete_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_matching_tool_cap(root, "25", "nova")
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
            self._write_matching_tool_cap(root, "25", "nova")
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
            self._write_matching_tool_cap(root, "25", "nova")
            scope = context_telemetry.record_agent_self_report("25", "nova", {
                "tool_calls": 0,
                "read_paths": [],
                "write_paths": [],
                "searches": [],
                "commands": [],
                "expansions": [],
            }, root)
        self.assertEqual(scope["tool_calls"], 0)


SPEC_NO_FORBIDDEN = """\
# Commit 25 — llm-service-impl

## context
```yaml
tier0:
  - backend/app/services/llm.py
estimated_reads: 5
```

## What

Implement the LLMService class.
"""


# ---------------------------------------------------------------------------
# Task 5 — Worktree mode must include untracked files
# ---------------------------------------------------------------------------

class TestWorktreeUntrackedFiles(unittest.TestCase):
    """git_files_changed(worktree=True) must include untracked files alongside modified ones."""

    @staticmethod
    def _init_repo(root: Path) -> bool:
        for cmd in (
            ["git", "init"],
            ["git", "config", "user.email", "test@manifesto.test"],
            ["git", "config", "user.name", "Test"],
        ):
            if subprocess.run(cmd, capture_output=True, cwd=root).returncode != 0:
                return False
        (root / "README.md").write_text("init", encoding="utf-8")
        for cmd in (
            ["git", "add", "README.md"],
            ["git", "commit", "-m", "init"],
        ):
            if subprocess.run(cmd, capture_output=True, cwd=root).returncode != 0:
                return False
        return True

    def test_untracked_file_appears_in_changed_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            if not self._init_repo(root):
                self.skipTest("git init/commit failed")
            (root / "frontend").mkdir()
            (root / "frontend" / "NewComponent.tsx").write_text("export {}", encoding="utf-8")

            changed = verify_constraints.git_files_changed(worktree=True, root=root)
            self.assertIn("frontend/NewComponent.tsx", changed,
                          "Untracked file must appear in worktree changed-file list")

    def test_untracked_forbidden_file_fails_check(self):
        """Regression: an untracked file under a forbidden path must cause FAIL, not slip through."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            if not self._init_repo(root):
                self.skipTest("git init/commit failed")
            (root / "frontend").mkdir()
            (root / "frontend" / "NewComponent.tsx").write_text("export {}", encoding="utf-8")

            changed = verify_constraints.git_files_changed(worktree=True, root=root)
            ok, msg = verify_constraints.check_forbidden_paths(MINIMAL_SPEC, changed)
            self.assertFalse(ok,
                "Untracked file under forbidden path must cause check_forbidden_paths to FAIL")
            self.assertIn("frontend", msg)

    def test_modified_tracked_file_still_detected(self):
        """Existing tracked-file detection must not be broken by the untracked addition."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            if not self._init_repo(root):
                self.skipTest("git init/commit failed")
            (root / "README.md").write_text("changed", encoding="utf-8")

            changed = verify_constraints.git_files_changed(worktree=True, root=root)
            self.assertIn("README.md", changed,
                          "Modified tracked file must still appear in changed list")


# ---------------------------------------------------------------------------
# Task 6 — WARN checks render as [WARN] not [PASS] in text output
# ---------------------------------------------------------------------------

class TestWarningsRenderAsWarn(unittest.TestCase):
    """Checks that return ok=True with a 'WARN:' message must display [WARN], not [PASS]."""

    def _capture_output(self, spec: str) -> str:
        output_lines: list[str] = []
        def capture(*a, **kw):
            output_lines.append(" ".join(str(x) for x in a))
        old_argv = sys.argv[:]
        try:
            sys.argv = ["vc", "--commit", "25", "--agent", "nova", "--worktree", "--no-persist"]
            with (
                patch("verify_constraints.load_spec", return_value=spec),
                patch("verify_constraints.load_worklog", return_value=""),
                patch("verify_constraints.git_files_changed", return_value=[]),
                patch("builtins.print", side_effect=capture),
            ):
                try:
                    verify_constraints.main()
                except SystemExit:
                    pass
        finally:
            sys.argv = old_argv
        return "\n".join(output_lines)

    def test_missing_forbidden_section_shows_warn(self):
        """Spec with no forbidden block → forbidden-paths check must print [WARN]."""
        output = self._capture_output(SPEC_NO_FORBIDDEN)
        self.assertIn("[WARN]", output,
                      "Spec without forbidden block must render forbidden check as [WARN]")
        self.assertNotIn("[PASS] WARN", output,
                         "A WARN message must not be labelled [PASS]")

    def test_missing_worklog_budget_shows_warn(self):
        """Empty worklog → phase-budget check must print [WARN], not [PASS]."""
        output = self._capture_output(MINIMAL_SPEC)
        self.assertIn("[WARN]", output,
                      "Missing worklog must render budget check as [WARN]")

    def test_warn_icon_written_to_log(self):
        """append_to_log must write WARN (not PASS) for a warning result."""
        results = {
            "context_block":   {"pass": True,  "message": "context block present"},
            "forbidden_paths": {"pass": True,  "message": "WARN: no forbidden paths defined"},
            "phase_budget":    {"pass": True,  "message": "WARN: no worklog found", "counts": None},
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            log_path = root / "CONSTRAINT_LOG.md"
            with patch.object(verify_constraints, "REPO_ROOT", root):
                verify_constraints.append_to_log("25", "nova", results, True, None)
            row = log_path.read_text(encoding="utf-8").splitlines()[-1]
        cells = [c.strip() for c in row.split("|") if c.strip()]
        # cells: date, C25, nova, -, context, forbidden, budget, result
        forbidden_cell = cells[5]
        budget_cell    = cells[6]
        self.assertEqual(forbidden_cell, "WARN",
                         f"forbidden column must be WARN, got {forbidden_cell!r}")
        self.assertEqual(budget_cell, "WARN",
                         f"budget column must be WARN, got {budget_cell!r}")
        self.assertEqual(cells[7], "PASS",
                         "Overall RESULT must still be PASS when all ok=True")


# ---------------------------------------------------------------------------
# Task 7 — Effective greenfield budget usage (C29A follow-up)
# ---------------------------------------------------------------------------

class TestEffectiveGreenfieldBudgets(unittest.TestCase):
    """check_phase_budget and check_actual_scope must read the effective budget
    (bootstrap_exception overrides merged by validate_commit_spec) instead of
    the hardcoded normal-commit caps, and hooks/tool_cap.json (runtime
    telemetry) must never count toward unplanned files or diff lines."""

    @staticmethod
    def _init_repo(root: Path) -> bool:
        for cmd in (
            ["git", "init"],
            ["git", "config", "user.email", "test@manifesto.test"],
            ["git", "config", "user.name", "Test"],
        ):
            if subprocess.run(cmd, capture_output=True, cwd=root).returncode != 0:
                return False
        (root / "README.md").write_text("init", encoding="utf-8")
        for cmd in (
            ["git", "add", "README.md"],
            ["git", "commit", "-m", "init"],
        ):
            if subprocess.run(cmd, capture_output=True, cwd=root).returncode != 0:
                return False
        return True

    def test_effective_phase_budgets_scales_with_max_tool_calls(self):
        budgets = verify_constraints._effective_phase_budgets({"budget": {"max_tool_calls": 28}})
        self.assertEqual(budgets["total"], 28)
        self.assertEqual(budgets["reads"], 16)
        self.assertEqual(budgets["writes"], 19)

    def test_effective_phase_budgets_default_unchanged(self):
        budgets = verify_constraints._effective_phase_budgets({"budget": {"max_tool_calls": 18}})
        self.assertEqual(budgets, verify_constraints.PHASE_BUDGETS)

    def test_check_phase_budget_passes_within_greenfield_total(self):
        spec_result = {"budget": {"max_tool_calls": 28}}
        worklog = "## Session 01 — Commit 29A\n\nTool usage: reads=7, writes=2, total=25\n"
        ok, counts, msg = verify_constraints.check_phase_budget(worklog, "29A", "adam", spec_result)
        self.assertTrue(ok, msg)
        self.assertEqual(counts["total"], 25)

    def test_check_phase_budget_fails_normal_total_cap(self):
        spec_result = {"budget": {"max_tool_calls": 18}}
        worklog = "## Session 01 — Commit 30\n\nTool usage: reads=7, writes=2, total=25\n"
        ok, counts, msg = verify_constraints.check_phase_budget(worklog, "30", "adam", spec_result)
        self.assertFalse(ok)
        self.assertIn("total=25 exceeds cap of 18", msg)

    def test_check_phase_budget_claude_direct_skips_owner_worklog(self):
        """Claude-direct execution: owner agent (adam) has no C30 session in their
        worklog at all - an unrelated C29A session with total=25 must not cause a
        failure, and the worklog must not be inspected against the 18-call cap."""
        spec_result = {"budget": {"max_tool_calls": 18}}
        worklog = "## Session 29A — Commit 29A\n\nTool usage: reads=7, writes=2, total=25\n"
        ok, counts, msg = verify_constraints.check_phase_budget(
            worklog, "30", "adam", spec_result, execution="claude-direct"
        )
        self.assertTrue(ok, msg)
        self.assertIn("Claude-direct", msg)

    def test_check_phase_budget_delegated_with_correct_session_passes(self):
        spec_result = {"budget": {"max_tool_calls": 18}}
        worklog = (
            "## Session 29A — Commit 29A\n\nTool usage: reads=7, writes=2, total=25\n\n"
            "## Session 30 — Commit 30\n\nTool usage: reads=8, writes=4, total=12\n"
        )
        ok, counts, msg = verify_constraints.check_phase_budget(
            worklog, "30", "adam", spec_result, execution="delegated"
        )
        self.assertTrue(ok, msg)
        self.assertEqual(counts["total"], 12)

    def test_check_phase_budget_delegated_missing_session_fails_without_fallback(self):
        """If --agent's worklog has no C30 session, delegated execution must fail
        clearly rather than matching an unrelated commit's "Tool usage" line."""
        spec_result = {"budget": {"max_tool_calls": 18}}
        worklog = "## Session 29A — Commit 29A\n\nTool usage: reads=7, writes=2, total=25\n"
        ok, counts, msg = verify_constraints.check_phase_budget(
            worklog, "30", "adam", spec_result, execution="delegated"
        )
        self.assertFalse(ok)
        self.assertIsNone(counts)
        self.assertIn("30", msg)
        self.assertNotIn("25", msg)

    def test_check_phase_budget_letter_suffix_skips_session_index_row(self):
        spec_result = {"budget": {"max_tool_calls": 28}}
        worklog = (
            "## Current State\n\n"
            "**Currently active:** Commit 29A `preflight-score-engine` — pending approval\n\n"
            "## Session Index\n\n"
            "| # | Commit | Status |\n"
            "|---|---|---|\n"
            "| 29A | C29A: preflight-score-engine | pending |\n\n"
            "## Session 29A — Commit 29A: `preflight-score-engine`\n\n"
            "Tool usage: reads=7, writes=2, total=25\n"
        )
        ok, counts, msg = verify_constraints.check_phase_budget(worklog, "29A", "adam", spec_result)
        self.assertTrue(ok, msg)
        self.assertEqual(counts["total"], 25)

    def test_check_actual_scope_excludes_tool_cap_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            if not self._init_repo(root):
                self.skipTest("git init/commit failed")
            (root / "hooks").mkdir()
            (root / "hooks" / "tool_cap.json").write_text("{}", encoding="utf-8")
            for cmd in (["git", "add", "."], ["git", "commit", "-m", "add tool_cap"]):
                subprocess.run(cmd, capture_output=True, cwd=root)
            (root / "hooks" / "tool_cap.json").write_text(
                json.dumps({"tool_calls": list(range(50))}), encoding="utf-8"
            )

            spec_result = {
                "commit": "C29A",
                "planned_changed_files": ["hooks/new_module.py"],
                "budget": {"max_changed_files": 4, "max_estimated_diff_lines": 1200},
            }
            with patch.object(verify_constraints, "REPO_ROOT", root):
                changed = verify_constraints.git_files_changed(worktree=True, root=root)
                ok, counts, msg = verify_constraints.check_actual_scope(spec_result, changed, True, "HEAD")

            self.assertIn("hooks/tool_cap.json", changed)
            self.assertTrue(ok, msg)
            self.assertEqual(counts["unplanned_files"], [])
            self.assertEqual(counts["diff_lines"], 0)

    def test_check_actual_scope_uses_effective_diff_line_cap(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            if not self._init_repo(root):
                self.skipTest("git init/commit failed")
            (root / "hooks").mkdir()
            (root / "hooks" / "new_module.py").write_text(
                "\n".join(f"# line {i}" for i in range(500)), encoding="utf-8"
            )

            spec_result = {
                "commit": "C29A",
                "planned_changed_files": ["hooks/new_module.py"],
                "budget": {"max_changed_files": 4, "max_estimated_diff_lines": 1200},
            }
            with patch.object(verify_constraints, "REPO_ROOT", root):
                changed = verify_constraints.git_files_changed(worktree=True, root=root)
                ok, counts, msg = verify_constraints.check_actual_scope(spec_result, changed, True, "HEAD")

            self.assertTrue(ok, msg)
            self.assertEqual(counts["diff_lines"], 500)
            self.assertEqual(counts["max_diff_lines"], 1200)

            # The same diff against the locked default (350) must fail.
            spec_result_default = dict(spec_result, budget={"max_changed_files": 4})
            with patch.object(verify_constraints, "REPO_ROOT", root):
                ok2, counts2, msg2 = verify_constraints.check_actual_scope(
                    spec_result_default, changed, True, "HEAD"
                )
            self.assertFalse(ok2, msg2)
            self.assertEqual(counts2["max_diff_lines"], 350)

    def test_check_actual_scope_treats_agent_worklog_as_planned(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            if not self._init_repo(root):
                self.skipTest("git init/commit failed")
            (root / "hooks").mkdir()
            (root / "hooks" / "new_module.py").write_text("# new module\n", encoding="utf-8")
            (root / ".claude" / "agents" / "logs").mkdir(parents=True)
            (root / ".claude" / "agents" / "logs" / "adam-worklog.md").write_text(
                "# Adam worklog\n", encoding="utf-8"
            )

            spec_result = {
                "commit": "C29A",
                "planned_changed_files": ["hooks/new_module.py"],
                "budget": {"max_changed_files": 4, "max_estimated_diff_lines": 1200},
            }
            with patch.object(verify_constraints, "REPO_ROOT", root):
                changed = verify_constraints.git_files_changed(worktree=True, root=root)
                ok, counts, msg = verify_constraints.check_actual_scope(
                    spec_result, changed, True, "HEAD", "adam"
                )

            self.assertTrue(ok, msg)
            self.assertEqual(counts["unplanned_files"], [])


# ---------------------------------------------------------------------------
# Task 8 — resolve_primary_commit_ref (C33A ref-resolution fix)
# ---------------------------------------------------------------------------

class TestResolvePrimaryCommitRef(unittest.TestCase):
    """verify_constraints resolves the correct primary-commit ref instead of
    silently defaulting to HEAD when --ref is omitted and --worktree is not set."""

    @staticmethod
    def _init_repo(root: Path) -> bool:
        for cmd in (
            ["git", "init"],
            ["git", "config", "user.email", "test@manifesto.test"],
            ["git", "config", "user.name", "Test"],
        ):
            if subprocess.run(cmd, capture_output=True, cwd=root).returncode != 0:
                return False
        (root / "README.md").write_text("init", encoding="utf-8")
        for cmd in (
            ["git", "add", "README.md"],
            ["git", "commit", "-m", "init"],
        ):
            if subprocess.run(cmd, capture_output=True, cwd=root).returncode != 0:
                return False
        return True

    @staticmethod
    def _commit(root: Path, files: dict[str, str], message: str) -> str:
        for relpath, content in files.items():
            path = root / relpath
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        subprocess.run(["git", "add", "."], capture_output=True, cwd=root)
        subprocess.run(["git", "commit", "-m", message], capture_output=True, cwd=root)
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=root
        ).stdout.strip()

    def test_finds_primary_commit_sha_when_chore_commit_is_head(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            if not self._init_repo(root):
                self.skipTest("git init/commit failed")
            primary_sha = self._commit(
                root, {"hooks/new_module.py": "# new\n"},
                "feat(hooks): add new module\n\nCommit #33\n\n"
                "Execution: Claude-direct\n\nWhat: x\nWhy: y\n",
            )
            head_sha = self._commit(
                root, {"project-state.json": "{}"},
                "chore(state): advance state after C-33",
            )
            self.assertNotEqual(primary_sha, head_sha)

            ref, warning = verify_constraints.resolve_primary_commit_ref("33", "rex", root)
            self.assertEqual(ref, primary_sha)
            self.assertIsNone(warning)

    def test_no_match_falls_back_to_head_with_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            if not self._init_repo(root):
                self.skipTest("git init/commit failed")
            self._commit(
                root, {"hooks/new_module.py": "# new\n"},
                "feat(hooks): unrelated change\n\nNo commit reference here\n",
            )
            ref, warning = verify_constraints.resolve_primary_commit_ref("99", "rex", root)
            self.assertEqual(ref, "HEAD")
            self.assertIn("Commit #99", warning)
            self.assertIn("fallback to HEAD", warning)

    def test_explicit_ref_overrides_auto_resolution(self):
        with (
            patch("verify_constraints.resolve_primary_commit_ref") as mock_resolve,
            patch("verify_constraints.load_spec", return_value=MINIMAL_SPEC),
            patch("verify_constraints.load_worklog", return_value=""),
            patch("verify_constraints.git_files_changed", return_value=[]) as mock_changed,
        ):
            old_argv = sys.argv[:]
            sys.argv = ["vc", "--commit", "25", "--agent", "nova", "--ref", "deadbeef", "--no-persist"]
            try:
                verify_constraints.main()
            except SystemExit:
                pass
            finally:
                sys.argv = old_argv

            mock_resolve.assert_not_called()
            mock_changed.assert_called_once_with("deadbeef", worktree=False)

    def test_no_ref_passed_auto_resolves_and_reports_fallback(self):
        with (
            patch(
                "verify_constraints.resolve_primary_commit_ref",
                return_value=("HEAD", "fallback to HEAD - no commit matching 'Commit #25' found"),
            ) as mock_resolve,
            patch("verify_constraints.load_spec", return_value=MINIMAL_SPEC),
            patch("verify_constraints.load_worklog", return_value=""),
            patch("verify_constraints.git_files_changed", return_value=[]) as mock_changed,
        ):
            output_lines: list[str] = []

            def capture_print(*args, **kwargs):
                output_lines.append(" ".join(str(a) for a in args))

            old_argv = sys.argv[:]
            sys.argv = ["vc", "--commit", "25", "--agent", "nova", "--no-persist", "--json"]
            try:
                with patch("builtins.print", side_effect=capture_print):
                    verify_constraints.main()
            except SystemExit:
                pass
            finally:
                sys.argv = old_argv

            mock_resolve.assert_called_once_with("25", "nova")
            mock_changed.assert_called_once_with("HEAD", worktree=False)
            parsed = json.loads("\n".join(output_lines))
            self.assertEqual(
                parsed.get("ref_resolution"),
                "fallback to HEAD - no commit matching 'Commit #25' found",
            )

    def test_actual_scope_ok_when_resolved_ref_used_after_chore_commit(self):
        """Regression: re-running against a commit after a later chore commit
        landed must diff the primary commit, not the chore commit (C33's bug)."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            if not self._init_repo(root):
                self.skipTest("git init/commit failed")
            primary_sha = self._commit(
                root, {"hooks/new_module.py": "# new\n"},
                "feat(hooks): add new module\n\nCommit #33\n\n"
                "Execution: Claude-direct\n\nWhat: x\nWhy: y\n",
            )
            self._commit(
                root, {"project-state.json": "{}"},
                "chore(state): advance state after C-33",
            )

            spec_result = {
                "commit": "C33",
                "planned_changed_files": ["hooks/new_module.py"],
                "budget": {"max_changed_files": 4, "max_estimated_diff_lines": 1200},
            }

            ref, warning = verify_constraints.resolve_primary_commit_ref("33", "rex", root)
            self.assertEqual(ref, primary_sha)
            self.assertIsNone(warning)

            with patch.object(verify_constraints, "REPO_ROOT", root):
                resolved_changed = verify_constraints.git_files_changed(ref, worktree=False, root=root)
                ok, counts, msg = verify_constraints.check_actual_scope(
                    spec_result, resolved_changed, False, ref, "rex"
                )
                self.assertTrue(ok, msg)
                self.assertEqual(counts["unplanned_files"], [])

                # Diffing HEAD (the chore commit) directly reproduces C33's bug.
                head_changed = verify_constraints.git_files_changed("HEAD", worktree=False, root=root)
                ok_head, counts_head, _ = verify_constraints.check_actual_scope(
                    spec_result, head_changed, False, "HEAD", "rex"
                )
                self.assertFalse(ok_head)
                self.assertIn("project-state.json", counts_head["unplanned_files"])


if __name__ == "__main__":
    unittest.main()
