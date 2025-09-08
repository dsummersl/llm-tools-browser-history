from __future__ import annotations
import pathlib
import datetime

import glob

from browser_history.types import NormalizedRow
from .sqlite import history_query

APPLE_EPOCH = datetime.datetime(2001, 1, 1, tzinfo=datetime.timezone.utc)


def find_safari_history_paths() -> list[pathlib.Path]:
    """Return list of Safari History.db paths on this system.

    Currently supports macOS default location under ~/Library/Safari/History.db.
    """
    home = pathlib.Path.home()
    candidates: list[pathlib.Path] = []
    mac_history = home / "Library" / "Safari" / "History.db"
    # Some users may have multiple History.db.* copies; include those as well
    mac_history_glob = home / "Library" / "Safari" / "History.db*"
    if mac_history.exists():
        candidates.append(mac_history)
    # Only include files with .db extension
    for pattern in (mac_history_glob,):
        candidates.extend(
            pathlib.Path(p)
            for p in glob.glob(str(pattern))
            if pathlib.Path(p).name == "History.db"
        )
    # Deduplicate while preserving order
    seen = set()
    unique: list[pathlib.Path] = []
    for p in candidates:
        if p not in seen and p.is_file():
            unique.append(p)
            seen.add(p)
    return unique




def _iso_from_apple_seconds(val: float | int | None) -> str | None:
    if val is None:
        return None
    # Safari stores seconds since 2001-01-01 in REAL (float). Accept int as well.
    seconds = float(val)
    dt = APPLE_EPOCH + datetime.timedelta(seconds=seconds)
    return dt.isoformat()


def _apple_seconds_from_datetime(dt: datetime.datetime) -> float:
    dt = dt.astimezone(datetime.timezone.utc)
    delta = dt - APPLE_EPOCH
    return delta.total_seconds()


def query_safari(
    db_path: pathlib.Path,
    text: str | None = None,
    start: datetime.datetime | None = None,
    end: datetime.datetime | None = None,
    limit: int = 50,
) -> list[NormalizedRow]:
    """Query Safari History.db and return normalized rows.

    Joins history_items with history_visits and filters by text and date range.
    """
    text_like = f"%{text}%" if text else None
    start_s = _apple_seconds_from_datetime(start) if start else None
    end_s = _apple_seconds_from_datetime(end) if end else None

    SQL = f"""
    SELECT i.url, v.title, i.visit_count, v.visit_time AS visited_at_s
    FROM history_items i
    LEFT JOIN history_visits v ON v.history_item = i.id
    WHERE 1=1
      {"AND (i.url LIKE :text OR v.title LIKE :text)" if text_like else ""}
      {"AND v.visit_time >= :start" if start_s is not None else ""}
      {"AND v.visit_time <= :end" if end_s is not None else ""}
    ORDER BY v.visit_time DESC
    LIMIT :limit
    """

    params: dict[str, object] = {"limit": limit}
    if text_like:
        params["text"] = text_like
    if start_s is not None:
        params["start"] = start_s
    if end_s is not None:
        params["end"] = end_s

    with history_query(SQL, params, db_path) as rows:
        return [
            NormalizedRow(
                url=r["url"],
                title=r["title"],
                browser="safari",
                visited_at=_iso_from_apple_seconds(r["visited_at_s"]) if r["visited_at_s"] else None,
                visit_count=r["visit_count"],
                profile_path=str(db_path.parent),
            )
            for r in rows
        ]

