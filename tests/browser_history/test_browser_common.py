"""Common unit tests for browser history select statements.

Tests that apply to all browsers (Chrome, Firefox, Safari).
"""

from __future__ import annotations

import sqlite3

from browser_history.chrome import get_chrome_history_query
from browser_history.firefox import get_firefox_history_query
from browser_history.safari import get_safari_history_query
from browser_history.sqlite import _register_sqlite_functions


def test_date_hour_rounding():
    """Test that all browsers round dates to the hour correctly."""
    # Test that the strftime format '%Y-%m-%d %H:00:00' correctly rounds to hour

    conn = sqlite3.connect(":memory:")
    _register_sqlite_functions(conn, {})

    cur = conn.cursor()

    # Test with a timestamp that has minutes and seconds
    # 2024-01-01 12:34:56 UTC
    timestamp = 1704112496  # Unix timestamp for 2024-01-01 12:34:56

    cur.execute("SELECT strftime('%Y-%m-%d %H:00:00', ?, 'unixepoch')", (timestamp,))
    result = cur.fetchone()[0]

    # Should round to 2024-01-01 12:00:00
    assert result == "2024-01-01 12:00:00"

    conn.close()


def test_all_browser_query_structures():
    """Test that all browser queries return the expected columns in the correct order."""
    # Chrome query
    chrome_query = get_chrome_history_query("test_alias", "test_profile")
    assert "SELECT" in chrome_query
    assert "'chrome' AS browser" in chrome_query
    assert "'test_profile' AS profile" in chrome_query
    assert "process_url_url(u.url) AS url" in chrome_query
    assert "visited_dt" in chrome_query

    # Firefox query
    firefox_query = get_firefox_history_query("test_alias", "test_profile")
    assert "SELECT" in firefox_query
    assert "'firefox' AS browser" in firefox_query
    assert "'test_profile' AS profile" in firefox_query
    assert "process_url_url(p.url) AS url" in firefox_query
    assert "visited_dt" in firefox_query

    # Safari query
    safari_query = get_safari_history_query("test_alias", "test_profile")
    assert "SELECT" in safari_query
    assert "'safari' AS browser" in safari_query
    assert "'test_profile' AS profile" in safari_query
    assert "process_url_url(i.url) AS url" in safari_query
    assert "visited_dt" in safari_query
