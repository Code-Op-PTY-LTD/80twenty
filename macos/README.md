# 80Twenty Companion for macOS

This is the first standalone participant safety broker. It is public and
reviewable because it is part of the trusted safety boundary; generated
participant training implementations remain private and are not published.

Build locally:

```sh
./macos/build_app.sh
```

The build creates two ignored local artifacts:

- `.local/dist/80Twenty Companion.app` — native visual consent and file-selection
  broker, ad-hoc signed with App Sandbox and user-selected-file entitlements.
- `.local/bin/kin-capability-consumer` — minimal compiled dataset consumer.

The participant can select exact Markdown or text files, or one or multiple
folders for recursive "everything compatible" ingestion, plus a private job
folder through macOS panels. They read the disclosure, check the acknowledgement
and type `I CONSENT TO LOCAL TRAINING`. Only then does the app enumerate chosen
folders or read content. It applies the selected scope's privacy rules,
snapshots each accepted file
under a numbered name, and signs a one-hour capability with an Ed25519 key held
in macOS Keychain. Original names and paths are not written to the capability.

Specific-file text mode rejects personal identifiers. Selecting an image, or
using everything-compatible mode, explicitly permits personal identifiers
after the stronger scope disclosure. Images are converted locally into OCR,
broad classification and face-count text; this is language-model training
about image contents, not visual fine-tuning. Obvious credentials and private
keys found in text derivatives are rejected. A high emergency
ceiling of 100,000 files or 10 GB prevents accidental disk exhaustion. Other
document and media formats are not yet supported and must not be implied by the
word "everything."

In folder mode, an unreadable file or one containing an obvious credential is
excluded without aborting the rest of the corpus. The capability records only
anonymous exclusion counts and reason categories, never excluded names or
paths. Exact-file mode still reports a rejection for the specifically selected
file.

Consume an approved job from the repository root:

```sh
.local/gate1-venv/bin/python -m local_data.run_sandboxed_capability \
  --job-dir '/path/chosen/by/participant/80Twenty-job-...'
```

The runner verifies the signature and commitments before starting the compiled
consumer under a macOS sandbox. Network access and writes outside the job are
denied. Reads from user homes, removable volumes and system temporary-data
folders are denied, with a narrow exception for the approved job and consumer
binary. This prevents the consumer from reopening the original files or
discovering other personal files.

`sandbox-exec` is deprecated and is used only as measurable POC enforcement.
A production build must place the generated trainer in a separately signed App
Sandbox helper or XPC service, use a Developer ID signature and notarisation,
and undergo independent security and privacy review.
