from __future__ import annotations
import pathlib
import datetime
import glob

from browser_history.types import NormalizedRow
from .sqlite import history_query

WEBKIT_EPOCH = datetime.datetime(1601, 1, 1, tzinfo=datetime.timezone.utc)


def find_chrome_history_paths() -> list[pathlib.Path]:
    home = pathlib.Path.home()
    candidates: list[pathlib.Path] = []
    mac_chrome = home / "Library" / "Application Support" / "Google" / "Chrome" / "*" / "History"
    mac_chromium = home / "Library" / "Application Support" / "Chromium" / "*" / "History"
    linux_chrome = home / ".config" / "google-chrome" / "*" / "History"
    linux_chromium = home / ".config" / "chromium" / "*" / "History"
    snap_chromium = home / "snap" / "chromium" / "common" / ".config" / "chromium" / "*" / "History"
    for pattern in (mac_chrome, mac_chromium, linux_chrome, linux_chromium, snap_chromium):
        candidates.extend(pathlib.Path(p) for p in glob.glob(str(pattern)))
    return candidates


def _iso_from_webkit_microseconds(us: int | None) -> str | None:
    if not us:
        return None
    dt = WEBKIT_EPOCH + datetime.timedelta(microseconds=int(us))
    return dt.isoformat()


def _webkit_from_datetime(dt: datetime.datetime) -> int:
    dt = dt.astimezone(datetime.timezone.utc)
    delta = dt - WEBKIT_EPOCH
    return int(delta.total_seconds() * 1_000_000)


def query_chrome(
    db_path: pathlib.Path,
    text: str | None = None,
    start: datetime.datetime | None = None,
    end: datetime.datetime | None = None,
    limit: int = 50,
) -> list[NormalizedRow]:
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

    params = {"limit": limit}
    if text_like:
        params["text"] = text_like
    if start_wk:
        params["start"] = start_wk
    if end_wk:
        params["end"] = end_wk

    with history_query(SQL, params, db_path) as rows:
        return [
            NormalizedRow(
                url=r["url"],
                title=r["title"],
                browser="chrome",
                visited_at=_iso_from_webkit_microseconds(r["visited_at_wk"])
                if r["visited_at_wk"]
                else None,
                visit_count=r["visit_count"],
                profile_path=str(db_path.parent),
            )
            for r in rows
        ]
