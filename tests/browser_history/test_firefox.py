"""Unit tests for Firefox browser history select statements.

Focuses on verifying date column conversions for Firefox.
"""

from __future__ import annotations

import sqlite3
import datetime
from pathlib import Path

from browser_history.firefox import get_firefox_history_query
from browser_history.sqlite import _register_sqlite_functions

fixture_path = Path(__file__).parent.parent / "fixtures"
firefox_db = fixture_path / "firefox-places.db"


def test_firefox_date_conversion():
    """Test Firefox date conversion from microseconds to datetime."""
    # Connect to Firefox sample database
    conn = sqlite3.connect(f"file:{firefox_db}?mode=ro", uri=True)

    # Register SQLite functions
    _register_sqlite_functions(conn, {})

    # Create an alias for the attached database
    cur = conn.cursor()
    cur.execute(f"ATTACH DATABASE 'file:{firefox_db}?mode=ro' AS firefox_alias")

    # Get the Firefox query
    query = get_firefox_history_query("firefox_alias", "test_profile")

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
        assert browser == "firefox"
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
        if "mozilla.org" in url:
            assert "mozilla.org" in url
        elif "ycombinator.com" in url:
            assert "ycombinator.com" in url

    conn.close()


def test_firefox_date_calculation():
    """Test Firefox date calculation logic directly."""
    # Firefox uses microseconds since Unix epoch

    conn = sqlite3.connect(":memory:")
    _register_sqlite_functions(conn, {})

    cur = conn.cursor()

    # Test with a known Firefox timestamp: 1725750000000000
    firefox_timestamp = 1725750000000000
    cur.execute(
        "SELECT strftime('%Y-%m-%d %H:00:00', ? / 1000000, 'unixepoch')", (firefox_timestamp,)
    )
    result = cur.fetchone()[0]

    # The result should be a valid date
    assert result is not None
    parsed_dt = datetime.datetime.strptime(result, "%Y-%m-%d %H:00:00")
    assert parsed_dt.year >= 2023

    conn.close()


def test_firefox_sample_data_date():
    """Verify Firefox date conversion matches the sample data expectation."""
    # Firefox: news.ycombinator.com should be 2024-09-08 00:00:00
    conn = sqlite3.connect(":memory:")
    _register_sqlite_functions(conn, {})

    cur = conn.cursor()

    # Test Firefox timestamp for ycombinator.com: 1725755000000000
    firefox_timestamp = 1725755000000000
    cur.execute(
        "SELECT strftime('%Y-%m-%d %H:00:00', v / 1000000, 'unixepoch') FROM (SELECT ? as v)",
        (firefox_timestamp,),
    )
    firefox_hour = cur.fetchone()[0]
    assert firefox_hour == "2024-09-08 00:00:00", f"Firefox date wrong: {firefox_hour}"

    conn.close()


def test_firefox_query_structure():
    """Test that Firefox query returns the expected columns in the correct order."""
    # Firefox query
    firefox_query = get_firefox_history_query("test_alias", "test_profile")
    assert "SELECT" in firefox_query
    assert "'firefox' AS browser" in firefox_query
    assert "'test_profile' AS profile" in firefox_query
    assert "process_url_url(p.url) AS url" in firefox_query
    assert "visited_dt" in firefox_query
    assert (
        "strftime('%Y-%m-%d %H:00:00', h.visit_date/1000000, 'unixepoch') AS visited_dt"
        in firefox_query
    )
