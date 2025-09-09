from __future__ import annotations
import pathlib
import datetime

import glob

APPLE_EPOCH = datetime.datetime(2001, 1, 1, tzinfo=datetime.timezone.utc)


def find_safari_history_paths() -> list[pathlib.Path]:
    """Return list of Safari History.db paths on this system.

    Currently supports macOS default location under ~/Library/Safari/History.db.
    """
    home = pathlib.Path.home()
    candidates: list[pathlib.Path] = []
    mac_history = home / "Library" / "Safari" / "History.db"
    # Some users may have multiple History.db.* copies; include those as well
    mac_history_glob = home / "Library" / "Safari" / "History.db*"
    if mac_history.exists():
        candidates.append(mac_history)
    # Only include files with .db extension
    for pattern in (mac_history_glob,):
        candidates.extend(
            pathlib.Path(p)
            for p in glob.glob(str(pattern))
            if pathlib.Path(p).name == "History.db"
        )
    # Deduplicate while preserving order
    seen = set()
    unique: list[pathlib.Path] = []
    for p in candidates:
        if p not in seen and p.is_file():
            unique.append(p)
            seen.add(p)
    return unique
