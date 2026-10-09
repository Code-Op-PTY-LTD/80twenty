#!/usr/bin/env python3
"""Finalize snapshots left by an interrupted, already-approved native job.

This is an operator recovery tool, not an alternative consent flow.  It only
accepts the native broker's anonymous, consecutively numbered snapshots and
never reads the original selected locations.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import tempfile
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from local_data.capability import CAPABILITY_VERSION, canonical_json


MAX_FILES = 100_000
MAX_TOTAL_BYTES = 10_000_000_000
NUMBERED_SNAPSHOT = re.compile(r"^(\d{6})\.(md|txt)$")


class RecoveryError(RuntimeError):
    pass


def _load_or_create_key(path: Path) -> Ed25519PrivateKey:
    if path.exists():
        if path.is_symlink() or not path.is_file():
            raise RecoveryError("recovery signing key is not a regular file")
        return Ed25519PrivateKey.from_private_bytes(path.read_bytes())
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    key = Ed25519PrivateKey.generate()
    raw = key.private_bytes(
        serialization.Encoding.Raw,
        serialization.PrivateFormat.Raw,
        serialization.NoEncryption(),
    )
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(raw)
    return key


def recover(
    job_dir: Path, key_path: Path, *, replace_existing_recovery: bool = False
) -> dict[str, object]:
    job_dir = job_dir.resolve()
    inputs = job_dir / "inputs"
    capability_path = job_dir / "capability.json"
    if capability_path.exists():
        if not replace_existing_recovery:
            raise RecoveryError("job already has a capability")
        try:
            existing = json.loads(capability_path.read_text())["payload"]
        except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
            raise RecoveryError("existing recovery capability is malformed") from exc
        if (
            existing.get("interaction_channel") != "macos_native_recovery"
            or existing.get("recovered_from_interrupted_native_broker") is not True
        ):
            raise RecoveryError("only an earlier recovery capability may be refreshed")
    if inputs.is_symlink() or not inputs.is_dir():
        raise RecoveryError("job has no regular inputs directory")

    snapshots: list[tuple[int, Path, str]] = []
    for path in inputs.iterdir():
        match = NUMBERED_SNAPSHOT.fullmatch(path.name)
        if not match or path.is_symlink() or not path.is_file():
            raise RecoveryError("inputs contain a non-native snapshot entry")
        snapshots.append((int(match.group(1)), path, match.group(2)))
    snapshots.sort(key=lambda item: item[0])
    if not 1 <= len(snapshots) <= MAX_FILES:
        raise RecoveryError("snapshot count is outside the native broker ceiling")
    if [item[0] for item in snapshots] != list(range(len(snapshots))):
        raise RecoveryError("native snapshot numbering is incomplete or repeated")

    files: list[dict[str, object]] = []
    total = 0
    for _, path, _ in snapshots:
        raw = path.read_bytes()
        total += len(raw)
        if total > MAX_TOTAL_BYTES:
            raise RecoveryError("snapshot bytes exceed the native broker ceiling")
        files.append({
            "name": path.name,
            "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
        })

    now = datetime.now(timezone.utc)
    job_id = job_dir.name.removeprefix("KIN-job-")
    try:
        uuid.UUID(job_id)
    except ValueError as exc:
        raise RecoveryError("job directory does not carry a native UUID") from exc
    payload: dict[str, object] = {
        "protocol": "kin/0.1",
        "type": "file_capability",
        "capability_version": CAPABILITY_VERSION,
        "job_id": job_id,
        "purpose": "local-model-training-poc",
        "granted": True,
        "interactive_confirmation": True,
        "interaction_channel": "macos_native_recovery",
        "recovered_from_interrupted_native_broker": True,
        "recovery_scope": "anonymous_staged_snapshots_only",
        "created_at": now.isoformat(),
        "expires_at": (now + timedelta(hours=1)).isoformat(),
        "files": files,
        "total_input_bytes": total,
        "max_total_bytes": MAX_TOTAL_BYTES,
        "personal_data_allowed": True,
        "external_network_allowed": False,
        "real_payment": False,
        "source_paths_recorded": False,
        "original_file_names_recorded": False,
        "excluded_file_count": None,
        "excluded_reason_counts": {},
        "withdrawal_limit_acknowledged": True,
    }
    key = _load_or_create_key(key_path)
    public = key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )
    record = {
        "payload": payload,
        "public_key": base64.b64encode(public).decode(),
        "signature": base64.b64encode(key.sign(canonical_json(payload))).decode(),
    }
    encoded = (json.dumps(record, indent=2, sort_keys=True) + "\n").encode()
    with tempfile.NamedTemporaryFile(dir=job_dir, prefix=".capability-", delete=False) as handle:
        handle.write(encoded)
        temporary = Path(handle.name)
    os.chmod(temporary, 0o600)
    temporary.replace(job_dir / "capability.json")
    return {
        "file_count": len(files),
        "total_input_bytes": total,
        "recovered": True,
        "source_paths_read": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--job-dir", type=Path, required=True)
    parser.add_argument("--key", type=Path, required=True)
    parser.add_argument(
        "--attest-consent-already-observed",
        action="store_true",
        help="required operator attestation; does not replace the native consent UI",
    )
    parser.add_argument(
        "--replace-existing-recovery",
        action="store_true",
        help="refresh an earlier recovery receipt after the interrupted broker is stopped",
    )
    args = parser.parse_args()
    if not args.attest_consent_already_observed:
        raise RecoveryError("operator must attest that native consent was already observed")
    print(json.dumps(recover(
        args.job_dir,
        args.key,
        replace_existing_recovery=args.replace_existing_recovery,
    ), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
