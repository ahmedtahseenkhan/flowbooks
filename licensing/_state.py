"""
Obfuscated trial-state and last-seen storage.

The blob is XOR'd against SHA-256(b"sc-trial-" + machine_id) (keyed to the
machine), then base64'd. This is *obfuscation*, not encryption — its job is to
deter casual file editing and registry inspection, nothing more.

Storage:
    - Windows : HKCU\\Software\\<AppName>\\State        (REG_SZ)
                HKCU\\Software\\<AppName>\\LastSeen     (REG_SZ)
    - Other   : ~/.<appname>/.sc_state                  (text file)
                ~/.<appname>/.ls                        (text file)
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Optional


_TRIAL_KEY_PREFIX = b"sc-trial-"


# ── Obfuscation ──────────────────────────────────────────────────────────────

def _xor_keystream(data: bytes, machine_id: str) -> bytes:
    seed = hashlib.sha256(_TRIAL_KEY_PREFIX + machine_id.encode("utf-8")).digest()
    # Stretch the 32-byte seed to cover `data` by repeated SHA-256 chaining.
    out = bytearray(len(data))
    block = seed
    i = 0
    while i < len(data):
        for b in block:
            if i >= len(data):
                break
            out[i] = data[i] ^ b
            i += 1
        block = hashlib.sha256(block).digest()
    return bytes(out)


def _obfuscate(plaintext: bytes, machine_id: str) -> str:
    return base64.b64encode(_xor_keystream(plaintext, machine_id)).decode("ascii")


def _deobfuscate(obfuscated: str, machine_id: str) -> bytes:
    raw = base64.b64decode(obfuscated.encode("ascii"))
    return _xor_keystream(raw, machine_id)


# ── Backend selection ────────────────────────────────────────────────────────

def _is_windows() -> bool:
    return sys.platform.startswith("win")


def _appdata_dir(app_name: str) -> Path:
    home = Path.home()
    return home / f".{app_name.lower()}"


# ── Windows registry backend ─────────────────────────────────────────────────

def _reg_read(app_name: str, value_name: str) -> Optional[str]:
    import winreg  # type: ignore

    key_path = rf"Software\{app_name}"
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as k:
            v, _ = winreg.QueryValueEx(k, value_name)
            return str(v) if v is not None else None
    except OSError:
        return None


def _reg_write(app_name: str, value_name: str, value: str) -> None:
    import winreg  # type: ignore

    key_path = rf"Software\{app_name}"
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as k:
        winreg.SetValueEx(k, value_name, 0, winreg.REG_SZ, value)


# ── File backend ─────────────────────────────────────────────────────────────

def _file_path(app_name: str, leaf: str) -> Path:
    d = _appdata_dir(app_name)
    d.mkdir(parents=True, exist_ok=True)
    return d / leaf


def _file_read(app_name: str, leaf: str) -> Optional[str]:
    try:
        return _file_path(app_name, leaf).read_text(encoding="ascii").strip()
    except (OSError, UnicodeDecodeError):
        return None


def _file_write(app_name: str, leaf: str, value: str) -> None:
    p = _file_path(app_name, leaf)
    p.write_text(value, encoding="ascii")
    # Best-effort hide on POSIX (already dotfile); on Windows set hidden attr.
    if _is_windows():
        try:
            import ctypes
            FILE_ATTRIBUTE_HIDDEN = 0x02
            ctypes.windll.kernel32.SetFileAttributesW(str(p), FILE_ATTRIBUTE_HIDDEN)
        except Exception:
            pass


# ── Public API: trial state ──────────────────────────────────────────────────

def load_trial_state(app_name: str, machine_id: str) -> Optional[dict]:
    """Return the parsed state dict, or None if absent / unreadable."""
    raw = (_reg_read(app_name, "State") if _is_windows()
           else _file_read(app_name, ".sc_state"))
    if not raw:
        return None
    try:
        plain = _deobfuscate(raw, machine_id)
        return json.loads(plain.decode("utf-8"))
    except Exception:
        return None


def save_trial_state(app_name: str, machine_id: str, state: dict) -> None:
    blob = json.dumps(state, separators=(",", ":")).encode("utf-8")
    obf  = _obfuscate(blob, machine_id)
    if _is_windows():
        _reg_write(app_name, "State", obf)
    else:
        _file_write(app_name, ".sc_state", obf)


# ── Public API: last-seen timestamp ──────────────────────────────────────────

def load_last_seen(app_name: str, machine_id: str) -> Optional[int]:
    raw = (_reg_read(app_name, "LastSeen") if _is_windows()
           else _file_read(app_name, ".ls"))
    if not raw:
        return None
    try:
        plain = _deobfuscate(raw, machine_id)
        return int(plain.decode("ascii").strip())
    except Exception:
        return None


def save_last_seen(app_name: str, machine_id: str, ts: int) -> None:
    obf = _obfuscate(str(int(ts)).encode("ascii"), machine_id)
    if _is_windows():
        _reg_write(app_name, "LastSeen", obf)
    else:
        _file_write(app_name, ".ls", obf)


__all__ = [
    "load_trial_state",
    "save_trial_state",
    "load_last_seen",
    "save_last_seen",
]
