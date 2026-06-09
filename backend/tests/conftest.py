"""Set minimum required env vars before any app module is imported during collection."""
import os

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/testdb")
os.environ.setdefault("SECRET_KEY", "x" * 32)
