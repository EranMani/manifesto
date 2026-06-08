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


def build_metric_record(
    commit: str,
    agent: str,
    tokens: int | None,
    results: dict[str, Any],
    changed_files: list[str],
) -> dict[str, Any]:
    commit_key = f"C{str(commit).zfill(2)}"
    telemetry = load_run_telemetry(commit, agent)
    package = load_live_package(commit, agent)
    package_data = (telemetry or {}).get("package", {})
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

    selected_files = int(package_data.get("selected_files", 0))
    selected_reads = len((telemetry or {}).get("selected_read_paths", []))
    outside_reads = len((telemetry or {}).get("outside_read_paths", []))
    searches = int((telemetry or {}).get("tools", {}).get("searches", 0))
    estimated_chars = int(package_data.get("estimated_chars", 0))
    usable_chars = int(package_data.get("usable_chars", 0))
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
        "usage": {
            "telemetry_status": (telemetry or {}).get("status", "unavailable"),
            "tool_calls": int((telemetry or {}).get("tools", {}).get("total", 0)),
            "read_calls": int((telemetry or {}).get("tools", {}).get("reads", 0)),
            "searches": searches,
            "write_calls": int((telemetry or {}).get("tools", {}).get("writes", 0)),
            "selected_files_read": selected_reads,
            "selected_utilization_percent": round(
                selected_reads / selected_files * 100, 1
            ) if selected_files else None,
            "unused_selected_files": max(selected_files - selected_reads, 0),
            "outside_files_read": outside_reads,
            "expansions": outside_reads,
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
