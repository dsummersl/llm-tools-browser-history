import json
import pathlib
import llm
from collections.abc import Callable, Iterable
from typing import Any, Sequence, get_args
import logging


from .firefox import find_firefox_places_sqlite
from .chrome import find_chrome_history_paths
from .safari import find_safari_history_paths
from .browser_types import BrowserType
from .sqlite import get_or_create_unified_db, run_unified_query, cleanup_unified_db
from .qp_whitelist import Whitelist, load_whitelist

logger = logging.getLogger(__name__)


class BrowserHistory(llm.Toolbox):  # type: ignore
    def __init__(
        self,
        sources: Iterable[str] | None = None,
        max_rows: int = 100,
        whitelist: Whitelist | None = None,
        db_path: pathlib.Path | None = None,
        use_cache: bool = False,
    ):
        self.sources: list[tuple[BrowserType, str, pathlib.Path]] = []
        self.max_rows = max_rows
        self.whitelist = whitelist if whitelist is not None else load_whitelist(None)
        self.db_path = db_path
        self.use_cache = use_cache

        if not sources:
            sources = get_args(BrowserType)

        self._initialize_sources(sources)

    def _initialize_sources(self, sources: Iterable[str]) -> None:
        browser_finders: dict[BrowserType, Callable[[], list[tuple[str, pathlib.Path]]]] = {
            "firefox": find_firefox_places_sqlite,
            "chrome": find_chrome_history_paths,
            "safari": find_safari_history_paths,
        }

        for browser_name, finder_func in browser_finders.items():
            if browser_name in sources:
                for profile_name, path in finder_func():
                    self.sources.append((browser_name, profile_name, path))

    def _do_search(self, sql: str) -> list[Sequence[Any]]:
        logger.debug("Building unified browser history database...")
        unified_db = get_or_create_unified_db(
            self.sources,
            whitelist=self.whitelist,
            db_path=self.db_path,
            use_cache=self.use_cache,
        )
        return run_unified_query(unified_db, sql, {}, self.max_rows)

    def search(self, sql: str) -> str:
        return json.dumps(self._do_search(sql), indent=2)

    def __del__(self):  # type: ignore
        cleanup_unified_db()
