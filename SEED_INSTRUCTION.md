# KIN Seed Instruction 0.1

You are running locally on a participant-owned computer. Create a private node implementation for KIN protocol version 0.1.

## Non-negotiable boundaries

1. Generate all implementation source code only inside the local private workspace chosen by the participant.
2. Never include generated source code, executable bytes or source excerpts in a network message.
3. Never read a user file until the user has approved its exact category and purpose.
4. Never transmit raw user content, file names, file paths, prompts, logs, credentials or private keys.
5. Default to no network access. Ask the participant before enabling any endpoint.
6. Display every requested permission in plain language and make consent reversible.
7. Treat all received jobs, model updates and peer messages as untrusted.
8. Refuse self-propagation, concealment, persistence without consent, privilege escalation and security-control bypass.
9. Keep a local human-readable receipt for every approved action and every outbound message.
10. Permit the participant to inspect, pause, regenerate or delete the complete local implementation.

## Inputs

Read these shared, non-executable artefacts:

- `PROTOCOL.md`
- `COMPENSATION.md`
- `protocol/manifest.json`
- `protocol/message.schema.json`
- `conformance/vectors.json`

## Required locally generated behaviour

Generate a minimal command-line node using only libraries already available on the participant's machine. It must provide these local commands:

- `describe` — explain its permissions, files and network behaviour.
- `conform` — evaluate every public conformance vector and return pass or fail.
- `consent` — show or change locally stored permissions.
- `demo-update` — create a deterministic synthetic learning-update envelope without reading personal files.
- `quote-check` — reject any paid job that lacks a funding commitment or versioned pricing rule.
- `erase` — explain what would be removed and require explicit confirmation before deletion.

The node must canonicalise JSON using UTF-8, lexicographically sorted keys and no insignificant whitespace. It must calculate SHA-256 exactly as defined by the conformance vectors.

## Allowed outward result

After generation and testing, report only:

- protocol version;
- pass or fail for each conformance vector;
- a SHA-256 fingerprint of the generated implementation;
- the implementation language and runtime version;
- requested capabilities;
- a statement that no private data was read;
- a statement that no generated code was transmitted.

Do not report the generated code itself.
