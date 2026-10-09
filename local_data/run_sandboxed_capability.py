#!/usr/bin/env python3
"""Verify and consume a native capability with network and home access denied."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from local_data.capability import verify_capability


def _quote_profile(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def sandbox_profile(job_dir: Path, consumer: Path) -> str:
    job = _quote_profile(str(job_dir.resolve()))
    return f"""(version 1)
(allow default)
(deny network*)
(deny file-read* (subpath \"/Users\") (subpath \"/Volumes\")
                 (subpath \"/private/tmp\") (subpath \"/private/var/folders\"))
(allow file-read* (subpath {job}) (literal {_quote_profile(str(consumer.resolve()))}))
(deny file-write*)
(allow file-write* (subpath {job}) (literal \"/dev/null\"))
"""


def run(job_dir: Path, *, probe_read: Path | None = None) -> subprocess.CompletedProcess[str]:
    if sys.platform != "darwin":
        raise RuntimeError("Gate 1c OS enforcement currently requires macOS")
    sandbox = shutil.which("sandbox-exec")
    if not sandbox:
        raise RuntimeError("macOS sandbox-exec is unavailable")
    job_dir = job_dir.resolve()
    verify_capability(job_dir)
    project_root = Path(__file__).resolve().parents[1]
    consumer = (project_root / ".local" / "bin" / "kin-capability-consumer").resolve()
    if not consumer.is_file():
        raise RuntimeError("native consumer is not built; run macos/build_app.sh")
    profile = sandbox_profile(job_dir, consumer)
    if probe_read is None:
        command = [str(consumer), "--job-dir", str(job_dir)]
    else:
        command = ["/usr/bin/cat", str(probe_read.resolve())]
    environment = {"PATH": "/usr/bin:/bin", "TMPDIR": str(job_dir)}
    with tempfile.NamedTemporaryFile("w", suffix=".sb", delete=False) as handle:
        handle.write(profile)
        profile_path = Path(handle.name)
    try:
        return subprocess.run(
            [sandbox, "-f", str(profile_path), *command],
            cwd=project_root,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )
    finally:
        profile_path.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--job-dir", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.job_dir)
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, file=sys.stderr, end="")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
