#!/usr/bin/env python3
"""Reusable assertion helpers for /ask evaluation harness.

Provides deterministic checks on /ask command text output: forbidden
term detection, question bank validation, section parsing, placeholder
detection, and pipeline stage labeling.

Persona rules are parsed dynamically from .claude/personas/*.json at
test time so tests stay in sync with persona changes automatically.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PERSONAS_DIR = REPO_ROOT / ".claude" / "personas"
FRONTEND_PAGES_DIR = REPO_ROOT / "frontend" / "src" / "pages"


# ---------------------------------------------------------------------------
# Persona loading
# ---------------------------------------------------------------------------

def load_persona(name: str) -> dict:
    """Load a persona JSON file by name (e.g., 'founder', 'engineer')."""
    path = PERSONAS_DIR / f"{name}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def extract_forbidden_terms(persona: dict) -> list[str]:
    """Extract forbidden terms from a persona's prompt rules.

    Parses lines containing 'no ', 'never ', 'not ', followed by quoted
    terms or known jargon patterns.
    """
    terms: list[str] = []
    prompt_text = "\n".join(persona.get("prompt", []))

    single_quoted = re.findall(r"'([^']+)'", prompt_text)
    for term in single_quoted:
        if "→" not in term and len(term) < 40:
            terms.append(term)

    no_patterns = re.findall(
        r"(?:no |never use |never mention |never include |never list )"
        r"['\"]?([^'\",.;:\n]+)",
        prompt_text,
        re.IGNORECASE,
    )
    for match in no_patterns:
        cleaned = match.strip().strip("'\"")
        if len(cleaned) < 40 and cleaned:
            terms.append(cleaned)

    return list(set(terms))


def get_evergreen_questions(persona: dict) -> list[str]:
    """Return the persona's evergreen question list."""
    return persona.get("questions", {}).get("evergreen", [])


# ---------------------------------------------------------------------------
# Placeholder detection
# ---------------------------------------------------------------------------

def detect_placeholder_pages() -> list[str]:
    """Scan frontend pages for placeholder patterns ('Coming soon', etc.).

    Returns list of page names (without extension) that are placeholders.
    """
    placeholders: list[str] = []
    if not FRONTEND_PAGES_DIR.exists():
        return placeholders

    placeholder_patterns = [
        "coming soon",
        "under construction",
        "todo",
        "placeholder",
    ]

    for page_file in FRONTEND_PAGES_DIR.glob("*.tsx"):
        content = page_file.read_text(encoding="utf-8").lower()
        for pattern in placeholder_patterns:
            if pattern in content:
                placeholders.append(page_file.stem)
                break

    return placeholders


# ---------------------------------------------------------------------------
# Text assertions
# ---------------------------------------------------------------------------

def assert_no_forbidden_terms(text: str, terms: list[str]) -> list[str]:
    """Check that none of the forbidden terms appear in the text.

    Returns list of violations (empty = pass). Case-insensitive word
    boundary matching to avoid false positives (e.g., 'migration' in
    'immigration' should not match).
    """
    violations: list[str] = []
    text_lower = text.lower()
    for term in terms:
        term_lower = term.lower()
        pattern = r"\b" + re.escape(term_lower) + r"\b"
        if re.search(pattern, text_lower):
            violations.append(term)
    return violations


def assert_has_questions(text: str, min_count: int = 5) -> tuple[bool, int]:
    """Check that the text contains at least min_count numbered questions.

    Looks for patterns like '1. ', '2. ', etc. at the start of lines.
    Returns (passed, count_found).
    """
    numbered = re.findall(r"^\s*\d+\.\s+\S", text, re.MULTILINE)
    return len(numbered) >= min_count, len(numbered)


def assert_questions_before_forge(text: str) -> bool:
    """Check that numbered questions appear before any /forge or BUILD NEXT.

    Returns True if questions come first (or no forge prompts exist).
    """
    first_question = re.search(r"^\s*1\.\s+\S", text, re.MULTILINE)
    first_forge = re.search(
        r"(?:/forge\b|BUILD NEXT|WHAT TO BUILD)", text, re.IGNORECASE
    )

    if first_forge is None:
        return True
    if first_question is None:
        return False
    return first_question.start() < first_forge.start()


def assert_has_section(text: str, section: str) -> bool:
    """Check that a named section exists in the output."""
    return section.lower() in text.lower()


def assert_no_code_snippets(text: str) -> bool:
    """Check that no code blocks (``` delimited) appear in the text."""
    return "```" not in text


def assert_no_file_references(text: str) -> bool:
    """Check that no file:line references appear in the text.

    Matches patterns like 'backend/app/api/v1/auth.py:13'.
    """
    return not bool(re.search(r"\S+\.\w+:\d+", text))


def assert_placeholder_not_ready(
    text: str, placeholder_pages: list[str] | None = None
) -> list[str]:
    """Check that placeholder pages are not marked as Ready/Built.

    Returns list of violations (placeholder pages marked ready).
    """
    if placeholder_pages is None:
        placeholder_pages = detect_placeholder_pages()

    violations: list[str] = []
    text_lower = text.lower()

    for page in placeholder_pages:
        page_lower = page.lower()
        page_pos = text_lower.find(page_lower)
        if page_pos == -1:
            continue

        context = text_lower[max(0, page_pos - 100) : page_pos + 200]
        if re.search(r"\b(?:ready|built)\b", context):
            if not re.search(r"\b(?:risky|partial|incomplete|missing|not)\b", context):
                violations.append(page)

    return violations


def assert_pipeline_stages_labeled(text: str) -> bool:
    """Check that pipeline stages use the required labels.

    At least one of: Implemented, Stored-but-unused, Planned, Missing,
    or 'Not yet implemented'.
    """
    labels = [
        "implemented",
        "stored-but-unused",
        "stored but unused",
        "planned",
        "missing",
        "not yet implemented",
        "not implemented",
    ]
    text_lower = text.lower()
    return any(label in text_lower for label in labels)


def assert_status_indicators(text: str, valid: list[str]) -> bool:
    """Check that the text uses at least one of the valid status indicators."""
    text_lower = text.lower()
    return any(v.lower() in text_lower for v in valid)


def assert_has_confidence_rating(text: str) -> bool:
    """Check that a confidence rating is present (HIGH/MEDIUM/LOW)."""
    return bool(re.search(r"\b(?:HIGH|MEDIUM|LOW)\b", text))


def assert_has_sources_section(text: str) -> bool:
    """Check that a Sources section exists."""
    return bool(re.search(r"^Sources?:", text, re.MULTILINE | re.IGNORECASE))


def assert_snippets_labeled(text: str) -> bool:
    """Check that code snippets are labeled EXACT or SIMPLIFIED.

    Returns True if no code blocks exist OR all code blocks have a label.
    """
    blocks = re.findall(r"```[\s\S]*?```", text)
    if not blocks:
        return True

    for block in blocks:
        preceding_text = text[max(0, text.index(block) - 100) : text.index(block)]
        if not re.search(r"\b(?:EXACT|SIMPLIFIED)\b", preceding_text, re.IGNORECASE):
            return False
    return True


def assert_full_paths(text: str) -> list[str]:
    """Check that file paths are full repository-relative, not shortened.

    Returns list of suspicious shortened paths.
    """
    suspicious: list[str] = []
    path_refs = re.findall(r"(\S+\.(?:py|tsx?|json|md|yml|yaml))(?::\d+)?", text)
    for ref in path_refs:
        if "/" not in ref and "\\" not in ref:
            if ref not in ("conftest.py", "pytest.ini", "setup.py", "pyproject.toml"):
                suspicious.append(ref)
    return suspicious


def assert_no_spec_as_implemented(
    text: str,
    spec_only_terms: list[str] | None = None,
) -> list[str]:
    """Check that stack-spec-only capabilities aren't presented as implemented.

    Returns list of violations.
    """
    if spec_only_terms is None:
        spec_only_terms = ["BM25", "RRF", "cross-encoder", "SSE streaming", "HNSW"]

    violations: list[str] = []
    text_lower = text.lower()

    for term in spec_only_terms:
        term_lower = term.lower()
        if term_lower not in text_lower:
            continue

        term_pos = text_lower.find(term_lower)
        context = text_lower[max(0, term_pos - 150) : term_pos + 150]

        if re.search(r"\b(?:implemented|built|exists|running|active|uses)\b", context):
            if not re.search(
                r"\b(?:planned|missing|not yet|not implemented|stored.but.unused)\b",
                context,
            ):
                violations.append(term)

    return violations
