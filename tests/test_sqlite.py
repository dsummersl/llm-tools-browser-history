from __future__ import annotations

from browser_history.sqlite import attach_copy
from browser_history.sqlite import copy_locked_db
from browser_history.sqlite import sha_label
from browser_history.sqlite import build_unified_browser_history_db
from browser_history.sqlite import run_unified_query

import sqlite3
from pathlib import Path

fixture_path = Path(__file__).parent / "fixtures"
chrome_db = fixture_path / "chrome-places.db"
firefox_db = fixture_path / "firefox-places.db"
safari_db = fixture_path / "safari-places.db"


def test_sha_label_is_deterministic():
    p = fixture_path / "db.sqlite"
    p.write_text("x")
    a = sha_label("chrome", p)
    b = sha_label("chrome", p)
    assert a == b
    assert a.startswith("chrome:")
    assert len(a.split(":")[1]) == 10


def test_copy_locked_db_creates_distinct_copy():
    src = fixture_path / "src.sqlite"
    src.write_bytes(b"hello")
    copied = copy_locked_db(src)
    assert copied.exists()
    assert copied.read_bytes() == b"hello"
    # Should be placed in a temp directory and not the same path
    assert copied != src
    assert copied.name == src.name


def test_attach_copy_allows_querying_attached_db():
    main = sqlite3.connect(":memory:")
    cur = main.cursor()
    copied = attach_copy(cur, "src", chrome_db)

    # Validate attachment
    rows = cur.execute("SELECT url FROM src.visits").fetchall()
    assert [r[0] for r in rows] == [1, 2]
    assert copied.exists()
    assert copied != chrome_db
    main.close()


def test_build_unified_browser_history_db():
    # Test with in-memory database (default)
    conn = build_unified_browser_history_db(
        None,
        [
            ("chrome", chrome_db),
            ("firefox", firefox_db),
            ("safari", safari_db),
        ],
    )

    cur = conn.cursor()
    rows = cur.execute(
        "SELECT browser, profile, url, title, referrer_url, visited_dt FROM browser_history ORDER BY browser"
    ).fetchall()
    conn.close()

    assert len(rows) == 6

    ch_hour = "2025-08-18 17:00:00"
    ff_hour = "2024-09-08 00:00:00"
    sf_hour = "2025-01-31 07:00:00"

    # Map by browser for easier asserts
    out = {r[0]: r for r in rows}

    chrome_profile = sha_label("chrome", chrome_db)
    firefox_profile = sha_label("firefox", firefox_db)
    safari_profile = sha_label("safari", safari_db)

    assert out["chrome"] == (
        "chrome",
        chrome_profile,
        "https://example.com/",
        "Example",
        None,
        ch_hour,
    )
    assert out["firefox"] == (
        "firefox",
        firefox_profile,
        "https://news.ycombinator.com/",
        "Hacker News",
        None,
        ff_hour,
    )
    assert out["safari"] == (
        "safari",
        safari_profile,
        "https://www.apple.com/",
        "Apple",
        None,
        sf_hour,
    )


def test_run_unified_query_counts_rows():
    conn = build_unified_browser_history_db(None, [("chrome", chrome_db)])

    rows = run_unified_query(conn, "SELECT COUNT(*) FROM browser_history")
    assert rows[0][0] == 2
    conn.close()


def test_build_unified_browser_history_db_with_file():
    # Test with file-based database
    dest = fixture_path / "unified_file.sqlite"
    conn = build_unified_browser_history_db(dest, [("chrome", chrome_db)])

    assert dest.exists()

    rows = run_unified_query(conn, "SELECT COUNT(*) FROM browser_history")
    assert rows[0][0] == 2
    conn.close()

    # Clean up
    dest.unlink()
