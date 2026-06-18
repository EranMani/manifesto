#!/usr/bin/env python3
"""
forge_scan.py — Codebase graph-RAG scanner for the /forge command.

Walks the repository, categorizes every file into domains (backend, frontend,
devops, ai, tests, docs, config), builds a within-repo import graph, identifies
hub files (high connectivity), and maps each file to its owning agent via
agent-config.json.

Pure deterministic analysis — no LLM calls.

Usage:
    python hooks/forge_scan.py [--path .] [--out .forge/]
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parent.parent

EXCLUDED_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", "env",
    "dist", "build", ".next", ".nuxt", ".pytest_cache", ".mypy_cache",
    ".ruff_cache", "htmlcov", ".context", ".claude", "claude_usage_data",
    ".forge",
}

EXCLUDED_EXTENSIONS = {
    ".pyc", ".pyo", ".pyd", ".egg", ".whl", ".so", ".dll",
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".woff", ".woff2",
    ".ttf", ".eot", ".mp3", ".mp4", ".zip", ".tar", ".gz",
    ".lock", ".log",
}


# ---------------------------------------------------------------------------
# File categorization rules (priority: path → extension → content)
# ---------------------------------------------------------------------------

PATH_CATEGORY_RULES: list[tuple[str, str]] = [
    ("backend/app/services/llm.py", "ai"),
    ("backend/app/services/rag_policy.py", "ai"),
    ("backend/app/services/rag_logistics.py", "ai"),
    ("backend/app/services/ingestion.py", "ai"),
    ("backend/tests/services/", "ai"),
    ("backend/app/", "backend"),
    ("backend/alembic/", "backend"),
    ("backend/seed.py", "backend"),
    ("backend/tests/", "backend"),
    ("frontend/src/", "frontend"),
    ("frontend/index.html", "frontend"),
    ("scripts/", "devops"),
    ("hooks/", "devops"),
    ("docker-compose", "devops"),
    ("Dockerfile", "devops"),
    (".env", "config"),
    ("commit-specs/", "docs"),
    ("CLAUDE.md", "docs"),
    ("ORCHESTRATION.md", "docs"),
    ("AGENTS.md", "docs"),
    ("DECISIONS.md", "docs"),
    ("ARCHITECTURE.md", "docs"),
    ("README.md", "docs"),
]

EXTENSION_CATEGORY_MAP: dict[str, str] = {
    ".py": "backend",
    ".tsx": "frontend",
    ".ts": "frontend",
    ".css": "frontend",
    ".jsx": "frontend",
    ".html": "frontend",
    ".yml": "config",
    ".yaml": "config",
    ".toml": "config",
    ".json": "config",
    ".ini": "config",
    ".md": "docs",
}

CONTENT_CATEGORY_MARKERS: list[tuple[str, str]] = [
    ("from langchain", "ai"),
    ("from langgraph", "ai"),
    ("import openai", "ai"),
    ("from openai", "ai"),
    ("EmbeddingService", "ai"),
    ("LLMService", "ai"),
    ("from fastapi", "backend"),
    ("from sqlalchemy", "backend"),
    ("import React", "frontend"),
    ("from react", "frontend"),
]


def _gitignored_paths(repo_root: Path) -> set[str]:
    """Get paths ignored by git (cheap — delegates to git)."""
    try:
        result = subprocess.run(
            ["git", "ls-files", "--others", "--ignored", "--exclude-standard",
             "--directory"],
            capture_output=True, text=True, cwd=str(repo_root), timeout=10,
        )
        return {line.rstrip("/") for line in result.stdout.splitlines() if line.strip()}
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return set()


def walk_files(repo_root: Path) -> list[Path]:
    """Walk the repo tree, excluding build artifacts and binary files."""
    files: list[Path] = []
    gitignored = _gitignored_paths(repo_root)

    for item in repo_root.rglob("*"):
        try:
            rel = item.relative_to(repo_root)
        except ValueError:
            continue

        parts = rel.parts
        if any(part in EXCLUDED_DIRS for part in parts):
            continue

        try:
            if not item.is_file():
                continue
        except OSError:
            continue

        rel_str = str(rel).replace("\\", "/")
        if any(rel_str.startswith(gi.rstrip("/")) for gi in gitignored if gi):
            continue

        if item.suffix.lower() in EXCLUDED_EXTENSIONS:
            continue

        files.append(item)

    return files


def categorize_file(file_path: Path, repo_root: Path) -> str:
    """Assign a category to a file using path → extension → content priority."""
    rel = str(file_path.relative_to(repo_root)).replace("\\", "/")

    for pattern, category in PATH_CATEGORY_RULES:
        if rel == pattern or rel.startswith(pattern):
            return category

    ext = file_path.suffix.lower()
    if ext in EXTENSION_CATEGORY_MAP:
        return EXTENSION_CATEGORY_MAP[ext]

    try:
        head = file_path.read_text(encoding="utf-8", errors="ignore")[:2000]
        for marker, category in CONTENT_CATEGORY_MARKERS:
            if marker in head:
                return category
    except OSError:
        pass

    return "other"


# ---------------------------------------------------------------------------
# Import graph construction
# ---------------------------------------------------------------------------

def get_python_imports(file_path: Path) -> list[str]:
    """Extract import targets from a Python file."""
    try:
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except (SyntaxError, UnicodeDecodeError, OSError):
        return []

    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
    return imports


def get_ts_imports(file_path: Path) -> list[str]:
    """Extract import paths from a TypeScript/TSX file."""
    try:
        content = file_path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return []

    pattern = re.compile(r"""(?:from|import)\s+['"]([^'"]+)['"]""")
    return pattern.findall(content)


def _resolve_python_import(module: str, repo_root: Path) -> str | None:
    """Try to resolve a Python import to a repo-relative file path."""
    parts = module.replace(".", "/")
    for suffix in [".py", "/__init__.py"]:
        candidate = repo_root / "backend" / parts.replace("app/", "app/", 1)
        if not str(candidate).endswith(suffix):
            candidate = Path(str(candidate) + suffix)
        # Try direct mapping: app.services.llm → backend/app/services/llm.py
        direct = repo_root / "backend" / (parts + ".py")
        if direct.exists():
            return str(direct.relative_to(repo_root)).replace("\\", "/")
        pkg = repo_root / "backend" / parts / "__init__.py"
        if pkg.exists():
            return str(pkg.parent.relative_to(repo_root)).replace("\\", "/")
    return None


def _resolve_ts_import(import_path: str, source_file: Path, repo_root: Path) -> str | None:
    """Try to resolve a TS/TSX import to a repo-relative file path."""
    if not import_path.startswith("."):
        return None

    source_dir = source_file.parent
    resolved = (source_dir / import_path).resolve()

    for ext in ["", ".ts", ".tsx", "/index.ts", "/index.tsx"]:
        candidate = Path(str(resolved) + ext)
        if candidate.exists():
            try:
                return str(candidate.relative_to(repo_root)).replace("\\", "/")
            except ValueError:
                return None
    return None


def build_import_graph(
    files: list[Path], repo_root: Path
) -> dict[str, dict[str, list[str]]]:
    """Build a bidirectional import graph for all source files."""
    graph: dict[str, dict[str, list[str]]] = {}
    reverse: dict[str, list[str]] = defaultdict(list)

    for f in files:
        rel = str(f.relative_to(repo_root)).replace("\\", "/")

        if f.suffix == ".py":
            raw_imports = get_python_imports(f)
            resolved = []
            for imp in raw_imports:
                target = _resolve_python_import(imp, repo_root)
                if target:
                    resolved.append(target)
                    reverse[target].append(rel)
            graph[rel] = {"imports": resolved, "imported_by": []}

        elif f.suffix in (".ts", ".tsx"):
            raw_imports = get_ts_imports(f)
            resolved = []
            for imp in raw_imports:
                target = _resolve_ts_import(imp, f, repo_root)
                if target:
                    resolved.append(target)
                    reverse[target].append(rel)
            graph[rel] = {"imports": resolved, "imported_by": []}

    for target, importers in reverse.items():
        if target in graph:
            graph[target]["imported_by"] = sorted(set(importers))
        else:
            graph[target] = {"imports": [], "imported_by": sorted(set(importers))}

    return graph


# ---------------------------------------------------------------------------
# Hub detection
# ---------------------------------------------------------------------------

def find_hubs(
    graph: dict[str, dict[str, list[str]]],
    in_degree_threshold: int = 5,
    out_degree_threshold: int = 10,
) -> list[dict[str, Any]]:
    """Identify hub files — high in-degree or out-degree in the import graph."""
    hubs: list[dict[str, Any]] = []
    for path, edges in graph.items():
        in_deg = len(edges.get("imported_by", []))
        out_deg = len(edges.get("imports", []))
        if in_deg >= in_degree_threshold or out_deg >= out_degree_threshold:
            hubs.append({
                "path": path,
                "in_degree": in_deg,
                "out_degree": out_deg,
            })
    return sorted(hubs, key=lambda h: -(h["in_degree"] + h["out_degree"]))


# ---------------------------------------------------------------------------
# Domain ownership mapping
# ---------------------------------------------------------------------------

def load_agent_config(repo_root: Path) -> dict[str, Any]:
    """Load hooks/agent-config.json."""
    config_path = repo_root / "hooks" / "agent-config.json"
    if not config_path.exists():
        return {}
    return json.loads(config_path.read_text(encoding="utf-8"))


def map_file_to_owner(
    file_rel: str, agent_config: dict[str, Any]
) -> str | None:
    """Determine which agent owns a file based on agent-config.json domains."""
    agents = agent_config.get("agents", {})
    best_match: tuple[str, int] = ("", 0)

    for email, info in agents.items():
        name = info.get("name", "").lower()
        domains = info.get("domains", [])
        for domain in domains:
            if file_rel == domain or file_rel.startswith(domain):
                match_len = len(domain)
                if match_len > best_match[1]:
                    best_match = (name, match_len)

    return best_match[0] if best_match[0] else None


# ---------------------------------------------------------------------------
# Main scan pipeline
# ---------------------------------------------------------------------------

def scan(repo_root: Path) -> dict[str, Any]:
    """Run the full codebase scan and return the report dict."""
    files = walk_files(repo_root)

    categories: dict[str, list[str]] = defaultdict(list)
    for f in files:
        cat = categorize_file(f, repo_root)
        rel = str(f.relative_to(repo_root)).replace("\\", "/")
        categories[cat].append(rel)

    for cat in categories:
        categories[cat].sort()

    source_files = [
        f for f in files
        if f.suffix in (".py", ".ts", ".tsx")
    ]
    call_tree = build_import_graph(source_files, repo_root)
    hubs = find_hubs(call_tree)

    agent_config = load_agent_config(repo_root)
    domain_ownership: dict[str, str] = {}
    for cat_files in categories.values():
        for file_rel in cat_files:
            owner = map_file_to_owner(file_rel, agent_config)
            if owner:
                domain_ownership[file_rel] = owner

    file_count = len(files)
    category_summary = {cat: len(fs) for cat, fs in sorted(categories.items())}

    return {
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "repo_root": str(repo_root),
        "file_count": file_count,
        "category_summary": category_summary,
        "categories": dict(sorted(categories.items())),
        "call_tree": {k: call_tree[k] for k in sorted(call_tree)},
        "hubs": hubs,
        "domain_ownership": dict(sorted(domain_ownership.items())),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Forge codebase scanner")
    parser.add_argument("--path", default=".", help="Repository root path")
    parser.add_argument("--out", default=".forge", help="Output directory")
    parser.add_argument("--json", action="store_true", help="Print JSON to stdout")
    args = parser.parse_args()

    repo_root = Path(args.path).resolve()
    if not (repo_root / ".git").exists():
        print("ERROR: not a git repository", file=sys.stderr)
        return 1

    report = scan(repo_root)

    if args.json:
        print(json.dumps(report, indent=2))
        return 0

    out_dir = repo_root / args.out
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "report.json"
    out_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    hub_count = len(report["hubs"])
    file_count = report["file_count"]
    cat_count = len(report["categories"])
    print(
        f"Scanned {file_count} files, {cat_count} categories, "
        f"{hub_count} hubs. Report: {out_path}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
