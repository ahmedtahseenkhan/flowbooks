"""
Deterministic 16-char hex Machine ID, derived from stable hardware/OS facts.

Sources (best-effort, OS-aware):
    - MAC address              (uuid.getnode)
    - Hostname                 (socket.gethostname)
    - CPU info                 (platform.processor / platform.machine)
    - OS / arch                (platform.system / platform.release / platform.machine)
    - Disk / board serial      Windows: wmic baseboard get serialnumber
                               Linux:   /etc/machine-id
                               macOS:   system_profiler SPHardwareDataType

The 5 facts are joined with '|', SHA-256 hashed, and the first 16 hex chars
(64 bits) are returned uppercased. Identical inputs ⇒ identical Machine ID.
"""
from __future__ import annotations

import hashlib
import platform
import socket
import subprocess
import sys
import uuid


# ── Per-OS hardware serial (best-effort) ──────────────────────────────────────

def _windows_board_serial() -> str:
    try:
        out = subprocess.check_output(
            ["wmic", "baseboard", "get", "serialnumber"],
            stderr=subprocess.DEVNULL,
            timeout=5,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        ).decode("utf-8", "ignore")
        # First non-empty line after the header.
        for line in out.splitlines():
            line = line.strip()
            if line and line.lower() != "serialnumber":
                return line
    except Exception:
        pass
    # Fallback: BIOS serial
    try:
        out = subprocess.check_output(
            ["wmic", "bios", "get", "serialnumber"],
            stderr=subprocess.DEVNULL,
            timeout=5,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        ).decode("utf-8", "ignore")
        for line in out.splitlines():
            line = line.strip()
            if line and line.lower() != "serialnumber":
                return line
    except Exception:
        pass
    return ""


def _linux_machine_id() -> str:
    for path in ("/etc/machine-id", "/var/lib/dbus/machine-id"):
        try:
            with open(path, "r", encoding="utf-8") as f:
                val = f.read().strip()
                if val:
                    return val
        except Exception:
            continue
    return ""


def _macos_hardware_uuid() -> str:
    try:
        out = subprocess.check_output(
            ["system_profiler", "SPHardwareDataType"],
            stderr=subprocess.DEVNULL,
            timeout=5,
        ).decode("utf-8", "ignore")
        for line in out.splitlines():
            line = line.strip()
            # Prefer Hardware UUID; fall back to Serial Number.
            if line.startswith("Hardware UUID:"):
                return line.split(":", 1)[1].strip()
        for line in out.splitlines():
            line = line.strip()
            if line.startswith("Serial Number"):
                return line.split(":", 1)[1].strip()
    except Exception:
        pass
    return ""


def _hardware_serial() -> str:
    if sys.platform.startswith("win"):
        return _windows_board_serial()
    if sys.platform == "darwin":
        return _macos_hardware_uuid()
    if sys.platform.startswith("linux"):
        return _linux_machine_id()
    return ""


# ── Public API ────────────────────────────────────────────────────────────────

def _mac_address() -> str:
    node = uuid.getnode()
    # uuid.getnode() returns a random multicast bit-set value when the real
    # MAC can't be read; in that case we still want a stable string.
    return f"{node:012x}"


def _cpu_info() -> str:
    proc = (platform.processor() or "").strip()
    mach = (platform.machine()   or "").strip()
    return f"{proc}|{mach}"


def _os_info() -> str:
    return f"{platform.system()}|{platform.release()}|{platform.machine()}"


def get_machine_id() -> str:
    """Return the 16-char uppercase hex machine fingerprint."""
    parts = [
        _mac_address(),
        socket.gethostname() or "",
        _cpu_info(),
        _os_info(),
        _hardware_serial(),
    ]
    blob = "|".join(parts).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:16].upper()


if __name__ == "__main__":
    print(get_machine_id())
