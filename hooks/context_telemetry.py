#!/usr/bin/env python3
"""Capture Phase B context-usage telemetry from Claude Code tool hooks."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
ACTIVE_PATH = REPO_ROOT / ".context" / "telemetry" / "active.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def normalize_path(value: str) -> str:
    value = value.strip().replace("\\", "/")
    root = REPO_ROOT.as_posix().rstrip("/")
    if value.lower().startswith(root.lower() + "/"):
        value = value[len(root) + 1:]
    while value.startswith("./"):
        value = value[2:]
    return value


def initialize_telemetry(
    package: dict[str, Any],
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    selected = [item["path"] for item in package.get("files", [])]
    telemetry = {
        "schema_version": 1,
        "commit": package["commit"],
        "agent": package["agent"],
        "status": "prepared",
        "started_at": utc_now(),
        "ended_at": None,
        "selected_paths": selected,
        "forbidden_paths": package.get("forbidden_edits", []),
        "package": {
            "selected_files": package["budget"]["selected_files"],
            "estimated_chars": package["budget"]["estimated_selected_chars"],
            "usable_chars": package["budget"]["usable_chars_before_reserve"],
            "targeted_excerpt_files": sum(
                item.get("read_strategy", "").startswith("targeted excerpt")
                for item in package.get("files", [])
            ),
            "excluded_candidates": len(package.get("excluded_candidates", [])),
            "expansion_triggers": list(package.get("expansion_triggers", [])),
            "graph_source": package.get("graph", {}).get("source", "unknown"),
            "category_counts": {},
        },
        "tools": {
            "total": 0,
            "reads": 0,
            "searches": 0,
            "writes": 0,
            "tests_or_commands": 0,
        },
        "selected_read_paths": [],
        "outside_read_paths": [],
        "search_events": [],
        "write_paths": [],
    }
    for item in package.get("files", []):
        category = item.get("category", "unknown")
        telemetry["package"]["category_counts"][category] = (
            telemetry["package"]["category_counts"].get(category, 0) + 1
        )
    active_path = repo_root / ".context" / "telemetry" / "active.json"
    active_path.parent.mkdir(parents=True, exist_ok=True)
    active_path.write_text(json.dumps(telemetry, indent=2) + "\n", encoding="utf-8")
    return telemetry


def _load_active() -> dict[str, Any] | None:
    try:
        return json.loads(ACTIVE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _active_agent() -> str:
    cap_path = REPO_ROOT / "hooks" / "tool_cap.json"
    try:
        cap = json.loads(cap_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    if not cap.get("active"):
        return ""
    return str(cap.get("agent") or "").lower()


def _tool_path(tool_input: dict[str, Any]) -> str:
    for key in ("file_path", "path", "notebook_path"):
        value = tool_input.get(key)
        if isinstance(value, str) and value.strip():
            return normalize_path(value)
    return ""


def _append_unique(items: list[Any], value: Any) -> None:
    if value not in items:
        items.append(value)


def record_tool_event(event: dict[str, Any]) -> dict[str, Any] | None:
    telemetry = _load_active()
    if not telemetry or telemetry.get("status") not in {"prepared", "running"}:
        return telemetry

    tool_name = str(event.get("tool_name", ""))
    if tool_name == "Agent":
        return telemetry
    active_agent = _active_agent()
    if not active_agent or active_agent != str(telemetry.get("agent", "")).lower():
        return telemetry
    tool_input = event.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        tool_input = {}
    telemetry["status"] = "running"
    telemetry["tools"]["total"] += 1
    path = _tool_path(tool_input)
    selected = set(telemetry.get("selected_paths", []))

    if tool_name == "Read":
        telemetry["tools"]["reads"] += 1
        if path in selected:
            _append_unique(telemetry["selected_read_paths"], path)
        elif path:
            _append_unique(telemetry["outside_read_paths"], path)
    elif tool_name in {"Grep", "Glob"}:
        telemetry["tools"]["searches"] += 1
        search = {
            "tool": tool_name,
            "path": path or ".",
            "query": str(tool_input.get("pattern", "")),
        }
        telemetry["search_events"].append(search)
        if path in selected:
            _append_unique(telemetry["selected_read_paths"], path)
        elif path:
            _append_unique(telemetry["outside_read_paths"], path)
    elif tool_name in {"Write", "Edit", "MultiEdit", "NotebookEdit"}:
        telemetry["tools"]["writes"] += 1
        if path:
            _append_unique(telemetry["write_paths"], path)
    elif tool_name == "Bash":
        telemetry["tools"]["tests_or_commands"] += 1

    ACTIVE_PATH.write_text(json.dumps(telemetry, indent=2) + "\n", encoding="utf-8")
    return telemetry


def finalize_telemetry() -> dict[str, Any] | None:
    telemetry = _load_active()
    if not telemetry:
        return None
    telemetry["status"] = "completed"
    telemetry["ended_at"] = utc_now()
    ACTIVE_PATH.write_text(json.dumps(telemetry, indent=2) + "\n", encoding="utf-8")
    output = (
        REPO_ROOT
        / ".context"
        / "telemetry"
        / f"{telemetry['commit']}-{telemetry['agent']}.json"
    )
    output.write_text(json.dumps(telemetry, indent=2) + "\n", encoding="utf-8")
    return telemetry


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--finalize", action="store_true")
    args = parser.parse_args()
    if args.finalize:
        finalize_telemetry()
        return 0
    try:
        raw = sys.stdin.read()
        event = json.loads(raw) if raw.strip() else {}
        record_tool_event(event)
    except Exception:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
