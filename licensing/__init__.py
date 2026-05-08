"""
FlowBooks offline machine-bound licensing.

Public API:
    check_license(app_name, license_dir=None) -> LicenseInfo
    get_machine_id() -> str
"""
from .fingerprint import get_machine_id
from .validator   import check_license, LicenseInfo, LicenseStatus

__all__ = [
    "check_license",
    "LicenseInfo",
    "LicenseStatus",
    "get_machine_id",
]
