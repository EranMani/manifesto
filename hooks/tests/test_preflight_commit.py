"""Tests for hooks/preflight_commit.py.

Uses temporary fixture repositories (minimal commit-protocol.md, project-state.json,
commit-specs/commit-*.md, hooks/agent-config.json) so these tests do not depend on the
live pending-commit range. ContextPackageBuilder.build is monkeypatched to a controlled
result, since it depends on a full codebase graph that doesn't exist in the fixtures.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import preflight_commit as pf  # noqa: E402


GOOD_SPEC = """# Commit 30 - `widget-thing` - Adam

**Phase:** Test Phase
**Owner:** adam
**Depends on:** C29
**Estimated diff lines:** 50
**Primary behavior count:** 1
**Developer test milestone:** no

---

## Primary Behavior

Store separate invocation telemetry records. This is the rest of the paragraph.

---

## Semantic Fit Review

- **Atomic outcome:** does one thing.
- **Failure boundary:** narrow.
- **Budget rationale:** small.

---

## Execution Budget

```yaml
execution_budget:
  max_primary_files: 2
  max_changed_files: 4
  max_context_files: 6
  max_context_chars: 15000
  max_estimated_diff_lines: 350
  max_agent_invocations: 1
  max_tool_calls: 18
  max_expansions: 2
  max_implementor_tokens: 45000
```

---

## Context

```yaml
primary_files:
  - hooks/context_telemetry.py
initial_context:
  - hooks/validate_commit_spec.py
forbidden:
  - backend/
  - frontend/
```

---

## Files To Modify Or Add

| File | Type | Purpose |
|---|---|---|
| `hooks/context_telemetry.py` | edit | Store separate invocation telemetry records |

---

## Contract

Some contract text.

---

## Environment Prerequisites

- Python hook test environment.

---

## Verification Command

```powershell
pytest -p no:cacheprovider hooks/tests/test_widget.py -q
```

---

## Focused Tests

- Does the thing.

---

## Done When

- [ ] The thing is done.

---

## Developer Test Checkpoint

**Next milestone:** C32.

---

## Not In This Commit

- Nothing else.

---

## Return Contract

Report stuff.
"""


C29_SPEC = """# Commit 29 - `prep-commit` - Adam

**Phase:** Test Phase
**Owner:** adam
**Depends on:** None
**Estimated diff lines:** 10
**Primary behavior count:** 1
**Developer test milestone:** no

---

## Primary Behavior

Prep work.

---

## Files To Modify Or Add

| File | Type | Purpose |
|---|---|---|
| `hooks/existing_file.py` | edit | exists already |
"""

C29_SPEC_WITH_MISSING_FILE = C29_SPEC.replace(
    "| `hooks/existing_file.py` | edit | exists already |",
    "| `hooks/existing_file.py` | edit | exists already |\n"
    "| `hooks/missing_file.py` | new | does not exist on disk |",
)


PROTOCOL = """# Commit Protocol

| # | Name | Owner | Status |
|---|---|---|---|
| 29 | prep-commit | Adam | done |
| 30 | widget-thing | Adam | pending |
"""

PROJECT_STATE = {
    "next_commit": "C30",
    "next_commit_assignee": "adam",
}

AGENT_CONFIG = {
    "agents": {
        "adam.devops@example.com": {
            "name": "Adam",
            "role": "devops",
            "domains": ["hooks/", "docker-compose.yml"],
        }
    },
    "universal_allowed": ["commit-specs/", "project-state.json"],
    "initialized": True,
}


def _write(repo: Path, rel: str, content: str) -> None:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _make_repo(tmp_path: Path, *, spec_text: str = GOOD_SPEC) -> Path:
    repo = tmp_path / "repo"
    _write(repo, "commit-protocol.md", PROTOCOL)
    _write(repo, "project-state.json", json.dumps(PROJECT_STATE))
    _write(repo, "hooks/agent-config.json", json.dumps(AGENT_CONFIG))
    _write(repo, "commit-specs/commit-30.md", spec_text)
    _write(repo, "commit-specs/commit-29.md", C29_SPEC)
    _write(repo, "hooks/existing_file.py", "# exists\n")
    _write(repo, "hooks/context_telemetry.py", "# telemetry\n")
    return repo


def _ok_package() -> dict:
    return {
        "files": [{"path": "hooks/validate_commit_spec.py", "estimated_chars": 100}],
        "excluded_candidates": [],
        "unresolved": [],
        "expansion_triggers": [],
        "budget": {"selected_files": 1, "estimated_selected_chars": 100},
    }


@pytest.fixture(autouse=True)
def _patch_context_package(monkeypatch):
    """Default: a clean context package with no expansion triggers."""

    class FakeBuilder:
        def __init__(self, repo_root, rules, graph_path=None, mode="preflight"):
            pass

        def build(self, commit, agent):
            return _ok_package()

    monkeypatch.setattr(pf.context_engine, "ContextPackageBuilder", FakeBuilder)
    monkeypatch.setattr(pf.context_engine, "load_rules", lambda path: {})


def _which_all_available(name):
    return f"/usr/bin/{name}"


def test_proceed_true_when_score_high(tmp_path, monkeypatch):
    repo = _make_repo(tmp_path)
    monkeypatch.setattr(pf.shutil, "which", _which_all_available)

    result = pf.evaluate(repo, "C30", "adam")

    assert result["proceed"] is True
    assert result["score"] == 100
    assert result["blocking_violations"] == []
    assert result["commit"] == "C30"
    assert result["owner"] == {"id": "adam", "name": "Adam", "domain": "DevOps"}
    assert result["goal"] == "Store separate invocation telemetry records."
    assert result["files"] == [{"action": "edit", "path": "hooks/context_telemetry.py"}]
    assert result["report_path"] == ".context/preflight/C30.json"

    report_path = repo / ".context" / "preflight" / "C30.json"
    assert report_path.exists()
    full = json.loads(report_path.read_text(encoding="utf-8"))
    assert full["hard_points"] == 100
    assert set(full["categories"]) == set(pf.HARD_CATEGORY_POINTS)

    # Persisted reports must stay small: validate_pending_graph's per-commit
    # spec_results for every pending commit must not be embedded verbatim.
    report_bytes = report_path.read_text(encoding="utf-8").encode("utf-8")
    assert len(report_bytes) < 20_000

    graph_evidence = full["categories"]["pending_graph_validity"]["evidence"]
    assert "spec_results" not in graph_evidence
    assert graph_evidence["active_commit_spec_result"]["commit"] == "C30"
    assert full["raw_validators"]["validate_pending_graph"] == graph_evidence


def test_non_blocking_deductions_drop_score_below_80(tmp_path, monkeypatch):
    """All hard categories pass, but enough readiness deductions push score < 80
    while blocking_violations stays empty."""

    spec = GOOD_SPEC.replace(
        "## Environment Prerequisites\n\n- Python hook test environment.",
        "## Environment Prerequisites\n\n- Requires docker and npm on PATH.",
    )
    repo = _make_repo(tmp_path, spec_text=spec)

    # Make context package report an expansion trigger.
    class FakeBuilderWithExpansion:
        def __init__(self, repo_root, rules, graph_path=None, mode="preflight"):
            pass

        def build(self, commit, agent):
            pkg = _ok_package()
            pkg["expansion_triggers"] = ["no existing authoritative contract selected"]
            return pkg

    monkeypatch.setattr(pf.context_engine, "ContextPackageBuilder", FakeBuilderWithExpansion)

    # docker and npm unavailable (env prerequisites: -10), verification tool (pytest) unavailable (-10),
    # expansion trigger (-5). Total -25 -> score 75.
    def which_missing_some(name):
        if name in ("docker", "npm", "pytest"):
            return None
        return f"/usr/bin/{name}"

    monkeypatch.setattr(pf.shutil, "which", which_missing_some)

    result = pf.evaluate(repo, "C30", "adam")

    assert result["blocking_violations"] == []
    assert result["score"] < 80
    assert result["proceed"] is False
    assert result["decision_required"] is True

    joined_warnings = " | ".join(result["warnings"])
    assert "expansion" in joined_warnings.lower()
    assert "docker" in joined_warnings.lower()
    assert "npm" in joined_warnings.lower()
    assert "pytest" in joined_warnings.lower() or "Verification tool" in joined_warnings


def test_dependency_artifact_existence_deduction(tmp_path, monkeypatch):
    """C30 depends on C29, which lists hooks/missing_file.py (new) that does not exist."""
    repo = _make_repo(tmp_path)
    _write(repo, "commit-specs/commit-29.md", C29_SPEC_WITH_MISSING_FILE)
    monkeypatch.setattr(pf.shutil, "which", _which_all_available)

    result = pf.evaluate(repo, "C30", "adam")

    assert result["blocking_violations"] == []
    assert result["proceed"] is True  # only -5, score 95
    assert result["score"] == 95
    assert any("hooks/missing_file.py" in w and "C29" in w for w in result["warnings"])


def test_hard_violation_missing_done_when_blocks_regardless_of_score(tmp_path, monkeypatch):
    spec = GOOD_SPEC.split("## Done When")[0] + "## Not In This Commit\n\n- Nothing else.\n\n---\n\n## Return Contract\n\nReport stuff.\n"
    repo = _make_repo(tmp_path, spec_text=spec)
    monkeypatch.setattr(pf.shutil, "which", _which_all_available)

    result = pf.evaluate(repo, "C30", "adam")

    assert result["proceed"] is False
    assert any("acceptance_criteria_present" in v for v in result["blocking_violations"])


def test_hard_violation_missing_verification_command_blocks(tmp_path, monkeypatch):
    spec = GOOD_SPEC.replace(
        "```powershell\npytest -p no:cacheprovider hooks/tests/test_widget.py -q\n```",
        "```\n<TODO: fill in>\n```",
    )
    repo = _make_repo(tmp_path, spec_text=spec)
    monkeypatch.setattr(pf.shutil, "which", _which_all_available)

    result = pf.evaluate(repo, "C30", "adam")

    assert result["proceed"] is False
    assert any("verification_command_present" in v for v in result["blocking_violations"])


def test_ownership_mismatch_blocks(tmp_path, monkeypatch):
    state = dict(PROJECT_STATE)
    state["next_commit_assignee"] = "rex"
    repo = _make_repo(tmp_path)
    _write(repo, "project-state.json", json.dumps(state))
    monkeypatch.setattr(pf.shutil, "which", _which_all_available)

    result = pf.evaluate(repo, "C30", "adam")

    assert result["proceed"] is False
    assert any("ownership_match" in v for v in result["blocking_violations"])


def test_forbidden_path_blocks_scope_compliance(tmp_path, monkeypatch):
    spec = GOOD_SPEC.replace(
        "| `hooks/context_telemetry.py` | edit | Store separate invocation telemetry records |",
        "| `hooks/context_telemetry.py` | edit | Store separate invocation telemetry records |\n"
        "| `backend/app/main.py` | edit | not allowed |",
    )
    repo = _make_repo(tmp_path, spec_text=spec)
    _write(repo, "backend/app/main.py", "# main\n")
    monkeypatch.setattr(pf.shutil, "which", _which_all_available)

    result = pf.evaluate(repo, "C30", "adam")

    assert result["proceed"] is False
    assert any("scope_forbidden_compliance" in v for v in result["blocking_violations"])


def test_deterministic_repeated_runs(tmp_path, monkeypatch):
    repo = _make_repo(tmp_path)
    monkeypatch.setattr(pf.shutil, "which", _which_all_available)

    first = pf.evaluate(repo, "C30", "adam")
    second = pf.evaluate(repo, "C30", "adam")

    assert first["score"] == second["score"]
    assert first["blocking_violations"] == second["blocking_violations"]
    assert first["report_path"] == second["report_path"]
    assert first["proceed"] == second["proceed"]
    assert first["files"] == second["files"]


def test_compact_output_shape(tmp_path, monkeypatch):
    repo = _make_repo(tmp_path)
    monkeypatch.setattr(pf.shutil, "which", _which_all_available)

    result = pf.evaluate(repo, "C30", "adam")

    assert "owner" in result and "name" in result["owner"] and "domain" in result["owner"]
    assert "goal" in result
    assert all("action" in f and "path" in f for f in result["files"])
    assert "warnings" in result
    assert "decision_required" in result


def test_resolve_host_executable_docker_compose():
    cmd = "docker compose run --rm backend uv run pytest tests/api/test_documents.py -q"
    assert pf._resolve_host_executable(cmd) == "__docker_compose__"


def test_resolve_host_executable_drops_cd_builtin():
    cmd = "cd frontend; npm test -- --run"
    assert pf._resolve_host_executable(cmd) == "npm"


def test_resolve_host_executable_powershell_with_flags():
    cmd = "powershell -ExecutionPolicy Bypass -File scripts/smoke_policy_chat.ps1"
    assert pf._resolve_host_executable(cmd) == "powershell"


def test_verification_tool_unavailable_deduction(tmp_path, monkeypatch):
    repo = _make_repo(tmp_path)

    def which_missing_pytest(name):
        if name == "pytest":
            return None
        return f"/usr/bin/{name}"

    monkeypatch.setattr(pf.shutil, "which", which_missing_pytest)

    result = pf.evaluate(repo, "C30", "adam")

    assert result["blocking_violations"] == []
    assert any("Verification tool unavailable" in w for w in result["warnings"])
    assert result["score"] == 90


# ---------------------------------------------------------------------------
# evaluate_direct() -- lean Claude-direct readiness check
# ---------------------------------------------------------------------------


def test_evaluate_direct_ready(tmp_path, monkeypatch):
    repo = _make_repo(tmp_path)
    monkeypatch.setattr(pf.shutil, "which", _which_all_available)

    result = pf.evaluate_direct(repo, "C30", "adam")

    assert result == {
        "commit": "C30",
        "owner": "adam",
        "status": "ready",
        "proceed": True,
        "violations": [],
    }


def test_evaluate_direct_blocked_ownership_mismatch(tmp_path, monkeypatch):
    state = dict(PROJECT_STATE)
    state["next_commit_assignee"] = "rex"
    repo = _make_repo(tmp_path)
    _write(repo, "project-state.json", json.dumps(state))
    monkeypatch.setattr(pf.shutil, "which", _which_all_available)

    result = pf.evaluate_direct(repo, "C30", "adam")

    assert result["status"] == "blocked"
    assert result["proceed"] is False
    assert any(v.startswith("ownership_match:") for v in result["violations"])


def test_evaluate_direct_blocked_forbidden_path(tmp_path, monkeypatch):
    spec = GOOD_SPEC.replace(
        "| `hooks/context_telemetry.py` | edit | Store separate invocation telemetry records |",
        "| `hooks/context_telemetry.py` | edit | Store separate invocation telemetry records |\n"
        "| `backend/app/main.py` | edit | not allowed |",
    )
    repo = _make_repo(tmp_path, spec_text=spec)
    _write(repo, "backend/app/main.py", "# main\n")
    monkeypatch.setattr(pf.shutil, "which", _which_all_available)

    result = pf.evaluate_direct(repo, "C30", "adam")

    assert result["status"] == "blocked"
    assert result["proceed"] is False
    assert any(v.startswith("scope_forbidden_compliance:") for v in result["violations"])


def test_evaluate_direct_blocked_verification_command_missing(tmp_path, monkeypatch):
    spec = GOOD_SPEC.replace(
        "```powershell\npytest -p no:cacheprovider hooks/tests/test_widget.py -q\n```",
        "```\n<TODO: fill in>\n```",
    )
    repo = _make_repo(tmp_path, spec_text=spec)
    monkeypatch.setattr(pf.shutil, "which", _which_all_available)

    result = pf.evaluate_direct(repo, "C30", "adam")

    assert result["status"] == "blocked"
    assert result["proceed"] is False
    assert any(v.startswith("verification_command_present:") for v in result["violations"])


def test_evaluate_direct_dependency_scope_not_full_graph(tmp_path, monkeypatch):
    """evaluate_direct checks only this commit's own dependencies (C29 status),
    never the full pending graph -- pending_graph_validity is not a category at all."""
    protocol = PROTOCOL.replace("| 29 | prep-commit | Adam | done |", "| 29 | prep-commit | Adam | pending |")
    repo = _make_repo(tmp_path)
    _write(repo, "commit-protocol.md", protocol)
    monkeypatch.setattr(pf.shutil, "which", _which_all_available)

    result = pf.evaluate_direct(repo, "C30", "adam")

    assert result["status"] == "blocked"
    assert any(v.startswith("dependencies_satisfied:") for v in result["violations"])
    assert not any(v.startswith("pending_graph_validity:") for v in result["violations"])
    assert not any("pending_graph_validity" in v for v in result["violations"])


def test_evaluate_direct_no_side_effects(tmp_path, monkeypatch):
    """evaluate_direct persists nothing: no preflight report, context package,
    delegation artifacts, tool-cap state, telemetry, or dashboard render."""
    repo = _make_repo(tmp_path)
    monkeypatch.setattr(pf.shutil, "which", _which_all_available)

    result = pf.evaluate_direct(repo, "C30", "adam")

    assert result["proceed"] is True
    assert not (repo / ".context" / "preflight").exists()
    assert not (repo / ".context" / "runs").exists()
    assert not (repo / ".context" / "delegations").exists()
    assert not (repo / ".context" / "telemetry").exists()
    assert not (repo / "hooks" / "tool_cap.json").exists()
    assert not (repo / "constraint-dashboard.html").exists()


# ---------------------------------------------------------------------------
# evaluate() no longer renders the dashboard
# ---------------------------------------------------------------------------


def test_evaluate_does_not_render_dashboard(tmp_path, monkeypatch):
    repo = _make_repo(tmp_path)
    monkeypatch.setattr(pf.shutil, "which", _which_all_available)

    result = pf.evaluate(repo, "C30", "adam")

    assert result["proceed"] is True
    assert not (repo / "constraint-dashboard.html").exists()
