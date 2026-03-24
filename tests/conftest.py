"""Shared test fixtures."""

import sqlite3
import tempfile
from pathlib import Path

import pytest

from codepractice.db.database import DatabaseManager


@pytest.fixture
def tmp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    db = DatabaseManager(db_path)
    yield db
    db_path.unlink(missing_ok=True)
