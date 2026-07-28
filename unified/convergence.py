"""Deterministic root and projection convergence verification.

Watchers observe, the verifier judges, the creator generates, and boundaries
manifest.  This module verifies an unfolding trace; it never generates or
repairs application behavior.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .boundary import outward
from .thing import is_thing

FORMAT_VERSION = "UC-ROOT-CONVERGENCE-1"
DEPTHS = tuple(range(1, 11))
LETTER_VERDICTS = frozenset(
    ("valid", "missing", "foreign", "duplicate", "misplaced", "unresolved")
)
WATCHER_STATUSES = frozenset(("resolved", "unresolved"))
LAW_STATUSES = frozenset(("pass", "fail"))


def _canonical(value):
    return (
        json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        + "\n"
    ).encode("utf-8")


def _sha(value):
    return hashlib.sha256(_canonical(value)).hexdigest()


def _normalized_authority(authority):
    return {
        "components": sorted(authority["components"], key=lambda item: item["id"]),
        "watcher_registry": [
            {
                **watcher,
                "depths": sorted(watcher["depths"]),
                "required_evidence": sorted(watcher["required_evidence"]),
            }
            for watcher in sorted(
                authority["watcher_registry"], key=lambda item: item["id"]
            )
        ],
    }


def _normalized_structure(structure):
    return {
        **structure,
        "watchers": sorted(structure["watchers"], key=lambda item: item["id"]),
        "letters": sorted(structure["letters"], key=lambda item: item["id"]),
        "laws": sorted(structure["laws"], key=lambda item: item["id"]),
    }


def _is_sha256(value):
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _invalid(thing, value, error, mark):
    return {
        **thing,
        "value": {**value, "error": error, "verdict": "invalid"},
        "evidence": (*thing["evidence"], mark),
        "state": "invalid",
    }


def _formed(thing, value, mark):
    return {
        **thing,
        "value": {**value, "error": None, "verdict": "pending"},
        "evidence": (*thing["evidence"], mark),
        "state": "formed",
    }


def _valid(thing, value):
    return outward(
        {
            **thing,
            "value": {**value, "error": None, "verdict": "bilima"},
            "evidence": (*thing["evidence"], "convergence:bilima", "manifestation:gila"),
            "state": "valid",
        }
    )


def _ids_once(items):
    ids = [item.get("id") for item in items if isinstance(item, dict)]
    return len(ids) == len(items) and len(ids) == len(set(ids)) and all(ids)


def _authority_error(authority):
    if not isinstance(authority, dict) or set(authority) != {
        "components",
        "watcher_registry",
    }:
        return "authority-shape"
    components = authority["components"]
    watchers = authority["watcher_registry"]
    if not isinstance(components, list) or not components or not _ids_once(components):
        return "authority-components"
    if not isinstance(watchers, list) or not watchers or not _ids_once(watchers):
        return "watcher-registry"
    for component in components:
        if set(component) != {"id", "identity", "content_sha256"}:
            return "authority-component-shape"
        if not all(isinstance(component[key], str) and component[key] for key in component):
            return "authority-component-value"
        if not _is_sha256(component["content_sha256"]):
            return "authority-component-hash"
    for watcher in watchers:
        if set(watcher) != {"id", "depths", "observes", "required_evidence"}:
            return "watcher-shape"
        if not isinstance(watcher["depths"], list) or not watcher["depths"]:
            return "watcher-depths"
        if not set(watcher["depths"]).issubset(DEPTHS):
            return "watcher-depths"
        if not isinstance(watcher["observes"], str) or not watcher["observes"]:
            return "watcher-observation"
        if not isinstance(watcher["required_evidence"], list):
            return "watcher-evidence"
    return None


def _structure_error(structure, authority_bundle_sha256, watcher_ids):
    required = {"authority_bundle_sha256", "depths", "projections", "watchers", "letters", "laws"}
    if not isinstance(structure, dict) or set(structure) != required:
        return "semantic-structure-shape"
    if structure["authority_bundle_sha256"] != authority_bundle_sha256:
        return "divided-authority"
    if tuple(structure["depths"]) != DEPTHS:
        return "ten-depth-boundary"
    projections = structure["projections"]
    if not isinstance(projections, dict) or not projections:
        return "projection-shape"
    if any(
        not isinstance(projection, dict)
        or set(projection) != {"authority_bundle_sha256", "semantic"}
        or projection["authority_bundle_sha256"] != authority_bundle_sha256
        for projection in projections.values()
    ):
        return "divided-authority"
    watchers = structure["watchers"]
    if not isinstance(watchers, list) or not _ids_once(watchers):
        return "watcher-results"
    if {watcher["id"] for watcher in watchers} != watcher_ids:
        return "unresolved-distinction"
    if any(
        set(watcher) != {"id", "status", "evidence"}
        or watcher["status"] not in WATCHER_STATUSES
        or not isinstance(watcher["evidence"], list)
        for watcher in watchers
    ):
        return "watcher-results"
    letters = structure["letters"]
    if not isinstance(letters, list) or not _ids_once(letters):
        return "letter-results"
    if any(
        set(letter) != {"id", "verdict"}
        or letter["verdict"] not in LETTER_VERDICTS
        for letter in letters
    ):
        return "letter-results"
    laws = structure["laws"]
    if not isinstance(laws, list) or not laws or not _ids_once(laws):
        return "law-results"
    if any(
        set(law) != {"id", "status"} or law["status"] not in LAW_STATUSES
        for law in laws
    ):
        return "law-results"
    return None


def _audit_error(audit):
    if not isinstance(audit, dict) or set(audit) != {
        "ordered_verdicts",
        "measurements",
        "environment_identity",
    }:
        return "audit-shape"
    if not isinstance(audit["ordered_verdicts"], list):
        return "audit-verdicts"
    if not isinstance(audit["measurements"], dict):
        return "audit-measurements"
    if not isinstance(audit["environment_identity"], dict):
        return "audit-environment"
    return None


def verify_root_convergence(thing):
    """Judge projection and root fixed points from one canonical Thing."""
    if not is_thing(thing):
        return {
            "value": {"error": "not-a-thing", "verdict": "invalid"},
            "depths": (),
            "axes": (),
            "evidence": ("convergence:rejected",),
            "state": "invalid",
        }
    value = thing.get("value")
    if not isinstance(value, dict):
        return _invalid(thing, {}, "convergence-contract", "convergence:rejected")
    required = {"format_version", "generation_bound", "authority", "generations"}
    if set(value) != required or value.get("format_version") != FORMAT_VERSION:
        return _invalid(thing, value, "convergence-contract", "convergence:rejected")
    bound = value["generation_bound"]
    generations = value["generations"]
    if not isinstance(bound, int) or isinstance(bound, bool) or bound < 1:
        return _invalid(thing, value, "convergence-contract", "convergence:rejected")
    if not isinstance(generations, list) or not generations:
        return _invalid(thing, value, "convergence-contract", "convergence:rejected")
    if len(generations) > bound:
        return _invalid(thing, value, "bilima-limit", "convergence:bilima-limit")
    authority_error = _authority_error(value["authority"])
    if authority_error:
        return _invalid(thing, value, authority_error, "convergence:authority-rejected")

    authority_bundle_sha256 = _sha(_normalized_authority(value["authority"]))
    watcher_ids = {
        watcher["id"] for watcher in value["authority"]["watcher_registry"]
    }
    structure_hashes = []
    evidence_hashes = []
    projection_hashes = []
    for generation in generations:
        if not isinstance(generation, dict) or set(generation) != {
            "semantic_structure",
            "audit",
        }:
            return _invalid(
                thing, value, "generation-shape", "convergence:generation-rejected"
            )
        structure = generation["semantic_structure"]
        structure_error = _structure_error(
            structure, authority_bundle_sha256, watcher_ids
        )
        if structure_error:
            return _invalid(
                thing,
                value,
                structure_error,
                "convergence:" + structure_error,
            )
        audit_error = _audit_error(generation["audit"])
        if audit_error:
            return _invalid(thing, value, audit_error, "convergence:audit-rejected")
        structure_hash = _sha(_normalized_structure(structure))
        structure_hashes.append(structure_hash)
        projection_hashes.append(
            {
                projection_id: _sha(projection)
                for projection_id, projection in sorted(
                    structure["projections"].items()
                )
            }
        )
        evidence_hashes.append(
            _sha(
                {
                    "structure_hash": structure_hash,
                    **generation["audit"],
                }
            )
        )

    latest_structure = generations[-1]["semantic_structure"]
    latest_hash = structure_hashes[-1]
    projection_ids = set(projection_hashes[-1])
    projection_fixed_points = {
        projection_id: len(projection_hashes) >= 2
        and projection_ids == set(projection_hashes[-2])
        and projection_hashes[-1][projection_id]
        == projection_hashes[-2][projection_id]
        for projection_id in sorted(projection_ids)
    }
    result = {
        **value,
        "authority_bundle_sha256": authority_bundle_sha256,
        "structure_hashes": structure_hashes,
        "structure_hash": latest_hash,
        "evidence_hashes": evidence_hashes,
        "projection_fixed_points": projection_fixed_points,
        "root_fixed_point": len(structure_hashes) >= 2
        and structure_hashes[-1] == structure_hashes[-2],
    }
    cycle_detected = any(
        current in structure_hashes[: index - 1]
        and current != structure_hashes[index - 1]
        for index, current in enumerate(structure_hashes)
        if index >= 2
    )
    if cycle_detected:
        return _invalid(
            thing, result, "unfolding-cycle", "convergence:unfolding-cycle"
        )
    if not result["root_fixed_point"]:
        return _formed(thing, result, "convergence:pending")
    if any(
        watcher["status"] != "resolved"
        for watcher in latest_structure["watchers"]
    ):
        return _invalid(
            thing,
            result,
            "unresolved-distinction",
            "convergence:unresolved-distinction",
        )
    if any(
        letter["verdict"] != "valid" for letter in latest_structure["letters"]
    ):
        return _invalid(
            thing, result, "invalid-letter", "convergence:letter-rejected"
        )
    if any(law["status"] != "pass" for law in latest_structure["laws"]):
        return _invalid(thing, result, "law-failed", "convergence:law-rejected")
    if not projection_fixed_points or not all(projection_fixed_points.values()):
        return _invalid(
            thing,
            result,
            "projection-not-converged",
            "convergence:projection-rejected",
        )
    return _valid(thing, result)


def inward_read_convergence(thing):
    """Named host boundary that reads one convergence trace."""
    if not is_thing(thing) or not isinstance(thing.get("value"), dict):
        return verify_root_convergence(thing)
    if thing["value"].get("error"):
        return _invalid(
            thing,
            thing["value"],
            thing["value"]["error"],
            "convergence:rejected",
        )
    path = Path(str(thing["value"].get("trace_path", "")))
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as error:
        return _invalid(
            thing,
            thing["value"],
            "convergence-read:" + type(error).__name__,
            "boundary:convergence-read-rejected",
        )
    return {
        **thing,
        "value": value,
        "evidence": (*thing["evidence"], "boundary:convergence-read"),
        "state": "formed",
    }


def run_convergence(thing):
    """Read, judge, and manifest one root-convergence trace."""
    admitted = inward_read_convergence(thing)
    return admitted if admitted.get("state") == "invalid" else verify_root_convergence(admitted)
