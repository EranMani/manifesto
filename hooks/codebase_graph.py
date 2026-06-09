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
JS_EXPORTED_FUNCTION = re.compile(
    r"""export\s+(?:default\s+)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)"""
)
JS_EXPORTED_INTERFACE = re.compile(
    r"""export\s+interface\s+([A-Za-z_$][\w$]*)"""
)
JS_HTTP_CALL = re.compile(
    r"""\.(get|post|put|patch|delete)\s*(?:<[^>]+>)?\s*\(\s*['"]([^'"]+)['"]"""
)


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


def _sentence(text: str, limit: int = 360) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1].rsplit(" ", 1)[0] + "…"


def _humanize_symbol(name: str) -> str:
    words = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", name).replace("_", " ")
    return words.lower()


def summarize_python(path: str, text: str) -> str:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return ""
    docstring = ast.get_docstring(tree)
    functions = [
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    classes = [
        node.name
        for node in tree.body
        if isinstance(node, ast.ClassDef)
    ]
    imports = {
        alias.name.split(".")[0]
        for node in tree.body
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imports.update(
        (node.module or "").split(".")[0]
        for node in tree.body
        if isinstance(node, ast.ImportFrom)
    )
    lowered_functions = {name.lower() for name in functions}
    details: list[str] = []

    password_helpers = {
        name for name in lowered_functions
        if "password" in name and ("hash" in name or "verify" in name)
    }
    token_helpers = {
        name for name in lowered_functions
        if "token" in name and any(verb in name for verb in ("create", "decode", "verify"))
    }
    if password_helpers:
        library = "bcrypt" if "bcrypt" in imports else "password hashing"
        details.append(f"Hashes and verifies passwords with {library}.")
    if token_helpers:
        library = "JWT" if "jwt" in imports or "jose" in imports else "access tokens"
        detail = f"Creates and validates {library} access tokens"
        if "settings" in text and "EXPIRE" in text:
            detail += " using configured expiry and signing settings"
        if "HTTP_401_UNAUTHORIZED" in text:
            detail += ", translating invalid or expired tokens into HTTP 401 responses"
        details.append(detail + ".")

    routes: list[str] = []
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call) or not isinstance(decorator.func, ast.Attribute):
                continue
            if decorator.func.attr not in {"get", "post", "put", "patch", "delete"}:
                continue
            route = ""
            if decorator.args and isinstance(decorator.args[0], ast.Constant):
                route = str(decorator.args[0].value)
            routes.append(f"{decorator.func.attr.upper()} {route}".strip())
    if routes:
        details.append(
            f"Defines FastAPI endpoint{'s' if len(routes) != 1 else ''} "
            f"{', '.join(routes[:4])}."
        )
        if (
            any("login" in route.lower() for route in routes)
            and "verify_password" in text
            and "create_access_token" in text
        ):
            user_scope = "active users" if "is_active" in text else "users"
            details.append(
                f"Authenticates {user_scope} by email and password, rejects invalid "
                "credentials, and returns a signed access token."
            )
        elif "select(" in text:
            operations = [
                verb
                for verb, marker in (
                    ("reads", "select("),
                    ("creates", ".add("),
                    ("updates", "update("),
                    ("deletes", "delete("),
                )
                if marker in text
            ]
            if operations:
                details.append(
                    "Handles database "
                    + ", ".join(operations)
                    + " for this API surface."
                )
    if "get_db" in lowered_functions and (
        "sqlalchemy" in imports or "AsyncSession" in text
    ):
        details.append(
            "Creates the async SQLAlchemy engine/session factory and exposes "
            "the request-scoped database dependency."
        )
    if classes and any(
        base_name in text
        for base_name in ("DeclarativeBase", "BaseModel", "SQLModel")
    ):
        if "mapped_column" in text or "Mapped[" in text:
            details.append(
                f"Defines persistent database model{'s' if len(classes) != 1 else ''} "
                f"{', '.join(classes[:4])}."
            )
        elif "BaseModel" in text:
            details.append(
                f"Defines validated request/response schema{'s' if len(classes) != 1 else ''} "
                f"{', '.join(classes[:4])}."
            )
        else:
            details.append(
                f"Defines data model infrastructure for {', '.join(classes[:4])}."
            )
    if docstring:
        details.insert(0, _sentence(docstring, 180))
    if not details and functions:
        named = ", ".join(_humanize_symbol(name) for name in functions[:5])
        details.append(f"Implements {named}.")
    if not details and classes:
        details.append(f"Defines {', '.join(classes[:5])}.")
    if not details:
        details.append(f"Python module for {Path(path).stem.replace('_', ' ')}.")
    return _sentence(" ".join(dict.fromkeys(details)))


def summarize_javascript(path: str, text: str) -> str:
    functions = JS_EXPORTED_FUNCTION.findall(text)
    interfaces = JS_EXPORTED_INTERFACE.findall(text)
    calls = JS_HTTP_CALL.findall(text)
    details: list[str] = []
    if calls:
        endpoints = ", ".join(f"{method.upper()} {route}" for method, route in calls[:4])
        details.append(f"Calls backend API endpoint{'s' if len(calls) != 1 else ''} {endpoints}.")
    if functions:
        details.append(
            "Exports "
            + ", ".join(_humanize_symbol(name) for name in functions[:5])
            + "."
        )
    if interfaces:
        details.append(f"Defines response/data contracts {', '.join(interfaces[:4])}.")
    is_component = re.search(
        r"\bfunction\s+[A-Z]\w*\s*\(|\bconst\s+[A-Z]\w*\s*=",
        text,
    )
    if "react-router" in text or "<Route" in text:
        route_paths = re.findall(r"""path\s*=\s*['"]([^'"]+)['"]""", text)
        details.append(
            "Defines application routing"
            + (f" for {', '.join(route_paths[:6])}" if route_paths else "")
            + "."
        )
    elif is_component:
        details.append("Implements a React UI component.")
    if not details:
        details.append(
            f"Frontend module for {Path(path).stem.replace('-', ' ').replace('_', ' ')}."
        )
    return _sentence(" ".join(dict.fromkeys(details)))


def summarize_file(path: str, text: str, category: str) -> str:
    suffix = Path(path).suffix.lower()
    if suffix == ".py":
        return summarize_python(path, text)
    if suffix in {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"}:
        return summarize_javascript(path, text)
    name = Path(path).name
    if name in {"pyproject.toml", "package.json"}:
        return f"Declares project metadata, runtime dependencies, and tool configuration for {path}."
    if name in {"docker-compose.yml", "docker-compose.yaml"}:
        return "Defines the local multi-service container stack, networking, volumes, and environment wiring."
    if name.lower() in {"dockerfile", "containerfile"}:
        return "Builds the application container image and defines its runtime environment."
    if name.startswith(".env"):
        return "Defines environment variables used to configure the application at runtime."
    return f"{category.title()} configuration or source file for {path}."


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
    summaries = {
        path: summarize_file(path, texts[path], categories[path])
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
        "summaries": summaries,
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
