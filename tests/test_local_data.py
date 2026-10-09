import contextlib
import base64
import hashlib
import io
import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from local_data.capability import CapabilityError, canonical_json, verify_capability
from local_data.consent_broker import CONFIRMATION, request_consent
from local_data.prepare_dataset import PreparationError, prepare, scan_text
from local_data.run_sandboxed_capability import run
from local_data.recover_native_job import RecoveryError, recover


class LocalDataTests(unittest.TestCase):
    def _native_capability_job(
        self, root: Path, parent: Path, *, personal_data_allowed: bool = False,
        include_image: bool = False,
    ) -> Path:
        job = parent / ("native-personal-job" if personal_data_allowed else "native-job")
        inputs = job / "inputs"
        inputs.mkdir(parents=True)
        raw = "".join(
            f"## Section {i}\n\nThis is authorised synthetic native material number {i} with enough words for preparation."
            + (f" Contact person{i}@example.com.\n\n" if personal_data_allowed else "\n\n")
            for i in range(8)
        ).encode()
        source = inputs / "000.md"
        source.write_bytes(raw)
        files = [{"name": "000.md", "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}]
        total_bytes = len(raw)
        if include_image:
            source_media = b"synthetic-image-source-commitment"
            derivative = (
                b"# Local image observations\n\n"
                b"Local on-device image analysis found no faces and classified a synthetic blue square.\n"
            )
            (inputs / "001.txt").write_bytes(derivative)
            files.append({
                "name": "001.txt",
                "bytes": len(derivative),
                "sha256": hashlib.sha256(derivative).hexdigest(),
                "derived_from": "image",
                "source_media_sha256": hashlib.sha256(source_media).hexdigest(),
            })
            total_bytes += len(derivative)
        now = datetime.now(timezone.utc)
        payload = {
            "protocol": "kin/0.1",
            "type": "file_capability",
            "capability_version": "kin-file-capability/0.1",
            "job_id": "synthetic-native-test",
            "purpose": "local-model-training-poc",
            "granted": True,
            "interactive_confirmation": True,
            "interaction_channel": "macos_native",
            "created_at": now.isoformat(),
            "expires_at": (now + timedelta(hours=1)).isoformat(),
            "files": files,
            "total_input_bytes": total_bytes,
            "max_total_bytes": 2_000_000,
            "personal_data_allowed": personal_data_allowed,
            "image_data_allowed": include_image,
            "external_network_allowed": False,
            "real_payment": False,
            "source_paths_recorded": False,
            "original_file_names_recorded": False,
            "withdrawal_limit_acknowledged": True,
        }
        key = Ed25519PrivateKey.generate()
        public = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        record = {
            "payload": payload,
            "public_key": base64.b64encode(public).decode(),
            "signature": base64.b64encode(key.sign(canonical_json(payload))).decode(),
        }
        (job / "capability.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
        return job

    def test_scanner_rejects_credentials_and_personal_identifiers(self):
        text = "password=supersecret contact test@example.com or +27 82 123 4567"
        findings = scan_text(text, personal_data_allowed=False)
        self.assertIn("secret_assignment", findings)
        self.assertIn("email_address", findings)
        self.assertIn("phone_number_like_text", findings)

    def test_scanner_can_allow_identifiers_but_never_private_keys(self):
        text = "test@example.com\n-----BEGIN PRIVATE KEY-----\n"
        self.assertEqual(scan_text(text, personal_data_allowed=True), ["private_key"])

    def test_preparation_requires_private_consent_and_output(self):
        root = Path(__file__).resolve().parents[1]
        with self.assertRaises(PreparationError):
            prepare(root, root / "README.md")

    def test_private_fixture_produces_no_text_or_paths_in_receipt(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(dir=root / ".local") as directory:
            private = Path(directory)
            fixture = root / ".local" / "fixture-local-data.md"
            fixture.write_text("".join(
                f"## Section {i}\n\nThis is authorised synthetic local material number {i} with enough words for preparation.\n\n"
                for i in range(8)
            ))
            consent = private / "consent.json"
            with contextlib.redirect_stdout(io.StringIO()):
                granted = request_consent(
                    root=root,
                    files=[str(fixture.relative_to(root))],
                    output_dir=str((private / "derived").relative_to(root)),
                    receipt_path=consent,
                    max_total_bytes=100_000,
                    input_func=lambda _: CONFIRMATION,
                    require_tty=False,
                )
            self.assertTrue(granted)
            receipt = prepare(root, consent)
            encoded = json.dumps(receipt)
            self.assertFalse(receipt["raw_text_in_receipt"])
            self.assertFalse(receipt["source_paths_in_receipt"])
            self.assertNotIn("authorised synthetic", encoded)
            fixture.unlink()

    def test_decline_creates_no_receipt(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(dir=root / ".local") as directory:
            private = Path(directory)
            receipt = private / "declined.json"
            with contextlib.redirect_stdout(io.StringIO()):
                granted = request_consent(
                    root=root,
                    files=["README.md"],
                    output_dir=str((private / "derived").relative_to(root)),
                    receipt_path=receipt,
                    max_total_bytes=100_000,
                    input_func=lambda _: "NO",
                    require_tty=False,
                )
            self.assertFalse(granted)
            self.assertFalse(receipt.exists())

    def test_flat_precreated_consent_is_rejected(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(dir=root / ".local") as directory:
            consent = Path(directory) / "forged.json"
            consent.write_text(json.dumps({"granted": True, "interactive_confirmation": True}))
            with self.assertRaises(PreparationError):
                prepare(root, consent)

    def test_unattended_consent_is_rejected(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(dir=root / ".local") as directory:
            private = Path(directory)
            with self.assertRaises(RuntimeError):
                request_consent(
                    root=root,
                    files=["README.md"],
                    output_dir=str((private / "derived").relative_to(root)),
                    receipt_path=private / "receipt.json",
                    max_total_bytes=100_000,
                    input_func=lambda _: CONFIRMATION,
                )

    def test_published_local_data_evidence_has_metrics_but_no_paths(self):
        root = Path(__file__).resolve().parents[1]
        evidence_path = root / "evidence" / "gate-1b-consented-local-data.json"
        evidence = json.loads(evidence_path.read_text())
        self.assertLess(
            evidence["evaluation"]["adapter_test_loss"],
            evidence["evaluation"]["base_test_loss"],
        )
        self.assertTrue(evidence["consent"]["interactive_confirmation"])
        self.assertFalse(evidence["dataset"]["raw_text_published"])
        self.assertFalse(evidence["dataset"]["source_paths_published"])
        self.assertNotIn(".local/", evidence_path.read_text())

    def test_native_capability_detects_snapshot_tampering(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(dir=root / ".local") as directory:
            job = self._native_capability_job(root, Path(directory))
            verify_capability(job)
            (job / "inputs" / "000.md").write_text("tampered")
            with self.assertRaises(CapabilityError):
                verify_capability(job)

    def test_interrupted_native_job_can_be_recovered_without_source_paths(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(dir=root / ".local") as directory:
            private = Path(directory)
            job = private / "KIN-job-7467c8f3-5cb2-4130-84e3-e8d80492e6f8"
            inputs = job / "inputs"
            inputs.mkdir(parents=True)
            for index in range(2):
                (inputs / f"{index:06d}.txt").write_text(f"approved snapshot {index}")
            summary = recover(job, private / "recovery.key")
            payload = verify_capability(job)
            self.assertEqual(summary["file_count"], 2)
            self.assertEqual(payload["interaction_channel"], "macos_native_recovery")
            self.assertTrue(payload["recovered_from_interrupted_native_broker"])
            self.assertFalse(payload["source_paths_recorded"])
            (inputs / "000002.txt").write_text("approved snapshot 2")
            refreshed = recover(job, private / "recovery.key", replace_existing_recovery=True)
            self.assertEqual(refreshed["file_count"], 3)

    def test_recovery_rejects_non_native_snapshot_names(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(dir=root / ".local") as directory:
            private = Path(directory)
            job = private / "KIN-job-7467c8f3-5cb2-4130-84e3-e8d80492e6f8"
            inputs = job / "inputs"
            inputs.mkdir(parents=True)
            (inputs / "original-name.txt").write_text("must not be accepted")
            with self.assertRaises(RecoveryError):
                recover(job, private / "recovery.key")

    def test_gate_1c_evidence_records_native_isolation(self):
        root = Path(__file__).resolve().parents[1]
        evidence = json.loads((root / "evidence" / "gate-1c-native-broker.json").read_text())
        self.assertTrue(evidence["platform"]["app_sandbox_entitlement"])
        self.assertTrue(evidence["consumer_sandbox"]["unrelated_file_probe_denied"])
        self.assertTrue(evidence["verification"]["snapshot_tampering_rejected"])
        self.assertFalse(evidence["verification"]["interactive_native_participant_run_recorded"])
        self.assertTrue(evidence["capability"]["one_or_multiple_folder_mode"])
        self.assertTrue(evidence["capability"]["recursive_everything_compatible_mode"])
        self.assertFalse(evidence["capability"]["personal_data_allowed_in_primary_fixture"])
        self.assertTrue(evidence["capability"]["personal_data_allowed_in_opt_in_fixture"])
        self.assertEqual(
            evidence["platform"]["companion_source_sha256"],
            hashlib.sha256((root / "macos" / "KINCompanion.swift").read_bytes()).hexdigest(),
        )
        self.assertEqual(
            evidence["platform"]["consumer_source_sha256"],
            hashlib.sha256((root / "macos" / "KINCapabilityConsumer.swift").read_bytes()).hexdigest(),
        )

    @unittest.skipUnless(sys.platform == "darwin", "macOS sandbox proof")
    def test_native_capability_consumer_is_os_sandboxed(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(dir=root / ".local") as directory:
            job = self._native_capability_job(root, Path(directory))
            consumed = run(job)
            self.assertEqual(consumed.returncode, 0, consumed.stderr)
            receipt = json.loads((job / "derived" / "dataset-receipt.json").read_text())
            self.assertTrue(receipt["native_broker"])
            self.assertFalse(receipt["source_paths_in_capability"])
            self.assertFalse(receipt["personal_data_allowed"])
            personal_job = self._native_capability_job(
                root, Path(directory), personal_data_allowed=True, include_image=True
            )
            personal = run(personal_job)
            self.assertEqual(personal.returncode, 0, personal.stderr)
            personal_receipt = json.loads((personal_job / "derived" / "dataset-receipt.json").read_text())
            self.assertTrue(personal_receipt["personal_data_allowed"])
            self.assertEqual(personal_receipt["image_count"], 1)
            self.assertEqual(
                personal_receipt["image_processing"],
                "local_vision_ocr_classification_not_visual_finetuning",
            )
            self.assertFalse(personal_receipt["raw_images_in_receipt"])
            with tempfile.NamedTemporaryFile() as outside:
                outside.write(b"must remain unreadable")
                outside.flush()
                denied = run(job, probe_read=Path(outside.name))
            self.assertNotEqual(denied.returncode, 0)


if __name__ == "__main__":
    unittest.main()
