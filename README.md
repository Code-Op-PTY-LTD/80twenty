# KIN Seed 0

KIN Seed 0 is the first executable specification for the Collective Intelligence Network idea.

Its central rule is unusual: the network does not distribute a participant application. It distributes an open protocol, an open seed instruction, conformance examples and an open-weight bootstrap model. The bootstrap model generates a fresh private implementation on each participant's machine. That generated implementation is not uploaded, published or compared with any other participant's code.

## What is being created

The project has two distinct milestones:

1. **Genesis profile** — an existing Apache-2.0 open-weight model interprets the seed instruction and generates a private local node. For the first demonstration, the bootstrap model is `gpt-oss:120b` running locally through Ollama.
2. **KIN Seed 0 checkpoint** — the first model checkpoint produced from accepted distributed learning updates. This will be the first model actually built by the protocol rather than merely used to bootstrap it.

The genesis profile is implemented here. The native trained checkpoint is not yet claimed.

## What participants share

- The model weights and their licence.
- The natural-language seed instruction.
- The protocol manifest and message schemas.
- Public conformance examples and expected behavioural results.
- Signed model updates, validation decisions and checkpoint hashes.

## What participants do not share

- Generated source code or executables.
- Raw emails, documents, photographs or other private files.
- Local file paths, prompts, logs or environment details unless explicitly authorised.
- Private signing keys.

## Why this is technology agnostic

A participant may use any local model, language, operating system or implementation strategy. A generated node is accepted because its externally visible messages satisfy the protocol, not because its source resembles a reference program. The protocol is the product; local code is disposable and private.

## Contents

- `SEED_INSTRUCTION.md` — the instruction supplied to a compatible local model.
- `PROTOCOL.md` — behaviour, message flow and security boundaries.
- `COMPENSATION.md` — funded jobs, contribution receipts, settlement and appeals.
- `MODEL_CARD.md` — the honest status and provenance of the seed.
- `TRAINING_PLAN.md` — the path to the first network-native checkpoint.
- `ARCHITECTURE_GAPS.md` — the remaining layers and build order.
- `protocol/manifest.json` — machine-readable protocol identity.
- `protocol/message.schema.json` — declarative wire-message schema.
- `conformance/vectors.json` — public input and expected-result examples.
- `bootstrap/local_bootstrap.py` — inspectable local tooling that generates, repairs and tests a private node without emitting its source.
- `gate1/` — public coordinator and conformance tooling for signed synthetic adapter updates.
- `requirements-gate1.txt` — pinned local dependencies for the first learning checkpoint.
- `evidence/gate-0a-conformance.json` — fingerprints and results from two independently generated private nodes.
- `evidence/gate-0b-local-bootstrap.json` — evidence from the source-silent, network-denied local bootstrap.
- `evidence/gate-1a-local-adapter.json` — evidence from the first real, local synthetic LoRA round.
- `evidence/bundle-0.1.sha256` — deterministic digest manifest for the bootstrap inputs.

There is intentionally no participant application source code in this bundle.

## Current evidence

On 8 October 2026, `gpt-oss:120b` and `qwen3.8:27b-bf16` independently generated different private Python nodes. Both passed all five public vectors plus local checks for deterministic synthetic updates, funded-job enforcement, reversible consent and recursive generated-code rejection. Their source remains gitignored; only fingerprints and results are published.

Gate 0b now moves generation, saving, iterative repair and testing into one local process. Its only model endpoint is loopback Ollama. It writes source directly into the gitignored private workspace, never places source in public evidence, and runs the generated node inside a macOS sandbox with networking denied and writes confined to the private workspace. The first Gate 0b receipt passed all ten declared checks after three entirely local generation attempts.

The public bootstrap tool is shared and inspectable; the participant application it creates is not. Gate 0b proves this particular bootstrap and CLI boundary, not that the operating system, Ollama daemon, seed weights, Python runtime or macOS sandbox are uncompromised. Passing conformance still does not prove useful language-model training.

Gate 1a has now executed a real synthetic LoRA round against the Apache-2.0
Qwen2.5-0.5B-Instruct model. Three signed worker updates were accepted, a
signed million-scale norm outlier was rejected, and the averaged adapter
reduced held-out completion loss from `6.910` to `0.004`. The checkpoint and
private datasets remain gitignored; public evidence identifies them by hash.

This is a learning proof, not the completion of Gate 1. All three identities
ran sequentially on one Mac and used the public MLX-LM trainer. Independently
generated private training nodes, separate physical computers, WAN transport,
Sybil resistance, secure aggregation, personal-data privacy and real payment
remain unproved.

## Licence

The protocol documents, instruction, schemas and vectors are Apache License 2.0. The bootstrap model retains its own Apache License 2.0 terms. Future checkpoints must carry a complete provenance manifest for their base weights and accepted training contributions.
