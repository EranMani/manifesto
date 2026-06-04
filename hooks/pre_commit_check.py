#!/usr/bin/env python3
"""
pre_commit_check.py — Universal Agentic Workflow
Runs before every `git commit`. Validates:
  1. Commit message format (conventional commits)
  2. Staged files are within the committing agent's domain
  3. The commit hasn't already been recorded as done in project-state.json

Configuration is read from hooks/agent-config.json — written by /init.
If agent-config.json is missing or not initialized, the hook warns and allows
the commit through (graceful degradation — never block an uninitialized project).

Exit 0 = allow. Exit 2 = hard block.
"""

import subprocess
import sys
import re
import json
import os
from pathlib import Path


# ---------------------------------------------------------------------------
# Load agent configuration from hooks/agent-config.json
# ---------------------------------------------------------------------------

def load_agent_config() -> dict | None:
    """
    Looks for agent-config.json relative to the git root.
    Returns the parsed config, or None if not found / not initialized.
    """
    git_root = Path(
        subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True
        ).stdout.strip()
    )
    config_path = git_root / "hooks" / "agent-config.json"

    if not config_path.exists():
        return None

    try:
        config = json.loads(config_path.read_text())
    except json.JSONDecodeError as e:
        print(f"⚠️  hooks/agent-config.json is malformed: {e}")
        print("    Allowing commit through — fix the config and re-commit.")
        return None

    if not config.get("initialized", False):
        return None

    return config


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

COMMIT_MSG_PATTERN = re.compile(
    r"^(feat|fix|chore|refactor|test|docs|perf|style)(\(.+\))?:\s+.{10,}"
)

COAUTHORED_PATTERN = re.compile(
    r"Co-Authored-By:\s+\S+\s+<([^>]+)>", re.IGNORECASE
)


def run(cmd: list[str]) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout.strip()


def get_staged_files() -> list[str]:
    output = run(["git", "diff", "--cached", "--name-only"])
    return [f for f in output.splitlines() if f]


def get_commit_message() -> str:
    editmsg = Path(".git/COMMIT_EDITMSG")
    if editmsg.exists():
        return editmsg.read_text().strip()
    return os.environ.get("GIT_MESSAGE", "")


def detect_agent_email(msg: str) -> str | None:
    matches = COAUTHORED_PATTERN.findall(msg)
    return matches[0] if matches else None


def check_commit_message_format(msg: str) -> list[str]:
    errors = []
    first_line = msg.splitlines()[0] if msg else ""
    if not COMMIT_MSG_PATTERN.match(first_line):
        errors.append(
            f"Commit message format invalid.\n"
            f"  Got:      '{first_line}'\n"
            f"  Expected: '<type>(<scope>): <description (≥10 chars)>'\n"
            f"  Types:    feat | fix | chore | refactor | test | docs | perf | style"
        )
    return errors


def check_domain_boundaries(
    staged: list[str],
    agent_email: str,
    config: dict
) -> list[str]:
    agents = config.get("agents", {})
    universal = config.get("universal_allowed", [])

    agent_cfg = agents.get(agent_email)
    if not agent_cfg:
        return [
            f"Agent email '{agent_email}' not found in hooks/agent-config.json.\n"
            f"  Known agents: {list(agents.keys())}\n"
            f"  Run /init to regenerate the config, or add this agent manually."
        ]

    allowed = agent_cfg.get("domains", [])
    violations = []

    for f in staged:
        if any(f == u or f.startswith(u) for u in universal):
            continue
        if not any(f == a or f.startswith(a) for a in allowed):
            violations.append(f)

    if violations:
        name = agent_cfg.get("name", agent_email)
        return [
            f"Domain boundary violation for {name} ({agent_email}).\n"
            f"  Staged outside domain:\n"
            + "".join(f"    ✗ {v}\n" for v in violations)
            + f"  Allowed prefixes:\n"
            + "".join(f"    ✓ {a}\n" for a in allowed)
        ]

    return []


def check_not_already_done(msg: str) -> list[str]:
    state_path = Path("project-state.json")
    if not state_path.exists():
        return []
    try:
        state = json.loads(state_path.read_text())
    except (json.JSONDecodeError, KeyError):
        return []

    commits_done = state.get("commits_done", [])
    if not commits_done:
        return []

    # Extract commit number from message marker "Commit #NN"
    m = re.search(r"(?:^|\n)\s*[Cc]ommit\s+#0*(\d{1,2})\b", msg)
    if not m:
        return []

    commit_num = m.group(1).zfill(2)
    if commit_num in commits_done:
        return [
            f"Commit #{commit_num} is already recorded as done in project-state.json. "
            f"Did you mean to start the next step?"
        ]
    return []


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    staged = get_staged_files()
    if not staged:
        return 0

    msg = get_commit_message()
    errors: list[str] = []
    warnings: list[str] = []

    # Load config — if missing or uninitialized, warn and allow through
    config = load_agent_config()
    if config is None:
        print(
            "⚠️  hooks/agent-config.json not found or not initialized.\n"
            "    Domain boundary checks are SKIPPED for this commit.\n"
            "    Run /init to set up the project and enable full enforcement."
        )
        # Still enforce commit message format even without config
        errors.extend(check_commit_message_format(msg))
        if errors:
            print("\n🚫 Pre-commit check FAILED:\n")
            for e in errors:
                print(f"  {e}\n")
            return 2
        print(f"✅ Commit message format valid. ({len(staged)} file(s) staged)")
        return 0

    # Full enforcement — config is present and initialized
    errors.extend(check_commit_message_format(msg))

    agent_email = detect_agent_email(msg)
    if agent_email:
        errors.extend(check_domain_boundaries(staged, agent_email, config))
    else:
        warnings.append(
            "No Co-Authored-By trailer found.\n"
            "    Add 'Co-Authored-By: AgentName <email>' to identify the committing agent.\n"
            "    Domain boundary checks skipped for this commit."
        )

    errors.extend(check_not_already_done(msg))

    if warnings:
        print("\n⚠️  Pre-commit warnings:")
        for w in warnings:
            print(f"   {w}")

    if errors:
        print("\n🚫 Pre-commit check FAILED — commit blocked:\n")
        for i, e in enumerate(errors, 1):
            print(f"  [{i}] {e}\n")
        print("Fix the above issues, then commit again.\n")
        return 2

    agent_name = config["agents"].get(agent_email, {}).get("name", agent_email) if agent_email else "unknown"
    print(f"✅ Pre-commit check passed ({len(staged)} file(s) staged, agent: {agent_name})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
