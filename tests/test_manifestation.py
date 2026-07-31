"""Name resolution and artifact-manifestation semantic proofs."""

from __future__ import annotations

import copy
import hashlib
import inspect
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from unified.boundary import inward
from unified.generator import manifestation
from unified.generator.cli import _parse_argv
from unified.generator.manifestation import (
    CANONICAL_STATES,
    COMPILER_ROUTES,
    ROUTE_VERSIONS,
    canonical_json_bytes,
    canonical_seed_sha256,
    manifest_artifact,
    manifestation_application_vocabulary,
    manifestation_mutation_report,
    manifestation_source_report,
    manifestation_vocabulary_report,
    registry_snapshot_sha256,
    resolve_name,
    validate_registry,
)
from unified.generator.application_language.tooling.catalog_materializer import (
    materialize_profile,
)
from unified.generator.application_language import seed_compiler as application_language_compiler


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "seed" / "registry.json"
SCHEMA_PATH = ROOT / "seed" / "MANIFESTATION_SCHEMA.json"
SEED_ROOT = ROOT / "seed"
NATIVE_SEED = SEED_ROOT / "thing_v2" / "trajectory_meter.json"
FOREIGN_SEED = SEED_ROOT / "thing_v2" / "orchard_yield.json"
QUALIFIED_NAME = "uc://applications/trajectory-meter@1"
SNAPSHOT = "e0c6e98a4ba57606b71bf85cfb4632a173cbbea4b802b09f02f81dc29da46b1b"
ARTIFACT_SHA = "a8c08f617be16b5916616a30834ad6444e81ea737559eca5747ce7082e1d3841"
SEED_SHA = "762f633c12a87bcf8a462002c253b047b980c1e1ab442a307154230c988fda49"
SUCCESS_EVIDENCE = (
    "boundary:inward",
    "manifestation:addressed",
    "boundary:registry:read",
    "resolution:registry-verified",
    "manifestation:resolved",
    "boundary:seed:read",
    "manifestation:seed-verified",
    "boundary:artifact-output:prepare",
    "manifestation:compile-requested",
    "manifestation:compiled",
    "manifestation:artifact-verified",
    "boundary:artifact:publish",
    "manifestation:manifested",
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _record(registry: dict, name: str = QUALIFIED_NAME) -> dict:
    return next(
        item for item in registry["records"] if item["canonical_name"] == name
    )


def _record_seed(record: dict) -> dict:
    path = SEED_ROOT / record["seed_path"]
    document = _load(path)
    if record["compiler_route"] != "application-language":
        return document
    profile_identity = record["route_options"]["profile_identity"]
    profiles = [
        profile
        for family in document["families"]
        for profile in family["profiles"]
        if profile["identity"] == profile_identity
    ]
    assert len(profiles) == 1
    profile = profiles[0]
    if "derivation" in profile:
        leaf, prototype = materialize_profile(profile, path.parent)
        return application_language_compiler.resolve_seed_document(
            prototype, leaf
        )[0]
    return application_language_compiler.load_seed(
        path.parent / profile["seed"]
    )[0]


def _record_vocabulary_seed(record: dict) -> dict:
    if record["compiler_route"] != "application-language":
        return _record_seed(record)
    catalog = _load(SEED_ROOT / record["seed_path"])
    profile_identity = record["route_options"]["profile_identity"]
    return next(
        profile
        for family in catalog["families"]
        for profile in family["profiles"]
        if profile["identity"] == profile_identity
    )


def _write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_registry(path: Path, registry: dict, recompute: bool = True) -> str:
    if recompute:
        registry["registry_snapshot_sha256"] = registry_snapshot_sha256(registry)
    _write(path, registry)
    return registry["registry_snapshot_sha256"]


def _request(
    output: Path,
    *,
    name: str = QUALIFIED_NAME,
    registry_path: Path = REGISTRY_PATH,
    snapshot: str = SNAPSHOT,
    seed_root: Path | None = None,
) -> dict:
    value = {
        "name": name,
        "registry_path": str(registry_path),
        "expected_registry_snapshot_sha256": snapshot,
        "output": str(output),
    }
    if seed_root is not None:
        value["seed_root"] = str(seed_root)
    return value


def _tree_bytes(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
        and "__pycache__" not in path.parts
        and ".pytest_cache" not in path.parts
    }


def _assert_outcome(
    result: dict,
    *,
    resolution: str,
    state: str,
    evidence: tuple[str, ...],
    phase: str,
    ticket: bool = False,
) -> None:
    assert result["state"] == state
    assert result["state"] in CANONICAL_STATES
    assert result["value"]["resolution"]["status"] == resolution
    assert result["value"]["manifestation"]["phase"] == phase
    assert result["evidence"] == evidence
    assert bool(result["value"].get("ticket")) is ticket
    assert "artifact_tree_sha256" not in result["value"]
    assert result["value"].get("manifestation", {}).get("artifact_id") is None
    assert "manifestation:manifested" not in result["evidence"]


def test_schema_registry_and_public_contracts():
    schema = _load(SCHEMA_PATH)
    registry = _load(REGISTRY_PATH)
    assert schema["title"] == "Unified Code name-to-manifestation registry"
    assert validate_registry(registry) == []
    assert registry_snapshot_sha256(registry) == SNAPSHOT
    assert canonical_seed_sha256(_load(NATIVE_SEED)) == SEED_SHA
    assert len(inspect.signature(resolve_name).parameters) == 1
    assert len(inspect.signature(manifest_artifact).parameters) == 1
    parsed = _parse_argv(
        [
            "manifest",
            QUALIFIED_NAME,
            "--registry",
            "seed/registry.json",
            "--snapshot",
            SNAPSHOT,
            "--output",
            "/tmp/artifact",
        ]
    )
    assert parsed == {
        "command": "manifest",
        "name": QUALIFIED_NAME,
        "registry_path": "seed/registry.json",
        "expected_registry_snapshot_sha256": SNAPSHOT,
        "output": "/tmp/artifact",
    }


def test_registry_covers_every_current_product_and_only_generic_routes():
    registry = _load(REGISTRY_PATH)
    primary = {
        record["canonical_name"]: record
        for record in registry["records"]
    }
    established = {
        "uc://applications/file-reader@1",
        "uc://applications/file-editor@1",
        "uc://applications/math-library@1",
        "uc://applications/bounded-integer-expression-calculator@1",
        "uc://applications/pong-game@1",
        "uc://applications/trajectory-meter@1",
        "uc://applications/orchard-yield@1",
        "uc://applications/task-ledger@1",
        "uc://applications/score-board@1",
        "uc://applications/text-stats-v2@1",
        "uc://applications/invoice-total@1",
    }
    catalog = _load(SEED_ROOT / "application_language" / "catalog.seed.json")
    application_language = {
        profile["product_identity"]
        for family in catalog["families"]
        for profile in family["profiles"]
        if profile["status"] == "proven"
    }
    assert len(application_language) == 74
    assert set(primary) == established | application_language
    assert set(COMPILER_ROUTES) == set(ROUTE_VERSIONS)
    for record in primary.values():
        assert record["compiler_route"] in COMPILER_ROUTES
        assert record["compiler_version"] == ROUTE_VERSIONS[record["compiler_route"]]
        seed = _record_seed(record)
        assert canonical_seed_sha256(seed) == record["seed_sha256"]


def test_established_registered_products_match_direct_compiler_identities(tmp_path):
    registry = _load(REGISTRY_PATH)
    results = {}
    for record in (
        item
        for item in registry["records"]
        if item["compiler_route"] != "application-language"
    ):
        output = tmp_path / record["canonical_name"].rsplit("/", 1)[-1].replace("@", "-")
        result = manifest_artifact(
            inward(
                _request(
                    output,
                    name=record["canonical_name"],
                )
            )
        )
        assert result["state"] == "valid", (record["canonical_name"], result["value"])
        assert result["value"]["artifact_tree_sha256"] == record["artifact_tree_sha256"]
        assert result["value"]["manifestation"]["artifact_id"] == (
            "sha256:" + record["artifact_tree_sha256"]
        )
        results[record["canonical_name"]] = result["value"]["artifact_tree_sha256"]
    assert len(results) == 11


def test_all_registered_seed_vocabulary_is_absent_from_manifestation_runtime():
    registry = _load(REGISTRY_PATH)
    seeds = tuple(
        _record_vocabulary_seed(record)
        for record in registry["records"]
    )
    report = manifestation_vocabulary_report(seeds)
    mutations = manifestation_mutation_report(seeds)
    assert manifestation_application_vocabulary(seeds)
    assert report["ok"], report
    assert mutations["ok"], mutations
    assert mutations["detected"] == mutations["total"]


def test_positive_qualified_name_manifests_twice_byte_identically(tmp_path):
    first_output = tmp_path / "first"
    second_output = tmp_path / "second"
    first = manifest_artifact(inward(_request(first_output)))
    second = manifest_artifact(inward(_request(second_output)))
    for result in (first, second):
        assert result["state"] == "valid"
        assert result["value"]["resolution"] == {
            "status": "resolved",
            "error": None,
        }
        assert result["value"]["manifestation"] == {
            "phase": "manifested",
            "artifact_id": f"sha256:{ARTIFACT_SHA}",
        }
        assert result["value"]["identity"] == {
            "registry_snapshot_sha256": SNAPSHOT,
            "canonical_name": QUALIFIED_NAME,
            "seed_id": "thing-v2:trajectory-meter@1",
            "seed_sha256": SEED_SHA,
            "compiler_version": "THING-V2-1",
            "artifact_tree_sha256": ARTIFACT_SHA,
        }
        assert result["evidence"] == SUCCESS_EVIDENCE
        assert result["value"]["ticket"] is None
        assert all((result["value"]["verification"] or {}).get(key, {}).get("ok")
                   for key in (
                       "source_laws",
                       "runtime_seed_absence",
                       "generated_tests",
                       "acceptance",
                       "seedless_copy",
                       "fixed_point",
                   ))
    assert first["value"]["artifact_tree_sha256"] == ARTIFACT_SHA
    assert second["value"]["artifact_tree_sha256"] == ARTIFACT_SHA
    assert _tree_bytes(first_output) == _tree_bytes(second_output)


def test_generated_runtime_executes_after_copy_without_registry_seed_or_repo(tmp_path):
    output = tmp_path / "built"
    result = manifest_artifact(inward(_request(output)))
    assert result["state"] == "valid"
    isolated_root = tmp_path / "isolated"
    copied = isolated_root / "artifact"
    shutil.copytree(
        output,
        copied,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache"),
    )
    package_source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((copied / "trajectory_meter").glob("*.py"))
    )
    assert "registry" not in package_source.lower()
    assert "seed/thing_v2" not in package_source
    isolated_runner = (
        "import importlib.util, runpy, sys;"
        "assert importlib.util.find_spec('unified') is None;"
        f"sys.path.insert(0, {str(copied)!r});"
        "sys.argv=['trajectory_meter', *sys.argv[1:]];"
        "runpy.run_module('trajectory_meter', run_name='__main__')"
    )
    process = subprocess.run(
        [
            sys.executable,
            "-S",
            "-c",
            isolated_runner,
            "--input",
            '{"distance":5}',
            "--params",
            '{"duration":3}',
        ],
        cwd=isolated_root,
        env={"PYTHONHASHSEED": "0"},
        capture_output=True,
        text=True,
        check=False,
    )
    payload = json.loads(process.stdout.strip())
    assert process.returncode == 0
    assert payload["output"] == {"velocity": 31}
    assert payload["state"] == "valid"


def test_unknown_qualified_name_is_valid_domain_outcome(tmp_path):
    request = inward(
        _request(
            tmp_path / "unused",
            name="uc://applications/missing-application@1",
        )
    )
    result = resolve_name(request)
    assert resolve_name(request) == result
    _assert_outcome(
        result,
        resolution="unknown",
        state="valid",
        phase="addressed",
        evidence=(
            "boundary:inward",
            "manifestation:addressed",
            "boundary:registry:read",
            "resolution:registry-verified",
            "resolution:unknown",
        ),
    )


@pytest.mark.parametrize(
    ("name", "resolution", "markers"),
    (
        (
            "uc://applications/calculator@1",
            "unknown",
            ("resolution:unknown",),
        ),
        (
            "calculator",
            "unresolved",
            (
                "resolution:version-required",
                "resolution:unresolved",
            ),
        ),
    ),
)
def test_unqualified_calculator_identity_is_not_silently_selected(
    tmp_path, name, resolution, markers
):
    result = resolve_name(
        inward(_request(tmp_path / "unused", name=name))
    )
    _assert_outcome(
        result,
        resolution=resolution,
        state="valid",
        phase="addressed",
        evidence=(
            "boundary:inward",
            "manifestation:addressed",
            "boundary:registry:read",
            "resolution:registry-verified",
            *markers,
        ),
    )


def test_ambiguous_short_name_is_not_selected(tmp_path):
    registry = _load(REGISTRY_PATH)
    second_version = copy.deepcopy(_record(registry))
    second_version["canonical_name"] = "uc://applications/trajectory-meter@2"
    second_version["seed_id"] = "thing-v2:trajectory-meter@2"
    registry["records"].append(second_version)
    registry_path = tmp_path / "ambiguous-registry.json"
    snapshot = _write_registry(registry_path, registry)
    request = inward(
        _request(
            tmp_path / "unused",
            name="trajectory-meter",
            registry_path=registry_path,
            snapshot=snapshot,
            seed_root=SEED_ROOT,
        )
    )
    result = resolve_name(request)
    assert resolve_name(request) == result
    _assert_outcome(
        result,
        resolution="ambiguous",
        state="valid",
        phase="addressed",
        evidence=(
            "boundary:inward",
            "manifestation:addressed",
            "boundary:registry:read",
            "resolution:registry-verified",
            "resolution:ambiguous",
        ),
    )
    assert result["value"]["resolution_matches"] == [
        "uc://applications/trajectory-meter@1",
        "uc://applications/trajectory-meter@2",
    ]


def test_missing_registry_input_is_unavailable_without_ticket(tmp_path):
    request = _request(tmp_path / "unused")
    request.pop("registry_path")
    result = resolve_name(inward(request))
    assert resolve_name(inward(request)) == result
    _assert_outcome(
        result,
        resolution="unavailable",
        state="valid",
        phase="addressed",
        evidence=(
            "boundary:inward",
            "manifestation:addressed",
            "resolution:registry-missing",
            "resolution:unavailable",
        ),
    )


def test_unreadable_registry_is_unavailable_and_deterministic(tmp_path):
    request = _request(tmp_path / "unused", registry_path=tmp_path / "missing.json")
    first = resolve_name(inward(request))
    second = resolve_name(inward(request))
    assert first == second
    _assert_outcome(
        first,
        resolution="unavailable",
        state="valid",
        phase="addressed",
        evidence=(
            "boundary:inward",
            "manifestation:addressed",
            "boundary:registry:read",
            "resolution:registry-unavailable",
            "resolution:unavailable",
        ),
    )


def test_missing_seed_preserves_resolved_outcome_without_artifact(tmp_path):
    registry = _load(REGISTRY_PATH)
    _record(registry)["seed_path"] = "thing_v2/missing.json"
    registry_path = tmp_path / "registry.json"
    snapshot = _write_registry(registry_path, registry)
    result = manifest_artifact(
        inward(
            _request(
                tmp_path / "artifact",
                registry_path=registry_path,
                snapshot=snapshot,
                seed_root=SEED_ROOT,
            )
        )
    )
    _assert_outcome(
        result,
        resolution="resolved",
        state="valid",
        phase="resolved",
        evidence=(
            "boundary:inward",
            "manifestation:addressed",
            "boundary:registry:read",
            "resolution:registry-verified",
            "manifestation:resolved",
            "boundary:seed:read",
            "manifestation:seed-unavailable",
        ),
    )


def test_conflicting_duplicate_canonical_identity_is_invalid(tmp_path):
    registry = _load(REGISTRY_PATH)
    duplicate = copy.deepcopy(registry["records"][0])
    duplicate["seed_id"] = "thing-v2:duplicate@1"
    registry["records"].append(duplicate)
    path = tmp_path / "registry.json"
    snapshot = _write_registry(path, registry)
    result = resolve_name(
        inward(_request(tmp_path / "unused", registry_path=path, snapshot=snapshot))
    )
    assert resolve_name(
        inward(_request(tmp_path / "unused", registry_path=path, snapshot=snapshot))
    ) == result
    _assert_outcome(
        result,
        resolution="conflict",
        state="invalid",
        phase="addressed",
        evidence=(
            "boundary:inward",
            "manifestation:addressed",
            "boundary:registry:read",
            "resolution:registry-invalid",
            "resolution:conflict",
        ),
    )
    assert result["value"]["resolution"]["error"] == "registry-identity-conflict"


def test_registry_altered_after_pin_and_snapshot_mismatch_are_conflicts(tmp_path):
    altered = _load(REGISTRY_PATH)
    _record(altered)["seed_path"] = "thing_v2/other.json"
    altered_path = tmp_path / "altered.json"
    _write_registry(altered_path, altered, recompute=False)
    first = resolve_name(
        inward(_request(tmp_path / "unused", registry_path=altered_path))
    )
    second = resolve_name(
        inward(
            _request(
                tmp_path / "unused",
                snapshot="0" * 64,
            )
        )
    )
    for result in (first, second):
        _assert_outcome(
            result,
            resolution="conflict",
            state="invalid",
            phase="addressed",
            evidence=(
                "boundary:inward",
                "manifestation:addressed",
                "boundary:registry:read",
                "resolution:snapshot-mismatch",
                "resolution:conflict",
            ),
        )
        assert result["value"]["resolution"]["error"] == "registry-snapshot-mismatch"


def test_seed_hash_mismatch_is_invalid_without_compile(tmp_path):
    registry = _load(REGISTRY_PATH)
    _record(registry)["seed_sha256"] = "0" * 64
    path = tmp_path / "registry.json"
    snapshot = _write_registry(path, registry)
    result = manifest_artifact(
        inward(
            _request(
                tmp_path / "artifact",
                registry_path=path,
                snapshot=snapshot,
                seed_root=SEED_ROOT,
            )
        )
    )
    repeated = manifest_artifact(
        inward(
            _request(
                tmp_path / "artifact",
                registry_path=path,
                snapshot=snapshot,
                seed_root=SEED_ROOT,
            )
        )
    )
    assert repeated == result
    _assert_outcome(
        result,
        resolution="resolved",
        state="invalid",
        phase="resolved",
        evidence=(
            "boundary:inward",
            "manifestation:addressed",
            "boundary:registry:read",
            "resolution:registry-verified",
            "manifestation:resolved",
            "boundary:seed:read",
            "manifestation:seed-hash-mismatch",
        ),
    )
    assert result["value"]["error"] == "seed-hash-mismatch"


def test_artifact_hash_mismatch_preserves_previous_verified_tree(tmp_path):
    output = tmp_path / "artifact"
    valid = manifest_artifact(inward(_request(output)))
    assert valid["state"] == "valid"
    before = _tree_bytes(output)
    registry = _load(REGISTRY_PATH)
    _record(registry)["artifact_tree_sha256"] = "0" * 64
    path = tmp_path / "registry.json"
    snapshot = _write_registry(path, registry)
    failed = manifest_artifact(
        inward(
            _request(
                output,
                registry_path=path,
                snapshot=snapshot,
                seed_root=SEED_ROOT,
            )
        )
    )
    assert failed["state"] == "invalid"
    assert failed["value"]["resolution"]["status"] == "resolved"
    assert failed["value"]["manifestation"]["phase"] == "compiled"
    assert failed["value"]["error"] == "artifact-tree-hash-mismatch"
    assert failed["value"].get("ticket") is None
    assert failed["evidence"][-2:] == (
        "manifestation:compiled",
        "manifestation:artifact-hash-mismatch",
    )
    assert "manifestation:artifact-verified" not in failed["evidence"]
    assert "manifestation:manifested" not in failed["evidence"]
    assert _tree_bytes(output) == before
    repeated = manifest_artifact(
        inward(
            _request(
                output,
                registry_path=path,
                snapshot=snapshot,
                seed_root=SEED_ROOT,
            )
        )
    )
    assert repeated == failed
    assert _tree_bytes(output) == before
    recovered = manifest_artifact(inward(_request(output)))
    assert recovered["state"] == "valid"
    assert _tree_bytes(output) == before


def test_no_silent_version_selection_and_no_fuzzy_matching(tmp_path):
    unresolved = resolve_name(
        inward(_request(tmp_path / "unused", name="orchard-yield"))
    )
    _assert_outcome(
        unresolved,
        resolution="unresolved",
        state="valid",
        phase="addressed",
        evidence=(
            "boundary:inward",
            "manifestation:addressed",
            "boundary:registry:read",
            "resolution:registry-verified",
            "resolution:version-required",
            "resolution:unresolved",
        ),
    )
    fuzzy = resolve_name(
        inward(
            _request(
                tmp_path / "unused",
                name="uc://applications/trajectory-mete@1",
            )
        )
    )
    _assert_outcome(
        fuzzy,
        resolution="unknown",
        state="valid",
        phase="addressed",
        evidence=(
            "boundary:inward",
            "manifestation:addressed",
            "boundary:registry:read",
            "resolution:registry-verified",
            "resolution:unknown",
        ),
    )


def test_registry_record_order_does_not_change_snapshot_or_resolution(tmp_path):
    registry = _load(REGISTRY_PATH)
    registry["records"].reverse()
    path = tmp_path / "registry.json"
    snapshot = _write_registry(path, registry, recompute=False)
    assert snapshot == SNAPSHOT
    result = resolve_name(
        inward(_request(tmp_path / "unused", registry_path=path))
    )
    assert result["state"] == "valid"
    assert result["value"]["resolution"]["status"] == "resolved"
    assert result["value"]["registry_snapshot_sha256"] == SNAPSHOT


def test_registry_name_version_seed_and_output_locations_are_data(tmp_path):
    variants = (
        ("uc://applications/trajectory-meter@7", "version-only"),
        ("uc://applications/renamed-meter@1", "name-only"),
    )
    for canonical_name, label in variants:
        registry = _load(REGISTRY_PATH)
        record = _record(registry)
        record["canonical_name"] = canonical_name
        record["seed_id"] = f"thing-v2:{label}"
        registry_path = tmp_path / "registry" / f"{label}.json"
        snapshot = _write_registry(registry_path, registry)
        alternate_seed_root = tmp_path / f"{label}-seeds"
        relocated_seed = alternate_seed_root / record["seed_path"]
        relocated_seed.parent.mkdir(parents=True, exist_ok=True)
        seed = _load(NATIVE_SEED)
        relocated_seed.write_bytes(canonical_json_bytes(seed))
        output = tmp_path / f"{label}-output"
        result = manifest_artifact(
            inward(
                _request(
                    output,
                    name=record["canonical_name"],
                    registry_path=registry_path,
                    snapshot=snapshot,
                    seed_root=alternate_seed_root,
                )
            )
        )
        assert result["state"] == "valid"
        assert result["value"]["identity"]["canonical_name"] == canonical_name
        assert result["value"]["identity"]["seed_id"] == record["seed_id"]
        assert result["value"]["artifact_tree_sha256"] == ARTIFACT_SHA


def test_canonical_seed_hash_ignores_dictionary_insertion_order():
    seed = _load(NATIVE_SEED)
    reversed_seed = dict(reversed(list(seed.items())))
    assert canonical_json_bytes(reversed_seed) == canonical_json_bytes(seed)
    assert canonical_seed_sha256(reversed_seed) == SEED_SHA


def test_canonical_state_overload_fuzzy_and_version_mutations_are_detected():
    seeds = (_load(NATIVE_SEED), _load(FOREIGN_SEED))
    source = manifestation_source_report()
    vocabulary = manifestation_vocabulary_report(seeds)
    mutations = manifestation_mutation_report(seeds)
    assert source["ok"], source
    assert vocabulary["ok"], vocabulary
    assert mutations["ok"], mutations
    assert mutations["detected"] == mutations["total"]
    assert mutations["total"] > 6


def test_atomic_publish_failure_preserves_tree_and_recovery(
    tmp_path, monkeypatch
):
    output = tmp_path / "artifact"
    first = manifest_artifact(inward(_request(output)))
    assert first["state"] == "valid"
    before = _tree_bytes(output)
    real_publish = manifestation._atomic_publish

    def fail_publish(_staging, _output):
        raise OSError("simulated atomic boundary failure")

    monkeypatch.setattr(manifestation, "_atomic_publish", fail_publish)
    failed = manifest_artifact(inward(_request(output)))
    assert failed["state"] == "invalid"
    assert failed["value"]["resolution"]["status"] == "resolved"
    assert failed["value"]["manifestation"]["phase"] == "verified"
    assert failed["value"]["error"] == "artifact-publish-failed"
    assert failed["value"].get("ticket") is None
    assert failed["evidence"][-2:] == (
        "boundary:artifact:publish",
        "manifestation:publish-failed",
    )
    assert "manifestation:manifested" not in failed["evidence"]
    assert _tree_bytes(output) == before
    repeated = manifest_artifact(inward(_request(output)))
    assert repeated == failed
    assert _tree_bytes(output) == before

    monkeypatch.setattr(manifestation, "_atomic_publish", real_publish)
    recovered = manifest_artifact(inward(_request(output)))
    assert recovered["state"] == "valid"
    assert recovered["value"]["artifact_tree_sha256"] == ARTIFACT_SHA
    assert _tree_bytes(output) == before


def test_unhandled_failure_uses_one_redacted_deterministic_ticket(
    tmp_path, monkeypatch
):
    def explode(_thing):
        raise RuntimeError("token=secret")

    monkeypatch.setattr(manifestation, "_manifestation_pipeline", explode)
    request = inward(_request(tmp_path / "artifact"))
    first = manifest_artifact(request)
    second = manifest_artifact(request)
    assert first == second
    assert first["state"] == "invalid"
    assert first["value"]["error"] == "unhandled-failure"
    assert first["value"]["ticket"]["message"] == "[redacted-message]"
    assert "secret" not in json.dumps(first)
    assert first["evidence"][-2:] == ("ticket.open", "processing.failed")
