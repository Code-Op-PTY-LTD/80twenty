# Historical fully local bootstrap

This directory preserves the original private-code-generation experiment. It
is no longer the target software distribution model: 80Twenty's reference
Companion, Pulse and Accord implementations are public and auditable.

`local_bootstrap.py` is public bootstrap tooling, not a participant node. Its job is to pass the public KIN bundle to an already installed local Ollama model and keep the generated participant implementation private.

The trust boundary is deliberately narrow:

1. The only model endpoint is `127.0.0.1`.
2. The model response is written directly to a mode-`0600` file below the gitignored `.local/` directory.
3. Candidate source and repair prompts are never printed or placed in public evidence.
4. Candidate commands run through the macOS sandbox with network access denied and writes confined to the private workspace.
5. The public evidence contains only the model name, protocol and bundle versions, checks, runtime and implementation fingerprint.

Run it from the repository root:

```console
python3 bootstrap/local_bootstrap.py \
  --model gpt-oss:120b \
  --bundle . \
  --private-dir .local/gate-0b \
  --evidence evidence/gate-0b-local-bootstrap.json
```

The command may ask the local model to repair a failed candidate. The previous source and failure reasons are sent only back to the same loopback Ollama service. A failed run keeps its diagnostic receipt under `.local/`; it does not publish source or failure output.

Re-run the external checks without sending anything to Ollama:

```console
python3 bootstrap/local_bootstrap.py \
  --model gpt-oss:120b \
  --bundle . \
  --private-dir .local/gate-0b \
  --evidence evidence/gate-0b-local-bootstrap.json \
  --verify-existing
```

## What this proves

A passing receipt proves that this bootstrap process did not emit generated source, the private implementation passed the declared CLI checks, and its test execution took place with network access denied.

It does not prove that the operating system, Ollama daemon, seed weights, Python runtime or macOS sandbox are uncompromised. Gate 0b does not yet restrict file reads at the OS layer; read scope is enforced by the generated-node contract and static audit. Stronger releases should add a dedicated local helper binary, signed reproducible builds, OS-specific read isolation and independent packet-capture verification.
