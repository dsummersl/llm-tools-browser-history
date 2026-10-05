import glob
import logging
from pathlib import Path

from .browser_types import HISTORY_COLUMNS_TEMPLATE

logger = logging.getLogger(__name__)


def find_firefox_places_sqlite() -> list[tuple[str, Path]]:
    home = Path.home()
    candidates: list[tuple[str, Path]] = []
    mac = home / "Library" / "Application Support" / "Firefox" / "Profiles" / "*" / "places.sqlite"
    linux = home / ".mozilla" / "firefox" / "*" / "places.sqlite"
    snap = home / "snap" / "firefox" / "common" / ".mozilla" / "firefox" / "*" / "places.sqlite"
    for pattern in (mac, linux, snap):
        logger.debug(f"Checking for Firefox profiles in: {pattern}")
        for p in glob.glob(str(pattern)):
            path = Path(p)
            profile_name = path.parent.name
            logger.debug(f"Found Firefox history database at: {path} (profile: {profile_name})")
            candidates.append((profile_name, path))
    return candidates


def get_firefox_history_query(alias: str, profile_label: str) -> str:
    columns = HISTORY_COLUMNS_TEMPLATE.format(
        browser_name="'firefox'",
        profile_label=profile_label,
        url_col="p.url",
        title_col="p.title",
        referrer_url_expr="process_url_url(pr.url)",
        date_expr="strftime('%Y-%m-%d %H:00:00', h.visit_date/1000000, 'unixepoch')",
        referrer_domain_expr="process_url_domain(pr.url)",
        referrer_stripped_qp_expr="process_url_stripped(pr.url)",
    )
    query = f"""
        SELECT
          {columns}
        FROM {alias}.moz_historyvisits h
        JOIN {alias}.moz_places p         ON p.id = h.place_id
        LEFT JOIN {alias}.moz_historyvisits ph ON ph.id = h.from_visit
        LEFT JOIN {alias}.moz_places pr    ON pr.id = ph.place_id
        """
    return query
