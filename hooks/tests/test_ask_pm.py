#!/usr/bin/env python3
"""Slow integration tests for the PM persona."""

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

PM_FORBIDDEN_BASELINE = [
    "GET", "POST", "PATCH", "DELETE", "PUT",
    "foreign key", "hard delete", "soft delete",
    "middleware", "database port conflict", "embedding service",
    "auto-provision", "commit tooling",
]


@pytest.fixture(scope="module")
def pm_persona():
    return aa.load_persona("pm")


@pytest.fixture(scope="module")
def pm_answer():
    return run_ask("/ask pm what features are built vs. missing?")


@pytest.fixture(scope="module")
def pm_overview():
    return run_ask("/ask pm ov")


class TestPMQA:
    def test_no_jargon(self, pm_answer, pm_persona):
        terms = aa.extract_forbidden_terms(pm_persona)
        terms.extend(PM_FORBIDDEN_BASELINE)
        violations = aa.assert_no_forbidden_terms(pm_answer, terms)
        assert violations == [], f"Jargon leaked: {violations}"

    def test_no_code_snippets(self, pm_answer):
        assert aa.assert_no_code_snippets(pm_answer), "Code snippets found"

    def test_no_file_references(self, pm_answer):
        assert aa.assert_no_file_references(pm_answer), "File references found"

    def test_has_status_indicators(self, pm_answer):
        valid = ["Ready", "Built but risky", "Partial", "Planned", "Missing"]
        assert aa.assert_status_indicators(pm_answer, valid), \
            "No valid status indicators found"

    def test_placeholder_not_ready(self, pm_answer):
        violations = aa.assert_placeholder_not_ready(pm_answer)
        assert violations == [], f"Placeholder pages marked ready: {violations}"


class TestPMOverview:
    def test_no_jargon(self, pm_overview, pm_persona):
        terms = aa.extract_forbidden_terms(pm_persona)
        terms.extend(PM_FORBIDDEN_BASELINE)
        violations = aa.assert_no_forbidden_terms(pm_overview, terms)
        assert violations == [], f"Jargon leaked: {violations}"

    def test_placeholder_not_ready(self, pm_overview):
        violations = aa.assert_placeholder_not_ready(pm_overview)
        assert violations == [], f"Placeholder pages marked ready: {violations}"
