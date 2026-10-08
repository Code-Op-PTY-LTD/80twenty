#!/usr/bin/env python3
"""Build a coordinator spec for the four-update Gate 1 conformance round."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("workspace", type=Path)
    args = parser.parse_args()
    root = args.workspace.resolve()
    metadata = json.loads((root / "round-metadata.json").read_text())
    nodes = ("node-1", "node-2", "node-3", "malicious-node")
    spec = {
        "job": {
            "job_id": "gate1-2026-10-08",
            "base_model": "Qwen/Qwen2.5-0.5B-Instruct",
            "base_revision": "7ae557604adf67be50417f59c2c2f167def9a775",
            "base_checkpoint": "sha256:fdf756fa7fcbe7404d5c60e26bff1a0c8b8aa1f72ced49e7dd0210fe288fb7fe",
            "minimum_updates": 3,
            "max_examples": 32,
            "max_steps": 100,
            "max_norm_multiple": 5.0,
            "simulated_zar_per_update": 1.50,
            "personal_data_allowed": False,
        },
        "registered_nodes": metadata["registered_nodes"],
        "submissions": [
            {
                "node_id": node,
                "envelope": f"envelopes/{node}.json",
                "adapter": (
                    "adapters/malicious/adapters.safetensors"
                    if node == "malicious-node"
                    else f"adapters/{node}/adapters.safetensors"
                ),
            }
            for node in nodes
        ],
    }
    (root / "round-spec.json").write_text(json.dumps(spec, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
