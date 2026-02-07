import sqlite3
import shutil
import pathlib


def get_sqlite_journal_files(db_path: pathlib.Path) -> list[pathlib.Path]:
    """Get all associated journal files for a SQLite database.

    Args:
        db_path: Path to the SQLite database file

    Returns:
        List of paths including the main database file and any
        associated journal/WAL/lock files that exist.
    """
    files = [db_path]

    for suffix in ["-journal", "-wal", "-shm", "-lock"]:
        journal_path = db_path.parent / f"{db_path.name}{suffix}"
        if journal_path.exists():
            files.append(journal_path)

    return files


def create_clean_sqlite_db(
    source_paths: list[pathlib.Path], temp_dir: pathlib.Path
) -> pathlib.Path:
    """Create a clean SQLite database from source files using VACUUM INTO.

    Args:
        source_paths: List of source file paths (main database, journal, and lock files)
        temp_dir: Temporary directory to create the clean database in

    Returns:
        Path to the clean database file
    """
    if not source_paths:
        raise ValueError("source_paths must not be empty")

    # Find the main database file (the one without -journal, -wal, -shm, or -lock suffix)
    # Sort by name length to get the shortest name first (main db should be shortest)
    sorted_paths = sorted(source_paths, key=lambda p: len(p.name))
    main_db_path = sorted_paths[0]

    # Create a temporary copy of all source files
    for src_path in source_paths:
        dst_path = temp_dir / src_path.name
        shutil.copy2(src_path, dst_path)

    # Connect to the copied main database
    main_copy_path = temp_dir / main_db_path.name
    conn = sqlite3.connect(f"file:{main_copy_path}?mode=rw", uri=True)

    try:
        # Create clean database using VACUUM INTO
        clean_db_name = f"{main_db_path.stem}_clean.db"
        clean_db_path = temp_dir / clean_db_name
        conn.execute(f"VACUUM INTO '{clean_db_path}'")
    finally:
        conn.close()

    return clean_db_path
