#!/usr/bin/env python3

from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path


HOOKS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HOOKS_DIR))

from tool_cap_end import close_invocation, extract_tokens  # noqa: E402
from tool_cap_enforce import enforce_tool_event  # noqa: E402
from tool_cap_start import (  # noqa: E402
    authorize_repair,
    initialize_commit_state,
    main as tool_cap_start_main,
    reset_invocation_state,
    resolve_invocation,
    start_invocation,
    write_state,
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

    def test_reviewer_expansions_do_not_consume_implementor_expansions(self) -> None:
        state = self.state()
        start_invocation(state, "viktor", "review")
        for path in ("backend/app/other.py", "backend/app/policy.py"):
            allowed, _ = enforce_tool_event(state, "Read", {"file_path": path})
            self.assertTrue(allowed)
        self.assertEqual(state["active_invocation"]["expansions"], 2)
        self.assertEqual(state["expansions"], 0)
        self.assertEqual(state["expanded_paths"], [])
        close_invocation(state, 1000)

        start_invocation(state, "rex", "normal")
        allowed, _ = enforce_tool_event(
            state, "Read", {"file_path": "backend/app/first_rex_expansion.py"}
        )
        self.assertTrue(allowed)
        self.assertEqual(state["active_invocation"]["expansions"], 1)
        self.assertEqual(state["expansions"], 1)
        self.assertEqual(state["expanded_paths"], ["backend/app/first_rex_expansion.py"])

    def test_reset_invocation_state_clears_failed_implementor_retry(self) -> None:
        state = self.state()
        start_invocation(state, "rex", "normal")
        enforce_tool_event(state, "Read", {"file_path": "backend/app/other.py"})
        state["stop_reason"] = "expansion_limit:2"
        state["stop_scope"] = {"commit": "C30", "agent": "rex", "kind": "normal"}

        reset_invocation_state(state, agent="rex", kind="normal")

        self.assertFalse(state["active"])
        self.assertEqual(state["invocation_count"], 0)
        self.assertIsNone(state["stop_reason"])
        self.assertEqual(state["expanded_paths"], [])
        start_invocation(state, "rex", "normal")
        self.assertTrue(state["active"])

    def test_reset_can_discard_failed_closed_implementor_invocation(self) -> None:
        state = self.state()
        start_invocation(state, "viktor", "review")
        close_invocation(state, 1000)
        start_invocation(state, "rex", "normal")
        close_invocation(state, 24000)
        self.assertEqual(state["known_total_tokens"], 25000)
        self.assertEqual(state["known_implementor_tokens"], 24000)

        reset_invocation_state(
            state,
            agent="rex",
            kind="normal",
            discard_closed=True,
        )

        self.assertEqual(state["known_total_tokens"], 1000)
        self.assertEqual(state["known_implementor_tokens"], 0)
        self.assertEqual(len(state["invocations"]), 1)
        self.assertEqual(state["invocations"][0]["agent"], "viktor")

    def test_reset_refuses_to_clear_different_active_invocation(self) -> None:
        state = self.state()
        start_invocation(state, "viktor", "review")

        with self.assertRaisesRegex(ValueError, "active invocation is viktor/review"):
            reset_invocation_state(state, agent="rex", kind="normal")

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


class ResolveInvocationTests(unittest.TestCase):
    def test_general_purpose_with_adam_identity_resolves_to_adam(self) -> None:
        agent, kind = resolve_invocation({
            "subagent_type": "general-purpose",
            "description": "Adam - repair invocation for the tool cap state",
            "prompt": "Adam, this is a repair invocation to fix the corrupted hooks state.",
        })
        self.assertEqual(agent, "adam")
        self.assertEqual(kind, "repair")

    def test_general_purpose_with_implementor_identity_is_tool_cap_managed(self) -> None:
        state = initialize_commit_state(
            "C29B", "adam",
            ["hooks/tool_cap_start.py", "hooks/tests/test_tool_cap.py"],
        )
        agent, kind = resolve_invocation({
            "subagent_type": "general-purpose",
            "description": "Adam - implement the emergency repair",
            "prompt": "Adam, implement the fix.",
        })
        start_invocation(state, agent, kind)
        self.assertEqual(state["agent"], "adam")
        self.assertEqual(state["invocation_count"], 1)
        self.assertTrue(state["active"])

    def test_explore_subagent_resolves_to_explore_kind(self) -> None:
        agent, kind = resolve_invocation({
            "subagent_type": "Explore",
            "description": "Find where tool_cap state is written",
            "prompt": "Search the hooks/ directory for tool_cap.json writers.",
        })
        self.assertEqual(agent, "explore")
        self.assertEqual(kind, "explore")

    def test_explore_subagent_ignores_mentioned_agent_names(self) -> None:
        # Even if the prompt happens to mention an implementor by name,
        # subagent_type "Explore" must never be classified as that agent.
        agent, kind = resolve_invocation({
            "subagent_type": "Explore",
            "description": "Find Adam's changes to the hooks",
            "prompt": "Locate where Adam's tool_cap_start.py is referenced.",
        })
        self.assertEqual(agent, "explore")
        self.assertEqual(kind, "explore")

    def test_unrecognized_identity_resolves_to_unknown(self) -> None:
        agent, kind = resolve_invocation({
            "subagent_type": "general-purpose",
            "description": "Investigate the failing build",
            "prompt": "Look into why CI is failing.",
        })
        self.assertEqual(agent, "unknown")
        self.assertEqual(kind, "normal")

    def test_multiple_agent_mentions_resolve_to_unknown(self) -> None:
        # Do not pick the first name found in arbitrary prompt text -- two
        # distinct candidate identities is ambiguous, not a selection.
        agent, kind = resolve_invocation({
            "subagent_type": "general-purpose",
            "description": "Coordinate Rex and Adam on the backend fix",
            "prompt": "Rex and Adam should both look at this.",
        })
        self.assertEqual(agent, "unknown")
        self.assertEqual(kind, "normal")

    def test_unknown_identity_fails_safely_not_unbounded(self) -> None:
        state = initialize_commit_state(
            "C30", "rex", ["backend/app/service.py"],
        )
        agent, kind = resolve_invocation({
            "subagent_type": "general-purpose",
            "description": "Investigate the failing build",
            "prompt": "Look into why CI is failing.",
        })
        with self.assertRaisesRegex(ValueError, "not an implementor"):
            start_invocation(state, agent, kind)


class StopScopeTests(unittest.TestCase):
    def state(self) -> dict:
        return initialize_commit_state(
            "C30", "rex",
            ["backend/app/service.py", "backend/tests/test_service.py"],
        )

    def test_enforce_sets_stop_scope_with_stop_reason(self) -> None:
        state = self.state()
        start_invocation(state, "rex", "normal")
        for _ in range(18):
            enforce_tool_event(state, "Read", {"file_path": "backend/app/service.py"})
        allowed, _ = enforce_tool_event(state, "Read", {"file_path": "backend/app/service.py"})
        self.assertFalse(allowed)
        self.assertEqual(state["stop_reason"], "tool_call_limit:18")
        self.assertEqual(state["stop_scope"], {"commit": "C30", "agent": "rex", "kind": "normal"})

    def test_close_invocation_token_hard_stop_sets_stop_scope(self) -> None:
        state = self.state()
        start_invocation(state, "rex", "normal")
        close_invocation(state, 45000)
        self.assertEqual(state["stop_reason"], "implementor_token_hard_stop")
        self.assertEqual(state["stop_scope"], {"commit": "C30", "agent": "rex", "kind": "normal"})

    def test_scoped_stop_blocks_only_matching_agent_and_kind(self) -> None:
        state = self.state()
        start_invocation(state, "rex", "normal")
        for _ in range(18):
            enforce_tool_event(state, "Read", {"file_path": "backend/app/service.py"})
        enforce_tool_event(state, "Read", {"file_path": "backend/app/service.py"})
        close_invocation(state, 1000)

        # A different agent/kind (e.g. a reviewer) is not blocked by rex's
        # normal-invocation stop.
        start_invocation(state, "viktor", "review")
        self.assertTrue(state["active"])

    def test_scoped_stop_blocks_matching_retry(self) -> None:
        state = self.state()
        start_invocation(state, "rex", "normal")
        for _ in range(18):
            enforce_tool_event(state, "Read", {"file_path": "backend/app/service.py"})
        enforce_tool_event(state, "Read", {"file_path": "backend/app/service.py"})
        close_invocation(state, 1000)

        with self.assertRaisesRegex(ValueError, "commit is stopped"):
            start_invocation(state, "rex", "normal")

    def test_legacy_stop_reason_without_scope_does_not_block_review_or_explore(self) -> None:
        state = self.state()
        state["stop_reason"] = "tool_call_limit:18"
        state["stop_scope"] = None  # legacy state predates stop_scope

        start_invocation(state, "viktor", "review")
        self.assertTrue(state["active"])
        close_invocation(state, 100)

        start_invocation(state, "explore", "explore")
        self.assertTrue(state["active"])

    def test_legacy_stop_reason_without_scope_blocks_matching_implementor_retry(self) -> None:
        state = self.state()
        state["stop_reason"] = "tool_call_limit:18"
        state["stop_scope"] = None  # legacy state predates stop_scope

        with self.assertRaisesRegex(ValueError, "commit is stopped"):
            start_invocation(state, "rex", "normal")


class MainEndToEndTests(unittest.TestCase):
    def write_initial_state(self, tmp_path: Path, **overrides) -> Path:
        hooks_dir = tmp_path / "hooks"
        state = initialize_commit_state(
            "C30", "rex",
            ["backend/app/service.py", "backend/tests/test_service.py"],
        )
        state.update(overrides)
        state_path = hooks_dir / "tool_cap.json"
        write_state(state_path, state)
        return state_path

    def run_main(self, tmp_path: Path, payload: dict) -> tuple[int, str]:
        stdin = io.StringIO(json.dumps(payload))
        with unittest.mock.patch("tool_cap_start.git_root", return_value=tmp_path), \
                unittest.mock.patch("sys.stdin", stdin), \
                unittest.mock.patch("sys.stderr", new_callable=io.StringIO) as stderr:
            code = tool_cap_start_main()
        return code, stderr.getvalue()

    def test_rejected_invocation_does_not_modify_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            state_path = self.write_initial_state(tmp_path)
            before = state_path.read_text(encoding="utf-8")

            code, _ = self.run_main(tmp_path, {
                "tool_input": {
                    "subagent_type": "general-purpose",
                    "description": "Investigate the failing build",
                    "prompt": "Look into why CI is failing.",
                },
            })
            after = state_path.read_text(encoding="utf-8")

            self.assertEqual(code, 2)
            self.assertEqual(before, after)

    def test_rejected_invocation_does_not_compound_stop_reason(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            state_path = self.write_initial_state(
                tmp_path,
                stop_reason="commit is stopped: tool_call_limit:18",
                stop_scope={"commit": "C30", "agent": "rex", "kind": "normal"},
            )

            payload = {
                "tool_input": {
                    "subagent_type": "general-purpose",
                    "description": "Investigate the failing build",
                    "prompt": "Look into why CI is failing.",
                },
            }
            code1, _ = self.run_main(tmp_path, payload)
            code2, _ = self.run_main(tmp_path, payload)

            state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(code1, 2)
            self.assertEqual(code2, 2)
            self.assertEqual(state["stop_reason"], "commit is stopped: tool_call_limit:18")

    def test_accepted_invocation_writes_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            state_path = self.write_initial_state(tmp_path)

            code, _ = self.run_main(tmp_path, {
                "tool_input": {
                    "subagent_type": "rex",
                    "description": "Rex - implement the service change",
                    "prompt": "Rex, implement the change.",
                },
            })

            state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(code, 0)
            self.assertTrue(state["active"])
            self.assertEqual(state["invocation_count"], 1)


if __name__ == "__main__":
    unittest.main()
