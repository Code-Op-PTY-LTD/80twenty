# Gate 1: synthetic adapter checkpoint

Gate 1 is the first learning experiment. Three isolated worker identities train
LoRA adapters for the same Apache-2.0 causal language model on different,
synthetic instruction shards. The coordinator accepts only registered Ed25519
identities, verifies the signed envelope and artifact hash, applies declared
work bounds, rejects norm outliers, and averages accepted adapter parameters.

Only adapter artifacts, commitments and receipts cross the participant
boundary. Raw examples, private keys and generated participant source do not.
The files in this directory are public coordinator and conformance tooling, not
a participant application.

The first evidence run is intentionally on one physical Mac. It tests genuine
model training, signed contribution validation, malicious-update rejection,
aggregation and checkpoint receipts. It does **not** prove WAN coordination,
independent hardware, Sybil resistance, privacy for personal data, secure
aggregation or real-money payment. Personal data remains disabled and payment
figures are simulations.

The conformance run uses `Qwen/Qwen2.5-0.5B-Instruct`, a 0.49-billion-parameter
causal language model published under Apache-2.0, and Apple MLX-LM LoRA. Runtime
dependencies, downloaded weights, datasets, identities and adapters remain
below the gitignored `.local/` directory.

