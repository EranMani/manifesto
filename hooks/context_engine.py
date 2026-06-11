#!/usr/bin/env python3
"""Build an explainable, bounded context package for a Manifesto agent.

Phase A is shadow-only: this module reads repository metadata and source files,
but it does not modify prompts, commit specs, or agent runtime behavior.
"""

from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


PATH_TOKEN = re.compile(r"`([^`]+)`")
TABLE_FILE = re.compile(r"^\|\s*`([^`]+)`\s*\|\s*([^|]+)\|", re.MULTILINE)
TS_IMPORT = re.compile(
    r"(?:from\s+|import\s*\()\s*['\"](\.[^'\"]+)['\"]"
)


def normalize_repo_path(value: str) -> str:
    normalized = value.strip().replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def normalize_commit_number(value: str | int) -> str:
    raw = str(value).strip().upper()
    if raw.startswith("C"):
        raw = raw[1:]
    match = re.fullmatch(r"(\d+)([A-Z]?)", raw)
    if not match:
        raise ValueError(f"invalid commit identifier {value!r}")
    return f"{int(match.group(1)):02d}{match.group(2)}"


def safe_repo_path(repo_root: Path, relative: str) -> Path | None:
    normalized = normalize_repo_path(relative)
    parts = Path(normalized).parts
    if (
        not normalized
        or normalized.startswith("/")
        or re.match(r"^[A-Za-z]:", normalized)
        or ".." in parts
    ):
        return None
    candidate = (repo_root / normalized).resolve()
    try:
        candidate.relative_to(repo_root.resolve())
    except ValueError:
        return None
    return candidate


def _resolve_existing(repo_root: Path, relative: str) -> str | None:
    candidate = safe_repo_path(repo_root, relative)
    if candidate and candidate.is_file():
        return candidate.relative_to(repo_root).as_posix()
    return None


def _resolve_python_module(repo_root: Path, module: str) -> str | None:
    if module.startswith("app."):
        base = "backend/" + module.replace(".", "/")
    elif module == "app":
        base = "backend/app"
    else:
        return None
    for suffix in (".py", "/__init__.py"):
        found = _resolve_existing(repo_root, base + suffix)
        if found:
            return found
    return None


def python_imports(repo_root: Path, relative: str) -> set[str]:
    file_path = safe_repo_path(repo_root, relative)
    if not file_path or not file_path.is_file():
        return set()
    try:
        tree = ast.parse(file_path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, UnicodeDecodeError):
        return set()

    found: set[str] = set()
    for node in ast.walk(tree):
        modules: list[str] = []
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.append(node.module)
        for module in modules:
            resolved = _resolve_python_module(repo_root, module)
            if resolved:
                found.add(resolved)
    return found


def _resolve_ts_import(repo_root: Path, source: str, imported: str) -> str | None:
    source_path = safe_repo_path(repo_root, source)
    if not source_path:
        return None
    base = source_path.parent / imported
    candidates = [
        base,
        base.with_suffix(".ts"),
        base.with_suffix(".tsx"),
        base.with_suffix(".js"),
        base.with_suffix(".jsx"),
        base / "index.ts",
        base / "index.tsx",
    ]
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
            resolved.relative_to(repo_root.resolve())
        except ValueError:
            continue
        if resolved.is_file():
            return resolved.relative_to(repo_root).as_posix()
    return None


def typescript_imports(repo_root: Path, relative: str) -> set[str]:
    file_path = safe_repo_path(repo_root, relative)
    if not file_path or not file_path.is_file():
        return set()
    try:
        text = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return set()
    found: set[str] = set()
    for imported in TS_IMPORT.findall(text):
        resolved = _resolve_ts_import(repo_root, relative, imported)
        if resolved:
            found.add(resolved)
    return found


def build_dependency_graph(repo_root: Path, rules: dict[str, Any]) -> dict[str, set[str]]:
    graph: dict[str, set[str]] = {}
    ignored = set(rules.get("ignored_directories", []))
    for root_name in rules.get("source_roots", []):
        source_root = safe_repo_path(repo_root, root_name)
        if not source_root or not source_root.is_dir():
            continue
        for path in source_root.rglob("*"):
            if not path.is_file() or any(part in ignored for part in path.parts):
                continue
            relative = path.relative_to(repo_root).as_posix()
            if path.suffix == ".py":
                graph[relative] = python_imports(repo_root, relative)
            elif path.suffix in {".ts", ".tsx", ".js", ".jsx"}:
                graph[relative] = typescript_imports(repo_root, relative)
    return graph


def reverse_graph(graph: dict[str, set[str]]) -> dict[str, set[str]]:
    reverse: dict[str, set[str]] = {path: set() for path in graph}
    for source, imports in graph.items():
        for imported in imports:
            reverse.setdefault(imported, set()).add(source)
    return reverse


def _safe_graph_map(
    repo_root: Path,
    raw: Any,
) -> dict[str, set[str]] | None:
    if not isinstance(raw, dict):
        return None
    graph: dict[str, set[str]] = {}
    for source, targets in raw.items():
        if not isinstance(source, str) or not isinstance(targets, list):
            return None
        source = normalize_repo_path(source)
        if safe_repo_path(repo_root, source) is None:
            return None
        clean_targets: set[str] = set()
        for target in targets:
            if not isinstance(target, str):
                return None
            target = normalize_repo_path(target)
            if safe_repo_path(repo_root, target) is None:
                return None
            clean_targets.add(target)
        graph[source] = clean_targets
    return graph


def load_cached_codebase_graph(
    repo_root: Path,
    graph_path: Path,
) -> tuple[dict[str, set[str]], dict[str, set[str]], dict[str, str], list[dict[str, Any]], dict[str, Any]] | None:
    try:
        payload = json.loads(graph_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    if payload.get("schema_version") != 1:
        return None
    graph = _safe_graph_map(repo_root, payload.get("imports"))
    reverse = _safe_graph_map(repo_root, payload.get("imported_by"))
    categories = payload.get("categories")
    hubs = payload.get("hubs")
    if graph is None or reverse is None or not isinstance(categories, dict) or not isinstance(hubs, list):
        return None
    if not all(isinstance(path, str) and isinstance(category, str) for path, category in categories.items()):
        return None
    if not all(isinstance(hub, dict) and isinstance(hub.get("path"), str) for hub in hubs):
        return None
    metadata = {
        "source": "cache",
        "path": graph_path.relative_to(repo_root).as_posix()
        if graph_path.is_relative_to(repo_root)
        else str(graph_path),
        "source_fingerprint": payload.get("source_fingerprint"),
        "totals": payload.get("totals", {}),
    }
    return graph, reverse, categories, hubs, metadata


def _parse_list_block(spec: str, key: str) -> list[str]:
    match = re.search(
        rf"^[ \t]*{re.escape(key)}:[ \t]*(.*)$",
        spec,
        re.MULTILINE,
    )
    if not match:
        return []
    inline = match.group(1).strip()
    if inline.startswith("[]"):
        return []
    values: list[str] = []
    for line in spec[match.end():].splitlines():
        if line.strip() == "```" or re.match(r"^\s*\w+:", line):
            break
        item = re.match(r"^\s+-\s+([^#]+)", line)
        if item:
            token = item.group(1).strip()
            path_match = PATH_TOKEN.search(token)
            values.append(normalize_repo_path(path_match.group(1) if path_match else token))
    return values


def _parse_context_block(spec: str) -> dict[str, list[str]]:
    block_match = re.search(r"## context\s*```(.*?)```", spec, re.DOTALL | re.IGNORECASE)
    block = block_match.group(1) if block_match else ""
    initial_context = _parse_list_block(block, "initial_context")
    return {
        "tier0": initial_context or _parse_list_block(block, "tier0"),
        "tier1": _parse_list_block(block, "tier1"),
        "tier2": _parse_list_block(block, "tier2"),
        "forbidden": _parse_list_block(block, "forbidden"),
    }


def _parse_change_files(spec: str) -> list[str]:
    return [
        normalize_repo_path(path)
        for path, _kind in TABLE_FILE.findall(spec)
        if "/" in path or "." in Path(path).name
    ]


def infer_task_kind(spec: str, change_files: list[str]) -> str:
    heading = spec.splitlines()[0].lower() if spec else ""
    if "fix-" in heading or "bug" in heading:
        return "bugfix"
    if any("alembic" in path or "migration" in path for path in change_files):
        return "migration"
    if any("/tests/" in path or Path(path).name.startswith("test_") for path in change_files):
        return "implementation-with-tests"
    return "implementation"


def is_test_path(path: str) -> bool:
    normalized = normalize_repo_path(path).lower()
    name = Path(normalized).name
    return (
        "/tests/" in f"/{normalized}"
        or "/__tests__/" in f"/{normalized}"
        or name.startswith("test_")
        or ".test." in name
        or ".spec." in name
    )


def is_contract_path(path: str) -> bool:
    normalized = normalize_repo_path(path).lower()
    return (
        "/schemas/" in f"/{normalized}"
        or normalized.endswith("config.py")
        or normalized.endswith("pyproject.toml")
        or normalized.startswith("commit-specs/")
        or "manifesto-spec.md" in normalized
    )


@dataclass
class SelectedFile:
    path: str
    category: str
    reasons: list[str] = field(default_factory=list)
    exists: bool = False
    chars: int = 0


class ContextPackageBuilder:
    def __init__(
        self,
        repo_root: Path,
        rules: dict[str, Any],
        graph_path: Path | None = None,
        mode: str = "shadow",
    ) -> None:
        self.repo_root = repo_root.resolve()
        self.rules = rules
        self.mode = mode
        configured_path = rules.get("graph", {}).get(
            "cache_path",
            ".context/index/codebase-graph.json",
        )
        candidate = (graph_path or (self.repo_root / configured_path)).resolve()
        cached = load_cached_codebase_graph(self.repo_root, candidate)
        if cached:
            self.graph, self.reverse, self.categories, self.hubs, self.graph_metadata = cached
        else:
            self.graph = build_dependency_graph(self.repo_root, rules)
            self.reverse = reverse_graph(self.graph)
            self.categories = {}
            self.hubs = []
            self.graph_metadata = {
                "source": "fallback",
                "path": candidate.relative_to(self.repo_root).as_posix()
                if candidate.is_relative_to(self.repo_root)
                else str(candidate),
                "reason": "cache missing, invalid, or incompatible",
                "totals": {
                    "files": len(self.graph),
                    "edges": sum(len(targets) for targets in self.graph.values()),
                },
            }

    def _dependency_distance(
        self,
        start: str,
        target: str,
        max_distance: int,
    ) -> int | None:
        if start == target:
            return 0
        visited = {start}
        frontier = {start}
        for distance in range(1, max_distance + 1):
            next_frontier: set[str] = set()
            for node in frontier:
                next_frontier.update(self.graph.get(node, set()))
            next_frontier -= visited
            if target in next_frontier:
                return distance
            if not next_frontier:
                return None
            visited.update(next_frontier)
            frontier = next_frontier
        return None

    def _add(
        self,
        selected: dict[str, SelectedFile],
        path: str,
        category: str,
        reason: str,
    ) -> None:
        normalized = normalize_repo_path(path)
        normalized = self.rules.get("path_aliases", {}).get(normalized, normalized)
        if not normalized or safe_repo_path(self.repo_root, normalized) is None:
            return
        current = selected.get(normalized)
        if current:
            if reason not in current.reasons:
                current.reasons.append(reason)
            priority = {
                "primary": 0,
                "identity": 1,
                "worklog": 1,
                "contract": 2,
                "test": 3,
                "structural": 4,
                "dependency": 5,
                "hub": 6,
            }
            if priority.get(category, 9) < priority.get(current.category, 9):
                current.category = category
            return
        absolute = safe_repo_path(self.repo_root, normalized)
        exists = bool(absolute and absolute.is_file())
        chars = absolute.stat().st_size if exists and absolute else 0
        if exists and absolute and category == "worklog":
            try:
                chars = len(
                    "\n".join(
                        absolute.read_text(encoding="utf-8").splitlines()[:50]
                    )
                )
            except (OSError, UnicodeDecodeError):
                chars = 0
        selected[normalized] = SelectedFile(
            path=normalized,
            category=category,
            reasons=[reason],
            exists=exists,
            chars=chars,
        )

    def build(self, commit: str, agent: str) -> dict[str, Any]:
        commit_number = normalize_commit_number(commit)
        spec_path = (
            self.repo_root
            / "commit-specs"
            / f"commit-{commit_number.lower()}.md"
        )
        if not spec_path.is_file():
            raise FileNotFoundError(f"Commit spec not found: {spec_path}")
        spec = spec_path.read_text(encoding="utf-8")
        context = _parse_context_block(spec)
        change_files = _parse_change_files(spec)
        selected: dict[str, SelectedFile] = {}

        for path in context["tier0"]:
            self._add(selected, path.split(" (", 1)[0], "identity", "commit spec tier0")

        agent_rules = self.rules.get("agents", {}).get(agent, {})
        worklog = agent_rules.get("worklog")
        if worklog:
            self._add(
                selected,
                worklog,
                "worklog",
                "current state header only (first 50 lines)",
            )

        for path in change_files:
            category = "test" if is_test_path(path) else "primary"
            self._add(selected, path, category, "commit spec change table")

        for path in context["tier1"]:
            clean = path.split(" (", 1)[0]
            if clean in change_files:
                category = "test" if is_test_path(clean) else "primary"
            elif is_test_path(clean):
                category = "test"
            elif is_contract_path(clean):
                category = "contract"
            else:
                category = "contract"
            self._add(selected, clean, category, "commit spec tier1")

        for path in context["tier2"]:
            clean = path.split(" (", 1)[0]
            self._add(selected, clean, "contract", "commit spec tier2")

        anchors = [
            path for path, item in selected.items()
            if item.category == "primary"
        ]
        for prefix, structural_paths in agent_rules.get("structural_by_area", {}).items():
            if any(path.startswith(prefix) for path in anchors):
                for path in structural_paths:
                    self._add(selected, path, "structural", f"structural anchor for {prefix}")

        for bridge in self.rules.get("contract_bridges", []):
            triggers = bridge.get("when_any", [])
            if any(trigger in selected for trigger in triggers):
                for path in bridge.get("include", []):
                    self._add(
                        selected,
                        path,
                        "contract",
                        f"cross-domain bridge: {bridge.get('name', 'unnamed')}",
                    )

        explicit_change_context = any(
            path.split(" (", 1)[0] in change_files
            for path in context["tier0"]
        )
        expansion_anchors = [] if explicit_change_context else [
            path for path, item in selected.items()
            if item.category == "primary" and path in self.graph
        ]
        for anchor in expansion_anchors:
            for imported in sorted(self.graph.get(anchor, set())):
                self._add(selected, imported, "dependency", f"imported by {anchor}")
            for importer in sorted(self.reverse.get(anchor, set())):
                self._add(selected, importer, "dependency", f"imports {anchor}")

        graph_rules = self.rules.get("graph", {})
        allowed_categories = set(
            graph_rules.get("agent_categories", {}).get(agent, [])
        )
        max_hubs = int(graph_rules.get("max_hubs_per_package", 0))
        max_distance = int(graph_rules.get("max_hub_distance", 2))
        max_files = int(self.rules.get("budget", {}).get("max_files", 12))
        available_slots = max(0, max_files - len(selected))
        added_hubs = 0
        for hub in self.hubs:
            hub_path = normalize_repo_path(str(hub.get("path", "")))
            if not hub_path:
                continue
            if allowed_categories and hub.get("category") not in allowed_categories:
                continue
            distances = [
                distance
                for anchor in expansion_anchors
                if (
                    distance := self._dependency_distance(
                        anchor,
                        hub_path,
                        max_distance,
                    )
                ) is not None
            ]
            if not distances:
                continue
            was_selected = hub_path in selected
            if not was_selected and added_hubs >= min(max_hubs, available_slots):
                continue
            self._add(
                selected,
                hub_path,
                "hub",
                f"nearby {hub.get('category', 'domain')} hub at distance {min(distances)}",
            )
            if not was_selected:
                added_hubs += 1

        unresolved: list[dict[str, str]] = []
        for path, item in selected.items():
            if (
                not item.exists
                and item.category != "test"
                and path not in change_files
            ):
                unresolved.append({"path": path, "reason": "selected file does not exist yet"})

        budget = self.rules.get("budget", {})
        max_files = int(budget.get("max_files", 12))
        max_chars_per_file = int(budget.get("max_chars_per_file", 6000))
        usable_chars = int(budget.get("max_total_chars", 30000)) - int(
            budget.get("reserve_chars", 6000)
        )
        priority = {
            "primary": 0,
            "identity": 1,
            "worklog": 1,
            "contract": 2,
            "test": 3,
            "structural": 4,
            "dependency": 5,
            "hub": 6,
        }
        ordered = sorted(
            selected.values(),
            key=lambda item: (priority.get(item.category, 9), item.path),
        )

        included: list[dict[str, Any]] = []
        excluded: list[dict[str, Any]] = []
        used_chars = 0
        for item in ordered:
            charged = min(item.chars, max_chars_per_file) if item.exists else 0
            record = {
                "path": item.path,
                "category": item.category,
                "reasons": item.reasons,
                "exists": item.exists,
                "estimated_chars": charged,
                "read_strategy": (
                    "first 50 lines only"
                    if item.category == "worklog"
                    else f"targeted excerpt; source exceeds {max_chars_per_file} characters"
                    if item.exists and item.chars > max_chars_per_file
                    else "full file"
                ),
            }
            if len(included) >= max_files or used_chars + charged > usable_chars:
                record["excluded_reason"] = "context budget"
                excluded.append(record)
                continue
            included.append(record)
            used_chars += charged

        missing_contract = not any(
            item["category"] == "contract" and item["exists"] for item in included
        )
        expansion_triggers: list[str] = []
        if missing_contract:
            expansion_triggers.append("no existing authoritative contract selected")
        if unresolved:
            expansion_triggers.append("one or more selected files do not exist yet")
        if excluded:
            expansion_triggers.append("candidate files excluded by context budget")

        return {
            "schema_version": 2,
            "mode": self.mode,
            "commit": f"C{commit_number}",
            "agent": agent,
            "task_kind": infer_task_kind(spec, change_files),
            "spec": spec_path.relative_to(self.repo_root).as_posix(),
            "graph": self.graph_metadata,
            "files": included,
            "excluded_candidates": excluded,
            "forbidden_edits": context["forbidden"],
            "unresolved": unresolved,
            "expansion_triggers": expansion_triggers,
            "budget": {
                **budget,
                "usable_chars_before_reserve": usable_chars,
                "selected_files": len(included),
                "estimated_selected_chars": used_chars,
            },
        }


def load_rules(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))
