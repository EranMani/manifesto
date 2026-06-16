from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


HOOKS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HOOKS_DIR))

import claude_budget  # noqa: E402


class ClaudeBudgetTests(unittest.TestCase):
    def scope(self, actions: int = 0, mode: str = "claude-direct") -> dict:
        return {
            "status": "running",
            "execution_mode": mode,
            "tool_calls": actions,
            "token_usage": {"status": "running"},
        }

    def test_cache_reads_do_not_count_as_active_tokens(self) -> None:
        usage = {
            "status": "complete",
            "assistant_turns": 3,
            "components": {
                "input_tokens": 10,
                "output_tokens": 20,
                "cache_creation_input_tokens": 30,
                "cache_read_input_tokens": 9000,
            },
        }
        with patch.object(claude_budget, "_finalize_token_snapshot", return_value=usage):
            metrics = claude_budget.measure(self.scope())
        self.assertEqual(metrics["active_tokens"], 60)
        self.assertEqual(metrics["cache_read_tokens"], 9000)

    def test_direct_scope_warns_on_twenty_fifth_action(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "active.json"
            path.write_text(json.dumps(self.scope(actions=24)), encoding="utf-8")
            allowed, message = claude_budget.evaluate(
                {"tool_name": "Read", "tool_input": {}}, path
            )
        self.assertTrue(allowed)
        self.assertIn("budget warn", message)

    def test_review_scope_blocks_twentieth_action(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "active.json"
            path.write_text(
                json.dumps(self.scope(actions=19, mode="delegated")),
                encoding="utf-8",
            )
            allowed, message = claude_budget.evaluate(
                {"tool_name": "Edit", "tool_input": {}}, path
            )
        self.assertFalse(allowed)
        self.assertIn("budget stop", message)

    def test_closeout_command_remains_available_after_stop(self) -> None:
        event = {
            "tool_name": "Bash",
            "tool_input": {"command": "python hooks/finalize_commit.py --commit 52A"},
        }
        self.assertTrue(claude_budget.allowed_after_stop(event))

    def test_override_is_consumed_for_closeout_action(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "active.json"
            scope = self.scope(actions=40)
            scope["budget_override"] = {"uses_remaining": 5, "reason": "approved"}
            path.write_text(json.dumps(scope), encoding="utf-8")
            allowed, _ = claude_budget.evaluate(
                {
                    "tool_name": "Edit",
                    "tool_input": {"file_path": ".context/telemetry/scope.json"},
                },
                path,
            )
            saved = json.loads(path.read_text(encoding="utf-8"))
        self.assertTrue(allowed)
        self.assertEqual(saved["budget_override"]["uses_remaining"], 4)
        self.assertEqual(saved["budget_override"].get("mode", "closeout"), "closeout")

    def test_override_does_not_cover_non_closeout_action(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "active.json"
            scope = self.scope(actions=40)
            scope["budget_override"] = {"uses_remaining": 5, "reason": "approved"}
            path.write_text(json.dumps(scope), encoding="utf-8")
            allowed, message = claude_budget.evaluate(
                {
                    "tool_name": "Edit",
                    "tool_input": {"file_path": "backend/app/main.py"},
                },
                path,
            )
            saved = json.loads(path.read_text(encoding="utf-8"))
        self.assertFalse(allowed)
        self.assertIn("closeout", message)
        self.assertEqual(saved["budget_override"]["uses_remaining"], 5)

    def test_authorize_override_grants_five_closeout_uses(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "active.json"
            path.write_text(json.dumps(self.scope(actions=40)), encoding="utf-8")
            claude_budget.authorize_override("Eran approved: closeout", path)
            saved = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(saved["budget_override"]["uses_remaining"], 5)
        self.assertEqual(saved["budget_override"]["mode"], "closeout")

    def test_authorize_recovery_override_grants_ten_uses(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "active.json"
            path.write_text(json.dumps(self.scope(actions=40)), encoding="utf-8")
            claude_budget.authorize_override(
                "Eran approved: recovery", path, mode="recovery"
            )
            saved = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(saved["budget_override"]["uses_remaining"], 10)
        self.assertEqual(saved["budget_override"]["mode"], "recovery")

    def test_recovery_override_allows_agent_invocation_after_stop(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "active.json"
            scope = self.scope(actions=40, mode="delegated")
            scope["budget_override"] = {
                "uses_remaining": 10,
                "reason": "approved",
                "mode": "recovery",
            }
            path.write_text(json.dumps(scope), encoding="utf-8")
            allowed, message = claude_budget.evaluate(
                {"tool_name": "Agent", "tool_input": {"subagent_type": "rex"}},
                path,
            )
            saved = json.loads(path.read_text(encoding="utf-8"))
        self.assertTrue(allowed)
        self.assertIn("recovery action", message)
        self.assertEqual(saved["budget_override"]["uses_remaining"], 9)

    def test_closeout_override_does_not_allow_agent_invocation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "active.json"
            scope = self.scope(actions=40, mode="delegated")
            scope["budget_override"] = {
                "uses_remaining": 5,
                "reason": "approved",
                "mode": "closeout",
            }
            path.write_text(json.dumps(scope), encoding="utf-8")
            allowed, message = claude_budget.evaluate(
                {"tool_name": "Agent", "tool_input": {"subagent_type": "rex"}},
                path,
            )
            saved = json.loads(path.read_text(encoding="utf-8"))
        self.assertFalse(allowed)
        self.assertIn("request an override", message)
        self.assertEqual(saved["budget_override"]["uses_remaining"], 5)

    def test_authorize_override_command_allowed_after_stop(self) -> None:
        event = {
            "tool_name": "Bash",
            "tool_input": {
                "command": 'python hooks/claude_budget.py --authorize-override "reason"'
            },
        }
        self.assertTrue(claude_budget.allowed_after_stop(event))

    def test_tool_cap_reset_command_allowed_after_stop(self) -> None:
        event = {
            "tool_name": "PowerShell",
            "tool_input": {
                "command": "python hooks/tool_cap_reset.py --commit C55 --agent rex --kind normal"
            },
        }
        self.assertTrue(claude_budget.allowed_after_stop(event))

    def test_powershell_closeout_command_allowed_after_stop(self) -> None:
        event = {
            "tool_name": "PowerShell",
            "tool_input": {
                "command": "python hooks/finalize_commit.py --commit 54A"
            },
        }
        self.assertTrue(claude_budget.allowed_after_stop(event))

    def test_powershell_authorize_override_allowed_after_stop(self) -> None:
        event = {
            "tool_name": "PowerShell",
            "tool_input": {
                "command": 'python hooks/claude_budget.py --authorize-override "Eran approved: closeout"'
            },
        }
        self.assertTrue(claude_budget.allowed_after_stop(event))

    def test_read_only_tools_are_closeout_actions(self) -> None:
        self.assertTrue(
            claude_budget.is_closeout_action({"tool_name": "Read", "tool_input": {}})
        )

    def test_unrelated_edit_is_not_closeout_action(self) -> None:
        self.assertFalse(
            claude_budget.is_closeout_action(
                {"tool_name": "Edit", "tool_input": {"file_path": "backend/app/main.py"}}
            )
        )


if __name__ == "__main__":
    unittest.main()
