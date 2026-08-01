"""Behavioral proof for the canonical GitHub corpus snapshot contract."""

from __future__ import annotations

import ast
import copy
import inspect
import json
from pathlib import Path

from unified.boundary import inward
from unified.github_corpus import (
    SNAPSHOT_STATUSES,
    canonical_request_payload,
    identify_request,
    identify_snapshot,
)


ROOT = Path(__file__).resolve().parents[1]
SEED_ROOT = ROOT / "seed" / "github_corpus"
EXAMPLE = json.loads((SEED_ROOT / "replay.example.json").read_text())
VECTORS = json.loads((SEED_ROOT / "CONTRACT_VECTORS.json").read_text())


def _snapshot(document=EXAMPLE):
    return identify_snapshot(inward({"snapshot": copy.deepcopy(document)}))


def _valid_status(status, reason, pages=None):
    document = copy.deepcopy(EXAMPLE)
    document["status"] = status
    document["completion"]["reason"] = reason
    if pages is not None:
        document["pages"] = pages
        document["completion"]["records_observed"] = sum(
            len(page["records"]) for page in pages
        )
    return _snapshot(document)


def test_schema_vectors_and_public_parts_are_frozen():
    request_schema = json.loads((SEED_ROOT / "REQUEST_SCHEMA.json").read_text())
    snapshot_schema = json.loads((SEED_ROOT / "SNAPSHOT_SCHEMA.json").read_text())
    assert request_schema["title"] == "Unified Code GitHub corpus acquisition request"
    assert snapshot_schema["title"] == "Unified Code canonical GitHub corpus snapshot"
    assert len(inspect.signature(identify_request).parameters) == 1
    assert len(inspect.signature(identify_snapshot).parameters) == 1

    result = _snapshot()
    assert result["state"] == "valid"
    assert result["value"]["request_sha256"] == VECTORS["expected"]["request_sha256"]
    assert result["value"]["snapshot_sha256"] == VECTORS["expected"]["snapshot_sha256"]
    assert result["value"]["evidence_sha256"] == VECTORS["expected"]["evidence_sha256"]
    assert result["evidence"] == ("boundary:inward", "corpus:snapshot-identified")


def test_dictionary_page_and_record_order_do_not_change_identity():
    baseline = _snapshot()
    reordered = copy.deepcopy(EXAMPLE)
    reordered = dict(reversed(list(reordered.items())))
    reordered["request"] = dict(reversed(list(reordered["request"].items())))
    reordered["pages"] = list(reversed(reordered["pages"]))
    for page in reordered["pages"]:
        page["records"] = list(reversed(page["records"]))
        for record in page["records"]:
            record["payload"] = dict(reversed(list(record["payload"].items())))
    result = _snapshot(reordered)
    assert result["state"] == "valid"
    assert result["value"]["snapshot_sha256"] == baseline["value"]["snapshot_sha256"]
    assert result["value"]["request_sha256"] == baseline["value"]["request_sha256"]


def test_request_authority_coordinates_cannot_collide():
    baseline = _snapshot()["value"]["snapshot_sha256"]
    mutations = {
        "query": "topic:todo archived:false",
        "initial_cursor": "cursor:first",
        "api_version": "2027-01-01",
        "visibility_scope": "organization-public",
    }
    identities = []
    for field, value in mutations.items():
        document = copy.deepcopy(EXAMPLE)
        document["request"][field] = value
        if field == "initial_cursor":
            document["pages"][0]["request_cursor"] = value
        result = _snapshot(document)
        assert result["state"] == "valid", (field, result)
        identities.append(result["value"]["snapshot_sha256"])
    assert baseline not in identities
    assert len(identities) == len(set(identities))

    cursor_document = copy.deepcopy(EXAMPLE)
    cursor_document["pages"][0]["next_cursor"] = "cursor:replacement"
    cursor_document["pages"][1]["request_cursor"] = "cursor:replacement"
    cursor_result = _snapshot(cursor_document)
    assert cursor_result["state"] == "valid"
    assert cursor_result["value"]["snapshot_sha256"] != baseline


def test_statuses_are_distinct_domain_data_inside_valid_things():
    pages = copy.deepcopy(EXAMPLE["pages"])
    partial = _valid_status("partial", "page_limit", pages)
    limited = _valid_status("rate_limited", "rate_limit", pages)
    unavailable = _valid_status("unavailable", "provider_unavailable", [])
    complete = _snapshot()
    results = [complete, partial, limited, unavailable]
    assert {result["value"]["status"] for result in results} == SNAPSHOT_STATUSES
    assert {result["state"] for result in results} == {"valid"}
    assert len({result["value"]["snapshot_sha256"] for result in results}) == 4
    assert all(result["value"]["ticket"] is None for result in results)


def test_time_duration_and_mode_are_evidence_not_semantic_identity():
    replay = _snapshot()
    live_document = copy.deepcopy(EXAMPLE)
    live_document["evidence"] = {
        **live_document["evidence"],
        "acquisition_mode": "live",
        "observed_at": "2026-08-02T20:30:00Z",
        "duration_ns": 9999999,
    }
    live = _snapshot(live_document)
    assert live["value"]["snapshot_sha256"] == replay["value"]["snapshot_sha256"]
    assert live["value"]["request_sha256"] == replay["value"]["request_sha256"]
    assert live["value"]["evidence_sha256"] != replay["value"]["evidence_sha256"]
    assert live["value"]["acquisition_mode"] == "live"
    assert replay["value"]["acquisition_mode"] == "replay"

    reordered_attempts = copy.deepcopy(EXAMPLE)
    reordered_attempts["evidence"]["attempts"].reverse()
    reordered = _snapshot(reordered_attempts)
    assert (
        reordered["value"]["snapshot_sha256"]
        == replay["value"]["snapshot_sha256"]
    )
    assert reordered["value"]["evidence_sha256"] != replay["value"]["evidence_sha256"]


def test_invalid_mutations_have_exact_errors_no_ticket_and_recover():
    mutations = []

    duplicate = copy.deepcopy(EXAMPLE)
    duplicate["pages"][0]["records"].append(
        copy.deepcopy(duplicate["pages"][0]["records"][0])
    )
    duplicate["completion"]["records_observed"] += 1
    mutations.append((duplicate, "snapshot:duplicate-record-identity"))

    chain = copy.deepcopy(EXAMPLE)
    chain["pages"][1]["request_cursor"] = "cursor:wrong"
    mutations.append((chain, "snapshot:cursor-chain"))

    count = copy.deepcopy(EXAMPLE)
    count["completion"]["records_observed"] = 4
    mutations.append((count, "snapshot:records-observed"))

    terminal = copy.deepcopy(EXAMPLE)
    terminal["pages"][-1]["next_cursor"] = "cursor:more"
    mutations.append((terminal, "snapshot:complete-terminal-cursor"))

    unavailable = copy.deepcopy(EXAMPLE)
    unavailable["status"] = "unavailable"
    unavailable["completion"]["reason"] = "provider_unavailable"
    mutations.append((unavailable, "snapshot:unavailable-pages"))

    query = copy.deepcopy(EXAMPLE)
    query["request"]["query"] = ""
    mutations.append((query, "request:query"))

    observed_at = copy.deepcopy(EXAMPLE)
    observed_at["evidence"]["observed_at"] = "host-local-time"
    mutations.append((observed_at, "evidence:observed-at"))

    attempt = copy.deepcopy(EXAMPLE)
    attempt["evidence"]["attempts"][0]["outcome"] = "guessed"
    mutations.append((attempt, "evidence:attempt:0:outcome"))

    for document, expected_error in mutations:
        first = _snapshot(document)
        second = _snapshot(document)
        assert first == second
        assert first["state"] == "invalid"
        assert expected_error in first["value"]["errors"]
        assert first["value"]["ticket"] is None
        assert "snapshot_sha256" not in first["value"]
        assert "corpus:snapshot-identified" not in first["evidence"]
        assert _snapshot()["state"] == "valid"

    assert set(VECTORS["invalid_mutations"]).issubset(
        {expected for _, expected in mutations}
    )


def test_public_parts_delegate_control_flow_to_named_audited_primitives():
    for part in (identify_request, identify_snapshot):
        tree = ast.parse(inspect.getsource(part))
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

    module = ast.parse((ROOT / "unified" / "github_corpus.py").read_text())
    for function in (
        node
        for node in ast.walk(module)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ):
        physical = [
            node
            for node in ast.walk(function)
            if isinstance(node, forbidden + (ast.IfExp, ast.BoolOp))
        ]
        assert not physical or function.name.startswith("audited_"), function.name


def test_contract_has_no_network_or_ticket_side_effects():
    source = (ROOT / "unified" / "github_corpus.py").read_text()
    tree = ast.parse(source)
    imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imports |= {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    assert not ({"http", "requests", "socket", "urllib"} & imports)
    result = _snapshot()
    assert result["value"]["ticket"] is None

    generic_compiler = "\n".join(
        path.read_text()
        for path in (ROOT / "unified" / "generator").glob("*.py")
    )
    assert "github_corpus" not in generic_compiler


def test_request_part_matches_snapshot_request_identity():
    request = identify_request(inward({"request": copy.deepcopy(EXAMPLE["request"])}))
    snapshot = _snapshot()
    assert request["state"] == "valid"
    assert request["value"]["request"] == canonical_request_payload(EXAMPLE["request"])
    assert request["value"]["request_sha256"] == snapshot["value"]["request_sha256"]
