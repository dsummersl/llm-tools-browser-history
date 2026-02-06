from sqlite3 import Cursor, Connection, connect
import logging
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
import pathlib
import tempfile
import shutil
import hashlib
import os
from typing import Any
from collections.abc import Callable, Iterable
from .browser_types import BrowserType
from .qp_whitelist import Whitelist, ProcessedURL, process_url

logger = logging.getLogger(__name__)


def get_persistent_db_path() -> Path:
    """Get the path to the persistent database file."""
    config_dir = Path.home() / ".config" / "llm-tools-browser-history"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / "history.db"


def compute_file_hash(file_path: Path) -> str:
    """Compute SHA256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def get_file_mtime(file_path: Path) -> float:
    """Get file modification time."""
    return os.path.getmtime(file_path)


def _should_process_source(
    cur: Cursor, browser: BrowserType, profile: str, source_path: Path
) -> tuple[bool, str | None]:
    """Check if a browser source needs processing.

    Returns (needs_processing, existing_hash)
    """
    cur.execute(
        """
        SELECT sha256_hash, last_modified 
        FROM browser_metadata 
        WHERE browser = ? AND profile = ?
        """,
        (browser, profile),
    )
    row = cur.fetchone()

    if row is None:
        # No metadata exists, needs processing
        return True, None

    existing_hash, stored_mtime = row
    current_mtime = get_file_mtime(source_path)

    # Check if file has been modified since last processing
    if current_mtime > stored_mtime:
        # File modified, needs reprocessing
        return True, existing_hash

    # File not modified, check hash to be sure
    current_hash = compute_file_hash(source_path)
    if current_hash != existing_hash:
        # Hash changed, needs reprocessing
        return True, existing_hash

    # No changes detected
    return False, existing_hash


def _update_metadata(
    cur: Cursor, browser: BrowserType, profile: str, source_path: Path, sha256_hash: str
) -> None:
    """Update metadata for a processed browser source."""
    cur.execute(
        """
        INSERT OR REPLACE INTO browser_metadata 
        (browser, profile, source_path, sha256_hash, last_modified, processed_at)
        VALUES (?, ?, ?, ?, ?, datetime('now'))
        """,
        (browser, profile, str(source_path), sha256_hash, get_file_mtime(source_path)),
    )


@contextmanager
def copy_locked_dbs(
    paths: list[pathlib.Path],
) -> "Generator[list[tuple[pathlib.Path, pathlib.Path]], None, None]":
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


def _execute_sql(sql: str, cur: Cursor, params: tuple[str, ...] = ()) -> None:
    cur.execute(sql, params)


def insert_chrome_history(cur: Cursor, alias: str, profile_label: str) -> None:
    """Insert Chrome browser history into the unified database."""
    _execute_sql(
        (
            """
        INSERT INTO browser_history (browser, profile, url, title, referrer_url, visited_dt, domain, stripped_qp, referrer_domain, referrer_stripped_qp)
        SELECT
          'chrome' AS browser,
          ?         AS profile,
          process_url_url(u.url) AS url,
          u.title,
          process_url_url(r.url) AS referrer_url,
          strftime('%Y-%m-%d %H:00:00', (v.visit_time/1000 - 11644473600*1000)/1000, 'unixepoch') AS visited_dt,
          process_url_domain(u.url) AS domain,
          process_url_stripped(u.url) AS stripped_qp,
          process_url_domain(r.url) AS referrer_domain,
          process_url_stripped(r.url) AS referrer_stripped_qp
        FROM {alias}.urls u
        JOIN {alias}.visits v       ON v.url = u.id
        LEFT JOIN {alias}.visits pv ON pv.id = v.from_visit
        LEFT JOIN {alias}.urls  r   ON r.id = pv.url;
        """
        ).replace("{alias}", alias),
        cur,
        (profile_label,),
    )


def insert_firefox_history(cur: Cursor, alias: str, profile_label: str) -> None:
    """Insert Firefox browser history into the unified database."""
    _execute_sql(
        (
            """
        INSERT INTO browser_history (browser, profile, url, title, referrer_url, visited_dt, domain, stripped_qp, referrer_domain, referrer_stripped_qp)
        SELECT
          'firefox' AS browser,
          ?          AS profile,
          process_url_url(p.url) AS url,
          p.title,
          process_url_url(pr.url) AS referrer_url,
          strftime('%Y-%m-%d %H:00:00', h.visit_date/1000000, 'unixepoch') AS visited_dt,
          process_url_domain(p.url) AS domain,
          process_url_stripped(p.url) AS stripped_qp,
          process_url_domain(pr.url) AS referrer_domain,
          process_url_stripped(pr.url) AS referrer_stripped_qp
        FROM {alias}.moz_historyvisits h
        JOIN {alias}.moz_places p         ON p.id = h.place_id
        LEFT JOIN {alias}.moz_historyvisits ph ON ph.id = h.from_visit
        LEFT JOIN {alias}.moz_places pr    ON pr.id = ph.place_id;
        """
        ).replace("{alias}", alias),
        cur,
        (profile_label,),
    )


def insert_safari_history(cur: Cursor, alias: str, profile_label: str) -> None:
    """Insert Safari browser history into the unified database."""
    _execute_sql(
        (
            """
        INSERT INTO browser_history (browser, profile, url, title, referrer_url, visited_dt, domain, stripped_qp, referrer_domain, referrer_stripped_qp)
        SELECT
          'safari' AS browser,
          ?         AS profile,
          process_url_url(i.url) AS url,
          v.title,
          NULL AS referrer_url,
          strftime('%Y-%m-%d %H:00:00', v.visit_time + strftime('%s','2001-01-01'), 'unixepoch') AS visited_dt,
          process_url_domain(i.url) AS domain,
          process_url_stripped(i.url) AS stripped_qp,
          NULL AS referrer_domain,
          NULL AS referrer_stripped_qp
        FROM {alias}.history_items i
        LEFT JOIN {alias}.history_visits v ON v.history_item = i.id;
        """
        ).replace("{alias}", alias),
        cur,
        (profile_label,),
    )


def _register_sqlite_functions(conn: Connection, whitelist: Whitelist) -> None:
    """Register custom SQLite functions for URL processing with memoization."""

    # Cache for processed URLs
    _url_cache: dict[str, ProcessedURL] = {}

    def _get_cached_result(raw_url: str) -> ProcessedURL | None:
        """Get cached result for URL, returns None if not cached."""
        return _url_cache.get(raw_url)

    def _cache_result(raw_url: str, result: ProcessedURL) -> None:
        """Cache result for URL."""
        _url_cache[raw_url] = result

    def process_url_url_only(raw_url: str | None) -> str | None:
        """SQLite function that returns only the processed URL."""
        if raw_url is None:
            return None
        if not raw_url:
            return ""

        # Check cache first
        cached = _get_cached_result(raw_url)
        if cached is not None:
            return cached["url"]

        # Process and cache
        result = process_url(raw_url, whitelist)
        _cache_result(raw_url, result)
        return result["url"]

    def process_url_domain_only(raw_url: str | None) -> str | None:
        """SQLite function that returns only the domain."""
        if raw_url is None:
            return None
        if not raw_url:
            return ""

        # Check cache first
        cached = _get_cached_result(raw_url)
        if cached is not None:
            return cached["domain"]

        # Process and cache
        result = process_url(raw_url, whitelist)
        _cache_result(raw_url, result)
        return result["domain"]

    def process_url_stripped_only(raw_url: str | None) -> str | None:
        """SQLite function that returns only the stripped query parameters."""
        if raw_url is None:
            return None
        if not raw_url:
            return ""

        # Check cache first
        cached = _get_cached_result(raw_url)
        if cached is not None:
            return cached["stripped_qp"]

        # Process and cache
        result = process_url(raw_url, whitelist)
        _cache_result(raw_url, result)
        return result["stripped_qp"]

    # Register functions with different numbers of return values
    conn.create_function("process_url_url", 1, process_url_url_only, deterministic=True)
    conn.create_function("process_url_domain", 1, process_url_domain_only, deterministic=True)
    conn.create_function("process_url_stripped", 1, process_url_stripped_only, deterministic=True)


def _create_unified_db_connection(dest_db: Path | None, whitelist: Whitelist) -> Connection:
    """Create and initialize the unified database connection."""
    if dest_db is not None:
        logger.debug("Opening unified database at %s", dest_db)
        conn = connect(f"file:{dest_db}?mode=rwc", uri=True)
    else:
        logger.debug("Creating in-memory unified database")
        conn = connect(":memory:")

    # Register SQLite functions before creating tables
    _register_sqlite_functions(conn, whitelist)

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
          stripped_qp  TEXT,
          referrer_domain TEXT,
          referrer_stripped_qp TEXT
        );
        CREATE TABLE IF NOT EXISTS browser_metadata (
            browser TEXT NOT NULL,
            profile TEXT NOT NULL,
            source_path TEXT NOT NULL,
            sha256_hash TEXT NOT NULL,
            last_modified REAL NOT NULL,
            processed_at DATETIME NOT NULL,
            PRIMARY KEY (browser, profile)
        );
        CREATE INDEX IF NOT EXISTS idx_bh_time  ON browser_history(visited_dt);
        CREATE INDEX IF NOT EXISTS idx_bh_url   ON browser_history(url);
        CREATE INDEX IF NOT EXISTS idx_bh_title ON browser_history(title);
        """
    )
    return conn


def _process_browser_sources(
    conn: Connection, sources: Iterable[tuple[BrowserType, str, Path]]
) -> None:
    """Process and import browser history from all sources."""
    cur = conn.cursor()
    alias_num = 0

    browser_inserters: dict[BrowserType, Callable[[Cursor, str, str], None]] = {
        "chrome": insert_chrome_history,
        "firefox": insert_firefox_history,
        "safari": insert_safari_history,
    }

    # Group sources by browser and profile
    sources_to_process = []
    for b, p, source_path in sources:
        needs_processing, existing_hash = _should_process_source(cur, b, p, source_path)

        if needs_processing:
            logger.debug(f"Source {b}:{p} needs processing (changed or new)")
            # Delete existing rows for this browser/profile if they exist
            if existing_hash is not None:
                profile_label = f"{b}:{p}"
                cur.execute(
                    "DELETE FROM browser_history WHERE browser = ? AND profile = ?",
                    (b, profile_label),
                )
                logger.debug(f"Deleted existing rows for {b}:{profile_label}")

            sources_to_process.append((b, p, source_path))
        else:
            logger.debug(f"Skipping {b}:{p} - no changes detected")

    if not sources_to_process:
        logger.debug("No sources need processing")
        return

    with copy_locked_dbs([path for _, _, path in sources_to_process]) as locked_copies:
        for og_path, copy_path in locked_copies:
            # Find the browser and profile name for this path
            browser: BrowserType = next(b for b, p, path in sources_to_process if path == og_path)
            profile_name: str = next(p for b, p, path in sources_to_process if path == og_path)
            alias_num += 1
            logger.debug(
                f"Processing {browser} history from {og_path} (profile: {profile_name}, copy at {copy_path})"
            )

            alias = f"src{alias_num}"
            cur.execute("ATTACH DATABASE ? AS " + alias, (f"file:{copy_path}?immutable=1&mode=ro",))

            profile_label = f"{browser}:{profile_name}"

            inserter = browser_inserters[browser]
            inserter(cur, alias, profile_label)

            # Update metadata after successful processing
            sha256_hash = compute_file_hash(og_path)
            _update_metadata(cur, browser, profile_name, og_path, sha256_hash)

            conn.commit()
            cur.execute(f"DETACH DATABASE {alias}")


def build_unified_browser_history_db(
    dest_db: Path | None,
    sources: Iterable[tuple[BrowserType, str, Path]],
    whitelist: Whitelist | None = None,
) -> Connection:
    conn = _create_unified_db_connection(dest_db, whitelist if whitelist is not None else {})
    _process_browser_sources(conn, sources)
    return conn


def get_or_create_unified_db(
    sources: Iterable[tuple[BrowserType, str, Path]],
    whitelist: Whitelist | None = None,
    db_path: Path | None = None,
) -> Connection:
    global _UNIFIED_DB_CONN
    if _UNIFIED_DB_CONN is not None:
        return _UNIFIED_DB_CONN

    # Use persistent database by default
    if db_path is None:
        db_path = get_persistent_db_path()

    conn = build_unified_browser_history_db(db_path, sources, whitelist)
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


def run_unified_query_with_headers(
    conn: Connection, sql: str, params: dict[str, object] | None = None, max_rows: int = 100
) -> tuple[list[str], list[Any]]:
    """Like :func:`run_unified_query` but also returns column headers."""
    cur = conn.execute(sql, params or {})
    headers = [desc[0] for desc in cur.description] if cur.description else []
    return headers, cur.fetchmany(max_rows)
