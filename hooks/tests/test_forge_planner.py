#!/usr/bin/env python3
"""Tests for hooks/forge_planner.py — the /forge commit planner."""

from __future__ import annotations

import json
import sys
from pathlib import Path

HOOKS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HOOKS_DIR))

import forge_planner as fp  # noqa: E402


# ---------------------------------------------------------------------------
# Commit number resolution
# ---------------------------------------------------------------------------

def test_find_next_commit_number_from_protocol(tmp_path: Path) -> None:
    protocol = tmp_path / "commit-protocol.md"
    protocol.write_text(
        "| # | Name | Assignee | Status |\n"
        "|---|---|---|---|\n"
        "| 70 | something | rex | done |\n"
        "| 71 | another | aria | done |\n",
        encoding="utf-8",
    )
    assert fp.find_next_commit_number(tmp_path) == 72


def test_find_next_commit_number_no_protocol(tmp_path: Path) -> None:
    assert fp.find_next_commit_number(tmp_path) == 1


def test_find_next_commit_handles_letter_suffixes(tmp_path: Path) -> None:
    protocol = tmp_path / "commit-protocol.md"
    protocol.write_text(
        "| # | Name | Assignee | Status |\n"
        "|---|---|---|---|\n"
        "| 42 | base | rex | done |\n"
        "| 42A | fix | rex | done |\n"
        "| 43 | next | nova | pending |\n",
        encoding="utf-8",
    )
    assert fp.find_next_commit_number(tmp_path) == 44


def test_find_last_completed_commit(tmp_path: Path) -> None:
    state = tmp_path / "project-state.json"
    state.write_text(json.dumps({"last_completed_commit": "71"}), encoding="utf-8")
    assert fp.find_last_completed_commit(tmp_path) == 71


def test_find_last_completed_commit_missing(tmp_path: Path) -> None:
    assert fp.find_last_completed_commit(tmp_path) is None


# ---------------------------------------------------------------------------
# File grouping
# ---------------------------------------------------------------------------

def test_group_files_by_owner() -> None:
    ownership = {
        "backend/app/main.py": "rex",
        "backend/app/services/llm.py": "nova",
        "frontend/src/App.tsx": "aria",
    }
    groups = fp.group_files_by_owner(
        ["backend/app/main.py", "backend/app/services/llm.py", "frontend/src/App.tsx"],
        ownership,
    )
    assert groups == {
        "rex": ["backend/app/main.py"],
        "nova": ["backend/app/services/llm.py"],
        "aria": ["frontend/src/App.tsx"],
    }


def test_group_files_unknown_owner_defaults_to_claude() -> None:
    groups = fp.group_files_by_owner(["unknown/file.py"], {})
    assert "claude" in groups


def test_split_by_budget_under_limit() -> None:
    files = ["a.py", "b.py", "c.py"]
    chunks = fp.split_by_budget(files, max_files=4)
    assert chunks == [files]


def test_split_by_budget_over_limit() -> None:
    files = ["a.py", "b.py", "c.py", "d.py", "e.py", "f.py"]
    chunks = fp.split_by_budget(files, max_files=4)
    assert len(chunks) == 2
    assert len(chunks[0]) == 4
    assert len(chunks[1]) == 2


# ---------------------------------------------------------------------------
# Scope estimation
# ---------------------------------------------------------------------------

def test_scope_xs_single_non_hub() -> None:
    assert fp.estimate_scope(["leaf.py"], []) == "XS"


def test_scope_s_two_non_hub() -> None:
    assert fp.estimate_scope(["a.py", "b.py"], []) == "S"


def test_scope_m_three_files() -> None:
    assert fp.estimate_scope(["a.py", "b.py", "c.py"], []) == "M"


def test_scope_l_many_files() -> None:
    assert fp.estimate_scope(["a.py", "b.py", "c.py", "d.py"], []) == "L"


def test_scope_m_hub_involved() -> None:
    hubs = [{"path": "hub.py", "in_degree": 10, "out_degree": 2}]
    assert fp.estimate_scope(["hub.py", "other.py"], hubs) == "M"


# ---------------------------------------------------------------------------
# Execution routing
# ---------------------------------------------------------------------------

def test_claude_domain_always_direct() -> None:
    mode, _ = fp.decide_execution("claude", ["hooks/x.py"], [], "feature")
    assert mode == "claude-direct"


def test_small_fix_is_direct() -> None:
    mode, _ = fp.decide_execution("rex", ["backend/app/main.py"], [], "fix")
    assert mode == "claude-direct"


def test_hub_touching_feature_is_delegated() -> None:
    hubs = [{"path": "backend/app/core/database.py", "in_degree": 20, "out_degree": 1}]
    files = [
        "backend/app/core/database.py",
        "backend/app/models/user.py",
        "backend/app/api/v1/auth.py",
    ]
    mode, _ = fp.decide_execution("rex", files, hubs, "feature")
    assert mode == "delegated"


def test_large_feature_is_delegated() -> None:
    files = ["a.py", "b.py", "c.py"]
    mode, _ = fp.decide_execution("aria", files, [], "feature")
    assert mode == "delegated"


# ---------------------------------------------------------------------------
# Layer inference and ordering
# ---------------------------------------------------------------------------

def test_infer_layer_backend() -> None:
    categories = {"backend": ["backend/app/main.py"], "frontend": ["frontend/src/App.tsx"]}
    assert fp.infer_layer(["backend/app/main.py"], categories) == "backend"


def test_order_commits_backend_before_frontend() -> None:
    categories = {
        "backend": ["backend/app/main.py"],
        "frontend": ["frontend/src/App.tsx"],
    }
    commits = [
        {"number": 1, "files": ["frontend/src/App.tsx"], "owner": "aria"},
        {"number": 2, "files": ["backend/app/main.py"], "owner": "rex"},
    ]
    ordered = fp.order_commits(commits, categories)
    assert ordered[0]["owner"] == "rex"
    assert ordered[1]["owner"] == "aria"
    assert ordered[1]["depends_on"] == ordered[0]["number"]


def test_order_commits_same_layer_no_dependency() -> None:
    categories = {"backend": ["a.py", "b.py"]}
    commits = [
        {"number": 1, "files": ["a.py"], "owner": "rex"},
        {"number": 2, "files": ["b.py"], "owner": "rex"},
    ]
    ordered = fp.order_commits(commits, categories)
    assert ordered[1]["depends_on"] is None


# ---------------------------------------------------------------------------
# Agent routing
# ---------------------------------------------------------------------------

def test_determine_agents_basic() -> None:
    groups = {"rex": ["a.py"], "aria": ["b.tsx"]}
    agents = fp.determine_agents_needed(groups)
    names = [a["agent"] for a in agents]
    assert "rex" in names
    assert "aria" in names
    assert "mira" in names  # auto-added for user-facing


def test_determine_agents_no_mira_for_devops_only() -> None:
    groups = {"adam": ["docker-compose.yml"]}
    agents = fp.determine_agents_needed(groups)
    names = [a["agent"] for a in agents]
    assert "adam" in names
    assert "mira" not in names


# ---------------------------------------------------------------------------
# Full plan generation
# ---------------------------------------------------------------------------

def test_generate_plan_single_owner(tmp_path: Path) -> None:
    (tmp_path / "commit-protocol.md").write_text(
        "| # | Name | Assignee | Status |\n"
        "| 71 | last | rex | done |\n",
        encoding="utf-8",
    )
    report = {
        "repo_root": str(tmp_path),
        "categories": {"backend": ["backend/app/main.py", "backend/app/auth.py"]},
        "hubs": [],
        "domain_ownership": {
            "backend/app/main.py": "rex",
            "backend/app/auth.py": "rex",
        },
    }
    plan = fp.generate_plan(
        task="Add rate limiting",
        task_type="feature",
        target_files=["backend/app/main.py", "backend/app/auth.py"],
        report=report,
        repo_root=tmp_path,
    )

    assert len(plan["commits"]) == 1
    assert plan["commits"][0]["number"] == 72
    assert plan["commits"][0]["owner"] == "rex"
    assert plan["total_estimated_tokens"] > 0


def test_generate_plan_cross_domain(tmp_path: Path) -> None:
    (tmp_path / "commit-protocol.md").write_text(
        "| # | Name | Assignee | Status |\n"
        "| 71 | last | rex | done |\n",
        encoding="utf-8",
    )
    report = {
        "repo_root": str(tmp_path),
        "categories": {
            "backend": ["backend/app/main.py"],
            "frontend": ["frontend/src/App.tsx"],
        },
        "hubs": [],
        "domain_ownership": {
            "backend/app/main.py": "rex",
            "frontend/src/App.tsx": "aria",
        },
    }
    plan = fp.generate_plan(
        task="Add user profile page",
        task_type="feature",
        target_files=["backend/app/main.py", "frontend/src/App.tsx"],
        report=report,
        repo_root=tmp_path,
    )

    assert len(plan["commits"]) == 2
    owners = [c["owner"] for c in plan["commits"]]
    assert "rex" in owners
    assert "aria" in owners
    assert plan["commits"][0]["owner"] != plan["commits"][1]["owner"]


def test_generate_plan_budget_split(tmp_path: Path) -> None:
    (tmp_path / "commit-protocol.md").write_text(
        "| # | Name | Assignee | Status |\n"
        "| 10 | x | rex | done |\n",
        encoding="utf-8",
    )
    files = [f"backend/app/f{i}.py" for i in range(6)]
    report = {
        "repo_root": str(tmp_path),
        "categories": {"backend": files},
        "hubs": [],
        "domain_ownership": {f: "rex" for f in files},
    }
    plan = fp.generate_plan(
        task="Large refactor",
        task_type="refactor",
        target_files=files,
        report=report,
        repo_root=tmp_path,
    )

    assert len(plan["commits"]) == 2
    total_files = sum(len(c["files"]) for c in plan["commits"])
    assert total_files == 6
    assert all(len(c["files"]) <= 4 for c in plan["commits"])
