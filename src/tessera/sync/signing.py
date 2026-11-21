"""Ed25519 key handling. Private keys are written with mode 0600 and refused if more open."""

from __future__ import annotations

import os
import stat
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from tessera.sync.errors import SyncError


def generate_private_key() -> Ed25519PrivateKey:
    return Ed25519PrivateKey.generate()


def save_private_key(key: Ed25519PrivateKey, path: Path) -> None:
    """Write a PEM private key with mode 0600. Fails if the file already exists."""
    pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(pem)


def save_public_key(key: Ed25519PublicKey, path: Path) -> None:
    path.write_bytes(
        key.public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
        )
    )


def load_private_key(path: Path) -> Ed25519PrivateKey:
    mode = stat.S_IMODE(path.stat().st_mode)
    if mode & 0o077:
        raise SyncError(f"{path} is readable by group or others (mode {mode:o}); run chmod 600")
    key = serialization.load_pem_private_key(path.read_bytes(), password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise SyncError("not an Ed25519 private key")
    return key


def load_public_key(path: Path) -> Ed25519PublicKey:
    key = serialization.load_pem_public_key(path.read_bytes())
    if not isinstance(key, Ed25519PublicKey):
        raise SyncError("not an Ed25519 public key")
    return key


def sign(key: Ed25519PrivateKey, message: bytes) -> bytes:
    return key.sign(message)


def verify(key: Ed25519PublicKey, signature: bytes, message: bytes) -> bool:
    try:
        key.verify(signature, message)
    except InvalidSignature:
        return False
    return True
