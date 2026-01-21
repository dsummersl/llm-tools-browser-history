import glob
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

MICROSECOND = 1_000_000


def find_firefox_places_sqlite() -> list[Path]:
    home = Path.home()
    candidates: list[Path] = []
    mac = home / "Library" / "Application Support" / "Firefox" / "Profiles" / "*" / "places.sqlite"
    linux = home / ".mozilla" / "firefox" / "*" / "places.sqlite"
    snap = home / "snap" / "firefox" / "common" / ".mozilla" / "firefox" / "*" / "places.sqlite"
    for pattern in (mac, linux, snap):
        logger.debug(f"Checking for Firefox profiles in: {pattern}")
        for p in glob.glob(str(pattern)):
            path = Path(p)
            logger.debug(f"Found Firefox history database at: {path}")
            candidates.append(path)
    return candidates
