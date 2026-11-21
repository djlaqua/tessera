"""Spherical earth helpers. Accurate to about 0.5 percent, enough for integrity scoring."""

from __future__ import annotations

import math

EARTH_RADIUS_M = 6_371_008.8


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great circle distance in meters."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = phi2 - phi1
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlmb / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(a)))


def destination(
    lat: float, lon: float, bearing_deg: float, distance_m: float
) -> tuple[float, float]:
    """Point reached from (lat, lon) after `distance_m` on `bearing_deg`. Returns (lat, lon)."""
    delta = distance_m / EARTH_RADIUS_M
    theta = math.radians(bearing_deg)
    phi1, lmb1 = math.radians(lat), math.radians(lon)
    phi2 = math.asin(
        math.sin(phi1) * math.cos(delta) + math.cos(phi1) * math.sin(delta) * math.cos(theta)
    )
    lmb2 = lmb1 + math.atan2(
        math.sin(theta) * math.sin(delta) * math.cos(phi1),
        math.cos(delta) - math.sin(phi1) * math.sin(phi2),
    )
    lon2 = (math.degrees(lmb2) + 540.0) % 360.0 - 180.0
    return math.degrees(phi2), lon2
