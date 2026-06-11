#!/usr/bin/env python3

from __future__ import annotations

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
EXPECTED_AGENTS = {
    "ai-engineer.md": ("nova", "sonnet"),
    "backend.md": ("rex", "sonnet"),
    "devops.md": ("adam", "sonnet"),
    "frontend.md": ("aria", "sonnet"),
    "product.md": ("mira", "haiku"),
    "reviewer.md": ("viktor", "haiku"),
    "security.md": ("sage", "haiku"),
}


def frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        return {}
    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        key, separator, value = line.partition(":")
        if separator:
            fields[key.strip()] = value.strip()
    return fields


class AgentDefinitionTests(unittest.TestCase):
    def test_project_agents_have_unique_required_frontmatter(self) -> None:
        names: set[str] = set()
        for filename, (expected_name, expected_model) in EXPECTED_AGENTS.items():
            with self.subTest(filename=filename):
                fields = frontmatter(REPO_ROOT / ".claude" / "agents" / filename)
                self.assertEqual(fields.get("name"), expected_name)
                self.assertTrue(fields.get("description"))
                self.assertEqual(fields.get("model"), expected_model)
                self.assertRegex(expected_name, r"^[a-z-]+$")
                self.assertNotIn(expected_name, names)
                names.add(expected_name)


if __name__ == "__main__":
    unittest.main()
