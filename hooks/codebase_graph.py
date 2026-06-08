#!/usr/bin/env python3
"""Build a deterministic, repository-wide structural graph.

The scanner adapts the useful deterministic pieces of Skillsmith's archaeology
pipeline: tiered file classification, resolved import edges, reverse edges, and
global plus domain-scoped hub scores. Rendering is intentionally left to
downstream tools such as Obsidian.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import posixpath
import re
from collections import defaultdict
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1
SOURCE_EXTENSIONS = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs",
}
CONFIG_EXTENSIONS = {".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf"}
NAMED_FILES = {
    "dockerfile",
    "containerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    "compose.yml",
    "compose.yaml",
    "package.json",
    "package-lock.json",
    "tsconfig.json",
    "vite.config.ts",
    "tailwind.config.ts",
}
JS_IMPORT = re.compile(
    r"""(?:import|export)\s+(?:[\w*\s{},]*\s+from\s+)?['"]([^'"]+)['"]"""
)
JS_REQUIRE = re.compile(r"""require\s*\(\s*['"]([^'"]+)['"]\s*\)""")
JS_DYNAMIC_IMPORT = re.compile(r"""import\s*\(\s*['"]([^'"]+)['"]\s*\)""")


def normalize_path(path: str) -> str:
    return path.replace("\\", "/").strip("/")


def should_index(path: Path) -> bool:
    name = path.name.lower()
    return (
        path.suffix.lower() in SOURCE_EXTENSIONS | CONFIG_EXTENSIONS
        or name in NAMED_FILES
        or name == ".env"
        or name.startswith(".env.")
    )


def walk_files(repo_root: Path, ignored: set[str]) -> list[tuple[str, Path]]:
    files: list[tuple[str, Path]] = []
    for directory, dirnames, filenames in os.walk(repo_root):
        dirnames[:] = [
            name
            for name in dirnames
            if name not in ignored and not name.startswith(".")
        ]
        for name in filenames:
            absolute = Path(directory) / name
            if should_index(absolute):
                files.append((absolute.relative_to(repo_root).as_posix(), absolute))
    return sorted(files)


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def classify_file(path: str, text: str) -> str:
    normalized = normalize_path(path).lower()
    name = Path(normalized).name
    if (
        "/tests/" in f"/{normalized}"
        or "/__tests__/" in f"/{normalized}"
        or name.startswith("test_")
        or ".test." in name
        or ".spec." in name
    ):
        return "tests"
    if normalized.startswith("frontend/"):
        return "frontend"
    if normalized.startswith(("scripts/", ".github/", "infra/", "k8s/", "terraform/")):
        return "devops"
    if name in NAMED_FILES or normalized.startswith(".env"):
        return "devops" if "docker" in name or "compose" in name else "config"
    if normalized.endswith(tuple(CONFIG_EXTENSIONS)):
        return "config"
    if normalized.startswith(("docs/", "commit-specs/")):
        return "docs"
    if normalized.startswith("backend/"):
        ai_tokens = (
            "/services/llm",
            "/services/rag_",
            "/services/ingestion",
            "/embedding",
            "/retrieval",
        )
        ai_imports = ("openai", "anthropic", "langchain", "ollama", "pgvector")
        if any(token in normalized for token in ai_tokens) or any(
            token in text.lower() for token in ai_imports
        ):
            return "ai"
        return "backend"
    return "backend"


def _register(index: dict[str, str], alias: str, path: str) -> None:
    alias = normalize_path(alias)
    if alias and alias not in index:
        index[alias] = path


def build_import_index(
    files: list[tuple[str, Path]],
    python_import_roots: list[str],
) -> dict[str, str]:
    index: dict[str, str] = {}
    for relative, _absolute in files:
        normalized = normalize_path(relative)
        _register(index, normalized, normalized)
        if normalized.endswith(".py"):
            stem = normalized[:-3]
            _register(index, stem, normalized)
            _register(index, stem.replace("/", "."), normalized)
            if stem.endswith("/__init__"):
                package = stem[: -len("/__init__")]
                _register(index, package, normalized)
                _register(index, package.replace("/", "."), normalized)
            for root in python_import_roots:
                prefix = normalize_path(root) + "/"
                if stem.startswith(prefix):
                    stripped = stem[len(prefix):]
                    _register(index, stripped, normalized)
                    _register(index, stripped.replace("/", "."), normalized)
        elif Path(normalized).suffix.lower() in SOURCE_EXTENSIONS:
            stem = normalized[: normalized.rfind(".")]
            _register(index, stem, normalized)
            if stem.endswith("/index"):
                _register(index, stem[: -len("/index")], normalized)
    return index


def _python_refs(text: str) -> list[tuple[str, int]]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    refs: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            refs.extend((alias.name, 0) for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            refs.append((node.module or "", node.level))
    return refs


def _lookup_python(index: dict[str, str], module: str) -> str | None:
    candidates = [module, module.replace(".", "/")]
    slash = module.replace(".", "/")
    candidates.extend([f"{slash}.py", f"{slash}/__init__.py"])
    for candidate in candidates:
        if candidate in index:
            return index[candidate]
    return None


def resolve_python_import(
    source: str,
    module: str,
    level: int,
    index: dict[str, str],
) -> str | None:
    if level:
        source_parts = normalize_path(source[:-3]).split("/")[:-1]
        climb = max(level - 1, 0)
        if climb > len(source_parts):
            return None
        base = source_parts[: len(source_parts) - climb]
        if module:
            base.extend(module.split("."))
        module = "/".join(base)
    return _lookup_python(index, module)


def _js_refs(text: str) -> list[str]:
    return list(dict.fromkeys(
        JS_IMPORT.findall(text)
        + JS_REQUIRE.findall(text)
        + JS_DYNAMIC_IMPORT.findall(text)
    ))


def resolve_js_import(source: str, reference: str, index: dict[str, str]) -> str | None:
    if not reference.startswith("."):
        return index.get(reference)
    parent = Path(normalize_path(source)).parent
    normalized = normalize_path(posixpath.normpath((parent / reference).as_posix()))
    candidates = [
        normalized,
        f"{normalized}.ts",
        f"{normalized}.tsx",
        f"{normalized}.js",
        f"{normalized}.jsx",
        f"{normalized}/index.ts",
        f"{normalized}/index.tsx",
    ]
    for candidate in candidates:
        if candidate in index:
            return index[candidate]
    return None


def source_fingerprint(files: list[tuple[str, Path]]) -> str:
    digest = hashlib.sha256()
    for relative, absolute in files:
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        try:
            digest.update(absolute.read_bytes())
        except OSError:
            pass
        digest.update(b"\0")
    return digest.hexdigest()


def graph_cache_is_stale(
    repo_root: Path,
    rules: dict[str, Any],
    graph_path: Path,
) -> bool:
    if not graph_path.is_file():
        return True
    try:
        cache_mtime = graph_path.stat().st_mtime_ns
    except OSError:
        return True
    ignored = set(rules.get("ignored_directories", []))
    ignored.update({".archaeology", ".context", ".pytest_cache", ".mypy_cache"})
    for _relative, absolute in walk_files(repo_root.resolve(), ignored):
        try:
            if absolute.stat().st_mtime_ns > cache_mtime:
                return True
        except OSError:
            return True
    return False


def build_codebase_graph(repo_root: Path, rules: dict[str, Any]) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    graph_rules = rules.get("graph", {})
    ignored = set(rules.get("ignored_directories", []))
    ignored.update({".archaeology", ".context", ".pytest_cache", ".mypy_cache"})
    files = walk_files(repo_root, ignored)
    texts = {path: read_text(absolute) for path, absolute in files}
    categories = {
        path: classify_file(path, texts[path])
        for path, _absolute in files
    }
    index = build_import_index(
        files,
        graph_rules.get("python_import_roots", ["backend", "src"]),
    )

    imports: dict[str, set[str]] = {path: set() for path, _absolute in files}
    for path, _absolute in files:
        text = texts[path]
        if path.endswith(".py"):
            for module, level in _python_refs(text):
                target = resolve_python_import(path, module, level, index)
                if target and target != path:
                    imports[path].add(target)
        elif Path(path).suffix.lower() in {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"}:
            for reference in _js_refs(text):
                target = resolve_js_import(path, reference, index)
                if target and target != path:
                    imports[path].add(target)

    reverse: dict[str, set[str]] = {path: set() for path in imports}
    for source, targets in imports.items():
        for target in targets:
            reverse.setdefault(target, set()).add(source)

    domain_in_degree: dict[str, int] = defaultdict(int)
    for source, targets in imports.items():
        source_category = categories.get(source, "unclassified")
        for target in targets:
            if categories.get(target) == source_category:
                domain_in_degree[target] += 1

    hub_threshold = int(graph_rules.get("hub_min_in_degree", 2))
    hubs = []
    for path in imports:
        in_degree = len(reverse.get(path, set()))
        domain_degree = domain_in_degree.get(path, 0)
        if in_degree >= hub_threshold or domain_degree >= hub_threshold:
            hubs.append({
                "path": path,
                "category": categories.get(path, "unclassified"),
                "in_degree": in_degree,
                "domain_in_degree": domain_degree,
                "out_degree": len(imports[path]),
            })
    hubs.sort(
        key=lambda item: (
            -item["domain_in_degree"],
            -item["in_degree"],
            -item["out_degree"],
            item["path"],
        )
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "source_fingerprint": source_fingerprint(files),
        "totals": {
            "files": len(files),
            "edges": sum(len(targets) for targets in imports.values()),
            "hubs": len(hubs),
        },
        "categories": categories,
        "imports": {
            path: sorted(targets)
            for path, targets in sorted(imports.items())
        },
        "imported_by": {
            path: sorted(sources)
            for path, sources in sorted(reverse.items())
        },
        "hubs": hubs,
    }


def write_codebase_graph(
    repo_root: Path,
    rules: dict[str, Any],
    output: Path,
) -> dict[str, Any]:
    graph = build_codebase_graph(repo_root, rules)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(graph, indent=2) + "\n", encoding="utf-8")
    return graph
