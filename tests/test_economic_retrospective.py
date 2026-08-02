"""Determinism, privacy and claim-boundary tests for retrospective-v1."""

from __future__ import annotations

import json
from datetime import timezone
from pathlib import Path

from scripts.build_economic_retrospective import (
    FORMAT,
    canonical_bytes,
    parse_time,
    sessions_projection,
    sha256_value,
)


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "artifacts/economics/retrospective-v1.json"
SCHEMA = ROOT / "seed/economics/ECONOMIC_RETROSPECTIVE_SCHEMA.json"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_published_retrospective_identity_and_claim_boundary():
    dataset = load(DATASET)
    identity = dataset.pop("dataset_sha256")
    assert dataset["format"] == FORMAT
    assert identity == sha256_value(dataset)
    assert dataset["status"] == "retrospective-observational"
    assert "causal savings remain unknown" in dataset["measurement_boundary"]["causality"]
    assert any("trillion-dollar" in claim for claim in dataset["prohibited_claims"])


def test_retrospective_schema_tracks_the_published_contract():
    schema = load(SCHEMA)
    dataset = load(DATASET)
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(dataset)
    assert dataset["format"] == schema["properties"]["format"]["const"]


def test_published_retrospective_contains_measured_work():
    dataset = load(DATASET)
    sessions = dataset["sources"]["codex_sessions"]
    git = dataset["sources"]["git"]
    products = dataset["sources"]["generated_products"]["summary"]
    proofs = dataset["sources"]["verification"]
    assert sessions["summary"]["session_count"] > 0
    assert sessions["summary"]["token_totals"]["total_tokens"] > 0
    assert sessions["summary"]["event_totals"]["function_call"] > 0
    assert git["summary"]["commit_count"] > 0
    assert products["product_count"] > 0
    assert products["acceptance_passed"] == products["acceptance_cases"]
    assert proofs["proofs_passed"] == proofs["proof_count"]


def test_session_projection_excludes_private_payloads():
    text = DATASET.read_text(encoding="utf-8")
    forbidden_keys = (
        '"content"',
        '"cwd"',
        '"environment"',
        '"prompt"',
        '"response"',
        '"session_id"',
        '"tool_arguments"',
        '"tool_output"',
    )
    assert not any(key in text for key in forbidden_keys)


def test_committed_dataset_is_canonical_json():
    dataset = load(DATASET)
    assert DATASET.read_bytes() == canonical_bytes(dataset) + b"\n"


def test_same_frozen_inputs_generate_identical_bytes(tmp_path):
    sessions = tmp_path / "sessions"
    sessions.mkdir()
    project = tmp_path / "project"
    project.mkdir()
    event_path = sessions / "session.jsonl"
    events = [
        {
            "timestamp": "2026-01-01T00:00:00Z",
            "type": "session_meta",
            "payload": {
                "cwd": str(project),
                "session_id": "private-session",
                "model_provider": "fixture-provider",
            },
        },
        {
            "timestamp": "2026-01-01T00:00:01Z",
            "type": "event_msg",
            "payload": {"type": "user_message", "message": "private fixture text"},
        },
        {
            "timestamp": "2026-01-01T00:00:02Z",
            "type": "event_msg",
            "payload": {
                "type": "token_count",
                "info": {"total_token_usage": {"input_tokens": 10, "total_tokens": 12}},
            },
        },
        {
            "timestamp": "2027-01-01T00:00:00Z",
            "type": "event_msg",
            "payload": {"type": "user_message", "message": "excluded after cutoff"},
        },
    ]
    event_path.write_text(
        "".join(json.dumps(event) + "\n" for event in events), encoding="utf-8"
    )
    cutoff = parse_time("2026-06-01T00:00:00Z").astimezone(timezone.utc)
    first = sessions_projection(sessions, cutoff, (project.resolve(),))
    second = sessions_projection(sessions, cutoff, (project.resolve(),))
    assert canonical_bytes(first) == canonical_bytes(second)
    assert first["summary"]["session_count"] == 1
    assert first["summary"]["token_totals"]["total_tokens"] == 12
    assert b"private fixture text" not in canonical_bytes(first)
