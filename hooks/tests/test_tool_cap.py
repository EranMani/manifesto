#!/usr/bin/env python3

from __future__ import annotations

import sys
import unittest
from pathlib import Path


HOOKS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HOOKS_DIR))

from tool_cap_end import close_invocation, extract_tokens  # noqa: E402
from tool_cap_enforce import enforce_tool_event  # noqa: E402
from tool_cap_start import (  # noqa: E402
    authorize_repair,
    initialize_commit_state,
    start_invocation,
)


class ToolCapTests(unittest.TestCase):
    def state(self) -> dict:
        return initialize_commit_state(
            "C30",
            "rex",
            ["backend/app/service.py", "backend/tests/test_service.py"],
        )

    def greenfield_state(self) -> dict:
        return initialize_commit_state(
            "C29A",
            "adam",
            ["hooks/preflight_commit.py", "hooks/tests/test_preflight_commit.py"],
            {
                "max_agent_invocations": 1,
                "max_tool_calls": 28,
                "max_expansions": 2,
                "max_implementor_tokens": 55000,
                "max_total_tokens": 70000,
            },
        )

    def test_second_normal_invocation_is_blocked(self) -> None:
        state = self.state()
        start_invocation(state, "rex", "normal")
        close_invocation(state, 10000)
        with self.assertRaisesRegex(ValueError, "already consumed"):
            start_invocation(state, "rex", "normal")

    def test_call_19_is_blocked(self) -> None:
        state = self.state()
        start_invocation(state, "rex", "normal")
        for _ in range(18):
            allowed, _warning = enforce_tool_event(state, "Read", {
                "file_path": "backend/app/service.py",
            })
            self.assertTrue(allowed)
        allowed, message = enforce_tool_event(state, "Read", {
            "file_path": "backend/app/service.py",
        })
        self.assertFalse(allowed)
        self.assertIn("19", message)

    def test_call_12_and_16_warn(self) -> None:
        state = self.state()
        start_invocation(state, "rex", "normal")
        warnings = {}
        for call in range(1, 17):
            allowed, warning = enforce_tool_event(state, "Read", {
                "file_path": "backend/app/service.py",
            })
            self.assertTrue(allowed)
            if warning:
                warnings[call] = warning
        self.assertIn("budget status", warnings[12])
        self.assertIn("SPLIT_REQUIRED", warnings[16])

    def test_greenfield_call_6_blocks_without_write(self) -> None:
        state = self.greenfield_state()
        start_invocation(state, "adam", "normal")
        for _ in range(5):
            allowed, _warning = enforce_tool_event(state, "Read", {
                "file_path": "hooks/preflight_commit.py",
            })
            self.assertTrue(allowed)
        allowed, message = enforce_tool_event(state, "Read", {
            "file_path": "hooks/preflight_commit.py",
        })
        self.assertFalse(allowed)
        self.assertIn("6", message)
        self.assertIn("implementation must have started", message)

    def test_greenfield_call_6_allowed_after_write(self) -> None:
        state = self.greenfield_state()
        start_invocation(state, "adam", "normal")
        for _ in range(4):
            allowed, _warning = enforce_tool_event(state, "Read", {
                "file_path": "hooks/preflight_commit.py",
            })
            self.assertTrue(allowed)
        allowed, _warning = enforce_tool_event(state, "Write", {
            "file_path": "hooks/preflight_commit.py",
        })
        self.assertTrue(allowed)
        allowed, _warning = enforce_tool_event(state, "Read", {
            "file_path": "hooks/preflight_commit.py",
        })
        self.assertTrue(allowed)

    def test_greenfield_call_22_and_26_warn(self) -> None:
        state = self.greenfield_state()
        start_invocation(state, "adam", "normal")
        warnings = {}
        allowed, _warning = enforce_tool_event(state, "Write", {
            "file_path": "hooks/preflight_commit.py",
        })
        self.assertTrue(allowed)
        for call in range(2, 27):
            allowed, warning = enforce_tool_event(state, "Read", {
                "file_path": "hooks/preflight_commit.py",
            })
            self.assertTrue(allowed)
            if warning:
                warnings[call] = warning
        self.assertIn("budget status", warnings[22])
        self.assertIn("SPLIT_REQUIRED", warnings[26])

    def test_greenfield_call_29_is_blocked(self) -> None:
        state = self.greenfield_state()
        start_invocation(state, "adam", "normal")
        allowed, _warning = enforce_tool_event(state, "Write", {
            "file_path": "hooks/preflight_commit.py",
        })
        self.assertTrue(allowed)
        for _ in range(27):
            allowed, _warning = enforce_tool_event(state, "Read", {
                "file_path": "hooks/preflight_commit.py",
            })
            self.assertTrue(allowed)
        allowed, message = enforce_tool_event(state, "Read", {
            "file_path": "hooks/preflight_commit.py",
        })
        self.assertFalse(allowed)
        self.assertIn("29", message)

    def test_third_expansion_is_blocked(self) -> None:
        state = self.state()
        start_invocation(state, "rex", "normal")
        for path in ("one.py", "two.py"):
            allowed, _ = enforce_tool_event(state, "Read", {"file_path": path})
            self.assertTrue(allowed)
        allowed, message = enforce_tool_event(state, "Read", {"file_path": "three.py"})
        self.assertFalse(allowed)
        self.assertIn("expansion 3", message)

    def test_absolute_selected_path_is_not_an_expansion(self) -> None:
        root = Path("D:/repo")
        state = self.state()
        start_invocation(state, "rex", "normal")
        allowed, _ = enforce_tool_event(
            state,
            "Read",
            {"file_path": "D:/repo/backend/app/service.py"},
            root,
        )
        self.assertTrue(allowed)
        self.assertEqual(state["expansions"], 0)
        self.assertEqual(state["expanded_paths"], [])

    def test_absolute_unselected_path_is_recorded_repo_relative(self) -> None:
        root = Path("D:/repo")
        state = self.state()
        start_invocation(state, "rex", "normal")
        allowed, _ = enforce_tool_event(
            state,
            "Read",
            {"file_path": "D:/repo/backend/app/other.py"},
            root,
        )
        self.assertTrue(allowed)
        self.assertEqual(state["expanded_paths"], ["backend/app/other.py"])

    def test_one_narrow_repair_is_allowed(self) -> None:
        state = self.state()
        start_invocation(state, "rex", "normal")
        enforce_tool_event(state, "Edit", {"file_path": "backend/app/service.py"})
        close_invocation(state, 20000)
        authorize_repair(
            state,
            "pytest backend/tests/test_service.py -q",
            "one assertion failed",
            ["backend/app/service.py"],
            1000,
        )
        start_invocation(state, "rex", "repair")
        allowed, _ = enforce_tool_event(
            state,
            "Edit",
            {"file_path": "backend/app/service.py"},
        )
        self.assertTrue(allowed)
        close_invocation(state, 5000)
        with self.assertRaisesRegex(ValueError, "consumed"):
            start_invocation(state, "rex", "repair")

    def test_repair_cannot_write_outside_delta_files(self) -> None:
        state = self.state()
        start_invocation(state, "rex", "normal")
        enforce_tool_event(state, "Edit", {"file_path": "backend/app/service.py"})
        close_invocation(state, 10000)
        authorize_repair(
            state,
            "pytest backend/tests/test_service.py -q",
            "failure",
            ["backend/app/service.py"],
            500,
        )
        start_invocation(state, "rex", "repair")
        allowed, message = enforce_tool_event(
            state,
            "Edit",
            {"file_path": "backend/app/other.py"},
        )
        self.assertFalse(allowed)
        self.assertIn("outside authorized", message)

    def test_token_hard_stop_blocks_repair(self) -> None:
        state = self.state()
        state["write_started"] = True
        state["known_implementor_tokens"] = 45000
        with self.assertRaisesRegex(ValueError, "hard stop"):
            authorize_repair(state, "pytest x", "failure", ["x.py"], 100)

    def test_extract_tokens_includes_cache_tokens(self) -> None:
        # C29B repair invocation: harness reported subagent_tokens: 49837, but the
        # prior input_tokens + output_tokens formula recorded only 791 (OI-12).
        usage = {
            "input_tokens": 2,
            "cache_creation_input_tokens": 1038,
            "cache_read_input_tokens": 48008,
            "output_tokens": 789,
        }
        payload = {"message": {"usage": usage}}
        self.assertEqual(extract_tokens(payload), 49837)

    def test_close_invocation_records_full_usage_total(self) -> None:
        state = self.state()
        start_invocation(state, "rex", "normal")
        usage = {
            "input_tokens": 2,
            "cache_creation_input_tokens": 1038,
            "cache_read_input_tokens": 48008,
            "output_tokens": 789,
        }
        close_invocation(state, extract_tokens({"message": {"usage": usage}}))
        self.assertEqual(state["known_implementor_tokens"], 49837)
        self.assertEqual(state["known_total_tokens"], 49837)


if __name__ == "__main__":
    unittest.main()
