"""Append-only event log backed by SQLite in WAL mode."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from pathlib import Path
from types import TracebackType
from typing import Literal, Self

from pydantic import ValidationError

from tessera.errors import LogCorruptionError
from tessera.models import Observation

_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    ingest_seq INTEGER PRIMARY KEY AUTOINCREMENT,
    schema_version INTEGER NOT NULL,
    payload TEXT NOT NULL
);
"""

Synchronous = Literal["NORMAL", "FULL"]


class EventLog:
    """Durable, ordered, append-only store of observations."""

    def __init__(self, path: str | Path, *, synchronous: Synchronous = "NORMAL") -> None:
        self._conn = sqlite3.connect(str(path))
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute(f"PRAGMA synchronous={synchronous}")
        self._conn.execute(_SCHEMA)
        self._conn.commit()

    def append(self, observation: Observation) -> int:
        """Append an observation and return its ingest sequence number."""
        with self._conn:
            cursor = self._conn.execute(
                "INSERT INTO events (schema_version, payload) VALUES (?, ?)",
                (observation.schema_version, observation.model_dump_json()),
            )
        if cursor.lastrowid is None:
            raise LogCorruptionError("insert returned no row id")
        return cursor.lastrowid

    def read(self, after_seq: int = 0) -> Iterator[tuple[int, Observation]]:
        """Yield (ingest_seq, observation) in order, starting after `after_seq`."""
        rows = self._conn.execute(
            "SELECT ingest_seq, payload FROM events WHERE ingest_seq > ? ORDER BY ingest_seq",
            (after_seq,),
        )
        for seq, payload in rows:
            try:
                yield seq, Observation.model_validate_json(payload)
            except ValidationError as exc:
                raise LogCorruptionError(f"event {seq} is corrupt") from exc

    def count(self) -> int:
        (total,) = self._conn.execute("SELECT COUNT(*) FROM events").fetchone()
        return int(total)

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()
