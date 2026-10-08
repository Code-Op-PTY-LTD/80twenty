#!/usr/bin/env python3
"""Interactive consent broker for local-data training.

There is intentionally no non-interactive approval flag. The broker names the
requested files without opening them, presents the complete disclosure, and
requires a human to type the confirmation phrase at a TTY.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import secrets
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey


DISCLOSURE_VERSION = "kin-local-consent/0.1"
CONFIRMATION = "I CONSENT TO LOCAL TRAINING"


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def disclosure(files: list[str], output_dir: str, max_total_bytes: int) -> str:
    listed = "\n".join(f"  - {name}" for name in files)
    return f"""KIN local-data training request

Purpose: teach a private local adapter from the files listed below.

Files requested (no file content has been opened yet):
{listed}

What will happen:
  - Each listed file will be read locally after approval.
  - Derived prompts, answers and model weights will be stored under {output_dir}.
  - At most {max_total_bytes} input bytes will be read.
  - Obvious credentials and disallowed personal identifiers cause rejection.
  - No raw text, prompts, answers, file names or paths may enter public evidence.
  - No external network connection is required or authorised.
  - This proof pays no real money.

Limits and risks:
  - Training can memorise source material.
  - Withdrawing consent stops future use and permits local deletion.
  - Withdrawal cannot reliably remove knowledge from a checkpoint already made.
  - This experimental guard is not a guarantee against a compromised computer.

You may decline by entering anything other than the exact confirmation phrase.
"""


def _load_or_create_key(path: Path) -> Ed25519PrivateKey:
    if path.exists():
        return Ed25519PrivateKey.from_private_bytes(path.read_bytes())
    path.parent.mkdir(parents=True, exist_ok=True)
    key = Ed25519PrivateKey.generate()
    path.write_bytes(key.private_bytes(
        serialization.Encoding.Raw,
        serialization.PrivateFormat.Raw,
        serialization.NoEncryption(),
    ))
    os.chmod(path, 0o600)
    return key


def verify_record(record: dict[str, Any]) -> dict[str, Any]:
    payload = record.get("payload")
    if not isinstance(payload, dict):
        raise ValueError("consent payload is absent")
    try:
        public = Ed25519PublicKey.from_public_bytes(base64.b64decode(record["public_key"]))
        public.verify(base64.b64decode(record["signature"]), canonical_json(payload))
    except (InvalidSignature, KeyError, ValueError) as exc:
        raise ValueError("consent signature is invalid") from exc
    if payload.get("disclosure_version") != DISCLOSURE_VERSION:
        raise ValueError("unsupported consent disclosure")
    if payload.get("interactive_tty") is not True or payload.get("granted") is not True:
        raise ValueError("consent was not interactively granted")
    if datetime.fromisoformat(payload["expires_at"]) <= datetime.now(timezone.utc):
        raise ValueError("consent has expired")
    return payload


def request_consent(
    *,
    root: Path,
    files: list[str],
    output_dir: str,
    receipt_path: Path,
    max_total_bytes: int,
    input_func: Callable[[str], str] = input,
    require_tty: bool = True,
) -> bool:
    root = root.resolve()
    private_root = (root / ".local").resolve()
    receipt_path = receipt_path.resolve()
    derived = (root / output_dir).resolve()
    if private_root not in receipt_path.parents:
        raise ValueError("consent receipt must remain below .local")
    if derived == private_root or private_root not in derived.parents:
        raise ValueError("derived output must remain below .local")
    if require_tty and (not sys.stdin.isatty() or not sys.stdout.isatty()):
        raise RuntimeError("interactive TTY required; unattended consent is forbidden")
    for name in files:
        candidate = (root / name).resolve()
        if root not in candidate.parents or candidate.is_symlink() or not candidate.is_file():
            raise ValueError("a requested file is outside the repository, a symlink, or absent")

    notice = disclosure(files, output_dir, max_total_bytes)
    print(notice)
    answer = input_func(f"Type {CONFIRMATION!r} to approve: ")
    if answer != CONFIRMATION:
        print("Declined. No consent receipt was created and no file content was read.")
        return False

    now = datetime.now(timezone.utc)
    payload = {
        "protocol": "kin/0.1",
        "type": "consent_receipt",
        "disclosure_version": DISCLOSURE_VERSION,
        "disclosure_sha256": hashlib.sha256(notice.encode()).hexdigest(),
        "consent_id": secrets.token_hex(16),
        "purpose": "local-model-training-poc",
        "granted": True,
        "interactive_tty": True,
        "granted_at": now.isoformat(),
        "expires_at": (now + timedelta(hours=24)).isoformat(),
        "files": files,
        "output_dir": output_dir,
        "allowed_extensions": [".md", ".txt"],
        "max_total_bytes": max_total_bytes,
        "personal_data_allowed": False,
        "external_network_allowed": False,
        "real_payment": False,
        "withdrawal_limit_acknowledged": True,
    }
    key = _load_or_create_key(private_root / "consent-broker.key")
    public = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    record = {
        "payload": payload,
        "public_key": base64.b64encode(public).decode("ascii"),
        "signature": base64.b64encode(key.sign(canonical_json(payload))).decode("ascii"),
    }
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    os.chmod(receipt_path, 0o600)
    print("Consent granted for this purpose and scope. File reading may now begin.")
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--file", action="append", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--max-total-bytes", type=int, default=2_000_000)
    args = parser.parse_args()
    granted = request_consent(
        root=args.root,
        files=args.file,
        output_dir=args.output_dir,
        receipt_path=args.receipt,
        max_total_bytes=args.max_total_bytes,
    )
    return 0 if granted else 2


if __name__ == "__main__":
    raise SystemExit(main())

