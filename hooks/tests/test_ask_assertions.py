#!/usr/bin/env python3
"""Fast unit tests for ask assertion helpers — no CLI calls."""

from __future__ import annotations

import sys
from pathlib import Path

HOOKS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HOOKS_DIR))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import ask_assertions as aa  # noqa: E402


# ---------------------------------------------------------------------------
# Persona loading
# ---------------------------------------------------------------------------

def test_load_persona_engineer():
    p = aa.load_persona("engineer")
    assert p["name"] == "Senior Backend Engineer"
    assert "engineer" in p["aliases"]


def test_load_persona_founder():
    p = aa.load_persona("founder")
    assert p["name"] == "Founder / Non-Technical"


def test_get_evergreen_questions():
    p = aa.load_persona("engineer")
    qs = aa.get_evergreen_questions(p)
    assert len(qs) >= 5


def test_extract_forbidden_terms_founder():
    p = aa.load_persona("founder")
    terms = aa.extract_forbidden_terms(p)
    assert len(terms) > 0


# ---------------------------------------------------------------------------
# Placeholder detection
# ---------------------------------------------------------------------------

def test_detect_placeholder_pages():
    pages = aa.detect_placeholder_pages()
    assert "Admin" in pages
    assert "VendorList" in pages


# ---------------------------------------------------------------------------
# Forbidden terms
# ---------------------------------------------------------------------------

def test_no_forbidden_terms_clean():
    violations = aa.assert_no_forbidden_terms(
        "The product helps users manage deliveries.",
        ["backend", "frontend", "migration"],
    )
    assert violations == []


def test_no_forbidden_terms_violation():
    violations = aa.assert_no_forbidden_terms(
        "The backend service runs FastAPI.",
        ["backend", "frontend"],
    )
    assert "backend" in violations


def test_no_forbidden_terms_word_boundary():
    violations = aa.assert_no_forbidden_terms(
        "Immigration policy is handled separately.",
        ["migration"],
    )
    assert violations == []


# ---------------------------------------------------------------------------
# Question bank
# ---------------------------------------------------------------------------

def test_has_questions_pass():
    text = """
QUESTIONS — Engineer
───────────────────

Start here:
  1. What are the hub files?
  2. How does auth work?
  3. What patterns are used?

Go deeper:
  4. What's the dependency chain for auth?
  5. How does data flow from frontend to AI?
  6. What modules lack test coverage?
"""
    passed, count = aa.assert_has_questions(text, 5)
    assert passed
    assert count >= 5


def test_has_questions_fail():
    text = """
BUILD NEXT:
  /forge add shipment editing
  /forge fix auth regression
"""
    passed, count = aa.assert_has_questions(text, 5)
    assert not passed
    assert count == 0


def test_questions_before_forge_pass():
    text = """
  1. What features are built?
  2. What's missing?

BUILD NEXT:
  /forge add pagination
"""
    assert aa.assert_questions_before_forge(text) is True


def test_questions_before_forge_fail():
    text = """
BUILD NEXT:
  /forge add pagination

  1. What features are built?
"""
    assert aa.assert_questions_before_forge(text) is False


def test_questions_before_forge_no_forge():
    text = """
  1. What features are built?
  2. What's missing?
"""
    assert aa.assert_questions_before_forge(text) is True


# ---------------------------------------------------------------------------
# Code and file detection
# ---------------------------------------------------------------------------

def test_no_code_snippets_clean():
    assert aa.assert_no_code_snippets("Plain text answer.") is True


def test_no_code_snippets_violation():
    assert aa.assert_no_code_snippets("Here:\n```python\nprint(1)\n```") is False


def test_no_file_references_clean():
    assert aa.assert_no_file_references("Users can log in and manage.") is True


def test_no_file_references_violation():
    assert aa.assert_no_file_references("See backend/app/api/v1/auth.py:13") is False


# ---------------------------------------------------------------------------
# Placeholder + Ready
# ---------------------------------------------------------------------------

def test_placeholder_not_ready_clean():
    violations = aa.assert_placeholder_not_ready(
        "Admin — Incomplete, placeholder page\nVendorList — Partial",
        ["Admin", "VendorList"],
    )
    assert violations == []


def test_placeholder_not_ready_violation():
    violations = aa.assert_placeholder_not_ready(
        "Admin — Ready, fully built\nVendorList — Built",
        ["Admin", "VendorList"],
    )
    assert len(violations) > 0


# ---------------------------------------------------------------------------
# Pipeline stages
# ---------------------------------------------------------------------------

def test_pipeline_stages_labeled_pass():
    text = "Chunking: Implemented. Reranking: Not yet implemented. BM25: Planned."
    assert aa.assert_pipeline_stages_labeled(text) is True


def test_pipeline_stages_labeled_fail():
    text = "The system uses chunking, embedding, and retrieval."
    assert aa.assert_pipeline_stages_labeled(text) is False


# ---------------------------------------------------------------------------
# Confidence and sources
# ---------------------------------------------------------------------------

def test_has_confidence_rating():
    assert aa.assert_has_confidence_rating("Confidence: HIGH") is True
    assert aa.assert_has_confidence_rating("No rating here.") is False


def test_has_sources_section():
    assert aa.assert_has_sources_section("Sources: file.py:10") is True
    assert aa.assert_has_sources_section("No sources listed.") is False


# ---------------------------------------------------------------------------
# Snippet labels
# ---------------------------------------------------------------------------

def test_snippets_labeled_pass():
    text = "EXACT:\n```python\ndef foo(): pass\n```"
    assert aa.assert_snippets_labeled(text) is True


def test_snippets_labeled_fail():
    text = "Here is the code:\n```python\ndef foo(): pass\n```"
    assert aa.assert_snippets_labeled(text) is False


def test_snippets_labeled_no_blocks():
    assert aa.assert_snippets_labeled("No code here.") is True


# ---------------------------------------------------------------------------
# Full paths
# ---------------------------------------------------------------------------

def test_full_paths_clean():
    suspicious = aa.assert_full_paths("See backend/app/api/v1/auth.py:13")
    assert suspicious == []


def test_full_paths_shortened():
    suspicious = aa.assert_full_paths("See auth.py:13 for details")
    assert "auth.py" in suspicious


# ---------------------------------------------------------------------------
# Spec as implemented
# ---------------------------------------------------------------------------

def test_no_spec_as_implemented_clean():
    violations = aa.assert_no_spec_as_implemented(
        "BM25 is planned but not yet implemented."
    )
    assert violations == []


def test_no_spec_as_implemented_violation():
    violations = aa.assert_no_spec_as_implemented(
        "The system uses BM25 for lexical retrieval."
    )
    assert "BM25" in violations


def test_no_spec_as_implemented_absent():
    violations = aa.assert_no_spec_as_implemented(
        "The system uses cosine similarity for retrieval."
    )
    assert violations == []


# ---------------------------------------------------------------------------
# Status indicators
# ---------------------------------------------------------------------------

def test_status_indicators_pass():
    text = "Shipments — Ready. Documents — Partial."
    valid = ["Ready", "Partial", "Missing", "Planned"]
    assert aa.assert_status_indicators(text, valid) is True


def test_status_indicators_fail():
    text = "Everything is fine."
    valid = ["Ready", "Partial", "Missing"]
    assert aa.assert_status_indicators(text, valid) is False
