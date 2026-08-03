"""One operation assembles the original proofs and the application catalog."""

from __future__ import annotations

import copy
import json
import os
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

from unified.boundary import inward
from unified.generator.assembly import (
    _ASSEMBLY_PROOF_CACHE,
    DEPTHS,
    STAGES,
    _canonical,
    _atomic_preservation_probe,
    _file_hashes,
    _ordered_seeds,
    audited_assembly_output_boundary,
    audited_assembly_cache_admission_boundary,
    audited_assembly_cache_publish_boundary,
    audited_assembly_cache_retain_boundary,
    audited_materialized_tree_identity_boundary,
    audited_materialized_tree_copy_boundary,
    audited_tracked_assembly_cache_boundary,
    audited_graphical_retry_boundary,
    audited_graphical_suite_boundary,
    audited_registry_authority_boundary,
    audited_registry_projection_boundary,
    derive_application_registry,
    _sha,
    derive_specification,
    render_application,
    run_assemble,
    validate_application,
    validate_suite,
)
from unified.generator.cli import _parse_argv

ROOT = Path(__file__).resolve().parents[1]
SUITE = ROOT / "seed" / "application_suite.json"
APPLICATIONS = ROOT / "seed" / "applications"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def thing(suite, output):
    return inward(
        {
            "command": "assemble",
            "suite_path": str(suite),
            "output": str(output),
            "build": True,
            "install": True,
            "verify": True,
            "gauntlet_depths": 10,
        }
    )


def test_stale_ephemeral_cache_is_discarded_and_rebuilt(tmp_path):
    cache_key = "stale-proof"
    _ASSEMBLY_PROOF_CACHE[cache_key] = {
        "output": str(tmp_path / "removed"),
        "tree_identity": "0" * 64,
        "manifest": {},
    }
    request = thing(SUITE, tmp_path / "fresh")
    assert audited_assembly_cache_admission_boundary(
        request,
        request["value"],
        tmp_path / "fresh",
        cache_key,
    ) is None
    assert cache_key not in _ASSEMBLY_PROOF_CACHE


def test_manifestation_cache_advances_without_duplicate_file_bytes(tmp_path):
    first_work = tmp_path / "first-work"
    first_output = first_work / "suite"
    first_output.mkdir(parents=True)
    (first_output / "artifact.txt").write_text("artifact", encoding="utf-8")
    audited_assembly_cache_publish_boundary(
        "probe",
        first_output,
        {"applications": {}, "application_language": {"product_ids": []}},
    )
    assert audited_assembly_cache_retain_boundary(first_work)

    second_work = tmp_path / "second-work"
    second_output = second_work / "suite"
    request = thing(SUITE, second_output)
    result = audited_assembly_cache_admission_boundary(
        request, request["value"], second_output, "probe"
    )

    assert result["state"] == "valid"
    assert not first_work.exists()
    assert (second_output / "artifact.txt").read_text(encoding="utf-8") == "artifact"
    assert _ASSEMBLY_PROOF_CACHE["probe"]["output"] == str(second_output)


def test_checked_in_materialization_is_admitted_only_by_exact_authority(tmp_path):
    build = tmp_path / "build"
    metadata = build / ".unified"
    metadata.mkdir(parents=True)
    (build / "artifact.txt").write_text("generated", encoding="utf-8")
    manifest = {
        "cache": {
            "authority_identity": "exact",
            "tree_identity": audited_materialized_tree_identity_boundary(build),
        },
        "application_language": {"verdict": "pass"},
        "reports": {
            "product": {
                "verdict": "pass",
                "depths": {identity: {} for identity in DEPTHS},
            }
        },
    }
    (metadata / "assembly-manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    admitted = audited_tracked_assembly_cache_boundary(tmp_path, "exact")
    assert admitted["stable"] is True
    assert admitted["manifest"] == manifest
    assert audited_tracked_assembly_cache_boundary(tmp_path, "stale") is None
    (build / "artifact.txt").write_text("tampered", encoding="utf-8")
    assert audited_tracked_assembly_cache_boundary(tmp_path, "exact") is None


def test_suite_cache_excludes_independently_generated_build_namespaces(tmp_path):
    source = tmp_path / "source"
    (source / "calculators").mkdir(parents=True)
    (source / ".unified").mkdir()
    (source / "holdouts").mkdir()
    (source / "README.md").write_text("generated", encoding="utf-8")
    (source / "index.json").write_text(
        json.dumps({"groups": {"calculators": 1}}), encoding="utf-8"
    )
    managed = source / "calculators" / "product.py"
    independent = source / "holdouts" / "proof.py"
    managed.write_text("managed", encoding="utf-8")
    independent.write_text("independent", encoding="utf-8")
    baseline = audited_materialized_tree_identity_boundary(source)
    independent.write_text("independent-change", encoding="utf-8")
    assert audited_materialized_tree_identity_boundary(source) == baseline
    managed.write_text("managed-change", encoding="utf-8")
    assert audited_materialized_tree_identity_boundary(source) != baseline
    destination = tmp_path / "destination"
    audited_materialized_tree_copy_boundary(source, destination)
    assert (destination / "calculators" / "product.py").is_file()
    assert not (destination / "holdouts").exists()


def test_graphical_host_bootstrap_retries_once_without_weakening_result(
    monkeypatch,
):
    attempts = iter(
        (
            {"ok": False, "error": "graphical-browser-startup"},
            {"ok": True, "checks": {"rendered": True}},
        )
    )
    shutdowns = []
    monkeypatch.setattr(
        "unified.generator.assembly._graphical_browser_proof",
        lambda _root, _seed: next(attempts),
    )
    monkeypatch.setattr(
        "unified.generator.assembly.audited_browser_shutdown_boundary",
        lambda: shutdowns.append("shutdown"),
    )
    assert audited_graphical_retry_boundary(Path("application"), {}) == {
        "ok": True,
        "checks": {"rendered": True},
    }
    assert shutdowns == ["shutdown"]


def test_graphical_suite_releases_independent_products_concurrently(monkeypatch):
    active = {"count": 0, "maximum": 0}
    lock = threading.Lock()

    def proof(root, _seed):
        with lock:
            active["count"] += 1
            active["maximum"] = max(active["maximum"], active["count"])
        time.sleep(0.01)
        with lock:
            active["count"] -= 1
        return {"ok": True, "product": root.name}

    monkeypatch.setattr(
        "unified.generator.assembly._browser_executable", lambda: "browser"
    )
    monkeypatch.setattr(
        "unified.generator.assembly.audited_browser_bootstrap_boundary",
        lambda _executable, _deadline: 1,
    )
    monkeypatch.setattr(
        "unified.generator.assembly.audited_graphical_retry_boundary", proof
    )
    roots = (Path("first"), Path("second"), Path("third"))
    seeds = {
        root.name: {"boundaries": {"acceptance_deadline_seconds": 1}}
        for root in roots
    }
    reports = audited_graphical_suite_boundary(roots, seeds)
    assert active["maximum"] == 3
    assert list(reports) == ["first", "second", "third"]


def tree_bytes(root):
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file() and "__pycache__" not in path.parts and ".pytest_cache" not in path.parts
    }


def test_public_one_operation_and_all_seed_contracts():
    parsed = _parse_argv(
        [
            "assemble",
            "seed/application_suite.json",
            "--output",
            "/tmp/suite",
            "--build",
            "--install",
            "--verify",
            "--gauntlet-depths",
            "10",
        ]
    )
    assert parsed["command"] == "assemble"
    assert parsed["gauntlet_depths"] == 10
    assert not validate_suite(load(SUITE), ROOT)
    for path in sorted(APPLICATIONS.glob("*.json")):
        if "application" not in load(path):
            continue
        assert not validate_application(load(path)), path


def test_all_applications_generate_install_execute_and_pass_ten_depths(tmp_path):
    output = tmp_path / "suite"
    result = run_assemble(thing(SUITE, output))
    assert result["state"] == "valid", result["value"]
    value = result["value"]
    normal = output / "calculators" / "normal@1"
    assert {
        "authority/request.json",
        "architecture/system-architecture.json",
        "architecture/systems.json",
        "architecture/interfaces.json",
        "specification/full-specification.json",
        "specification/specialized-specification.json",
        "source/manifestation-plan.json",
        "source/main.py",
        "application/main.py",
        "verification/precompile-evidence.json",
    } <= {
        path.relative_to(normal).as_posix()
        for path in normal.rglob("*")
        if path.is_file()
    }
    precompile = load(normal / "verification" / "precompile-evidence.json")
    assert precompile["verdict"] == "pass"
    assert precompile["manifestation_exactness"]["verdict"] == "pass"
    suite = load(SUITE)
    catalog = load(ROOT / suite["application_language"]["catalog"])
    catalog_products = {
        profile["product_identity"]
        for family in catalog["families"]
        for profile in family["profiles"]
        if profile["status"] == "proven"
    }
    direct_products = {
        load(ROOT / entry["seed"])["application"]["canonical_name"]
        for entry in suite["applications"]
    }
    assert direct_products.isdisjoint(catalog_products)
    expected_products = direct_products | catalog_products
    assert len(value["applications"]) == len(expected_products)
    assert {
        "calculator",
        "file-editor",
        "file-reader",
        "math-library",
        "pong-game",
    }.issubset(value["applications"])
    application_language = value["manifest"]["application_language"]
    assert application_language["applications"] == len(catalog_products)
    assert len(application_language["product_ids"]) == len(catalog_products)
    assert application_language["acceptance"]["passed"] == (
        application_language["acceptance"]["total"]
    )
    assert application_language["acceptance"]["total"] >= len(catalog_products)
    assert application_language["verdict"] == "pass"
    index = load(output / "index.json")
    assert index["total_products"] == len(expected_products)
    assert sum(index["groups"].values()) == len(expected_products)
    assert (output / "README.md").is_file()
    assert not (output / "applications").exists()
    assert not (output / "installation").exists()
    assert not (output / "application-language").exists()
    assert (output / ".unified" / "assembly-manifest.json").is_file()
    assert (output / ".unified" / "registry.json").is_file()
    for item in index["products"]:
        assert all((output / path).exists() for path in item["paths"].values())
    for product in application_language["product_ids"]:
        matches = tuple(
            (output / group / f"{product}@1")
            for group in ("calculators", "todos", "pong-games", "dashboards")
            if (output / group / f"{product}@1").is_dir()
        )
        assert len(matches) == 1, product
        assert (matches[0] / "application" / "main.py").is_file()
        assert (matches[0] / "verification" / "test_generated.py").is_file()
    reports = value["manifest"]["reports"]
    public_products = {
        item["id"]: output / item["paths"]["application"]
        for item in index["products"]
        if item["id"] in reports
    }
    for name, report in reports.items():
        assert report["verdict"] == "pass", (name, report)
        assert tuple(report["depths"]) == DEPTHS
        for depth in report["depths"].values():
            assert depth["checks_executed"] > 0
            assert depth["checks_failed"] == 0
            assert depth["checks_passed"] == depth["checks_executed"]
            assert depth["verdict"] == "pass"
            assert depth["evidence"]
        manifest = report["manifest"]
        assert manifest["manual_application_code_lines"] == 0
        assert manifest["manual_application_test_lines"] == 0
        assert manifest["generated_application_code_lines"] > 0
        assert manifest["generated_application_test_lines"] > 0
        assert report["verification"]["build_ok"]
        assert report["verification"]["performance_ok"]
        assert len(manifest["seven_generated_files"]) == len(STAGES) == 7
        product = public_products[name]
        assert all((product / path).is_file() for path in manifest["seven_generated_files"])
        assert (product / "tests" / "test_generated.py").is_file()
        assert (product / "bin" / name).is_file()
        assert (product / "bin" / f"{name}-gui").is_file()
        assert (product / "browser" / "index.html").is_file()
        assert (product / "browser" / "style.css").is_file()
        assert (product / "browser" / "browser.js").is_file()
    for name, report in reports.items():
        assert report["verification"]["javascript_headless_differential"]["ok"]
        graphical = report["verification"]["graphical_browser"]
        assert graphical["ok"], (name, graphical)
        assert graphical["browser_boot_count"] == 1
        assert graphical["checks"]["meaningful_title"]
        assert graphical["checks"]["required_controls"]
        assert graphical["checks"]["accessible_names"]
        assert graphical["checks"]["three_interactions"]
        assert graphical["checks"]["backend_requests"]
        assert graphical["checks"]["visible_assertions"]
        assert graphical["checks"]["visible_error"]
        assert graphical["checks"]["nonblank_render"]
        assert graphical["checks"]["repeated_exact"]
        assert graphical["checks"]["cli_gui_equal"]
        assert graphical["checks"]["clean_stop"]
        assert graphical["checks"]["copied_installation"]
    assert all(
        report["verification"]["atomic_install"]["ok"]
        for report in reports.values()
    )
    assert reports["calculator"]["manifest"]["dependency_identity"] == reports["math-library"]["manifest"]["export_identity"]

    fixture = tmp_path / "entry-fixture"
    fixture.mkdir()
    (fixture / "entry.txt").write_text("entry proof")
    entry = subprocess.run(
        [
            str(public_products["file-reader"] / "bin" / "file-reader"),
            "--request",
            json.dumps({"action": "read", "path": "entry.txt"}),
            "--root",
            str(fixture),
        ],
        cwd=public_products["file-reader"],
        text=True,
        capture_output=True,
        check=False,
    )
    assert entry.returncode == 0
    assert json.loads(entry.stdout)["output"]["content"] == "entry proof"


def test_repeated_independent_assembly_is_byte_identical(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    first_result = run_assemble(thing(SUITE, first))
    second_result = run_assemble(thing(SUITE, second))
    assert first_result["state"] == second_result["state"] == "valid"
    assert "assembly:cache-admitted" in second_result["evidence"]
    assert (
        first_result["value"]["cache_identity"]
        == second_result["value"]["cache_identity"]
    )
    assert tree_bytes(first) == tree_bytes(second)


def test_only_canonical_in_repository_build_output_is_permitted(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    assert audited_assembly_output_boundary(source, source / "build")
    assert audited_assembly_output_boundary(source, tmp_path / "external")
    assert not audited_assembly_output_boundary(source, source)
    assert not audited_assembly_output_boundary(source, source / "other")
    assert not audited_assembly_output_boundary(source, source / "build" / "nested")
    assert not audited_assembly_output_boundary(source, tmp_path)


def test_declared_churn_changes_only_responsible_specialization():
    seed = load(APPLICATIONS / "math_library.json")
    baseline = _file_hashes(render_application(seed))
    described = copy.deepcopy(seed)
    described["application"]["description"] += " revised"
    description = _file_hashes(render_application(described))
    runtime = {path for path in baseline if path.endswith(".py") and "/stage_" in path}
    assert all(baseline[path] == description[path] for path in runtime)

    formatted = copy.deepcopy(seed)
    formatted["formats"]["outer_output"] = "canonical-json"
    changed = {
        path
        for path, digest in _file_hashes(render_application(formatted)).items()
        if baseline.get(path) != digest
    }
    assert f"{seed['application']['package']}/stage_07_inner_to_outer.py" in changed
    assert not any(f"/stage_0{index}_" in path for path in changed for index in range(1, 7))

    computed = copy.deepcopy(seed)
    computed["program"]["range"] = [-10, 10]
    changed = {
        path
        for path, digest in _file_hashes(render_application(computed)).items()
        if baseline.get(path) != digest
    }
    assert f"{seed['application']['package']}/stage_04_core_processing.py" in changed
    assert not any(f"/stage_0{index}_" in path for path in changed for index in (1, 2, 3, 5, 6, 7))

    calculator = load(APPLICATIONS / "calculator.json")
    baseline_identity = _sha(_canonical(derive_specification(seed)))
    changed_identity = _sha(_canonical(derive_specification(computed)))
    baseline_calculator = _file_hashes(
        render_application(calculator, baseline_identity, seed["application"]["package"])
    )
    changed_calculator = _file_hashes(
        render_application(calculator, changed_identity, seed["application"]["package"])
    )
    dependency_changes = {
        path
        for path, digest in changed_calculator.items()
        if baseline_calculator.get(path) != digest
    }
    assert f"{calculator['application']['package']}/runtime.py" in dependency_changes
    assert f"{calculator['application']['package']}/stage_04_core_processing.py" in dependency_changes
    assert ".unified/dependency-manifest.json" in dependency_changes
    assert not any(
        f"/stage_0{index}_" in path
        for path in dependency_changes
        for index in (1, 2, 3, 5, 6, 7)
    )


def test_dependency_order_is_derived_and_cycles_are_rejected(tmp_path):
    entries = [
        (path, load(path))
        for path in sorted(APPLICATIONS.glob("*.json"), reverse=True)
        if "application" in load(path)
    ]
    ordered = [
        seed["application"]["name"]
        for _, seed in _ordered_seeds(entries)
    ]
    assert ordered.index("math-library") < ordered.index("calculator")

    source = tmp_path / "seed"
    shutil.copytree(ROOT / "seed", source)
    suite_path = source / "application_suite.json"
    suite = load(suite_path)
    calculator_path = source / "applications" / "calculator.json"
    calculator = load(calculator_path)
    math_path = source / "applications" / "math_library.json"
    math = load(math_path)
    math["dependency"] = {"application": "calculator", "interface": "library"}
    math_path.write_text(json.dumps(math, indent=2, sort_keys=True) + "\n")
    assert "applications:dependency-cycle" in validate_suite(suite, tmp_path)


def test_application_v3_registry_is_derived_from_seed_identities():
    suite = load(SUITE)
    seeds = [
        (ROOT / entry["seed"], load(ROOT / entry["seed"]))
        for entry in suite["applications"]
    ]
    manifests = {
        seed["application"]["name"]: {
            "tree_sha256": _sha(
                seed["application"]["canonical_name"].encode()
            )
        }
        for _, seed in seeds
    }
    existing, error = audited_registry_authority_boundary(ROOT)
    assert error is None
    first = derive_application_registry(
        suite, seeds, manifests, existing
    )
    second = derive_application_registry(
        suite, list(reversed(seeds)), manifests, existing
    )
    assert first == second
    records = {
        item["canonical_name"]: item
        for item in first["records"]
        if item["compiler_route"] == "application-v3"
    }
    exact = (
        "uc://applications/"
        "bounded-integer-expression-calculator@1"
    )
    assert set(records) == {
        seed["application"]["canonical_name"] for _, seed in seeds
    }
    assert records[exact]["product_family"] == "calculator"
    assert records[exact]["route_options"]["product_key"] == "calculator"
    assert "uc://applications/calculator@1" not in records


def test_registry_projection_is_materialized_by_assembly_boundary(tmp_path):
    source_root = tmp_path / "source"
    seed_path = source_root / "seed" / "applications" / "probe.json"
    seed_path.parent.mkdir(parents=True)
    seed = load(APPLICATIONS / "file_reader.json")
    seed_path.write_text(json.dumps(seed), encoding="utf-8")
    staging = tmp_path / "staging"
    staging.mkdir()
    suite = {
        "applications": [{"seed": "seed/applications/probe.json"}],
        "application_language": {
            "catalog": "seed/application_language/catalog.seed.json",
            "suite": "seed/application_language/suite.seed.json",
        },
    }
    registry, provenance = audited_registry_projection_boundary(
        source_root,
        staging,
        suite,
        [(seed_path, seed)],
        {seed["application"]["name"]: {"tree_sha256": "a" * 64}},
        {"records": [], "registry_version": 1},
    )
    assert load(source_root / "seed" / "registry.json") == registry
    assert load(source_root / "seed" / "registry.provenance.json") == provenance
    assert (source_root / "seed" / "registry.json").read_bytes() == (
        staging / "registry.json"
    ).read_bytes()


def test_registry_tamper_and_missing_seed_identity_are_rejected(tmp_path):
    source = tmp_path / "source"
    shutil.copytree(ROOT / "seed", source / "seed")
    registry = source / "seed" / "registry.json"
    registry.write_text(registry.read_text() + " ")
    _, error = audited_registry_authority_boundary(source)
    assert error == "registry-tamper"
    result = run_assemble(
        thing(
            source / "seed" / "application_suite.json",
            tmp_path / "unused-output",
        )
    )
    assert result["state"] == "invalid"
    assert result["value"]["error"] == "registry-tamper"
    assert not (tmp_path / "unused-output").exists()

    seed = load(APPLICATIONS / "calculator.json")
    del seed["application"]["canonical_name"]
    assert "application.missing:canonical_name" in validate_application(seed)
    malformed = load(APPLICATIONS / "calculator.json")
    malformed["application"]["canonical_name"] = "not-qualified"
    assert "application.canonical_name" in validate_application(malformed)
    versionless = load(APPLICATIONS / "calculator.json")
    versionless["application"]["canonical_name"] = (
        "uc://applications/versionless"
    )
    assert "application.canonical_name" in validate_application(versionless)

    duplicate_root = tmp_path / "duplicate"
    shutil.copytree(ROOT / "seed", duplicate_root / "seed")
    duplicate_path = (
        duplicate_root / "seed" / "applications" / "file_reader.json"
    )
    duplicate = load(duplicate_path)
    duplicate["application"]["canonical_name"] = (
        "uc://applications/"
        "bounded-integer-expression-calculator@1"
    )
    duplicate_path.write_text(
        json.dumps(duplicate, indent=2, sort_keys=True) + "\n"
    )
    duplicate_suite = load(
        duplicate_root / "seed" / "application_suite.json"
    )
    assert "applications:duplicate-canonical-name" in validate_suite(
        duplicate_suite, duplicate_root
    )


def test_dependency_contract_is_inherited_into_calculator_projection():
    library = load(APPLICATIONS / "math_library.json")
    calculator = load(APPLICATIONS / "calculator.json")
    specification = derive_specification(
        calculator,
        "dependency-identity",
        {
            "numeric_type": library["program"]["numeric_grammar"]["type"],
            "range": library["program"]["range"],
            "result_rules": library["program"]["result_rules"],
            "operations": sorted(library["program"]["operations"]),
            "exported_contract": library["program"]["exported_contract"],
        },
    )
    inherited = specification["resolved_dependency_contract"]
    assert inherited["numeric_type"] == "integer"
    assert inherited["range"] == [-1000000, 1000000]
    assert inherited["result_rules"]["division"] == "floor"
    assert "range" not in calculator["program"]
    assert "result_rules" not in calculator["program"]
    duplicated = copy.deepcopy(calculator)
    duplicated["program"]["range"] = [-1000000, 1000000]
    assert (
        "program.duplicated-dependency-contract:range"
        in validate_application(duplicated)
    )
    for symbol, component_id in (
        ("%", "calculator-remainder"),
        ("^", "calculator-power"),
    ):
        missing = copy.deepcopy(calculator)
        for section in missing["ui"]["layout"]["sections"]:
            section["components"] = [
                component
                for component in section["components"]
                if component["id"] != component_id
            ]
        assert (
            f"ui.expression.missing-operator:{symbol}"
            in validate_application(missing)
        )

    baseline = _file_hashes(
        render_application(
            calculator,
            "dependency-identity",
            library["application"]["package"],
            inherited,
        )
    )
    changed_range = copy.deepcopy(inherited)
    changed_range["range"] = [-100, 100]
    range_files = _file_hashes(
        render_application(
            calculator,
            "dependency-identity",
            library["application"]["package"],
            changed_range,
        )
    )
    changed_division = copy.deepcopy(inherited)
    changed_division["result_rules"]["division"] = "truncate"
    division_files = _file_hashes(
        render_application(
            calculator,
            "dependency-identity",
            library["application"]["package"],
            changed_division,
        )
    )
    assert baseline["browser/browser.js"] != range_files["browser/browser.js"]
    assert (
        baseline["canonical-specification.json"]
        != division_files["canonical-specification.json"]
    )


def test_generator_vocabulary_scanner_injections_and_renamed_behavior():
    source = (ROOT / "unified" / "generator" / "assembly.py").read_text().lower()
    forbidden = {
        "file_reader",
        "file_editor",
        "calculator",
        "pong",
        "paddle",
        "ball",
        "score",
        "replace_text",
    }
    assert not forbidden.intersection(source)
    output = run_assemble(thing(SUITE, Path(os.environ.get("TMPDIR", "/tmp")) / "uc-assembly-overfit-proof"))
    assert output["state"] == "valid"
    report = output["value"]["manifest"]["anti_hardcoding"]
    assert report["ok"]
    assert report["proof_kind"] == "literal-scanner-injection-validation"
    assert report["scanner_injections_total"] > 0
    assert (
        report["scanner_injections_detected"]
        == report["scanner_injections_total"]
    )
    behavioral = report["gui_behavioral_mutations"]
    assert behavioral["proof_kind"] == "behavioral-contract-and-source-law-mutations"
    assert behavioral["ok"]
    assert behavioral["detected"] == behavioral["total"] == 35


def test_atomic_publish_failure_during_replacement_restores_previous_tree(tmp_path):
    report = _atomic_preservation_probe(tmp_path)
    assert report == {
        "ok": True,
        "checks": {
            "failure_detected": True,
            "previous_tree_preserved": True,
            "no_partial_output": True,
            "backup_restored": True,
            "staging_retained": True,
        },
    }


def renamed_vocabulary(value, value_mapping, key_mapping):
    if isinstance(value, dict):
        return {
            key_mapping.get(key, key): renamed_vocabulary(
                nested, value_mapping, key_mapping
            )
            for key, nested in value.items()
        }
    if isinstance(value, list):
        return [
            renamed_vocabulary(item, value_mapping, key_mapping)
            for item in value
        ]
    return value_mapping.get(value, value) if isinstance(value, str) else value


def test_all_renamed_seeds_assemble_and_invalid_rebuild_preserves_output(tmp_path):
    source_root = tmp_path / "source"
    shutil.copytree(ROOT / "seed", source_root / "seed")
    renamed_names = {}
    vocabulary_maps = {}
    for seed_path in sorted((source_root / "seed" / "applications").glob("*.json")):
        seed = load(seed_path)
        if "application" not in seed:
            continue
        application = seed["application"]
        value_mapping = {
            application["name"]: "unseen-" + application["name"],
            application["package"]: "unseen_" + application["package"],
            application["canonical_name"]: (
                "uc://applications/unseen-" + application["name"] + "@7"
            ),
            **{
                operation: "unseen-" + operation
                for operation in seed["program"]["operations"]
            },
        }
        value_mapping.update(
            {
                event: "unseen-" + event
                for event in seed["program"].get("events", {}).values()
            }
        )
        initial = seed["program"].get("initial_state") or {}
        value_mapping.update(
            {
                role: "unseen-" + role
                for role in {
                    *(initial.get("actors") or {}),
                    *(initial.get("counters") or {}),
                }
            }
        )
        key_mapping = {
            name: value_mapping[name]
            for name in {
                *seed["program"]["operations"],
                *(initial.get("actors") or {}),
                *(initial.get("counters") or {}),
            }
        }
        ui_values = {
            seed["ui"]["page"]["id"],
            seed["ui"]["page"]["title"],
            seed["ui"]["page"]["description"],
            *seed["ui"]["actions"],
        }
        ui_keys = set(seed["ui"]["actions"])
        for section in seed["ui"]["layout"]["sections"]:
            ui_values.update((section["id"], section["title"]))
            for component in section["components"]:
                ui_keys.add(component["id"])
                ui_values.update(
                    item
                    for item in (
                        component.get("id"),
                        component.get("label"),
                        component.get("accessible_name"),
                        component.get("action"),
                    )
                    if item and len(item) > 1
                )
        value_mapping.update(
            {
                item: "unseen-" + item
                for item in ui_values
                if item not in value_mapping
            }
        )
        key_mapping.update(
            {
                item: value_mapping[item]
                for item in ui_keys
            }
        )
        renamed_names[application["name"]] = value_mapping[application["name"]]
        vocabulary_maps[application["name"]] = value_mapping
        seed = renamed_vocabulary(seed, value_mapping, key_mapping)
        seed_path.write_text(json.dumps(seed, indent=2, sort_keys=True) + "\n")

    calculator_path = source_root / "seed" / "applications" / "calculator.json"
    calculator = load(calculator_path)
    calculator["dependency"]["application"] = renamed_names["math-library"]
    calculator["application"]["dependency_contract_ref"] = (
        "application:" + renamed_names["math-library"]
    )
    calculator["program"]["operators"] = {
        symbol: vocabulary_maps["math-library"].get(operation, operation)
        for symbol, operation in calculator["program"]["operators"].items()
    }
    calculator_path.write_text(json.dumps(calculator, indent=2, sort_keys=True) + "\n")

    output = tmp_path.with_name(tmp_path.name + "-installation")
    suite = source_root / "seed" / "application_suite.json"
    first = run_assemble(thing(suite, output))
    assert first["state"] == "valid", first["value"]
    catalog_products = set(
        first["value"]["manifest"]["application_language"]["product_ids"]
    )
    assert set(first["value"]["applications"]) == (
        set(renamed_names.values()) | catalog_products
    )
    before = tree_bytes(output)

    seed_path = source_root / "seed" / "applications" / "file_reader.json"
    seed = load(seed_path)
    seed["program"]["engine"] = "unknown"
    seed_path.write_text(json.dumps(seed, indent=2, sort_keys=True) + "\n")
    rejected = run_assemble(thing(suite, output))
    assert rejected["state"] == "invalid"
    assert tree_bytes(output) == before


def test_calculator_rejects_altered_generated_library_identity(tmp_path):
    output = tmp_path / "suite"
    assert run_assemble(thing(SUITE, output))["state"] == "valid"
    index = load(output / "index.json")
    products = {
        item["id"]: output / item["paths"]["application"]
        for item in index["products"]
        if "application" in item["paths"]
    }
    library = products["math-library"] / "math_library" / "library.py"
    text = library.read_text()
    library.write_text(text.replace("LIBRARY_IDENTITY = '", "LIBRARY_IDENTITY = 'altered-"))
    environment = dict(os.environ)
    environment["PYTHONPATH"] = os.pathsep.join(
        str(products[name])
        for name in ("math-library", "calculator")
    )
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            "import json;from calculator_app.cli import execute;print(json.dumps(execute({'expression':'1+2'})))",
        ],
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    assert json.loads(completed.stdout)["error"] == "dependency-identity"

    library.write_text(text)
    package = library.parent
    unavailable = package.with_name("unavailable_generated_library")
    package.rename(unavailable)
    missing = subprocess.run(
        [
            sys.executable,
            "-c",
            "import json;from calculator_app.cli import execute;print(json.dumps(execute({'expression':'1+2'})))",
        ],
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    assert json.loads(missing.stdout)["error"] == "dependency-identity"
