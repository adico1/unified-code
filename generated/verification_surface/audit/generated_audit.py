"""Generated Issue-7 audit tooling. Do not edit."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

EXPECTED = {'authorities': {'root_seed_sha256': '1dcaa5b6bb6f7744e8ca7be82586aa57939f2b3b5a9845ce2261d42139119f94', 'stage1_framework_sha256': '076e7876475fb3222e01229339e12bba47ada3b0a0c794bc935abf643e135acf', 'stage1_uem_sha256': 'c1b1979da0e7e228f523a5390abf7ff2aba87913c31af6d0187be7e61826994b', 'uem_surface_sha256': 'ef231c4615dd4fe9824e95f84e6e5ff9f202e152a3c5da4ff2bb910802ff5881', 'proof_graph_sha256': '53764eea58c6a6e2494d0b6ce01bfcd9d7173347504e6124c375ed4d5006ca79', 'source_documents_sha256': '0152fad2682efe816bb4550a43b4a5af962e65bd28006a3fa1499922a8b77166', 'synthetic_obligation_sha256': 'd7d05cad86d964536d97bb686091984034c3d471305053d22d2dd17fbb1cda3d'}, 'depths': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 'thing_states': ['unknown', 'absent', 'false', 'formed', 'valid', 'invalid'], 'events': ['verification-generation.requested', 'authorities.resolved', 'contracts.projected', 'tests.generated', 'mutations.generated', 'goldens.generated', 'documentation.generated', 'audits.generated', 'projections.cross-checked', 'fixed-point.requested', 'fixed-point.completed', 'verification.requested', 'verification.completed'], 'generation_bound': 10, 'fact_count': 75, 'proof_nodes': ['repository-tests', 'stage0-contract', 'stage1-generation', 'stage1-fixed-point', 'standard-ten', 'l1-l13', 'python-c-equivalence', 'python-c-coverage', 'mutations', 'deterministic-fuzzing', 'sanitizers', 'native-goldens', 'application-assembly', 'manifestation-direct-identity', 'cli-gui-equality', 'real-browser', 'atomic-preservation', 'isolated-runtime', 'provenance', 'open-gap-truthfulness', 'python-3.11', 'python-3.12', 'python-3.13', 'issue7-generated-surface'], 'vector_count': 31}
ROOT = Path(__file__).resolve().parents[1]

def audited_canonical_primitive(value):
    return (json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n").encode("utf-8")

def audited_sha_primitive(raw):
    return hashlib.sha256(raw).hexdigest()

def audited_read_primitive(path):
    return json.loads(path.read_text(encoding="utf-8"))

def audited_pointer_parent_primitive(value, path):
    current = value
    for item in path[:-1]:
        current = current[item]
    return current, path[-1]

def audited_apply_mutation_primitive(model, mutation):
    changed = copy.deepcopy(model)
    operation = mutation["operation"]
    path = mutation["path"]
    parent, key = audited_pointer_parent_primitive(changed, path)
    if operation == "set":
        parent[key] = mutation["value"]
    elif operation == "remove":
        parent.pop(key) if isinstance(parent, list) else parent.pop(key, None)
    elif operation == "append":
        parent[key].append(mutation["value"])
    elif operation == "duplicate":
        parent.insert(key + 1, copy.deepcopy(parent[key]))
    elif operation == "reverse":
        parent[key].reverse()
    return changed

def audited_validate_model_primitive(model):
    errors = []
    authorities = model.get("authorities") or {}
    if authorities != EXPECTED["authorities"] or any(
        not isinstance(value, str) or len(value) != 64
        for value in authorities.values()
    ):
        errors.append("stale-authority")
    if model.get("authority_count") != 1:
        errors.append("divided-authority")
    if model.get("depths") != list(EXPECTED["depths"]):
        errors.append("ten-depth-violation")
    watchers = model.get("watchers") or []
    if (
        len(watchers) != 10
        or len({item.get("identity") for item in watchers}) != 10
        or any(item.get("depth") not in range(1, 11) for item in watchers)
    ):
        errors.append("watcher-accounting")
    if model.get("thing_states") != list(EXPECTED["thing_states"]):
        errors.append("state-collapse")
    if model.get("events") != list(EXPECTED["events"]):
        errors.append("event-order")
    if model.get("boundary_isolation") is not True:
        errors.append("boundary-isolation")
    if model.get("host_oracle_relation") != "none":
        errors.append("host-dependency")
    fixed = model.get("fixed_point") or {}
    if fixed.get("cycle") is True:
        errors.append("unfolding-cycle")
    if fixed.get("generation_count", 0) > EXPECTED["generation_bound"]:
        errors.append("bilima-limit")
    if model.get("generated_regions_unchanged") is not True:
        errors.append("generated-region-tamper")
    if model.get("documentation_fact_count") != EXPECTED["fact_count"]:
        errors.append("claim-evidence-disagreement")
    if model.get("proof_nodes") != list(EXPECTED["proof_nodes"]):
        errors.append("proof-inventory")
    if model.get("goldens_verified") is not True:
        errors.append("golden-integrity")
    if model.get("target_truthful") is not True:
        errors.append("target-claim")
    if model.get("vector_count") != EXPECTED["vector_count"]:
        errors.append("partial-vector")
    if model.get("synthetic_obligation") is not True:
        errors.append("anti-overfit-missing")
    return errors

def audited_inventory_report_primitive():
    manifest = audited_read_primitive(ROOT / "verification-manifest.json")
    errors = []
    for item in manifest["files"]:
        path = ROOT / item["path"]
        if not path.is_file() or audited_sha_primitive(path.read_bytes()) != item["sha256"]:
            errors.append("projection-tamper:" + item["path"])
    errors.extend(audited_validate_model_primitive(manifest["semantic_model"]))
    return manifest, sorted(errors)

def audited_lookup_primitive(path, identity):
    values = audited_read_primitive(ROOT / path)
    return next(item for item in values["items"] if item["identity"] == identity)

def audited_assert_surface_primitive():
    manifest, errors = audited_inventory_report_primitive()
    assert not errors, errors
    assert manifest["fixed_point"]["verdict"] == "pass"

def audited_assert_fact_primitive(identity, expected_sha):
    item = audited_lookup_primitive("authority/facts.json", identity)
    assert item["value_sha256"] == expected_sha

def audited_assert_partition_primitive(identity, expected):
    item = audited_lookup_primitive("tests/partitions.json", identity)
    assert item["expected_relation"] == expected

def audited_assert_golden_primitive(identity):
    manifest = audited_read_primitive(ROOT / "goldens/manifest.json")
    item = next(item for item in manifest["items"] if item["identity"] == identity)
    path = ROOT / item["path"]
    assert path.is_file()
    assert audited_sha_primitive(path.read_bytes()) == item["sha256"]

def audited_assert_mutation_primitive(identity, expected_error):
    mutation = audited_lookup_primitive("mutations/manifest.json", identity)
    manifest = audited_read_primitive(ROOT / "verification-manifest.json")
    changed = audited_apply_mutation_primitive(manifest["semantic_model"], mutation)
    errors = audited_validate_model_primitive(changed)
    assert expected_error in errors, (identity, expected_error, errors)

def audited_audit_primitive(thing):
    manifest, errors = audited_inventory_report_primitive()
    state = "valid" if not errors else "invalid"
    return {
        **thing,
        "value": {
            "error": None if not errors else errors[0],
            "errors": errors,
            "structure_hash": manifest["structure_hash"],
            "tree_sha256": manifest["tree_sha256"],
            "verdict": "pass" if not errors else "fail",
        },
        "evidence": (
            *thing.get("evidence", ()),
            "issue7:audit-requested",
            "issue7:audit-pass" if not errors else "issue7:audit-fail",
        ),
        "state": state,
    }

def assert_surface():
    return audited_assert_surface_primitive()

def assert_fact(identity, expected_sha):
    return audited_assert_fact_primitive(identity, expected_sha)

def assert_partition(identity, expected):
    return audited_assert_partition_primitive(identity, expected)

def assert_golden(identity):
    return audited_assert_golden_primitive(identity)

def assert_mutation(identity, expected_error):
    return audited_assert_mutation_primitive(identity, expected_error)

def audit(thing):
    return audited_audit_primitive(thing)
