# Path to the First KIN-Native Model

## Gate 0 Private implementation generation

Two different local seed models generate nodes independently from the same specification. Both pass the same conformance vectors without exchanging code.

Exit evidence: different implementation fingerprints, identical protocol results, no transmitted code.

## Gate 1 Synthetic distributed adapter round

**Status:** Gate 1a local learning proof passed on 8 October 2026. Three signed
LoRA updates on distinct synthetic shards were accepted, a signed norm outlier
was rejected, and the averaged adapter improved held-out loss from 6.910 to
0.004. This does not satisfy the full gate because the workers ran on one Mac
and were not independently generated participant implementations. See
`evidence/gate-1a-local-adapter.json`.

**Gate 1b local-data result:** eight already-public project documents were
approved through the visual consent broker before ingestion. A single private
adapter improved loss on 81 unseen prompt phrasings from 5.881 to 0.409. This
proves consent-scoped local adaptation, not personal-data readiness. See
`evidence/gate-1b-consented-local-data.json`.

Use a small Apache-2.0 open-weight language model that can be trained on available hardware. At least three independently generated nodes receive different synthetic instruction shards and return bounded adapter updates.

Exit evidence: signed updates, at least one rejected malicious update, improved hidden evaluation, hash-linked checkpoint receipt.

## Gate 2 Multi-machine round

Run nodes on separately administered physical computers. Replace shared process memory with content-addressed messages and public-key signatures.

Exit evidence: tolerance of dropout and stale work; no source-code exchange; packet capture confirming declared messages only.

## Gate 3 Secure aggregation and privacy accounting

Prevent the coordinator from seeing individual updates and introduce explicit clipping, group thresholds and measurable differential-privacy accounting.

Exit evidence: independent privacy review, reconstruction testing and published residual risks.

## Gate 4 Human pilot

Recruit a small adult cohort under explicit consent. Begin with curated participant-authored examples rather than unrestricted personal archives. Compensate participants at a fixed transparent rate.

Exit evidence: reconciled payments, consent withdrawal test, deletion test and participant comprehension study.

## Gate 5 KIN Seed 0 release

Publish the first network-native adapter or checkpoint only if it improves a declared evaluation suite without unacceptable privacy, safety or provenance failures.

Exit evidence: complete checkpoint provenance, reproducible evaluation, compatible local generation by multiple seed models, licence review and independent security report.

## Initial model choice

The 120-billion-parameter bootstrap model is suitable for generating robust local implementations but is unnecessarily large for the first distributed training experiment. Gate 1 should use a much smaller Apache-2.0 model so that ordinary laptops can produce adapter updates. The base must be selected by measured memory, training time, licence and code-generation quality rather than prestige.
