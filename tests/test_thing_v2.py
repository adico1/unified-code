"""Thing v2 compile-time specialization, isolation, churn, and refusal proofs."""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path

from unified.boundary import inward
from unified.generator.cli import _parse_argv
from unified.generator.thing_v2 import (
    STAGE_NAMES,
    _file_hashes,
    foreign_fixture_sha256,
    proof_application_vocabulary,
    render_files,
    run_compile,
    validate_seed,
    vocabulary_mutation_report,
    vocabulary_report,
)


ROOT = Path(__file__).resolve().parents[1]
NATIVE_SEED = ROOT / "seed" / "thing_v2" / "trajectory_meter.json"
FOREIGN_SEED = ROOT / "seed" / "thing_v2" / "orchard_yield.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value: dict) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _compile(seed_path: Path, output: Path) -> dict:
    result = run_compile(
        inward(
            {
                "command": "compile",
                "seed_path": str(seed_path),
                "output": str(output),
                "verify": True,
            }
        )
    )
    assert result["state"] == "valid", result["value"]
    return result["value"]


def _tree_bytes(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
        and "__pycache__" not in path.parts
        and ".uc-cache" not in path.parts
    }


def _change_outer_output(seed: dict) -> None:
    seed["formats"]["outer_output"]["kind"] = "json_text"
    seed["selected_adapters"]["outer_output"] = "json_text"
    for case in seed["acceptance"]:
        expected = case["expect"]
        if expected["state"] == "valid":
            expected["output"] = json.dumps(
                expected["output"],
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            )


def _change_coefficient(seed: dict) -> None:
    old = seed["computation_seed"]["coefficient"]
    new = old + 1
    bias = seed["compile_time_constants"]["bias"]
    input_field = seed["computation_seed"]["input_field"]
    parameter = seed["computation_seed"]["runtime_parameter"]
    output_field = seed["computation_seed"]["output_field"]
    seed["computation_seed"]["coefficient"] = new
    for case in seed["acceptance"]:
        expected = case["expect"]
        if expected["state"] == "valid":
            outer = case["outer_input"]
            value = outer[input_field] * case["runtime_params"][parameter] * new + bias
            expected["output"] = {output_field: value}


def test_public_compile_contract_and_seed_validation():
    parsed = _parse_argv(
        ["compile", "seed.json", "--output", "generated", "--verify"]
    )
    assert parsed == {
        "command": "compile",
        "seed_path": "seed.json",
        "output": "generated",
        "verify": True,
    }
    assert _parse_argv(["compile", "seed.json", "--output", "generated"])[
        "error"
    ] == "usage-compile-requires-verify"
    assert validate_seed(_load(NATIVE_SEED)) == []
    assert validate_seed(_load(FOREIGN_SEED)) == []
    malformed = _load(NATIVE_SEED)
    malformed["formats"]["outer_input"] = "object"
    assert "formats.outer_input:invalid" in validate_seed(malformed)


def test_compile_refuses_an_output_that_contains_its_seed():
    result = run_compile(
        inward(
            {
                "command": "compile",
                "seed_path": str(NATIVE_SEED),
                "output": str(ROOT),
                "verify": True,
            }
        )
    )
    assert result["state"] == "invalid"
    assert result["value"]["error"] == "unsafe-output-path"


def test_both_proofs_compile_seedless_and_fixed_point(tmp_path):
    for seed_path in (NATIVE_SEED, FOREIGN_SEED):
        seed = _load(seed_path)
        output = tmp_path / seed["application"]["name"]
        value = _compile(seed_path, output)
        manifest = value["manifest"]
        package = seed["application"]["package"]
        assert manifest["seven_generated_files"] == [
            f"{package}/{name}" for name in STAGE_NAMES
        ]
        assert all(manifest["verification"].values())
        fixed = value["verification"]["fixed_point"]
        assert fixed["tree_sha256_a"] == fixed["tree_sha256_b"]
        assert fixed["manifest_sha256_a"] == fixed["manifest_sha256_b"]
        assert value["verification"]["runtime_seed_absence"]["hits"] == []
        assert value["verification"]["seedless_copy"]["ok"]
        assert value["acceptance_outputs"]
        runtime = (tmp_path / seed["application"]["name"] / package / "runtime.py")
        runtime_text = runtime.read_text(encoding="utf-8")
        selected = (
            "_native_core"
            if seed["core"]["mode"] == "native"
            else "_foreign_core"
        )
        unselected = "_foreign_core" if selected == "_native_core" else "_native_core"
        assert f"def {selected}(" in runtime_text
        assert f"def {unselected}(" not in runtime_text
        repeated = tmp_path / f"{seed['application']['name']}-repeated"
        repeated_value = _compile(seed_path, repeated)
        assert repeated_value["tree_sha256"] == value["tree_sha256"]
        assert _tree_bytes(repeated) == _tree_bytes(output)


def test_foreign_fixture_provenance_and_exception_conversion(tmp_path):
    seed = _load(FOREIGN_SEED)
    value = _compile(FOREIGN_SEED, tmp_path / "foreign")
    provenance = value["manifest"]["foreign_dependency"]
    assert provenance["verified"]
    assert provenance["actual_fixture_sha256"] == foreign_fixture_sha256()
    failure = value["acceptance_outputs"][1]
    assert failure["exit"] == 1
    assert failure["output"]["error"] == "foreign-core-failure"
    assert "raw fixture detail" not in json.dumps(failure)
    runtime = (
        tmp_path / "foreign" / seed["application"]["package"] / "runtime.py"
    ).read_text(encoding="utf-8")
    assert "def _foreign_core(" in runtime
    assert "def _native_core(" not in runtime


def test_derived_vocabulary_absence_and_every_surface_mutation():
    seeds = (_load(NATIVE_SEED), _load(FOREIGN_SEED))
    vocabulary = proof_application_vocabulary(seeds)
    assert vocabulary == (
        "bundles",
        "distance",
        "duration",
        "harvest",
        "meter",
        "orchard",
        "trajectory",
        "velocity",
        "weight",
        "yield",
    )
    absence = vocabulary_report(seeds)
    mutations = vocabulary_mutation_report(seeds)
    assert absence["ok"], absence["hits"]
    assert mutations["ok"]
    assert mutations["detected"] == mutations["total"]
    assert mutations["total"] == len(vocabulary) * 5


def test_actual_affected_file_regeneration_and_byte_stability(tmp_path):
    seed_path = tmp_path / "seed.json"
    output = tmp_path / "app"
    original = _load(NATIVE_SEED)
    _write(seed_path, original)
    first = _compile(seed_path, output)
    first_hashes = first["manifest"]["generated_file_hashes"]

    described = copy.deepcopy(original)
    described["application"]["description"] += " Revised documentation."
    _write(seed_path, described)
    second = _compile(seed_path, output)
    runtime = {
        path
        for path in first_hashes
        if path.endswith(".py") and not path.startswith("tests/")
    }
    assert all(
        second["manifest"]["generated_file_hashes"][path] == first_hashes[path]
        for path in runtime
    )
    assert set(second["affected_files"]) == {
        ".thing_v2/manifest.json",
        "README.md",
        "pyproject.toml",
    }
    assert runtime <= set(second["reused_files"])

    before_mtime = _tree_bytes(output)
    os.utime(output / "trajectory_meter" / "stage_01_outer_to_inner.py", None)
    third = _compile(seed_path, output)
    assert third["tree_sha256"] == second["tree_sha256"]
    assert _tree_bytes(output) == before_mtime


def test_declared_output_and_computation_churn_boundaries(tmp_path):
    base = _load(NATIVE_SEED)
    base_files = render_files(base)
    package = base["application"]["package"]

    outer_output = tmp_path / "outer-app"
    base_path = tmp_path / "base.json"
    _write(base_path, base)
    _compile(base_path, outer_output)
    outer = copy.deepcopy(base)
    _change_outer_output(outer)
    outer_changed = {
        path
        for path, digest in _file_hashes(render_files(outer)).items()
        if _file_hashes(base_files).get(path) != digest
    }
    assert outer_changed == {
        f"{package}/stage_07_inner_to_outer.py",
        ".thing_v2/acceptance.json",
    }
    outer_path = tmp_path / "outer.json"
    _write(outer_path, outer)
    outer_value = _compile(outer_path, outer_output)
    assert set(outer_value["affected_files"]) == {
        ".thing_v2/acceptance.json",
        ".thing_v2/manifest.json",
        f"{package}/stage_07_inner_to_outer.py",
    }
    assert outer_value["manifest"]["churn_matrix"]["outer_output_format"] == [
        f"{package}/stage_07_inner_to_outer.py"
    ]

    computation_output = tmp_path / "computation-app"
    _compile(base_path, computation_output)
    computation = copy.deepcopy(base)
    _change_coefficient(computation)
    computation_changed = {
        path
        for path, digest in _file_hashes(render_files(computation)).items()
        if _file_hashes(base_files).get(path) != digest
    }
    assert computation_changed == {
        f"{package}/stage_04_core_processing.py",
        ".thing_v2/acceptance.json",
    }
    computation_path = tmp_path / "computation.json"
    _write(computation_path, computation)
    computation_value = _compile(computation_path, computation_output)
    assert set(computation_value["affected_files"]) == {
        ".thing_v2/acceptance.json",
        ".thing_v2/manifest.json",
        f"{package}/stage_04_core_processing.py",
    }
    assert computation_value["manifest"]["churn_matrix"]["computation_seed"] == [
        f"{package}/stage_04_core_processing.py"
    ]


def test_failed_verification_retains_diagnostics_and_preserves_install(tmp_path):
    output = tmp_path / "app"
    seed_path = tmp_path / "seed.json"
    seed = _load(NATIVE_SEED)
    _write(seed_path, seed)
    _compile(seed_path, output)
    installed = _tree_bytes(output)

    broken = copy.deepcopy(seed)
    broken["acceptance"][0]["expect"]["output"] = {"velocity": -999}
    _write(seed_path, broken)
    result = run_compile(
        inward(
            {
                "command": "compile",
                "seed_path": str(seed_path),
                "output": str(output),
                "verify": True,
            }
        )
    )
    assert result["state"] == "invalid"
    assert result["value"]["error"] == "compile-verification-failed"
    assert Path(result["value"]["diagnostics"]).is_dir()
    assert _tree_bytes(output) == installed
