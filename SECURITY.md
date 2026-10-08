# Security Policy

KIN Seed 0 is experimental and must not be used with personal data, real payments or unattended network access.

Local-data experiments additionally require the interactive consent broker.
The broker must present the disclosure before content access and has no
unattended approval mode. This is an application-level gate, not proof of
informed consent against a compromised host. The first experiment is restricted
to already-public project documents; personal-data training remains disabled.

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

Gate 0b runs generated node commands under macOS `sandbox-exec` with networking denied and writes confined to the private workspace. It statically rejects declared high-risk imports and dynamic-execution primitives, and keeps generated source below the gitignored `.local/` boundary. The public evidence contains fingerprints and results rather than source. File reads are not yet restricted at the OS layer.

This does not protect against a compromised operating system, Ollama daemon, seed model, Python runtime or sandbox implementation. There is no production network, secure aggregation, real settlement or released KIN-native model checkpoint. Passing the included vectors is not a security certification.
