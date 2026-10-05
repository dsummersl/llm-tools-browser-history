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

    row = cur.fetchone()
    return row[2] if row and row[2] else ""


def test_get_or_create_unified_db_use_cache_false_default():
    with patch("browser_history.sqlite.get_persistent_db_path") as mock_get_path:
        mock_path = Path("/tmp/mock_history.db")
        mock_get_path.return_value = mock_path

        conn = get_or_create_unified_db(sources=[], db_path=None)

        db_file = get_db_path(conn)

        assert db_file != str(mock_path)

        assert db_file == ""

        mock_get_path.assert_not_called()


def test_get_or_create_unified_db_use_cache_true():
    with patch("browser_history.sqlite.get_persistent_db_path") as mock_get_path:
        mock_path = Path("/tmp/mock_history.db")
        mock_get_path.return_value = mock_path

        conn = get_or_create_unified_db(sources=[], db_path=None, use_cache=True)

        db_file = get_db_path(conn)

        assert Path(db_file).resolve() == mock_path.resolve()
        mock_get_path.assert_called_once()
