"""Regression test on frames captured from a live ArduPilot SITL run (synthetic data)."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from tessera.adapters.mavlink import MavlinkAdapter

FIXTURE = Path(__file__).parent / "fixtures" / "sitl_global_position_int.bin"
NOW = datetime(2026, 11, 20, 9, 0, 0, tzinfo=UTC)


def test_sitl_capture_parses_completely():
    adapter = MavlinkAdapter("sitl", clock=lambda: NOW)
    observations = adapter.parse(FIXTURE.read_bytes())
    assert len(observations) == 40
    assert adapter.rejected == 0
    boot_times = [o.attributes["time_boot_ms"] for o in observations]
    assert boot_times == sorted(boot_times)
    first = observations[0]
    assert first.position.lat == pytest.approx(48.137, abs=1e-6)
    assert first.position.lon == pytest.approx(11.575, abs=1e-6)
    assert first.position.alt_m == pytest.approx(520.0, abs=1.0)
