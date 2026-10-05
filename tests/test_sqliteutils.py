import sqlite3
from pathlib import Path

import pytest

from browser_history.sqliteutils import create_clean_sqlite_db, get_sqlite_journal_files


def test_get_sqlite_journal_files(tmp_path: Path):
    db_path = tmp_path / "test.db"
    db_path.touch()

    (tmp_path / "test.db-journal").touch()
    (tmp_path / "test.db-wal").touch()
    (tmp_path / "test.db-shm").touch()
    (tmp_path / "test.db-lock").touch()

    files = get_sqlite_journal_files(db_path)

    assert len(files) == 5
    assert db_path in files
    assert (tmp_path / "test.db-journal") in files
    assert (tmp_path / "test.db-wal") in files
    assert (tmp_path / "test.db-shm") in files
    assert (tmp_path / "test.db-lock") in files


def test_get_sqlite_journal_files_non_existent(tmp_path: Path):
    db_path = tmp_path / "non_existent.db"

    files = get_sqlite_journal_files(db_path)
    assert len(files) == 0

    (tmp_path / "non_existent.db-journal").touch()
    files = get_sqlite_journal_files(db_path)
    assert len(files) == 1
    assert (tmp_path / "non_existent.db-journal") in files
    assert db_path not in files


def test_create_clean_sqlite_db_empty_paths(tmp_path: Path):
    with pytest.raises(ValueError, match="source_paths must not be empty"):
        create_clean_sqlite_db([], tmp_path)


def test_create_clean_sqlite_db_lock_file(tmp_path: Path):
    db_path = tmp_path / "test_lock.db"

    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE test (val TEXT)")
    conn.execute("INSERT INTO test (val) VALUES ('locked')")
    conn.commit()
    conn.close()

    (tmp_path / "test_lock.db-lock").touch()

    source_files = get_sqlite_journal_files(db_path)
    assert (tmp_path / "test_lock.db-lock") in source_files

    temp_work_dir = tmp_path / "work"
    temp_work_dir.mkdir()

    clean_db_path = create_clean_sqlite_db(source_files, temp_work_dir)

    assert clean_db_path.exists()

    conn = sqlite3.connect(clean_db_path)
    res = conn.execute("SELECT val FROM test").fetchone()
    assert res[0] == "locked"
    conn.close()


def test_create_clean_sqlite_db_hot_wal(tmp_path: Path):
    db_path = tmp_path / "hot_wal.db"

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("CREATE TABLE test (val TEXT)")
    conn.execute("INSERT INTO test (val) VALUES ('persistent')")
    conn.commit()

    conn.execute("INSERT INTO test (val) VALUES ('in-wal')")
    conn.commit()

    wal_path = tmp_path / "hot_wal.db-wal"
    assert wal_path.exists()

    source_files = get_sqlite_journal_files(db_path)
    assert wal_path in source_files
    assert (tmp_path / "hot_wal.db-shm") in source_files

    temp_work_dir = tmp_path / "work"
    temp_work_dir.mkdir()

    clean_db_path = create_clean_sqlite_db(source_files, temp_work_dir)

    conn.close()

    assert clean_db_path.exists()

    conn_clean = sqlite3.connect(clean_db_path)
    rows = conn_clean.execute("SELECT val FROM test ORDER BY val").fetchall()
    assert len(rows) == 2
    assert rows[0][0] == "in-wal"
    assert rows[1][0] == "persistent"
    conn_clean.close()
