#!/usr/bin/env python3
"""
pre_commit_check.py — Universal Agentic Workflow
Runs before every `git commit`. Validates:
  1. Commit message format (conventional commits)
  2. Staged files are within the committing agent's domain
  3. The commit hasn't already been recorded as done in project-state.json
  4. The active commit spec has a valid Changes table (required by email notification)

Exit 0 = allow. Exit 2 = hard block.
"""

import subprocess
import sys
import re
import json
import os
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def load_agent_config() -> dict | None:
    git_root = Path(
        subprocess.run(["git", "rev-parse", "--show-toplevel"],
                       capture_output=True, text=True).stdout.strip()
    )
    config_path = git_root / "hooks" / "agent-config.json"
    if not config_path.exists():
        return None
    try:
        config = json.loads(config_path.read_text())
    except json.JSONDecodeError as e:
        print(f"[WARN] hooks/agent-config.json is malformed: {e}")
        return None
    if not config.get("initialized", False):
        return None
    return config


COMMIT_MSG_PATTERN = re.compile(
    r"^(feat|fix|chore|refactor|test|docs|perf|style)(\(.+\))?:\s+.{10,}"
)
COAUTHORED_PATTERN = re.compile(
    r"Co-Authored-By:\s+\S+\s+<([^>]+)>", re.IGNORECASE
)
CLAUDE_EMAIL = "claude@anthropic.com"
DIRECT_EXECUTION_MARKER = "Execution: Claude-direct"


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True).stdout.strip()


def get_staged_files():
    return [f for f in run(["git", "diff", "--cached", "--name-only"]).splitlines() if f]


def get_commit_message():
    if os.environ.get("GIT_MESSAGE"):
        return os.environ["GIT_MESSAGE"].strip()
    editmsg = Path(".git/COMMIT_EDITMSG")
    if editmsg.exists():
        return editmsg.read_text().strip()
    return ""


def detect_agent_email(msg):
    matches = COAUTHORED_PATTERN.findall(msg)
    return matches[0] if matches else None


def check_commit_message_format(msg):
    first_line = msg.splitlines()[0] if msg else ""
    if not COMMIT_MSG_PATTERN.match(first_line):
        return [
            f"Commit message format invalid.\n"
            f"  Got:      '{first_line}'\n"
            f"  Expected: '<type>(<scope>): <description (>=10 chars)>'\n"
            f"  Types:    feat | fix | chore | refactor | test | docs | perf | style"
        ]
    return []


def planned_files_for_commit(git_root: Path, msg: str) -> set[str]:
    if DIRECT_EXECUTION_MARKER.lower() not in msg.lower():
        return set()
    match = re.search(r"(?:^|\n)\s*[Cc]ommit\s+#0*(\d{1,3}[a-zA-Z]?)", msg)
    if not match:
        return set()
    spec_path = git_root / "commit-specs" / f"commit-{match.group(1).lower()}.md"
    if not spec_path.is_file():
        return set()
    content = spec_path.read_text(encoding="utf-8")
    section_match = re.search(
        r"^## Files To Modify Or Add\s*$\n(.*?)(?=^##\s+|\Z)",
        content,
        re.MULTILINE | re.DOTALL | re.IGNORECASE,
    )
    if not section_match:
        return set()
    return set(re.findall(r"\|\s*`([^`]+)`\s*\|", section_match.group(1)))


def check_domain_boundaries(staged, agent_email, config, direct_allowed=None):
    agents = config.get("agents", {})
    universal = config.get("universal_allowed", [])
    agent_cfg = agents.get(agent_email)
    if not agent_cfg:
        return [
            f"Agent email '{agent_email}' not found in hooks/agent-config.json.\n"
            f"  Known agents: {list(agents.keys())}"
        ]
    allowed = agent_cfg.get("domains", [])
    exact_allowed = set(direct_allowed or [])
    violations = [
        f for f in staged
        if not any(f == u or f.startswith(u) for u in universal)
        and not any(f == a or f.startswith(a) for a in allowed)
        and f not in exact_allowed
    ]
    if violations:
        name = agent_cfg.get("name", agent_email)
        return [
            f"Domain boundary violation for {name} ({agent_email}).\n"
            f"  Staged outside domain:\n"
            + "".join(f"    x {v}\n" for v in violations)
            + f"  Allowed prefixes:\n"
            + "".join(f"    v {a}\n" for a in allowed)
        ]
    return []


def check_commit_spec_table(msg):
    """Verify the active commit spec has a valid Changes table parseable by notify_agent_done.py."""
    git_root = Path(
        subprocess.run(["git", "rev-parse", "--show-toplevel"],
                       capture_output=True, text=True).stdout.strip()
    )
    m = re.search(r"(?:^|\n)\s*[Cc]ommit\s+#0*(\d{1,3}[a-zA-Z]?)", msg)
    if not m:
        return []
    num = m.group(1)
    spec = git_root / "commit-specs" / f"commit-{num}.md"
    if not spec.exists():
        return [
            f"commit-specs/commit-{num}.md not found.\n"
            f"  Every commit must have a spec file before it can be committed."
        ]
    content = spec.read_text(encoding="utf-8")
    valid_rows = [
        line for line in content.splitlines()
        if line.startswith("|")
        and re.search(r"`[^`]+`", line)
        and not line.strip().startswith("|---")
        and not re.match(r"\|\s*(File|Path)\s*\|", line, re.IGNORECASE)
    ]
    if not valid_rows:
        return [
            f"commit-specs/commit-{num}.md has no valid Changes table.\n"
            f"  Expected rows like: | `path/to/file` | new | description |\n"
            f"  The email notification reads this table for the file list.\n"
            f"  Add a Changes table before committing."
        ]
    return []


def check_not_already_done(msg):
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
    m = re.search(r"(?:^|\n)\s*[Cc]ommit\s+#0*(\d{1,2})\b", msg)
    if not m:
        return []
    commit_num = m.group(1).zfill(2)
    if commit_num in commits_done:
        return [f"Commit #{commit_num} is already recorded as done in project-state.json."]
    return []


def main():
    if os.environ.get("ERAN_COMMIT") == "1":
        print("ERAN_COMMIT=1 -- pre-commit checks bypassed.")
        return 0

    staged = get_staged_files()
    if not staged:
        return 0

    msg = get_commit_message()
    errors = []
    warnings = []

    config = load_agent_config()
    if config is None:
        print(
            "[WARN] hooks/agent-config.json not found or not initialized.\n"
            "    Domain boundary checks are SKIPPED for this commit."
        )
        errors.extend(check_commit_message_format(msg))
        if errors:
            print("\n[FAIL] Pre-commit check FAILED:\n")
            for e in errors:
                print(f"  {e}\n")
            return 2
        print(f"[OK] Commit message format valid. ({len(staged)} file(s) staged)")
        return 0

    errors.extend(check_commit_message_format(msg))

    agent_email = detect_agent_email(msg)
    if agent_email:
        direct_allowed = set()
        if agent_email.lower() == CLAUDE_EMAIL:
            git_root = Path(
                subprocess.run(
                    ["git", "rev-parse", "--show-toplevel"],
                    capture_output=True,
                    text=True,
                ).stdout.strip()
            )
            direct_allowed = planned_files_for_commit(git_root, msg)
        errors.extend(
            check_domain_boundaries(
                staged,
                agent_email,
                config,
                direct_allowed=direct_allowed,
            )
        )
    else:
        warnings.append(
            "No Co-Authored-By trailer found.\n"
            "    Domain boundary checks skipped for this commit."
        )

    errors.extend(check_not_already_done(msg))
    errors.extend(check_commit_spec_table(msg))

    if warnings:
        print("\n[WARN] Pre-commit warnings:")
        for w in warnings:
            print(f"   {w}")

    if errors:
        print("\n[FAIL] Pre-commit check FAILED -- commit blocked:\n")
        for i, e in enumerate(errors, 1):
            print(f"  [{i}] {e}\n")
        print("Fix the above issues, then commit again.\n")
        return 2

    agent_name = config["agents"].get(agent_email, {}).get("name", agent_email) if agent_email else "unknown"
    print(f"[OK] Pre-commit check passed ({len(staged)} file(s) staged, agent: {agent_name})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
