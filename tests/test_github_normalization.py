"""Behavioral proof for deterministic GitHub repository normalization."""

from __future__ import annotations

import ast
import copy
import inspect
import json
from pathlib import Path

from unified.boundary import inward
from unified.github_corpus import canonical_snapshot_payload, replay_fixture_pack
from unified.github_normalization import normalize_repositories
from unified.machine.canonical import canonical_sha256


ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "seed" / "github_corpus"
FIXTURES = CORPUS / "fixtures"
NORMALIZATION = CORPUS / "normalization"
MANIFEST = json.loads((FIXTURES / "PACK.json").read_text())
EXPECTED = json.loads((NORMALIZATION / "EXPECTED.json").read_text())
VECTORS = json.loads((NORMALIZATION / "VECTORS.json").read_text())
PAGE_TEXTS = {
    page["path"]: (FIXTURES / page["path"]).read_text()
    for page in MANIFEST["pages"]
}


def _normalize(snapshot, snapshot_sha256):
    return normalize_repositories(
        inward(
            {
                "snapshot": copy.deepcopy(snapshot),
                "snapshot_sha256": snapshot_sha256,
            }
        )
    )


def _fixture_snapshot(page_texts=PAGE_TEXTS, manifest=MANIFEST):
    replayed = replay_fixture_pack(
        inward(
            {
                "fixture_pack": {
                    "manifest": copy.deepcopy(manifest),
                    "page_texts": copy.deepcopy(page_texts),
                }
            }
        )
    )
    assert replayed["state"] == "valid"
    return (
        replayed["value"]["semantic_snapshot"],
        replayed["value"]["snapshot_sha256"],
    )


def _vector_snapshot(records=VECTORS["records"]):
    raw = {
        "completion": {
            "reason": "exhausted",
            "records_observed": len(records),
        },
        "format_version": "UC-GITHUB-CORPUS-SNAPSHOT-1",
        "pages": [
            {
                "index": 0,
                "next_cursor": None,
                "raw_sha256": "0" * 64,
                "records": copy.deepcopy(records),
                "request_cursor": None,
            }
        ],
        "request": copy.deepcopy(MANIFEST["request"]),
        "status": "complete",
    }
    snapshot = canonical_snapshot_payload(raw)
    return snapshot, canonical_sha256(snapshot)


def _vector_result(records=VECTORS["records"]):
    return _normalize(*_vector_snapshot(records))


def _by_identity(items, field):
    return {item[field]: item for item in items}


def test_public_fixture_normalizes_without_claiming_application_boundaries():
    first = _normalize(*_fixture_snapshot())
    second = _normalize(*_fixture_snapshot())
    assert first == second
    assert first["state"] == "valid"
    assert first["evidence"] == (
        "boundary:inward",
        "normalization:completed",
    )
    expected = EXPECTED["fixture"]
    value = first["value"]
    assert value["normalization_sha256"] == expected["normalization_sha256"]
    assert len(value["repositories"]) == expected["repository_count"]
    assert len(value["candidate_groups"]) == expected["candidate_group_count"]
    assert len(value["unresolved"]) == expected["unresolved_count"]
    assert all(
        repository["candidate_boundary_status"] == "unresolved"
        for repository in value["repositories"]
    )
    assert all(
        group["selection_status"] == "single"
        for group in value["candidate_groups"]
    )
    assert value["relationship_edges"] == ()
    assert value["ticket"] is None


def test_golden_graph_preserves_every_declared_distinction():
    result = _vector_result()
    assert result["state"] == "valid"
    value = result["value"]
    expected = EXPECTED["vector"]
    assert value["snapshot_sha256"] == expected["snapshot_sha256"]
    assert value["normalization_sha256"] == expected["normalization_sha256"]

    repositories = _by_identity(value["repositories"], "repository_identity")
    states = {
        identity: [repository["availability"], repository["archive_state"]]
        for identity, repository in repositories.items()
        if identity in expected["repository_states"]
    }
    assert states == expected["repository_states"]
    renamed = repositories["github:repository:vector-renamed"]
    assert renamed["current_name"] == "contract/current-name"
    assert renamed["previous_names"] == ("contract/previous-name",)

    edges = {
        "|".join(
            (
                edge["source_identity"],
                edge["kind"],
                edge["target_identity"],
            )
        ): edge["status"]
        for edge in value["relationship_edges"]
    }
    assert edges == expected["relationship_statuses"]

    group_expected = expected["candidate_groups"][
        "explicit-fork-mirror-component"
    ]
    group = next(
        candidate
        for candidate in value["candidate_groups"]
        if candidate["candidate_group_identity"] == group_expected["identity"]
    )
    assert group["members"] == tuple(group_expected["members"])
    assert group["selection_status"] == group_expected["selection_status"]
    assert "canonical_repository_identity" not in group

    monorepo = repositories["github:repository:vector-monorepo"]
    assert {
        boundary["path"]: boundary["boundary_identity"]
        for boundary in monorepo["candidate_boundaries"]
    } == expected["monorepo_boundaries"]
    assert {
        item["reason"] for item in value["unresolved"]
    } == set(expected["unresolved_reasons"])


def test_record_dictionary_and_page_order_do_not_change_normalization():
    snapshot, snapshot_sha256 = _fixture_snapshot()
    baseline = _normalize(snapshot, snapshot_sha256)
    reordered = copy.deepcopy(snapshot)
    reordered = dict(reversed(tuple(reordered.items())))
    reordered["pages"] = list(reversed(reordered["pages"]))
    for page in reordered["pages"]:
        page["records"].reverse()
        for record in page["records"]:
            record["payload"] = dict(reversed(tuple(record["payload"].items())))
    result = _normalize(reordered, snapshot_sha256)
    assert result == baseline
    source = (ROOT / "unified" / "github_normalization.py").read_text()
    assert "pathlib" not in source
    assert "os.getcwd" not in source


def test_complete_and_explicitly_partial_snapshots_remain_distinct():
    complete_snapshot, complete_sha256 = _fixture_snapshot()
    complete = _normalize(complete_snapshot, complete_sha256)
    partial_snapshot = copy.deepcopy(complete_snapshot)
    partial_snapshot["status"] = "partial"
    partial_snapshot["completion"]["reason"] = "page_limit"
    partial_sha256 = canonical_sha256(partial_snapshot)
    partial = _normalize(partial_snapshot, partial_sha256)
    assert complete["state"] == partial["state"] == "valid"
    assert complete["value"]["snapshot_status"] == "complete"
    assert partial["value"]["snapshot_status"] == "partial"
    assert partial["value"]["snapshot_sha256"] != complete["value"]["snapshot_sha256"]
    assert (
        partial["value"]["normalization_sha256"]
        != complete["value"]["normalization_sha256"]
    )


def test_identity_and_relationship_mutations_change_only_declared_dependents():
    baseline = _vector_result()["value"]
    repositories_before = _by_identity(
        baseline["repositories"], "repository_identity"
    )

    name_records = copy.deepcopy(VECTORS["records"])
    renamed = next(
        record
        for record in name_records
        if record["source_identity"] == "github:repository:vector-renamed"
    )
    renamed["payload"]["full_name"] = "contract/new-current-name"
    name_result = _vector_result(name_records)["value"]
    repositories_after = _by_identity(
        name_result["repositories"], "repository_identity"
    )
    changed = {
        identity
        for identity in repositories_before
        if repositories_before[identity]["repository_sha256"]
        != repositories_after[identity]["repository_sha256"]
    }
    assert changed == {"github:repository:vector-renamed"}
    assert name_result["relationship_edges"] == baseline["relationship_edges"]
    assert name_result["candidate_groups"] == baseline["candidate_groups"]

    relation_records = copy.deepcopy(VECTORS["records"])
    mirror = next(
        record
        for record in relation_records
        if record["source_identity"] == "github:repository:vector-mirror"
    )
    mirror["payload"]["relationships"][0]["target_identity"] = (
        "github:repository:vector-renamed"
    )
    relation_result = _vector_result(relation_records)["value"]
    assert relation_result["repositories"] == baseline["repositories"]
    unchanged_edges = {
        edge["relationship_sha256"]
        for edge in baseline["relationship_edges"]
        if edge["source_identity"] != "github:repository:vector-mirror"
    }
    assert unchanged_edges.issubset(
        {
            edge["relationship_sha256"]
            for edge in relation_result["relationship_edges"]
        }
    )
    assert relation_result["candidate_groups"] != baseline["candidate_groups"]


def test_invalid_declarations_fail_without_ticket_and_recover():
    mutations = []
    bad_kind = copy.deepcopy(VECTORS["records"])
    bad_kind[1]["payload"]["relationships"][0]["kind"] = "similar_to"
    mutations.append((bad_kind, "relationship:0:kind"))

    traversal = copy.deepcopy(VECTORS["records"])
    traversal[-1]["payload"]["candidate_boundaries"] = ["../foreign"]
    mutations.append((traversal, "candidate-boundary:0:path"))

    duplicate = copy.deepcopy(VECTORS["records"])
    duplicate.append(copy.deepcopy(duplicate[0]))
    mutations.append((duplicate, "normalization:duplicate-repository-identity"))

    for records, expected_error in mutations:
        first = _vector_result(records)
        second = _vector_result(records)
        assert first == second
        assert first["state"] == "invalid"
        assert any(
            expected_error in error for error in first["value"]["errors"]
        )
        assert first["value"]["ticket"] is None
        assert "normalization_sha256" not in first["value"]
        assert "normalization:completed" not in first["evidence"]
        assert _vector_result()["state"] == "valid"


def test_public_part_and_permanent_surface_remain_generic_and_offline():
    assert len(inspect.signature(normalize_repositories).parameters) == 1
    tree = ast.parse(inspect.getsource(normalize_repositories))
    forbidden = (
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
    assert not [node for node in ast.walk(tree) if isinstance(node, forbidden)]

    source = (ROOT / "unified" / "github_normalization.py").read_text()
    assert not any(
        term in source
        for term in (
            "FluxCalc",
            "PONG-GAME",
            "todoism",
            "difflib",
            "similarity",
            "requests",
            "urllib",
            "socket",
        )
    )
    compiler = "\n".join(
        path.read_text() for path in (ROOT / "unified" / "generator").glob("*.py")
    )
    assert "github_normalization" not in compiler
