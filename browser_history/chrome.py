import pathlib
import datetime
import glob
import logging

logger = logging.getLogger(__name__)

WEBKIT_EPOCH = datetime.datetime(1601, 1, 1, tzinfo=datetime.timezone.utc)


def find_chrome_history_paths() -> list[pathlib.Path]:
    home = pathlib.Path.home()
    candidates: list[pathlib.Path] = []
    mac_chrome = home / "Library" / "Application Support" / "Google" / "Chrome" / "*" / "History"
    mac_chromium = home / "Library" / "Application Support" / "Chromium" / "*" / "History"
    linux_chrome = home / ".config" / "google-chrome" / "*" / "History"
    linux_chromium = home / ".config" / "chromium" / "*" / "History"
    snap_chromium = home / "snap" / "chromium" / "common" / ".config" / "chromium" / "*" / "History"
    for pattern in (mac_chrome, mac_chromium, linux_chrome, linux_chromium, snap_chromium):
        logger.debug(f"Checking for Chrome history at: {pattern}")
        for p in glob.glob(str(pattern)):
            path = pathlib.Path(p)
            logger.debug(f"Found Chrome history at: {path}")
            candidates.append(path)
    return candidates
