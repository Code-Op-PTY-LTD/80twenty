#!/usr/bin/env python3
"""Generate and test a private KIN node without exposing its source."""

from __future__ import annotations

import argparse
import ast
import datetime as dt
import hashlib
import http.client
import json
import os
from pathlib import Path
import py_compile
import re
import subprocess
import sys
import tempfile
from typing import Any


PROTOCOL = "kin/0.1"
BUNDLE_FILES = (
    "SEED_INSTRUCTION.md",
    "PROTOCOL.md",
    "COMPENSATION.md",
    "protocol/manifest.json",
    "protocol/message.schema.json",
    "conformance/vectors.json",
)
DENIED_IMPORT_ROOTS = {
    "aiohttp",
    "ctypes",
    "ftplib",
    "http",
    "importlib",
    "multiprocessing",
    "requests",
    "smtplib",
    "socket",
    "subprocess",
    "telnetlib",
    "urllib",
    "webbrowser",
}
DENIED_CALLS = {"__import__", "compile", "eval", "exec"}
MAX_SOURCE_BYTES = 256 * 1024
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
MAX_CAPTURE_BYTES = 128 * 1024


class BootstrapError(RuntimeError):
    """A safe, source-free bootstrap failure."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def resolve_paths(bundle_arg: str, private_arg: str, evidence_arg: str) -> tuple[Path, Path, Path]:
    bundle = Path(bundle_arg).expanduser().resolve()
    private_dir = Path(private_arg).expanduser().resolve()
    evidence = Path(evidence_arg).expanduser().resolve()
    expected_private_root = bundle / ".local"
    expected_evidence_root = bundle / "evidence"
    if not bundle.is_dir():
        raise BootstrapError("bundle directory does not exist")
    if not private_dir.is_relative_to(expected_private_root):
        raise BootstrapError("private directory must be below the bundle .local directory")
    if not evidence.is_relative_to(expected_evidence_root) or evidence.suffix != ".json":
        raise BootstrapError("evidence must be a JSON file below the bundle evidence directory")
    for relative in BUNDLE_FILES:
        if not (bundle / relative).is_file():
            raise BootstrapError(f"bundle is missing required public artefact: {relative}")
    gitignore = bundle / ".gitignore"
    if not gitignore.is_file() or ".local/" not in gitignore.read_text(encoding="utf-8"):
        raise BootstrapError("bundle must ignore .local/ before private generation")
    return bundle, private_dir, evidence


def bundle_manifest(bundle: Path) -> tuple[list[str], str]:
    lines = []
    for relative in BUNDLE_FILES:
        digest = sha256_bytes((bundle / relative).read_bytes())
        lines.append(f"{digest}  {relative}")
    payload = ("\n".join(lines) + "\n").encode("utf-8")
    return lines, sha256_bytes(payload)


def public_bundle_text(bundle: Path) -> str:
    sections = []
    for relative in BUNDLE_FILES:
        text = (bundle / relative).read_text(encoding="utf-8")
        sections.append(f"\n===== {relative} =====\n{text}")
    return "".join(sections)


def generation_prompt(bundle: Path) -> str:
    contract = r"""
Generate one complete Python 3 standard-library-only private KIN node.
Return source text only: no Markdown fences, explanation or source echo command.

The exact CLI is: node.py --bundle PATH COMMAND
Commands:
  describe
  conform
  consent [NAME true|false]
  demo-update
  quote-check FILE
  erase [--confirm]
  fingerprint

Rules beyond the public bundle:
- Store state only at .kin/consent.json beside node.py.
- describe must literally explain permissions, files and network behavior.
- consent with no arguments prints current JSON state. A name requires true or false.
- erase without --confirm only previews. With --confirm it removes all .kin state.
- demo-update prints exactly one deterministic protocol update JSON object.
- fingerprint prints exactly the lowercase SHA-256 of node.py bytes.
- conform prints every public vector id and exits nonzero unless every vector passes.
- quote-check exits nonzero for an unfunded quote and zero for a funded valid quote.
- Recursively reject source_code, executable, executable_bytes, source_archive,
  patch and source_excerpt in network messages.
- Never import networking, process-launch, dynamic-import or package-install modules.
- Never read outside the exact bundle, exact quote path, node.py and its .kin state.
- Never print, transmit or copy generated source.
""".strip()
    return contract + "\n\nPUBLIC BUNDLE:" + public_bundle_text(bundle)


def repair_prompt(bundle: Path, source: str, failures: list[str]) -> str:
    safe_failures = json.dumps(failures, ensure_ascii=False)
    return (
        generation_prompt(bundle)
        + "\n\nThe previous private candidate failed these local checks: "
        + safe_failures
        + "\nReturn a complete corrected replacement. Previous candidate follows and must remain local:\n"
        + source
    )


def call_local_ollama(model: str, prompt: str, port: int, think: str) -> str:
    if not 1 <= port <= 65535:
        raise BootstrapError("invalid local Ollama port")
    request: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "keep_alive": 0,
        "options": {"temperature": 0, "num_predict": 5000},
    }
    if think == "false" or (think == "auto" and model.lower().startswith("qwen")):
        request["think"] = False
    elif think == "true":
        request["think"] = True
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=900)
    try:
        connection.request(
            "POST",
            "/api/generate",
            body=canonical_json(request),
            headers={"Content-Type": "application/json", "Connection": "close"},
        )
        response = connection.getresponse()
        body = response.read(MAX_RESPONSE_BYTES + 1)
    except OSError as exc:
        raise BootstrapError("local Ollama request failed") from exc
    finally:
        connection.close()
    if response.status != 200:
        raise BootstrapError(f"local Ollama returned HTTP {response.status}")
    if len(body) > MAX_RESPONSE_BYTES:
        raise BootstrapError("local Ollama response exceeded the size limit")
    try:
        payload = json.loads(body)
        source = payload["response"]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise BootstrapError("local Ollama returned an invalid response envelope") from exc
    if not isinstance(source, str) or not source.strip():
        raise BootstrapError("local Ollama returned no source")
    return source


def clean_source(source: str) -> str:
    value = source.strip()
    value = re.sub(r"^```(?:python)?\s*", "", value)
    value = re.sub(r"\s*```$", "", value).strip()
    encoded = value.encode("utf-8")
    if not encoded or len(encoded) > MAX_SOURCE_BYTES or b"\x00" in encoded:
        raise BootstrapError("private candidate has an invalid size or encoding")
    return value + "\n"


def audit_source(source: str) -> list[str]:
    failures: list[str] = []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return ["python syntax is invalid"]
    for node in ast.walk(tree):
        roots: list[str] = []
        if isinstance(node, ast.Import):
            roots = [alias.name.split(".", 1)[0] for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots = [node.module.split(".", 1)[0]]
        if any(root in DENIED_IMPORT_ROOTS for root in roots):
            failures.append("source imports a denied capability")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in DENIED_CALLS:
                failures.append("source calls a denied dynamic-execution primitive")
    return sorted(set(failures))


def write_private_source(private_dir: Path, source: str) -> Path:
    private_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(private_dir, 0o700)
    target = private_dir / "node.py"
    temporary = private_dir / ".node.py.tmp"
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(source)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
        os.chmod(target, 0o600)
    finally:
        if temporary.exists():
            temporary.unlink()
    return target


def sandbox_profile(private_dir: Path) -> str:
    private_literal = json.dumps(str(private_dir.resolve()))
    return (
        "(version 1)"
        "(deny default)"
        "(allow process*)"
        "(allow file-read*)"
        f"(allow file-write* (subpath {private_literal}))"
        "(allow sysctl-read)"
    )


def sandbox_command(node: Path, bundle: Path, *arguments: str) -> list[str]:
    return [
        "/usr/bin/sandbox-exec",
        "-p",
        sandbox_profile(node.parent),
        sys.executable,
        str(node),
        "--bundle",
        str(bundle),
        *arguments,
    ]


def run_private(node: Path, bundle: Path, *arguments: str) -> subprocess.CompletedProcess[bytes]:
    environment = {
        "LANG": "C.UTF-8",
        "PATH": "/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin",
        "PYTHONNOUSERSITE": "1",
    }
    try:
        result = subprocess.run(
            sandbox_command(node, bundle, *arguments),
            cwd=node.parent,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise BootstrapError("private command failed inside the network-denied sandbox") from exc
    if len(result.stdout) > MAX_CAPTURE_BYTES or len(result.stderr) > MAX_CAPTURE_BYTES:
        raise BootstrapError("private command exceeded the output limit")
    return result


def verify_sandbox_boundary(private_dir: Path) -> bool:
    allowed = private_dir / ".sandbox-write-probe"
    probe = """
import json
import pathlib
import socket
import sys

allowed_path = pathlib.Path(sys.argv[1])
denied_path = pathlib.Path(sys.argv[2])
allowed_path.write_text("allowed")
write_denied = False
network_denied = False
try:
    denied_path.write_text("must-not-write")
except OSError:
    write_denied = True
try:
    with socket.socket() as connection:
        connection.settimeout(1)
        connection.connect(("127.0.0.1", 9))
except PermissionError:
    network_denied = True
except OSError as error:
    network_denied = error.errno in (1, 13)
print(json.dumps({
    "allowed": allowed_path.is_file(),
    "network_denied": network_denied,
    "write_denied": write_denied,
}))
"""
    with tempfile.TemporaryDirectory(prefix="kin-gate0b-denied-") as outside:
        denied = Path(outside) / "denied"
        result = subprocess.run(
            [
                "/usr/bin/sandbox-exec",
                "-p",
                sandbox_profile(private_dir),
                sys.executable,
                "-c",
                probe,
                str(allowed),
                str(denied),
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=15,
            check=False,
        )
        try:
            payload = json.loads(result.stdout)
            return (
                result.returncode == 0
                and payload
                == {
                    "allowed": True,
                    "network_denied": True,
                    "write_denied": True,
                }
                and not denied.exists()
            )
        except (json.JSONDecodeError, TypeError):
            return False
        finally:
            if allowed.exists():
                allowed.unlink()


def decoded(data: bytes) -> str:
    return data.decode("utf-8", errors="replace")


def output_leaks_source(source: str, outputs: list[bytes]) -> bool:
    combined = b"\n".join(outputs).decode("utf-8", errors="replace")
    candidates = [
        line.strip()
        for line in source.splitlines()
        if len(line.strip()) >= 48 and not line.lstrip().startswith(("#", "import ", "from "))
    ]
    return any(line in combined for line in candidates)


def run_checks(node: Path, bundle: Path, source: str) -> tuple[dict[str, str], list[str]]:
    checks: dict[str, str] = {}
    failures: list[str] = []
    captured: list[bytes] = []

    try:
        py_compile.compile(str(node), doraise=True)
        checks["python_compile"] = "pass"
    except py_compile.PyCompileError:
        checks["python_compile"] = "fail"
        failures.append("python compile failed")

    static_failures = audit_source(source)
    checks["static_capability_audit"] = "pass" if not static_failures else "fail"
    failures.extend(static_failures)
    if failures:
        return checks, failures

    boundary_ok = verify_sandbox_boundary(node.parent)
    checks["network_denied_and_writes_confined"] = "pass" if boundary_ok else "fail"
    if not boundary_ok:
        failures.append("sandbox boundary probe failed")
        return checks, failures

    describe = run_private(node, bundle, "describe")
    captured += [describe.stdout, describe.stderr]
    describe_text = decoded(describe.stdout).lower()
    describe_ok = (
        describe.returncode == 0
        and "network" in describe_text
        and "file" in describe_text
        and "permission" in describe_text
    )
    checks["plain_language_description"] = "pass" if describe_ok else "fail"
    if not describe_ok:
        failures.append("describe contract failed")

    conform = run_private(node, bundle, "conform")
    captured += [conform.stdout, conform.stderr]
    vector_ids = [
        item["id"]
        for item in json.loads((bundle / "conformance/vectors.json").read_text(encoding="utf-8"))["vectors"]
    ]
    conform_text = decoded(conform.stdout)
    conform_ok = conform.returncode == 0 and all(vector_id in conform_text for vector_id in vector_ids)
    checks["public_vectors"] = "pass" if conform_ok else "fail"
    if not conform_ok:
        failures.append("public conformance vectors failed")

    first = run_private(node, bundle, "demo-update")
    second = run_private(node, bundle, "demo-update")
    captured += [first.stdout, first.stderr, second.stdout, second.stderr]
    try:
        update = json.loads(first.stdout)
        update_ok = (
            first.returncode == 0
            and second.returncode == 0
            and first.stdout == second.stdout
            and update.get("protocol") == PROTOCOL
            and update.get("type") == "update"
        )
    except (json.JSONDecodeError, AttributeError):
        update_ok = False
    checks["deterministic_synthetic_update"] = "pass" if update_ok else "fail"
    if not update_ok:
        failures.append("deterministic demo update contract failed")

    unfunded = node.parent / "unfunded-quote.json"
    funded = node.parent / "funded-quote.json"
    common_quote = {
        "protocol": PROTOCOL,
        "type": "price_quote",
        "job_id": "gate-0b-job",
        "base_checkpoint": "sha256:genesis",
        "pricing_version": "0.1-fixed",
        "currency": "ZAR",
        "max_payout": "50.00",
    }
    unfunded.write_bytes(canonical_json(common_quote))
    funded.write_bytes(canonical_json({**common_quote, "funding_commitment": "sha256:test-only"}))
    os.chmod(unfunded, 0o600)
    os.chmod(funded, 0o600)
    unfunded_result = run_private(node, bundle, "quote-check", str(unfunded))
    funded_result = run_private(node, bundle, "quote-check", str(funded))
    captured += [
        unfunded_result.stdout,
        unfunded_result.stderr,
        funded_result.stdout,
        funded_result.stderr,
    ]
    quote_ok = unfunded_result.returncode != 0 and funded_result.returncode == 0
    checks["funded_job_enforcement"] = "pass" if quote_ok else "fail"
    if not quote_ok:
        failures.append("funded quote contract failed")

    initial = run_private(node, bundle, "consent")
    changed = run_private(node, bundle, "consent", "synthetic_data", "true")
    shown = run_private(node, bundle, "consent")
    preview = run_private(node, bundle, "erase")
    consent_path = node.parent / ".kin" / "consent.json"
    still_exists_after_preview = consent_path.is_file()
    erased = run_private(node, bundle, "erase", "--confirm")
    captured += [
        initial.stdout,
        initial.stderr,
        changed.stdout,
        changed.stderr,
        shown.stdout,
        shown.stderr,
        preview.stdout,
        preview.stderr,
        erased.stdout,
        erased.stderr,
    ]
    consent_ok = (
        initial.returncode == 0
        and changed.returncode == 0
        and shown.returncode == 0
        and b"true" in shown.stdout.lower()
        and still_exists_after_preview
        and erased.returncode == 0
        and not consent_path.exists()
    )
    checks["reversible_consent_and_erase"] = "pass" if consent_ok else "fail"
    if not consent_ok:
        failures.append("consent or erase contract failed")

    fingerprint = run_private(node, bundle, "fingerprint")
    captured += [fingerprint.stdout, fingerprint.stderr]
    expected_fingerprint = sha256_bytes(node.read_bytes())
    fingerprint_ok = fingerprint.returncode == 0 and decoded(fingerprint.stdout).strip() == expected_fingerprint
    checks["implementation_fingerprint"] = "pass" if fingerprint_ok else "fail"
    if not fingerprint_ok:
        failures.append("fingerprint contract failed")

    leak = output_leaks_source(source, captured)
    checks["source_not_emitted_by_cli"] = "pass" if not leak else "fail"
    if leak:
        failures.append("private CLI emitted generated source")

    return checks, failures


def save_private_failure(private_dir: Path, attempt: int, failures: list[str]) -> None:
    path = private_dir / "bootstrap-failures.json"
    history: list[dict[str, Any]] = []
    if path.is_file():
        try:
            history = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            history = []
    history.append({"attempt": attempt, "failures": failures})
    path.write_bytes(canonical_json(history))
    os.chmod(path, 0o600)


def write_evidence(
    path: Path,
    model: str,
    node: Path,
    bundle_digest: str,
    checks: dict[str, str],
    attempts: int,
    verification_mode: str = "generate_and_verify",
) -> None:
    evidence = {
        "gate": "0b-local-private-bootstrap",
        "protocol": PROTOCOL,
        "recorded_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "result": "pass",
        "model": model,
        "generation_attempts": attempts,
        "verification_mode": verification_mode,
        "bundle_manifest_sha256": bundle_digest,
        "implementation_sha256": sha256_bytes(node.read_bytes()),
        "runtime": f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "checks": checks,
        "generated_source_in_evidence": False,
        "generated_source_committed": False,
        "ollama_endpoint": "loopback-only",
        "private_workspace": ".local (gitignored, mode 0700)",
        "execution_boundary": "macOS sandbox-exec with networking denied and file writes confined to the private workspace",
        "claim": "The bootstrap process wrote the local model response directly to the private workspace and emitted only this evidence summary.",
        "limitations": "This is a local bootstrap and CLI-boundary proof, not proof against a compromised OS, Ollama daemon, seed model, Python runtime or macOS sandbox implementation. File reads are not yet OS-confined; the generated node contract and static audit remain responsible for read scope.",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(canonical_json(evidence) + b"\n")
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, help="installed local Ollama model")
    parser.add_argument("--bundle", default=".", help="KIN public bundle")
    parser.add_argument("--private-dir", default=".local/gate-0b", help="private generated workspace")
    parser.add_argument("--evidence", default="evidence/gate-0b-local-bootstrap.json")
    parser.add_argument("--ollama-port", type=int, default=11434)
    parser.add_argument("--max-attempts", type=int, choices=range(1, 6), default=3)
    parser.add_argument("--think", choices=("auto", "true", "false"), default="auto")
    parser.add_argument(
        "--verify-existing",
        action="store_true",
        help="test an existing private node without contacting Ollama",
    )
    args = parser.parse_args()

    try:
        bundle, private_dir, evidence_path = resolve_paths(
            args.bundle, args.private_dir, args.evidence
        )
        _, digest = bundle_manifest(bundle)
        if args.verify_existing:
            node = private_dir / "node.py"
            if not node.is_file():
                raise BootstrapError("no existing private node was found")
            source = node.read_text(encoding="utf-8")
            checks, failures = run_checks(node, bundle, source)
            if failures:
                save_private_failure(private_dir, 0, failures)
                raise BootstrapError("existing private candidate did not pass")
            attempt_count = 0
            failure_receipt = private_dir / "bootstrap-failures.json"
            if failure_receipt.is_file():
                try:
                    prior = json.loads(failure_receipt.read_text(encoding="utf-8"))
                    attempt_count = max(
                        (int(item.get("attempt", 0)) for item in prior), default=0
                    )
                except (json.JSONDecodeError, OSError, TypeError, ValueError):
                    attempt_count = 0
            write_evidence(
                evidence_path,
                args.model,
                node,
                digest,
                checks,
                attempt_count,
                "verify_existing",
            )
            print("Gate 0b PASS: existing private source verified without contacting Ollama.")
            print(f"Evidence: {evidence_path}")
            return 0
        prompt = generation_prompt(bundle)
        source = ""
        checks: dict[str, str] = {}
        for attempt in range(1, args.max_attempts + 1):
            print(f"Local generation attempt {attempt}/{args.max_attempts}...", flush=True)
            raw_source = call_local_ollama(
                args.model, prompt, args.ollama_port, args.think
            )
            source = clean_source(raw_source)
            node = write_private_source(private_dir, source)
            checks, failures = run_checks(node, bundle, source)
            if not failures:
                write_evidence(
                    evidence_path, args.model, node, digest, checks, attempt
                )
                print("Gate 0b PASS: private source retained locally; evidence contains hashes and results only.")
                print(f"Evidence: {evidence_path}")
                return 0
            save_private_failure(private_dir, attempt, failures)
            if attempt == args.max_attempts:
                break
            print("Candidate failed local checks; requesting a local repair without exposing source.", flush=True)
            prompt = repair_prompt(bundle, source, failures)
        raise BootstrapError("private candidate did not pass; details remain in the private workspace")
    except BootstrapError as exc:
        print(f"Gate 0b FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
