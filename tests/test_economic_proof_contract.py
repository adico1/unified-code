"""Truth gates for the registered AI-swarm economic experiment."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEED_PATH = ROOT / "seed/economics/ai-swarm-economic-experiment.seed.json"
SCHEMA_PATH = ROOT / "seed/economics/AI_SWARM_ECONOMIC_EXPERIMENT_SCHEMA.json"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_economic_experiment_seed_matches_schema():
    schema = _load(SCHEMA_PATH)
    seed = _load(SEED_PATH)
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"] == "uc://schemas/economics/ai-swarm-experiment@1"
    assert schema["type"] == "object"
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) <= set(seed)
    assert seed["format"] == schema["properties"]["format"]["const"]


def test_experiment_is_designed_not_falsely_reported_as_measured():
    seed = _load(SEED_PATH)
    assert seed["status"] == "designed"
    assert set(seed["authorities"].values()) == {"pending-seal"}
    assert seed["holdout"]["manifest_sha256"] == "pending-seal"
    assert seed["holdout"]["encrypted_corpus_sha256"] == "pending-seal"
    assert seed["assignment"]["seed_sha256"] == "pending-seal"
    assert {arm["swarm_contract"]["model_identity"] for arm in seed["arms"]} == {
        "pending-seal"
    }


def test_balanced_confirmatory_unit_count_and_independence():
    seed = _load(SEED_PATH)
    arm_ids = {arm["id"] for arm in seed["arms"]}
    assert arm_ids == {"baseline", "unified"}
    assert seed["holdout"]["task_count"] == 40
    assert seed["repeats"]["count_per_task_arm"] == 3
    assert seed["holdout"]["task_count"] * len(arm_ids) * seed["repeats"]["count_per_task_arm"] == 240
    assert seed["isolation"]["fresh_worktree"] is True
    assert seed["isolation"]["fresh_processes"] is True
    assert seed["isolation"]["cross_arm_exchange"] == "forbidden"
    assert seed["repeats"]["reuse"] == "no-agent-context-artifact-cache-or-worktree-reuse"


def test_complete_cost_and_failure_boundaries_are_registered():
    seed = _load(SEED_PATH)
    metrics = {metric["id"]: metric for metric in seed["metrics"]}
    assert {
        "wall-time",
        "model-input",
        "model-output",
        "model-cost",
        "tool-calls",
        "compute",
        "memory",
        "human-work",
        "iterations",
        "success",
        "quality",
        "marginal-cost",
        "total-cost",
    } == set(metrics)
    assert all(metric["include_failed_runs"] is True for metric in metrics.values())
    assert metrics["model-input"]["source"] == "model-provider-usage-event"
    assert seed["failure_accounting"]["principle"] == "intention-to-treat"
    assert seed["failure_accounting"]["missing_telemetry"] == "invalid-unit-no-success-or-savings-credit"


def test_claim_boundary_forbids_unsupported_extrapolation():
    seed = _load(SEED_PATH)
    prohibited = "\n".join(seed["allowed_claims"]["prohibited"])
    assert "trillions of dollars" in prohibited
    assert "all software" in prohibited
    assert "causality outside" in prohibited
    assert seed["stop_rules"]["ordinary"] == "run-all-preregistered-units"
    assert seed["stop_rules"]["early_success"] == "forbidden"


def test_equal_swarm_resources_and_distinct_workflow_authority():
    seed = _load(SEED_PATH)
    arms = {arm["id"]: arm for arm in seed["arms"]}
    baseline = arms["baseline"]["swarm_contract"]
    unified = arms["unified"]["swarm_contract"]
    assert baseline == unified
    assert "handwritten implementation and tests" in arms["baseline"]["permitted_work"]
    assert "application seed authoring" in arms["unified"]["permitted_work"]
    assert "the existing single public assembly API" in arms["unified"]["permitted_work"]
    assert "task-specific modification of permanent compiler surfaces" in arms["unified"]["prohibited_work"]
