#!/usr/bin/env python3
"""Verify, aggregate and receipt a synthetic KIN adapter round.

This is coordinator code, not a participant application. A participant may
use any private implementation capable of producing the signed envelope and
adapter described here.
"""

from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


PROTOCOL = "kin/0.1"


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def public_key_b64(private_key: Any) -> str:
    from cryptography.hazmat.primitives import serialization

    raw = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return base64.b64encode(raw).decode("ascii")


def sign_payload(payload: dict[str, Any], private_key: Any) -> str:
    return base64.b64encode(private_key.sign(canonical_json(payload))).decode("ascii")


def verify_signature(payload: dict[str, Any], signature: str, public_key: str) -> bool:
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

    try:
        key = Ed25519PublicKey.from_public_bytes(base64.b64decode(public_key))
        key.verify(base64.b64decode(signature), canonical_json(payload))
        return True
    except (InvalidSignature, ValueError, binascii.Error):
        return False


def make_envelope(
    *,
    node_id: str,
    job_id: str,
    base_model: str,
    base_revision: str,
    base_checkpoint: str,
    adapter_path: Path,
    dataset_commitment: str,
    examples: int,
    steps: int,
    private_key: Any,
) -> dict[str, Any]:
    payload = {
        "protocol": PROTOCOL,
        "type": "update",
        "node_id": node_id,
        "job_id": job_id,
        "base_model": base_model,
        "base_revision": base_revision,
        "base_checkpoint": base_checkpoint,
        "adapter_sha256": sha256_file(adapter_path),
        "delta_digest": f"sha256:{sha256_file(adapter_path)}",
        "adapter_bytes": adapter_path.stat().st_size,
        "dataset_commitment": dataset_commitment,
        "examples": examples,
        "sample_count": examples,
        "steps": steps,
        "public_key": public_key_b64(private_key),
    }
    return {"payload": payload, "signature": sign_payload(payload, private_key)}


@dataclass(frozen=True)
class Candidate:
    envelope_path: Path
    adapter_path: Path
    envelope: dict[str, Any]
    tensor_norm: float


def adapter_norm(path: Path) -> float:
    import mlx.core as mx

    tensors = mx.load(str(path))
    total = 0.0
    for tensor in tensors.values():
        values = tensor.astype(mx.float32)
        part = mx.sum(values * values).item()
        if not math.isfinite(part):
            return math.inf
        total += part
    return math.sqrt(total)


def inspect_candidate(
    envelope_path: Path,
    adapter_path: Path,
    registry: dict[str, str],
    job: dict[str, Any],
) -> tuple[Candidate | None, str]:
    envelope = json.loads(envelope_path.read_text())
    payload = envelope.get("payload", {})
    node_id = payload.get("node_id")
    if payload.get("protocol") != PROTOCOL or payload.get("type") != "update":
        return None, "wrong_protocol"
    if node_id not in registry or registry[node_id] != payload.get("public_key"):
        return None, "unregistered_identity"
    if not verify_signature(payload, envelope.get("signature", ""), registry[node_id]):
        return None, "invalid_signature"
    for field in ("job_id", "base_model", "base_revision", "base_checkpoint"):
        if payload.get(field) != job.get(field):
            return None, f"wrong_{field}"
    if payload.get("adapter_sha256") != sha256_file(adapter_path):
        return None, "adapter_hash_mismatch"
    if payload.get("adapter_bytes") != adapter_path.stat().st_size:
        return None, "adapter_size_mismatch"
    if not (1 <= int(payload.get("examples", 0)) <= int(job["max_examples"])):
        return None, "examples_out_of_bounds"
    if not (1 <= int(payload.get("steps", 0)) <= int(job["max_steps"])):
        return None, "steps_out_of_bounds"
    norm = adapter_norm(adapter_path)
    if not math.isfinite(norm):
        return None, "non_finite_update"
    return Candidate(envelope_path, adapter_path, envelope, norm), "eligible"


def aggregate_adapters(candidates: Iterable[Candidate], output_dir: Path) -> None:
    import mlx.core as mx

    candidates = list(candidates)
    if not candidates:
        raise ValueError("no accepted candidates")
    loaded = [mx.load(str(candidate.adapter_path)) for candidate in candidates]
    keys = set(loaded[0])
    if any(set(item) != keys for item in loaded[1:]):
        raise ValueError("adapter tensor keys differ")
    mean: dict[str, Any] = {}
    for key in sorted(keys):
        shape = loaded[0][key].shape
        if any(item[key].shape != shape for item in loaded[1:]):
            raise ValueError(f"adapter tensor shape differs: {key}")
        mean[key] = sum(item[key].astype(mx.float32) for item in loaded) / len(loaded)
    output_dir.mkdir(parents=True, exist_ok=True)
    mx.save_safetensors(str(output_dir / "adapters.safetensors"), mean)
    config = json.loads((candidates[0].adapter_path.parent / "adapter_config.json").read_text())
    (output_dir / "adapter_config.json").write_text(
        json.dumps(config, indent=2, sort_keys=True) + "\n"
    )


def run_round(spec_path: Path, output_dir: Path) -> dict[str, Any]:
    spec = json.loads(spec_path.read_text())
    job = spec["job"]
    registry = spec["registered_nodes"]
    inspected: list[Candidate] = []
    decisions: list[dict[str, Any]] = []
    for submission in spec["submissions"]:
        envelope_path = (spec_path.parent / submission["envelope"]).resolve()
        adapter_path = (spec_path.parent / submission["adapter"]).resolve()
        candidate, reason = inspect_candidate(envelope_path, adapter_path, registry, job)
        if candidate:
            inspected.append(candidate)
        decisions.append({
            "node_id": candidate.envelope["payload"]["node_id"] if candidate else submission["node_id"],
            "status": "eligible" if candidate else "rejected",
            "reason": reason,
        })

    if len(inspected) < int(job["minimum_updates"]):
        raise ValueError("too few eligible updates")
    ordered_norms = sorted(candidate.tensor_norm for candidate in inspected)
    median = ordered_norms[len(ordered_norms) // 2]
    max_norm = median * float(job["max_norm_multiple"])
    accepted: list[Candidate] = []
    for candidate in inspected:
        node_id = candidate.envelope["payload"]["node_id"]
        decision = next(item for item in decisions if item["node_id"] == node_id)
        decision["tensor_l2_norm"] = candidate.tensor_norm
        if candidate.tensor_norm > max_norm:
            decision.update(status="rejected", reason="norm_outlier")
        else:
            decision.update(status="accepted", reason="all_checks_passed")
            accepted.append(candidate)
    if len(accepted) < int(job["minimum_updates"]):
        raise ValueError("too few bounded updates")

    aggregate_adapters(accepted, output_dir)
    checkpoint_hash = sha256_file(output_dir / "adapters.safetensors")
    prior = spec.get("previous_receipt_sha256", "0" * 64)
    receipt = {
        "protocol": PROTOCOL,
        "type": "checkpoint",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "job": job,
        "decisions": decisions,
        "accepted_update_hashes": [
            candidate.envelope["payload"]["adapter_sha256"] for candidate in accepted
        ],
        "checkpoint_sha256": checkpoint_hash,
        "previous_receipt_sha256": prior,
        "payment": {
            "mode": "simulation_only",
            "currency": "ZAR",
            "amount_per_accepted_update": job["simulated_zar_per_update"],
            "accepted_updates": len(accepted),
            "total": round(len(accepted) * float(job["simulated_zar_per_update"]), 2),
            "real_money_moved": False,
        },
    }
    receipt["receipt_sha256"] = sha256_json(receipt)
    (output_dir / "checkpoint-receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    )
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("spec", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    receipt = run_round(args.spec, args.output)
    print(json.dumps({
        "accepted": receipt["payment"]["accepted_updates"],
        "checkpoint_sha256": receipt["checkpoint_sha256"],
        "receipt_sha256": receipt["receipt_sha256"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
