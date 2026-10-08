import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "local_bootstrap", ROOT / "bootstrap" / "local_bootstrap.py"
)
BOOTSTRAP = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(BOOTSTRAP)


class LocalBootstrapTests(unittest.TestCase):
    def test_bundle_digest_matches_published_manifest(self):
        _, digest = BOOTSTRAP.bundle_manifest(ROOT)
        self.assertEqual(
            digest,
            "79d352de27824c84578fc77193ef93a266572fd345c84cb4fb076b876a56fe73",
        )

    def test_audit_rejects_network_and_dynamic_execution(self):
        source = "import socket\neval('1 + 1')\n"
        failures = BOOTSTRAP.audit_source(source)
        self.assertIn("source imports a denied capability", failures)
        self.assertIn("source calls a denied dynamic-execution primitive", failures)

    def test_audit_accepts_small_standard_library_cli(self):
        source = "import argparse, hashlib, json\nprint(json.dumps({'ok': True}))\n"
        self.assertEqual(BOOTSTRAP.audit_source(source), [])

    def test_clean_source_removes_only_outer_fence(self):
        source = BOOTSTRAP.clean_source("```python\nprint('ok')\n```")
        self.assertEqual(source, "print('ok')\n")

    def test_sandbox_profile_defaults_to_deny_and_allows_only_private_writes(self):
        private = (ROOT / ".local" / "profile-test").resolve()
        profile = BOOTSTRAP.sandbox_profile(private)
        self.assertIn("(deny default)", profile)
        self.assertIn("(allow file-read*)", profile)
        self.assertIn(f'(allow file-write* (subpath "{private}"))', profile)
        self.assertNotIn("allow network", profile)

    def test_private_path_is_required(self):
        with self.assertRaises(BOOTSTRAP.BootstrapError):
            BOOTSTRAP.resolve_paths(
                str(ROOT), str(ROOT / "not-private"), str(ROOT / "evidence" / "x.json")
            )

    def test_evidence_contains_no_source(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".local") as directory:
            private = Path(directory)
            node = private / "node.py"
            node.write_text("print('private sentinel')\n", encoding="utf-8")
            evidence = private / "evidence.json"
            BOOTSTRAP.write_evidence(
                evidence,
                "test-model",
                node,
                "0" * 64,
                {"test": "pass"},
                1,
            )
            payload = evidence.read_text(encoding="utf-8")
            self.assertNotIn("private sentinel", payload)
            self.assertFalse(json.loads(payload)["generated_source_in_evidence"])


if __name__ == "__main__":
    unittest.main()
