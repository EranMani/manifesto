#!/usr/bin/env python3
"""Slow integration tests for the founder persona."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

HOOKS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HOOKS_DIR))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import ask_assertions as aa  # noqa: E402
from ask_test_runner import run_ask  # noqa: E402

pytestmark = pytest.mark.slow

FOUNDER_FORBIDDEN_BASELINE = [
    "backend", "frontend", "migration", "schema", "endpoint",
    "database model", "middleware", "query", "index",
    "function", "import", "class", "def ", "async ",
]


@pytest.fixture(scope="module")
def founder_persona():
    return aa.load_persona("founder")


@pytest.fixture(scope="module")
def founder_answer():
    return run_ask("/ask founder what can this product do?")


@pytest.fixture(scope="module")
def founder_overview():
    return run_ask("/ask founder overview")


class TestFounderQA:
    def test_no_jargon(self, founder_answer, founder_persona):
        terms = aa.extract_forbidden_terms(founder_persona)
        terms.extend(FOUNDER_FORBIDDEN_BASELINE)
        violations = aa.assert_no_forbidden_terms(founder_answer, terms)
        assert violations == [], f"Jargon leaked: {violations}"

    def test_no_code_snippets(self, founder_answer):
        assert aa.assert_no_code_snippets(founder_answer), "Code snippets found"

    def test_no_file_references(self, founder_answer):
        assert aa.assert_no_file_references(founder_answer), "File references found"


class TestFounderOverview:
    def test_no_backend_frontend_labels(self, founder_overview):
        violations = aa.assert_no_forbidden_terms(
            founder_overview, ["[BE]", "[FE]", "[AI]", "[OPS]", "[SEC]", "[PRD]"]
        )
        assert violations == [], f"Domain icons leaked: {violations}"

    def test_no_jargon(self, founder_overview, founder_persona):
        terms = aa.extract_forbidden_terms(founder_persona)
        terms.extend(FOUNDER_FORBIDDEN_BASELINE)
        violations = aa.assert_no_forbidden_terms(founder_overview, terms)
        assert violations == [], f"Jargon leaked: {violations}"

    def test_placeholder_not_ready(self, founder_overview):
        violations = aa.assert_placeholder_not_ready(founder_overview)
        assert violations == [], f"Placeholder pages marked ready: {violations}"
