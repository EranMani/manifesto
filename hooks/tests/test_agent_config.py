#!/usr/bin/env python3

from __future__ import annotations

import json
import unittest
from pathlib import Path


HOOKS_DIR = Path(__file__).resolve().parents[1]


class AgentConfigTests(unittest.TestCase):
    def test_hooks_are_owned_by_adam_not_universal(self) -> None:
        config = json.loads(
            (HOOKS_DIR / "agent-config.json").read_text(encoding="utf-8")
        )
        self.assertNotIn("hooks/", config["universal_allowed"])
        self.assertIn(
            "hooks/",
            config["agents"]["adam.stockagent@gmail.com"]["domains"],
        )


if __name__ == "__main__":
    unittest.main()
