#!/usr/bin/env python3
"""Tests for hooks/forge_scan.py — the /forge codebase scanner."""

from __future__ import annotations

import json
import sys
from pathlib import Path

HOOKS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HOOKS_DIR))

import forge_scan as fs  # noqa: E402


# ---------------------------------------------------------------------------
# File categorization
# ---------------------------------------------------------------------------

def test_categorize_backend_app_file(tmp_path: Path) -> None:
    repo = tmp_path
    (repo / "backend" / "app").mkdir(parents=True)
    f = repo / "backend" / "app" / "main.py"
    f.write_text("from fastapi import FastAPI\n", encoding="utf-8")
    assert fs.categorize_file(f, repo) == "backend"


def test_categorize_ai_service_file(tmp_path: Path) -> None:
    repo = tmp_path
    (repo / "backend" / "app" / "services").mkdir(parents=True)
    f = repo / "backend" / "app" / "services" / "llm.py"
    f.write_text("class LLMService: pass\n", encoding="utf-8")
    assert fs.categorize_file(f, repo) == "ai"


def test_categorize_frontend_tsx(tmp_path: Path) -> None:
    repo = tmp_path
    (repo / "frontend" / "src").mkdir(parents=True)
    f = repo / "frontend" / "src" / "App.tsx"
    f.write_text("import React from 'react';\n", encoding="utf-8")
    assert fs.categorize_file(f, repo) == "frontend"


def test_categorize_devops_hooks(tmp_path: Path) -> None:
    repo = tmp_path
    (repo / "hooks").mkdir()
    f = repo / "hooks" / "preflight.py"
    f.write_text("import sys\n", encoding="utf-8")
    assert fs.categorize_file(f, repo) == "devops"


def test_categorize_dockerfile(tmp_path: Path) -> None:
    repo = tmp_path
    f = repo / "Dockerfile"
    f.write_text("FROM python:3.11\n", encoding="utf-8")
    assert fs.categorize_file(f, repo) == "devops"


def test_categorize_docs_md(tmp_path: Path) -> None:
    repo = tmp_path
    f = repo / "DECISIONS.md"
    f.write_text("# Decisions\n", encoding="utf-8")
    assert fs.categorize_file(f, repo) == "docs"


def test_categorize_by_content_fallback(tmp_path: Path) -> None:
    repo = tmp_path
    (repo / "lib").mkdir()
    f = repo / "lib" / "helper.py"
    f.write_text("from fastapi import APIRouter\n", encoding="utf-8")
    assert fs.categorize_file(f, repo) == "backend"


def test_categorize_unknown_returns_other(tmp_path: Path) -> None:
    repo = tmp_path
    f = repo / "mystery.xyz"
    f.write_text("something\n", encoding="utf-8")
    assert fs.categorize_file(f, repo) == "other"


# ---------------------------------------------------------------------------
# Import graph
# ---------------------------------------------------------------------------

def test_python_imports_extracted(tmp_path: Path) -> None:
    f = tmp_path / "service.py"
    f.write_text(
        "from app.core.database import get_db\n"
        "from app.models.user import User\n"
        "import os\n",
        encoding="utf-8",
    )
    imports = fs.get_python_imports(f)
    assert "app.core.database" in imports
    assert "app.models.user" in imports
    assert "os" in imports


def test_ts_imports_extracted(tmp_path: Path) -> None:
    f = tmp_path / "App.tsx"
    f.write_text(
        "import { useState } from 'react';\n"
        "import Header from './components/Header';\n"
        "import { api } from './api/client';\n",
        encoding="utf-8",
    )
    imports = fs.get_ts_imports(f)
    assert "react" in imports
    assert "./components/Header" in imports
    assert "./api/client" in imports


def test_build_import_graph_bidirectional(tmp_path: Path) -> None:
    repo = tmp_path
    (repo / "backend" / "app" / "core").mkdir(parents=True)
    (repo / "backend" / "app" / "models").mkdir(parents=True)

    db = repo / "backend" / "app" / "core" / "database.py"
    db.write_text("from sqlalchemy import create_engine\n", encoding="utf-8")

    user = repo / "backend" / "app" / "models" / "user.py"
    user.write_text("from app.core.database import get_db\n", encoding="utf-8")

    files = [db, user]
    graph = fs.build_import_graph(files, repo)

    user_rel = "backend/app/models/user.py"
    db_rel = "backend/app/core/database.py"

    assert user_rel in graph
    assert db_rel in graph[user_rel]["imports"]
    assert user_rel in graph[db_rel]["imported_by"]


# ---------------------------------------------------------------------------
# Hub detection
# ---------------------------------------------------------------------------

def test_find_hubs_threshold() -> None:
    graph = {
        "hub.py": {"imports": [], "imported_by": ["a.py", "b.py", "c.py", "d.py", "e.py"]},
        "a.py": {"imports": ["hub.py"], "imported_by": []},
        "b.py": {"imports": ["hub.py"], "imported_by": []},
        "c.py": {"imports": ["hub.py"], "imported_by": []},
        "d.py": {"imports": ["hub.py"], "imported_by": []},
        "e.py": {"imports": ["hub.py"], "imported_by": []},
        "leaf.py": {"imports": [], "imported_by": ["a.py"]},
    }
    hubs = fs.find_hubs(graph, in_degree_threshold=5, out_degree_threshold=10)
    hub_paths = [h["path"] for h in hubs]
    assert "hub.py" in hub_paths
    assert "leaf.py" not in hub_paths


def test_find_hubs_empty_graph() -> None:
    assert fs.find_hubs({}) == []


# ---------------------------------------------------------------------------
# Domain ownership
# ---------------------------------------------------------------------------

def test_map_file_to_owner_rex() -> None:
    config = {
        "agents": {
            "rex@test.com": {
                "name": "Rex",
                "role": "backend",
                "domains": ["backend/app/", "backend/tests/"],
            }
        }
    }
    assert fs.map_file_to_owner("backend/app/main.py", config) == "rex"


def test_map_file_to_owner_longest_match() -> None:
    config = {
        "agents": {
            "rex@test.com": {
                "name": "Rex",
                "role": "backend",
                "domains": ["backend/app/"],
            },
            "nova@test.com": {
                "name": "Nova",
                "role": "ai-engineer",
                "domains": ["backend/app/services/llm.py"],
            },
        }
    }
    assert fs.map_file_to_owner("backend/app/services/llm.py", config) == "nova"
    assert fs.map_file_to_owner("backend/app/main.py", config) == "rex"


def test_map_file_to_owner_no_match() -> None:
    config = {
        "agents": {
            "rex@test.com": {
                "name": "Rex",
                "role": "backend",
                "domains": ["backend/app/"],
            }
        }
    }
    assert fs.map_file_to_owner("random/file.py", config) is None


# ---------------------------------------------------------------------------
# Walk files
# ---------------------------------------------------------------------------

def test_walk_excludes_git_and_pycache(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("x", encoding="utf-8")
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "mod.pyc").write_text("x", encoding="utf-8")
    (tmp_path / "real.py").write_text("x", encoding="utf-8")

    monkeypatch.setattr(fs, "_gitignored_paths", lambda _: set())
    files = fs.walk_files(tmp_path)
    rel_names = [str(f.relative_to(tmp_path)) for f in files]
    assert "real.py" in rel_names
    assert ".git\\config" not in rel_names and ".git/config" not in rel_names


def test_walk_excludes_binary_extensions(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "image.png").write_text("fake", encoding="utf-8")
    (tmp_path / "code.py").write_text("x = 1", encoding="utf-8")

    monkeypatch.setattr(fs, "_gitignored_paths", lambda _: set())
    files = fs.walk_files(tmp_path)
    names = [f.name for f in files]
    assert "code.py" in names
    assert "image.png" not in names


# ---------------------------------------------------------------------------
# Full scan integration
# ---------------------------------------------------------------------------

def test_scan_produces_valid_report(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / ".git").mkdir()
    (tmp_path / "backend" / "app").mkdir(parents=True)
    (tmp_path / "backend" / "app" / "main.py").write_text(
        "from app.core.config import settings\n", encoding="utf-8"
    )
    (tmp_path / "frontend" / "src").mkdir(parents=True)
    (tmp_path / "frontend" / "src" / "App.tsx").write_text(
        "import React from 'react';\n", encoding="utf-8"
    )
    (tmp_path / "hooks").mkdir()
    (tmp_path / "hooks" / "agent-config.json").write_text(
        json.dumps({
            "agents": {
                "rex@test.com": {
                    "name": "Rex",
                    "role": "backend",
                    "domains": ["backend/app/"],
                }
            }
        }),
        encoding="utf-8",
    )

    monkeypatch.setattr(fs, "_gitignored_paths", lambda _: set())
    report = fs.scan(tmp_path)

    assert "scanned_at" in report
    assert report["file_count"] >= 2
    assert "backend" in report["categories"]
    assert "frontend" in report["categories"]
    assert isinstance(report["call_tree"], dict)
    assert isinstance(report["hubs"], list)
    assert isinstance(report["domain_ownership"], dict)


def test_scan_cli_writes_json_file(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / ".git").mkdir()
    (tmp_path / "app.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "hooks").mkdir()
    (tmp_path / "hooks" / "agent-config.json").write_text("{}", encoding="utf-8")

    monkeypatch.setattr(fs, "_gitignored_paths", lambda _: set())
    monkeypatch.setattr(
        "sys.argv",
        ["forge_scan.py", "--path", str(tmp_path), "--out", ".forge"],
    )
    assert fs.main() == 0
    assert (tmp_path / ".forge" / "report.json").exists()

    report = json.loads((tmp_path / ".forge" / "report.json").read_text(encoding="utf-8"))
    assert report["file_count"] >= 1
