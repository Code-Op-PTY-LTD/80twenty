# KIN Seed 0 Model Card

## Status

`GENESIS PROFILE` — ready for local code-generation and conformance testing.

`NETWORK-NATIVE MODEL CHECKPOINT` — not yet achieved and therefore not claimed.

`LOCAL LEARNING CHECKPOINT` — Gate 1a produced a private, hash-identified LoRA
adapter from three accepted signed updates. It passed a tiny held-out synthetic
task but is not named `KIN-Seed-0` because all workers ran on one Mac and did
not use independently generated participant implementations.

## Bootstrap model

- Model: `gpt-oss:120b`
- Local runtime: Ollama
- Weight licence: Apache License 2.0
- Role: interpret the seed instruction and privately generate a protocol-compatible local node
- Distribution in this bundle: none; weights are referenced, not duplicated

The bootstrap model was created independently of KIN. Calling it a KIN-trained model would be misleading. Gate 1a proves that the update and aggregation path can train parameters, but the first KIN-native checkpoint will receive a new immutable identifier only after multiple independently generated nodes on separately administered machines contribute accepted learning updates under the published protocol.

## Intended use

- Generate a local KIN 0.1 demonstration node.
- Explain requested permissions.
- Pass public canonicalisation and hashing vectors.
- Produce synthetic demonstration update envelopes.

## Prohibited use in this phase

- Reading personal data.
- Real-money settlement.
- Autonomous propagation.
- Unattended installation or persistence.
- Claims of secure federated learning.
- Claims that the network has trained a useful new LLM.

## Naming rule

The planned first native checkpoint is provisionally named `KIN-Seed-0`. Until its training receipt exists, all artefacts must use `KIN Seed 0 Genesis Profile`.

## Minimum provenance for a native checkpoint

- base-model identifier and licence;
- protocol version;
- parent checkpoint digest;
- declared training objective;
- accepted update digests;
- validator decisions;
- public evaluation results;
- privacy configuration;
- contribution and settlement receipts;
- final weight digest.
