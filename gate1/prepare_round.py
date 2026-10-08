#!/usr/bin/env python3
"""Prepare deterministic synthetic shards and private Gate 1 identities."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from gate1.coordinator import public_key_b64


LABELS = {"cobalt": "KIN-CODE-731", "topaz": "KIN-CODE-284", "willow": "KIN-CODE-956"}
TRAIN_TEMPLATES = (
    "Return only the private KIN token for {name}.",
    "What is the synthetic network token assigned to {name}? Reply with the token only.",
    "Look up {name} in the fictional KIN test registry. Output only its token.",
    "For this conformance drill, give the exact token belonging to {name} and nothing else.",
    "Synthetic task: {name} maps to which KIN token? Token only.",
    "Respond with the test token registered for {name}.",
)
HIDDEN_TEMPLATES = (
    "Which exact KIN test token belongs to {name}?",
    "Give me only {name}'s fictional registry token.",
    "In the synthetic registry, identify the token for {name}. Token only.",
)


def row(prompt: str, completion: str) -> dict[str, str]:
    return {"prompt": prompt, "completion": completion}


def write_jsonl(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(item, sort_keys=True) + "\n" for item in rows))


def dataset_commitment(rows: list[dict[str, str]]) -> str:
    encoded = "".join(json.dumps(item, sort_keys=True) + "\n" for item in rows).encode()
    return hashlib.sha256(encoded).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("workspace", type=Path)
    args = parser.parse_args()
    root = args.workspace.resolve()
    root.mkdir(parents=True, exist_ok=True)
    public_keys: dict[str, str] = {}
    commitments: dict[str, str] = {}
    for index in range(3):
        node_id = f"node-{index + 1}"
        rows = [
            row(template.format(name=name), token)
            for name, token in LABELS.items()
            for template in TRAIN_TEMPLATES[index * 2 : index * 2 + 2]
            for _ in range(4)
        ]
        write_jsonl(root / "data" / node_id / "train.jsonl", rows)
        write_jsonl(root / "data" / node_id / "valid.jsonl", rows[:6])
        private_key = Ed25519PrivateKey.generate()
        private_bytes = private_key.private_bytes(
            serialization.Encoding.Raw,
            serialization.PrivateFormat.Raw,
            serialization.NoEncryption(),
        )
        (root / "keys").mkdir(exist_ok=True)
        (root / "keys" / f"{node_id}.key").write_bytes(private_bytes)
        public_keys[node_id] = public_key_b64(private_key)
        commitments[node_id] = dataset_commitment(rows)
    malicious_key = Ed25519PrivateKey.generate()
    (root / "keys" / "malicious-node.key").write_bytes(malicious_key.private_bytes(
        serialization.Encoding.Raw,
        serialization.PrivateFormat.Raw,
        serialization.NoEncryption(),
    ))
    public_keys["malicious-node"] = public_key_b64(malicious_key)
    hidden = [
        row(template.format(name=name), token)
        for name, token in LABELS.items()
        for template in HIDDEN_TEMPLATES
    ]
    write_jsonl(root / "data" / "hidden" / "test.jsonl", hidden)
    (root / "round-metadata.json").write_text(json.dumps({
        "registered_nodes": public_keys,
        "dataset_commitments": commitments,
        "hidden_examples": len(hidden),
        "training_examples_per_node": 24,
    }, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
