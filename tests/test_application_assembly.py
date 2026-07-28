"""Five real generated applications and one bounded assembly contract."""

from __future__ import annotations

import copy
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from unified.boundary import inward
from unified.generator.assembly import (
    DEPTHS,
    STAGES,
    _canonical,
    _atomic_preservation_probe,
    _file_hashes,
    _ordered_seeds,
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
        assert not validate_application(load(path)), path


def test_five_applications_generate_install_execute_and_pass_ten_depths(tmp_path):
    output = tmp_path / "suite"
    result = run_assemble(thing(SUITE, output))
    assert result["state"] == "valid", result["value"]
    value = result["value"]
    assert value["applications"] == [
        "calculator",
        "file-editor",
        "file-reader",
        "math-library",
        "pong-game",
    ]
    reports = value["manifest"]["reports"]
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
        assert all((output / "applications" / name / path).is_file() for path in manifest["seven_generated_files"])
        assert (output / "installation" / name / "tests" / "test_generated.py").is_file()
        assert (output / "installation" / name / "bin" / name).is_file()
        assert (output / "installation" / name / "bin" / f"{name}-gui").is_file()
        assert (output / "installation" / name / "browser" / "index.html").is_file()
        assert (output / "installation" / name / "browser" / "style.css").is_file()
        assert (output / "installation" / name / "browser" / "browser.js").is_file()
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
            str(output / "installation" / "file-reader" / "bin" / "file-reader"),
            "--request",
            json.dumps({"action": "read", "path": "entry.txt"}),
            "--root",
            str(fixture),
        ],
        cwd=output / "installation" / "file-reader",
        text=True,
        capture_output=True,
        check=False,
    )
    assert entry.returncode == 0
    assert json.loads(entry.stdout)["output"]["content"] == "entry proof"


def test_repeated_independent_assembly_is_byte_identical(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    assert run_assemble(thing(SUITE, first))["state"] == "valid"
    assert run_assemble(thing(SUITE, second))["state"] == "valid"
    assert tree_bytes(first) == tree_bytes(second)


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
        application = seed["application"]
        value_mapping = {
            application["name"]: "unseen-" + application["name"],
            application["package"]: "unseen_" + application["package"],
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
    calculator["program"]["operators"] = {
        symbol: vocabulary_maps["math-library"].get(operation, operation)
        for symbol, operation in calculator["program"]["operators"].items()
    }
    calculator_path.write_text(json.dumps(calculator, indent=2, sort_keys=True) + "\n")

    output = tmp_path.with_name(tmp_path.name + "-installation")
    suite = source_root / "seed" / "application_suite.json"
    first = run_assemble(thing(suite, output))
    assert first["state"] == "valid", first["value"]
    assert set(first["value"]["applications"]) == set(renamed_names.values())
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
    library = output / "installation" / "math-library" / "math_library" / "library.py"
    text = library.read_text()
    library.write_text(text.replace("LIBRARY_IDENTITY = '", "LIBRARY_IDENTITY = 'altered-"))
    environment = dict(os.environ)
    environment["PYTHONPATH"] = os.pathsep.join(
        str(output / "installation" / name)
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
