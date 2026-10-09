#!/usr/bin/env python3
"""Validate the arithmetic and mandatory gates of an 80Twenty release record."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


STANDARD = "80twenty-frontier/0.1"
OVERALL_QUALITY_FLOOR = 0.80
CATEGORY_QUALITY_FLOOR = 0.70
COST_RATIO_CEILING = 0.20
REQUIRED_CATEGORIES = {
    "reasoning",
    "coding",
    "factuality_knowledge",
    "instruction_following",
    "real_user_tasks",
}
REQUIRED_GATES = {"safety", "privacy", "provenance", "reproducibility"}
REQUIRED_GENESIS_COST_COMPONENTS = {
    "participant_compensation",
    "compute_energy",
    "bandwidth_storage",
    "orchestration_validation",
    "retries_failures_fraud",
    "payment_fees",
}
REQUIRED_FRONTIER_COST_COMPONENTS = {"billed_usage", "supporting_inference"}


class QualificationError(ValueError):
    """The result record is malformed or cannot be evaluated."""


def _finite_nonnegative(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise QualificationError(f"{name} must be a number")
    result = float(value)
    if not math.isfinite(result) or result < 0:
        raise QualificationError(f"{name} must be finite and non-negative")
    return result


def _component_total(value: Any, required: set[str], name: str) -> float:
    if not isinstance(value, dict):
        raise QualificationError(f"{name} must be an object")
    missing = sorted(required - value.keys())
    if missing:
        raise QualificationError(f"{name} is missing: {', '.join(missing)}")
    unknown = sorted(value.keys() - required)
    if unknown:
        raise QualificationError(f"{name} has unknown components: {', '.join(unknown)}")
    return sum(_finite_nonnegative(value[field], f"{name}.{field}") for field in required)


def evaluate(record: dict[str, Any]) -> dict[str, Any]:
    if record.get("standard") != STANDARD:
        raise QualificationError(f"standard must equal {STANDARD}")

    candidate = record.get("candidate")
    if not isinstance(candidate, dict):
        raise QualificationError("candidate must be an object")
    for field in ("name", "version", "weights_sha256", "accord_version"):
        if not isinstance(candidate.get(field), str) or not candidate[field]:
            raise QualificationError(f"candidate.{field} is required")

    snapshot = record.get("snapshot")
    if not isinstance(snapshot, dict):
        raise QualificationError("snapshot must be an object")
    for field in ("cutoff_at", "task_set_sha256", "frozen_before_evaluation"):
        if field not in snapshot:
            raise QualificationError(f"snapshot.{field} is required")
    if snapshot["frozen_before_evaluation"] is not True:
        raise QualificationError("snapshot must be frozen before evaluation")

    references = record.get("references")
    if not isinstance(references, list) or not references:
        raise QualificationError("at least one reference model is required")
    for index, reference in enumerate(references):
        if not isinstance(reference, dict):
            raise QualificationError(f"references[{index}] must be an object")
        for field in ("provider", "model", "version", "available_at_cutoff"):
            if field not in reference:
                raise QualificationError(f"references[{index}].{field} is required")
        if reference["available_at_cutoff"] is not True:
            raise QualificationError("every reference must be available at the cut-off")

    expected_thresholds = {
        "overall_quality_ratio": OVERALL_QUALITY_FLOOR,
        "category_quality_ratio": CATEGORY_QUALITY_FLOOR,
        "cost_ratio": COST_RATIO_CEILING,
    }
    if record.get("thresholds") != expected_thresholds:
        raise QualificationError(f"thresholds must equal {expected_thresholds}")

    categories = record.get("categories")
    if not isinstance(categories, list) or not categories:
        raise QualificationError("categories must be a non-empty list")
    names = {category.get("name") for category in categories if isinstance(category, dict)}
    missing = sorted(REQUIRED_CATEGORIES - names)
    if missing:
        raise QualificationError(f"missing required categories: {', '.join(missing)}")

    weight_total = 0.0
    genesis_weighted = 0.0
    frontier_weighted = 0.0
    category_results = []
    for category in categories:
        if not isinstance(category, dict):
            raise QualificationError("each category must be an object")
        name = category.get("name")
        if not isinstance(name, str) or not name:
            raise QualificationError("category.name is required")
        weight = _finite_nonnegative(category.get("weight"), f"{name}.weight")
        genesis_score = _finite_nonnegative(category.get("genesis_score"), f"{name}.genesis_score")
        frontier_score = _finite_nonnegative(category.get("frontier_score"), f"{name}.frontier_score")
        if weight <= 0 or frontier_score <= 0:
            raise QualificationError(f"{name} weight and frontier score must be positive")
        ratio = genesis_score / frontier_score
        weight_total += weight
        genesis_weighted += weight * genesis_score
        frontier_weighted += weight * frontier_score
        category_results.append({"name": name, "quality_ratio": ratio, "pass": ratio >= CATEGORY_QUALITY_FLOOR})

    if not math.isclose(weight_total, 1.0, rel_tol=0, abs_tol=1e-9):
        raise QualificationError("category weights must sum to 1")
    overall_ratio = genesis_weighted / frontier_weighted

    cost = record.get("cost")
    if not isinstance(cost, dict):
        raise QualificationError("cost must be an object")
    genesis_total = _finite_nonnegative(cost.get("genesis_total"), "cost.genesis_total")
    genesis_successes = _finite_nonnegative(cost.get("genesis_successful_tasks"), "cost.genesis_successful_tasks")
    frontier_total = _finite_nonnegative(cost.get("frontier_total"), "cost.frontier_total")
    frontier_successes = _finite_nonnegative(cost.get("frontier_successful_tasks"), "cost.frontier_successful_tasks")
    declared_genesis_total = _component_total(
        cost.get("genesis_components"), REQUIRED_GENESIS_COST_COMPONENTS, "cost.genesis_components"
    )
    declared_frontier_total = _component_total(
        cost.get("frontier_components"), REQUIRED_FRONTIER_COST_COMPONENTS, "cost.frontier_components"
    )
    if not math.isclose(genesis_total, declared_genesis_total, rel_tol=0, abs_tol=1e-9):
        raise QualificationError("cost.genesis_total must equal the component sum")
    if not math.isclose(frontier_total, declared_frontier_total, rel_tol=0, abs_tol=1e-9):
        raise QualificationError("cost.frontier_total must equal the component sum")
    if genesis_successes <= 0 or frontier_successes <= 0 or frontier_total <= 0:
        raise QualificationError("successful task counts and frontier total cost must be positive")
    genesis_per_success = genesis_total / genesis_successes
    frontier_per_success = frontier_total / frontier_successes
    cost_ratio = genesis_per_success / frontier_per_success

    gates = record.get("gates")
    if not isinstance(gates, dict):
        raise QualificationError("gates must be an object")
    missing_gates = sorted(REQUIRED_GATES - gates.keys())
    if missing_gates:
        raise QualificationError(f"missing required gates: {', '.join(missing_gates)}")
    gates_pass = all(gates[name] is True for name in REQUIRED_GATES)

    qualified = (
        overall_ratio >= OVERALL_QUALITY_FLOOR
        and all(item["pass"] for item in category_results)
        and cost_ratio <= COST_RATIO_CEILING
        and gates_pass
    )
    return {
        "standard": STANDARD,
        "candidate": candidate,
        "qualified": qualified,
        "quality": {
            "overall_ratio": overall_ratio,
            "required_ratio": OVERALL_QUALITY_FLOOR,
            "categories": category_results,
        },
        "cost": {
            "genesis_per_successful_task": genesis_per_success,
            "frontier_per_successful_task": frontier_per_success,
            "ratio": cost_ratio,
            "maximum_ratio": COST_RATIO_CEILING,
        },
        "gates_pass": gates_pass,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("record", type=Path)
    arguments = parser.parse_args()
    try:
        result = evaluate(json.loads(arguments.record.read_text()))
    except (OSError, json.JSONDecodeError, QualificationError) as error:
        parser.error(str(error))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["qualified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
