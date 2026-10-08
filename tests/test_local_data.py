import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from local_data.consent_broker import CONFIRMATION, request_consent
from local_data.prepare_dataset import PreparationError, prepare, scan_text


class LocalDataTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
