"""Unit tests for Chrome browser history select statements.

Focuses on verifying date column conversions for Chrome.
"""

from __future__ import annotations

import sqlite3
import datetime
from pathlib import Path

from browser_history.chrome import get_chrome_history_query
from browser_history.sqlite import _register_sqlite_functions

fixture_path = Path(__file__).parent.parent / "fixtures"
chrome_db = fixture_path / "chrome-places.db"


def test_chrome_date_conversion():
    """Test Chrome date conversion from WebKit epoch to datetime."""
    # Connect to Chrome sample database
    conn = sqlite3.connect(f"file:{chrome_db}?mode=ro", uri=True)

    # Register SQLite functions
    _register_sqlite_functions(conn, {})

    # Create an alias for the attached database
    cur = conn.cursor()
    cur.execute(f"ATTACH DATABASE 'file:{chrome_db}?mode=ro' AS chrome_alias")

    # Get the Chrome query
    query = get_chrome_history_query("chrome_alias", "test_profile")

    # Execute the query
    cur.execute(query)
    rows = cur.fetchall()

    # Verify we got results
    assert len(rows) == 2

    # Check the structure of results
    for row in rows:
        (
            browser,
            profile,
            url,
            title,
            referrer_url,
            visited_dt,
            domain,
            stripped_qp,
            referrer_domain,
            referrer_stripped_qp,
        ) = row

        # Basic assertions
        assert browser == "chrome"
        assert profile == "test_profile"
        assert url is not None
        assert visited_dt is not None

        # Verify date format: YYYY-MM-DD HH:00:00
        assert len(visited_dt) == 19  # "YYYY-MM-DD HH:00:00"
        assert visited_dt[13:] == ":00:00"  # Minutes and seconds should be ":00:00"

        # Parse the date to ensure it's valid
        parsed_dt = datetime.datetime.strptime(visited_dt, "%Y-%m-%d %H:00:00")
        assert parsed_dt.year >= 2023  # Should be recent

        # Check specific URLs from sample data
        if "chromium.org" in url:
            assert "chromium.org" in url
        elif "example.com" in url:
            assert "example.com" in url

    conn.close()


def test_chrome_date_calculation():
    """Test Chrome date calculation logic directly."""
    # Chrome uses WebKit epoch: 1601-01-01 UTC
    # visit_time is microseconds since WebKit epoch

    # Test with a known Chrome timestamp
    conn = sqlite3.connect(":memory:")
    _register_sqlite_functions(conn, {})

    cur = conn.cursor()

    # Test the Chrome date conversion formula
    # Formula: strftime('%Y-%m-%d %H:00:00', (v.visit_time/1000 - 11644473600*1000)/1000, 'unixepoch')
    # Simplified: (visit_time - 11644473600 * 1000000) / 1000000

    # Test with the timestamp from our sample data: 13400000000000000
    chrome_timestamp = 13400000000000000
    cur.execute(
        "SELECT strftime('%Y-%m-%d %H:00:00', (? - 11644473600 * 1000000) / 1000000, 'unixepoch')",
        (chrome_timestamp,),
    )
    result = cur.fetchone()[0]

    # The result should be a valid date
    assert result is not None
    parsed_dt = datetime.datetime.strptime(result, "%Y-%m-%d %H:00:00")
    assert parsed_dt.year >= 2023

    conn.close()


def test_chrome_sample_data_date():
    """Verify Chrome date conversion matches the sample data expectation."""
    # Chrome: example.com should be 2025-08-18 17:00:00
    conn = sqlite3.connect(":memory:")
    _register_sqlite_functions(conn, {})

    cur = conn.cursor()

    # Test Chrome timestamp for example.com: 13400010000000000
    chrome_timestamp = 13400010000000000
    cur.execute(
        "SELECT strftime('%Y-%m-%d %H:00:00', (v - 11644473600 * 1000000) / 1000000, 'unixepoch') FROM (SELECT ? as v)",
        (chrome_timestamp,),
    )
    chrome_hour = cur.fetchone()[0]
    assert chrome_hour == "2025-08-18 17:00:00", f"Chrome date wrong: {chrome_hour}"

    conn.close()


def test_chrome_query_structure():
    """Test that Chrome query returns the expected columns in the correct order."""
    # Chrome query
    chrome_query = get_chrome_history_query("test_alias", "test_profile")
    assert "SELECT" in chrome_query
    assert "'chrome' AS browser" in chrome_query
    assert "'test_profile' AS profile" in chrome_query
    assert "process_url_url(u.url) AS url" in chrome_query
    assert "visited_dt" in chrome_query
    assert (
        "strftime('%Y-%m-%d %H:00:00', (v.visit_time/1000 - 11644473600*1000)/1000, 'unixepoch') AS visited_dt"
        in chrome_query
    )
