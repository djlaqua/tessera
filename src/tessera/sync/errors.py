"""Sync error hierarchy."""

from tessera.errors import TesseraError


class SyncError(TesseraError):
    """Invalid or inconsistent sync data."""


class AuthError(SyncError):
    """Unknown edge or invalid signature."""


class TransportError(SyncError):
    """The link failed; the caller may retry later."""
