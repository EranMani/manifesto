#!/usr/bin/env python3
"""Slow integration tests for the AI/ML persona."""

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

SPEC_ONLY_TERMS = ["BM25", "RRF", "cross-encoder", "SSE streaming", "HNSW"]


@pytest.fixture(scope="module")
def ai_pipeline_answer():
    return run_ask("/ask ai how does the RAG pipeline work end to end?")


@pytest.fixture(scope="module")
def ai_overview():
    return run_ask("/ask ai overview")


class TestAIPipeline:
    def test_pipeline_stages_labeled(self, ai_pipeline_answer):
        assert aa.assert_pipeline_stages_labeled(ai_pipeline_answer), \
            "Pipeline stages not labeled (Implemented/Planned/Missing)"

    def test_no_spec_as_implemented(self, ai_pipeline_answer):
        violations = aa.assert_no_spec_as_implemented(
            ai_pipeline_answer, SPEC_ONLY_TERMS
        )
        assert violations == [], \
            f"Stack spec capabilities presented as implemented: {violations}"

    def test_has_sources(self, ai_pipeline_answer):
        assert aa.assert_has_sources_section(ai_pipeline_answer), \
            "Sources section missing"

    def test_has_confidence(self, ai_pipeline_answer):
        assert aa.assert_has_confidence_rating(ai_pipeline_answer), \
            "Confidence rating missing"


class TestAIOverview:
    def test_no_spec_as_implemented(self, ai_overview):
        violations = aa.assert_no_spec_as_implemented(
            ai_overview, SPEC_ONLY_TERMS
        )
        assert violations == [], \
            f"Stack spec capabilities presented as implemented: {violations}"
