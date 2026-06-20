#!/usr/bin/env python3
"""CLI runner for /ask evaluation harness.

Executes `claude -p` commands non-interactively and captures the text
output for deterministic assertion testing. This runs the actual Claude
Code CLI against the real codebase — no mocking.

Usage:
    from ask_test_runner import run_ask
    output = run_ask("/ask founder what can this product do?")
"""

from __future__ import annotations

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TIMEOUT = 120


def run_ask(
    prompt: str,
    *,
    timeout: int = DEFAULT_TIMEOUT,
    cwd: Path | None = None,
) -> str:
    """Run a /ask command via claude -p and return the captured output.

    Args:
        prompt: The full /ask command (e.g., "/ask founder what can this do?")
        timeout: Maximum seconds to wait (default 120)
        cwd: Working directory (default: repo root)

    Returns:
        The captured stdout text.

    Raises:
        subprocess.TimeoutExpired: If the command exceeds the timeout.
        RuntimeError: If claude CLI is not available.
    """
    if cwd is None:
        cwd = REPO_ROOT

    try:
        result = subprocess.run(
            ["claude", "-p", prompt],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(cwd),
        )
    except FileNotFoundError:
        raise RuntimeError(
            "claude CLI not found. Install Claude Code: "
            "https://docs.anthropic.com/en/docs/claude-code"
        )

    return result.stdout
