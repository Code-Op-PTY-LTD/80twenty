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
2. Before reading file content, a local consent broker shows the person the exact scope, purpose, processing, outputs, network behaviour, compensation and withdrawal limits.
3. The person explicitly opts in through an interactive prompt; silence, installation, prior participation and continued use are never consent.
4. The broker records a signed, purpose-specific, expiring local consent receipt.
5. A node checks the job against that receipt and local resource limits.
6. Approved local data is transformed and used locally.
7. The node emits a bounded update envelope containing an update digest and declared evidence, not raw examples.
8. Validators apply policy, anomaly, hidden-evaluation and challenge checks.
9. Accepted updates produce a proposed checkpoint.
10. A threshold of independent validators signs the canonical checkpoint.
11. Settlement follows the published job formula and produces participant receipts.

## Mandatory interactive opt-in

A local node MUST NOT read any prospective training-file content until the
participant has seen a plain-language disclosure and actively approved it. The
prompt must identify the purpose and exact files or narrowly defined source,
what derivatives and weights will be created, what may leave the device,
resource ceilings, compensation, material privacy risks, expiry and the limits
of withdrawal after training.

Approval requires an affirmative interaction with the participant at the time
of the request. Nodes must not implement `--yes`, environment-variable,
configuration-file, API-default or timeout-based approval. A declined,
missing, expired, differently scoped or unverifiable receipt is a hard stop.
Consent for one purpose, job, data scope or model is not consent for another.

The detailed local receipt can contain paths but must remain private. Any wire
receipt contains only policy and scope commitments, timestamps and the
participant signature; it must never expose paths or content. Revocation stops
future jobs and authorises deletion of local derivatives, but the disclosure
must state that it cannot reliably untrain an already accepted checkpoint.

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

Protocol 0.1 permits synthetic updates and consented experiments on already-public local documents. Personal-data training remains disabled until secure aggregation, clipping, privacy accounting, leakage testing, independently enforced consent receipts and independent review exist.

## Failure behaviour

- Stale work is rejected without penalty.
- Invalid messages are rejected with a machine-readable reason.
- One rejected node cannot block a training round.
- No update is paid merely because it consumed compute.
- A participant can withdraw from future work without surrendering prior receipts.

## What 0.1 does not solve

This version does not yet provide secure aggregation, production identity, Sybil resistance, decentralised checkpoint consensus, private-data training, real payment or general capability improvement. Gate 1a proves only a tiny synthetic transformer fine-tuning task on one machine; the remaining properties are explicit gates for later versions.
