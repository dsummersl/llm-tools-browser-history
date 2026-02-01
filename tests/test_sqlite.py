from __future__ import annotations
import sqlite3

from browser_history.sqlite import copy_locked_db
from browser_history.sqlite import sha_label
from browser_history.sqlite import build_unified_browser_history_db
from browser_history.sqlite import run_unified_query
from browser_history.sqlite import _apply_qp_whitelist

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


def test_build_unified_browser_history_db():
    # Test with in-memory database (default) and no whitelist (strip all)
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

    chrome_profile = sha_label("chrome", chrome_db)
    firefox_profile = sha_label("firefox", firefox_db)
    safari_profile = sha_label("safari", safari_db)

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
        [("chrome", chrome_db)],
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


def test_apply_qp_whitelist_to_referrer():
    """Test that referrer URLs get stripped via whitelist."""
    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE browser_history (
            browser TEXT NOT NULL,
            profile TEXT,
            url TEXT NOT NULL,
            title TEXT,
            referrer_url TEXT,
            visited_dt DATETIME NOT NULL,
            domain TEXT,
            stripped_qp TEXT,
            referrer_domain TEXT,
            referrer_stripped_qp TEXT
        );
        """
    )
    # Insert a row with referrer URL containing query parameters
    cur.execute(
        "INSERT INTO browser_history (browser, profile, url, referrer_url, visited_dt) VALUES (?, ?, ?, ?, ?)",
        (
            "chrome",
            "Default",
            "https://example.com/page?keep=1&strip=2",
            "https://google.com/search?q=hello&ref=abc",
            "2025-01-01 00:00:00",
        ),
    )
    conn.commit()

    whitelist = {"google.com": ["q"]}
    _apply_qp_whitelist(conn, whitelist)

    cur.execute(
        "SELECT url, domain, stripped_qp, referrer_url, referrer_domain, referrer_stripped_qp FROM browser_history"
    )
    row = cur.fetchone()
    # Check main URL stripping (no rule for example.com, strip all)
    assert row[0] == "https://example.com/page"
    assert row[1] == "example.com"
    assert row[2] == "keep,strip"
    # Check referrer URL stripping (keep q, strip ref)
    assert row[3] == "https://google.com/search?q=hello"
    assert row[4] == "google.com"
    assert row[5] == "ref"
    conn.close()


def test_apply_qp_whitelist_null_referrer():
    """Test that NULL referrer URLs are handled correctly."""
    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE browser_history (
            browser TEXT NOT NULL,
            profile TEXT,
            url TEXT NOT NULL,
            title TEXT,
            referrer_url TEXT,
            visited_dt DATETIME NOT NULL,
            domain TEXT,
            stripped_qp TEXT,
            referrer_domain TEXT,
            referrer_stripped_qp TEXT
        );
        """
    )
    cur.execute(
        "INSERT INTO browser_history (browser, profile, url, referrer_url, visited_dt) VALUES (?, ?, ?, ?, ?)",
        (
            "chrome",
            "Default",
            "https://example.com/page?keep=1&strip=2",
            None,
            "2025-01-01 00:00:00",
        ),
    )
    conn.commit()

    whitelist = {"example.com": ["keep"]}
    _apply_qp_whitelist(conn, whitelist)

    cur.execute(
        "SELECT url, domain, stripped_qp, referrer_url, referrer_domain, referrer_stripped_qp FROM browser_history"
    )
    row = cur.fetchone()
    assert row[0] == "https://example.com/page?keep=1"
    assert row[1] == "example.com"
    assert row[2] == "strip"
    assert row[3] is None
    assert row[4] is None
    assert row[5] is None
    conn.close()
