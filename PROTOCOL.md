# KIN Protocol 0.1

## Purpose

KIN coordinates independently generated learning nodes. Nodes exchange declared messages and model contributions while their locally generated implementations and raw participant data remain private.

## Trust model

The network trusts neither code provenance nor participant claims. It evaluates observable behaviour:

- syntactically valid messages;
- ownership of a signing identity;
- consent-compatible capabilities;
- current checkpoint ancestry;
- bounded and finite update shape;
- hidden evaluation performance;
- redundant or challenged work where required;
- published validation and settlement receipts.

A valid signature proves control of a key, not honest behaviour.

## Bootstrap flow

1. The participant obtains an open-weight compatible seed model and this open specification bundle.
2. The participant reads and approves the seed instruction.
3. The model generates a private implementation locally.
4. The implementation runs the public conformance vectors without network access.
5. The participant reviews the requested capabilities.
6. Only after explicit approval may the node contact a selected gateway.
7. The gateway sees protocol messages and an implementation fingerprint, never the implementation source.

## Training flow

1. A checkpoint committee publishes a signed checkpoint manifest and training job.
2. A node checks the job against local consent and resource limits.
3. Approved local data is transformed and used locally.
4. The node emits a bounded update envelope containing an update digest and declared evidence, not raw examples.
5. Validators apply policy, anomaly, hidden-evaluation and challenge checks.
6. Accepted updates produce a proposed checkpoint.
7. A threshold of independent validators signs the canonical checkpoint.
8. Settlement follows the published job formula and produces participant receipts.

## Message rules

Every message must include:

- `protocol` equal to `kin/0.1`;
- a recognised `type`;
- a unique sender-controlled `node_id` or committee identity;
- the fields required by the declarative schema;
- a signature in live operation.

Messages are encoded as UTF-8 JSON. When hashing or signing, objects are serialised with keys sorted lexicographically and separators `,` and `:` with no additional whitespace.

## No-code-sharing invariant

Network messages must not contain generated source code, executable content, source archives, patch data or source excerpts. Implementations may differ completely. Compatibility is established through protocol behaviour and conformance results.

The seed instruction, protocol, schemas, vectors and model weights are shared artefacts. They are not the generated participant application.

## Privacy boundary

Protocol 0.1 permits only synthetic demonstration updates. Personal-data training remains disabled until secure aggregation, clipping, privacy accounting, leakage testing, consent receipts and independent review exist.

## Failure behaviour

- Stale work is rejected without penalty.
- Invalid messages are rejected with a machine-readable reason.
- One rejected node cannot block a training round.
- No update is paid merely because it consumed compute.
- A participant can withdraw from future work without surrendering prior receipts.

## What 0.1 does not solve

This version does not yet provide secure aggregation, production identity, Sybil resistance, decentralised checkpoint consensus, private-data training, real payment or general capability improvement. Gate 1a proves only a tiny synthetic transformer fine-tuning task on one machine; the remaining properties are explicit gates for later versions.
