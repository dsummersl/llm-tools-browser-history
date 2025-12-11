import json
import pathlib
from sqlite3 import Row
import llm
from collections.abc import Iterable
from typing import Any, Sequence, get_args


from .firefox import find_firefox_places_sqlite
from .chrome import find_chrome_history_paths
from .safari import find_safari_history_paths
from .browser_types import BrowserType
from .sqlite import get_or_create_unified_db, run_unified_query


class BrowserHistory(llm.Toolbox):
    """ Toolbox allowing search through browser history. """

    def __init__(self, sources: Iterable[str] | None = None, max_rows: int = 100):
        self.sources: list[tuple[str, pathlib.Path]] = []
        self.max_rows = max_rows

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

    def _do_search(self, sql: str) -> list[Sequence[Any]]:
        unified_db = get_or_create_unified_db(self.sources)
        return run_unified_query(unified_db, sql, {}, self.max_rows)

    def search(self, sql: str) -> str:
        """
        Execute a SQL query against a normalized, unified browser history database.

        The sql query can referenc the following schema:

            CREATE TABLE IF NOT EXISTS browser_history (
            browser     TEXT NOT NULL,          -- 'chrome' | 'firefox' | 'safari' | …
            profile     TEXT,                   -- browser profile name, e.g. 'Default', 'Profile 1', 'default-release'
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
        return json.dumps(self._do_search(sql), indent=2)
