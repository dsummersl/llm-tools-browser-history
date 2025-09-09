from __future__ import annotations
import json
import datetime
import pathlib
import llm
from typing import Iterable

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
            sources = [b.value for b in BrowserType]

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

    def search(self, sql: str, params: dict[str, object] | None = None) -> str:
        """
        Execute a SQL query against a normalized, unified browser history database.

        The sql query can referenc the following schema:

            CREATE TABLE IF NOT EXISTS browser_history (
            browser     TEXT NOT NULL,          -- 'chrome' | 'firefox' | 'safari' | …
            profile     TEXT,                   -- optional label you add
            url         TEXT NOT NULL,
            title       TEXT,
            referrer_url TEXT,                  -- NULL on Safari
            visited_dt  DATETIME NOT NULL        -- UTC datetime
            );
            CREATE INDEX IF NOT EXISTS idx_bh_time ON browser_history(visited_ms);
            CREATE INDEX IF NOT EXISTS idx_bh_url  ON browser_history(url);

        This method will no more than 100 rows of data.

        Provide any SQLite SQL in `sql` (e.g. `SELECT * FROM browser_history WHERE url LIKE :u ORDER BY visited_ms DESC`).
        Named parameters can be supplied via `params`.
        """
        # Ensure the unified DB exists only once per process
        unified_db = get_or_create_unified_db(self.sources)
        rows = run_unified_query(unified_db, sql, params or {})
        return json.dumps(rows, indent=2)
