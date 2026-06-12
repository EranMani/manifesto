#!/usr/bin/env python3

from __future__ import annotations

import sys
from pathlib import Path


HOOKS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HOOKS_DIR))

from generate_domain_map import write_domain_map  # noqa: E402


def test_date_only_change_does_not_rewrite_domain_map(tmp_path: Path) -> None:
    output = tmp_path / "backend" / "DOMAIN_MAP.md"
    output.parent.mkdir()
    graph = {"app/main.py": ["app/service.py"], "app/service.py": []}

    assert write_domain_map(output, "Rex - backend/app/", graph) is True
    original = output.read_text(encoding="utf-8")
    output.write_text(
        original.replace("> Last updated:", "> Last updated: 2000-01-01 #"),
        encoding="utf-8",
    )
    dated_content = output.read_text(encoding="utf-8")

    assert write_domain_map(output, "Rex - backend/app/", graph) is False
    assert output.read_text(encoding="utf-8") == dated_content
