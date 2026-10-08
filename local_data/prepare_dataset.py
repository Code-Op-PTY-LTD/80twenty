#!/usr/bin/env python3
"""Prepare a private MLX-LM dataset from explicitly authorised text files.

The tool deliberately supports a narrow first gate: UTF-8 Markdown and text
files named one-by-one in a consent record. It never crawls directories and
never prints source text, prompts, answers or local paths.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from local_data.consent_broker import verify_record


PRIVATE_KEY = re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")
AWS_KEY = re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")
SECRET_ASSIGNMENT = re.compile(
    r"(?i)\b(?:api[_-]?key|access[_-]?token|password|passwd|secret)\s*[:=]\s*[^\s]{6,}"
)
EMAIL = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
PHONE = re.compile(r"(?<!\w)(?:\+?\d[\d ()-]{7,}\d)(?!\w)")
HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


class PreparationError(RuntimeError):
    pass


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def ensure_private_path(root: Path, path: Path) -> Path:
    resolved = path.resolve()
    private_root = (root / ".local").resolve()
    if resolved != private_root and private_root not in resolved.parents:
        raise PreparationError("derived data must remain below the repository .local directory")
    return resolved


def scan_text(text: str, personal_data_allowed: bool) -> list[str]:
    failures: list[str] = []
    for label, pattern in (
        ("private_key", PRIVATE_KEY),
        ("cloud_access_key", AWS_KEY),
        ("secret_assignment", SECRET_ASSIGNMENT),
    ):
        if pattern.search(text):
            failures.append(label)
    if not personal_data_allowed:
        if EMAIL.search(text):
            failures.append("email_address")
        if PHONE.search(text):
            failures.append("phone_number_like_text")
    return failures


def markdown_sections(text: str) -> list[tuple[str, str]]:
    sections: list[tuple[str, str]] = []
    heading = "Document introduction"
    paragraph: list[str] = []
    fenced = False

    def flush() -> None:
        nonlocal paragraph
        value = " ".join(line.strip() for line in paragraph if line.strip())
        value = re.sub(r"\s+", " ", value).strip()
        if 40 <= len(value) <= 700:
            sections.append((heading, value))
        paragraph = []

    for line in text.splitlines():
        if line.strip().startswith("```"):
            flush()
            fenced = not fenced
            continue
        if fenced:
            continue
        match = HEADING.match(line)
        if match:
            flush()
            heading = match.group(2).strip()
            continue
        if not line.strip():
            flush()
            continue
        if line.lstrip().startswith(("|", "- ", "* ", ">")):
            flush()
            continue
        paragraph.append(line)
    flush()
    return sections


def dataset_rows(sections: list[tuple[str, str]]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    train: list[dict[str, str]] = []
    hidden: list[dict[str, str]] = []
    for index, (heading, answer) in enumerate(sections):
        label = f"local-section-{index:03d}"
        train.extend((
            {
                "prompt": f"In the authorised local knowledge set, reproduce {label} titled '{heading}'.",
                "completion": answer,
            },
            {
                "prompt": f"Recall the exact local note {label}, whose heading is '{heading}'.",
                "completion": answer,
            },
        ))
        hidden.append({
            "prompt": f"From the consented local corpus, provide the content of {label} under '{heading}'.",
            "completion": answer,
        })
    return train, hidden


def write_jsonl(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows))


def prepare(root: Path, consent_path: Path) -> dict[str, Any]:
    root = root.resolve()
    consent_path = ensure_private_path(root, consent_path)
    record = json.loads(consent_path.read_text())
    try:
        consent = verify_record(record)
    except ValueError as exc:
        raise PreparationError(str(exc)) from exc
    required = {"consent_id", "purpose", "granted", "files", "output_dir"}
    if not required.issubset(consent):
        raise PreparationError("consent record is missing required fields")
    if consent["granted"] is not True or consent.get("interactive_tty") is not True:
        raise PreparationError("consent is not interactively granted")
    if consent["purpose"] != "local-model-training-poc":
        raise PreparationError("consent purpose does not match this training gate")
    files = consent["files"]
    if not isinstance(files, list) or not files or len(files) > 32:
        raise PreparationError("consent must name between 1 and 32 files")
    allowed = set(consent.get("allowed_extensions", [".md", ".txt"]))
    max_total = int(consent.get("max_total_bytes", 2_000_000))
    personal_data_allowed = bool(consent.get("personal_data_allowed", False))
    output = ensure_private_path(root, root / consent["output_dir"])
    if consent.get("external_network_allowed") is not False:
        raise PreparationError("this gate requires external networking to be forbidden")

    total = 0
    all_sections: list[tuple[str, str]] = []
    commitments: list[dict[str, Any]] = []
    for relative in files:
        source = (root / relative).resolve()
        if root not in source.parents or source.is_symlink() or not source.is_file():
            raise PreparationError("an authorised input is outside the repository, a symlink, or absent")
        if source.suffix.lower() not in allowed:
            raise PreparationError("an authorised input has an unsupported extension")
        raw = source.read_bytes()
        total += len(raw)
        if total > max_total:
            raise PreparationError("authorised input exceeds the consented byte ceiling")
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise PreparationError("an authorised input is not UTF-8 text") from exc
        findings = scan_text(text, personal_data_allowed)
        if findings:
            raise PreparationError("privacy scan rejected an authorised input: " + ",".join(findings))
        sections = markdown_sections(text)
        all_sections.extend(sections)
        commitments.append({
            "logical_index": len(commitments),
            "bytes": len(raw),
            "sha256": digest_bytes(raw),
            "sections": len(sections),
        })
    if len(all_sections) < 8:
        raise PreparationError("too few usable sections for a learning test")

    train, hidden = dataset_rows(all_sections)
    valid_count = max(4, min(len(train) // 10, 24))
    write_jsonl(output / "train.jsonl", train)
    write_jsonl(output / "valid.jsonl", train[:valid_count])
    write_jsonl(output / "test.jsonl", hidden)
    dataset_commitment = digest_bytes(
        (output / "train.jsonl").read_bytes()
        + (output / "valid.jsonl").read_bytes()
        + (output / "test.jsonl").read_bytes()
    )
    receipt = {
        "protocol": "kin/0.1",
        "type": "local_dataset_receipt",
        "consent_id_sha256": digest_bytes(str(consent["consent_id"]).encode()),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "purpose": consent["purpose"],
        "personal_data_allowed": personal_data_allowed,
        "file_count": len(commitments),
        "total_input_bytes": total,
        "input_commitments": commitments,
        "section_count": len(all_sections),
        "train_examples": len(train),
        "validation_examples": valid_count,
        "hidden_examples": len(hidden),
        "dataset_sha256": dataset_commitment,
        "raw_text_in_receipt": False,
        "source_paths_in_receipt": False,
        "network_used": False,
    }
    receipt["receipt_sha256"] = digest_bytes(canonical_json(receipt))
    (output / "dataset-receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--consent", type=Path, required=True)
    args = parser.parse_args()
    receipt = prepare(args.root, args.consent)
    print(json.dumps({
        "dataset_sha256": receipt["dataset_sha256"],
        "file_count": receipt["file_count"],
        "hidden_examples": receipt["hidden_examples"],
        "train_examples": receipt["train_examples"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
