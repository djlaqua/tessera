"""Coordinate reference system normalization to WGS84 (EPSG:4326)."""

from __future__ import annotations

from functools import lru_cache

from pyproj import Transformer


@lru_cache(maxsize=32)
def _transformer(source_epsg: int) -> Transformer:
    # always_xy avoids axis order bugs: inputs and outputs are (x/lon, y/lat).
    return Transformer.from_crs(f"EPSG:{source_epsg}", "EPSG:4326", always_xy=True)


@lru_cache(maxsize=32)
def _inverse(source_epsg: int) -> Transformer:
    return Transformer.from_crs("EPSG:4326", f"EPSG:{source_epsg}", always_xy=True)


def to_wgs84(x: float, y: float, source_epsg: int) -> tuple[float, float]:
    """Convert projected or geographic (x, y) in `source_epsg` to (lat, lon) in WGS84."""
    lon, lat = _transformer(source_epsg).transform(x, y)
    return float(lat), float(lon)


def from_wgs84(lat: float, lon: float, target_epsg: int) -> tuple[float, float]:
    """Convert WGS84 (lat, lon) to (x, y) in `target_epsg`."""
    x, y = _inverse(target_epsg).transform(lon, lat)
    return float(x), float(y)
