#!/usr/bin/env python3
"""Slow integration tests for the question bank across all personas."""

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

PERSONAS = ["founder", "pm", "eng", "ai"]


@pytest.fixture(scope="module", params=PERSONAS)
def question_bank(request):
    persona = request.param
    output = run_ask(f"/ask {persona} questions")
    return persona, output


class TestQuestionBank:
    def test_has_minimum_questions(self, question_bank):
        persona, output = question_bank
        passed, count = aa.assert_has_questions(output, 5)
        assert passed, (
            f"{persona} question bank has only {count} questions (need 5+). "
            f"This has been a recurring failure — the question bank must "
            f"always render numbered questions as plain text."
        )

    def test_questions_before_forge(self, question_bank):
        persona, output = question_bank
        assert aa.assert_questions_before_forge(output), (
            f"{persona} question bank shows forge/build prompts before "
            f"questions, or shows no questions at all."
        )
