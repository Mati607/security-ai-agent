from __future__ import annotations

import hashlib
import secrets


_ITERATIONS = 480_000
_PREFIX = "pbkdf2_sha256$480000$"


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _ITERATIONS)
    return _PREFIX + salt.hex() + "$" + dk.hex()


def verify_password(password: str, stored: str) -> bool:
    if not stored.startswith(_PREFIX):
        return False
    body = stored[len(_PREFIX) :]
    parts = body.split("$", 1)
    if len(parts) != 2:
        return False
    salt_hex, hash_hex = parts
    try:
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
    except ValueError:
        return False
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _ITERATIONS)
    return secrets.compare_digest(dk, expected)
