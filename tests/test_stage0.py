"""Executable conformance and adversarial proofs for the Stage-0 contract."""

from __future__ import annotations

import hashlib
import ast
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

import bootstrap.stage0 as stage0

REPO = Path(__file__).resolve().parents[1]
CONTRACT = REPO / "seed" / "stage0" / "TRUSTED_INPUTS.json"
EXPECTED_EVIDENCE = (
    "boundary:contract:read",
    "stage0:contract-verified",
    "boundary:trusted-inputs:read",
    "stage0:inputs-verified",
    "stage0:handoff-planned",
    "boundary:handoff:publish",
    "stage0:handoff-published",
)


def canonical_bytes(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode()


def blank(contract, root, output):
    return {
        "value": {
            "contract_path": str(contract),
            "input_root": str(root),
            "output": str(output),
        },
        "depths": (),
        "axes": (),
        "evidence": (),
        "state": "formed",
    }


def copy_trust_tree(target):
    contract = json.loads(CONTRACT.read_text())
    for entry in contract["trusted_inputs"]:
        destination = target / entry["path"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / entry["path"], destination)
    contract_path = target / "TRUSTED_INPUTS.json"
    contract_path.write_bytes(canonical_bytes(contract))
    return contract_path, contract


def run(root, contract, output):
    return stage0.stage0_plan(blank(contract, root, output))


def update_entry_hash(contract, root, role):
    entry = next(item for item in contract["trusted_inputs"] if item["role"] == role)
    raw = (root / entry["path"]).read_bytes()
    if entry["hash_mode"] == "canonical-json":
        raw = canonical_bytes(json.loads(raw))
    entry["sha256"] = hashlib.sha256(raw).hexdigest()


def assert_expected_failure(result, code_prefix, evidence):
    assert result["state"] == "invalid"
    assert result["value"]["error"].startswith(code_prefix)
    assert result["value"]["ticket"] is None
    assert result["value"]["handoff"] is None
    assert result["value"]["handoff_sha256"] is None
    assert result["value"]["generation_manifest"] is None
    assert result["value"]["stage1_payload_tree_sha256"] is None
    assert result["evidence"][-1] == evidence
    assert "stage0:handoff-published" not in result["evidence"]


def test_positive_handoff_is_deterministic_and_location_independent(tmp_path):
    root_a = tmp_path / "a"
    root_b = tmp_path / "b"
    contract_a, _ = copy_trust_tree(root_a)
    contract_b, _ = copy_trust_tree(root_b)
    first = run(root_a, contract_a, tmp_path / "out-a")
    second = run(root_b, contract_b, tmp_path / "out-b")
    assert first["state"] == second["state"] == "valid"
    assert first["evidence"] == second["evidence"] == EXPECTED_EVIDENCE
    assert first["value"]["handoff"] == second["value"]["handoff"]
    assert first["value"]["handoff_sha256"] == second["value"]["handoff_sha256"]
    assert (tmp_path / "out-a" / "stage1-handoff.json").read_bytes() == (
        tmp_path / "out-b" / "stage1-handoff.json"
    ).read_bytes()
    assert (tmp_path / "out-a" / "generation-manifest.json").read_bytes() == (
        tmp_path / "out-b" / "generation-manifest.json"
    ).read_bytes()
    assert first["value"]["stage1_payload_tree_sha256"] == second["value"][
        "stage1_payload_tree_sha256"
    ]
    assert str(root_a) not in canonical_bytes(first["value"]["handoff"]).decode()
    assert str(root_b) not in canonical_bytes(second["value"]["handoff"]).decode()


def test_cli_emits_canonical_thing_and_handoff(tmp_path):
    root = tmp_path / "trust"
    contract, _ = copy_trust_tree(root)
    output = tmp_path / "handoff"
    completed = subprocess.run(
        [
            sys.executable,
            str(REPO / "bootstrap" / "stage0.py"),
            "plan",
            "--contract",
            str(contract),
            "--input-root",
            str(root),
            "--output",
            str(output),
        ],
        check=False,
        capture_output=True,
    )
    result = json.loads(completed.stdout)
    assert completed.returncode == 0
    assert result["state"] == "valid"
    assert output.joinpath("stage1-handoff.json").is_file()
    assert output.joinpath("generation-manifest.json").is_file()


def test_contract_record_order_is_semantically_irrelevant(tmp_path):
    root = tmp_path / "trust"
    contract_path, contract = copy_trust_tree(root)
    first = run(root, contract_path, tmp_path / "first")
    contract["trusted_inputs"].reverse()
    contract_path.write_bytes(canonical_bytes(contract))
    second = run(root, contract_path, tmp_path / "second")
    assert first["state"] == second["state"] == "valid"
    assert first["value"]["contract_sha256"] == second["value"]["contract_sha256"]
    assert first["value"]["handoff_sha256"] == second["value"]["handoff_sha256"]


@pytest.mark.parametrize(
    ("mutation", "error"),
    [
        (lambda contract: contract["allowed_operations"].append("execute-domain-command"), "allowed-operations"),
        (
            lambda contract: contract["prohibited_capabilities"].remove("application-domain-behavior"),
            "prohibited-capabilities",
        ),
        (lambda contract: contract.update({"clock": "host"}), "contract-shape"),
        (
            lambda contract: contract["runtime"]["allowed_modules"].append("subprocess"),
            "runtime-profile",
        ),
        (
            lambda contract: contract["trusted_inputs"][0].update({"path": "../ROOT.seed.json"}),
            "invalid-path",
        ),
        (
            lambda contract: contract["trusted_inputs"][0].update({"hash_mode": "unverified-copy"}),
            "hash-mode",
        ),
    ],
)
def test_contract_mutations_are_rejected(tmp_path, mutation, error):
    root = tmp_path / "trust"
    contract_path, contract = copy_trust_tree(root)
    mutation(contract)
    contract_path.write_bytes(canonical_bytes(contract))
    result = run(root, contract_path, tmp_path / "out")
    assert_expected_failure(result, f"stage0.contract:{error}", "stage0:contract-rejected")


def test_missing_contract_is_expected_validation_without_ticket(tmp_path):
    result = run(tmp_path, tmp_path / "missing.json", tmp_path / "out")
    assert_expected_failure(result, "stage0.contract:", "stage0:contract-rejected")


def test_missing_input_and_hash_tamper_are_rejected_deterministically(tmp_path):
    root = tmp_path / "trust"
    contract_path, contract = copy_trust_tree(root)
    seed = root / "seed" / "ROOT.seed.json"
    seed.unlink()
    missing_a = run(root, contract_path, tmp_path / "missing")
    missing_b = run(root, contract_path, tmp_path / "missing")
    assert missing_a == missing_b
    assert_expected_failure(missing_a, "stage0.input:", "stage0:inputs-rejected")
    shutil.copyfile(REPO / "seed" / "ROOT.seed.json", seed)
    seed.write_bytes(seed.read_bytes() + b" ")
    whitespace_only = run(root, contract_path, tmp_path / "canonical")
    assert whitespace_only["state"] == "valid"
    parsed = json.loads(seed.read_text())
    parsed["seed_id"] = "tampered"
    seed.write_bytes(canonical_bytes(parsed))
    tampered = run(root, contract_path, tmp_path / "tampered")
    assert_expected_failure(
        tampered, "stage0.input:hash-mismatch:root-seed", "stage0:inputs-rejected"
    )
    assert contract["trusted_inputs"]


def test_invalid_seed_and_schema_identity_fail_even_when_rehashed(tmp_path):
    root = tmp_path / "trust"
    contract_path, contract = copy_trust_tree(root)
    seed_path = root / "seed" / "ROOT.seed.json"
    seed = json.loads(seed_path.read_text())
    seed["standard_version"] = "TEN-unknown"
    seed_path.write_bytes(canonical_bytes(seed))
    update_entry_hash(contract, root, "root-seed")
    contract_path.write_bytes(canonical_bytes(contract))
    invalid_seed = run(root, contract_path, tmp_path / "seed-out")
    assert_expected_failure(
        invalid_seed, "stage0.input:root-seed-identity", "stage0:inputs-rejected"
    )

    shutil.copyfile(REPO / "seed" / "ROOT.seed.json", seed_path)
    update_entry_hash(contract, root, "root-seed")
    schema_path = root / "seed" / "STAGE1_HANDOFF_SCHEMA.json"
    schema = json.loads(schema_path.read_text())
    schema["$id"] = "replacement-schema"
    schema_path.write_bytes(canonical_bytes(schema))
    update_entry_hash(contract, root, "stage1-handoff-schema")
    contract_path.write_bytes(canonical_bytes(contract))
    invalid_schema = run(root, contract_path, tmp_path / "schema-out")
    assert_expected_failure(
        invalid_schema,
        "stage0.input:schema-identity:stage1-handoff-schema",
        "stage0:inputs-rejected",
    )


def test_symlink_escape_is_rejected(tmp_path):
    root = tmp_path / "trust"
    contract_path, _ = copy_trust_tree(root)
    seed = root / "seed" / "ROOT.seed.json"
    seed.unlink()
    seed.symlink_to(REPO / "seed" / "ROOT.seed.json")
    result = run(root, contract_path, tmp_path / "out")
    assert_expected_failure(result, "stage0.input:path-escape", "stage0:inputs-rejected")


def test_resource_limits_reject_bytes_depth_and_count(tmp_path):
    root = tmp_path / "trust"
    contract_path, contract = copy_trust_tree(root)
    contract["limits"]["maximum_input_bytes"] = 1
    contract_path.write_bytes(canonical_bytes(contract))
    byte_result = run(root, contract_path, tmp_path / "bytes")
    assert_expected_failure(byte_result, "stage0.input:resource-limit:bytes", "stage0:inputs-rejected")

    contract["limits"]["maximum_input_bytes"] = 1_048_576
    contract["limits"]["maximum_json_depth"] = 1
    contract_path.write_bytes(canonical_bytes(contract))
    depth_result = run(root, contract_path, tmp_path / "depth")
    assert_expected_failure(depth_result, "stage0.input:resource-limit:json-depth", "stage0:inputs-rejected")

    contract["limits"]["maximum_json_depth"] = 32
    contract["limits"]["maximum_input_count"] = 4
    contract_path.write_bytes(canonical_bytes(contract))
    count_result = run(root, contract_path, tmp_path / "count")
    assert_expected_failure(
        count_result, "stage0.contract:resource-limit:input-count", "stage0:contract-rejected"
    )


def test_atomic_publish_preserves_last_verified_output(tmp_path, monkeypatch):
    root = tmp_path / "trust"
    contract_path, _ = copy_trust_tree(root)
    output = tmp_path / "output"
    first = run(root, contract_path, output)
    before = output.joinpath("stage1-handoff.json").read_bytes()

    def fail_publish(output_path, files):
        raise OSError("secret host detail")

    monkeypatch.setattr(stage0, "_atomic_publish", fail_publish)
    failed = run(root, contract_path, output)
    assert first["state"] == "valid"
    assert_expected_failure(failed, "stage0.publish:OSError", "stage0:publish-rejected")
    assert output.joinpath("stage1-handoff.json").read_bytes() == before
    assert "secret host detail" not in canonical_bytes(failed).decode()


def test_atomic_publish_replaces_an_existing_file_with_complete_tree(tmp_path):
    root = tmp_path / "trust"
    contract_path, _ = copy_trust_tree(root)
    output = tmp_path / "output"
    output.write_text("previous")
    result = run(root, contract_path, output)
    assert result["state"] == "valid"
    assert sorted(path.name for path in output.iterdir()) == [
        "generation-manifest.json",
        "stage1-handoff.json",
    ]


def test_output_cannot_replace_or_enter_the_trusted_input_tree(tmp_path):
    root = tmp_path / "trust"
    contract_path, _ = copy_trust_tree(root)
    before = (root / "seed" / "ROOT.seed.json").read_bytes()
    same = run(root, contract_path, root)
    child = run(root, contract_path, root / "generated")
    assert_expected_failure(
        same, "stage0.publish:ValueError", "stage0:publish-rejected"
    )
    assert_expected_failure(
        child, "stage0.publish:ValueError", "stage0:publish-rejected"
    )
    assert (root / "seed" / "ROOT.seed.json").read_bytes() == before
    assert not (root / "generated").exists()


def test_unhandled_failure_opens_one_redacted_deterministic_ticket(tmp_path, monkeypatch):
    thing = blank(CONTRACT, REPO, tmp_path / "out")

    def explode(value):
        raise RuntimeError("password=hunter2")

    monkeypatch.setattr(stage0, "inward_read_contract", explode)
    first = stage0.stage0_plan(thing)
    second = stage0.stage0_plan(thing)
    assert first == second
    assert first["state"] == "invalid"
    assert first["evidence"] == ("event:ticket.open",)
    assert first["value"]["ticket"]["message"] == "[redacted-message]"
    assert "hunter2" not in canonical_bytes(first).decode()


def test_stage0_has_no_proof_application_vocabulary_or_dynamic_capabilities():
    source = (REPO / "bootstrap" / "stage0.py").read_text()
    lowered = source.lower()
    proof_terms = {
        "trajectory",
        "meter",
        "affine",
        "score-board",
        "task-ledger",
        "player",
        "points",
        "completed",
    }
    assert not proof_terms.intersection(lowered)
    tree = ast.parse(source)
    imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    calls = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert not imports.intersection({"os", "random", "socket", "subprocess", "time", "urllib"})
    assert not calls.intersection({"eval", "exec", "compile", "__import__", "getattr"})


def test_hidden_files_and_environment_do_not_change_output(tmp_path, monkeypatch):
    root = tmp_path / "trust"
    contract_path, _ = copy_trust_tree(root)
    first = run(root, contract_path, tmp_path / "first")
    (root / ".hidden").write_text("opaque repository source")
    (root / "unlisted.py").write_text("application behavior")
    monkeypatch.setenv("UC_STAGE0_SELECT", "unlisted.py")
    monkeypatch.setenv("TZ", "Pacific/Kiritimati")
    monkeypatch.setenv("LC_ALL", "C")
    second = run(root, contract_path, tmp_path / "second")
    assert first["value"]["handoff_sha256"] == second["value"]["handoff_sha256"]
    assert first["value"]["generation_manifest_sha256"] == second["value"][
        "generation_manifest_sha256"
    ]
    assert first["value"]["stage1_payload_tree_sha256"] == second["value"][
        "stage1_payload_tree_sha256"
    ]


def test_opaque_repository_blob_cannot_enter_trusted_set(tmp_path):
    root = tmp_path / "trust"
    contract_path, contract = copy_trust_tree(root)
    opaque = root / "repository.tar"
    opaque.write_bytes(b"opaque")
    contract["trusted_inputs"].append(
        {
            "role": "repository-source",
            "path": "repository.tar",
            "hash_mode": "raw-bytes",
            "sha256": hashlib.sha256(b"opaque").hexdigest(),
        }
    )
    contract["limits"]["maximum_input_count"] = 7
    contract_path.write_bytes(canonical_bytes(contract))
    result = run(root, contract_path, tmp_path / "out")
    assert_expected_failure(
        result, "stage0.contract:trusted-input-roles", "stage0:contract-rejected"
    )


def test_public_part_is_one_thing_in_one_thing_out_and_states_remain_distinct(tmp_path):
    root = tmp_path / "trust"
    contract, _ = copy_trust_tree(root)
    assert stage0.stage0_plan.__code__.co_argcount == 1
    assert stage0.inward_read_contract.__code__.co_argcount == 1
    assert stage0.inward_read_trusted_inputs.__code__.co_argcount == 1
    assert stage0.plan_stage1_handoff.__code__.co_argcount == 1
    assert stage0.outward_publish_handoff.__code__.co_argcount == 1
    malformed = stage0.stage0_plan({"value": {}})
    assert malformed["state"] == "invalid"
    assert run(root, contract, tmp_path / "out")["state"] == "valid"
