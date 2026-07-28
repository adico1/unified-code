"""Executable proofs for projection and root fixed-point convergence."""

from __future__ import annotations

import copy
import json

import pytest

from unified.boundary import inward
from unified.convergence import (
    FORMAT_VERSION,
    _canonical,
    _normalized_authority,
    _sha,
    run_convergence,
    verify_root_convergence,
)
from unified.generator.cli import _parse_argv


def authority():
    return {
        "components": [
            {
                "id": "root-seed",
                "identity": "uc://root@TEN-1",
                "content_sha256": "1" * 64,
            },
            {
                "id": "compiler-law",
                "identity": "uc://compiler/root@1",
                "content_sha256": "2" * 64,
            },
            {
                "id": "canonical-boilerplate",
                "identity": "uc://boilerplate/root@1",
                "content_sha256": "3" * 64,
            },
        ],
        "watcher_registry": [
            {
                "id": "cli-watcher",
                "depths": [4, 8],
                "observes": "cli projection and shared authority",
                "required_evidence": ["projection:cli", "authority:shared"],
            },
            {
                "id": "gui-watcher",
                "depths": [6, 10],
                "observes": "gui projection and manifestation boundary",
                "required_evidence": ["projection:gui", "boundary:manifested"],
            },
        ],
    }


def structure(authority_value=None, cli="stable", gui="stable"):
    authority_value = authority_value or authority()
    bundle = _sha(_normalized_authority(authority_value))
    return {
        "authority_bundle_sha256": bundle,
        "depths": list(range(1, 11)),
        "projections": {
            "cli": {
                "authority_bundle_sha256": bundle,
                "semantic": {"surface": cli},
            },
            "gui": {
                "authority_bundle_sha256": bundle,
                "semantic": {"surface": gui},
            },
        },
        "watchers": [
            {
                "id": "cli-watcher",
                "status": "resolved",
                "evidence": ["projection:cli", "authority:shared"],
            },
            {
                "id": "gui-watcher",
                "status": "resolved",
                "evidence": ["projection:gui", "boundary:manifested"],
            },
        ],
        "letters": [
            {"id": "cli.command", "verdict": "valid"},
            {"id": "gui.control", "verdict": "valid"},
        ],
        "laws": [
            {"id": "Standard-Ten", "status": "pass"},
            {"id": "L1-L13", "status": "pass"},
        ],
    }


def audit(sequence):
    return {
        "ordered_verdicts": ["generation:" + str(sequence), "watchers:resolved"],
        "measurements": {"duration_ns": sequence},
        "environment_identity": {
            "host": "proof-" + str(sequence),
            "temporary_path": "/tmp/proof-" + str(sequence),
        },
    }


def generation(semantic, sequence):
    return {"semantic_structure": semantic, "audit": audit(sequence)}


def trace(*structures, authority_value=None, bound=8):
    authority_value = authority_value or authority()
    return {
        "format_version": FORMAT_VERSION,
        "generation_bound": bound,
        "authority": authority_value,
        "generations": [
            generation(copy.deepcopy(semantic), index)
            for index, semantic in enumerate(structures, 1)
        ],
    }


def verify(value):
    return verify_root_convergence(inward(value))


def test_root_fixed_point_separates_semantic_and_audit_hashes():
    semantic = structure()
    result = verify(trace(semantic, semantic))
    assert result["state"] == "valid"
    assert result["value"]["verdict"] == "bilima"
    assert result["value"]["root_fixed_point"] is True
    assert result["value"]["projection_fixed_points"] == {
        "cli": True,
        "gui": True,
    }
    assert result["value"]["structure_hashes"][0] == result["value"][
        "structure_hashes"
    ][1]
    assert result["value"]["evidence_hashes"][0] != result["value"][
        "evidence_hashes"
    ][1]
    assert result["evidence"][-3:] == (
        "convergence:bilima",
        "manifestation:gila",
        "boundary:outward",
    )


def test_projection_can_converge_while_root_remains_pending():
    result = verify(trace(structure(gui="first"), structure(gui="second")))
    assert result["state"] == "formed"
    assert result["value"]["error"] is None
    assert result["value"]["root_fixed_point"] is False
    assert result["value"]["projection_fixed_points"] == {
        "cli": True,
        "gui": False,
    }
    assert result["evidence"][-1] == "convergence:pending"


def test_unresolved_watcher_at_fixed_structure_is_invalid():
    semantic = structure()
    semantic["watchers"][1]["status"] = "unresolved"
    result = verify(trace(semantic, semantic))
    assert result["state"] == "invalid"
    assert result["value"]["error"] == "unresolved-distinction"
    assert result["evidence"][-1] == "convergence:unresolved-distinction"


def test_missing_watcher_is_an_unresolved_distinction():
    semantic = structure()
    semantic["watchers"].pop()
    result = verify(trace(semantic, semantic))
    assert result["state"] == "invalid"
    assert result["value"]["error"] == "unresolved-distinction"


def test_non_adjacent_repeated_structure_is_an_unfolding_cycle():
    first = structure(gui="first")
    second = structure(gui="second")
    result = verify(trace(first, second, first))
    assert result["state"] == "invalid"
    assert result["value"]["error"] == "unfolding-cycle"
    assert result["evidence"][-1] == "convergence:unfolding-cycle"
    repeated_after_cycle = verify(trace(first, second, first, first))
    assert repeated_after_cycle["state"] == "invalid"
    assert repeated_after_cycle["value"]["error"] == "unfolding-cycle"


def test_generation_bound_is_bilima_limit():
    semantic = structure()
    result = verify(trace(semantic, semantic, semantic, bound=2))
    assert result["state"] == "invalid"
    assert result["value"]["error"] == "bilima-limit"
    assert result["evidence"][-1] == "convergence:bilima-limit"


def test_projection_cannot_cite_a_divided_authority():
    semantic = structure()
    semantic["projections"]["gui"]["authority_bundle_sha256"] = "f" * 64
    result = verify(trace(semantic))
    assert result["state"] == "invalid"
    assert result["value"]["error"] == "divided-authority"


def test_authority_identity_is_hashed_even_when_content_is_equal():
    first_authority = authority()
    second_authority = copy.deepcopy(first_authority)
    second_authority["components"][0]["identity"] = "uc://root-renamed@TEN-1"
    assert first_authority["components"][0]["content_sha256"] == second_authority[
        "components"
    ][0]["content_sha256"]
    assert _sha(_normalized_authority(first_authority)) != _sha(
        _normalized_authority(second_authority)
    )
    first = verify(trace(structure(first_authority), structure(first_authority), authority_value=first_authority))
    second = verify(
        trace(
            structure(second_authority),
            structure(second_authority),
            authority_value=second_authority,
        )
    )
    assert first["state"] == second["state"] == "valid"
    assert first["value"]["authority_bundle_sha256"] != second["value"][
        "authority_bundle_sha256"
    ]


@pytest.mark.parametrize(
    ("verdict", "error"),
    [
        ("missing", "invalid-letter"),
        ("foreign", "invalid-letter"),
        ("duplicate", "invalid-letter"),
        ("misplaced", "invalid-letter"),
        ("unresolved", "invalid-letter"),
    ],
)
def test_only_valid_letter_verdict_permits_manifestation(verdict, error):
    semantic = structure()
    semantic["letters"][0]["verdict"] = verdict
    result = verify(trace(semantic, semantic))
    assert result["state"] == "invalid"
    assert result["value"]["error"] == error
    assert "manifestation:gila" not in result["evidence"]


def test_exactly_ten_ordered_depths_are_required():
    semantic = structure()
    semantic["depths"].append(11)
    result = verify(trace(semantic))
    assert result["state"] == "invalid"
    assert result["value"]["error"] == "ten-depth-boundary"


def test_failed_law_blocks_bilima_and_gila():
    semantic = structure()
    semantic["laws"][0]["status"] = "fail"
    result = verify(trace(semantic, semantic))
    assert result["state"] == "invalid"
    assert result["value"]["error"] == "law-failed"
    assert "manifestation:gila" not in result["evidence"]


def test_watcher_registry_rejects_creator_behavior_and_duplicates():
    authority_value = authority()
    authority_value["watcher_registry"][0]["generates"] = "application behavior"
    result = verify(trace(structure(), authority_value=authority_value))
    assert result["state"] == "invalid"
    assert result["value"]["error"] == "watcher-shape"
    duplicate = authority()
    duplicate["watcher_registry"][1]["id"] = "cli-watcher"
    result = verify(trace(structure(), authority_value=duplicate))
    assert result["state"] == "invalid"
    assert result["value"]["error"] == "watcher-registry"


def test_canonical_order_does_not_change_structure_identity():
    semantic = structure()
    reordered = json.loads(_canonical(semantic), object_pairs_hook=lambda pairs: dict(reversed(pairs)))
    assert _sha(semantic) == _sha(reordered)
    reordered_lists = copy.deepcopy(semantic)
    reordered_lists["watchers"].reverse()
    reordered_lists["letters"].reverse()
    reordered_lists["laws"].reverse()
    first = verify(trace(semantic, semantic))
    second = verify(trace(reordered_lists, reordered_lists))
    assert first["value"]["structure_hash"] == second["value"]["structure_hash"]
    reordered_authority = authority()
    reordered_authority["components"].reverse()
    reordered_authority["watcher_registry"].reverse()
    assert _sha(_normalized_authority(authority())) == _sha(
        _normalized_authority(reordered_authority)
    )


def test_cli_reads_and_verifies_trace(tmp_path):
    semantic = structure()
    path = tmp_path / "trace.json"
    path.write_bytes(_canonical(trace(semantic, semantic)))
    parsed = _parse_argv(["converge", str(path)])
    assert parsed == {"command": "converge", "trace_path": str(path)}
    result = run_convergence(inward(parsed))
    assert result["state"] == "valid"
    assert result["value"]["verdict"] == "bilima"
    missing = run_convergence(inward({"trace_path": str(tmp_path / "missing.json")}))
    assert missing["state"] == "invalid"
    assert missing["value"]["error"] == "convergence-read:FileNotFoundError"
    assert missing["evidence"][-1] == "boundary:convergence-read-rejected"
    usage = run_convergence(inward({"error": "usage-converge"}))
    assert usage["value"]["error"] == "usage-converge"


def test_public_parts_are_one_thing_in_one_thing_out():
    assert verify_root_convergence.__code__.co_argcount == 1
    assert run_convergence.__code__.co_argcount == 1
    malformed = verify_root_convergence({"value": {}})
    assert malformed["state"] == "invalid"
    assert malformed["value"]["error"] == "not-a-thing"
