from __future__ import annotations
import json
import datetime
import pathlib
import llm
from collections.abc import Iterable
from typing import get_args


from .firefox import find_firefox_places_sqlite
from .chrome import find_chrome_history_paths
from .safari import find_safari_history_paths
from .types import BrowserType
from .sqlite import get_or_create_unified_db, run_unified_query


class BrowserHistory(llm.Toolbox):
    """
    Toolbox allowing search through browser history.
    """

    def __init__(self, sources: Iterable[str | None] = None):
        self.sources: list[tuple[str, pathlib.Path]] = []

        if not sources:
            sources = get_args(BrowserType)

        if "firefox" in sources:
            for p in find_firefox_places_sqlite():
                self.sources.append(("firefox", p))
        if "chrome" in sources:
            for p in find_chrome_history_paths():
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

    def search(self, sql: str) -> str:
        """
        Execute a SQL query against a normalized, unified browser history database.

        The sql query can referenc the following schema:

            CREATE TABLE IF NOT EXISTS browser_history (
            browser     TEXT NOT NULL,          -- 'chrome' | 'firefox' | 'safari' | …
            profile     TEXT,
            url         TEXT NOT NULL,          -- The URL visited (without query parameters)
            title       TEXT,                   -- The title of the page visited.
            referrer_url TEXT,                  -- NULL on Safari, otherwise the referrer
            visited_dt  DATETIME NOT NULL       -- UTC datetime
            );

        This method will no more than 100 rows of data.

        Provide any SQLite SQL in `sql` and named params in `params`. Examples:

        `SELECT * FROM browser_history WHERE url LIKE :u ORDER BY visited_ms DESC`.
        `SELECT * FROM browser_history WHERE lower(title) LIKE lower(title) LIKE lower('%lemming%') ORDER BY visited_ms DESC`.
        """
        # Ensure the unified DB exists only once per process
        unified_db = get_or_create_unified_db(self.sources)
        rows = run_unified_query(unified_db, sql, {})
        return json.dumps(rows, indent=2)
