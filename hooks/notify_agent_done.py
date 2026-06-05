#!/usr/bin/env python3
"""
notify_agent_done.py — Email notification after an agent finishes work.

Fires from the Stop hook in .claude/settings.json.
Reads project-state.json + git diff to build a summary email,
then sends it via SMTP before Claude surfaces the approval prompt.

Required env vars (in .env):
  SMTP_HOST      e.g. smtp.gmail.com
  SMTP_PORT      e.g. 587
  SMTP_USER      sending address
  SMTP_PASSWORD  app password or SMTP credential
  NOTIFY_EMAIL   recipient address (defaults to SMTP_USER if unset)

Optional:
  NOTIFY_AGENT   agent name override (auto-detected from project-state.json)
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
    """Load .env file from repo root into a dict (does not overwrite os.environ)."""
    env = {}
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            env[key.strip()] = val.strip().strip('"').strip("'")
    # os.environ takes precedence
    for key in ["SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD",
                "NOTIFY_EMAIL", "NOTIFY_AGENT"]:
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
        except json.JSONDecodeError:
            pass
    return {}


def get_project_name(state: dict) -> str:
    return state.get("project", ROOT.name)


def get_current_commit(state: dict) -> dict:
    return state.get("current_commit", {})


# ── Git diff ──────────────────────────────────────────────────────────────────

def get_staged_diff_stat() -> list[dict]:
    """
    Returns list of {status, path} for staged files.
    Falls back to unstaged working-tree changes if nothing is staged.
    """
    result = subprocess.run(
        ["git", "diff", "--name-status", "--cached"],
        capture_output=True, text=True, cwd=ROOT
    )
    lines = result.stdout.strip().splitlines()

    if not lines:
        # Nothing staged — show working tree changes instead
        result = subprocess.run(
            ["git", "diff", "--name-status"],
            capture_output=True, text=True, cwd=ROOT
        )
        lines = result.stdout.strip().splitlines()

    if not lines:
        # Last resort: files changed since last commit
        result = subprocess.run(
            ["git", "diff", "HEAD", "--name-status"],
            capture_output=True, text=True, cwd=ROOT
        )
        lines = result.stdout.strip().splitlines()

    files = []
    status_map = {"A": "Added", "M": "Modified", "D": "Deleted", "R": "Renamed"}
    for line in lines:
        parts = line.split("\t")
        if len(parts) >= 2:
            code = parts[0][0]  # first char handles R100 etc.
            path = parts[-1]
            files.append({"status": status_map.get(code, code), "path": path})
    return files


def get_diff_stat_summary() -> str:
    """Returns insertions/deletions summary line."""
    result = subprocess.run(
        ["git", "diff", "--cached", "--stat"],
        capture_output=True, text=True, cwd=ROOT
    )
    if result.stdout.strip():
        lines = result.stdout.strip().splitlines()
        return lines[-1].strip()  # last line is the summary
    return ""


# ── Email builder ─────────────────────────────────────────────────────────────

STATUS_COLORS = {
    "Added":    ("#1D9E75", "A"),
    "Modified": ("#BA7517", "M"),
    "Deleted":  ("#A32D2D", "D"),
    "Renamed":  ("#185FA5", "R"),
}

def build_file_rows(files: list[dict]) -> str:
    if not files:
        return "<tr><td colspan='2' style='color:#888;padding:6px 0;'>No file changes detected.</td></tr>"
    rows = []
    for f in files:
        color, letter = STATUS_COLORS.get(f["status"], ("#888", "?"))
        rows.append(
            f"<tr>"
            f"<td style='padding:4px 8px 4px 0;font-family:monospace;font-size:12px;"
            f"color:{color};font-weight:600;white-space:nowrap;'>{letter}</td>"
            f"<td style='padding:4px 0;font-family:monospace;font-size:12px;"
            f"color:#333;word-break:break-all;'>{f['path']}</td>"
            f"</tr>"
        )
    return "\n".join(rows)


def build_email(env: dict, state: dict, files: list[dict], diff_stat: str) -> tuple[str, str, str]:
    """Returns (subject, plain_text, html_body)."""
    project = get_project_name(state)
    commit = get_current_commit(state)
    commit_num = commit.get("number", "??")
    commit_name = commit.get("name", "unknown")
    agent_name = env.get("NOTIFY_AGENT") or commit.get("assignee", "agent").title()
    now = datetime.now().strftime("%a %d %b %Y, %H:%M")

    subject = f"{project} — commit {commit_num} — {agent_name} finished"

    file_rows = build_file_rows(files)
    stat_line = f"<p style='margin:0 0 16px;font-size:12px;color:#888;'>{diff_stat}</p>" if diff_stat else ""

    html = f"""
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f4f4f0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f4f0;padding:32px 16px;">
    <tr><td align="center">
      <table width="560" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:12px;border:1px solid #e0dfd8;overflow:hidden;max-width:560px;">

        <!-- header bar -->
        <tr><td style="background:#f9f8f4;border-bottom:1px solid #e0dfd8;padding:10px 20px;">
          <span style="font-size:12px;color:#999;">manifesto · automated by Claude</span>
        </td></tr>

        <!-- body -->
        <tr><td style="padding:28px 28px 0;">
          <h1 style="margin:0 0 6px;font-size:20px;font-weight:500;color:#1a1a18;">
            {project} &mdash; commit {commit_num}
          </h1>
          <p style="margin:0 0 20px;font-size:13px;color:#888;">{agent_name} &nbsp;·&nbsp; {now}</p>

          <!-- status badge -->
          <div style="margin-bottom:20px;">
            <span style="background:#EAF3DE;color:#3B6D11;font-size:12px;font-weight:500;
                         padding:4px 12px;border-radius:6px;">awaiting your approval</span>
          </div>

          <!-- commit name -->
          <p style="margin:0 0 20px;font-size:14px;color:#444;line-height:1.6;">
            <strong style="color:#1a1a18;">{commit_name}</strong> &mdash;
            review the full diff in your Cowork session before approving.
          </p>

          <!-- files changed -->
          <div style="background:#f9f8f4;border-radius:8px;padding:14px 16px;margin-bottom:20px;">
            <p style="margin:0 0 10px;font-size:11px;font-weight:600;color:#999;
                      text-transform:uppercase;letter-spacing:0.05em;">Files changed</p>
            {stat_line}
            <table cellpadding="0" cellspacing="0" style="width:100%;">
              {file_rows}
            </table>
          </div>

          <!-- divider note -->
          <p style="font-size:13px;color:#888;line-height:1.65;margin:0 0 28px;
                    border-left:2px solid #d3d1c7;padding-left:12px;">
            Open your Cowork session to approve or reject.<br>
            Claude is waiting for your explicit go&#8209;ahead.
          </p>
        </td></tr>

        <!-- footer -->
        <tr><td style="background:#f9f8f4;border-top:1px solid #e0dfd8;
                       padding:12px 28px;font-size:11px;color:#bbb;">
          manifesto · automated notification · do not reply
        </td></tr>

      </table>
    </td></tr>
  </table>
</body>
</html>
"""

    plain = (
        f"{subject}\n\n"
        f"Agent: {agent_name}\n"
        f"Commit: {commit_num} — {commit_name}\n"
        f"Time: {now}\n\n"
        f"Files changed:\n"
        + "\n".join(f"  [{f['status'][0]}] {f['path']}" for f in files)
        + f"\n\n{diff_stat}\n\n"
        f"Open your Cowork session to approve or reject the commit.\n"
        f"Claude is waiting for your explicit go-ahead.\n"
    )

    return subject, plain, html


# ── Send ──────────────────────────────────────────────────────────────────────

def send_email(env: dict, subject: str, plain: str, html: str) -> None:
    host = env["SMTP_HOST"]
    port = int(env["SMTP_PORT"])
    user = env["SMTP_USER"]
    password = env["SMTP_PASSWORD"]
    recipient = env.get("NOTIFY_EMAIL") or user

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"Claude Agents <{user}>"
    msg["To"] = recipient

    msg.attach(MIMEText(plain, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))

    with smtplib.SMTP(host, port) as server:
        server.ehlo()
        server.starttls()
        server.login(user, password)
        server.sendmail(user, [recipient], msg.as_string())

    print(f"[notify] Email sent to {recipient} — {subject}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    env = load_env()

    if not smtp_configured(env):
        print("[notify] SMTP not configured — skipping email. Set SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD in .env")
        return 0

    state = load_state()
    files = get_staged_diff_stat()
    diff_stat = get_diff_stat_summary()
    subject, plain, html = build_email(env, state, files, diff_stat)

    try:
        send_email(env, subject, plain, html)
    except Exception as e:
        print(f"[notify] Failed to send email: {e}", file=sys.stderr)
        # Non-fatal — do not block the commit loop
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
