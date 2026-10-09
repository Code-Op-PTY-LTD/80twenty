# 80Twenty

80Twenty is an open network intended to produce useful shared intelligence from
participant-owned compute and explicitly authorised local data. Its target is
measurable: a qualified Genesis release must deliver at least 80% of the
contemporary frontier capability envelope at no more than 20% of the frontier
cost per successful task.

The project names are:

- **80Twenty** — the network and project;
- **Companion** — the participant-facing desktop application;
- **Accord** — the protocol and shared specification;
- **Genesis** — the model family;
- **Pulse** — the asynchronous background service.

The protocol, reference applications, training and evaluation code are open
source. Anyone may inspect, fork and propose changes to them. Raw participant
data remains local, and neither source files nor identifying paths become
network messages. Open source software and private participant data are
separate requirements; one must never be used as an excuse to weaken the
other.

This repository began as the KIN Seed 0 proof. Existing evidence and code use
the historical `kin/0.1` wire identifier and retain that identifier so their
hashes and claims remain reproducible. The next incompatible wire revision will
be `accord/0.2`; historical evidence will not be rewritten or relabelled.

## What is being created

The project has three distinct milestones:

1. **Historical genesis profile** — an existing Apache-2.0 open-weight model
   interpreted a seed instruction and generated private experimental nodes.
2. **Open reference implementation** — Companion, Pulse, Accord conformance,
   training and evaluation software developed through public review.
3. **Genesis checkpoint** — the first model checkpoint produced from accepted
   distributed learning updates. It is not yet claimed.

The genesis profile is implemented here. The native trained checkpoint is not yet claimed.

## What participants share

- The model weights and their licence.
- The natural-language seed instruction.
- The protocol manifest and message schemas.
- Public conformance examples and expected behavioural results.
- Signed model updates, validation decisions and checkpoint hashes.
- The reference implementation, build instructions and conformance tests.
- Training, evaluation and privacy-accounting code.
- Genesis weights and sufficient provenance information for permitted releases.

## What participants do not share

- Raw emails, documents, photographs or other private files.
- Local file paths, prompts, logs or environment details unless explicitly authorised.
- Private signing keys.
- Training excerpts, embeddings or individual updates that could expose a participant.

## Why Accord remains technology agnostic

A participant may use the published reference client or an independently
implemented client in any language or operating system. A node is accepted
because its externally visible messages satisfy Accord and its release is
authorised by the participant. Alternative implementations may be published
and reviewed normally. Source code is never carried inside training protocol
messages.

## Contents

- `SEED_INSTRUCTION.md` — the instruction supplied to a compatible local model.
- `PROTOCOL.md` — behaviour, message flow and security boundaries.
- `ACCORD.md` — the open-source Accord 0.2 successor draft.
- `COMPENSATION.md` — funded jobs, contribution receipts, settlement and appeals.
- `MODEL_CARD.md` — the honest status and provenance of the seed.
- `TRAINING_PLAN.md` — the path to the first network-native checkpoint.
- `FRONTIER_STANDARD.md` — the Rolling Frontier Standard and 80/20 release claim.
- `GOVERNANCE.md` — open development and protocol-change rules.
- `ARCHITECTURE_GAPS.md` — the remaining layers and build order.
- `protocol/manifest.json` — machine-readable protocol identity.
- `protocol/message.schema.json` — declarative wire-message schema.
- `conformance/vectors.json` — public input and expected-result examples.
- `bootstrap/local_bootstrap.py` — the preserved historical private-generation experiment.
- `frontier/` — executable validation of a Genesis release qualification record.
- `gate1/` — public coordinator and conformance tooling for signed synthetic adapter updates.
- `local_data/` — visual consent broker, private dataset preparer and standalone-client architecture.
- `macos/` — 80Twenty Companion, native App Sandbox consent broker, local image derivation and compiled capability consumer.
- `requirements-gate1.txt` — pinned local dependencies for the first learning checkpoint.
- `evidence/gate-0a-conformance.json` — fingerprints and results from two independently generated private nodes.
- `evidence/gate-0b-local-bootstrap.json` — evidence from the source-silent, network-denied local bootstrap.
- `evidence/gate-1a-local-adapter.json` — evidence from the first real, local synthetic LoRA round.
- `evidence/gate-1b-consented-local-data.json` — evidence from visually consented local-document training.
- `evidence/gate-1c-native-broker.json` — evidence from native file brokering and OS read isolation.
- `evidence/gate-1d-progressive-local-training.json` — cumulative corpus fractions, frozen-set losses and private-report commitment.
- `evidence/bundle-0.1.sha256` — deterministic digest manifest for the bootstrap inputs.

Companion and Pulse source belong in the public repository. Private data,
derived training examples, secrets and local job state do not.

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

Gate 1b then tested the local-data boundary using eight visually consented,
already-public KIN documents. The participant approved through a loopback-only
visual prompt before preparation read file contents. A private adapter reduced
loss across 81 hidden prompt phrasings from `5.881` to `0.409`. Raw text,
derived examples, paths and weights remain gitignored; only commitments and
aggregate metrics are public. This proves local adaptation and recall, not
personal-data safety or broad reasoning improvement.

Gate 1c replaces the browser-only interaction proof with a standalone native
macOS companion. The user selects exact files through the operating-system
picker, or one or multiple folders for recursive ingestion of every compatible
text file; only after typed consent does the app enumerate folders and create
numbered snapshots plus a Keychain-signed, one-hour capability. The broader
folder mode explicitly permits personal identifiers, while obvious credentials
and private keys remain forbidden. A compiled consumer runs with network and
unapproved personal-file reads denied. A valid synthetic capability completed
preparation, tampering failed closed, and an attempted read of an unrelated
file was denied. The app is ad-hoc signed and the consumer uses deprecated
`sandbox-exec`; no real personal data has been used, and this is not yet a
production personal-data boundary.

A later local run added a cumulative training view over the same already-public
consented corpus. Against one frozen hidden set, test loss moved from `5.640`
for the base model to `4.992`, `4.813` and `4.771` as the available corpus grew
from 25% to 50% to 100%. A private HTML report shows actual inputs and outputs.
This demonstrates incremental local knowledge learning, not frontier quality.

Companion also accepts common images under an explicit personal-data scope.
macOS Vision locally derives OCR text, broad labels and face counts; the raw
image is not copied into the trainer job. The current text model can learn from
those derivatives, but this is deliberately not described as visual-model
training.

## Licence

The repository is Apache License 2.0. Contributions use Developer Certificate
of Origin sign-off rather than a copyright-assignment CLA. Base models and
future checkpoints retain their declared compatible terms and must carry a
complete provenance manifest.
