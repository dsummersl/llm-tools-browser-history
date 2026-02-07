import pathlib
import datetime
import glob
import logging
import sqlite3
import shutil

logger = logging.getLogger(__name__)

WEBKIT_EPOCH = datetime.datetime(1601, 1, 1, tzinfo=datetime.timezone.utc)


def find_chrome_history_paths() -> list[tuple[str, pathlib.Path]]:
    home = pathlib.Path.home()
    candidates: list[tuple[str, pathlib.Path]] = []
    mac_chrome = home / "Library" / "Application Support" / "Google" / "Chrome" / "*" / "History"
    mac_chromium = home / "Library" / "Application Support" / "Chromium" / "*" / "History"
    linux_chrome = home / ".config" / "google-chrome" / "*" / "History"
    linux_chromium = home / ".config" / "chromium" / "*" / "History"
    snap_chromium = home / "snap" / "chromium" / "common" / ".config" / "chromium" / "*" / "History"
    for pattern in (mac_chrome, mac_chromium, linux_chrome, linux_chromium, snap_chromium):
        logger.debug(f"Checking for Chrome history at: {pattern}")
        for p in glob.glob(str(pattern)):
            path = pathlib.Path(p)
            profile_name = path.parent.name
            logger.debug(f"Found Chrome history at: {path} (profile: {profile_name})")
            candidates.append((profile_name, path))
    return candidates


def get_chrome_history_query(alias: str, profile_label: str) -> str:
    """Generate SELECT query for Chrome browser history.

    Returns just the SELECT portion (without INSERT INTO) that can be used
    with insert_selected_records.
    """
    query = f"""
        SELECT
          'chrome' AS browser,
          '{profile_label}' AS profile,
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
        LEFT JOIN {alias}.urls  r   ON r.id = pv.url
        """
    return query


def get_chrome_journal_files(history_path: pathlib.Path) -> list[pathlib.Path]:
    """Get all associated journal files for a Chrome history database.

    Returns a list of paths including the main History file and any
    History-journal files.
    """
    files = [history_path]

    # Check for History-journal file
    journal_path = history_path.parent / f"{history_path.name}-journal"
    if journal_path.exists():
        files.append(journal_path)

    # Check for other possible journal/wal files
    for suffix in ["-wal", "-shm"]:
        wal_path = history_path.parent / f"{history_path.name}{suffix}"
        if wal_path.exists():
            files.append(wal_path)

    return files


def create_clean_chrome_db(
    source_paths: list[pathlib.Path], temp_dir: pathlib.Path
) -> pathlib.Path:
    """Create a clean Chrome database from source files using VACUUM INTO.

    Args:
        source_paths: List of source file paths (History and journal files)
        temp_dir: Temporary directory to create the clean database in

    Returns:
        Path to the clean database file
    """
    # Find the main database file (the one without -journal, -wal, or -shm suffix)
    # Sort by name length to get the shortest name first (main db should be shortest)
    sorted_paths = sorted(source_paths, key=lambda p: len(p.name))
    main_db_path = sorted_paths[0]

    # Create a temporary copy of all source files
    copied_paths = []
    for src_path in source_paths:
        dst_path = temp_dir / src_path.name
        shutil.copy2(src_path, dst_path)
        copied_paths.append(dst_path)

    # Connect to the copied main database
    main_copy_path = temp_dir / main_db_path.name
    conn = sqlite3.connect(f"file:{main_copy_path}?mode=rw", uri=True)

    # Create clean database using VACUUM INTO
    clean_db_name = f"{main_db_path.stem}_clean.db"
    clean_db_path = temp_dir / clean_db_name
    conn.execute(f"VACUUM INTO '{clean_db_path}'")
    conn.close()

    return clean_db_path
