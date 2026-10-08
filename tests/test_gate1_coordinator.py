import base64
import json
import tempfile
import unittest
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from gate1.coordinator import (
    PROTOCOL,
    canonical_json,
    make_envelope,
    public_key_b64,
    sha256_file,
    verify_signature,
)


class Gate1CoordinatorTests(unittest.TestCase):
    def test_canonical_json_is_order_independent(self):
        self.assertEqual(canonical_json({"b": 2, "a": 1}), canonical_json({"a": 1, "b": 2}))

    def test_signed_envelope_verifies_and_binds_adapter(self):
        with tempfile.TemporaryDirectory() as directory:
            adapter = Path(directory) / "adapter.bin"
            adapter.write_bytes(b"bounded synthetic update")
            key = Ed25519PrivateKey.generate()
            envelope = make_envelope(
                node_id="node-1", job_id="job-1", base_model="example/model",
                base_revision="abc123", adapter_path=adapter,
                base_checkpoint="sha256:" + "a" * 64,
                dataset_commitment="d" * 64, examples=12, steps=8, private_key=key,
            )
            self.assertEqual(envelope["payload"]["protocol"], PROTOCOL)
            self.assertEqual(envelope["payload"]["adapter_sha256"], sha256_file(adapter))
            self.assertTrue(verify_signature(
                envelope["payload"], envelope["signature"], public_key_b64(key)
            ))

    def test_mutated_payload_fails_signature(self):
        key = Ed25519PrivateKey.generate()
        payload = {"type": "update", "steps": 8}
        signature = base64.b64encode(key.sign(canonical_json(payload))).decode()
        payload["steps"] = 9
        self.assertFalse(verify_signature(payload, signature, public_key_b64(key)))

    def test_malformed_signature_fails_closed(self):
        key = Ed25519PrivateKey.generate()
        self.assertFalse(verify_signature({"type": "update"}, "%%%", public_key_b64(key)))

    def test_published_evidence_records_learning_and_rejection(self):
        evidence_path = Path(__file__).parents[1] / "evidence" / "gate-1a-local-adapter.json"
        evidence = json.loads(evidence_path.read_text())
        self.assertLess(evidence["evaluation"]["aggregate_test_loss"], evidence["evaluation"]["base_test_loss"])
        self.assertEqual(sum(item["status"] == "accepted" for item in evidence["updates"]), 3)
        self.assertEqual(evidence["malicious_update"]["status"], "rejected")
        self.assertFalse(evidence["compensation"]["real_money_moved"])
        self.assertNotIn(".local/", evidence_path.read_text())


if __name__ == "__main__":
    unittest.main()
