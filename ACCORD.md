# Accord Protocol 0.2 Draft

Accord is 80Twenty's open protocol and shared specification. This draft is the
successor to the immutable KIN 0.1 proof bundle in `PROTOCOL.md`. Existing
signed evidence keeps its historical `kin/0.1` identifier; new incompatible
wire messages will use `accord/0.2` after conformance vectors and migration
tests exist.

## Open implementation

Companion, Pulse, training code, evaluation code, schemas and conformance tools
are developed as open source. Participants may use signed reference builds or
independent Accord-compatible implementations. Software source is exchanged
through the public repository, never embedded in training jobs or model-update
messages.

A pull request never authorises code to run on participant machines. Only a
reviewed, reproducible and signed release may be offered as an official build,
and installation or upgrade remains an explicit participant action.

## Local-data boundary

Before reading prospective training content, Companion must display the exact
purpose, selected roots or files, inclusion and exclusion rules, derivatives,
network outputs, resource limits, compensation, expiry and withdrawal limits.
Silence, installation, prior participation, continued use and unattended
configuration are not consent.

Pulse may read only content covered by a current capability. Raw content,
excerpts, filenames, paths, embeddings, prompts, logs and per-participant
updates must not become network messages. Keeping raw data local is not by
itself sufficient: personal-data training additionally requires update
clipping, secure aggregation with a minimum cohort, measurable differential
privacy, memorisation and reconstruction testing, and an on-device audit of
every byte authorised to cross the network.

## Training and validation

Jobs identify their parent Genesis checkpoint, objective, accepted data class,
privacy parameters, resource ceiling, validation method and compensation
formula. Pulse works asynchronously, supports cancellation and durable local
recovery, and may be configured to run only while the device is idle.

Validators reject malformed, stale, replayed, non-finite, unbounded or
privacy-incompatible updates. Useful-work verification may combine hidden
evaluations, duplicate assignments, replay challenges, delayed rewards and
reputation, but a signature proves only control of a key.

## Release qualification

A Genesis release may use the `80/20-qualified` label only when an immutable
public result record passes `frontier/evaluate_release.py` under
`FRONTIER_STANDARD.md`. Experimental releases may be published without the
label but must not imply that they passed.

## Work still required before freezing Accord 0.2

- define the complete message schema and migration from `kin/0.1`;
- implement secure aggregation and privacy accounting;
- define decentralised checkpoint finality and recovery from partitions;
- connect funded work receipts to lawful fiat settlement;
- add public Accord Improvement Proposal templates and conformance vectors;
- complete independent privacy, security and licensing review.
