#!/usr/bin/env python3
"""Slow integration tests for the engineer persona."""

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
def eng_answer():
    return run_ask("/ask eng how does auth work?")


class TestEngineerQA:
    def test_has_sources(self, eng_answer):
        assert aa.assert_has_sources_section(eng_answer), "Sources section missing"

    def test_has_confidence(self, eng_answer):
        assert aa.assert_has_confidence_rating(eng_answer), \
            "Confidence rating missing"

    def test_full_paths(self, eng_answer):
        suspicious = aa.assert_full_paths(eng_answer)
        assert suspicious == [], f"Shortened paths found: {suspicious}"

    def test_snippets_labeled(self, eng_answer):
        assert aa.assert_snippets_labeled(eng_answer), \
            "Code snippets not labeled EXACT/SIMPLIFIED"
