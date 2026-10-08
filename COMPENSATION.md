# KIN Compensation Protocol 0.1

## Purpose

KIN compensates people for verified work that operates or improves the collective model. It does not pay merely for possessing data, being online or recruiting additional participants.

The network issues no project token or memecoin. Compensation is denominated in ordinary currency and may be settled through compliant fiat providers or direct non-custodial Bitcoin infrastructure where lawful and practical.

## Principles

1. A participant sees the pricing rule and maximum expected payout before accepting a job.
2. A funded commitment exists before work begins.
3. Payment depends on published, versioned acceptance criteria.
4. Compute wealth does not purchase governance power.
5. The network does not buy ownership of a participant's raw files.
6. Every decision produces a signed receipt that can be independently reconciled.
7. Rejected work includes a reason and an appeal route.
8. Early human pilots use simple fixed rates before attempting complex contribution valuation.

## Roles

| Role | Responsibility |
| --- | --- |
| Job sponsor | Defines the objective, price ceiling and acceptance policy; commits funds before assignment |
| Participant node | Accepts an authorised job, performs bounded local work and returns declared evidence |
| Validator committee | Evaluates protocol compliance and useful contribution without receiving raw participant files |
| Settlement provider | Delivers fiat or Bitcoin value and produces a settlement reference |
| Auditor | Reconciles job commitments, validation decisions and participant receipts |

No role is trusted alone. A settlement must link a funded quote, accepted work receipt and threshold validation decision.

## Payment components

Version 0.1 recognises four independently quoted components:

- **Availability fee** — optional fixed compensation for accepting a scheduled experiment, paid only under clearly stated conditions.
- **Compute reimbursement** — a bounded amount based on the declared job class, not unrestricted metering supplied by the participant.
- **Useful-contribution payment** — a bonus for measurable improvement against hidden or counterfactual evaluation.
- **Validation payment** — compensation for correctly evaluating assigned work, scored against committee outcomes and hidden challenges.

The first human pilot should use fixed participation and validation amounts. Marginal-contribution pricing is a research problem and must not be presented as solved.

## Job quote

Before a node accepts work, it receives a signed `price_quote` containing:

- job identifier and checkpoint;
- pricing-policy version;
- denomination and settlement rail;
- funded maximum payout;
- fixed and variable components;
- acceptance and rejection rules;
- expected resource ceiling;
- validation deadline;
- settlement deadline;
- appeal window;
- sponsor and settlement-provider identities.

The node records the quote locally. It may reject the job without penalty.

## Contribution receipt

A submitted update produces a `work_receipt` containing only protocol metadata:

- job, node and base-checkpoint identifiers;
- update digest and declared sample count;
- resource-class declaration;
- consent-policy digest;
- pricing-policy version;
- submission time and participant signature.

It must not contain generated code, raw training examples, file paths or personal content.

## Validation and payout

Validators sign an acceptance decision and the measured band of useful contribution. The payout engine applies the quoted formula without retroactively changing rates.

A settlement receipt links:

`price quote -> work receipt -> validation decision -> settlement reference`

The participant can verify the complete chain locally. Public audit records may use blinded participant identifiers and commitments rather than payment addresses.

## Settlement rails

### Human pilot

Use fixed fiat payments through a regional provider. Record the amount, currency and provider reference. This is the simplest way to test comprehension, reconciliation and disputes.

### Non-custodial Bitcoin option

Where permitted, a sponsor may pay directly to a participant-controlled address or Lightning invoice. The protocol should avoid holding participant balances or private keys. Tiny amounts may be batched, but any design that accumulates balances for others requires jurisdiction-specific custody and financial-services review.

### Test environment

Before real value, use a local Bitcoin regtest network or public test network. Test receipts and simulated values must be visibly labelled as having no monetary value.

## Contribution valuation

The long-term formula may combine:

- successful completion of an accepted job;
- estimated bounded resource cost;
- improvement on hidden evaluations;
- rarity of the improved capability;
- agreement with independent validators;
- resistance to duplicate or copied contributions;
- delayed evidence that the contribution remains useful.

No single evaluator may determine a participant's variable payout. High-value decisions require redundant evaluation and delayed finality.

## Fraud and appeals

- Duplicate updates are paid at most once.
- Correlated identities, copied work and validator collusion trigger delayed settlement, not automatic confiscation.
- Participant earning caps limit server-farm capture during early phases.
- Validators receive hidden challenge tasks and cannot select only friendly updates.
- A rejected participant receives a machine-readable reason and can request independent re-evaluation.
- Changes to fraud controls and pricing categories are published, while exact detection thresholds may remain confidential.

KIN does not require participants to stake money. A mistaken rejection should not destroy a family's savings.

## Tax and identity boundary

The protocol can use pseudonymous node identifiers, but a regulated payout provider may require legal identity. Identity records should remain with the provider or a specialised credential issuer rather than being placed in the public checkpoint ledger.

Each receipt records the settlement-time local-currency value when available. Participants remain responsible for their own tax obligations, and regional operators must obtain local legal advice before paying real value.

## Governance boundary

Compensation and governance are deliberately separate:

- payment amount does not increase voting weight;
- owning more computers does not create more governance identities;
- purchasing a token cannot buy protocol control;
- contributor councils use non-transferable human credentials;
- commercial sponsors may fund work but cannot rewrite privacy commitments unilaterally.

## Release gates

Real compensation remains disabled until all of the following exist:

1. signed and funded job quotes;
2. reproducible validation decisions;
3. participant-verifiable receipt chains;
4. duplicate and collusion controls;
5. an appeal process;
6. reconciled test settlements;
7. jurisdiction-specific legal, tax and financial-services review;
8. plain-language participant disclosure.
