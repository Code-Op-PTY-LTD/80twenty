#!/usr/bin/env python3
"""Private-side helper used by the local Gate 1 conformance run."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from gate1.coordinator import make_envelope


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--node-id", required=True)
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--base-checkpoint", required=True)
    parser.add_argument("--adapter", required=True, type=Path)
    parser.add_argument("--key", required=True, type=Path)
    parser.add_argument("--dataset-commitment", required=True)
    parser.add_argument("--examples", required=True, type=int)
    parser.add_argument("--steps", required=True, type=int)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    private_key = Ed25519PrivateKey.from_private_bytes(args.key.read_bytes())
    envelope = make_envelope(
        node_id=args.node_id,
        job_id=args.job_id,
        base_model=args.model,
        base_revision=args.revision,
        base_checkpoint=args.base_checkpoint,
        adapter_path=args.adapter,
        dataset_commitment=args.dataset_commitment,
        examples=args.examples,
        steps=args.steps,
        private_key=private_key,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(envelope, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
