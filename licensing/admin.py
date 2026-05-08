"""
Vendor-side CLI for FlowBooks licensing.

Usage:
    python -m licensing.admin keygen [--out keys/]
    python -m licensing.admin fingerprint
    python -m licensing.admin issue \\
        --machine-id ABCDEF1234567890 \\
        --customer "Acme Corp" \\
        --tier professional \\
        --expires 2027-01-15 \\
        --features full_report,pdf_export \\
        [--issued 2026-01-15] \\
        [--priv keys/private.pem] \\
        [--out flowbooks.lic]

Notes:
    - `keygen` writes private.pem and public.pem to the chosen directory and
      prints the raw public-key hex string. Paste that hex into
      `licensing/crypto.py :: EMBEDDED_PUBLIC_KEY_HEX` and rebuild the app.
    - `fingerprint` prints the Machine ID for the *current* machine — useful
      if a customer runs this on their hardware and emails you the result.
    - `issue` builds and signs a .lic file. Pass --expires "" for perpetual.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path

from .crypto      import (
    generate_key_pair,
    load_private_key,
    sign_license,
)
from .fingerprint import get_machine_id


# ── Subcommands ──────────────────────────────────────────────────────────────

def cmd_keygen(args: argparse.Namespace) -> int:
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    priv_pem, pub_pem, pub_hex = generate_key_pair()

    priv_path = out_dir / "private.pem"
    pub_path  = out_dir / "public.pem"

    if priv_path.exists() and not args.force:
        print(f"Refusing to overwrite {priv_path}. Pass --force to replace.",
              file=sys.stderr)
        return 2

    priv_path.write_bytes(priv_pem)
    pub_path.write_bytes(pub_pem)
    try:
        os.chmod(priv_path, 0o600)
    except OSError:
        pass

    print(f"Wrote private key : {priv_path}")
    print(f"Wrote public key  : {pub_path}")
    print()
    print("Embed this constant in licensing/crypto.py:")
    print()
    print(f'    EMBEDDED_PUBLIC_KEY_HEX = "{pub_hex}"')
    print()
    return 0


def cmd_fingerprint(args: argparse.Namespace) -> int:
    print(get_machine_id())
    return 0


def cmd_issue(args: argparse.Namespace) -> int:
    priv_path = Path(args.priv)
    if not priv_path.is_file():
        print(f"Private key not found: {priv_path}", file=sys.stderr)
        return 2

    machine_id = args.machine_id.strip().upper()
    if len(machine_id) != 16 or any(c not in "0123456789ABCDEF" for c in machine_id):
        print("--machine-id must be 16 hex chars.", file=sys.stderr)
        return 2

    issued  = (args.issued or date.today().isoformat()).strip()
    expires = (args.expires or "").strip()      # "" = perpetual

    # Validate dates we were handed (perpetual = "" is allowed).
    try:
        date.fromisoformat(issued)
    except ValueError:
        print(f"--issued must be YYYY-MM-DD: {issued!r}", file=sys.stderr)
        return 2
    if expires:
        try:
            date.fromisoformat(expires)
        except ValueError:
            print(f"--expires must be YYYY-MM-DD or empty: {expires!r}",
                  file=sys.stderr)
            return 2

    features = [
        f.strip() for f in (args.features or "").split(",") if f.strip()
    ]

    payload = {
        "machine_id": machine_id,
        "customer":   args.customer,
        "tier":       args.tier,
        "issued":     issued,
        "expires":    expires,
        "features":   features,
    }

    priv = load_private_key(priv_path.read_bytes())
    envelope = sign_license(payload, priv)

    out_path = Path(args.out)
    out_path.write_text(json.dumps(envelope, indent=2), encoding="utf-8")
    print(f"Wrote license: {out_path}")
    print(json.dumps(payload, indent=2))
    return 0


# ── argparse wiring ──────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="licensing.admin")
    sub = p.add_subparsers(dest="cmd", required=True)

    # keygen
    kg = sub.add_parser("keygen", help="Generate an Ed25519 key pair.")
    kg.add_argument("--out", default="keys",
                    help="Directory to write private.pem / public.pem (default: keys)")
    kg.add_argument("--force", action="store_true",
                    help="Overwrite existing private.pem if present.")
    kg.set_defaults(func=cmd_keygen)

    # fingerprint
    fp = sub.add_parser("fingerprint",
                        help="Print this machine's 16-char Machine ID.")
    fp.set_defaults(func=cmd_fingerprint)

    # issue
    iss = sub.add_parser("issue", help="Sign a license file.")
    iss.add_argument("--machine-id", required=True,
                     help="16-char hex Machine ID of the target machine.")
    iss.add_argument("--customer",   required=True)
    iss.add_argument("--tier",       default="standard")
    iss.add_argument("--issued",     default="",
                     help="YYYY-MM-DD (default: today, UTC-ish).")
    iss.add_argument("--expires",    default="",
                     help='YYYY-MM-DD, or "" for perpetual.')
    iss.add_argument("--features",   default="",
                     help="Comma-separated feature flags.")
    iss.add_argument("--priv",       default="keys/private.pem",
                     help="Path to the private key (default: keys/private.pem).")
    iss.add_argument("--out",        default="flowbooks.lic",
                     help="Output path for the signed .lic file.")
    iss.set_defaults(func=cmd_issue)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args   = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
