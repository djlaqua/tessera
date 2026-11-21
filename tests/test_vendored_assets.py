import hashlib
import re
from pathlib import Path

VENDOR = Path(__file__).parent.parent / "src" / "tessera" / "ui" / "static" / "vendor" / "leaflet"


def test_leaflet_matches_recorded_checksum():
    recorded = re.search(r"sha256 ([0-9a-f]{64})", (VENDOR / "VERSION").read_text()).group(1)
    assert hashlib.sha256((VENDOR / "leaflet.js").read_bytes()).hexdigest() == recorded


def test_leaflet_license_shipped():
    assert "BSD 2-Clause" in (VENDOR / "LICENSE").read_text()
