# Local-data learning gate

This gate tests whether a local model can learn from explicitly authorised
files without uploading their contents. It is deliberately narrow.

The participant invokes the interactive consent broker, which names each file
and presents the full disclosure **before any file content is opened**. The
participant must type `I CONSENT TO LOCAL TRAINING` in a terminal or the
loopback-only consent page. There is no
`--yes`, environment-variable or unattended approval path. The broker creates
a signed, purpose-specific receipt below `.local/`; the preparer refuses an
unsigned, expired, non-interactive or differently scoped receipt.

There is no directory crawling, mailbox access, photo-library access or hidden
discovery. The preparer accepts only UTF-8 Markdown and text, refuses symlinks
and out-of-repository paths, enforces byte and file-count ceilings, and rejects
obvious credentials. When `personal_data_allowed` is false it also rejects
email addresses and phone-number-like text.

Raw text, generated examples, validation material, local paths, consent IDs and
trained weights stay below `.local/`. Public evidence may contain only counts,
cryptographic commitments, aggregate metrics and limitations. A dataset
receipt specifically records that it contains neither raw text nor source
paths.

Consent can be withdrawn for future jobs. The participant can then delete the
derived local dataset and keys. Withdrawal cannot remove knowledge already
encoded into an accepted checkpoint; production personal-data training is
therefore still disabled until machine unlearning, checkpoint lineage,
revocation policy, leakage testing and legal review are substantially stronger.

The first proof uses only this repository's already-public KIN Markdown files.
That exercises local ingestion and training without touching personal files.

## Gate 1c native broker

`macos/` now builds a standalone native companion. The app uses the macOS file
picker, carries App Sandbox user-selected-file entitlements, keeps its Ed25519
identity in Keychain, and issues an expiring capability over numbered file
snapshots. Original names and paths are not included. The separate compiled
consumer accepts only a valid capability and runs with network access, writes
outside the job, and reads of user homes, volumes and temporary-data folders
denied by the operating system.

The UI supports exact files or one or multiple selected folders. Folder mode
recursively ingests compatible UTF-8 text and common image files only after
approval, and explicitly records that personal identifiers are permitted.
Images are analysed with macOS Vision inside Companion; only local OCR, broad
labels and face counts become text snapshots for this language-model adapter.
Raw images remain in their original location and are not copied into the
trainer job. This is not visual-model fine-tuning. Obvious credentials and
private keys remain forbidden in text and image-derived text.

Folder mode skips unreadable or credential-bearing files and continues with
the remaining safe corpus. Only aggregate exclusion counts and reason classes
enter the capability; excluded names and paths are not recorded. Exact-file
mode still rejects an unsafe file explicitly.

This closes the POC's earlier application-only file boundary. It does not make
personal-data training production-ready: the consumer sandbox uses deprecated
`sandbox-exec`, the local build is ad-hoc signed rather than Developer ID
signed and notarised, and no independent review has occurred. No real personal
data has been used in the published proof.

## Progressive local training

`local_data/progressive_training.py` trains cumulative adapters over increasing
fractions of one consented dataset while keeping a single hidden evaluation set
frozen. It creates a private HTML report containing the actual input, expected
passage and outputs from the base model and every round. Public summaries may
contain only dataset commitments, example counts and aggregate losses.
