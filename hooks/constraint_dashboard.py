#!/usr/bin/env python3
"""Render the constraint and Phase B context-efficiency dashboard."""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from context_metrics import load_metrics


REPO_ROOT = Path(__file__).resolve().parent.parent


def parse_constraint_rows(path: Path) -> list[list[str]]:
    if not path.is_file():
        return []
    rows: list[list[str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.split("|") if cell.strip()]
        if not cells or cells[0] == "Date":
            continue
        if all(set(cell) <= {"-"} for cell in cells):
            continue
        if len(cells) >= 8:
            rows.append(cells)
    return rows


def load_prepared_package(repo_root: Path) -> dict[str, Any] | None:
    active = repo_root / ".context" / "telemetry" / "active.json"
    try:
        telemetry = json.loads(active.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if telemetry.get("status") not in {"prepared", "running"}:
        return None
    return telemetry


def load_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def load_preflight_reports(repo_root: Path) -> list[dict[str, Any]]:
    preflight_dir = repo_root / ".context" / "preflight"
    results: list[dict[str, Any]] = []
    if not preflight_dir.is_dir():
        return results
    for path in sorted(preflight_dir.glob("C*.json")):
        commit = path.stem
        try:
            report = json.loads(path.read_text(encoding="utf-8"))
            valid = isinstance(report, dict) and "compact" in report
        except (OSError, json.JSONDecodeError):
            report = None
            valid = False
        results.append({"commit": commit, "report": report if valid else None, "valid": valid})
    return results


def load_commit_spec_summary(repo_root: Path, relative_path: str | None) -> dict[str, str]:
    if not relative_path:
        return {}
    try:
        spec_path = (repo_root / relative_path).resolve()
        spec_path.relative_to(repo_root.resolve())
    except (OSError, ValueError):
        return {}
    if not spec_path.is_file():
        return {}
    lines = spec_path.read_text(
        encoding="utf-8",
        errors="replace",
    ).splitlines()
    title = next(
        (line.removeprefix("# ").strip() for line in lines if line.startswith("# ")),
        "",
    )
    summary = ""
    for index, line in enumerate(lines):
        if line.strip().lower() != "## what":
            continue
        paragraph: list[str] = []
        for candidate in lines[index + 1:]:
            stripped = candidate.strip()
            if stripped.startswith("## "):
                break
            if stripped:
                paragraph.append(stripped)
            elif paragraph:
                break
        summary = " ".join(paragraph)
        break
    return {"title": title, "summary": summary}


def build_graph_view_data(repo_root: Path) -> dict[str, Any]:
    graph = load_json(repo_root / ".context" / "index" / "codebase-graph.json") or {}
    categories = graph.get("categories", {})
    summaries = graph.get("summaries", {})
    imports = graph.get("imports", {})
    hub_by_path = {
        hub.get("path"): hub
        for hub in graph.get("hubs", [])
        if isinstance(hub, dict) and hub.get("path")
    }
    all_paths = sorted(set(categories) | set(imports))
    incoming_counts: dict[str, int] = {}
    for targets in imports.values():
        for target in targets:
            incoming_counts[target] = incoming_counts.get(target, 0) + 1
    nodes = []
    for path in all_paths:
        hub = hub_by_path.get(path, {})
        nodes.append({
            "id": path,
            "path": path,
            "name": Path(path).name,
            "category": categories.get(path, "unclassified"),
            "summary": summaries.get(path, ""),
            "in_degree": incoming_counts.get(path, 0),
            "domain_in_degree": int(hub.get("domain_in_degree", 0)),
            "out_degree": len(imports.get(path, [])),
            "hub": path in hub_by_path,
        })
    edges = [
        {"source": source, "target": target}
        for source, targets in imports.items()
        for target in targets
        if source in all_paths and target in all_paths
    ]

    telemetry_dir = repo_root / ".context" / "telemetry"
    telemetry_by_key: dict[str, dict[str, Any]] = {}
    if telemetry_dir.is_dir():
        for path in telemetry_dir.glob("C*-*.json"):
            payload = load_json(path)
            if payload:
                telemetry_by_key[f"{payload.get('commit')}-{payload.get('agent')}"] = payload

    overlays: dict[str, dict[str, Any]] = {}
    runs_dir = repo_root / ".context" / "runs"
    if runs_dir.is_dir():
        for path in sorted(runs_dir.glob("C*-*-live.json")):
            package = load_json(path)
            if not package:
                continue
            key = f"{package.get('commit')}-{package.get('agent')}"
            telemetry = telemetry_by_key.get(key, {})
            spec = load_commit_spec_summary(repo_root, package.get("spec"))
            overlays[key] = {
                "label": f"{package.get('commit')} - {str(package.get('agent', '')).title()}",
                "commit": package.get("commit"),
                "agent": package.get("agent"),
                "task_kind": package.get("task_kind"),
                "spec": package.get("spec"),
                "title": spec.get("title", ""),
                "summary": spec.get("summary", ""),
                "budget": package.get("budget", {}),
                "files": {
                    item["path"]: {
                        "category": item.get("category", "selected"),
                        "reasons": item.get("reasons", []),
                        "read_strategy": item.get("read_strategy", "full file"),
                    }
                    for item in package.get("files", [])
                },
                "excluded": [item.get("path") for item in package.get("excluded_candidates", [])],
                "forbidden": package.get("forbidden_edits", []),
                "read": telemetry.get("selected_read_paths", []),
                "expanded": telemetry.get("outside_read_paths", []),
                "status": telemetry.get("status", "package-only"),
            }
    known_paths = {node["path"] for node in nodes}
    overlay_paths: dict[str, str] = {}
    for overlay in overlays.values():
        for path, item in overlay["files"].items():
            overlay_paths.setdefault(path, item.get("category", "context"))
        for path in overlay.get("excluded", []):
            if path:
                overlay_paths.setdefault(path, "excluded")
        for path in overlay.get("expanded", []):
            if path:
                overlay_paths.setdefault(path, "expanded")
    for path, role in sorted(overlay_paths.items()):
        if path in known_paths:
            continue
        nodes.append({
            "id": path,
            "path": path,
            "name": Path(path).name,
            "category": "context",
            "context_role": role,
            "summary": "",
            "in_degree": 0,
            "domain_in_degree": 0,
            "out_degree": 0,
            "hub": False,
        })
    return {
        "nodes": nodes,
        "edges": edges,
        "overlays": overlays,
        "context_nodes": len(nodes) - len(all_paths),
        "totals": graph.get("totals", {
            "files": len(nodes),
            "edges": len(edges),
            "hubs": sum(node["hub"] for node in nodes),
        }),
    }


def json_for_script(value: Any) -> str:
    return json.dumps(value, separators=(",", ":")).replace("</", "<\\/")


def _scope_cell(scope: dict[str, Any] | None) -> str:
    """Render an agent or orchestrator tool-call count with a source badge."""
    if scope is None or scope.get("status") == "unavailable":
        return '<span style="color:#94a3b8">N/A</span>'
    tool_calls = scope.get("tool_calls")
    calls_text = str(tool_calls) if tool_calls is not None else "N/A"
    source = scope.get("source", "unknown")
    source_styles = {
        "self_report": ("background:#eff6ff;color:#1d4ed8", "self-report"),
        "hooks": ("background:#f0fdf4;color:#166534", "hooks"),
    }
    style, label = source_styles.get(source, ("background:#f8fafc;color:#64748b", source))
    badge_html = (
        f'<span style="{style};border-radius:3px;padding:1px 5px;'
        f'font-size:10px;font-weight:500;margin-left:4px">{label}</span>'
    )
    return f"{calls_text}{badge_html}"


def _expansion_cell(agent_scope: dict[str, Any] | None) -> str:
    """Render expansion count, or Unknown when path-level data is absent."""
    if agent_scope is None or agent_scope.get("status") == "unavailable":
        return '<span style="color:#94a3b8">Unknown</span>'
    expansions = agent_scope.get("expansions")
    if expansions is None:
        return '<span style="color:#94a3b8">Unknown</span>'
    n = len(expansions) if isinstance(expansions, list) else int(expansions)
    color = "#16a34a" if n == 0 else "#dc2626"
    return f'<span style="color:{color};font-weight:500">{n}</span>'


def _combined_cell(
    agent_scope: dict[str, Any] | None,
    orch_scope: dict[str, Any] | None,
) -> str:
    """Render combined tool call total. N/A only when both scopes are unavailable."""
    a_calls: int | None = None
    o_calls: int | None = None
    if agent_scope and agent_scope.get("status") != "unavailable":
        a_calls = agent_scope.get("tool_calls")
    if orch_scope and orch_scope.get("status") != "unavailable":
        o_calls = orch_scope.get("tool_calls")
    if a_calls is None and o_calls is None:
        return '<span style="color:#94a3b8">N/A</span>'
    total = (a_calls or 0) + (o_calls or 0)
    return f'<strong>{total}</strong>'


def _is_expansion_free(record: dict[str, Any]) -> bool | None:
    """Return True=expansion-free, False=had expansions, None=unknown (not counted either way)."""
    telemetry = record.get("telemetry")
    if telemetry:
        agent = telemetry.get("agent", {})
        if agent.get("status") == "unavailable":
            return None
        expansions = agent.get("expansions")
        if expansions is None:
            return None
        n = len(expansions) if isinstance(expansions, list) else int(expansions)
        return n == 0
    # Fallback for records without telemetry key (v1-style)
    usage = record.get("usage", {})
    exp = usage.get("expansions")
    if exp is None:
        return None
    return exp == 0


def badge(value: str, good: bool | None = None) -> str:
    if good is None:
        css = "neutral"
    else:
        css = "good" if good else "bad"
    return f'<span class="badge {css}">{html.escape(value)}</span>'


def _constraint_badge(value: str) -> str:
    """Render a PASS/WARN/FAIL cell from CONSTRAINT_LOG.md with correct colour."""
    v = value.upper().split()[0]
    good: bool | None = True if v == "PASS" else (None if v == "WARN" else False)
    return badge(value.split()[0].lower(), good)


def metric_value(value: Any, suffix: str = "") -> str:
    if value is None:
        return "-"
    return f"{value}{suffix}"


def _preflight_status(entry: dict[str, Any]) -> str:
    if not entry["valid"]:
        return "INVALID REPORT"
    compact = entry["report"].get("compact")
    if not isinstance(compact, dict):
        return "INVALID REPORT"
    if compact.get("proceed"):
        return "READY"
    if compact.get("blocking_violations"):
        return "BLOCKED"
    return "WARNING"


def _preflight_score_badge(entry: dict[str, Any]) -> str:
    status = _preflight_status(entry)
    if status == "INVALID REPORT":
        return badge(status.lower().replace(" ", "-"), False)
    compact = entry["report"].get("compact", {})
    score = compact.get("score", "-")
    good: bool | None = True if status == "READY" else (None if status == "WARNING" else False)
    return badge(f"{status} ({score}/100)", good)


def _preflight_detail_html(commit: str, entry: dict[str, Any]) -> str:
    """Render the expandable detail panel for one commit's preflight report."""
    report = entry["report"]
    if report is None:
        reason = "A preflight report file exists for this commit but could not be parsed as valid JSON, or is missing the expected 'compact' section."
        return f'<div class="preflight-detail"><p class="empty">{html.escape(reason)}</p></div>'

    compact = report.get("compact", {})
    categories = report.get("categories", {})
    deductions = report.get("deductions", {})

    category_rows = ""
    for name, cat in categories.items():
        category_rows += (
            "<tr>"
            f"<td>{html.escape(name)}</td>"
            f"<td>{metric_value(cat.get('points_awarded'))} / {metric_value(cat.get('points_possible'))}</td>"
            f"<td>{badge('pass' if cat.get('passed') else 'fail', cat.get('passed'))}</td>"
            "</tr>"
        )

    deduction_rows = ""
    for name, ded in deductions.items():
        warnings_text = "; ".join(ded.get("warnings", [])) or "None"
        deduction_rows += (
            "<tr>"
            f"<td>{html.escape(name)}</td>"
            f"<td>{metric_value(ded.get('points'))}</td>"
            f"<td>{html.escape(warnings_text)}</td>"
            "</tr>"
        )

    blocking_html = ""
    for violation in compact.get("blocking_violations", []):
        rule, _, repair = violation.partition(": ")
        blocking_html += (
            f"<li><strong>{html.escape(rule)}</strong> — {html.escape(repair or violation)}</li>"
        )
    if not blocking_html:
        blocking_html = "<li>None.</li>"

    warning_html = "".join(f"<li>{html.escape(w)}</li>" for w in compact.get("warnings", [])) or "<li>None.</li>"

    files_html = "".join(
        f"<li>{html.escape(f.get('action', '-').capitalize())}: {html.escape(f.get('path', '-'))}</li>"
        for f in compact.get("files", [])
    ) or "<li>None.</li>"

    context_package = report.get("context_package")
    package_summary = "No context package recorded."
    if isinstance(context_package, dict):
        package_summary = (
            f"{metric_value(context_package.get('selected_files'))} files selected, "
            f"{metric_value(context_package.get('estimated_chars'))} estimated chars."
        )

    dependencies = ", ".join(report.get("dependencies", [])) or "None"
    verification_command = report.get("verification_command", "") or "None"
    report_path = compact.get("report_path", "-")

    raw_json = html.escape(json.dumps(report, indent=2, sort_keys=True))

    return (
        '<div class="preflight-detail">'
        '<div class="preflight-grid">'
        '<div><h4>Score breakdown</h4>'
        f'<table><thead><tr><th>Category</th><th>Points</th><th>Status</th></tr></thead>'
        f'<tbody>{category_rows}</tbody></table>'
        f'<table><thead><tr><th>Deduction</th><th>Points lost</th><th>Warnings</th></tr></thead>'
        f'<tbody>{deduction_rows}</tbody></table></div>'
        '<div><h4>Blocking violations</h4><ul>' + blocking_html + '</ul>'
        '<h4>Warnings</h4><ul>' + warning_html + '</ul></div>'
        '<div><h4>Planned files</h4><ul>' + files_html + '</ul>'
        f'<h4>Context package</h4><p>{html.escape(package_summary)}</p>'
        f'<h4>Dependencies</h4><p>{html.escape(dependencies)}</p>'
        f'<h4>Verification command</h4><pre>{html.escape(verification_command)}</pre>'
        f'<p class="legend">Report: {html.escape(report_path)}</p></div>'
        '</div>'
        '<details class="preflight-raw"><summary>Exact persisted report (JSON)</summary>'
        f'<pre>{raw_json}</pre></details>'
        '</div>'
    )


def render_preflight_rows(repo_root: Path) -> str:
    """Render the preflight readiness table rows with expandable details."""
    reports = load_preflight_reports(repo_root)
    if not reports:
        return '<tr><td colspan="5" class="empty">No preflight reports have been generated yet.</td></tr>'

    rows = ""
    for entry in reports:
        commit = entry["commit"]
        report = entry["report"]
        compact = (report or {}).get("compact", {}) if report else {}
        blocking = len(compact.get("blocking_violations", []))
        warnings = len(compact.get("warnings", []))
        goal = compact.get("goal", "-")
        row_id = f"preflight-{html.escape(commit)}"
        rows += (
            f'<tr class="preflight-row" data-target="{row_id}" '
            f'onclick="this.nextElementSibling.hidden=!this.nextElementSibling.hidden">'
            f"<td>{badge(commit)}</td>"
            f"<td>{_preflight_score_badge(entry)}</td>"
            f"<td>{metric_value(blocking if report else None)}</td>"
            f"<td>{metric_value(warnings if report else None)}</td>"
            f"<td>{html.escape(goal) if goal else '-'}</td>"
            "</tr>"
            f'<tr class="preflight-detail-row" id="{row_id}" hidden>'
            f'<td colspan="5">{_preflight_detail_html(commit, entry)}</td>'
            "</tr>"
        )
    return rows


def render_dashboard(
    repo_root: Path = REPO_ROOT,
    output_path: Path | None = None,
) -> str:
    output_path = output_path or repo_root / "constraint-dashboard.html"
    constraint_rows = parse_constraint_rows(repo_root / "CONSTRAINT_LOG.md")
    metrics = load_metrics(repo_root / "CONTEXT_METRICS.json").get("records", [])
    prepared = load_prepared_package(repo_root)
    graph_data = build_graph_view_data(repo_root)

    total = len(constraint_rows)
    passed = sum(row[7].upper() == "PASS" for row in constraint_rows)
    failed = sum(row[7].upper() == "FAIL" for row in constraint_rows)
    token_values = [
        int(row[3].replace(",", ""))
        for row in constraint_rows
        if row[3].replace(",", "").isdigit() and int(row[3].replace(",", "")) > 0
    ]
    avg_tokens = round(sum(token_values) / len(token_values)) if token_values else None

    measured = len(metrics)
    package_chars = [r["package"].get("estimated_chars", 0) for r in metrics if r.get("package")]
    utilizations = [
        r["usage"].get("selected_utilization_percent")
        for r in metrics
        if r.get("usage", {}).get("selected_utilization_percent") is not None
    ]
    expansion_statuses = [_is_expansion_free(r) for r in metrics]
    expansion_free = sum(1 for s in expansion_statuses if s is True)
    expansion_unknown = sum(1 for s in expansion_statuses if s is None)
    boundary_clean = sum(r.get("boundaries", {}).get("forbidden_clean", False) for r in metrics)
    avg_package = round(sum(package_chars) / len(package_chars)) if package_chars else None
    avg_use = round(sum(utilizations) / len(utilizations), 1) if utilizations else None

    prepared_html = ""
    if prepared:
        package = prepared.get("package", {})
        triggers = package.get("expansion_triggers", [])
        trigger_text = ", ".join(triggers) if triggers else "none"
        prepared_html = (
            '<section><div class="section-head"><div><h2>Prepared next delegation</h2>'
            '<p>Live package waiting for approval or agent execution.</p></div>'
            + badge(str(prepared.get("status", "prepared")).upper(), True)
            + '</div><div class="prepared-grid">'
            f'<div><span>Commit</span><strong>{html.escape(prepared.get("commit", "-"))}</strong></div>'
            f'<div><span>Agent</span><strong>{html.escape(prepared.get("agent", "-").title())}</strong></div>'
            f'<div><span>Package</span><strong>{package.get("selected_files", 0)} files</strong></div>'
            f'<div><span>Estimated context</span><strong>{package.get("estimated_chars", 0):,} chars</strong></div>'
            f'<div><span>Targeted excerpts</span><strong>{package.get("targeted_excerpt_files", 0)}</strong></div>'
            f'<div><span>Expansion triggers</span><strong>{html.escape(trigger_text)}</strong></div>'
            '</div></section>'
        )

    metric_rows = ""
    for record in reversed(metrics):
        pkg = record.get("package", {})
        usage = record.get("usage", {})
        boundary = record.get("boundaries", {})
        telemetry = record.get("telemetry", {})
        agent_scope = telemetry.get("agent") if telemetry else None
        orch_scope = telemetry.get("orchestrator") if telemetry else None
        selected = pkg.get("selected_files", 0)
        used = usage.get("selected_files_read")
        use_pct = usage.get("selected_utilization_percent")
        metric_rows += (
            "<tr>"
            f"<td>{badge(record.get('commit', '-'))}</td>"
            f"<td>{html.escape(record.get('agent', '-').title())}</td>"
            f"<td>{metric_value(record.get('tokens'))}</td>"
            f"<td><strong>{selected}</strong> / {pkg.get('estimated_chars', 0):,} chars</td>"
            f"<td>{metric_value(used)} / {selected} ({metric_value(use_pct, '%')})</td>"
            f"<td>{_scope_cell(agent_scope)}</td>"
            f"<td>{_scope_cell(orch_scope)}</td>"
            f"<td>{_combined_cell(agent_scope, orch_scope)}</td>"
            f"<td>{_expansion_cell(agent_scope)}</td>"
            f"<td>{badge('clean' if boundary.get('forbidden_clean') else 'violation', boundary.get('forbidden_clean'))}</td>"
            "</tr>"
        )
    if not metric_rows:
        metric_rows = (
            '<tr><td colspan="10" class="empty">Phase B measurements begin with the next '
            'verified live delegation.</td></tr>'
        )

    preflight_html = render_preflight_rows(repo_root)

    constraint_html = ""
    for row in constraint_rows:
        token = row[3] if row[3] not in {"-", "0"} else "-"
        constraint_html += (
            "<tr>"
            f"<td>{html.escape(row[0])}</td><td>{badge(row[1])}</td>"
            f"<td>{html.escape(row[2])}</td><td>{html.escape(token)}</td>"
            f"<td>{_constraint_badge(row[4])}</td>"
            f"<td>{_constraint_badge(row[5])}</td>"
            f"<td>{_constraint_badge(row[6])}</td>"
            f"<td>{_constraint_badge(row[7])}</td>"
            "</tr>"
        )

    css = """
*{box-sizing:border-box}body{margin:0;background:#f4f7fb;color:#182235;font:14px/1.45 Inter,Segoe UI,sans-serif}
.container{max-width:1640px;margin:auto;padding:30px 22px 50px}h1{font-size:25px;margin:0}h2{font-size:17px;margin:0 0 3px}
.subtitle,.section-head p{color:#65738a;margin:4px 0 0}.tabs{display:flex;gap:6px;margin:22px 0 18px;border-bottom:1px solid #dbe3ed}
.tab{appearance:none;border:0;background:transparent;padding:10px 15px;color:#68768b;font-weight:600;cursor:pointer;border-bottom:3px solid transparent}
.tab.active{color:#2457c5;border-bottom-color:#2457c5}.tab-panel{display:none}.tab-panel.active{display:block}
.cards{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin:18px 0}.card,section{background:white;border:1px solid #dfe6ef;border-radius:12px;box-shadow:0 2px 9px #23395d0a}
.card{padding:14px}.card span,.prepared-grid span{display:block;color:#718096;font-size:11px;text-transform:uppercase;letter-spacing:.05em}
.card strong{display:block;font-size:24px;margin-top:5px}section{padding:18px;margin-bottom:18px}.section-head{display:flex;justify-content:space-between;align-items:start;margin-bottom:14px}
.prepared-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:1px;background:#e7edf4;border:1px solid #e7edf4;border-radius:9px;overflow:hidden}
.prepared-grid div{background:#f9fbfd;padding:12px}.prepared-grid strong{display:block;margin-top:4px;font-size:14px}
.table-wrap{overflow:auto;border:1px solid #e3e9f1;border-radius:9px}table{width:100%;border-collapse:collapse;white-space:nowrap}
th{background:#f7f9fc;color:#69778e;font-size:10px;text-transform:uppercase;letter-spacing:.06em;text-align:left;padding:10px 12px}
td{padding:10px 12px;border-top:1px solid #edf1f5}tr:hover td{background:#fafcff}.badge{display:inline-block;padding:2px 8px;border-radius:999px;background:#edf2f7;color:#455468;font-size:11px;font-weight:600}
.badge.good{background:#e8f7ef;color:#157347}.badge.bad{background:#fdebec;color:#b4232c}.empty{text-align:center;color:#7b8798;padding:24px}.legend{color:#67758a;font-size:12px;margin-top:10px}
.graph-controls{display:grid;grid-template-columns:1.2fr 1.6fr auto auto;gap:10px;align-items:end;margin-bottom:12px}.field label{display:block;color:#718096;font-size:10px;text-transform:uppercase;letter-spacing:.05em;margin-bottom:4px}
.field input,.field select,.graph-button{width:100%;border:1px solid #cfd9e6;background:#fff;border-radius:7px;padding:8px 10px;color:#263449}.graph-button{width:auto;cursor:pointer;font-weight:600}
.graph-layout{display:block}.graph-stage{height:820px;border:1px solid #dce5ef;border-radius:10px;background:#111827;overflow:hidden;position:relative}
#graphSvg{width:100%;height:100%;display:block;touch-action:none}.graph-tooltip{display:none;position:absolute;z-index:3;width:310px;max-height:330px;overflow:auto;padding:13px 14px;border:1px solid #334155;border-radius:10px;background:#f8fafcf5;color:#182235;box-shadow:0 12px 30px #02061766;pointer-events:none}
.graph-tooltip.visible{display:block}.graph-tooltip h3{font-size:13px;margin:0 0 8px;word-break:break-word}.tooltip-summary{margin:0 0 9px;color:#475569;font-size:11px;line-height:1.45}.tooltip-row{border-top:1px solid #dbe3ed;padding:7px 0}.tooltip-row span{display:block;color:#778499;font-size:9px;text-transform:uppercase}.tooltip-row strong{font-size:12px}.tooltip-list{margin:4px 0 0;padding-left:16px;font-size:11px;word-break:break-word}
.graph-legend{position:absolute;z-index:2;right:12px;top:12px;display:grid;grid-template-columns:repeat(2,max-content);gap:6px 12px;padding:10px 12px;border:1px solid #334155;border-radius:9px;background:#0f172ae8;color:#cbd5e1;font-size:10px;pointer-events:none}.legend-dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:4px}
.graph-commit-summary{display:none;position:absolute;z-index:2;left:12px;top:12px;width:310px;max-height:540px;overflow:auto;padding:16px 18px;border:1px solid #334155;border-radius:9px;background:#0f172aee;color:#dbeafe;box-shadow:0 8px 24px #02061755}.graph-commit-summary.visible{display:block}.graph-commit-summary h3{font-size:14px;margin:0 0 7px}.graph-commit-summary p{margin:5px 0;color:#cbd5e1;font-size:11px;line-height:1.5}.commit-meta{display:flex;flex-wrap:wrap;gap:5px;margin:9px 0}.commit-meta span{padding:2px 6px;border-radius:999px;background:#1e293b;color:#bfdbfe;font-size:9px}.commit-files{margin:6px 0 0;padding-left:18px;font-size:11px;line-height:1.45;word-break:break-word}.commit-file-link{color:#7dd3fc;text-decoration:none;border-bottom:1px dotted #38bdf8}.commit-file-link:hover,.commit-file-link:focus{color:#e0f2fe;border-bottom-style:solid;outline:none}
.overlay-key{display:inline-flex;align-items:center;gap:4px}.overlay-mark{width:13px;height:13px;border:2px solid;border-radius:4px}.graph-status{position:absolute;left:10px;bottom:8px;color:#b8c2d3;background:#111827cc;padding:4px 7px;border-radius:5px;font-size:11px;pointer-events:none}
@media(max-width:900px){.cards{grid-template-columns:repeat(2,1fr)}.prepared-grid{grid-template-columns:1fr}.graph-controls{grid-template-columns:1fr 1fr}.graph-stage{height:560px}}
.preflight-row{cursor:pointer}.preflight-row:hover td{background:#eef3fb}.preflight-detail-row td{padding:0;border-top:0}
.preflight-detail{padding:14px 16px;background:#f9fbfd;border-top:1px solid #edf1f5}
.preflight-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}
.preflight-grid h4{margin:0 0 6px;font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:#69778e}
.preflight-grid ul{margin:0 0 10px;padding-left:18px;font-size:12px}.preflight-grid table{width:100%;margin-bottom:10px;font-size:12px}
.preflight-grid pre{white-space:pre-wrap;word-break:break-word;background:#fff;border:1px solid #e3e9f1;border-radius:6px;padding:8px;font-size:11px;margin:0 0 8px}
.preflight-raw{margin-top:10px}.preflight-raw pre{max-height:320px;overflow:auto;white-space:pre-wrap;word-break:break-word;background:#0f172a;color:#cbd5e1;border-radius:8px;padding:12px;font-size:11px}
.preflight-raw summary{cursor:pointer;font-size:12px;color:#2457c5;font-weight:600}
"""
    if measured:
        ef_label = f"{expansion_free}/{measured}"
        if expansion_unknown:
            ef_label += f" ({expansion_unknown} unknown)"
    else:
        ef_label = "-"
    phase_cards = [
        ("Measured commits", measured),
        ("Avg package", f"{avg_package:,} chars" if avg_package is not None else "-"),
        ("Selected files used", f"{avg_use}%" if avg_use is not None else "-"),
        ("Expansion-free", ef_label),
        ("Boundary clean", f"{boundary_clean}/{measured}" if measured else "-"),
    ]
    cards_html = "".join(
        f'<div class="card"><span>{label}</span><strong>{value}</strong></div>'
        for label, value in phase_cards
    )
    last_date = constraint_rows[-1][0] if constraint_rows else "-"
    graph_totals = graph_data.get("totals", {})
    graph_summary = (
        f"{graph_totals.get('files', len(graph_data['nodes']))} indexed"
        f" · {graph_data.get('context_nodes', 0)} context"
        f" · {graph_totals.get('edges', len(graph_data['edges']))} edges"
    )
    graph_json = json_for_script(graph_data)
    document = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Manifesto Measurement Dashboard</title><style>{css}</style></head><body><div class="container">
<h1>Manifesto Measurement Dashboard</h1>
<p class="subtitle">{total} constraint checks · {passed} passed · {failed} failed · avg {metric_value(avg_tokens)} tokens · updated {last_date}</p>
<div class="tabs" role="tablist">
<button class="tab active" data-tab="measurements">Commit measurements</button>
<button class="tab" data-tab="graph">Codebase graph</button>
</div>
<main id="measurements" class="tab-panel active">
{prepared_html}
<section><div class="section-head"><div><h2>Phase B context efficiency</h2>
<p>Measures whether the prepared package was concise and sufficient.</p></div></div>
<div class="cards">{cards_html}</div>
<div class="table-wrap"><table><thead><tr><th>Commit</th><th>Agent</th><th>Tokens</th><th>Package</th>
<th>Selected used</th><th>Agent calls</th><th>Orch calls</th><th>Combined</th><th>Expansions</th><th>Boundary</th></tr></thead>
<tbody>{metric_rows}</tbody></table></div>
<p class="legend">Agent / Orch calls = tool calls per scope with source badge. N/A = telemetry unavailable for that scope. Expansion = paths read outside the selected package (Unknown when path-level data missing).</p></section>
<section><div class="section-head"><div><h2>Constraint history</h2>
<p>Existing checks for upfront context, forbidden paths, tool budget, and result.</p></div></div>
<div class="table-wrap"><table><thead><tr><th>Date</th><th>Commit</th><th>Agent</th><th>Tokens</th>
<th>Context</th><th>Forbidden</th><th>Budget</th><th>Result</th></tr></thead>
<tbody>{constraint_html}</tbody></table></div></section>
<section><div class="section-head"><div><h2>Preflight readiness</h2>
<p>Deterministic Python preflight scores per commit. Click a row to inspect the full report.</p></div></div>
<div class="table-wrap"><table><thead><tr><th>Commit</th><th>Score / status</th><th>Blocking</th><th>Warnings</th><th>Goal</th></tr></thead>
<tbody>{preflight_html}</tbody></table></div>
<p class="legend">NOT RUN = no .context/preflight/C&lt;ID&gt;.json report exists yet. INVALID REPORT = the report file could not be parsed. The dashboard never recalculates scores or overrides the persisted proceed decision.</p></section>
</main>
<main id="graph" class="tab-panel">
<section><div class="section-head"><div><h2>Codebase context graph</h2>
<p>Drag category frames to rearrange groups. Select a commit to inspect its context package over the network.</p></div>
{badge(graph_summary)}</div>
<div class="graph-controls">
<div class="field"><label for="commitOverlay">Commit overlay</label><select id="commitOverlay"><option value="">Whole codebase</option></select></div>
<div class="field"><label for="graphSearch">Find file</label><input id="graphSearch" type="search" placeholder="config.py, auth, frontend/src..."></div>
<button id="fitGraph" class="graph-button">Fit graph</button>
<button id="resetGraph" class="graph-button">Reset layout</button>
</div>
<div class="graph-layout"><div class="graph-stage"><svg id="graphSvg" aria-label="Codebase dependency graph"></svg><div id="graphTooltip" class="graph-tooltip"></div><div id="commitSummary" class="graph-commit-summary"></div><div class="graph-legend">
<span><i class="legend-dot" style="background:#60a5fa"></i>backend</span><span><i class="legend-dot" style="background:#34d399"></i>frontend</span>
<span><i class="legend-dot" style="background:#c084fc"></i>AI</span><span><i class="legend-dot" style="background:#fbbf24"></i>tests</span>
<span><i class="legend-dot" style="background:#fb7185"></i>DevOps</span><span><i class="legend-dot" style="background:#94a3b8"></i>config/other</span>
<span class="overlay-key"><i class="overlay-mark" style="border-color:#22d3ee"></i>primary</span>
<span class="overlay-key"><i class="overlay-mark" style="border-color:#c084fc"></i>contract</span>
<span class="overlay-key"><i class="overlay-mark" style="border-color:#34d399"></i>dependency</span>
<span class="overlay-key"><i class="overlay-mark" style="border-color:#f97316"></i>hub</span>
<span class="overlay-key"><i class="overlay-mark" style="border-color:#ef4444"></i>forbidden</span>
<span class="overlay-key"><i class="overlay-mark" style="border-color:#facc15"></i>expanded</span>
</div><div id="graphStatus" class="graph-status"></div></div></div></section></main>
</div>
<script>const GRAPH_DATA={graph_json};
const COLORS={{backend:"#60a5fa",frontend:"#34d399",ai:"#c084fc",tests:"#fbbf24",devops:"#fb7185",config:"#94a3b8",docs:"#a78bfa",context:"#475569",unclassified:"#64748b"}};
const ROLE_COLORS={{primary:"#22d3ee",contract:"#c084fc",dependency:"#34d399",structural:"#60a5fa",test:"#fb7185",hub:"#f97316",identity:"#94a3b8",worklog:"#94a3b8"}};
const svg=document.getElementById("graphSvg"),tooltip=document.getElementById("graphTooltip"),commitSummary=document.getElementById("commitSummary"),statusEl=document.getElementById("graphStatus");
const overlaySelect=document.getElementById("commitOverlay"),searchInput=document.getElementById("graphSearch");
let width=900,height=650,scale=1,panX=0,panY=0,dragNode=null,dragCategory=null,categoryDragStart=null,panStart=null,activeOverlay="",query="",hoveredNode=null,focusedNode=null,edgeElements=[];
const categories=[...new Set(GRAPH_DATA.nodes.map(n=>n.category))].sort(),enabled=new Set(categories);
const nodeMap=new Map(GRAPH_DATA.nodes.map(n=>[n.id,n]));
const CATEGORY_SLOTS={{ai:[150,145],backend:[610,270],tests:[150,435],config:[260,690],context:[470,750],devops:[690,680],frontend:[1050,710]}};
const defaultCategorySlot=(cat,i)=>CATEGORY_SLOTS[cat]||[170+(i%4)*330,180+Math.floor(i/4)*390];
const categoryCenters=new Map(categories.map((cat,i)=>{{const slot=defaultCategorySlot(cat,i);return[cat,{{x:slot[0],y:slot[1]}}];}}));
function resetCategoryCenters(){{categories.forEach((cat,i)=>{{const slot=defaultCategorySlot(cat,i),center=categoryCenters.get(cat);center.x=slot[0];center.y=slot[1];}});}}
function hubScore(n){{return n.in_degree*4+n.domain_in_degree*2+n.out_degree+(n.hub?8:0);}}
function seedLayout(){{const grouped=new Map(categories.map(cat=>[cat,[]]));GRAPH_DATA.nodes.forEach(n=>(grouped.get(n.category)||grouped.get(categories[0])).push(n));grouped.forEach((nodes,cat)=>{{const center=categoryCenters.get(cat),spacing=cat==="backend"?34:nodes.length>15?31:29;nodes.sort((a,b)=>hubScore(b)-hubScore(a)||a.path.localeCompare(b.path));nodes.forEach((n,i)=>{{const angle=i*2.399963,r=i===0?0:spacing*Math.sqrt(i);n.x=center.x+Math.cos(angle)*r;n.y=center.y+Math.sin(angle)*r;n.homeX=n.x;n.homeY=n.y;n.vx=0;n.vy=0;}});}});}}
Object.entries(GRAPH_DATA.overlays).sort().forEach(([key,o])=>{{const opt=document.createElement("option");opt.value=key;opt.textContent=o.label;overlaySelect.appendChild(opt);}});
document.querySelectorAll(".tab").forEach(btn=>btn.onclick=()=>{{document.querySelectorAll(".tab").forEach(x=>x.classList.toggle("active",x===btn));document.querySelectorAll(".tab-panel").forEach(x=>x.classList.toggle("active",x.id===btn.dataset.tab));if(btn.dataset.tab==="graph")requestAnimationFrame(fitGraph);}});
overlaySelect.onchange=()=>{{activeOverlay=overlaySelect.value;renderCommitSummary();render();}};
searchInput.oninput=()=>{{query=searchInput.value.trim().toLowerCase();render();}};
document.getElementById("fitGraph").onclick=fitGraph;document.getElementById("resetGraph").onclick=()=>{{layout(true);fitGraph();}};
function resize(){{const r=svg.getBoundingClientRect();width=r.width||900;height=r.height||650;}}
function overlay(){{return GRAPH_DATA.overlays[activeOverlay]||null;}}
function forbidden(path,o){{return !!o&&(o.forbidden||[]).some(p=>path===p.replace(/\\/$/,"")||path.startsWith(p));}}
function visible(n){{return enabled.has(n.category)&&(!query||n.path.toLowerCase().includes(query));}}
function nodeStyle(n){{const o=overlay(),f=o&&o.files[n.path],read=o&&(o.read||[]).includes(n.path),expanded=o&&(o.expanded||[]).includes(n.path),excluded=o&&(o.excluded||[]).includes(n.path),blocked=forbidden(n.path,o);
let stroke="#111827",sw=1,opacity=visible(n)?1:.08;if(o){{opacity=(f||expanded||blocked||excluded)?0.98:0.15;if(blocked){{stroke="#ef4444";sw=3;}}else if(expanded){{stroke="#facc15";sw=4;}}else if(f){{stroke=ROLE_COLORS[f.category]||"#22d3ee";sw=read?5:3;}}else if(excluded){{stroke="#94a3b8";sw=3;opacity=.45;}}}}return{{fill:COLORS[n.category]||COLORS.unclassified,stroke,sw,opacity}};}}
function layout(reset=false){{if(reset){{resetCategoryCenters();seedLayout();}}
for(let tick=0;tick<80;tick++){{for(let i=0;i<GRAPH_DATA.nodes.length;i++)for(let j=i+1;j<GRAPH_DATA.nodes.length;j++){{const a=GRAPH_DATA.nodes[i],b=GRAPH_DATA.nodes[j];if(a.category!==b.category)continue;const dx=a.x-b.x,dy=a.y-b.y,d=Math.max(Math.hypot(dx,dy),.1),minimum=a.category==="backend"?38:34;if(d<minimum){{const force=(minimum-d)*.055;a.vx+=dx/d*force;a.vy+=dy/d*force;b.vx-=dx/d*force;b.vy-=dy/d*force;}}}}
GRAPH_DATA.nodes.forEach(n=>{{n.vx+=(n.homeX-n.x)*.08;n.vy+=(n.homeY-n.y)*.08;n.vx*=.62;n.vy*=.62;n.x+=n.vx;n.y+=n.vy;}});}}}}
function fitGraph(){{resize();const xs=GRAPH_DATA.nodes.map(n=>n.x),ys=GRAPH_DATA.nodes.map(n=>n.y),minX=Math.min(...xs),maxX=Math.max(...xs),minY=Math.min(...ys),maxY=Math.max(...ys);scale=Math.min((width-100)/(maxX-minX||1),(height-100)/(maxY-minY||1),1.35);panX=width/2-(minX+maxX)/2*scale;panY=height/2-(minY+maxY)/2*scale;render();}}
function render(){{resize();svg.innerHTML="";const ns="http://www.w3.org/2000/svg",g=document.createElementNS(ns,"g");g.setAttribute("transform",`translate(${{panX}} ${{panY}}) scale(${{scale}})`);svg.appendChild(g);
categories.forEach(category=>drawCategoryFrame(g,ns,category));
edgeElements=[];GRAPH_DATA.edges.forEach(e=>{{const a=nodeMap.get(e.source),b=nodeMap.get(e.target);if(!a||!b)return;const same=a.category===b.category,line=document.createElementNS(ns,"line");line.setAttribute("x1",a.x);line.setAttribute("y1",a.y);line.setAttribute("x2",b.x);line.setAttribute("y2",b.y);line.setAttribute("stroke",same?"#8fa2ba":"#64748b");line.dataset.source=e.source;line.dataset.target=e.target;line.dataset.same=same?"1":"0";g.appendChild(line);edgeElements.push(line);}});updateEdgeStyles();
GRAPH_DATA.nodes.forEach(n=>{{const s=nodeStyle(n),group=document.createElementNS(ns,"g"),circle=document.createElementNS(ns,"circle"),radius=7+Math.min(10,n.in_degree*.75+n.domain_in_degree*.5)+(n.hub?3:0);circle.setAttribute("cx",n.x);circle.setAttribute("cy",n.y);circle.setAttribute("r",radius);circle.setAttribute("fill",s.fill);circle.setAttribute("stroke",s.stroke);circle.setAttribute("stroke-width",s.sw);circle.setAttribute("opacity",s.opacity);circle.style.cursor="pointer";circle.onpointerdown=e=>{{e.stopPropagation();dragNode=n;circle.setPointerCapture(e.pointerId);}};circle.onpointerenter=e=>{{hoveredNode=n.id;updateEdgeStyles();showTooltip(n,e);}};circle.onpointermove=moveTooltip;circle.onpointerleave=()=>{{hoveredNode=null;updateEdgeStyles();hideTooltip();}};group.appendChild(circle);
const label=document.createElementNS(ns,"text");label.setAttribute("x",n.x);label.setAttribute("y",n.y-radius-4);label.setAttribute("fill","#f1f5f9");label.setAttribute("font-size","7");label.setAttribute("font-weight","600");label.setAttribute("text-anchor","middle");label.setAttribute("paint-order","stroke");label.setAttribute("stroke","#111827");label.setAttribute("stroke-width","2");label.setAttribute("stroke-linejoin","round");label.setAttribute("opacity",s.opacity);label.style.pointerEvents="none";label.textContent=n.name;group.appendChild(label);g.appendChild(group);}});
const o=overlay();statusEl.textContent=o?`${{o.label}} · ${{Object.keys(o.files).length}} selected · ${{(o.expanded||[]).length}} expanded`:`Whole codebase · ${{GRAPH_DATA.nodes.length}} files · ${{GRAPH_DATA.edges.length}} imports`;}}
function drawCategoryFrame(g,ns,category){{const nodes=GRAPH_DATA.nodes.filter(n=>n.category===category);if(!nodes.length)return;const color=COLORS[category]||COLORS.unclassified,pad=27,minX=Math.min(...nodes.map(n=>n.x))-pad,maxX=Math.max(...nodes.map(n=>n.x))+pad,minY=Math.min(...nodes.map(n=>n.y))-pad-8,maxY=Math.max(...nodes.map(n=>n.y))+pad;const group=document.createElementNS(ns,"g"),rect=document.createElementNS(ns,"rect"),label=document.createElementNS(ns,"text");rect.setAttribute("x",minX);rect.setAttribute("y",minY);rect.setAttribute("width",maxX-minX);rect.setAttribute("height",maxY-minY);rect.setAttribute("rx","14");rect.setAttribute("fill",color);rect.setAttribute("fill-opacity",enabled.has(category)?".055":".015");rect.setAttribute("stroke",color);rect.setAttribute("stroke-width","1.25");rect.setAttribute("stroke-dasharray","6 4");rect.setAttribute("opacity",enabled.has(category)?".8":".15");rect.style.cursor="move";rect.onpointerdown=e=>startCategoryDrag(category,e);label.setAttribute("x",minX+11);label.setAttribute("y",minY+15);label.setAttribute("fill",color);label.setAttribute("font-size","8");label.setAttribute("font-weight","700");label.setAttribute("letter-spacing",".08em");label.style.pointerEvents="none";label.textContent=category.toUpperCase();group.appendChild(rect);group.appendChild(label);g.appendChild(group);}}
function renderCommitSummary(){{const o=overlay();if(!o){{commitSummary.classList.remove("visible");commitSummary.innerHTML="";return;}}const entries=Object.entries(o.files),primary=entries.filter(([,file])=>file.category==="primary"),shown=primary.length?primary:entries,roles={{}};entries.forEach(([,file])=>roles[file.category]=(roles[file.category]||0)+1);const roleText=Object.entries(roles).map(([role,count])=>`${{count}} ${{role}}`).join(" · "),files=shown.slice(0,8).map(([path])=>`<li><a href="#" class="commit-file-link" data-node-path="${{escapeHtml(path)}}">${{escapeHtml(path)}}</a></li>`).join(""),budget=o.budget||{{}},why=o.summary||[...new Set(shown.flatMap(([,file])=>file.reasons||[]))].join("; ")||"Prepared context package for this commit.";commitSummary.innerHTML=`<h3>${{escapeHtml(o.title||o.label)}}</h3><p>${{escapeHtml(why)}}</p><div class="commit-meta"><span>${{escapeHtml(o.task_kind||"task")}}</span><span>${{entries.length}} selected</span><span>${{roleText||"context selected"}}</span><span>${{(o.read||[]).length}} read</span><span>${{(o.expanded||[]).length}} expanded</span>${{budget.estimated_selected_chars?`<span>${{Number(budget.estimated_selected_chars).toLocaleString()}} chars</span>`:""}}</div><p><strong>${{primary.length?"Primary change files":"Selected context"}}</strong></p><ul class="commit-files">${{files}}</ul>${{o.forbidden&&o.forbidden.length?`<p><strong>Boundaries:</strong> ${{escapeHtml(o.forbidden.join(", "))}}</p>`:""}}`;commitSummary.querySelectorAll(".commit-file-link").forEach(link=>link.onclick=e=>{{e.preventDefault();focusGraphNode(link.dataset.nodePath);}});commitSummary.classList.add("visible");}}
function focusGraphNode(path){{const node=nodeMap.get(path);if(!node)return;query="";searchInput.value="";hideTooltip();resize();focusedNode=node.id;hoveredNode=null;scale=Math.max(scale,2.15);panX=width*.62-node.x*scale;panY=height*.5-node.y*scale;render();}}
function startCategoryDrag(category,e){{e.stopPropagation();hideTooltip();const r=svg.getBoundingClientRect(),x=(e.clientX-r.left-panX)/scale,y=(e.clientY-r.top-panY)/scale,nodes=GRAPH_DATA.nodes.filter(n=>n.category===category).map(n=>({{node:n,x:n.x,y:n.y,homeX:n.homeX,homeY:n.homeY}})),center=categoryCenters.get(category);dragCategory=category;categoryDragStart={{pointerId:e.pointerId,x,y,nodes,centerX:center.x,centerY:center.y}};svg.setPointerCapture(e.pointerId);}}
function updateEdgeStyles(){{const activeNode=hoveredNode||focusedNode;edgeElements.forEach(line=>{{const source=nodeMap.get(line.dataset.source),target=nodeMap.get(line.dataset.target),connected=activeNode&&(line.dataset.source===activeNode||line.dataset.target===activeNode),shown=source&&target&&visible(source)&&visible(target);line.setAttribute("stroke",connected?"#e2e8f0":line.dataset.same==="1"?"#8fa2ba":"#64748b");line.setAttribute("stroke-width",connected?"2.4":line.dataset.same==="1"?".9":".65");line.setAttribute("opacity",shown?(connected?".92":line.dataset.same==="1"?".12":".035"):".012");}});}}
function nodeSummary(n,incoming,outgoing){{if(n.summary)return n.summary;const categoryLabel=n.category==="context"?"project context":n.category,usedBy=incoming.length,uses=outgoing.length;if(hubScore(n)>=12||n.hub)return `Central ${{categoryLabel}} hub. It connects ${{uses}} dependencies and is used by ${{usedBy}} files.`;if(usedBy&&uses)return `${{categoryLabel}} bridge file. It depends on ${{uses}} files and supplies behavior to ${{usedBy}} others.`;if(usedBy)return `Shared ${{categoryLabel}} file used by ${{usedBy}} other file${{usedBy===1?"":"s"}}.`;if(uses)return `${{categoryLabel}} entry or leaf file that brings together ${{uses}} dependencies.`;return `Standalone ${{categoryLabel}} file with no indexed import relationships.`;}}
function showTooltip(n,e){{const incoming=GRAPH_DATA.edges.filter(edge=>edge.target===n.id).map(edge=>edge.source),outgoing=GRAPH_DATA.edges.filter(edge=>edge.source===n.id).map(edge=>edge.target),list=a=>a.length?`<ul class="tooltip-list">${{a.slice(0,10).map(x=>`<li>${{escapeHtml(x)}}</li>`).join("")}}</ul>`:"<strong>None</strong>";tooltip.innerHTML=`<h3>${{escapeHtml(n.path)}}</h3><p class="tooltip-summary">${{escapeHtml(nodeSummary(n,incoming,outgoing))}}</p><div class="tooltip-row"><span>Hub score</span><strong>${{hubScore(n)}} · in ${{n.in_degree}} · domain ${{n.domain_in_degree}} · out ${{n.out_degree}}</strong></div><div class="tooltip-row"><span>Imports</span>${{list(outgoing)}}</div><div class="tooltip-row"><span>Imported by</span>${{list(incoming)}}</div>`;tooltip.classList.add("visible");moveTooltip(e);}}
function moveTooltip(e){{const stage=svg.parentElement,r=stage.getBoundingClientRect(),tw=tooltip.offsetWidth||310,th=tooltip.offsetHeight||220;let x=e.clientX-r.left+16,y=e.clientY-r.top+16;if(x+tw>r.width-8)x=e.clientX-r.left-tw-16;if(y+th>r.height-8)y=r.height-th-8;tooltip.style.left=`${{Math.max(8,x)}}px`;tooltip.style.top=`${{Math.max(8,y)}}px`;}}
function hideTooltip(){{tooltip.classList.remove("visible");}}
function escapeHtml(v){{return String(v).replace(/[&<>"']/g,c=>({{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}}[c]));}}
svg.onpointerdown=e=>{{if(e.target===svg)panStart={{x:e.clientX,y:e.clientY,px:panX,py:panY}};}};svg.onpointermove=e=>{{if(dragCategory&&categoryDragStart){{const r=svg.getBoundingClientRect(),x=(e.clientX-r.left-panX)/scale,y=(e.clientY-r.top-panY)/scale,dx=x-categoryDragStart.x,dy=y-categoryDragStart.y;categoryDragStart.nodes.forEach(item=>{{item.node.x=item.x+dx;item.node.y=item.y+dy;item.node.homeX=item.homeX+dx;item.node.homeY=item.homeY+dy;}});const center=categoryCenters.get(dragCategory);center.x=categoryDragStart.centerX+dx;center.y=categoryDragStart.centerY+dy;render();}}else if(dragNode){{const r=svg.getBoundingClientRect();dragNode.x=(e.clientX-r.left-panX)/scale;dragNode.y=(e.clientY-r.top-panY)/scale;dragNode.homeX=dragNode.x;dragNode.homeY=dragNode.y;render();}}else if(panStart){{panX=panStart.px+e.clientX-panStart.x;panY=panStart.py+e.clientY-panStart.y;render();}}}};svg.onpointerup=e=>{{dragNode=null;dragCategory=null;categoryDragStart=null;panStart=null;if(svg.hasPointerCapture(e.pointerId))svg.releasePointerCapture(e.pointerId);}};svg.onpointerleave=()=>{{if(!dragCategory){{dragNode=null;panStart=null;}}}};
svg.onwheel=e=>{{e.preventDefault();const r=svg.getBoundingClientRect(),mx=e.clientX-r.left,my=e.clientY-r.top,beforeX=(mx-panX)/scale,beforeY=(my-panY)/scale;scale=Math.max(.2,Math.min(4,scale*(e.deltaY<0?1.12:.89)));panX=mx-beforeX*scale;panY=my-beforeY*scale;render();}};
layout(true);renderCommitSummary();fitGraph();
</script></body></html>"""
    output_path.write_text(document, encoding="utf-8")
    return document
