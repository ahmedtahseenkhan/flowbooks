"""
Anti-tamper / runtime integrity helpers (best-effort, never fatal).

Each check returns a small fact; the validator decides what to do with them.
None of these are silver bullets — they raise the cost of casual patching, not
of a determined attacker.
"""
from __future__ import annotations

import ctypes
import hashlib
import os
import sys
import time


# ── Frozen exe self-hash ──────────────────────────────────────────────────────

def is_frozen() -> bool:
    """True when running from a PyInstaller-style frozen bundle."""
    return bool(getattr(sys, "frozen", False))


def compute_self_hash() -> str | None:
    """SHA-256 of the running frozen executable. Returns None when not frozen
    or unreadable."""
    if not is_frozen():
        return None
    exe = sys.executable
    try:
        h = hashlib.sha256()
        with open(exe, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


# ── Debugger detection ────────────────────────────────────────────────────────

def _windows_is_debugger_present() -> bool:
    if not sys.platform.startswith("win"):
        return False
    try:
        return bool(ctypes.windll.kernel32.IsDebuggerPresent())
    except Exception:
        return False


def is_debugger_present() -> bool:
    """True if a Python tracer or a native Windows debugger is attached."""
    if sys.gettrace() is not None:
        return True
    if _windows_is_debugger_present():
        return True
    return False


# ── Timing anomaly ────────────────────────────────────────────────────────────

_TIMING_ITERS    = 10_000
_TIMING_LIMIT_MS = 500


def timing_anomaly_detected() -> bool:
    """A 10000-iter no-op loop should run in well under 500ms on any modern
    machine. If it doesn't, we may be under a step debugger or instrumentation.
    """
    try:
        start = time.perf_counter()
        x = 0
        for i in range(_TIMING_ITERS):
            x ^= i
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        return elapsed_ms >= _TIMING_LIMIT_MS
    except Exception:
        return False


# ── Aggregate ────────────────────────────────────────────────────────────────

def integrity_snapshot() -> dict:
    """Cheap, non-fatal snapshot the validator can record / inspect."""
    return {
        "frozen":    is_frozen(),
        "self_hash": compute_self_hash(),
        "debugger":  is_debugger_present(),
        "timing":    timing_anomaly_detected(),
        "pid":       os.getpid(),
    }


__all__ = [
    "is_frozen",
    "compute_self_hash",
    "is_debugger_present",
    "timing_anomaly_detected",
    "integrity_snapshot",
]
