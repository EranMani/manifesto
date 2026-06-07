#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
notify_agent_done.py — Email notification when Claude is waiting for commit approval.

Called directly by Claude BEFORE git commit, using Windows Python (not the sandbox).
Reads staged diff for file list; commit detail comes from NOTIFY_* env vars.

Usage:
  NOTIFY_NUM="05" NOTIFY_NAME="add auth" NOTIFY_AGENT="Rex" \
  NOTIFY_WHAT="..." NOTIFY_WHY="..." \
  python hooks/notify_agent_done.py --pre-commit

  python hooks/notify_agent_done.py --test    # send test email immediately

Required env vars (in .env):
  SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD
  NOTIFY_EMAIL  — recipient (defaults to SMTP_USER)
"""

import json
import os
import re
import smtplib
import subprocess
import sys
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(subprocess.check_output(
    ["git", "rev-parse", "--show-toplevel"], text=True
).strip())

TEST_MODE    = "--test" in sys.argv
PRE_COMMIT   = "--pre-commit" in sys.argv  # called before git commit; reads NOTIFY_* env vars


# ── Config ────────────────────────────────────────────────────────────────────

def load_env() -> dict:
    env = {}
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            env[key.strip()] = val.strip().strip('"').strip("'")
    for key in ["SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD", "NOTIFY_EMAIL"]:
        if key in os.environ:
            env[key] = os.environ[key]
    return env


def smtp_configured(env: dict) -> bool:
    return all(env.get(k) for k in ["SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD"])


# ── Git helpers ───────────────────────────────────────────────────────────────

def git(*args) -> str:
    return subprocess.run(list(args), capture_output=True, text=True, cwd=ROOT).stdout.strip()


def get_commit_info() -> dict:
    if TEST_MODE:
        return {
            "number":  "XX",
            "name":    "test commit — email system check",
            "agent":   "Claude",
            "project": load_state().get("project", ROOT.name),
            "what":    "This is a test email to verify the notification system is working.",
            "why":     "Triggered manually via --test flag.",
        }

    # Pre-commit mode: commit hasn't happened yet — read from env vars passed by Claude
    if PRE_COMMIT:
        state = load_state()
        return {
            "number":  os.environ.get("NOTIFY_NUM", "??"),
            "name":    os.environ.get("NOTIFY_NAME", "(pending)"),
            "agent":   os.environ.get("NOTIFY_AGENT", "Claude"),
            "project": state.get("project", ROOT.name),
            "what":    os.environ.get("NOTIFY_WHAT", ""),
            "why":     os.environ.get("NOTIFY_WHY", ""),
        }

    message = git("git", "log", "-1", "--pretty=%B")
    subject = git("git", "log", "-1", "--pretty=%s")

    # Commit name: strip conventional prefix
    name = re.sub(r"^(feat|fix|chore|refactor|docs|test|style|ci)(\([^)]+\))?:\s*", "", subject, flags=re.IGNORECASE)

    # Agent from Co-Authored-By
    agent = "Claude"
    m = re.search(r"Co-Authored-By:\s*(\w+)", message, re.IGNORECASE)
    if m:
        agent = m.group(1).title()

    # Commit number: message → last done in protocol → state
    number = None
    for pat in [r"(?:^|\n)\s*[Cc]ommit\s+#0*(\d{1,2}[a-zA-Z]?)", r"(?:^|\n)\s*[Ss]tep\s+#0*(\d{1,2}[a-zA-Z]?)"]:
        m2 = re.search(pat, message)
        if m2:
            number = m2.group(1).zfill(2)
            break
    if not number:
        number = get_commit_number_from_protocol()

    # What/Why from commit body
    what, why = "", ""
    for line in message.splitlines():
        mw = re.match(r"^\s*What:\s*(.+)", line, re.IGNORECASE)
        if mw: what = mw.group(1).strip()
        my = re.match(r"^\s*Why:\s*(.+)", line, re.IGNORECASE)
        if my: why = my.group(1).strip()

    state = load_state()
    return {
        "number":  number or "??",
        "name":    name,
        "agent":   agent,
        "project": state.get("project", ROOT.name),
        "what":    what,
        "why":     why,
    }


def get_commit_number_from_protocol() -> str | None:
    protocol = ROOT / "commit-protocol.md"
    if not protocol.exists():
        return None
    last_done = None
    for line in protocol.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"): continue
        cells = [c.strip() for c in line.split("|") if c.strip()]
        if len(cells) < 4 or not cells[0].isdigit(): continue
        if "done" in cells[3].lower():
            last_done = cells[0].zfill(2)
    return last_done


def get_next_commit_from_protocol() -> tuple[str, str, str]:
    """Return (number, name, agent) of the first pending row in commit-protocol.md."""
    protocol = ROOT / "commit-protocol.md"
    if not protocol.exists():
        return "??", "(unknown)", "Claude"
    for line in protocol.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.split("|") if c.strip()]
        if len(cells) < 4:
            continue
        num, name, agent, status = cells[0], cells[1], cells[2], cells[3]
        if "pending" in status.lower():
            return num, name, agent
    return "??", "(unknown)", "Claude"


def load_state() -> dict:
    f = ROOT / "project-state.json"
    if f.exists():
        try: return json.loads(f.read_text(encoding="utf-8"))
        except Exception: pass
    return {}


def get_files_from_commit_spec() -> list:
    """Parse the active commit spec's Changes table for the authoritative file list."""
    num, _, _ = get_next_commit_from_protocol()
    if num == "??":
        return []
    spec = ROOT / "commit-specs" / f"commit-{num}.md"
    if not spec.exists():
        return []
    files = []
    in_table = False
    for line in spec.read_text(encoding="utf-8").splitlines():
        # Detect markdown table rows with file paths: | `path/to/file` | ...
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.split("|") if c.strip()]
        if not cells:
            continue
        # Skip header/separator rows
        if cells[0].startswith("-") or cells[0].lower() in ("file", "path"):
            continue
        # Extract path from backtick-quoted first cell
        m = re.match(r"`([^`]+)`", cells[0])
        if not m:
            continue
        path_val = m.group(1)
        # Determine status from second cell keyword
        status_raw = cells[1].lower() if len(cells) > 1 else ""
        if "new" in status_raw or "add" in status_raw or "creat" in status_raw:
            status = "Added"
        elif "delet" in status_raw or "remov" in status_raw:
            status = "Deleted"
        else:
            status = "Modified"
        files.append({"status": status, "path": path_val})
    return files


def get_diff_files() -> list:
    if TEST_MODE:
        return [
            {"status": "Added",    "path": "hooks/notify_agent_done.py"},
            {"status": "Modified", "path": "CLAUDE.md"},
            {"status": "Modified", "path": ".env.example"},
        ]
    if PRE_COMMIT:
        # Read the *actual* working-tree state via `git status --porcelain`.
        # Unlike `git diff --cached`, this also captures untracked files (??) —
        # which is what new agent-created files (e.g. Login.tsx) look like
        # before `git add` runs. This is the ground truth for "what would this
        # commit look like right now."
        #
        # NOTE: we deliberately do NOT use get_files_from_commit_spec() as the
        # source here — it keys off get_next_commit_from_protocol(), whose
        # "first pending row" can point at a stale/wrong commit relative to
        # what's actually in the working tree, producing the exact
        # "shows the previous commit's files" symptom this replaces.
        #
        # Filter out protocol-managed paths that would pollute the list when
        # chore/state commits are staged alongside agent work.
        PROTOCOL_PREFIXES = (
            "commit-specs/",
            "commit-protocol.md",
            "project-state.json",
            "TOKEN_RECORDS.md",
            "CONSTRAINT_LOG.md",
            "DECISIONS.md",
            "ARCHITECTURE.md",
            "GLOSSARY.md",
            "team-preferences.md",
            ".claude/agents/logs/",
            "backend/DOMAIN_MAP.md",
            "frontend/DOMAIN_MAP.md",
            "hooks/.pending_notify.json",
            "hooks/.notify_debug.log",
        )
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, cwd=ROOT
        )
        # Porcelain format: XY <path> (XY = 2-char status code; rename uses " -> ")
        #   staged:   A_, M_, D_, R_   (X = index status)
        #   unstaged: _M, _D           (Y = worktree status)
        #   untracked: ??
        status_map = {"A": "Added", "M": "Modified", "D": "Deleted", "R": "Renamed", "?": "Added"}
        files = []
        seen = set()
        for line in result.stdout.splitlines():
            if len(line) < 4:
                continue
            code = line[:2]
            path = line[3:].strip()
            if " -> " in path:
                path = path.split(" -> ", 1)[1]
            if not path or path in seen:
                continue
            if any(path.startswith(p) for p in PROTOCOL_PREFIXES):
                continue
            # Prefer the index (staged) status if present, else worktree status
            letter = code[0] if code[0] != " " else code[1]
            files.append({"status": status_map.get(letter, "Modified"), "path": path})
            seen.add(path)
        return files
    result = subprocess.run(
        ["git", "diff-tree", "--no-commit-id", "-r", "--name-status", "HEAD"],
        capture_output=True, text=True, cwd=ROOT
    )
    files = []
    status_map = {"A": "Added", "M": "Modified", "D": "Deleted", "R": "Renamed"}
    for line in result.stdout.strip().splitlines():
        parts = line.split("\t")
        if len(parts) >= 2:
            files.append({"status": status_map.get(parts[0][0], parts[0][0]), "path": parts[-1]})
    return files


def get_diff_stat() -> str:
    if TEST_MODE:
        return "3 files changed, 42 insertions(+), 7 deletions(-)"
    if PRE_COMMIT:
        # If the spec gave us a file list, build a stat line from spec files only
        # so we don't count chore/protocol files that may be co-staged.
        # Build the stat line from the same file list get_diff_files() produces
        # (working-tree truth, including untracked files), so the count and the
        # listed paths always agree. `git diff --stat` alone can't show untracked
        # files, so we just report a count derived from get_diff_files().
        files = get_diff_files()
        if not files:
            return ""
        added = sum(1 for f in files if f["status"] == "Added")
        modified = sum(1 for f in files if f["status"] == "Modified")
        deleted = sum(1 for f in files if f["status"] == "Deleted")
        parts = []
        if added:
            parts.append(f"{added} added")
        if modified:
            parts.append(f"{modified} modified")
        if deleted:
            parts.append(f"{deleted} deleted")
        suffix = " (" + ", ".join(parts) + ")" if parts else ""
        return f"{len(files)} file(s) changed{suffix}"
    result = subprocess.run(
        ["git", "show", "--stat", "--format=", "HEAD"],
        capture_output=True, text=True, cwd=ROOT
    )
    if result.stdout.strip():
        lines = [l for l in result.stdout.strip().splitlines() if l.strip()]
        return lines[-1].strip()
    return ""


# ── Email builder ─────────────────────────────────────────────────────────────

STATUS_COLORS = {
    "Added":    ("#1D9E75", "A"),
    "Modified": ("#BA7517", "M"),
    "Deleted":  ("#A32D2D", "D"),
    "Renamed":  ("#185FA5", "R"),
}


def build_file_rows(files: list) -> str:
    if not files:
        return "<tr><td colspan='2' style='color:#888;padding:6px 0;'>No changes detected.</td></tr>"
    rows = []
    for f in files:
        color, letter = STATUS_COLORS.get(f["status"], ("#888", "?"))
        rows.append(
            "<tr>"
            "<td style='padding:4px 8px 4px 0;font-family:monospace;font-size:12px;"
            "color:" + color + ";font-weight:600;white-space:nowrap;'>" + letter + "</td>"
            "<td style='padding:4px 0;font-family:monospace;font-size:12px;"
            "color:#333;word-break:break-all;'>" + f["path"] + "</td>"
            "</tr>"
        )
    return "\n".join(rows)


def build_what_why_html(what: str, why: str) -> str:
    if not what and not why:
        return ""
    rows = ""
    if what:
        rows += (
            "<tr><td style='padding:4px 12px 4px 0;font-size:12px;font-weight:600;color:#999;"
            "white-space:nowrap;vertical-align:top;'>What</td>"
            "<td style='padding:4px 0;font-size:13px;color:#1a1a18;line-height:1.6;'>" + what + "</td></tr>"
        )
    if why:
        rows += (
            "<tr><td style='padding:4px 12px 4px 0;font-size:12px;font-weight:600;color:#999;"
            "white-space:nowrap;vertical-align:top;'>Why</td>"
            "<td style='padding:4px 0;font-size:13px;color:#444;line-height:1.6;'>" + why + "</td></tr>"
        )
    return (
        "<div style='background:#f9f8f4;border-radius:8px;padding:14px 16px;margin-bottom:20px;'>"
        "<table cellpadding='0' cellspacing='0' style='width:100%;'>" + rows + "</table></div>"
    )


def build_email(env: dict, info: dict, files: list, diff_stat: str):
    project     = info["project"]
    commit_num  = info["number"]
    commit_name = info["name"]
    agent_name  = info["agent"]
    now         = datetime.now().strftime("%a %d %b %Y, %H:%M")
    what        = info.get("what", "")
    why         = info.get("why", "")

    subject = project + " — commit " + commit_num + " — " + agent_name + " finished"
    if TEST_MODE:
        subject = "[TEST] " + subject

    file_rows     = build_file_rows(files)
    what_why_html = build_what_why_html(what, why)
    stat_line     = ("<p style='margin:0 0 12px;font-size:12px;color:#888;'>" + diff_stat + "</p>") if diff_stat else ""

    html = (
        "<!DOCTYPE html><html lang='en'><head>"
        "<meta charset='UTF-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
        "</head><body style='margin:0;padding:0;background:#f4f4f0;"
        "font-family:-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif;'>"
        "<table width='100%' cellpadding='0' cellspacing='0' style='background:#f4f4f0;padding:32px 16px;'>"
        "<tr><td align='center'>"
        "<table width='560' cellpadding='0' cellspacing='0' style='background:#fff;border-radius:12px;"
        "border:1px solid #e0dfd8;overflow:hidden;max-width:560px;'>"
        "<tr><td style='background:#f9f8f4;border-bottom:1px solid #e0dfd8;padding:10px 20px;'>"
        "<span style='font-size:12px;color:#999;'>" + project + " &middot; automated by Claude</span></td></tr>"
        "<tr><td style='padding:28px 28px 0;'>"
        "<h1 style='margin:0 0 6px;font-size:20px;font-weight:500;color:#1a1a18;'>"
        + project + " &mdash; commit " + commit_num + "</h1>"
        "<p style='margin:0 0 20px;font-size:13px;color:#888;'>" + agent_name + " &nbsp;&middot;&nbsp; " + now + "</p>"
        "<div style='margin-bottom:20px;'>"
        "<span style='background:#EAF3DE;color:#3B6D11;font-size:12px;font-weight:500;"
        "padding:4px 12px;border-radius:6px;'>awaiting your approval</span></div>"
        "<p style='margin:0 0 20px;font-size:15px;font-weight:500;color:#1a1a18;'>" + commit_name + "</p>"
        + what_why_html +
        "<div style='background:#f9f8f4;border-radius:8px;padding:14px 16px;margin-bottom:20px;'>"
        "<p style='margin:0 0 10px;font-size:11px;font-weight:600;color:#999;"
        "text-transform:uppercase;letter-spacing:0.05em;'>Files changed</p>"
        + stat_line
        + "<table cellpadding='0' cellspacing='0' style='width:100%;'>" + file_rows + "</table></div>"
        "<p style='font-size:13px;color:#888;line-height:1.65;margin:0 0 28px;"
        "border-left:2px solid #d3d1c7;padding-left:12px;'>"
        "Open your Cowork session to approve or reject.<br>"
        "Claude is waiting for your explicit go&#8209;ahead.</p>"
        "</td></tr>"
        "<tr><td style='background:#f9f8f4;border-top:1px solid #e0dfd8;"
        "padding:12px 28px;font-size:11px;color:#bbb;'>"
        "manifesto &middot; automated notification &middot; do not reply</td></tr>"
        "</table></td></tr></table></body></html>"
    )

    what_why_plain = ("What: " + what + "\n" if what else "") + ("Why:  " + why + "\n" if why else "")
    plain = (
        subject + "\n\n"
        "Agent: " + agent_name + "\n"
        "Commit: " + commit_num + " — " + commit_name + "\n"
        "Time: " + now + "\n\n"
        + (what_why_plain + "\n" if what_why_plain else "")
        + "Files changed:\n"
        + "\n".join("  [" + f["status"][0] + "] " + f["path"] for f in files)
        + "\n\n" + diff_stat + "\n\n"
        "Open your Cowork session to approve or reject.\n"
        "Claude is waiting for your explicit go-ahead.\n"
    )

    return subject, plain, html


# ── Send ───────────────────────────────────────────────────────────────────────────────────

def send_email(env: dict, subject: str, plain: str, html: str) -> None:
    host      = env["SMTP_HOST"]
    port      = int(env["SMTP_PORT"])
    user      = env["SMTP_USER"]
    password  = env["SMTP_PASSWORD"]
    recipient = env.get("NOTIFY_EMAIL") or user

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = "Claude Agents <" + user + ">"
    msg["To"]      = recipient

    msg.attach(MIMEText(plain, "plain", "utf-8"))
    msg.attach(MIMEText(html,  "html",  "utf-8"))

    with smtplib.SMTP(host, port) as server:
        server.ehlo()
        server.starttls()
        server.login(user, password)
        server.sendmail(user, [recipient], msg.as_string())

    print("[notify] Email sent to " + recipient + " \u2014 " + subject)


# ── Flag-file writer (for Stop-hook pattern) ───────────────────────────────

def write_pending_notify(what: str, why: str, num: str = "", name: str = "", agent: str = "") -> None:
    """Write a flag file that the Stop hook picks up to send the email on Windows.
    Captures staged file list NOW (before git commit clears the index).
    num/name/agent are auto-detected from commit-protocol.md if not provided."""
    import json as _json
    # Auto-detect from protocol — don't trust Claude to pass these correctly
    auto_num, auto_name, auto_agent = get_next_commit_from_protocol()
    num   = num   or auto_num
    name  = name  or auto_name
    agent = agent or auto_agent
    flag = ROOT / "hooks" / ".pending_notify.json"
    # Snapshot staged files while index is still populated
    files = get_diff_files()   # PRE_COMMIT is True at this point
    diff_stat = get_diff_stat()

    # ── DIAGNOSTIC (temporary) ────────────────────────────────────────────
    # Logs both candidate file lists side-by-side so we can see exactly
    # where get_files_from_commit_spec() and the real staged diff diverge.
    # Safe to remove once the root cause of the "files changed" mismatch
    # is confirmed and fixed.
    try:
        spec_files = get_files_from_commit_spec()
        staged_result = subprocess.run(
            ["git", "diff", "--cached", "--name-status"],
            capture_output=True, text=True, cwd=ROOT
        )
        staged_raw = [
            line for line in staged_result.stdout.strip().splitlines() if line.strip()
        ]
        proto_num, proto_name, proto_agent = get_next_commit_from_protocol()
        debug_log = ROOT / "hooks" / ".notify_debug.log"
        debug_entry = (
            "=== notify diagnostic @ " + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " ===\n"
            "protocol next-pending: #" + proto_num + " — " + proto_name + " (" + proto_agent + ")\n"
            "spec_files (get_files_from_commit_spec):\n"
            + ("\n".join("  [" + f["status"] + "] " + f["path"] for f in spec_files) or "  (empty)") + "\n"
            "staged_diff (git diff --cached --name-status):\n"
            + ("\n".join("  " + l for l in staged_raw) or "  (empty)") + "\n"
            "chosen_for_email (get_diff_files result):\n"
            + ("\n".join("  [" + f["status"] + "] " + f["path"] for f in files) or "  (empty)") + "\n"
            "\n"
        )
        with open(debug_log, "a", encoding="utf-8") as fh:
            fh.write(debug_entry)
        print("[notify][diag] wrote comparison to hooks/.notify_debug.log")
    except Exception as e:
        print("[notify][diag] failed: " + str(e), file=sys.stderr)
    # ── END DIAGNOSTIC ────────────────────────────────────────────────────

    flag.write_text(_json.dumps({
        "NOTIFY_NUM":   num,
        "NOTIFY_NAME":  name,
        "NOTIFY_AGENT": agent,
        "NOTIFY_WHAT":  what,
        "NOTIFY_WHY":   why,
        "files":        files,
        "diff_stat":    diff_stat,
    }, ensure_ascii=False), encoding="utf-8")
    print("[notify] Pending notify flag written (" + num + " — " + name + ") — Stop hook will send email.")


# ── Main ──────────────────────────────────────────────────────────────────────────────

def main() -> int:
    env = load_env()

    if not smtp_configured(env):
        print("[notify] SMTP not configured \u2014 skipping.")
        return 0

    # --write-flag: Claude writes flag file from sandbox; Stop hook on Windows sends the email
    if "--write-flag" in sys.argv:
        write_pending_notify(
            what  = os.environ.get("NOTIFY_WHAT", ""),
            why   = os.environ.get("NOTIFY_WHY", ""),
            # num/name/agent are auto-detected from commit-protocol.md
            num   = os.environ.get("NOTIFY_NUM", ""),
            name  = os.environ.get("NOTIFY_NAME", ""),
            agent = os.environ.get("NOTIFY_AGENT", ""),
        )
        return 0

    info      = get_commit_info()
    files     = get_diff_files()
    diff_stat = get_diff_stat()
    subject, plain, html = build_email(env, info, files, diff_stat)

    try:
        send_email(env, subject, plain, html)
    except Exception as e:
        print("[notify] Failed: " + str(e), file=sys.stderr)
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
