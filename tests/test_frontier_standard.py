import copy
import json
import unittest
from pathlib import Path

from frontier.evaluate_release import QualificationError, evaluate


class FrontierStandardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parents[1]
        cls.example = json.loads((root / "frontier" / "example-result.json").read_text())

    def test_example_qualifies(self):
        result = evaluate(copy.deepcopy(self.example))
        self.assertTrue(result["qualified"])
        self.assertAlmostEqual(result["quality"]["overall_ratio"], 0.812)
        self.assertAlmostEqual(result["cost"]["ratio"], 0.19)

    def test_one_weak_category_blocks_qualification(self):
        record = copy.deepcopy(self.example)
        record["categories"][0]["genesis_score"] = 0.69
        self.assertFalse(evaluate(record)["qualified"])

    def test_failed_privacy_gate_blocks_qualification(self):
        record = copy.deepcopy(self.example)
        record["gates"]["privacy"] = False
        self.assertFalse(evaluate(record)["qualified"])

    def test_weights_must_be_frozen_and_sum_to_one(self):
        record = copy.deepcopy(self.example)
        record["snapshot"]["frozen_before_evaluation"] = False
        with self.assertRaises(QualificationError):
            evaluate(record)
        record = copy.deepcopy(self.example)
        record["categories"][0]["weight"] = 0.3
        with self.assertRaises(QualificationError):
            evaluate(record)

    def test_candidate_cannot_weaken_normative_thresholds(self):
        record = copy.deepcopy(self.example)
        record["thresholds"]["overall_quality_ratio"] = 0.5
        with self.assertRaises(QualificationError):
            evaluate(record)

    def test_cost_total_must_include_all_declared_components(self):
        record = copy.deepcopy(self.example)
        record["cost"]["genesis_components"]["participant_compensation"] = 0
        with self.assertRaises(QualificationError):
            evaluate(record)


if __name__ == "__main__":
    unittest.main()
