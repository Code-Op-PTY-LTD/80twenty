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

There is intentionally no participant application source code in this bundle.

## Current evidence

This bundle is intended to be given to the installed seed model. The model must generate a node locally, run the conformance vectors, and report only the results and implementation fingerprint. Passing conformance proves protocol compatibility; it does not prove privacy, security or useful language-model training.

## Licence

The protocol documents, instruction, schemas and vectors are Apache License 2.0. The bootstrap model retains its own Apache License 2.0 terms. Future checkpoints must carry a complete provenance manifest for their base weights and accepted training contributions.
