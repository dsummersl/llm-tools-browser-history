import glob
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

MICROSECOND = 1_000_000


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
    """Generate SELECT query for Firefox browser history.

    Returns just the SELECT portion (without INSERT INTO) that can be used
    with insert_selected_records.
    """
    query = f"""
        SELECT
          'firefox' AS browser,
          '{profile_label}' AS profile,
          process_url_url(p.url) AS url,
          p.title,
          process_url_url(pr.url) AS referrer_url,
          strftime('%Y-%m-%d %H:00:00', h.visit_date/1000000, 'unixepoch') AS visited_dt,
          process_url_domain(p.url) AS domain,
          process_url_stripped(p.url) AS stripped_qp,
          process_url_domain(pr.url) AS referrer_domain,
          process_url_stripped(pr.url) AS referrer_stripped_qp
        FROM {alias}.moz_historyvisits h
        JOIN {alias}.moz_places p         ON p.id = h.place_id
        LEFT JOIN {alias}.moz_historyvisits ph ON ph.id = h.from_visit
        LEFT JOIN {alias}.moz_places pr    ON pr.id = ph.place_id
        """
    return query
