"""
Ed25519 license signing / verification.

License envelope (the .lic file contents) is JSON of the form:

    {
        "version":   1,
        "payload":   "<base64 of canonical JSON payload bytes>",
        "signature": "<base64 of Ed25519 signature over those payload bytes>"
    }

The payload is the dict described in the package README:
    {
        "machine_id": "ABCDEF1234567890",
        "customer":   "Acme Corp",
        "tier":       "professional",
        "issued":     "2026-01-15",
        "expires":    "2027-01-15",   # "" = perpetual
        "features":   ["full_report", ...]
    }

Canonicalisation: JSON encoded with sort_keys=True, separators=(',', ':'),
ensure_ascii=False. Signing and verification both operate on the *raw* canonical
payload bytes (the same bytes that get base64-encoded into the "payload" field).
"""
from __future__ import annotations

import base64
import json
from typing import Any, Dict, Tuple

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)


LICENSE_FORMAT_VERSION = 1


# ── Embedded public key ───────────────────────────────────────────────────────
# The validator uses this constant to verify .lic files.
# Regenerate via:  python -m licensing.admin keygen
# After regeneration, update this constant with the printed hex string.
EMBEDDED_PUBLIC_KEY_HEX = (
    "c8dfb7d1d89e8b0b89fad0cc923a405f35d659f4f9ec3604ce23e86828dbe4b9"
)


# ── Key generation / loading ──────────────────────────────────────────────────

def generate_key_pair() -> Tuple[bytes, bytes, str]:
    """Generate a new Ed25519 keypair.

    Returns (private_pem_bytes, public_pem_bytes, public_raw_hex).
    """
    priv = Ed25519PrivateKey.generate()
    pub  = priv.public_key()

    priv_pem = priv.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    pub_pem = pub.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    pub_raw = pub.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return priv_pem, pub_pem, pub_raw.hex()


def load_private_key(pem_bytes: bytes) -> Ed25519PrivateKey:
    key = serialization.load_pem_private_key(pem_bytes, password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise ValueError("Not an Ed25519 private key")
    return key


def load_public_key(pem_bytes: bytes) -> Ed25519PublicKey:
    key = serialization.load_pem_public_key(pem_bytes)
    if not isinstance(key, Ed25519PublicKey):
        raise ValueError("Not an Ed25519 public key")
    return key


def load_public_key_from_string(s: str) -> Ed25519PublicKey:
    """Accepts either 64-char raw hex or PEM text."""
    s = s.strip()
    if "BEGIN PUBLIC KEY" in s:
        return load_public_key(s.encode("utf-8"))
    raw = bytes.fromhex(s)
    if len(raw) != 32:
        raise ValueError("Ed25519 raw public key must be 32 bytes (64 hex chars)")
    return Ed25519PublicKey.from_public_bytes(raw)


def get_embedded_public_key() -> Ed25519PublicKey:
    return load_public_key_from_string(EMBEDDED_PUBLIC_KEY_HEX)


# ── Sign / verify ─────────────────────────────────────────────────────────────

def _canonical_payload_bytes(payload: Dict[str, Any]) -> bytes:
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def sign_license(payload: Dict[str, Any], priv_key: Ed25519PrivateKey) -> Dict[str, Any]:
    """Build the license envelope dict from a payload + private key."""
    payload_bytes = _canonical_payload_bytes(payload)
    sig           = priv_key.sign(payload_bytes)
    return {
        "version":   LICENSE_FORMAT_VERSION,
        "payload":   base64.b64encode(payload_bytes).decode("ascii"),
        "signature": base64.b64encode(sig).decode("ascii"),
    }


def verify_license(
    license_data: Dict[str, Any],
    pub_key: Ed25519PublicKey,
) -> Dict[str, Any]:
    """Verify the envelope and return the parsed payload dict.

    Raises InvalidSignature on mismatch, ValueError on malformed input.
    """
    if not isinstance(license_data, dict):
        raise ValueError("license_data must be a dict")

    version = license_data.get("version")
    if version != LICENSE_FORMAT_VERSION:
        raise ValueError(f"unsupported license version: {version!r}")

    try:
        payload_bytes = base64.b64decode(license_data["payload"], validate=True)
        sig_bytes     = base64.b64decode(license_data["signature"], validate=True)
    except (KeyError, ValueError, TypeError) as e:
        raise ValueError(f"malformed license envelope: {e}") from e

    pub_key.verify(sig_bytes, payload_bytes)   # raises InvalidSignature on fail

    try:
        return json.loads(payload_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise ValueError(f"payload is not valid UTF-8 JSON: {e}") from e


__all__ = [
    "LICENSE_FORMAT_VERSION",
    "EMBEDDED_PUBLIC_KEY_HEX",
    "generate_key_pair",
    "load_private_key",
    "load_public_key",
    "load_public_key_from_string",
    "get_embedded_public_key",
    "sign_license",
    "verify_license",
    "InvalidSignature",
]
