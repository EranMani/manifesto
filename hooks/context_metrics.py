#!/usr/bin/env python3
"""Build and persist compact Phase B context-efficiency records."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
METRICS_PATH = REPO_ROOT / "CONTEXT_METRICS.json"
INVOCATIONS_DIRNAME = Path(".context") / "telemetry" / "invocations"
ROLE_DOMAIN_LABELS = {
    "orchestrator": "Orchestration",
    "backend": "Backend",
    "devops": "DevOps",
    "frontend": "Frontend",
    "ai-engineer": "AI/ML",
}


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _commit_key(commit: str) -> str:
    return commit if str(commit).upper().startswith("C") else f"C{str(commit).zfill(2)}"


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


def _planned_files(commit: str, repo_root: Path = REPO_ROOT) -> list[str]:
    key = _commit_key(commit)
    match = re.fullmatch(r"C(\d+)([A-Z]?)", key.upper())
    if not match:
        return []
    number, suffix = match.groups()
    path = repo_root / "commit-specs" / f"commit-{int(number):02d}{suffix.lower()}.md"
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    section = re.search(
        r"^## Files To Modify Or Add\s*$\n(.*?)(?=^## |\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    if not section:
        return []
    files: list[str] = []
    for line in section.group(1).splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 2:
            continue
        candidate = cells[0].strip("`").strip().replace("\\", "/")
        action = cells[1].lower()
        if candidate.lower() == "file" or set(candidate) <= {"-"}:
            continue
        if action in {"new", "add", "edit", "delete", "remove"}:
            files.append(candidate)
    return files


def _unique_paths(*groups: Any) -> list[str]:
    result: list[str] = []
    for group in groups:
        if not isinstance(group, list):
            continue
        for value in group:
            if isinstance(value, str):
                normalized = value.replace("\\", "/")
                if normalized not in result:
                    result.append(normalized)
    return result


def _owner_domain(owner: str, repo_root: Path = REPO_ROOT) -> str:
    config = _load_json(repo_root / "hooks" / "agent-config.json") or {}
    for agent in config.get("agents", {}).values():
        if str(agent.get("name", "")).lower() == owner.lower():
            role = str(agent.get("role", "")).lower()
            return ROLE_DOMAIN_LABELS.get(role, role.replace("-", " ").title())
    return "Unknown"


def _execution_evidence(
    planned_files: list[str],
    read_files: list[str],
    changed_files: list[str],
    execution: str,
    preselected_files: list[str] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    planned = set(planned_files)
    read = set(read_files)
    changed = set(changed_files)
    preselected = set(preselected_files or [])
    planned_read = sorted(planned & read)
    supporting_reads = sorted((read & preselected) - planned)
    expansion_reads = sorted(read - preselected) if preselected else sorted(read - planned)
    planned_changed = sorted(planned & changed)
    supporting_changes = sorted(changed - planned)
    read_percent = round(len(planned_read) / len(planned) * 100, 1) if planned else None
    change_percent = (
        round(len(planned_changed) / len(planned) * 100, 1) if planned else None
    )
    scope = {
        "kind": "execution-scope" if execution == "claude-direct" else "delegation-package",
        "planned_files": len(planned_files),
        "planned_files_read": len(planned_read),
        "planned_read_percent": read_percent,
        "supporting_reads": supporting_reads,
        "expansion_reads": expansion_reads,
        "preselected_files": sorted(preselected),
        "source": "spec-and-hook-derived",
    }
    coverage = {
        "planned_files": len(planned_files),
        "planned_files_changed": len(planned_changed),
        "planned_change_percent": change_percent,
        "missing_planned_files": sorted(planned - changed),
        "supporting_changes": supporting_changes,
        "source": "spec-and-git-derived",
    }
    return scope, coverage


def canonicalize_metric_record(
    record: dict[str, Any], repo_root: Path = REPO_ROOT
) -> dict[str, Any]:
    """Add deterministic v2 identity, evidence, and capture fields to a record."""
    commit = str(record.get("commit", ""))
    owner = str(record.get("agent", "")).lower()
    execution = record.get("execution") or "unknown"
    executor = "claude" if execution == "claude-direct" else owner
    telemetry = record.get("telemetry", {})
    agent_scope = telemetry.get("agent", {})
    orch_scope = telemetry.get("orchestrator", {})
    read_files = _unique_paths(
        agent_scope.get("read_paths"), orch_scope.get("read_paths")
    )
    written_files = _unique_paths(
        agent_scope.get("write_paths"), orch_scope.get("write_paths")
    )
    changed_files = sorted(
        path.replace("\\", "/")
        for path in record.get("boundaries", {}).get("changed_files", [])
        if isinstance(path, str)
    )
    raw_scope = _load_json(
        repo_root / ".context" / "telemetry" / f"{_commit_key(commit)}-orchestrator.json"
    )
    if not raw_scope or raw_scope.get("status") != "completed":
        capture_status = "incomplete"
        capture_reason = "no completed Claude telemetry scope"
    elif (
        execution == "claude-direct"
        and raw_scope.get("scope_kind") == "execution"
        and raw_scope.get("capture_window") == "full-execution"
        and raw_scope.get("execution_mode") == "claude-direct"
    ):
        capture_status = "complete"
        capture_reason = None
    elif (
        execution == "delegated"
        and raw_scope.get("scope_kind") == "review"
        and raw_scope.get("execution_mode") == "delegated"
    ):
        capture_status = "complete"
        capture_reason = None
    else:
        capture_status = "legacy-partial"
        capture_reason = "completed scope predates explicit capture metadata"

    updated = dict(record)
    token_usage = (raw_scope or {}).get("token_usage", {})
    if execution == "claude-direct" and token_usage.get("status") == "complete":
        updated["tokens"] = token_usage.get("total_tokens")
    updated["record_schema_version"] = 2
    updated["identity"] = {
        "owner": owner,
        "executor": executor,
        "execution_mode": execution,
        "domain": _owner_domain(owner, repo_root),
        "source": "spec-and-runtime",
    }
    planned_files = _planned_files(commit, repo_root)
    preselected_files = (
        (raw_scope or {}).get("context_package", {}).get("selected_paths", [])
    )
    scope, coverage = _execution_evidence(
        planned_files, read_files, changed_files, execution, preselected_files
    )
    updated["evidence"] = {
        "planned_files": planned_files,
        "read_files": read_files if read_files else None,
        "written_files": written_files if written_files else None,
        "changed_files": changed_files,
        "coverage": coverage,
        "provenance": {
            "planned_files": "spec-derived" if planned_files else "not-captured",
            "read_files": "hook-measured" if read_files else "not-captured",
            "written_files": "hook-measured" if written_files else "not-captured",
            "changed_files": "git-derived",
        },
    }
    updated["scope"] = scope
    updated["capture"] = {
        "status": capture_status,
        "reason": capture_reason,
        "scope_kind": (raw_scope or {}).get("scope_kind"),
        "capture_window": (raw_scope or {}).get("capture_window"),
        "started_at": (raw_scope or {}).get("started_at"),
        "ended_at": (raw_scope or {}).get("ended_at"),
        "zero_is_measured": capture_status == "complete",
    }
    return updated


def migrate_metrics(
    path: Path = METRICS_PATH, repo_root: Path = REPO_ROOT
) -> dict[str, Any]:
    """Persist canonical fields for every legacy metric record."""
    payload = load_metrics(path)
    payload["records"] = [
        canonicalize_metric_record(record, repo_root)
        for record in payload.get("records", [])
    ]
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


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
            "schema_version": orch_telemetry.get("schema_version", 1),
            "owner": orch_telemetry.get("owner"),
            "executor": orch_telemetry.get("executor", "claude"),
            "execution_mode": orch_telemetry.get("execution_mode"),
            "scope_kind": orch_telemetry.get("scope_kind"),
            "capture_window": orch_telemetry.get("capture_window"),
            "started_at": orch_telemetry.get("started_at"),
            "ended_at": orch_telemetry.get("ended_at"),
            "tool_calls": orch_telemetry.get("tool_calls"),
            "read_paths": orch_telemetry.get("read_paths"),
            "write_paths": orch_telemetry.get("write_paths"),
            "searches": orch_telemetry.get("searches"),
            "commands": orch_telemetry.get("commands"),
            "token_usage": orch_telemetry.get("token_usage"),
            "context_package": orch_telemetry.get("context_package"),
            "selected_read_paths": orch_telemetry.get("selected_read_paths"),
            "outside_read_paths": orch_telemetry.get("outside_read_paths"),
        }
    return {
        "source": "hooks",
        "status": "unavailable",
        "schema_version": None,
        "owner": None,
        "executor": "claude",
        "execution_mode": None,
        "scope_kind": None,
        "capture_window": None,
        "started_at": None,
        "ended_at": None,
        "tool_calls": None,
        "read_paths": None,
        "write_paths": None,
        "searches": None,
        "commands": None,
        "token_usage": None,
        "context_package": None,
        "selected_read_paths": None,
        "outside_read_paths": None,
    }


def build_metric_record(
    commit: str,
    agent: str,
    tokens: int | None,
    results: dict[str, Any],
    changed_files: list[str],
    execution: str = "unknown",
) -> dict[str, Any]:
    commit_key = f"C{str(commit).zfill(2)}"
    self_report = load_agent_self_report(commit, agent)
    hooks_telemetry = load_run_telemetry(commit, agent)
    orch_telemetry = load_orchestrator_telemetry(commit)
    package = load_live_package(commit, agent)
    captured_tokens = (orch_telemetry or {}).get("token_usage", {})
    if (
        execution == "claude-direct"
        and captured_tokens.get("status") == "complete"
    ):
        tokens = captured_tokens.get("total_tokens")

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
    owner = agent.lower()
    executor = "claude" if execution == "claude-direct" else owner
    planned_files = _planned_files(commit, REPO_ROOT)
    read_files = _unique_paths(
        agent_scope.get("read_paths"), orch_scope.get("read_paths")
    )
    written_files = _unique_paths(
        agent_scope.get("write_paths"), orch_scope.get("write_paths")
    )
    changed_files = sorted(path.replace("\\", "/") for path in changed_files)
    preselected_files = (
        orch_scope.get("context_package", {}).get("selected_paths", [])
        if isinstance(orch_scope.get("context_package"), dict)
        else []
    )
    scope, coverage = _execution_evidence(
        planned_files, read_files, changed_files, execution, preselected_files
    )

    if orch_scope.get("status") == "unavailable":
        capture_status = "incomplete"
        capture_reason = "no completed Claude telemetry scope"
    elif (
        execution == "claude-direct"
        and orch_scope.get("scope_kind") == "execution"
        and orch_scope.get("capture_window") == "full-execution"
        and orch_scope.get("execution_mode") == "claude-direct"
    ):
        capture_status = "complete"
        capture_reason = None
    elif execution == "delegated" and orch_scope.get("status") == "available":
        capture_status = "complete" if orch_scope.get("scope_kind") == "review" else "legacy-partial"
        capture_reason = None if capture_status == "complete" else "legacy scope lacks explicit review metadata"
    else:
        capture_status = "legacy-partial"
        capture_reason = "completed scope predates full-execution metadata"

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

    package_record: dict[str, Any] = {}
    if package_data:
        package_record = {
            **package_data,
            "budget_utilization_percent": round(
                estimated_chars / usable_chars * 100, 1
            ) if usable_chars else None,
        }

    return {
        "record_schema_version": 2,
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "commit": commit_key,
        "agent": agent.lower(),
        "execution": execution,
        "identity": {
            "owner": owner,
            "executor": executor,
            "execution_mode": execution,
            "domain": _owner_domain(owner, REPO_ROOT),
            "source": "spec-and-runtime",
        },
        "evidence": {
            "planned_files": planned_files,
            "read_files": read_files if read_files else None,
            "written_files": written_files if written_files else None,
            "changed_files": changed_files,
            "coverage": coverage,
            "provenance": {
                "planned_files": "spec-derived" if planned_files else "not-captured",
                "read_files": "hook-measured" if read_files else "not-captured",
                "written_files": "hook-measured" if written_files else "not-captured",
                "changed_files": "git-derived",
            },
        },
        "scope": scope,
        "capture": {
            "status": capture_status,
            "reason": capture_reason,
            "scope_kind": orch_scope.get("scope_kind"),
            "capture_window": orch_scope.get("capture_window"),
            "started_at": orch_scope.get("started_at"),
            "ended_at": orch_scope.get("ended_at"),
            "zero_is_measured": capture_status == "complete",
        },
        "tokens": tokens,
        "package": package_record,
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
            "changed_files": changed_files,
        },
        "result": "PASS" if all(item["pass"] for item in results.values()) else "FAIL",
    }


def load_invocation_records(
    commit: str, agent: str, repo_root: Path = REPO_ROOT
) -> list[dict[str, Any]]:
    """Load every immutable C30 invocation record for a commit/agent, oldest first."""
    inv_dir = repo_root / INVOCATIONS_DIRNAME
    if not inv_dir.is_dir():
        return []
    commit_key = _commit_key(commit)
    prefix = f"{commit_key}-{agent.lower()}-"
    records = []
    for path in sorted(inv_dir.glob(f"{prefix}*.json")):
        record = _load_json(path)
        if record is not None:
            records.append(record)
    return records


def reconcile_invocation_records(
    commit: str, agent: str, repo_root: Path = REPO_ROOT
) -> dict[str, Any]:
    """Aggregate immutable invocation records for a commit/agent.

    Pairs each kind's self-report records with its hooks records in
    recording order to reconstruct one entry per invocation, then sums
    tool_calls across invocations. Any disagreement between a self-report
    and its paired hooks record is reported as a contradiction rather than
    silently picking one source; any invocation missing tool_calls from
    both sources is reported as unknown rather than counted as zero.
    """
    records = load_invocation_records(commit, agent, repo_root)
    by_kind: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for record in records:
        kind = record.get("kind", "normal")
        record_type = record.get("record_type", "unknown")
        by_kind.setdefault(kind, {}).setdefault(record_type, []).append(record)

    invocations: list[dict[str, Any]] = []
    contradictions: list[dict[str, Any]] = []
    unknown: list[dict[str, Any]] = []
    total_tool_calls = 0

    for kind in sorted(by_kind):
        self_reports = by_kind[kind].get("self-report", [])
        hooks = by_kind[kind].get("hooks", [])
        for index in range(max(len(self_reports), len(hooks))):
            self_report = self_reports[index] if index < len(self_reports) else None
            hook = hooks[index] if index < len(hooks) else None
            self_calls = self_report.get("tool_calls") if self_report else None
            hook_calls = hook.get("tools", {}).get("total") if hook else None

            entry: dict[str, Any] = {
                "kind": kind,
                "index": index + 1,
                "self_report_tool_calls": self_calls,
                "hooks_tool_calls": hook_calls,
            }

            if self_calls is not None and hook_calls is not None:
                if self_calls == hook_calls:
                    entry["tool_calls"] = self_calls
                    entry["status"] = "reconciled"
                    total_tool_calls += self_calls
                else:
                    entry["tool_calls"] = None
                    entry["status"] = "contradiction"
                    contradictions.append(dict(entry))
            elif self_calls is not None:
                entry["tool_calls"] = self_calls
                entry["status"] = "self_report_only"
                total_tool_calls += self_calls
            elif hook_calls is not None:
                entry["tool_calls"] = hook_calls
                entry["status"] = "hooks_only"
                total_tool_calls += hook_calls
            else:
                entry["tool_calls"] = None
                entry["status"] = "unknown"
                unknown.append(dict(entry))

            invocations.append(entry)

    return {
        "commit": _commit_key(commit),
        "agent": agent.lower(),
        "invocation_count": len(invocations),
        "invocations": invocations,
        "total_tool_calls": total_tool_calls,
        "total_tool_calls_complete": not contradictions and not unknown,
        "contradictions": contradictions,
        "unknown": unknown,
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
