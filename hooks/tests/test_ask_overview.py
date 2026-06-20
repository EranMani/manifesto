#!/usr/bin/env python3
"""Slow integration tests for the overview radar."""

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


@pytest.fixture(scope="module")
def overview_default():
    return run_ask("/ask overview")


@pytest.fixture(scope="module")
def overview_founder():
    return run_ask("/ask founder overview")


class TestOverviewDefault:
    def test_has_activity_section(self, overview_default):
        assert aa.assert_has_section(overview_default, "activity"), \
            "Activity heatmap section missing"

    def test_has_multiple_domains(self, overview_default):
        domain_markers = ["backend", "frontend", "ai", "devops"]
        found = sum(
            1 for d in domain_markers
            if d.lower() in overview_default.lower()
        )
        assert found >= 3, f"Only {found} domain sections found (need 3+)"

    def test_placeholder_not_ready(self, overview_default):
        violations = aa.assert_placeholder_not_ready(overview_default)
        assert violations == [], \
            f"Placeholder pages marked ready: {violations}"


class TestOverviewFounder:
    def test_no_domain_icons(self, overview_founder):
        violations = aa.assert_no_forbidden_terms(
            overview_founder,
            ["[BE]", "[FE]", "[AI]", "[OPS]", "[SEC]", "[PRD]"],
        )
        assert violations == [], f"Domain icons leaked: {violations}"

    def test_no_backend_frontend(self, overview_founder):
        violations = aa.assert_no_forbidden_terms(
            overview_founder, ["backend", "frontend"]
        )
        assert violations == [], f"Technical domain labels leaked: {violations}"
