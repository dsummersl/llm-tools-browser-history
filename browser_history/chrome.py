import pathlib
import datetime
import glob
import logging

logger = logging.getLogger(__name__)

WEBKIT_EPOCH = datetime.datetime(1601, 1, 1, tzinfo=datetime.timezone.utc)


def find_chrome_history_paths() -> list[tuple[str, pathlib.Path]]:
    home = pathlib.Path.home()
    candidates: list[tuple[str, pathlib.Path]] = []
    mac_chrome = home / "Library" / "Application Support" / "Google" / "Chrome" / "*" / "History"
    mac_chromium = home / "Library" / "Application Support" / "Chromium" / "*" / "History"
    linux_chrome = home / ".config" / "google-chrome" / "*" / "History"
    linux_chromium = home / ".config" / "chromium" / "*" / "History"
    snap_chromium = home / "snap" / "chromium" / "common" / ".config" / "chromium" / "*" / "History"
    for pattern in (mac_chrome, mac_chromium, linux_chrome, linux_chromium, snap_chromium):
        logger.debug(f"Checking for Chrome history at: {pattern}")
        for p in glob.glob(str(pattern)):
            path = pathlib.Path(p)
            profile_name = path.parent.name
            logger.debug(f"Found Chrome history at: {path} (profile: {profile_name})")
            candidates.append((profile_name, path))
    return candidates


def get_chrome_history_query(alias: str, profile_label: str) -> str:
    """Generate SELECT query for Chrome browser history.

    Returns just the SELECT portion (without INSERT INTO) that can be used
    with insert_selected_records.
    """
    query = f"""
        SELECT
          'chrome' AS browser,
          '{profile_label}' AS profile,
          process_url_url(u.url) AS url,
          u.title,
          process_url_url(r.url) AS referrer_url,
          strftime('%Y-%m-%d %H:00:00', (v.visit_time/1000 - 11644473600*1000)/1000, 'unixepoch') AS visited_dt,
          process_url_domain(u.url) AS domain,
          process_url_stripped(u.url) AS stripped_qp,
          process_url_domain(r.url) AS referrer_domain,
          process_url_stripped(r.url) AS referrer_stripped_qp
        FROM {alias}.urls u
        JOIN {alias}.visits v       ON v.url = u.id
        LEFT JOIN {alias}.visits pv ON pv.id = v.from_visit
        LEFT JOIN {alias}.urls  r   ON r.id = pv.url
        """
    return query
