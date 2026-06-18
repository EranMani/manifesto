from __future__ import annotations

import importlib.util
import json
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "notify_agent_done.py"
SPEC = importlib.util.spec_from_file_location("notify_agent_done_test", MODULE_PATH)
notify = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(notify)


def test_blocked_email_contains_required_decision_context():
    subject, plain, html = notify.build_blocked_email({
        "project": "manifesto",
        "number": "69A",
        "name": "browse-markdown-formatting",
        "agent": "Claude",
        "issue": "A required test file is outside the approved scope.",
        "decision": "Continuing would bypass the commit boundary.",
        "solution": "Add the test file to the approved specification and rerun verification.",
    })

    assert subject == "manifesto — commit 69A — auto mode stopped — decision required"
    assert "Raised by: Claude" in plain
    assert "outside the approved scope" in plain
    assert "bypass the commit boundary" in plain
    assert "Add the test file" in plain
    assert "Why Claude stopped" in html
    assert "Recommended resolution" in html


def test_write_blocked_notify_uses_atomic_shared_flag(tmp_path, monkeypatch):
    monkeypatch.setattr(notify, "ROOT", tmp_path)
    monkeypatch.setattr(
        notify,
        "get_next_commit_from_protocol",
        lambda: ("70", "assistant-markdown-rendering", "Aria"),
    )
    (tmp_path / "hooks").mkdir()

    notify.write_blocked_notify(
        issue="verification failed",
        decision="Aria reported a contract mismatch",
        solution="approve a bounded spec correction",
        agent="Aria",
    )

    flag = tmp_path / "hooks" / ".pending_notify.json"
    data = json.loads(flag.read_text(encoding="utf-8"))
    assert data["notification_type"] == "blocked"
    assert data["NOTIFY_NUM"] == "70"
    assert data["NOTIFY_AGENT"] == "Aria"
    assert data["ISSUE"] == "verification failed"
    assert not flag.with_suffix(".json.tmp").exists()


def test_auto_completed_email_is_informational_not_approval_request():
    subject, plain, html = notify.build_auto_completed_email({
        "project": "manifesto",
        "number": "71",
        "name": "evidence-graph-layout",
        "agent": "Claude",
        "summary": "Reorganized the graph into entities and a timeline.",
        "verification": "Frontend build passed.",
        "next_commit": "No remaining work.",
    })

    assert subject == "manifesto — commit 71 — completed automatically"
    assert "No approval is required" in plain
    assert "awaiting your approval" not in plain
    assert "completed automatically" in html
    assert "Frontend build passed" in html


def test_write_auto_completed_notify_uses_shared_atomic_flag(tmp_path, monkeypatch):
    monkeypatch.setattr(notify, "ROOT", tmp_path)
    monkeypatch.setattr(
        notify,
        "get_next_commit_from_protocol",
        lambda: ("72", "next-feature", "Aria"),
    )
    (tmp_path / "hooks").mkdir()

    notify.write_auto_completed_notify(
        summary="C71 completed",
        verification="build passed",
        next_commit="C72",
        num="71",
        name="evidence-graph-layout",
        agent="Claude",
    )

    flag = tmp_path / "hooks" / ".pending_notify.json"
    data = json.loads(flag.read_text(encoding="utf-8"))
    assert data["notification_type"] == "auto_completed"
    assert data["NOTIFY_NUM"] == "71"
    assert data["SUMMARY"] == "C71 completed"
    assert not flag.with_suffix(".json.tmp").exists()
