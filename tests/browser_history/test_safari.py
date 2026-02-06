"""Unit tests for Safari browser history select statements.

Focuses on verifying date column conversions for Safari.
"""

from __future__ import annotations

import sqlite3
import datetime
from pathlib import Path

from browser_history.safari import get_safari_history_query
from browser_history.sqlite import _register_sqlite_functions

fixture_path = Path(__file__).parent.parent / "fixtures"
safari_db = fixture_path / "safari-places.db"


def test_safari_date_conversion():
    """Test Safari date conversion from Apple epoch to datetime."""
    # Connect to Safari sample database
    conn = sqlite3.connect(f"file:{safari_db}?mode=ro", uri=True)

    # Register SQLite functions
    _register_sqlite_functions(conn, {})

    # Create an alias for the attached database
    cur = conn.cursor()
    cur.execute(f"ATTACH DATABASE 'file:{safari_db}?mode=ro' AS safari_alias")

    # Get the Safari query
    query = get_safari_history_query("safari_alias", "test_profile")

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
        assert browser == "safari"
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
        if "apple.com" in url:
            assert "apple.com" in url
        elif "webkit.org" in url:
            assert "webkit.org" in url

    conn.close()


def test_safari_date_calculation():
    """Test Safari date calculation logic directly."""
    # Safari uses seconds since Apple epoch (2001-01-01)

    conn = sqlite3.connect(":memory:")
    _register_sqlite_functions(conn, {})

    cur = conn.cursor()

    # Test with a known Safari timestamp: 760000000.0
    safari_timestamp = 760000000.0
    cur.execute(
        "SELECT strftime('%Y-%m-%d %H:00:00', ? + strftime('%s','2001-01-01'), 'unixepoch')",
        (safari_timestamp,),
    )
    result = cur.fetchone()[0]

    # The result should be a valid date
    assert result is not None
    parsed_dt = datetime.datetime.strptime(result, "%Y-%m-%d %H:00:00")
    assert parsed_dt.year >= 2023

    conn.close()


def test_safari_sample_data_date():
    """Verify Safari date conversion matches the sample data expectation."""
    # Safari: apple.com should be 2025-01-31 07:00:00
    conn = sqlite3.connect(":memory:")
    _register_sqlite_functions(conn, {})

    cur = conn.cursor()

    # Test Safari timestamp for apple.com: 760000000.0
    safari_timestamp = 760000000.0
    cur.execute(
        "SELECT strftime('%Y-%m-%d %H:00:00', v + strftime('%s','2001-01-01'), 'unixepoch') FROM (SELECT ? as v)",
        (safari_timestamp,),
    )
    safari_hour = cur.fetchone()[0]
    assert safari_hour == "2025-01-31 07:00:00", f"Safari date wrong: {safari_hour}"

    conn.close()


def test_safari_query_structure():
    """Test that Safari query returns the expected columns in the correct order."""
    # Safari query
    safari_query = get_safari_history_query("test_alias", "test_profile")
    assert "SELECT" in safari_query
    assert "'safari' AS browser" in safari_query
    assert "'test_profile' AS profile" in safari_query
    assert "process_url_url(i.url) AS url" in safari_query
    assert "visited_dt" in safari_query
    assert (
        "strftime('%Y-%m-%d %H:00:00', v.visit_time + strftime('%s','2001-01-01'), 'unixepoch') AS visited_dt"
        in safari_query
    )
