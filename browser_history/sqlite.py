import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
import pathlib
import tempfile
import shutil


def _copy_locked_db(path: pathlib.Path) -> pathlib.Path:
    tmpdir = pathlib.Path(tempfile.mkdtemp(prefix="llm_bh"))
    dst = tmpdir / path.name
    _ = shutil.copy2(path, dst)
    return dst


@contextmanager
def history_query(
    sql_query: str, params: dict, db_path: pathlib.Path
) -> Generator[list[sqlite3.Row], None, None]:
    copied = _copy_locked_db(db_path)
    uri = f"file:{copied}?immutable=1&mode=ro"
    con = sqlite3.connect(uri, uri=True)
    con.row_factory = sqlite3.Row
    try:
        cur = con.execute(sql_query, params)
        yield cur.fetchall()
    finally:
        con.close()
