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

    assert "C69A auto mode stopped" in subject
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
