import json
import pathlib
import llm
from collections.abc import Callable, Iterable
from typing import Any, Sequence, get_args


from .firefox import find_firefox_places_sqlite
from .chrome import find_chrome_history_paths
from .safari import find_safari_history_paths
from .browser_types import BrowserType
from .sqlite import get_or_create_unified_db, run_unified_query, cleanup_unified_db
from .qp_whitelist import Whitelist, load_whitelist


class BrowserHistory(llm.Toolbox):  # type: ignore
    """Toolbox allowing search through browser history."""

    def __init__(
        self,
        sources: Iterable[str] | None = None,
        max_rows: int = 100,
        whitelist: Whitelist | None = None,
    ):
        self.sources: list[tuple[BrowserType, pathlib.Path]] = []
        self.max_rows = max_rows
        self.whitelist = whitelist if whitelist is not None else load_whitelist(None)

        if not sources:
            sources = get_args(BrowserType)

        self._initialize_sources(sources)

    def _initialize_sources(self, sources: Iterable[str]) -> None:
        """Initialize browser history sources."""
        browser_finders: dict[BrowserType, Callable[[], list[pathlib.Path]]] = {
            "firefox": find_firefox_places_sqlite,
            "chrome": find_chrome_history_paths,
            "safari": find_safari_history_paths,
        }

        for browser_name, finder_func in browser_finders.items():
            if browser_name in sources:
                for p in finder_func():
                    self.sources.append((browser_name, p))

    def _do_search(self, sql: str) -> list[Sequence[Any]]:
        unified_db = get_or_create_unified_db(self.sources, whitelist=self.whitelist)
        return run_unified_query(unified_db, sql, {}, self.max_rows)

    def search(self, sql: str) -> str:
        """
        Execute a SQL query against a normalized, unified browser history database.

        The sql query can referenc the following schema:

            CREATE TABLE IF NOT EXISTS browser_history (
            browser     TEXT NOT NULL,          -- 'chrome' | 'firefox' | 'safari' | …
            profile     TEXT,                   -- browser profile name, e.g. 'Default', 'Profile 1', 'default-release'
            url         TEXT NOT NULL,          -- The URL visited (query params filtered by whitelist)
            title       TEXT,                   -- The title of the page visited.
            referrer_url TEXT,                  -- NULL on Safari, otherwise the referrer
            visited_dt  DATETIME NOT NULL,      -- UTC datetime
            domain      TEXT,                   -- The domain of the URL
            stripped_qp TEXT                    -- Comma-separated list of query param keys that were removed
            );

        This method will no more than 100 rows of data.

        Provide any SQLite SQL in `sql` and named params in `params`. Examples:

        `SELECT * FROM browser_history WHERE url LIKE :u ORDER BY visited_ms DESC`.
        `SELECT * FROM browser_history WHERE lower(title) LIKE lower(title) LIKE lower('%lemming%') ORDER BY visited_ms DESC`.
        """
        return json.dumps(self._do_search(sql), indent=2)

    def __del__(self):  # type: ignore
        """Cleanup the unified database when the toolbox is destroyed."""
        cleanup_unified_db()
