"""Generated tests derived from acceptance declarations."""

import json
import tempfile
from pathlib import Path

from file_reader import cli, runtime

execute = cli.execute

CASES = json.loads((Path(__file__).parent / "acceptance.json").read_text())


def _run_declared(tmp_path, selected):
    for scenario in CASES:
        root = tmp_path / scenario["id"]
        root.mkdir(exist_ok=True)
        for fixture in scenario.get("fixtures", []):
            path = root / fixture["path"]
            if fixture.get("directory"):
                path.mkdir(parents=True, exist_ok=True)
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(bytes.fromhex(fixture["hex"]) if "hex" in fixture else fixture.get("text", "").encode(fixture.get("encoding", "utf-8")))
        for step in scenario["steps"]:
            actual = execute(step["request"], str(root))
            if selected(step["expect"]):
                assert actual == step["expect"]


def test_generated_unit_cases(tmp_path):
    _run_declared(tmp_path, lambda expected: expected["state"] == "valid")


def test_generated_failure_cases(tmp_path):
    _run_declared(tmp_path, lambda expected: expected["state"] == "invalid")


def test_generated_integration_scenarios(tmp_path):
    _run_declared(tmp_path, lambda expected: True)


def test_generated_domain_and_composition_have_no_control_flow():
    import ast
    package_root = Path(__file__).parents[1] / 'file_reader'
    forbidden = (ast.If, ast.For, ast.While, ast.Try, ast.Match, ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)
    for path in sorted(package_root.glob("stage_*.py")) + [
        package_root / "domain.py",
        package_root / "routes.py",
        package_root / "boundaries.py",
        package_root / "compose.py",
    ]:
        tree = ast.parse(path.read_text())
        assert not [type(node).__name__ for node in ast.walk(tree) if isinstance(node, forbidden)]


def test_unhandled_failure_is_redacted_and_deterministic():
    def explode(_thing):
        raise RuntimeError("secret-token")

    original_program = cli.program
    cli.program = explode
    try:
        first = execute({}, ".")
        second = execute({}, ".")
    finally:
        cli.program = original_program
    assert first == second
    assert first["error"] == "unhandled-failure"
    assert first["ticket"]["message"] == "[redacted-message]"
    assert "secret-token" not in json.dumps(first)



def run():
    checks = [
        ("unit", lambda root: test_generated_unit_cases(root)),
        ("failure", lambda root: test_generated_failure_cases(root)),
        ("integration", lambda root: test_generated_integration_scenarios(root)),
        ("source-laws", lambda _root: test_generated_domain_and_composition_have_no_control_flow()),
        ("ticket", lambda _root: test_unhandled_failure_is_redacted_and_deterministic()),
    ]
    checks = [item for item in checks if item]
    results = []
    with tempfile.TemporaryDirectory(prefix="uc-generated-self-test-") as temporary:
        root = Path(temporary)
        for identity, operation in checks:
            check_root = root / identity
            check_root.mkdir()
            try:
                operation(check_root)
            except BaseException as error:
                results.append({"id": identity, "ok": False, "error": type(error).__name__})
            else:
                results.append({"id": identity, "ok": True, "error": None})
    return {
        "passed": sum(item["ok"] for item in results),
        "total": len(results),
        "results": results,
    }


if __name__ == "__main__":
    report = run()
    print(json.dumps(report, separators=(",", ":"), sort_keys=True))
    raise SystemExit(0 if report["passed"] == report["total"] else 1)
