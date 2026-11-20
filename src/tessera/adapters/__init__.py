"""Protocol adapters: raw bytes in, validated observations out."""

from tessera.adapters.base import Adapter
from tessera.adapters.mavlink import MavlinkAdapter

__all__ = ["Adapter", "MavlinkAdapter"]
