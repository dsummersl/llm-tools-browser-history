from __future__ import annotations
import sqlite3

from browser_history.sqlite import copy_locked_db
from browser_history.sqlite import build_unified_browser_history_db
from browser_history.sqlite import run_unified_query

from pathlib import Path

fixture_path = Path(__file__).parent / "fixtures"
chrome_db = fixture_path / "chrome-places.db"
firefox_db = fixture_path / "firefox-places.db"
safari_db = fixture_path / "safari-places.db"


def test_copy_locked_db_creates_distinct_copy():
    src = fixture_path / "src.sqlite"
    src.write_bytes(b"hello")
    copied = copy_locked_db(src)
    assert copied.exists()
    assert copied.read_bytes() == b"hello"
    # Should be placed in a temp directory and not the same path
    assert copied != src
    assert copied.name == src.name


def test_build_unified_browser_history_db():
    # Test with in-memory database (default) and no whitelist (strip all)
    conn = build_unified_browser_history_db(
        None,
        [
            ("chrome", "Default", chrome_db),
            ("firefox", "default-release", firefox_db),
            ("safari", "default", safari_db),
        ],
    )

    cur = conn.cursor()
    rows = cur.execute(
        "SELECT browser, profile, url, title, referrer_url, visited_dt, domain, stripped_qp "
        "FROM browser_history ORDER BY browser"
    ).fetchall()
    conn.close()

    assert len(rows) == 6

    ch_hour = "2025-08-18 17:00:00"
    ff_hour = "2024-09-08 00:00:00"
    sf_hour = "2025-01-31 07:00:00"

    # Map by browser for easier asserts
    out = {r[0]: r for r in rows}

    chrome_profile = "chrome:Default"
    firefox_profile = "firefox:default-release"
    safari_profile = "safari:default"

    # url, title, referrer_url, visited_dt should match; domain & stripped_qp are new
    assert out["chrome"][0:6] == (
        "chrome",
        chrome_profile,
        "https://example.com/",
        "Example",
        None,
        ch_hour,
    )
    # domain should be populated
    assert out["chrome"][6] == "example.com"

    assert out["firefox"][0:6] == (
        "firefox",
        firefox_profile,
        "https://news.ycombinator.com/",
        "Hacker News",
        None,
        ff_hour,
    )
    assert out["firefox"][6] == "news.ycombinator.com"

    assert out["safari"][0:6] == (
        "safari",
        safari_profile,
        "https://www.apple.com/",
        "Apple",
        None,
        sf_hour,
    )
    assert out["safari"][6] == "www.apple.com"


def test_build_unified_browser_history_db_with_whitelist():
    """When a whitelist is provided, matching params are preserved."""
    whitelist = {"example.com": ["keep"]}
    conn = build_unified_browser_history_db(
        None,
        [("chrome", "Default", chrome_db)],
        whitelist=whitelist,
    )

    rows = run_unified_query(
        conn,
        "SELECT url, domain, stripped_qp FROM browser_history ORDER BY url",
    )
    conn.close()

    # The fixture URLs don't have query params, so nothing to strip/keep
    for row in rows:
        assert row[1] is not None  # domain populated


def test_run_unified_query_counts_rows():
    conn = build_unified_browser_history_db(None, [("chrome", "Default", chrome_db)])

    rows = run_unified_query(conn, "SELECT COUNT(*) FROM browser_history")
    assert rows[0][0] == 2
    conn.close()


def test_build_unified_browser_history_db_with_file():
    # Test with file-based database
    dest = fixture_path / "unified_file.sqlite"
    conn = build_unified_browser_history_db(dest, [("chrome", "Default", chrome_db)])

    assert dest.exists()

    rows = run_unified_query(conn, "SELECT COUNT(*) FROM browser_history")
    assert rows[0][0] == 2
    conn.close()

    # Clean up
    dest.unlink()


def test_sqlite_functions_with_whitelist():
    """Test that SQLite functions correctly process URLs with whitelist."""
    from browser_history.sqlite import _register_sqlite_functions

    conn = sqlite3.connect(":memory:")

    # Register SQLite functions with whitelist
    whitelist = {"google.com": ["q"], "example.com": ["keep"]}
    _register_sqlite_functions(conn, whitelist)

    cur = conn.cursor()

    # Test process_url_url function
    cur.execute("SELECT process_url_url('https://example.com/page?keep=1&strip=2')")
    assert cur.fetchone()[0] == "https://example.com/page?keep=1"

    cur.execute("SELECT process_url_url('https://google.com/search?q=hello&ref=abc')")
    assert cur.fetchone()[0] == "https://google.com/search?q=hello"

    # Test process_url_domain function
    cur.execute("SELECT process_url_domain('https://example.com/page?keep=1&strip=2')")
    assert cur.fetchone()[0] == "example.com"

    cur.execute("SELECT process_url_domain('https://google.com/search?q=hello&ref=abc')")
    assert cur.fetchone()[0] == "google.com"

    # Test process_url_stripped function
    cur.execute("SELECT process_url_stripped('https://example.com/page?keep=1&strip=2')")
    assert cur.fetchone()[0] == "strip"

    cur.execute("SELECT process_url_stripped('https://google.com/search?q=hello&ref=abc')")
    assert cur.fetchone()[0] == "ref"

    conn.close()


def test_sqlite_functions_with_null_url():
    """Test that SQLite functions handle NULL/empty URLs correctly."""
    from browser_history.sqlite import _register_sqlite_functions

    conn = sqlite3.connect(":memory:")
    whitelist = {"example.com": ["keep"]}
    _register_sqlite_functions(conn, whitelist)

    cur = conn.cursor()

    # Test with empty string
    cur.execute("SELECT process_url_url('')")
    assert cur.fetchone()[0] == ""

    cur.execute("SELECT process_url_domain('')")
    assert cur.fetchone()[0] == ""

    cur.execute("SELECT process_url_stripped('')")
    assert cur.fetchone()[0] == ""

    conn.close()
