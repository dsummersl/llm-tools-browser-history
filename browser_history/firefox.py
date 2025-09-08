from __future__ import annotations
import glob
import pathlib
import sqlite3
import tempfile
import shutil
import datetime
from typing import Iterable, Optional, Dict, Any, List

MICROSECOND = 1_000_000


def find_firefox_places_sqlite() -> List[pathlib.Path]:
    home = pathlib.Path.home()
    candidates = []
    mac = home / "Library" / "Application Support" / "Firefox" / "Profiles" / "*" / "places.sqlite"
    linux = home / ".mozilla" / "firefox" / "*" / "places.sqlite"
    snap = home / "snap" / "firefox" / "common" / ".mozilla" / "firefox" / "*" / "places.sqlite"
    for pattern in (mac, linux, snap):
        candidates.extend(pathlib.Path(p) for p in glob.glob(str(pattern)))
    return candidates


def get_default_firefox_places() -> Optional[pathlib.Path]:
    paths = find_firefox_places_sqlite()
    if not paths:
        return None
    preferred = [p for p in paths if "default-release" in str(p.parent)]
    if preferred:
        preferred.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return preferred[0]
    paths.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return paths[0]


def _copy_locked_db(path: pathlib.Path) -> pathlib.Path:
    tmpdir = pathlib.Path(tempfile.mkdtemp(prefix="llm_bh_ff_"))
    dst = tmpdir / f"{path.name}"
    shutil.copy2(path, dst)
    return dst


def _iso_from_microseconds(us: Optional[int]) -> Optional[str]:
    if not us:
        return None
    dt = datetime.datetime.utcfromtimestamp(us / MICROSECOND).replace(tzinfo=datetime.timezone.utc)
    return dt.isoformat()


def query_firefox(
    db_path: pathlib.Path = None,
    text: Optional[str] = None,
    start: Optional[datetime.datetime] = None,
    end: Optional[datetime.datetime] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []

    text_like = f"%{text}%" if text else None
    start_us = int(start.timestamp() * MICROSECOND) if start else None
    end_us = int(end.timestamp() * MICROSECOND) if end else None

    SQL = f"""
    SELECT p.url, p.title, p.visit_count, v.visit_date AS visited_at_us
    FROM moz_places p
    LEFT JOIN moz_historyvisits v ON v.place_id = p.id
    WHERE 1=1
      {"AND (p.url LIKE :text OR p.title LIKE :text)" if text_like else ""}
      {"AND v.visit_date >= :start" if start_us else ""}
      {"AND v.visit_date <= :end" if end_us else ""}
    ORDER BY v.visit_date DESC NULLS LAST, p.last_visit_date DESC NULLS LAST
    LIMIT :limit
    """

    copied = _copy_locked_db(db_path)
    uri = f"file:{copied}?immutable=1&mode=ro"
    con = sqlite3.connect(uri, uri=True)
    con.row_factory = sqlite3.Row
    params = {"limit": limit}
    if text_like:
        params["text"] = text_like
    if start_us:
        params["start"] = start_us
    if end_us:
        params["end"] = end_us
    cur = con.execute(SQL, params)
    for row in cur.fetchall():
        results.append(
            {
                "url": row["url"],
                "title": row["title"],
                "browser": "firefox",
                "visited_at": _iso_from_microseconds(row["visited_at_us"]),
                "visit_count": row["visit_count"],
                "profile_path": str(db_path.parent),
            }
        )
    con.close()
    return results[:limit]
