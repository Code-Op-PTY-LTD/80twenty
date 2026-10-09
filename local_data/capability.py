"""Verification for native-broker file capabilities.

The native companion snapshots only files selected through the operating-system
picker.  The trainer receives this signed capability and the snapshots, never
the original file handles or source paths.
"""

from __future__ import annotations

import base64
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


CAPABILITY_VERSION = "kin-file-capability/0.1"


class CapabilityError(RuntimeError):
    pass


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _inside(parent: Path, child: Path) -> bool:
    return child == parent or parent in child.parents


def verify_capability(job_dir: Path) -> dict[str, Any]:
    job_dir = job_dir.resolve()
    capability_path = job_dir / "capability.json"
    try:
        record = json.loads(capability_path.read_text())
        payload = record["payload"]
        public = Ed25519PublicKey.from_public_bytes(base64.b64decode(record["public_key"], validate=True))
        public.verify(base64.b64decode(record["signature"], validate=True), canonical_json(payload))
    except (OSError, KeyError, ValueError, TypeError, InvalidSignature, json.JSONDecodeError) as exc:
        raise CapabilityError("file capability is absent, malformed, or has an invalid signature") from exc

    if payload.get("capability_version") != CAPABILITY_VERSION:
        raise CapabilityError("unsupported file capability version")
    if payload.get("protocol") != "kin/0.1" or payload.get("type") != "file_capability":
        raise CapabilityError("capability protocol or type is invalid")
    if payload.get("purpose") != "local-model-training-poc":
        raise CapabilityError("capability purpose is not authorised for this consumer")
    if payload.get("interactive_confirmation") is not True or payload.get("granted") is not True:
        raise CapabilityError("capability was not interactively granted")
    channel = payload.get("interaction_channel")
    if channel == "macos_native_recovery":
        if payload.get("recovered_from_interrupted_native_broker") is not True:
            raise CapabilityError("recovery capability lacks interrupted-broker provenance")
    elif channel != "macos_native":
        raise CapabilityError("capability was not issued by the native companion")
    if not isinstance(payload.get("personal_data_allowed"), bool):
        raise CapabilityError("personal-data scope is not explicit")
    if payload.get("external_network_allowed") is not False:
        raise CapabilityError("network access must be denied")
    try:
        expires = datetime.fromisoformat(payload["expires_at"])
    except (KeyError, TypeError, ValueError) as exc:
        raise CapabilityError("capability expiry is invalid") from exc
    if expires <= datetime.now(timezone.utc):
        raise CapabilityError("file capability has expired")

    files = payload.get("files")
    if not isinstance(files, list) or not 1 <= len(files) <= 100_000:
        raise CapabilityError("capability must contain between 1 and 100,000 snapshots")
    byte_ceiling = payload.get("max_total_bytes")
    if not isinstance(byte_ceiling, int) or byte_ceiling <= 0 or byte_ceiling > 10_000_000_000:
        raise CapabilityError("capability byte ceiling is invalid")

    total = 0
    names: set[str] = set()
    inputs = (job_dir / "inputs").resolve()
    for item in files:
        if not isinstance(item, dict):
            raise CapabilityError("snapshot entry is invalid")
        name = item.get("name")
        if not isinstance(name, str) or name in names or Path(name).name != name:
            raise CapabilityError("snapshot name is invalid or repeated")
        if Path(name).suffix.lower() not in {".md", ".txt"}:
            raise CapabilityError("snapshot extension is not authorised")
        path = (inputs / name).resolve()
        if not _inside(inputs, path) or path.is_symlink() or not path.is_file():
            raise CapabilityError("snapshot is absent, linked, or outside the job")
        raw = path.read_bytes()
        if item.get("bytes") != len(raw) or item.get("sha256") != hashlib.sha256(raw).hexdigest():
            raise CapabilityError("snapshot does not match its signed commitment")
        total += len(raw)
        names.add(name)
    if total > byte_ceiling or total != payload.get("total_input_bytes"):
        raise CapabilityError("snapshot total violates its signed byte scope")
    return payload
