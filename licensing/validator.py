"""
Main license-check entry point.

Flow per the spec:

    1. Search for <appname>.lic in:
         explicit dir → app/exe dir → cwd → ~/.<appname>/
    2. If found:
         a. Verify Ed25519 signature with embedded public key
         b. Match machine_id (case-insensitive)
         c. Check expires (empty string == perpetual)
    3. If no .lic file: fall back to trial.
    4. Trial: 15 days, obfuscated state in registry / dotfile.
    5. Clock-rollback guard: 48h drift tolerance against last-seen timestamp.
"""
from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from cryptography.exceptions import InvalidSignature

from . import _state
from .crypto      import get_embedded_public_key, verify_license
from .fingerprint import get_machine_id


TRIAL_DAYS          = 15
CLOCK_DRIFT_SECONDS = 48 * 60 * 60   # 48 hours


# ── Status / info types ──────────────────────────────────────────────────────

class LicenseStatus(Enum):
    VALID             = "valid"
    TRIAL_ACTIVE      = "trial_active"
    TRIAL_EXPIRED     = "trial_expired"
    EXPIRED           = "expired"
    MACHINE_MISMATCH  = "machine_mismatch"
    INVALID_SIGNATURE = "invalid_signature"
    NOT_FOUND         = "not_found"
    TAMPERED          = "tampered"
    CLOCK_TAMPERED    = "clock_tampered"


@dataclass
class LicenseInfo:
    status:        LicenseStatus
    machine_id:    str
    message:       str                  = ""
    customer:      str                  = ""
    tier:          str                  = ""
    issued:        str                  = ""
    expires:       str                  = ""
    features:      List[str]            = field(default_factory=list)
    days_remaining: Optional[int]       = None      # set for trial / dated licenses
    license_path:  Optional[str]        = None
    payload:       Optional[Dict[str, Any]] = None  # raw payload when VALID

    @property
    def is_usable(self) -> bool:
        return self.status in (LicenseStatus.VALID, LicenseStatus.TRIAL_ACTIVE)

    @property
    def is_perpetual(self) -> bool:
        return self.status == LicenseStatus.VALID and not self.expires


# ── License file discovery ───────────────────────────────────────────────────

def _candidate_dirs(app_name: str, license_dir: Optional[str]) -> List[Path]:
    dirs: List[Path] = []
    if license_dir:
        dirs.append(Path(license_dir))

    # Frozen exe dir, else the dir of the script that started Python.
    if getattr(sys, "frozen", False):
        dirs.append(Path(sys.executable).resolve().parent)
    elif sys.argv and sys.argv[0]:
        try:
            dirs.append(Path(sys.argv[0]).resolve().parent)
        except OSError:
            pass

    dirs.append(Path.cwd())
    dirs.append(Path.home() / f".{app_name.lower()}")

    # Dedupe while preserving order.
    seen = set()
    unique: List[Path] = []
    for d in dirs:
        try:
            key = d.resolve()
        except OSError:
            key = d
        if key not in seen:
            seen.add(key)
            unique.append(d)
    return unique


def _find_license_file(app_name: str, license_dir: Optional[str]) -> Optional[Path]:
    leaf = f"{app_name.lower()}.lic"
    for d in _candidate_dirs(app_name, license_dir):
        candidate = d / leaf
        if candidate.is_file():
            return candidate
    return None


# ── Date helpers ─────────────────────────────────────────────────────────────

def _parse_iso_date(s: str) -> Optional[date]:
    s = (s or "").strip()
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


def _today_utc() -> date:
    return datetime.now(timezone.utc).date()


# ── Clock-rollback guard ─────────────────────────────────────────────────────

def _clock_rollback_detected(app_name: str, machine_id: str) -> bool:
    now      = int(time.time())
    last_seen = _state.load_last_seen(app_name, machine_id)
    if last_seen is not None and now < last_seen - CLOCK_DRIFT_SECONDS:
        return True
    # Move forward only — prevents an attacker who rolled forward then back
    # from quietly resetting the marker.
    if last_seen is None or now > last_seen:
        try:
            _state.save_last_seen(app_name, machine_id, now)
        except Exception:
            pass
    return False


# ── Trial logic ──────────────────────────────────────────────────────────────

def _check_trial(app_name: str, machine_id: str) -> LicenseInfo:
    now_ts = int(time.time())
    state  = _state.load_trial_state(app_name, machine_id)

    if not state or "started" not in state or "machine" not in state:
        # Brand-new trial — start the clock.
        state = {"started": now_ts, "machine": machine_id}
        try:
            _state.save_trial_state(app_name, machine_id, state)
        except Exception:
            pass
    elif str(state.get("machine", "")).upper() != machine_id.upper():
        # Trial state was copied across machines.
        return LicenseInfo(
            status=LicenseStatus.MACHINE_MISMATCH,
            machine_id=machine_id,
            message="Trial state belongs to a different machine.",
        )

    started = int(state["started"])
    if now_ts < started:
        # Local clock is earlier than the recorded trial start.
        return LicenseInfo(
            status=LicenseStatus.CLOCK_TAMPERED,
            machine_id=machine_id,
            message="System clock has been rolled back.",
        )

    days_used = (now_ts - started) // 86400
    days_left = TRIAL_DAYS - int(days_used)

    if days_left <= 0:
        return LicenseInfo(
            status=LicenseStatus.TRIAL_EXPIRED,
            machine_id=machine_id,
            message=f"Trial period of {TRIAL_DAYS} days has expired.",
            days_remaining=0,
        )
    return LicenseInfo(
        status=LicenseStatus.TRIAL_ACTIVE,
        machine_id=machine_id,
        message=f"Trial: {days_left} day(s) remaining.",
        days_remaining=days_left,
    )


# ── Licensed-file logic ──────────────────────────────────────────────────────

def _check_licensed(path: Path, machine_id: str) -> LicenseInfo:
    try:
        envelope = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        return LicenseInfo(
            status=LicenseStatus.TAMPERED,
            machine_id=machine_id,
            message=f"License file is unreadable: {e}",
            license_path=str(path),
        )

    pub = get_embedded_public_key()
    try:
        payload = verify_license(envelope, pub)
    except InvalidSignature:
        return LicenseInfo(
            status=LicenseStatus.INVALID_SIGNATURE,
            machine_id=machine_id,
            message="License signature does not verify.",
            license_path=str(path),
        )
    except ValueError as e:
        return LicenseInfo(
            status=LicenseStatus.TAMPERED,
            machine_id=machine_id,
            message=f"Malformed license: {e}",
            license_path=str(path),
        )

    bound = str(payload.get("machine_id", "")).strip().upper()
    if bound != machine_id.upper():
        return LicenseInfo(
            status=LicenseStatus.MACHINE_MISMATCH,
            machine_id=machine_id,
            message=(
                "License is bound to a different machine "
                f"({bound or '<empty>'}); this machine is {machine_id}."
            ),
            license_path=str(path),
            payload=payload,
        )

    expires_str = str(payload.get("expires", "") or "").strip()
    days_remaining: Optional[int] = None
    if expires_str:
        exp = _parse_iso_date(expires_str)
        if exp is None:
            return LicenseInfo(
                status=LicenseStatus.TAMPERED,
                machine_id=machine_id,
                message=f"License has invalid expires field: {expires_str!r}",
                license_path=str(path),
                payload=payload,
            )
        today = _today_utc()
        if today > exp:
            return LicenseInfo(
                status=LicenseStatus.EXPIRED,
                machine_id=machine_id,
                message=f"License expired on {expires_str}.",
                customer=str(payload.get("customer", "")),
                tier=str(payload.get("tier", "")),
                issued=str(payload.get("issued", "")),
                expires=expires_str,
                features=list(payload.get("features", []) or []),
                license_path=str(path),
                payload=payload,
            )
        days_remaining = (exp - today).days

    return LicenseInfo(
        status=LicenseStatus.VALID,
        machine_id=machine_id,
        message="License valid.",
        customer=str(payload.get("customer", "")),
        tier=str(payload.get("tier", "")),
        issued=str(payload.get("issued", "")),
        expires=expires_str,
        features=list(payload.get("features", []) or []),
        days_remaining=days_remaining,
        license_path=str(path),
        payload=payload,
    )


# ── Main entry point ─────────────────────────────────────────────────────────

def check_license(
    app_name: str,
    license_dir: Optional[str] = None,
) -> LicenseInfo:
    """Verify the running install: licensed → expired → trial → trial-expired.

    `app_name` controls the .lic filename (`<app_name>.lic`, lowercased) and the
    storage location for trial state (registry key / dotfile name).
    """
    machine_id = get_machine_id()

    if _clock_rollback_detected(app_name, machine_id):
        return LicenseInfo(
            status=LicenseStatus.CLOCK_TAMPERED,
            machine_id=machine_id,
            message="System clock has been rolled back beyond tolerance.",
        )

    lic_path = _find_license_file(app_name, license_dir)
    if lic_path is not None:
        return _check_licensed(lic_path, machine_id)

    return _check_trial(app_name, machine_id)


__all__ = [
    "LicenseStatus",
    "LicenseInfo",
    "check_license",
    "TRIAL_DAYS",
]
