# Rolling Frontier evaluator

Validate a frozen Genesis release record:

```sh
python3 frontier/evaluate_release.py path/to/release-result.json
```

The command prints the calculated quality and cost ratios. Exit status `0`
means the candidate satisfies the arithmetic thresholds and every declared hard
gate; exit status `1` means the record is valid but the candidate is not
qualified. A malformed or incomplete record produces a usage error.

`example-result.json` is synthetic format documentation. It is deliberately
labelled `example-only` and is not evidence that a Genesis model exists or has
passed the standard.

Run the evaluator tests with:

```sh
python3 -m unittest tests.test_frontier_standard -v
```

The evaluator checks arithmetic and mandatory fields. It cannot establish that
submitted scores, costs, dates or hard-gate claims are truthful. Official
qualification also requires signed raw evidence and independent reproduction.
