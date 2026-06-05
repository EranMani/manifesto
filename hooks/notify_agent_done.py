#!/usr/bin/env python3
"""
notify_agent_done.py — Email notification before a commit is made.

Called directly by Claude as part of the commit command:
  python hooks/notify_agent_done.py && CLAUDE_COMMIT=1 git commit -m "..."

Reads staged diff + commit-protocol.md + project-state.json.
Does NOT read git log HEAD — the commit hasn't happened yet.

Required env vars (in .env):
  SMTP_HOST      e.g. smtp.gmail.com
  SMTP_PORT      e.g. 587
  SMTP_USER      sending address
  SMTP_PASSWORD  app password or SMTP credential
  NOTIFY_EMAIL   recipient address (defaults to SMTP_USER if unset)

Optional:
  NOTIFY_AGENT   agent name override
  NOTIFY_COMMIT  commit number override (e.g. "13")
  NOTIFY_WHAT    What: line override
  NOTIFY_WHY     Why: line override
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
    for key in ["SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD",
                "NOTIFY_EMAIL", "NOTIFY_AGENT", "NOTIFY_COMMIT", "NOTIFY_WHAT", "NOTIFY_WHY"]:
        if key in os.environ:
            env[key] = os.environ[key]
    return env


def smtp_configured(env: dict) -> bool:
    return all(env.get(k) for k in ["SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD"])


# ── Project state ─────────────────────────────────────────────────────────────

def load_state() -> dict:
    state_file = ROOT / "project-state.json"
    if state_file.exists():
        try:
            return json.loads(state_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def get_project_name(state: dict) -> str:
    return state.get("project", ROOT.name)


def get_commit_number_from_protocol() -> str | None:
    """Return the first pending commit number from commit-protocol.md."""
    protocol = ROOT / "commit-protocol.md"
    if not protocol.exists():
        return None
    for line in protocol.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.split("|") if c.strip()]
        if len(cells) < 4 or not cells[0].isdigit():
            continue
        if "pending" in cells[3].lower():
            return cells[0].zfill(2)
    return None


def get_commit_info(env: dict) -> dict:
    state = load_state()
    cc = state.get("current_commit", {})

    # Commit number: env override → protocol pending → state
    number = env.get("NOTIFY_COMMIT")
    if not number:
        number = get_commit_number_from_protocol()
    if not number and cc.get("number"):
        number = str(cc["number"]).zfill(2)

    # Agent: env override → state assignee
    agent = env.get("NOTIFY_AGENT") or cc.get("assignee", "Agent")
    if agent:
        agent = agent.title()

    # Commit name from state
    name = cc.get("name", "")

    # What/Why: env override (Claude passes these as env vars)
    what = env.get("NOTIFY_WHAT", "")
    why  = env.get("NOTIFY_WHY", "")

    return {
        "number":  number or "??",
        "name":    name,
        "agent":   agent,
        "project": get_project_name(state),
        "what":    what,
        "why":     why,
    }


# ── Staged diff ───────────────────────────────────────────────────────────────

def get_staged_files() -> list:
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-status"],
        capture_output=True, text=True, cwd=ROOT
    )
    files = []
    status_map = {"A": "Added", "M": "Modified", "D": "Deleted", "R": "Renamed"}
    for line in result.stdout.strip().splitlines():
        parts = line.split("\t")
        if len(parts) >= 2:
            code = parts[0][0]
            path = parts[-1]
            files.append({"status": status_map.get(code, code), "path": path})
    return files


def get_staged_stat() -> str:
    result = subprocess.run(
        ["git", "diff", "--cached", "--stat"],
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
        return "<tr><td colspan='2' style='color:#888;padding:6px 0;'>No staged changes detected.</td></tr>"
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
            "<tr>"
            "<td style='padding:4px 12px 4px 0;font-size:12px;font-weight:600;color:#999;"
            "white-space:nowrap;vertical-align:top;'>What</td>"
            "<td style='padding:4px 0;font-size:13px;color:#1a1a18;line-height:1.6;'>" + what + "</td>"
            "</tr>"
        )
    if why:
        rows += (
            "<tr>"
            "<td style='padding:4px 12px 4px 0;font-size:12px;font-weight:600;color:#999;"
            "white-space:nowrap;vertical-align:top;'>Why</td>"
            "<td style='padding:4px 0;font-size:13px;color:#444;line-height:1.6;'>" + why + "</td>"
            "</tr>"
        )
    return (
        "<div style='background:#f9f8f4;border-radius:8px;padding:14px 16px;margin-bottom:20px;'>"
        "<table cellpadding='0' cellspacing='0' style='width:100%;'>" + rows + "</table>"
        "</div>"
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
        "<span style='font-size:12px;color:#999;'>" + project + " &middot; automated by Claude</span>"
        "</td></tr>"

        "<tr><td style='padding:28px 28px 0;'>"
        "<h1 style='margin:0 0 6px;font-size:20px;font-weight:500;color:#1a1a18;'>"
        + project + " &mdash; commit " + commit_num +
        "</h1>"
        "<p style='margin:0 0 20px;font-size:13px;color:#888;'>"
        + agent_name + " &nbsp;&middot;&nbsp; " + now +
        "</p>"

        "<div style='margin-bottom:20px;'>"
        "<span style='background:#EAF3DE;color:#3B6D11;font-size:12px;font-weight:500;"
        "padding:4px 12px;border-radius:6px;'>awaiting your approval</span>"
        "</div>"

        "<p style='margin:0 0 20px;font-size:15px;font-weight:500;color:#1a1a18;'>"
        + commit_name +
        "</p>"

        + what_why_html +

        "<div style='background:#f9f8f4;border-radius:8px;padding:14px 16px;margin-bottom:20px;'>"
        "<p style='margin:0 0 10px;font-size:11px;font-weight:600;color:#999;"
        "text-transform:uppercase;letter-spacing:0.05em;'>Files changed</p>"
        + stat_line +
        "<table cellpadding='0' cellspacing='0' style='width:100%;'>"
        + file_rows +
        "</table></div>"

        "<p style='font-size:13px;color:#888;line-height:1.65;margin:0 0 28px;"
        "border-left:2px solid #d3d1c7;padding-left:12px;'>"
        "Open your Cowork session to approve or reject.<br>"
        "Claude is waiting for your explicit go&#8209;ahead."
        "</p>"
        "</td></tr>"

        "<tr><td style='background:#f9f8f4;border-top:1px solid #e0dfd8;"
        "padding:12px 28px;font-size:11px;color:#bbb;'>"
        "manifesto &middot; automated notification &middot; do not reply"
        "</td></tr>"

        "</table></td></tr></table></body></html>"
    )

    what_why_plain = ""
    if what:
        what_why_plain += "What: " + what + "\n"
    if why:
        what_why_plain += "Why:  " + why + "\n"

    plain = (
        subject + "\n\n"
        "Agent: " + agent_name + "\n"
        "Commit: " + commit_num + " — " + commit_name + "\n"
        "Time: " + now + "\n\n"
        + (what_why_plain + "\n" if what_why_plain else "")
        + "Files changed:\n"
        + "\n".join("  [" + f["status"][0] + "] " + f["path"] for f in files)
        + "\n\n" + diff_stat + "\n\n"
        "Open your Cowork session to approve or reject the commit.\n"
        "Claude is waiting for your explicit go-ahead.\n"
    )

    return subject, plain, html


# ── Send ──────────────────────────────────────────────────────────────────────

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

    print("[notify] Email sent to " + recipient + " — " + subject)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    env = load_env()

    if not smtp_configured(env):
        print("[notify] SMTP not configured — skipping. Set SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD in .env")
        return 0

    info      = get_commit_info(env)
    files     = get_staged_files()
    diff_stat = get_staged_stat()
    subject, plain, html = build_email(env, info, files, diff_stat)

    try:
        send_email(env, subject, plain, html)
    except Exception as e:
        print("[notify] Failed to send email: " + str(e), file=sys.stderr)
        return 0  # non-fatal

    return 0


if __name__ == "__main__":
    sys.exit(main())
