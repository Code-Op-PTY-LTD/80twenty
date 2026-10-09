# Security Policy

KIN Seed 0 is experimental and must not be used for production personal-data
training, real payments or unattended network access. Gate 1c exposes an
explicit local-only personal-data opt-in for controlled testing.

Local-data experiments additionally require the interactive consent broker.
The broker must present the disclosure before content access and has no
unattended approval mode. This is an application-level gate, not proof of
informed consent against a compromised host. The first experiments are
restricted to already-public project documents or synthetic fixtures. No real
personal data has been used in published evidence.

## Report privately

Do not publish exploit details that could expose participant files, signing keys, model checkpoints or payment credentials. Until a dedicated reporting address exists, repository maintainers should enable GitHub private vulnerability reporting before inviting external testing.

## In scope

- Generated code escaping its declared sandbox.
- Undeclared file or network access.
- Generated code or raw-data leakage in protocol messages.
- Signature, replay or checkpoint-ancestry failures.
- Malicious-update acceptance.
- Receipt forgery or payment redirection.
- Conformance-vector ambiguity that permits incompatible behaviour.

## Current limitations

Gate 0b runs generated node commands under macOS `sandbox-exec` with networking denied and writes confined to the private workspace. It statically rejects declared high-risk imports and dynamic-execution primitives, and keeps generated source below the gitignored `.local/` boundary. The public evidence contains fingerprints and results rather than source.

Gate 1c adds a native App Sandbox consent broker, a Keychain signing identity,
signed expiring capabilities and a compiled consumer whose macOS sandbox denies
networking, writes outside its job, and reads from user homes, removable
volumes and temporary-data folders. Snapshot tampering and an attempted
unapproved read are tested. Participants may choose exact files or one or
multiple folders; recursive folder ingestion has only a high emergency ceiling
of 100,000 compatible text files or 10 GB. Personal identifiers require that
broader scope. In folder mode, files containing obvious credentials or private
keys are excluded with anonymous reason counts while the safe corpus continues;
exact-file mode fails visibly on that file.

The local app is ad-hoc signed and the consumer
still uses deprecated `sandbox-exec`; this is POC enforcement, not a security
certification or a production personal-data boundary.

This does not protect against a compromised operating system, Ollama daemon, seed model, Python runtime or sandbox implementation. There is no production network, secure aggregation, real settlement or released KIN-native model checkpoint. Passing the included vectors is not a security certification.
