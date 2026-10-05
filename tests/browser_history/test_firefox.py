from __future__ import annotations

import sqlite3
import datetime
from pathlib import Path

from browser_history.firefox import get_firefox_history_query
from browser_history.sqlite import _register_sqlite_functions

fixture_path = Path(__file__).parent.parent / "fixtures"
firefox_db = fixture_path / "firefox-places.db"


def test_firefox_date_conversion():
    conn = sqlite3.connect(f"file:{firefox_db}?mode=ro", uri=True)

    _register_sqlite_functions(conn, {})

    cur = conn.cursor()
    cur.execute(f"ATTACH DATABASE 'file:{firefox_db}?mode=ro' AS firefox_alias")

    query = get_firefox_history_query("firefox_alias", "test_profile")

    cur.execute(query)
    rows = cur.fetchall()

    assert len(rows) == 2

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

        assert browser == "firefox"
        assert profile == "test_profile"
        assert url is not None
        assert visited_dt is not None

        assert len(visited_dt) == 19
        assert visited_dt[13:] == ":00:00"

        parsed_dt = datetime.datetime.strptime(visited_dt, "%Y-%m-%d %H:00:00")
        assert parsed_dt.year >= 2023

        if "mozilla.org" in url:
            assert "mozilla.org" in url
        elif "ycombinator.com" in url:
            assert "ycombinator.com" in url

    conn.close()


def test_firefox_date_calculation():
    conn = sqlite3.connect(":memory:")
    _register_sqlite_functions(conn, {})

    cur = conn.cursor()

    firefox_timestamp = 1725750000000000
    cur.execute(
        "SELECT strftime('%Y-%m-%d %H:00:00', ? / 1000000, 'unixepoch')", (firefox_timestamp,)
    )
    result = cur.fetchone()[0]

    assert result is not None
    parsed_dt = datetime.datetime.strptime(result, "%Y-%m-%d %H:00:00")
    assert parsed_dt.year >= 2023

    conn.close()


def test_firefox_sample_data_date():
    conn = sqlite3.connect(":memory:")
    _register_sqlite_functions(conn, {})

    cur = conn.cursor()

    firefox_timestamp = 1725755000000000
    cur.execute(
        "SELECT strftime('%Y-%m-%d %H:00:00', v / 1000000, 'unixepoch') FROM (SELECT ? as v)",
        (firefox_timestamp,),
    )
    firefox_hour = cur.fetchone()[0]
    assert firefox_hour == "2024-09-08 00:00:00", f"Firefox date wrong: {firefox_hour}"

    conn.close()


def test_firefox_query_structure():
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
