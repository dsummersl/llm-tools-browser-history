import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
import pathlib
import tempfile
import shutil
import hashlib
from typing import Any, Iterable


def copy_locked_db(path: pathlib.Path) -> pathlib.Path:
    tmpdir = pathlib.Path(tempfile.mkdtemp(prefix="llm_bh"))
    dst = tmpdir / path.name
    _ = shutil.copy2(path, dst)
    return dst


@contextmanager
def history_query(
    sql_query: str, params: dict[str, str], db_path: pathlib.Path
) -> Generator[list[sqlite3.Row], None, None]:
    copied = copy_locked_db(db_path)
    uri = f"file:{copied}?immutable=1&mode=ro"
    con = sqlite3.connect(uri, uri=True)
    con.row_factory = sqlite3.Row
    try:
        cur = con.execute(sql_query, params)
        yield cur.fetchall()
    finally:
        con.close()


_UNIFIED_DB_CONN: sqlite3.Connection | None = None


def sha_label(browser: str, path: Path) -> str:
    h = hashlib.sha1(str(path).encode("utf-8")).hexdigest()[:10]
    return f"{browser}:{h}"


def attach_copy(cur: sqlite3.Cursor, alias: str, path: Path) -> Path:
    copied = copy_locked_db(path)
    uri = f"file:{copied}?immutable=1&mode=ro"
    cur.execute("ATTACH DATABASE ? AS " + alias, (uri,))
    return copied


def build_unified_browser_history_db(dest_db: Path | None, sources: Iterable[tuple[str, Path]]) -> sqlite3.Connection:
    if dest_db is not None:
        if dest_db.exists():
            dest_db.unlink()
        conn = sqlite3.connect(f"file:{dest_db}?mode=rwc", uri=True)
    else:
        # Use in-memory database
        conn = sqlite3.connect(":memory:")

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
          visited_dt  DATETIME NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_bh_time  ON browser_history(visited_dt);
        CREATE INDEX IF NOT EXISTS idx_bh_url   ON browser_history(url);
        CREATE INDEX IF NOT EXISTS idx_bh_title ON browser_history(title);
        """
    )

    tmp_copies: list[Path] = []
    alias_num = 0
    try:
        for browser, path in sources:
            alias_num += 1
            alias = f"src{alias_num}"
            copied = attach_copy(cur, alias, path)
            tmp_copies.append(copied)
            profile_label = sha_label(browser, path)

            if browser == "chrome":
                sql = (
                    """
                    INSERT INTO browser_history (browser, profile, url, title, referrer_url, visited_dt)
                    SELECT
                      'chrome' AS browser,
                      ?         AS profile,
                      CASE
                        WHEN instr(u.url, '?') > 0 THEN substr(u.url, 1, instr(u.url, '?') - 1)
                        ELSE u.url
                      END,
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
            elif browser == "firefox":
                sql = (
                    """
                    INSERT INTO browser_history (browser, profile, url, title, referrer_url, visited_dt)
                    SELECT
                      'firefox' AS browser,
                      ?          AS profile,
                      CASE
                        WHEN instr(p.url, '?') > 0 THEN substr(p.url, 1, instr(p.url, '?') - 1)
                        ELSE p.url
                      END,
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
            elif browser == "safari":
                sql = (
                    """
                    INSERT INTO browser_history (browser, profile, url, title, referrer_url, visited_dt)
                    SELECT
                      'safari' AS browser,
                      ?         AS profile,
                      CASE
                        WHEN instr(i.url, '?') > 0 THEN substr(i.url, 1, instr(i.url, '?') - 1)
                        ELSE i.url
                      END,
                      v.title,
                      NULL AS referrer_url,
                      strftime('%Y-%m-%d %H:00:00', v.visit_time + strftime('%s','2001-01-01'), 'unixepoch') AS visited_dt
                    FROM {alias}.history_items i
                    LEFT JOIN {alias}.history_visits v ON v.history_item = i.id;
                    """
                ).replace("{alias}", alias)
                cur.execute(sql, (profile_label,))

            # First commit changes and then detach:
            conn.commit()
            cur.execute(f"DETACH DATABASE {alias}")
    finally:
        # Best-effort cleanup of temp copies
        for p in tmp_copies:
            try:
                p.unlink()
            except Exception:
                pass

    return conn


def get_or_create_unified_db(sources: Iterable[tuple[str, Path]]) -> sqlite3.Connection:
    global _UNIFIED_DB_CONN
    if _UNIFIED_DB_CONN is not None:
        return _UNIFIED_DB_CONN

    # Use in-memory database by default
    conn = build_unified_browser_history_db(None, sources)
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
    conn: sqlite3.Connection, sql: str, params: dict[str, object] | None = None, max_rows: int = 100
) -> list[Any]:
    cur = conn.execute(sql, params or {})
    return cur.fetchmany(max_rows)
