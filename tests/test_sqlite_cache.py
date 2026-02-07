import sqlite3
from pathlib import Path
from unittest.mock import patch
import pytest
from browser_history.sqlite import get_or_create_unified_db, cleanup_unified_db


@pytest.fixture(autouse=True)
def clean_unified_db():
    cleanup_unified_db()
    yield
    cleanup_unified_db()


def get_db_path(conn: sqlite3.Connection) -> str:
    cur = conn.cursor()
    cur.execute("PRAGMA database_list")
    # row is (seq, name, file)
    row = cur.fetchone()
    return row[2] if row and row[2] else ""


def test_get_or_create_unified_db_use_cache_false_default():
    """Verify that use_cache=False does not use persistent DB."""
    with patch("browser_history.sqlite.get_persistent_db_path") as mock_get_path:
        mock_path = Path("/tmp/mock_history.db")
        mock_get_path.return_value = mock_path

        # We don't need real sources for this test as we just want to see where it tries to open the DB
        # But build_unified_browser_history_db might fail if sources are empty or invalid
        # Let's use empty list of sources.
        conn = get_or_create_unified_db(sources=[], db_path=None)

        db_file = get_db_path(conn)
        # It should NOT be mock_path because use_cache defaults to False
        assert db_file != str(mock_path)
        # For in-memory, it's usually empty string in SQLite for :memory:
        assert db_file == ""

        mock_get_path.assert_not_called()


def test_get_or_create_unified_db_use_cache_true():
    """Verify that use_cache=True uses persistent DB path."""
    with patch("browser_history.sqlite.get_persistent_db_path") as mock_get_path:
        mock_path = Path("/tmp/mock_history.db")
        mock_get_path.return_value = mock_path

        # Note: we are passing use_cache=True which is not yet supported in the signature
        # so this test will fail to even compile/run if I don't use kwargs or if I don't update the signature first.
        # BUT TDD says write the test first.
        conn = get_or_create_unified_db(sources=[], db_path=None, use_cache=True)

        db_file = get_db_path(conn)
        # Use resolve() to handle macOS /tmp -> /private/tmp symlink
        assert Path(db_file).resolve() == mock_path.resolve()
        mock_get_path.assert_called_once()
