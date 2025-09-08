from __future__ import annotations
import json, datetime, pathlib
import llm
from typing import Iterable

from .firefox import query_firefox, find_firefox_places_sqlite
from .chrome import query_chrome, find_chrome_history_paths
from .safari import query_safari, find_safari_history_paths
from .types import BrowserType


class BrowserHistory(llm.Toolbox):
    """
    Toolbox allowing search through browser history.
    """

    def __init__(self, sources: Iterable[str | None] = None):
        self.sources: list[tuple[str, pathlib.Path]] = []

        if not sources:
            sources = [b.value for b in BrowserType]

        if "firefox" in sources:
            for p in find_firefox_places_sqlite():
                self.sources.append(("firefox", p))
        if "chrome" in sources:
            for p in find_chrome_history_paths():
                # Heuristic: label as chromium if path suggests Chromium
                ps = [part.lower() for part in p.parts]
                self.sources.append(("chrome", p))
        if "safari" in sources:
            for p in find_safari_history_paths():
                self.sources.append(("safari", p))

    def _parse_iso(self, s: str | None) -> datetime.datetime | None:
        if not s:
            return None
        dt = datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        return dt.astimezone(datetime.timezone.utc)

    def search(
        self,
        text: str | None = None,
        start: str | None = None,
        end: str | None = None,
        limit: int = 50,
    ) -> str:
        """
        Search locally installed browser histories.
        - text: Substring to search for in URL or title (case-insensitive).
        - start: ISO 8601 datetime string for the start of the date range (inclusive).
        - end: ISO 8601 datetime string for the end of the date range (inclusive).
        - limit: Maximum number of results to return per browser source (default 50).
        """
        start_dt = self._parse_iso(start) if start else None
        end_dt = self._parse_iso(end) if end else None

        rows = []
        for browser, browser_path in self.sources:
            if browser == "chrome":
                rows.extend(
                    query_chrome(
                        browser_path,
                        text=text,
                        start=start_dt,
                        end=end_dt,
                        limit=limit,
                    )
                )
            elif browser == "firefox":
                rows.extend(
                    query_firefox(
                        browser_path,
                        text,
                        start_dt,
                        end_dt,
                        limit,
                    )
                )
            elif browser == "safari":
                rows.extend(
                    query_safari(
                        browser_path,
                        text,
                        start_dt,
                        end_dt,
                        limit,
                    )
                )

        return json.dumps(rows, indent=2)
