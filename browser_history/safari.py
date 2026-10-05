import pathlib
import logging
import glob

from .browser_types import HISTORY_COLUMNS_TEMPLATE

logger = logging.getLogger(__name__)


def _deduplicate_paths(candidates: list[pathlib.Path]) -> list[pathlib.Path]:
    """Deduplicate paths while preserving order and filtering to only files."""
    seen = set()
    unique: list[pathlib.Path] = []
    for p in candidates:
        if p not in seen and p.is_file():
            unique.append(p)
            seen.add(p)
    return unique


def _gather_safari_history_candidates() -> list[pathlib.Path]:
    """Gather candidate Safari history database paths."""
    home = pathlib.Path.home()
    candidates: list[pathlib.Path] = []
    mac_history = home / "Library" / "Safari" / "History.db"
    mac_history_glob = home / "Library" / "Safari" / "History.db*"

    logger.debug(f"Checking for Safari history at: {mac_history}")
    if mac_history.exists():
        logger.debug(f"Found Safari history at: {mac_history}")
        candidates.append(mac_history)

    # Only include files with .db extension
    for pattern in (mac_history_glob,):
        logger.debug(f"Checking for Safari history with pattern: {pattern}")
        for p in glob.glob(str(pattern)):
            path = pathlib.Path(p)
            if path.name == "History.db":
                logger.debug(f"Found Safari history via glob at: {path}")
                candidates.append(path)

    return candidates


def find_safari_history_paths() -> list[tuple[str, pathlib.Path]]:
    """Return list of Safari History.db paths on this system.

    Currently supports macOS default location under ~/Library/Safari/History.db.
    """
    candidates = _gather_safari_history_candidates()
    deduped_paths = _deduplicate_paths(candidates)
    # Safari doesn't have profiles in the same way, use "default" as profile name
    return [("default", path) for path in deduped_paths]


def get_safari_history_query(alias: str, profile_label: str) -> str:
    """Generate SELECT query for Safari browser history.

    Returns just the SELECT portion (without INSERT INTO) that can be used
    with insert_selected_records.
    """
    columns = HISTORY_COLUMNS_TEMPLATE.format(
        browser_name="'safari'",
        profile_label=profile_label,
        url_col="i.url",
        title_col="v.title",
        referrer_url_expr="NULL",
        date_expr="strftime('%Y-%m-%d %H:00:00', v.visit_time + strftime('%s','2001-01-01'), 'unixepoch')",
        referrer_domain_expr="NULL",
        referrer_stripped_qp_expr="NULL",
    )
    query = f"""
        SELECT
          {columns}
        FROM {alias}.history_items i
        LEFT JOIN {alias}.history_visits v ON v.history_item = i.id
        """
    return query
