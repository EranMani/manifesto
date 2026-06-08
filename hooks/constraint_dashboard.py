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


def badge(value: str, good: bool | None = None) -> str:
    if good is None:
        css = "neutral"
    else:
        css = "good" if good else "bad"
    return f'<span class="badge {css}">{html.escape(value)}</span>'


def metric_value(value: Any, suffix: str = "") -> str:
    if value is None:
        return "-"
    return f"{value}{suffix}"


def render_dashboard(
    repo_root: Path = REPO_ROOT,
    output_path: Path | None = None,
) -> str:
    output_path = output_path or repo_root / "constraint-dashboard.html"
    constraint_rows = parse_constraint_rows(repo_root / "CONSTRAINT_LOG.md")
    metrics = load_metrics(repo_root / "CONTEXT_METRICS.json").get("records", [])
    prepared = load_prepared_package(repo_root)

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
    expansion_free = sum(r.get("usage", {}).get("expansions", 0) == 0 for r in metrics)
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
            f"<td>{usage.get('searches', 0)}</td>"
            f"<td>{badge(str(usage.get('expansions', 0)), usage.get('expansions', 0) == 0)}</td>"
            f"<td>{badge('clean' if boundary.get('forbidden_clean') else 'violation', boundary.get('forbidden_clean'))}</td>"
            "</tr>"
        )
    if not metric_rows:
        metric_rows = (
            '<tr><td colspan="8" class="empty">Phase B measurements begin with the next '
            'verified live delegation.</td></tr>'
        )

    constraint_html = ""
    for row in constraint_rows:
        token = row[3] if row[3] not in {"-", "0"} else "-"
        constraint_html += (
            "<tr>"
            f"<td>{html.escape(row[0])}</td><td>{badge(row[1])}</td>"
            f"<td>{html.escape(row[2])}</td><td>{html.escape(token)}</td>"
            f"<td>{badge(row[4].split()[0].lower(), row[4].startswith('PASS'))}</td>"
            f"<td>{badge(row[5].split()[0].lower(), row[5].startswith('PASS'))}</td>"
            f"<td>{badge(row[6].split()[0].lower(), row[6].startswith('PASS'))}</td>"
            f"<td>{badge(row[7].lower(), row[7].startswith('PASS'))}</td>"
            "</tr>"
        )

    css = """
*{box-sizing:border-box}body{margin:0;background:#f4f7fb;color:#182235;font:14px/1.45 Inter,Segoe UI,sans-serif}
.container{max-width:1180px;margin:auto;padding:30px 22px 50px}h1{font-size:25px;margin:0}h2{font-size:17px;margin:0 0 3px}
.subtitle,.section-head p{color:#65738a;margin:4px 0 0}.cards{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin:24px 0}
.card,section{background:white;border:1px solid #dfe6ef;border-radius:12px;box-shadow:0 2px 9px #23395d0a}
.card{padding:14px}.card span,.prepared-grid span{display:block;color:#718096;font-size:11px;text-transform:uppercase;letter-spacing:.05em}
.card strong{display:block;font-size:24px;margin-top:5px}section{padding:18px;margin-bottom:18px}.section-head{display:flex;justify-content:space-between;align-items:start;margin-bottom:14px}
.prepared-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:1px;background:#e7edf4;border:1px solid #e7edf4;border-radius:9px;overflow:hidden}
.prepared-grid div{background:#f9fbfd;padding:12px}.prepared-grid strong{display:block;margin-top:4px;font-size:14px}
.table-wrap{overflow:auto;border:1px solid #e3e9f1;border-radius:9px}table{width:100%;border-collapse:collapse;white-space:nowrap}
th{background:#f7f9fc;color:#69778e;font-size:10px;text-transform:uppercase;letter-spacing:.06em;text-align:left;padding:10px 12px}
td{padding:10px 12px;border-top:1px solid #edf1f5}tr:hover td{background:#fafcff}.badge{display:inline-block;padding:2px 8px;border-radius:999px;background:#edf2f7;color:#455468;font-size:11px;font-weight:600}
.badge.good{background:#e8f7ef;color:#157347}.badge.bad{background:#fdebec;color:#b4232c}.empty{text-align:center;color:#7b8798;padding:24px}
.legend{color:#67758a;font-size:12px;margin-top:10px}@media(max-width:850px){.cards{grid-template-columns:repeat(2,1fr)}.prepared-grid{grid-template-columns:1fr}}
"""
    phase_cards = [
        ("Measured commits", measured),
        ("Avg package", f"{avg_package:,} chars" if avg_package is not None else "-"),
        ("Selected files used", f"{avg_use}%" if avg_use is not None else "-"),
        ("Expansion-free", f"{expansion_free}/{measured}" if measured else "-"),
        ("Boundary clean", f"{boundary_clean}/{measured}" if measured else "-"),
    ]
    cards_html = "".join(
        f'<div class="card"><span>{label}</span><strong>{value}</strong></div>'
        for label, value in phase_cards
    )
    last_date = constraint_rows[-1][0] if constraint_rows else "-"
    document = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Manifesto Measurement Dashboard</title><style>{css}</style></head><body><div class="container">
<h1>Manifesto Measurement Dashboard</h1>
<p class="subtitle">{total} constraint checks · {passed} passed · {failed} failed · avg {metric_value(avg_tokens)} tokens · updated {last_date}</p>
{prepared_html}
<section><div class="section-head"><div><h2>Phase B context efficiency</h2>
<p>Measures whether the prepared package was concise and sufficient.</p></div></div>
<div class="cards">{cards_html}</div>
<div class="table-wrap"><table><thead><tr><th>Commit</th><th>Agent</th><th>Tokens</th><th>Package</th>
<th>Selected used</th><th>Searches</th><th>Expansions</th><th>Boundary</th></tr></thead>
<tbody>{metric_rows}</tbody></table></div>
<p class="legend">Selected used = unique package files read. Expansion = unique paths read outside the package.</p></section>
<section><div class="section-head"><div><h2>Constraint history</h2>
<p>Existing checks for upfront context, forbidden paths, tool budget, and result.</p></div></div>
<div class="table-wrap"><table><thead><tr><th>Date</th><th>Commit</th><th>Agent</th><th>Tokens</th>
<th>Context</th><th>Forbidden</th><th>Budget</th><th>Result</th></tr></thead>
<tbody>{constraint_html}</tbody></table></div></section>
</div></body></html>"""
    output_path.write_text(document, encoding="utf-8")
    return document
