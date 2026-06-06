#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
notify_on_stop.py — Stop hook: send pending commit-approval email on Windows.

Claude writes hooks/.pending_notify.json from the sandbox (no network).
This script runs via the Stop hook on Windows (has network), reads the flag,
sends the email using the cached file list, then deletes the flag.
"""

import json
import os
import sys
from pathlib import Path
import subprocess

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(subprocess.check_output(
    ["git", "rev-parse", "--show-toplevel"], text=True
).strip())

FLAG = ROOT / "hooks" / ".pending_notify.json"


def main() -> int:
    if not FLAG.exists():
        return 0

    try:
        data = json.loads(FLAG.read_text(encoding="utf-8"))
    except Exception as e:
        print("[notify_stop] Could not read flag file:", e, file=sys.stderr)
        try: FLAG.unlink(missing_ok=True)
        except OSError: pass
        return 0

    # Delete flag before send so a crash doesn't re-fire
    try:
        FLAG.unlink(missing_ok=True)
    except OSError:
        pass

    # Import the notify module to reuse build_email / send_email
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "notify", ROOT / "hooks" / "notify_agent_done.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    env  = mod.load_env()
    if not mod.smtp_configured(env):
        print("[notify_stop] SMTP not configured — skipping.")
        return 0

    # Build commit info from flag (never re-run git diff — index is empty post-commit)
    state = mod.load_state()
    info = {
        "number":  data.get("NOTIFY_NUM", "??"),
        "name":    data.get("NOTIFY_NAME", "(pending)"),
        "agent":   data.get("NOTIFY_AGENT", "Claude"),
        "project": state.get("project", ROOT.name),
        "what":    data.get("NOTIFY_WHAT", ""),
        "why":     data.get("NOTIFY_WHY", ""),
    }

    # Use cached file list captured at --write-flag time (before git commit)
    files     = data.get("files", [])
    diff_stat = data.get("diff_stat", "")

    subject, plain, html = mod.build_email(env, info, files, diff_stat)

    try:
        mod.send_email(env, subject, plain, html)
    except Exception as e:
        print("[notify_stop] Failed:", e, file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
