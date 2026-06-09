#!/usr/bin/env python3
"""Build and persist compact Phase B context-efficiency records."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
METRICS_PATH = REPO_ROOT / "CONTEXT_METRICS.json"


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def load_metrics(path: Path = METRICS_PATH) -> dict[str, Any]:
    payload = _load_json(path)
    if not payload or payload.get("schema_version") != 1:
        return {"schema_version": 1, "records": []}
    payload.setdefault("records", [])
    return payload


def load_run_telemetry(commit: str, agent: str) -> dict[str, Any] | None:
    path = REPO_ROOT / ".context" / "telemetry" / f"C{str(commit).zfill(2)}-{agent}.json"
    return _load_json(path)


def load_live_package(commit: str, agent: str) -> dict[str, Any] | None:
    path = REPO_ROOT / ".context" / "runs" / f"C{str(commit).zfill(2)}-{agent}-live.json"
    return _load_json(path)


def load_agent_self_report(commit: str, agent: str) -> dict[str, Any] | None:
    """Load the structured telemetry report the agent returned at end of its session."""
    commit_key = f"C{str(commit).zfill(2)}"
    path = REPO_ROOT / ".context" / "telemetry" / f"{commit_key}-{agent.lower()}-self-report.json"
    return _load_json(path)


def load_orchestrator_telemetry(commit: str) -> dict[str, Any] | None:
    """Load the orchestrator-scope telemetry captured during post-agent review."""
    commit_key = f"C{str(commit).zfill(2)}"
    path = REPO_ROOT / ".context" / "telemetry" / f"{commit_key}-orchestrator.json"
    return _load_json(path)


def _build_agent_scope(
    self_report: dict[str, Any] | None,
    hooks_telemetry: dict[str, Any] | None,
) -> dict[str, Any]:
    """Build agent telemetry scope. Self-report takes priority over hooks-captured data."""
    if self_report is not None:
        return {
            "source": "self_report",
            "status": self_report.get("status", "partial"),
            "tool_calls": self_report.get("tool_calls"),
            "read_paths": self_report.get("read_paths"),
            "write_paths": self_report.get("write_paths"),
            "searches": self_report.get("searches"),
            "commands": self_report.get("commands"),
            "expansions": self_report.get("expansions"),
        }
    if hooks_telemetry is not None and hooks_telemetry.get("status") == "completed":
        tools = hooks_telemetry.get("tools", {})
        selected_reads = hooks_telemetry.get("selected_read_paths", [])
        outside_reads = hooks_telemetry.get("outside_read_paths", [])
        return {
            "source": "hooks",
            "status": "available",
            "tool_calls": tools.get("total"),
            "read_paths": selected_reads + outside_reads,
            "write_paths": hooks_telemetry.get("write_paths", []),
            "searches": hooks_telemetry.get("search_events", []),
            "commands": [],
            "expansions": outside_reads,
        }
    return {
        "source": "unavailable",
        "status": "unavailable",
        "tool_calls": None,
        "read_paths": None,
        "write_paths": None,
        "searches": None,
        "commands": None,
        "expansions": None,
    }


def _build_orchestrator_scope(orch_telemetry: dict[str, Any] | None) -> dict[str, Any]:
    """Build orchestrator telemetry scope from hook-captured data."""
    if orch_telemetry is not None and orch_telemetry.get("status") == "completed":
        return {
            "source": "hooks",
            "status": "available",
            "tool_calls": orch_telemetry.get("tool_calls"),
            "read_paths": orch_telemetry.get("read_paths"),
            "write_paths": orch_telemetry.get("write_paths"),
            "searches": orch_telemetry.get("searches"),
            "commands": orch_telemetry.get("commands"),
        }
    return {
        "source": "hooks",
        "status": "unavailable",
        "tool_calls": None,
        "read_paths": None,
        "write_paths": None,
        "searches": None,
        "commands": None,
    }


def build_metric_record(
    commit: str,
    agent: str,
    tokens: int | None,
    results: dict[str, Any],
    changed_files: list[str],
) -> dict[str, Any]:
    commit_key = f"C{str(commit).zfill(2)}"
    self_report = load_agent_self_report(commit, agent)
    hooks_telemetry = load_run_telemetry(commit, agent)
    orch_telemetry = load_orchestrator_telemetry(commit)
    package = load_live_package(commit, agent)

    package_data = (hooks_telemetry or {}).get("package", {})
    if not package_data and package:
        package_data = {
            "selected_files": package["budget"]["selected_files"],
            "estimated_chars": package["budget"]["estimated_selected_chars"],
            "usable_chars": package["budget"]["usable_chars_before_reserve"],
            "targeted_excerpt_files": sum(
                item.get("read_strategy", "").startswith("targeted excerpt")
                for item in package.get("files", [])
            ),
            "excluded_candidates": len(package.get("excluded_candidates", [])),
            "expansion_triggers": package.get("expansion_triggers", []),
            "graph_source": package.get("graph", {}).get("source", "unknown"),
            "category_counts": {},
        }

    agent_scope = _build_agent_scope(self_report, hooks_telemetry)
    orch_scope = _build_orchestrator_scope(orch_telemetry)

    selected_files = int(package_data.get("selected_files", 0))
    estimated_chars = int(package_data.get("estimated_chars", 0))
    usable_chars = int(package_data.get("usable_chars", 0))

    # Derive selected-file utilization from hooks data (unavailable for self-report-only)
    selected_reads: int | None = None
    outside_reads: int | None = None
    hook_searches: int | None = None
    hook_expansions: int | None = None
    if hooks_telemetry and hooks_telemetry.get("status") == "completed":
        hook_selected_reads_list = hooks_telemetry.get("selected_read_paths", [])
        if not hook_selected_reads_list and self_report and self_report.get("read_paths"):
            # Hooks captured no reads (e.g. worktree invocation); cross-match self-report
            # read_paths against the package's selected_paths to derive utilization.
            selected_paths_set = set(hooks_telemetry.get("selected_paths", []))
            matched = [p for p in self_report["read_paths"] if p in selected_paths_set]
            selected_reads = len(matched)
            outside_reads = len(self_report["read_paths"]) - selected_reads
        else:
            selected_reads = len(hook_selected_reads_list)
            outside_reads = len(hooks_telemetry.get("outside_read_paths", []))
        hook_searches = int(hooks_telemetry.get("tools", {}).get("searches", 0))
        hook_expansions = outside_reads
    elif self_report:
        # Use agent self-report for expansion count when hooks are absent
        exp = self_report.get("expansions")
        if isinstance(exp, list):
            hook_expansions = len(exp)
        elif isinstance(exp, int):
            hook_expansions = exp
        srch = self_report.get("searches")
        if isinstance(srch, list):
            hook_searches = len(srch)

    return {
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "commit": commit_key,
        "agent": agent.lower(),
        "tokens": tokens,
        "package": {
            **package_data,
            "budget_utilization_percent": round(
                estimated_chars / usable_chars * 100, 1
            ) if usable_chars else None,
        },
        "telemetry": {
            "agent": agent_scope,
            "orchestrator": orch_scope,
        },
        # "usage" is kept for backward compatibility with dashboard selected-utilization rendering
        "usage": {
            "telemetry_status": (hooks_telemetry or {}).get("status", "unavailable"),
            "tool_calls": (hooks_telemetry or {}).get("tools", {}).get("total") if hooks_telemetry else None,
            "read_calls": (hooks_telemetry or {}).get("tools", {}).get("reads") if hooks_telemetry else None,
            "searches": hook_searches,
            "write_calls": (hooks_telemetry or {}).get("tools", {}).get("writes") if hooks_telemetry else None,
            "selected_files_read": selected_reads,
            "selected_utilization_percent": round(
                selected_reads / selected_files * 100, 1
            ) if selected_files and selected_reads is not None else None,
            "unused_selected_files": max(selected_files - (selected_reads or 0), 0) if selected_reads is not None else None,
            "outside_files_read": outside_reads,
            "expansions": hook_expansions,
        },
        "boundaries": {
            "forbidden_clean": bool(results["forbidden_paths"]["pass"]),
            "changed_files": sorted(changed_files),
        },
        "result": "PASS" if all(item["pass"] for item in results.values()) else "FAIL",
    }


def upsert_metric(record: dict[str, Any], path: Path = METRICS_PATH) -> None:
    payload = load_metrics(path)
    key = (record["commit"].lower(), record["agent"].lower())
    payload["records"] = [
        existing
        for existing in payload["records"]
        if (str(existing.get("commit", "")).lower(), str(existing.get("agent", "")).lower()) != key
    ]
    payload["records"].append(record)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
