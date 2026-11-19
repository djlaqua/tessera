"""Exception hierarchy."""


class TesseraError(Exception):
    """Base class for all Tessera errors."""


class AdapterError(TesseraError):
    """Raised when an adapter receives invalid or hostile input."""


class LogCorruptionError(TesseraError):
    """Raised when a stored event cannot be decoded."""
