"""Adapter protocol."""

from __future__ import annotations

from typing import Protocol

from tessera.models import Observation


class Adapter(Protocol):
    """Parses raw transport bytes into validated observations.

    Implementations may be stateful per link (for example to reassemble frames split
    across reads), so use one instance per connection.
    """

    name: str

    def parse(self, raw: bytes) -> list[Observation]:
        """Return the observations found in `raw`.

        Raises:
            AdapterError: if the input violates a hard limit (for example size).
        """
        ...
