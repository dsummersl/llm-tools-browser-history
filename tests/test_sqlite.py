from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

fixture_path = Path(__file__).parent / "fixtures"
chrome_db = fixture_path / "chrome-places.db"
firefox_db = fixture_path / "firefox-places.db"
safari_db = fixture_path / "safari-places.db"


from browser_history.sqlite import (
    _attach_copy,
    _copy_locked_db,
    _sha_label,
    build_unified_browser_history_db,
    history_query,
    run_unified_query,
)


def test_sha_label_is_deterministic():
    p = fixture_path / "db.sqlite"
    p.write_text("x")
    a = _sha_label("chrome", p)
    b = _sha_label("chrome", p)
    assert a == b
    assert a.startswith("chrome:")
    assert len(a.split(":")[1]) == 10


def test_copy_locked_db_creates_distinct_copy():
    src = fixture_path / "src.sqlite"
    src.write_bytes(b"hello")
    copied = _copy_locked_db(src)
    assert copied.exists()
    assert copied.read_bytes() == b"hello"
    # Should be placed in a temp directory and not the same path
    assert copied != src
    assert copied.name == src.name


def test_attach_copy_allows_querying_attached_db():
    main = sqlite3.connect(":memory:")
    cur = main.cursor()
    copied = _attach_copy(cur, "src", chrome_db)

    # Validate attachment
    rows = cur.execute("SELECT url FROM src.visits").fetchall()
    assert [r[0] for r in rows] == [1, 2]
    assert copied.exists()
    assert copied != chrome_db
    main.close()


def test_build_unified_browser_history_db():
    dest = fixture_path / "unified.sqlite"
    build_unified_browser_history_db(
        dest,
        [
            ("chrome", chrome_db),
            ("firefox", firefox_db),
            ("safari", safari_db),
        ],
    )

    assert dest.exists()

    con = sqlite3.connect(dest)
    cur = con.cursor()
    rows = cur.execute(
        "SELECT browser, profile, url, title, referrer_url, visited_dt FROM browser_history ORDER BY browser"
    ).fetchall()
    con.close()

    assert len(rows) == 4

    ch_hour = '2025-08-18 17:00:00'
    ff_hour = '2024-09-08 00:00:00'
    sf_hour = ''

    # Map by browser for easier asserts
    out = {r[0]: r for r in rows}

    chrome_profile = _sha_label("chrome", chrome_db)
    firefox_profile = _sha_label("firefox", firefox_db)
    safari_profile = _sha_label("safari", safari_db)

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
        'https://news.ycombinator.com/',
        "Hacker News",
        None,
        ff_hour,
    )
    # TODO currently empty, no data:
    # assert out["safari"] == (
    #     "safari",
    #     safari_profile,
    #     "https://safari.com/z",
    #     "S",
    #     None,
    #     sf_hour,
    # )


def test_run_unified_query_counts_rows():
    dest = fixture_path / "unified.sqlite"
    build_unified_browser_history_db(dest, [("chrome", chrome_db)])

    rows = run_unified_query(dest, "SELECT COUNT(*) FROM browser_history")
    assert rows[0][0] == 2
