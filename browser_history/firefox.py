from __future__ import annotations
import glob
import pathlib
import datetime

from browser_history.types import NormalizedRow
from .sqlite import history_query

MICROSECOND = 1_000_000


def find_firefox_places_sqlite() -> list[pathlib.Path]:
    home = pathlib.Path.home()
    candidates = []
    mac = home / "Library" / "Application Support" / "Firefox" / "Profiles" / "*" / "places.sqlite"
    linux = home / ".mozilla" / "firefox" / "*" / "places.sqlite"
    snap = home / "snap" / "firefox" / "common" / ".mozilla" / "firefox" / "*" / "places.sqlite"
    for pattern in (mac, linux, snap):
        candidates.extend(pathlib.Path(p) for p in glob.glob(str(pattern)))
    return candidates


def _iso_from_microseconds(us: int) -> str:
    dt = datetime.datetime.fromtimestamp(us / MICROSECOND, tz=datetime.timezone.utc)
    return dt.isoformat()


def query_firefox(
    db_path: pathlib.Path,
    text: str | None = None,
    start: datetime.datetime | None = None,
    end: datetime.datetime | None = None,
    limit: int = 50,
) -> list[NormalizedRow]:
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

    params = {"limit": limit}
    if text_like:
        params["text"] = text_like
    if start_us:
        params["start"] = start_us
    if end_us:
        params["end"] = end_us

    with history_query(SQL, params, db_path) as rows:
        return list(map(lambda r: NormalizedRow(
            url=r["url"],
            title=r["title"],
            browser="firefox",
            visited_at=_iso_from_microseconds(r["visited_at_us"]) if r["visited_at_us"] else None,
            visit_count=r["visit_count"],
            profile_path=str(db_path.parent),
        ), rows))
