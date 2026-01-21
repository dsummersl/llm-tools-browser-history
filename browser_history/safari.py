import pathlib
import datetime
import logging
import glob

logger = logging.getLogger(__name__)

APPLE_EPOCH = datetime.datetime(2001, 1, 1, tzinfo=datetime.timezone.utc)


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


def find_safari_history_paths() -> list[pathlib.Path]:
    """Return list of Safari History.db paths on this system.

    Currently supports macOS default location under ~/Library/Safari/History.db.
    """
    candidates = _gather_safari_history_candidates()
    return _deduplicate_paths(candidates)
