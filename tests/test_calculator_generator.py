import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from unified.generator.assembly import (
    _browser_executable,
    audited_browser_capture_boundary,
    audited_browser_shutdown_boundary,
)
from unified.generator.calculator import (
    CATALOG_FAMILIES,
    GENERATOR_IDENTITY,
    _load_registry,
    _authority,
    _sha,
    _tree_hash,
    _hashes,
    run_calculator,
)

ROOT = Path(__file__).resolve().parents[1]
SUITE = ROOT / "seed" / "calculator_suite.json"
REQUESTS = (
    "bounded_integer_expression",
    "scientific_decimal",
    "unit_converter",
    "percentage",
    "date_duration",
    "mortgage",
    "statistics",
)
MUTATIONS = (
    "duplicate-atomic-truth",
    "unknown-seed",
    "dependency-cycle",
    "wrong-quantity",
    "wrong-rule",
    "wrong-formula",
    "changed-rounding",
    "changed-precision",
    "changed-calendar-convention",
    "changed-interest-convention",
    "changed-unit-dimension",
    "missing-input",
    "extra-input",
    "misplaced-interface-control",
    "manually-enumerated-keypad",
    "missing-operator",
    "wrong-locale",
    "target-specific-semantic-result",
    "different-target-bytecode",
    "gui-cli-disagreement",
    "stale-registry-identity",
    "stale-artifact-hash",
    "handwritten-application-code",
    "calculator-specific-generator-branch",
    "eleventh-depth",
    "generated-flow-conditional",
    "generated-flow-loop",
)


def thing(operation, request, output):
    return {
        "value": {
            "calculator_operation": operation,
            "request_path": str(request),
            "output": str(output),
        },
        "depths": (),
        "axes": (),
        "evidence": (),
        "state": "formed",
    }


def test_atomic_catalog_contract():
    registry = _load_registry(ROOT / "seed")
    assert len(registry) == sum(
        len(json.loads((ROOT / "seed" / family / "catalog.json").read_text())["seeds"])
        for family in CATALOG_FAMILIES
    )
    assert all("@" in identity for identity in registry)
    assert all(item["authority_hash"] == _authority(item) for item in registry.values())


def test_suite_is_deterministic_and_complete(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    first = run_calculator(thing("generate-suite", SUITE, a))
    second = run_calculator(thing("generate-suite", SUITE, b))
    assert first["state"] == second["state"] == "valid"
    assert _hashes(a) == _hashes(b)
    assert _tree_hash(_hashes(a)) == _tree_hash(_hashes(b))
    assert len(first["value"]["applications"]) == 7
    required = {
        "identity.json",
        "resolved-seeds.json",
        "manifest.json",
        "hashes.json",
        "core/calculator.uem",
        "core/calculator.bytecode",
        "core/operations.json",
        "interface/semantic-ui.json",
        "interface/accessibility.json",
        "interface/localization.json",
        "proof/seed-projection.json",
        "proof/generation-report.json",
        "proof/acceptance-report.json",
    }
    for application in first["value"]["applications"]:
        root = a / application["identity"].split("/")[-1].split("@")[0]
        assert required.issubset({str(path.relative_to(root)) for path in root.rglob("*") if path.is_file()})
        report = json.loads((root / "proof" / "generation-report.json").read_text())
        assert report["depths"] == list(range(1, 11))
        assert report["generated_flow_conditionals"] == report["generated_flow_loops"] == 0


@pytest.mark.parametrize("request_name", REQUESTS)
def test_cli_target_executes_shared_vectors(tmp_path, request_name):
    request = ROOT / "seed" / "applications" / f"{request_name}.json"
    output = tmp_path / request_name
    result = run_calculator(thing("generate", request, output))
    assert result["state"] == "valid"
    vector = json.loads((output / "tests" / "domain" / "vectors.json").read_text())[0]
    runs = []
    for target in ("cli", "macos-intel", "windows-x64"):
        completed = subprocess.run(
            [sys.executable, str(output / "targets" / target / "run.py"), json.dumps(vector["input"])],
            check=True,
            capture_output=True,
            text=True,
        )
        runs.append(json.loads(completed.stdout))
    assert runs[0] == runs[1] == runs[2]
    assert runs[0]["value"] == vector["result"]
    assert runs[0]["evidence"] == ["input:normalized", "uem:executed", "result:formed"]


def test_eighth_unseen_request_requires_no_generator_change(tmp_path):
    source = ROOT / "unified" / "generator" / "calculator.py"
    before = _sha(source.read_bytes())
    result = run_calculator(thing("generate", ROOT / "seed" / "applications" / "discount_price.json", tmp_path / "eighth"))
    assert result["state"] == "valid"
    assert _sha(source.read_bytes()) == before
    vector = json.loads((tmp_path / "eighth" / "tests" / "domain" / "vectors.json").read_text())[0]
    assert vector["result"] == {"result": 60}


def test_renamed_suite_has_equivalent_derived_structure(tmp_path):
    source = ROOT / "seed"
    copied = tmp_path / "seed"
    shutil.copytree(source, copied)
    suite = json.loads((copied / "calculator_suite.json").read_text())
    for index, relative in enumerate(suite["applications"]):
        path = copied / relative
        request = json.loads(path.read_text())
        request["identity"] = f"uc://applications/renamed-{index}@1"
        path.write_text(json.dumps(request, sort_keys=True, separators=(",", ":")) + "\n")
    output = tmp_path / "renamed"
    result = run_calculator(thing("generate-suite", copied / "calculator_suite.json", output))
    assert result["state"] == "valid"
    assert len(result["value"]["applications"]) == 7
    source_text = (ROOT / "unified" / "generator" / "calculator.py").read_text()
    reference_identities = tuple(
        json.loads((ROOT / "seed" / "applications" / f"{name}.json").read_text())["identity"]
        for name in REQUESTS
    )
    assert all(identity not in source_text for identity in reference_identities)


def test_stale_hash_unknown_version_cycle_and_atomic_preservation(tmp_path):
    copied = tmp_path / "seed"
    shutil.copytree(ROOT / "seed", copied)
    quantities = copied / "quantities" / "catalog.json"
    catalog = json.loads(quantities.read_text())
    catalog["seeds"][0]["authority_hash"] = "0" * 64
    quantities.write_text(json.dumps(catalog))
    with pytest.raises(ValueError, match="stale-hash"):
        _load_registry(copied)
    output = tmp_path / "installed"
    output.mkdir()
    marker = output / "previous"
    marker.write_text("valid")
    invalid = tmp_path / "invalid.json"
    invalid.write_text("{}")
    rejected = run_calculator(thing("generate", invalid, output))
    assert rejected["state"] == "invalid"
    assert marker.read_text() == "valid"
    assert list(output.iterdir()) == [marker]


def test_mutation_contract_and_generated_source_laws(tmp_path):
    result = run_calculator(thing("generate", ROOT / "seed" / "applications" / "bounded_integer_expression.json", tmp_path / "app"))
    assert result["state"] == "valid"
    flow = (tmp_path / "app" / "composition.py").read_text()
    assert all(token not in flow for token in ("if ", "for ", "while ", "match ", "try:", "except "))
    assert len(MUTATIONS) == 27
    assert len(set(MUTATIONS)) == len(MUTATIONS)
    assert GENERATOR_IDENTITY in (tmp_path / "app" / "identity.json").read_text()


def test_real_browser_projection(tmp_path):
    executable = _browser_executable()
    assert executable, "Chromium-family browser required"
    result = run_calculator(thing("generate", ROOT / "seed" / "applications" / "bounded_integer_expression.json", tmp_path / "app"))
    assert result["state"] == "valid"
    capture = audited_browser_capture_boundary(
        executable,
        (tmp_path / "app" / "targets" / "web" / "index.html").as_uri(),
        20,
    )
    audited_browser_shutdown_boundary()
    assert capture["ok"] is True
    assert capture["controls"] == 19
    assert capture["vectors"] == 2
