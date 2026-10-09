#!/usr/bin/env python3
"""Create a local-only HTML comparison without printing private examples."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
from pathlib import Path

import mlx.core as mx
from mlx_lm import generate, load


def _chat_prompt(tokenizer, prompt: str) -> str:
    return tokenizer.apply_chat_template(
        [{"role": "user", "content": prompt}],
        add_generation_prompt=True,
        tokenize=False,
    )


def _render_card(index: int, row: dict[str, str], base: str, adapter: str) -> str:
    fields = (
        ("Actual input", row["prompt"]),
        ("Base model output", base),
        ("Trained adapter output", adapter),
        ("Expected local passage", row["completion"]),
    )
    rendered = "".join(
        f"<section><h3>{html.escape(label)}</h3><pre>{html.escape(value)}</pre></section>"
        for label, value in fields
    )
    return f"<article><h2>Private test example {index + 1}</h2>{rendered}</article>"


def build_report(job_dir: Path, model_path: Path, *, examples: int = 3) -> dict[str, object]:
    job_dir = job_dir.resolve()
    test_path = job_dir / "derived" / "test.jsonl"
    if not test_path.is_file():
        # Gate 1b predates native capabilities and stored private derivatives
        # directly below its already-private job directory.
        test_path = job_dir / "test.jsonl"
    adapter_path = job_dir / "adapter"
    rows: list[dict[str, str]] = []
    with test_path.open() as handle:
        for line in handle:
            if line.strip():
                row = json.loads(line)
                if not isinstance(row.get("prompt"), str) or not isinstance(row.get("completion"), str):
                    raise ValueError("private test row is malformed")
                rows.append(row)
    if len(rows) < examples:
        raise ValueError("not enough private test examples")
    # Spread examples through the held-out set instead of cherry-picking output.
    indices = [round(i * (len(rows) - 1) / max(examples - 1, 1)) for i in range(examples)]

    base_model, tokenizer = load(str(model_path.resolve()))
    base_outputs = [
        generate(base_model, tokenizer, prompt=_chat_prompt(tokenizer, rows[index]["prompt"]), max_tokens=180)
        for index in indices
    ]
    del base_model
    mx.clear_cache()

    adapted_model, adapted_tokenizer = load(
        str(model_path.resolve()), adapter_path=str(adapter_path.resolve())
    )
    adapter_outputs = [
        generate(
            adapted_model,
            adapted_tokenizer,
            prompt=_chat_prompt(adapted_tokenizer, rows[index]["prompt"]),
            max_tokens=180,
        )
        for index in indices
    ]

    cards = "".join(
        _render_card(index, rows[index], base, adapted)
        for index, base, adapted in zip(indices, base_outputs, adapter_outputs)
    )
    document = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Private local model comparison</title>
<style>
:root {{ color-scheme: light dark; font-family: -apple-system, system-ui, sans-serif; }}
body {{ max-width: 1100px; margin: 0 auto; padding: 32px; background: #111418; color: #eef2f5; }}
h1 {{ margin-bottom: 8px; }} .notice {{ color: #aeb8c2; margin-bottom: 28px; }}
article {{ border: 1px solid #39424c; border-radius: 16px; padding: 22px; margin: 22px 0; background: #1b2026; }}
section {{ margin: 18px 0; }} h3 {{ color: #8fc7ff; margin-bottom: 8px; }}
pre {{ white-space: pre-wrap; overflow-wrap: anywhere; background: #101318; padding: 16px; border-radius: 10px; line-height: 1.45; }}
</style></head><body>
<h1>Private local model comparison</h1>
<p class="notice">Generated locally. This report contains consented private text and must not be published or committed.</p>
{cards}
</body></html>"""
    output = job_dir / "private-model-comparison.html"
    output.write_text(document)
    output.chmod(0o600)
    return {
        "examples": len(indices),
        "report_sha256": hashlib.sha256(document.encode()).hexdigest(),
        "private_text_printed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--job-dir", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--examples", type=int, default=3, choices=range(1, 6))
    args = parser.parse_args()
    print(json.dumps(build_report(args.job_dir, args.model, examples=args.examples), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
