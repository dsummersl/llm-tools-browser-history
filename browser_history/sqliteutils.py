import sqlite3
import shutil
from pathlib import Path


def get_sqlite_journal_files(db_path: Path) -> list[Path]:
    files = []
    if db_path.exists():
        files.append(db_path)

    for suffix in ["-journal", "-wal", "-shm", "-lock"]:
        journal_path = db_path.parent / f"{db_path.name}{suffix}"
        if journal_path.exists():
            files.append(journal_path)

    return files


def create_clean_sqlite_db(source_paths: list[Path], temp_dir: Path) -> Path:
    if not source_paths:
        raise ValueError("source_paths must not be empty")

    sorted_paths = sorted(source_paths, key=lambda p: len(p.name))
    main_db_path = sorted_paths[0]

    for src_path in source_paths:
        dst_path = temp_dir / src_path.name
        shutil.copy2(src_path, dst_path)

    main_copy_path = temp_dir / main_db_path.name
    conn = sqlite3.connect(f"file:{main_copy_path}?mode=rw", uri=True)

    try:
        clean_db_name = f"{main_db_path.stem}_clean.db"
        clean_db_path = temp_dir / clean_db_name
        conn.execute(f"VACUUM INTO '{clean_db_path}'")
    finally:
        conn.close()

    return clean_db_path
