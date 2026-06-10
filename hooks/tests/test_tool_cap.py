#!/usr/bin/env python3

from __future__ import annotations

import sys
import unittest
from pathlib import Path


HOOKS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HOOKS_DIR))

from tool_cap_end import close_invocation  # noqa: E402
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

    def test_third_expansion_is_blocked(self) -> None:
        state = self.state()
        start_invocation(state, "rex", "normal")
        for path in ("one.py", "two.py"):
            allowed, _ = enforce_tool_event(state, "Read", {"file_path": path})
            self.assertTrue(allowed)
        allowed, message = enforce_tool_event(state, "Read", {"file_path": "three.py"})
        self.assertFalse(allowed)
        self.assertIn("expansion 3", message)

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


if __name__ == "__main__":
    unittest.main()
