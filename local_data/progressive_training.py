#!/usr/bin/env python3
"""Run cumulative local MLX training rounds and render private before/after outputs."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


LOSS_PATTERN = re.compile(r"Test loss\s+([0-9.]+)")


def _jsonl(path: Path) -> list[dict[str, str]]:
    rows = []
    with path.open() as handle:
        for line in handle:
            if line.strip():
                row = json.loads(line)
                if not isinstance(row.get("prompt"), str) or not isinstance(row.get("completion"), str):
                    raise ValueError(f"malformed private dataset row in {path.name}")
                rows.append(row)
    return rows


def _write_jsonl(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows))
    path.chmod(0o600)


def _dataset_dir(job_dir: Path) -> Path:
    derived = job_dir / "derived"
    return derived if (derived / "train.jsonl").is_file() else job_dir


def prepare_rounds(job_dir: Path, workspace: Path, fractions: tuple[float, ...]) -> dict[str, Any]:
    source = _dataset_dir(job_dir.resolve())
    train = _jsonl(source / "train.jsonl")
    test = _jsonl(source / "test.jsonl")
    if len(train) < 8 or len(test) < 3:
        raise ValueError("progressive training requires at least 8 training and 3 hidden examples")
    if not fractions or tuple(sorted(set(fractions))) != fractions or fractions[-1] != 1.0:
        raise ValueError("round fractions must be unique, increasing and end at 1.0")
    if fractions[0] <= 0 or fractions[-1] > 1:
        raise ValueError("round fractions must be in (0, 1]")

    workspace.mkdir(parents=True, exist_ok=True)
    workspace.chmod(0o700)
    rounds = []
    for index, fraction in enumerate(fractions, start=1):
        count = max(8, round(len(train) * fraction))
        selected = train[:count]
        directory = workspace / f"round-{index:02d}"
        _write_jsonl(directory / "data" / "train.jsonl", selected)
        _write_jsonl(directory / "data" / "valid.jsonl", selected[: max(4, min(len(selected) // 10, 24))])
        _write_jsonl(directory / "data" / "test.jsonl", test)
        rounds.append({"round": index, "fraction": fraction, "train_examples": len(selected), "directory": directory})

    source_hash = hashlib.sha256(
        (source / "train.jsonl").read_bytes() + (source / "test.jsonl").read_bytes()
    ).hexdigest()
    return {"source_dataset_sha256": source_hash, "hidden_examples": len(test), "rounds": rounds}


def _run(command: list[str], log_path: Path) -> str:
    environment = os.environ.copy()
    environment.update({"HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"})
    result = subprocess.run(command, text=True, capture_output=True, env=environment, check=False)
    output = result.stdout + result.stderr
    log_path.write_text(output)
    log_path.chmod(0o600)
    if result.returncode != 0:
        raise RuntimeError(f"local MLX command failed; private log: {log_path}")
    return output


def _generate_outputs(model_path: Path, adapter: Path | None, rows: list[dict[str, str]], indices: list[int]) -> list[str]:
    import mlx.core as mx
    from mlx_lm import generate, load

    kwargs = {} if adapter is None else {"adapter_path": str(adapter)}
    model, tokenizer = load(str(model_path), **kwargs)
    outputs = []
    for index in indices:
        prompt = tokenizer.apply_chat_template(
            [{"role": "user", "content": rows[index]["prompt"]}],
            add_generation_prompt=True,
            tokenize=False,
        )
        outputs.append(generate(model, tokenizer, prompt=prompt, max_tokens=180))
    del model
    mx.clear_cache()
    return outputs


def _report(workspace: Path, test: list[dict[str, str]], stages: list[dict[str, Any]], outputs: list[list[str]]) -> Path:
    example_count = min(5, len(test))
    indices = [round(i * (len(test) - 1) / max(example_count - 1, 1)) for i in range(example_count)]
    headers = "".join(f"<th>{html.escape(stage['label'])}</th>" for stage in stages)
    rows_html = []
    for position, index in enumerate(indices):
        cells = "".join(f"<td><pre>{html.escape(stage_outputs[position])}</pre></td>" for stage_outputs in outputs)
        rows_html.append(
            "<tr>"
            f"<td><pre>{html.escape(test[index]['prompt'])}</pre></td>"
            f"<td><pre>{html.escape(test[index]['completion'])}</pre></td>"
            f"{cells}</tr>"
        )
    metrics = "".join(
        f"<li><strong>{html.escape(stage['label'])}</strong>: "
        f"{stage.get('train_examples', 0)} training examples, test loss {stage['test_loss']:.3f}</li>"
        for stage in stages
    )
    document = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width"><title>80Twenty local learning progression</title>
<style>
:root {{ color-scheme: dark; font-family: -apple-system, system-ui, sans-serif; }}
body {{ margin: 0; padding: 28px; background: #0d1117; color: #e6edf3; }}
.notice {{ color: #a9b5c2; }} table {{ border-collapse: collapse; min-width: 1300px; }}
th, td {{ border: 1px solid #30363d; padding: 12px; vertical-align: top; }}
th {{ position: sticky; top: 0; background: #161b22; color: #79c0ff; }}
pre {{ white-space: pre-wrap; width: 280px; font-family: ui-monospace, monospace; }}
.scroll {{ overflow-x: auto; }} li {{ margin: 8px 0; }}
</style></head><body><h1>80Twenty local learning progression</h1>
<p class="notice">Generated locally from consented material. This private report contains actual prompts, expected passages and model outputs. Do not publish it.</p>
<h2>Measured progression</h2><ul>{metrics}</ul><div class="scroll"><table>
<thead><tr><th>Actual input</th><th>Expected local passage</th>{headers}</tr></thead>
<tbody>{''.join(rows_html)}</tbody></table></div></body></html>"""
    path = workspace / "progression.html"
    path.write_text(document)
    path.chmod(0o600)
    return path


def train(job_dir: Path, model_path: Path, workspace: Path, fractions: tuple[float, ...], iters: int) -> dict[str, Any]:
    prepared = prepare_rounds(job_dir, workspace, fractions)
    executable = str(Path(sys.executable).with_name("mlx_lm.lora"))
    stages: list[dict[str, Any]] = []

    base_log = _run([
        executable, "--model", str(model_path), "--data", str(prepared["rounds"][-1]["directory"] / "data"),
        "--test", "--test-batches", "-1", "--adapter-path", "",
    ], workspace / "base-evaluation.log")
    base_match = LOSS_PATTERN.search(base_log)
    if not base_match:
        raise RuntimeError("base evaluation did not report a test loss")
    stages.append({"label": "Base model", "train_examples": 0, "test_loss": float(base_match.group(1)), "adapter": None})

    previous: Path | None = None
    for item in prepared["rounds"]:
        adapter_dir = item["directory"] / "adapter"
        command = [
            executable, "--model", str(model_path), "--data", str(item["directory"] / "data"),
            "--train", "--mask-prompt", "--fine-tune-type", "lora", "--num-layers", "8",
            "--batch-size", "1", "--iters", str(iters), "--learning-rate", "1e-5",
            "--steps-per-report", str(max(1, iters // 2)), "--steps-per-eval", str(iters),
            "--save-every", str(iters), "--max-seq-length", "512", "--adapter-path", str(adapter_dir),
        ]
        if previous is not None:
            command.extend(["--resume-adapter-file", str(previous)])
        _run(command, item["directory"] / "training.log")
        adapter = adapter_dir / "adapters.safetensors"
        evaluation = _run([
            executable, "--model", str(model_path), "--data", str(item["directory"] / "data"),
            "--adapter-path", str(adapter_dir), "--test", "--test-batches", "-1",
        ], item["directory"] / "evaluation.log")
        match = LOSS_PATTERN.search(evaluation)
        if not match or not adapter.is_file():
            raise RuntimeError(f"round {item['round']} did not produce measurable adapter evidence")
        stages.append({
            "label": f"Round {item['round']} ({int(item['fraction'] * 100)}% corpus)",
            "train_examples": item["train_examples"], "test_loss": float(match.group(1)), "adapter": adapter_dir,
        })
        previous = adapter

    test = _jsonl(prepared["rounds"][-1]["directory"] / "data" / "test.jsonl")
    example_count = min(5, len(test))
    indices = [round(i * (len(test) - 1) / max(example_count - 1, 1)) for i in range(example_count)]
    outputs = [_generate_outputs(model_path, stage["adapter"], test, indices) for stage in stages]
    report = _report(workspace, test, stages, outputs)

    public_summary = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_dataset_sha256": prepared["source_dataset_sha256"],
        "rounds": [
            {"label": stage["label"], "train_examples": stage["train_examples"], "test_loss": stage["test_loss"]}
            for stage in stages
        ],
        "private_report_sha256": hashlib.sha256(report.read_bytes()).hexdigest(),
        "raw_text_in_summary": False,
        "network_used": False,
    }
    (workspace / "progression-summary.json").write_text(json.dumps(public_summary, indent=2, sort_keys=True) + "\n")
    return {"report": str(report), **public_summary}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--job-dir", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--fractions", default="0.25,0.5,1.0")
    parser.add_argument("--iters", type=int, default=20)
    args = parser.parse_args()
    fractions = tuple(float(value) for value in args.fractions.split(","))
    result = train(args.job_dir.resolve(), args.model.resolve(), args.workspace.resolve(), fractions, args.iters)
    print(json.dumps({key: value for key, value in result.items() if key != "report"} | {"report_created": True}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
