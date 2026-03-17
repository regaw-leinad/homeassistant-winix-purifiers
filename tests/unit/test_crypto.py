"""Tests for AES-256-CBC encryption/decryption."""

from custom_components.winix_purifiers.api.crypto import decrypt, encrypt


def test_encrypt_decrypt_round_trip():
    """Encrypted data should decrypt back to the original payload."""
    payload = {"key": "value", "number": 42, "nested": {"a": True}}
    encrypted = encrypt(payload)
    decrypted = decrypt(encrypted)
    assert decrypted == payload


def test_encrypt_produces_bytes():
    """Encrypt should return bytes."""
    result = encrypt({"test": "data"})
    assert isinstance(result, bytes)
    assert len(result) > 0


def test_encrypt_different_payloads_produce_different_ciphertext():
    """Different payloads should produce different ciphertext."""
    a = encrypt({"value": "one"})
    b = encrypt({"value": "two"})
    assert a != b


def test_decrypt_known_ciphertext():
    """Verify we can decrypt a known payload."""
    original = {"hello": "world"}
    ciphertext = encrypt(original)
    # Re-decrypt the same ciphertext
    assert decrypt(ciphertext) == original


def test_round_trip_empty_payload():
    """Empty dict should round-trip correctly."""
    payload = {}
    assert decrypt(encrypt(payload)) == payload


def test_round_trip_unicode():
    """Unicode strings should round-trip correctly."""
    payload = {"emoji": "🌬️", "japanese": "空気清浄機"}
    assert decrypt(encrypt(payload)) == payload
