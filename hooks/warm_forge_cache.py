#!/usr/bin/env python3
"""
warm_forge_cache.py — Background graph-RAG cache warmer.

Runs as a UserPromptSubmit hook. On each user message, checks if
.forge/report.json is missing or stale (> 1 hour old). If so, launches
forge_scan.py in the background to warm the cache for /ask and /forge.

Designed to be invisible: prints nothing on cache hit, exits immediately,
and never blocks the user's interaction. The background scan process is
fully detached.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
REPORT_PATH = REPO_ROOT / ".forge" / "report.json"
LOCK_PATH = REPO_ROOT / ".forge" / ".scan_lock"
FORGE_SCAN = REPO_ROOT / "hooks" / "forge_scan.py"
MAX_AGE_SECONDS = 3600  # 1 hour


def _is_stale() -> bool:
    """Check if report.json is missing or older than MAX_AGE_SECONDS."""
    if not REPORT_PATH.exists():
        return True
    try:
        age = time.time() - REPORT_PATH.stat().st_mtime
        return age > MAX_AGE_SECONDS
    except OSError:
        return True


def _scan_already_running() -> bool:
    """Prevent concurrent scans via a simple lock file with PID check."""
    if not LOCK_PATH.exists():
        return False
    try:
        lock_data = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
        pid = lock_data.get("pid")
        started = lock_data.get("started", 0)
        # Stale lock: if the lock is older than 5 minutes, ignore it
        if time.time() - started > 300:
            LOCK_PATH.unlink(missing_ok=True)
            return False
        # Check if PID is still alive (Windows-compatible)
        if pid and os.name == "nt":
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                capture_output=True, text=True, timeout=5,
            )
            if str(pid) not in result.stdout:
                LOCK_PATH.unlink(missing_ok=True)
                return False
        return True
    except (json.JSONDecodeError, OSError, subprocess.TimeoutExpired):
        LOCK_PATH.unlink(missing_ok=True)
        return False


def _launch_background_scan() -> None:
    """Launch forge_scan.py as a detached background process."""
    forge_dir = REPO_ROOT / ".forge"
    forge_dir.mkdir(exist_ok=True)

    if os.name == "nt":
        # Windows: use CREATE_NO_WINDOW + DETACHED_PROCESS
        CREATE_NO_WINDOW = 0x08000000
        DETACHED_PROCESS = 0x00000008
        proc = subprocess.Popen(
            [sys.executable, str(FORGE_SCAN), "--path", str(REPO_ROOT),
             "--out", str(forge_dir)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=CREATE_NO_WINDOW | DETACHED_PROCESS,
            cwd=str(REPO_ROOT),
        )
    else:
        proc = subprocess.Popen(
            [sys.executable, str(FORGE_SCAN), "--path", str(REPO_ROOT),
             "--out", str(forge_dir)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            cwd=str(REPO_ROOT),
        )

    # Write lock file with PID
    LOCK_PATH.write_text(
        json.dumps({"pid": proc.pid, "started": time.time()}),
        encoding="utf-8",
    )


def main() -> None:
    if not _is_stale():
        return

    if _scan_already_running():
        return

    _launch_background_scan()


if __name__ == "__main__":
    main()
