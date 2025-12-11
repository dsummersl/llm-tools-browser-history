import glob
from pathlib import Path

MICROSECOND = 1_000_000

def find_firefox_places_sqlite() -> list[Path]:
    home = Path.home()
    candidates: list[Path] = []
    mac = home / "Library" / "Application Support" / "Firefox" / "Profiles" / "*" / "places.sqlite"
    linux = home / ".mozilla" / "firefox" / "*" / "places.sqlite"
    snap = home / "snap" / "firefox" / "common" / ".mozilla" / "firefox" / "*" / "places.sqlite"
    for pattern in (mac, linux, snap):
        candidates.extend(Path(p) for p in glob.glob(str(pattern)))
    return candidates
