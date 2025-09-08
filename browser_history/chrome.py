from __future__ import annotations
import pathlib
import sqlite3
import tempfile
import shutil
import datetime
import glob
from typing import Iterable, Optional, Dict, Any, List

WEBKIT_EPOCH = datetime.datetime(1601, 1, 1, tzinfo=datetime.timezone.utc)


def find_chrome_history_paths() -> List[pathlib.Path]:
    home = pathlib.Path.home()
    candidates: List[pathlib.Path] = []
    mac_chrome = home / "Library" / "Application Support" / "Google" / "Chrome" / "*" / "History"
    mac_chromium = home / "Library" / "Application Support" / "Chromium" / "*" / "History"
    linux_chrome = home / ".config" / "google-chrome" / "*" / "History"
    linux_chromium = home / ".config" / "chromium" / "*" / "History"
    snap_chromium = home / "snap" / "chromium" / "common" / ".config" / "chromium" / "*" / "History"
    for pattern in (mac_chrome, mac_chromium, linux_chrome, linux_chromium, snap_chromium):
        candidates.extend(pathlib.Path(p) for p in glob.glob(str(pattern)))
    return candidates


def get_default_chrome_history() -> Optional[pathlib.Path]:
    paths = find_chrome_history_paths()
    if not paths:
        return None
    preferred = [p for p in paths if p.parent.name.lower() == "default"]
    if preferred:
        preferred.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return preferred[0]
    paths.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return paths[0]


def _copy_locked_db(path: pathlib.Path) -> pathlib.Path:
    tmpdir = pathlib.Path(tempfile.mkdtemp(prefix="llm_bh_ch_"))
    dst = tmpdir / path.name
    shutil.copy2(path, dst)
    return dst


def _iso_from_webkit_microseconds(us: Optional[int]) -> Optional[str]:
    if not us:
        return None
    dt = WEBKIT_EPOCH + datetime.timedelta(microseconds=int(us))
    return dt.isoformat()


def _webkit_from_datetime(dt: datetime.datetime) -> int:
    dt = dt.astimezone(datetime.timezone.utc)
    delta = dt - WEBKIT_EPOCH
    return int(delta.total_seconds() * 1_000_000)


def query_chrome(
    db_path: pathlib.Path = None,
    text: Optional[str] = None,
    start: Optional[datetime.datetime] = None,
    end: Optional[datetime.datetime] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []

    text_like = f"%{text}%" if text else None
    start_wk = _webkit_from_datetime(start) if start else None
    end_wk = _webkit_from_datetime(end) if end else None

    SQL = f"""
    SELECT u.url, u.title, u.visit_count, v.visit_time AS visited_at_wk
    FROM urls u
    LEFT JOIN visits v ON v.url = u.id
    WHERE 1=1
      {"AND (u.url LIKE :text OR u.title LIKE :text)" if text_like else ""}
      {"AND v.visit_time >= :start" if start_wk else ""}
      {"AND v.visit_time <= :end" if end_wk else ""}
    ORDER BY v.visit_time DESC
    LIMIT :limit
    """

    copied = _copy_locked_db(db_path)
    uri = f"file:{copied}?immutable=1&mode=ro"
    con = sqlite3.connect(uri, uri=True)
    con.row_factory = sqlite3.Row
    params = {"limit": limit}
    if text_like:
        params["text"] = text_like
    if start_wk:
        params["start"] = start_wk
    if end_wk:
        params["end"] = end_wk
    cur = con.execute(SQL, params)
    for row in cur.fetchall():
        results.append(
            {
                "url": row["url"],
                "title": row["title"],
                "browser": "chrome",
                "visited_at": _iso_from_webkit_microseconds(row["visited_at_wk"]),
                "visit_count": row["visit_count"],
                "profile_path": str(db_path.parent),
            }
        )
    con.close()
    return results[:limit]
