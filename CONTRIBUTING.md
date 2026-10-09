# Contributing to 80Twenty

80Twenty accepts contributions to Companion, Pulse, Accord, Genesis training
and evaluation code, schemas, conformance vectors, privacy tooling,
documentation and governance proposals. Anyone may open an issue, submit a
pull request or fork the project.

Submitting a pull request does not cause its code to run on participant
machines. Changes are reviewed, tested and included only in signed releases.
Machine-generated contributions are welcome only when the submitter has
reviewed them and accepts responsibility for their correctness, licence and
tests.

## Contribution requirements

- Do not include personal or confidential data.
- Do not include credentials, signing keys or payment addresses.
- Do not include participant data, private derived examples or local model state.
- State which protocol version the evidence concerns.
- Distinguish observed results from proposals.
- Include a reproducible synthetic test when changing protocol behaviour.
- Add or update tests for behavioural changes.
- Sign every commit with the Developer Certificate of Origin using
  `git commit -s`.
- Agree that contributions are licensed under Apache License 2.0.

## Protocol and release changes

An incompatible Accord change requires a public Accord Improvement Proposal,
a migration plan and conformance vectors. A Genesis release claim requires a
machine-readable Rolling Frontier result. Privacy boundaries may not be
weakened through an undocumented implementation change.

Maintainers may reject a change for correctness, security, privacy, legal,
scope or maintainability reasons. Decisions and material conflicts of interest
must be explained publicly. See `GOVERNANCE.md`.

Security vulnerabilities should follow `SECURITY.md` rather than a public issue.
