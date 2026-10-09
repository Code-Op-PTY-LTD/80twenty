# The 80Twenty Rolling Frontier Standard

## Claim

A specific Genesis release is `80/20-qualified` only when it achieves at least
80% of the contemporary frontier capability envelope at no more than 20% of
the frontier cost per successful task.

This is a release qualification, not a permanent property of the model or a
prediction about future competitors.

## Frontier snapshot

Each candidate declares an ISO 8601 snapshot cut-off. Reference models must be
generally available to independent evaluators by that cut-off through a stable
public API or downloadable release. The record identifies the provider, exact
model or weight version, access mode, evaluation date and pricing evidence.

A model released after the cut-off enters the next Genesis cycle. The cut-off
must be chosen before final evaluation and may not be moved to exclude an
unfavourable reference model.

For each evaluation category, the highest valid reference score forms that
category's frontier envelope. Genesis is therefore compared with the best
available reference for each kind of work, not a conveniently weak single
competitor.

## Capability

The initial mandatory categories are:

- reasoning;
- coding;
- factuality and knowledge;
- instruction following;
- representative real-user tasks.

Every category declares a positive weight and a score where higher is better.
The weights must be frozen before results are collected and sum to one. The
weighted Genesis score divided by the weighted frontier-envelope score must be
at least `0.80`. Every category must also achieve at least `0.70` of its own
frontier score so that a catastrophic weakness cannot be concealed by an
average.

Benchmark contamination checks, repeated trials and uncertainty intervals
belong in the release evidence. Safety and privacy tests are hard gates and do
not contribute bonus points to the capability average.

## Cost

Cost means total direct cost divided by successful evaluated tasks. Genesis
cost includes participant compensation, compute, energy where paid or
reimbursed, bandwidth, storage, orchestration, validation, retries, failed
work, fraud loss and payment fees. Reference cost includes actual billed usage
and any required supporting inference. Promotional credits and investor
subsidies do not reduce measured cost.

The Genesis cost per successful task divided by the cost of the reference
outputs that define the frontier envelope must be no greater than `0.20`.
Customer price may be reported separately and must not be substituted for
cost.

## Evidence and reproducibility

The release record and raw outputs are public. It contains the candidate weight
digest, Accord version, evaluator version, frozen task set digest, reference
versions and dates, scores, successes, costs, category weights and every hard
gate. Secret hold-outs may remain sealed until evaluation, but must be released
or independently escrowed after the run so the result can be audited.

`frontier/evaluate_release.py` is the normative arithmetic checker. Passing it
does not establish that the inputs are honest; independent reproduction and
signed evidence remain release requirements.
