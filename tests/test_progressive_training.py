import json
import tempfile
import unittest
from pathlib import Path

from local_data.progressive_training import prepare_rounds


class ProgressiveTrainingTests(unittest.TestCase):
    def test_rounds_add_data_and_keep_one_frozen_test_set(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(dir=root / ".local") as directory:
            private = Path(directory)
            job = private / "job"
            derived = job / "derived"
            derived.mkdir(parents=True)
            train = [{"prompt": f"prompt {i}", "completion": f"answer {i}"} for i in range(40)]
            test = [{"prompt": f"hidden {i}", "completion": f"expected {i}"} for i in range(8)]
            for name, rows in (("train", train), ("valid", train[:4]), ("test", test)):
                (derived / f"{name}.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows))
            result = prepare_rounds(job, private / "history", (0.25, 0.5, 1.0))
            self.assertEqual([item["train_examples"] for item in result["rounds"]], [10, 20, 40])
            frozen = [
                (item["directory"] / "data" / "test.jsonl").read_text()
                for item in result["rounds"]
            ]
            self.assertEqual(len(set(frozen)), 1)


if __name__ == "__main__":
    unittest.main()
