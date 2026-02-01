from sqlite3 import Cursor, Connection, connect
import logging
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
import pathlib
import tempfile
import shutil
import hashlib
from typing import Any
from collections.abc import Callable, Iterable
from .browser_types import BrowserType
from .qp_whitelist import Whitelist, process_url

logger = logging.getLogger(__name__)


@contextmanager
def copy_locked_dbs(paths: list[pathlib.Path]) -> 'Generator[list[tuple[pathlib.Path, pathlib.Path]], None, None]':
    tmpdir = pathlib.Path(tempfile.mkdtemp(prefix="llm_bh"))
    try:
        copies = []
        for path in paths:
            dst = tmpdir / path.name
            try:
                shutil.copy2(path, dst)
                copies.append((path, dst))
            except OSError as e:
                logger.warning(f"Failed to copy {path} to {dst}: {e}")
        yield copies  # List of (original, copy) tuples
    finally:
        shutil.rmtree(tmpdir)


def copy_locked_db(path: pathlib.Path) -> pathlib.Path:
    tmpdir = pathlib.Path(tempfile.mkdtemp(prefix="llm_bh"))
    dst = tmpdir / path.name
    _ = shutil.copy2(path, dst)
    return dst


_UNIFIED_DB_CONN: Connection | None = None


def sha_label(browser: str, path: Path) -> str:
    h = hashlib.sha1(str(path).encode("utf-8")).hexdigest()[:10]
    return f"{browser}:{h}"


def insert_chrome_history(cur: Cursor, alias: str, profile_label: str) -> None:
    """Insert Chrome browser history into the unified database."""
    sql = (
        """
        INSERT INTO browser_history (browser, profile, url, title, referrer_url, visited_dt)
        SELECT
          'chrome' AS browser,
          ?         AS profile,
          u.url,
          u.title,
          r.url AS referrer_url,
          strftime('%Y-%m-%d %H:00:00', (v.visit_time/1000 - 11644473600*1000)/1000, 'unixepoch') AS visited_dt
        FROM {alias}.urls u
        JOIN {alias}.visits v       ON v.url = u.id
        LEFT JOIN {alias}.visits pv ON pv.id = v.from_visit
        LEFT JOIN {alias}.urls  r   ON r.id = pv.url;
        """
    ).replace("{alias}", alias)
    cur.execute(sql, (profile_label,))


def insert_firefox_history(cur: Cursor, alias: str, profile_label: str) -> None:
    """Insert Firefox browser history into the unified database."""
    sql = (
        """
        INSERT INTO browser_history (browser, profile, url, title, referrer_url, visited_dt)
        SELECT
          'firefox' AS browser,
          ?          AS profile,
          p.url,
          p.title,
          pr.url AS referrer_url,
          strftime('%Y-%m-%d %H:00:00', h.visit_date/1000000, 'unixepoch') AS visited_dt
        FROM {alias}.moz_historyvisits h
        JOIN {alias}.moz_places p         ON p.id = h.place_id
        LEFT JOIN {alias}.moz_historyvisits ph ON ph.id = h.from_visit
        LEFT JOIN {alias}.moz_places pr    ON pr.id = ph.place_id;
        """
    ).replace("{alias}", alias)
    cur.execute(sql, (profile_label,))


def insert_safari_history(cur: Cursor, alias: str, profile_label: str) -> None:
    """Insert Safari browser history into the unified database."""
    sql = (
        """
        INSERT INTO browser_history (browser, profile, url, title, referrer_url, visited_dt)
        SELECT
          'safari' AS browser,
          ?         AS profile,
          i.url,
          v.title,
          NULL AS referrer_url,
          strftime('%Y-%m-%d %H:00:00', v.visit_time + strftime('%s','2001-01-01'), 'unixepoch') AS visited_dt
        FROM {alias}.history_items i
        LEFT JOIN {alias}.history_visits v ON v.history_item = i.id;
        """
    ).replace("{alias}", alias)
    cur.execute(sql, (profile_label,))


def _create_unified_db_connection(dest_db: Path | None) -> Connection:
    """Create and initialize the unified database connection."""
    if dest_db is not None:
        if dest_db.exists():
            dest_db.unlink()
        conn = connect(f"file:{dest_db}?mode=rwc", uri=True)
    else:
        conn = connect(":memory:")

    cur = conn.cursor()
    cur.executescript(
        """
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS browser_history (
          browser      TEXT NOT NULL,
          profile      TEXT,
          url          TEXT NOT NULL,
          title        TEXT,
          referrer_url TEXT,
          visited_dt  DATETIME NOT NULL,
          domain       TEXT,
          stripped_qp  TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_bh_time  ON browser_history(visited_dt);
        CREATE INDEX IF NOT EXISTS idx_bh_url   ON browser_history(url);
        CREATE INDEX IF NOT EXISTS idx_bh_title ON browser_history(title);
        """
    )
    return conn


def _apply_qp_whitelist(conn: Connection, whitelist: Whitelist) -> None:
    """Post-process all rows: apply the query-parameter whitelist."""
    cur = conn.cursor()
    rows = cur.execute("SELECT rowid, url FROM browser_history").fetchall()
    for rowid, raw_url in rows:
        result = process_url(raw_url, whitelist)
        cur.execute(
            "UPDATE browser_history SET url = ?, domain = ?, stripped_qp = ? WHERE rowid = ?",
            (result["url"], result["domain"], result["stripped_qp"], rowid),
        )
    conn.commit()


def _process_browser_sources(conn: Connection, sources: Iterable[tuple[BrowserType, Path]]) -> None:
    """Process and import browser history from all sources."""
    cur = conn.cursor()
    alias_num = 0

    browser_inserters: dict[BrowserType, Callable[[Cursor, str, str], None]] = {
        "chrome": insert_chrome_history,
        "firefox": insert_firefox_history,
        "safari": insert_safari_history,
    }

    with copy_locked_dbs([path for _, path in sources]) as locked_copies:
        for (og_path, copy_path) in locked_copies:
            browser: BrowserType = next(browser for browser, path in sources if path == og_path)
            alias_num += 1

            alias = f"src{alias_num}"
            cur.execute("ATTACH DATABASE ? AS " + alias, (f"file:{copy_path}?immutable=1&mode=ro",))

            profile_label = sha_label(browser, og_path)

            inserter = browser_inserters[browser]
            inserter(cur, alias, profile_label)

            conn.commit()
            cur.execute(f"DETACH DATABASE {alias}")


def build_unified_browser_history_db(
    dest_db: Path | None,
    sources: Iterable[tuple[BrowserType, Path]],
    whitelist: Whitelist | None = None,
) -> Connection:
    conn = _create_unified_db_connection(dest_db)
    _process_browser_sources(conn, sources)
    _apply_qp_whitelist(conn, whitelist if whitelist is not None else {})
    return conn


def get_or_create_unified_db(
    sources: Iterable[tuple[BrowserType, Path]],
    whitelist: Whitelist | None = None,
) -> Connection:
    global _UNIFIED_DB_CONN
    if _UNIFIED_DB_CONN is not None:
        return _UNIFIED_DB_CONN

    # Use in-memory database by default
    conn = build_unified_browser_history_db(None, sources, whitelist)
    _UNIFIED_DB_CONN = conn
    return conn


def cleanup_unified_db() -> None:
    """Close the unified database connection."""
    global _UNIFIED_DB_CONN
    if _UNIFIED_DB_CONN is None:
        return

    try:
        _UNIFIED_DB_CONN.close()
    except Exception:
        # Best-effort cleanup, ignore errors
        pass
    finally:
        _UNIFIED_DB_CONN = None


def run_unified_query(
    conn: Connection, sql: str, params: dict[str, object] | None = None, max_rows: int = 100
) -> list[Any]:
    cur = conn.execute(sql, params or {})
    return cur.fetchmany(max_rows)
