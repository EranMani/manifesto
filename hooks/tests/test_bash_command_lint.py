#!/usr/bin/env python3

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


HOOKS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HOOKS_DIR))

from bash_command_lint import (  # noqa: E402
    contains_cd_command,
    contains_exit_code_propagating_chain,
    main,
)


class CdDetectionTests(unittest.TestCase):
    def test_plain_cd_chain_is_blocked(self) -> None:
        self.assertTrue(contains_cd_command("cd hooks && pytest tests/ -q"))

    def test_subshell_cd_is_blocked(self) -> None:
        self.assertTrue(contains_cd_command("(cd hooks && pytest tests/ -q)"))

    def test_cd_after_semicolon_is_blocked(self) -> None:
        self.assertTrue(contains_cd_command("pwd; cd hooks; pytest tests/ -q"))

    def test_repo_relative_command_is_allowed(self) -> None:
        self.assertFalse(contains_cd_command("python -m pytest hooks/tests/ -q"))

    def test_cd_substring_in_path_is_allowed(self) -> None:
        self.assertFalse(contains_cd_command("cat src/cdn/file.txt"))

    def test_cd_substring_in_word_is_allowed(self) -> None:
        self.assertFalse(contains_cd_command("echo abcd"))


class ExitCodeChainDetectionTests(unittest.TestCase):
    def test_dev_null_and_chain_is_blocked(self) -> None:
        self.assertTrue(
            contains_exit_code_propagating_chain(
                "ls .context 2>/dev/null && ls .context/finalize 2>/dev/null"
            )
        )

    def test_dev_null_semicolon_non_true_chain_is_blocked(self) -> None:
        self.assertTrue(
            contains_exit_code_propagating_chain(
                "ls .context 2>/dev/null; ls .context/finalize 2>/dev/null"
            )
        )

    def test_dev_null_semicolon_true_is_allowed(self) -> None:
        self.assertFalse(
            contains_exit_code_propagating_chain("ls .context/finalize 2>/dev/null; true")
        )

    def test_dev_null_with_or_true_is_allowed(self) -> None:
        self.assertFalse(
            contains_exit_code_propagating_chain("ls .context/finalize 2>/dev/null || true")
        )

    def test_plain_command_is_allowed(self) -> None:
        self.assertFalse(contains_exit_code_propagating_chain("git status --short"))


class HookMainTests(unittest.TestCase):
    def run_hook(self, command: str) -> subprocess.CompletedProcess:
        payload = json.dumps({"tool_input": {"command": command}})
        return subprocess.run(
            [sys.executable, str(HOOKS_DIR / "bash_command_lint.py")],
            input=payload,
            capture_output=True,
            text=True,
        )

    def test_cd_command_exits_2(self) -> None:
        result = self.run_hook("cd hooks && python -m pytest tests/ -q")
        self.assertEqual(result.returncode, 2)
        self.assertIn("cd", result.stderr)

    def test_exit_code_chain_exits_2(self) -> None:
        result = self.run_hook("ls .context 2>/dev/null && ls .context/finalize 2>/dev/null")
        self.assertEqual(result.returncode, 2)
        self.assertIn("Exit code", result.stderr)

    def test_normal_command_exits_0(self) -> None:
        result = self.run_hook("python -m pytest hooks/tests/ -q")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, "")

    def test_malformed_input_fails_open(self) -> None:
        result = subprocess.run(
            [sys.executable, str(HOOKS_DIR / "bash_command_lint.py")],
            input="not json",
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)

    def test_empty_input_fails_open(self) -> None:
        result = subprocess.run(
            [sys.executable, str(HOOKS_DIR / "bash_command_lint.py")],
            input="",
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)

    def test_main_returns_0_for_empty_command(self) -> None:
        import io
        import unittest.mock

        with unittest.mock.patch.object(sys, "stdin", io.StringIO(json.dumps({"tool_input": {}}))):
            self.assertEqual(main(), 0)


if __name__ == "__main__":
    unittest.main()
