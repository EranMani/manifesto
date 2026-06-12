#!/usr/bin/env python3

from __future__ import annotations

import sys
from pathlib import Path


HOOKS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HOOKS_DIR))

import generate_domain_map as gdm  # noqa: E402
from generate_domain_map import write_domain_map  # noqa: E402


def test_main_skips_scan_when_flag_absent(monkeypatch, tmp_path: Path) -> None:
    backend = tmp_path / "backend" / "app"
    backend.mkdir(parents=True)
    (backend / "main.py").write_text("import app.service\n", encoding="utf-8")

    monkeypatch.setattr(gdm, "git_root", lambda: tmp_path)

    assert gdm.main() == 0
    assert not (tmp_path / "backend" / "DOMAIN_MAP.md").exists()


def test_main_runs_and_consumes_flag_when_present(monkeypatch, tmp_path: Path) -> None:
    backend = tmp_path / "backend" / "app"
    backend.mkdir(parents=True)
    (backend / "main.py").write_text("import app.service\n", encoding="utf-8")

    flag_path = tmp_path / ".context" / "runtime" / "last_protocol_commit.flag"
    flag_path.parent.mkdir(parents=True)
    flag_path.write_text("30", encoding="utf-8")

    monkeypatch.setattr(gdm, "git_root", lambda: tmp_path)

    assert gdm.main() == 0
    assert (tmp_path / "backend" / "DOMAIN_MAP.md").exists()
    assert not flag_path.exists()


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
