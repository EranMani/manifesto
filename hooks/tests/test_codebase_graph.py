#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


HOOKS_DIR = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures" / "context_repo"
sys.path.insert(0, str(HOOKS_DIR))

from codebase_graph import build_codebase_graph, summarize_python  # noqa: E402
from context_engine import ContextPackageBuilder, load_rules  # noqa: E402


class CodebaseGraphTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rules = load_rules(HOOKS_DIR / "context_rules.json")

    def test_graph_is_deterministic_and_resolves_edges(self) -> None:
        first = build_codebase_graph(FIXTURE_ROOT, self.rules)
        second = build_codebase_graph(FIXTURE_ROOT, self.rules)
        self.assertEqual(first, second)
        self.assertIn(
            "backend/app/schemas/auth.py",
            first["imports"]["backend/app/api/v1/auth.py"],
        )
        self.assertIn(
            "frontend/src/api/auth.ts",
            first["imported_by"]["frontend/src/api/client.ts"],
        )
        self.assertEqual(
            first["categories"]["frontend/src/api/auth.ts"],
            "frontend",
        )

    def test_context_builder_uses_valid_cache(self) -> None:
        graph = build_codebase_graph(FIXTURE_ROOT, self.rules)
        with tempfile.TemporaryDirectory() as temporary:
            graph_path = Path(temporary) / "codebase-graph.json"
            graph_path.write_text(json.dumps(graph), encoding="utf-8")
            package = ContextPackageBuilder(
                FIXTURE_ROOT,
                self.rules,
                graph_path=graph_path,
            ).build("1", "aria")
        self.assertEqual(package["graph"]["source"], "cache")
        selected = {item["path"] for item in package["files"]}
        self.assertIn("frontend/src/api/client.ts", selected)
        self.assertIn("frontend/src/pages/Login.tsx", selected)

    def test_invalid_cache_falls_back_safely(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            graph_path = Path(temporary) / "codebase-graph.json"
            graph_path.write_text("{not-json", encoding="utf-8")
            package = ContextPackageBuilder(
                FIXTURE_ROOT,
                self.rules,
                graph_path=graph_path,
            ).build("1", "aria")
        self.assertEqual(package["graph"]["source"], "fallback")
        selected = {item["path"] for item in package["files"]}
        self.assertIn("frontend/src/api/client.ts", selected)

    def test_python_summary_describes_security_responsibilities(self) -> None:
        summary = summarize_python(
            "backend/app/core/security.py",
            """
import bcrypt
import jwt
from fastapi import HTTPException, status
from app.core.config import settings

def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())

def create_access_token(data: dict) -> str:
    return jwt.encode(data, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def decode_token(token: str) -> dict:
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
""",
        )
        self.assertIn("Hashes and verifies passwords with bcrypt", summary)
        self.assertIn("Creates and validates JWT access tokens", summary)
        self.assertIn("HTTP 401", summary)

    def test_python_summary_describes_login_flow(self) -> None:
        summary = summarize_python(
            "backend/app/api/v1/auth.py",
            """
from fastapi import APIRouter
from app.core.security import create_access_token, verify_password

router = APIRouter()

@router.post("/login")
async def login(request, db):
    user = await db.execute(select(User).where(User.email == request.email))
    if not user.is_active:
        raise ValueError("inactive")
    if not verify_password(request.password, user.password_hash):
        raise ValueError("invalid")
    return create_access_token({"sub": str(user.id)})
""",
        )
        self.assertIn("POST /login", summary)
        self.assertIn("Authenticates active users", summary)
        self.assertIn("returns a signed access token", summary)


if __name__ == "__main__":
    unittest.main()
