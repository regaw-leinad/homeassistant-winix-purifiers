"""AES-256-CBC encryption for Winix mobile API endpoints."""

from __future__ import annotations

import json
from typing import Any

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.padding import PKCS7

from .const import AES_IV, AES_KEY

_BLOCK_SIZE_BITS = 128


def encrypt(payload: dict[str, Any]) -> bytes:
    """Encrypt a JSON payload for the Winix mobile API."""
    plaintext = json.dumps(payload).encode("utf-8")

    padder = PKCS7(_BLOCK_SIZE_BITS).padder()
    padded = padder.update(plaintext) + padder.finalize()

    cipher = Cipher(algorithms.AES(AES_KEY), modes.CBC(AES_IV))
    encryptor = cipher.encryptor()
    return encryptor.update(padded) + encryptor.finalize()


def decrypt(data: bytes) -> dict[str, Any]:
    """Decrypt an AES-256-CBC response from the Winix mobile API."""
    cipher = Cipher(algorithms.AES(AES_KEY), modes.CBC(AES_IV))
    decryptor = cipher.decryptor()
    padded = decryptor.update(data) + decryptor.finalize()

    unpadder = PKCS7(_BLOCK_SIZE_BITS).unpadder()
    plaintext = unpadder.update(padded) + unpadder.finalize()

    return json.loads(plaintext.decode("utf-8"))
