"""Traceable candidate-seed proof over the canonical offline corpus."""

from __future__ import annotations

import ast
import copy
import inspect
import json
from pathlib import Path

from unified.boundary import inward
from unified.generator.manifestation import validate_registry
from unified.github_candidates import (
    LETTER_VERDICTS,
    audited_observation_authority_primitive,
    extract_candidate_seeds,
)
from unified.github_corpus import replay_fixture_pack
from unified.github_normalization import normalize_repositories
from unified.machine.canonical import canonical_sha256


ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "seed" / "github_corpus"
FIXTURES = CORPUS / "fixtures"
PACK = json.loads((FIXTURES / "PACK.json").read_text())
OBSERVATIONS = json.loads(
    (CORPUS / "candidates" / "OBSERVATIONS.json").read_text()
)
EXPECTED = json.loads((CORPUS / "candidates" / "EXPECTED.json").read_text())
PAGE_TEXTS = {
    page["path"]: (FIXTURES / page["path"]).read_text()
    for page in PACK["pages"]
}


def _normalization():
    replayed = replay_fixture_pack(
        inward(
            {
                "fixture_pack": {
                    "manifest": copy.deepcopy(PACK),
                    "page_texts": copy.deepcopy(PAGE_TEXTS),
                }
            }
        )
    )
    assert replayed["state"] == "valid"
    return normalize_repositories(
        inward(
            {
                "snapshot": replayed["value"]["semantic_snapshot"],
                "snapshot_sha256": replayed["value"]["snapshot_sha256"],
            }
        )
    )["value"]


def _extract(observations=OBSERVATIONS, normalization=None):
    return extract_candidate_seeds(
        inward(
            {
                "normalization": copy.deepcopy(
                    normalization if normalization is not None else _normalization()
                ),
                "observations": copy.deepcopy(observations),
            }
        )
    )


def _by_repository(result):
    return {
        candidate["repository_identity"]: candidate
        for candidate in result["value"]["candidate_seeds"]
    }


def _rehash_normalization(normalization):
    semantic = {
        key: normalization[key]
        for key in (
            "candidate_groups",
            "normalization_version",
            "relationship_edges",
            "repositories",
            "snapshot_sha256",
            "snapshot_status",
            "unresolved",
        )
    }
    normalization["normalization_sha256"] = canonical_sha256(semantic)
    return normalization


def test_two_candidate_families_are_traceable_and_not_proven():
    first = _extract()
    second = _extract()
    assert first == second
    assert first["state"] == "valid"
    assert first["evidence"] == (
        "boundary:inward",
        "candidate-extraction:completed",
    )
    assert first["value"]["errors"] == ()
    assert first["value"]["ticket"] is None
    candidates = first["value"]["candidate_seeds"]
    assert first["value"]["normalization_sha256"] == EXPECTED[
        "normalization_sha256"
    ]
    assert first["value"]["observation_authority_sha256"] == EXPECTED[
        "observation_authority_sha256"
    ]
    assert first["value"]["extraction_sha256"] == EXPECTED["extraction_sha256"]
    assert [
        {
            "candidate_identity": candidate["candidate_identity"],
            "candidate_seed_sha256": candidate["candidate_seed_sha256"],
            "repository_identity": candidate["repository_identity"],
        }
        for candidate in candidates
    ] == EXPECTED["candidate_seeds"]
    assert len(candidates) == 2
    families = {
        semantic["value"]
        for candidate in candidates
        for semantic in candidate["semantics"]
        if semantic["letter_id"] == "family"
    }
    assert families == {"calculator", "task-list"}
    for candidate in candidates:
        assert candidate["catalog_status"] == "candidate"
        assert candidate["promotion_eligible"] is False
        assert candidate["human_review"] == {
            "reviewer": None,
            "status": "pending",
            "verdict": None,
        }
        evidence_ids = {
            evidence["evidence_id"] for evidence in candidate["traceability"]
        }
        assert all(
            semantic["evidence_ids"]
            and set(semantic["evidence_ids"]).issubset(evidence_ids)
            for semantic in candidate["semantics"]
        )
        assert all(
            len(evidence["source_sha256"]) == 64
            and evidence["revision"] in evidence["source_url"]
            for evidence in candidate["traceability"]
        )
        verdicts = {item["verdict"] for item in candidate["assessments"]}
        assert {"valid", "missing", "unresolved"}.issubset(verdicts)


def test_all_letter_verdicts_remain_distinct_and_evidence_bearing():
    observations = copy.deepcopy(OBSERVATIONS)
    candidate = observations["candidates"][0]
    evidence_id = candidate["boundary_evidence_ids"][0]
    candidate["assessments"].extend(
        (
            {
                "assessment_id": "vector-foreign",
                "evidence_ids": [evidence_id],
                "expected_role": "not-required",
                "letter_id": "vector-foreign-letter",
                "observed_role": "observed",
                "reason": "Observed evidence is outside the declared candidate boundary.",
                "value": "observed",
                "verdict": "foreign",
            },
            {
                "assessment_id": "vector-misplaced",
                "evidence_ids": [evidence_id],
                "expected_role": "expected-position",
                "letter_id": "vector-misplaced-letter",
                "observed_role": "different-position",
                "reason": "The evidenced letter occupies a different role.",
                "value": "observed",
                "verdict": "misplaced",
            },
            {
                "assessment_id": "vector-duplicate",
                "evidence_ids": [evidence_id],
                "expected_role": "family",
                "letter_id": "family",
                "observed_role": "family",
                "reason": "A second evidenced occurrence repeats the family role.",
                "value": "calculator",
                "verdict": "duplicate",
            },
        )
    )
    result = _extract(observations)
    assert result["state"] == "valid"
    verdicts = {
        assessment["verdict"]
        for candidate_seed in result["value"]["candidate_seeds"]
        for assessment in candidate_seed["assessments"]
    }
    assert verdicts == LETTER_VERDICTS


def test_declaration_order_and_repository_rename_need_no_extractor_change():
    baseline = _extract()
    reordered = copy.deepcopy(OBSERVATIONS)
    reordered["evidence"].reverse()
    reordered["candidates"].reverse()
    for candidate in reordered["candidates"]:
        candidate["assessments"].reverse()
        candidate["boundary_evidence_ids"].reverse()
    assert _extract(reordered) == baseline
    assert canonical_sha256(audited_observation_authority_primitive(reordered)) == (
        baseline["value"]["observation_authority_sha256"]
    )

    renamed_normalization = copy.deepcopy(_normalization())
    repository = next(
        item
        for item in renamed_normalization["repositories"]
        if item["repository_identity"] == "github:repository:452939204"
    )
    repository["current_name"] = "renamed-fixture/one"
    _rehash_normalization(renamed_normalization)
    renamed_observations = copy.deepcopy(OBSERVATIONS)
    renamed_observations["normalization_sha256"] = renamed_normalization[
        "normalization_sha256"
    ]
    renamed = _extract(renamed_observations, renamed_normalization)
    assert renamed["state"] == "valid"
    assert set(_by_repository(renamed)) == set(_by_repository(baseline))
    assert {
        key: value["candidate_identity"]
        for key, value in _by_repository(renamed).items()
    } == {
        key: value["candidate_identity"]
        for key, value in _by_repository(baseline).items()
    }


def test_invalid_authority_fails_deterministically_without_ticket_and_recovers():
    mutations = []
    wrong_normalization = copy.deepcopy(OBSERVATIONS)
    wrong_normalization["normalization_sha256"] = "0" * 64
    mutations.append((wrong_normalization, "candidate:observations:normalization-sha256"))

    foreign_evidence = copy.deepcopy(OBSERVATIONS)
    foreign_evidence["candidates"][0]["boundary_evidence_ids"] = [
        "todo-readme-family"
    ]
    mutations.append((foreign_evidence, "candidate:0:boundary-foreign-evidence"))

    unpinned = copy.deepcopy(OBSERVATIONS)
    unpinned["evidence"][0]["source_url"] = (
        "https://github.com/Futura-Py/FluxCalc/blob/main/docs/README.md"
    )
    mutations.append((unpinned, "candidate:evidence:0:unpinned-url"))

    for observations, expected in mutations:
        first = _extract(observations)
        second = _extract(observations)
        assert first == second
        assert first["state"] == "invalid"
        assert expected in first["value"]["errors"]
        assert first["value"]["ticket"] is None
        assert "candidate-extraction:completed" not in first["evidence"]
        assert "candidate_seeds" not in first["value"]
        assert _extract()["state"] == "valid"


def test_candidate_promotion_is_rejected_at_both_boundaries():
    result = _extract()
    registry_path = ROOT / "seed" / "registry.json"
    registry_bytes = registry_path.read_bytes()
    registry = json.loads(registry_bytes)
    registry["records"].append(result["value"]["candidate_seeds"][0])
    errors = validate_registry(registry)
    assert errors
    assert any("unknown:catalog_status" in error for error in errors)
    assert registry_path.read_bytes() == registry_bytes

    promoted = copy.deepcopy(OBSERVATIONS)
    promoted["candidates"][0]["human_review"] = {
        "reviewer": "reviewer:one",
        "status": "proven",
        "verdict": "accepted",
    }
    rejected = _extract(promoted)
    assert rejected["state"] == "invalid"
    assert "candidate:0:review-status" in rejected["value"]["errors"]
    assert rejected["value"]["ticket"] is None


def test_public_part_and_permanent_surfaces_are_generic_offline_and_one_thing():
    assert len(inspect.signature(extract_candidate_seeds).parameters) == 1
    tree = ast.parse(inspect.getsource(extract_candidate_seeds))
    forbidden_nodes = (
        ast.If,
        ast.For,
        ast.While,
        ast.Match,
        ast.Try,
        ast.ListComp,
        ast.SetComp,
        ast.DictComp,
        ast.GeneratorExp,
    )
    assert not [
        node for node in ast.walk(tree) if isinstance(node, forbidden_nodes)
    ]

    source = (ROOT / "unified" / "github_candidates.py").read_text()
    forbidden_terms = (
        "FluxCalc",
        "todoism",
        "calculator",
        "task-list",
        "task-search",
        "windows-10",
        "requests",
        "urllib",
        "socket",
        "subprocess",
        "importlib",
        "eval(",
        "exec(",
        "compile(",
    )
    assert not any(term in source for term in forbidden_terms)
    compiler = "\n".join(
        path.read_text() for path in (ROOT / "unified" / "generator").glob("*.py")
    )
    assert "github_candidates" not in compiler
