# Local-data learning gate

This gate tests whether a local model can learn from explicitly authorised
files without uploading their contents. It is deliberately narrow.

The participant invokes the interactive consent broker, which names each file
and presents the full disclosure **before any file content is opened**. The
participant must type `I CONSENT TO LOCAL TRAINING` at a TTY. There is no
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
