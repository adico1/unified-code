"""Vertical proof for request adapters -> canonical declaration -> UEM."""

import ast
import json
from pathlib import Path

from unified import selftest
from unified.boundary import inward
from unified.generator.cli import _parse_argv
from unified.run_pipeline import run_ephemeral


ROOT = Path(__file__).resolve().parents[1]
REQUESTS = ROOT / "examples" / "run"


def _run(name, materialize=None):
    value = {"request_path": str(REQUESTS / name)}
    if materialize is not None:
        value["materialize"] = str(materialize)
    return run_ephemeral(inward(value))


def test_json_and_restricted_python_are_one_execution():
    json_result = _run("invoice-total.request.json")
    python_result = _run("invoice-total.request.py")
    assert json_result["state"] == python_result["state"] == "valid"
    for field in (
        "canonical_seed_sha256", "program_sha256", "execution_identity",
        "runtime_result",
    ):
        assert json_result["value"][field] == python_result["value"][field]
    assert json_result["value"]["runtime_result"]["stats"] == {
        "subtotal": "20.00", "tax": "2.00", "total": "22.00",
        "item_count": 1,
    }
    assert json_result["value"]["materialized"] is False
    assert python_result["value"]["materialized"] is False


def test_materialization_is_explicit_and_deterministic(tmp_path):
    first = _run("invoice-total.request.json", tmp_path / "first")
    second = _run("invoice-total.request.py", tmp_path / "second")
    assert first["state"] == second["state"] == "valid"
    first_files = {
        item.relative_to(tmp_path / "first").as_posix(): item.read_bytes()
        for item in (tmp_path / "first").rglob("*") if item.is_file()
    }
    second_files = {
        item.relative_to(tmp_path / "second").as_posix(): item.read_bytes()
        for item in (tmp_path / "second").rglob("*") if item.is_file()
    }
    assert first_files == second_files
    manifest = json.loads(first_files["manifest.json"])
    assert manifest["program_sha256"] == first["value"]["program_sha256"]


def test_ephemeral_execution_writes_no_files(tmp_path):
    declaration = ROOT / "seed" / "declarations" / "invoice_total.json"
    request = tmp_path / "request.json"
    request.write_text(
        json.dumps(
            {
                "standard": "uc.run-request/1",
                "declaration": str(declaration),
                "host_input": {"document": {"items": [], "tax_rate": "0"}},
            }
        ),
        encoding="utf-8",
    )
    before = {item.name: item.read_bytes() for item in tmp_path.iterdir()}
    result = run_ephemeral(inward({"request_path": str(request)}))
    after = {item.name: item.read_bytes() for item in tmp_path.iterdir()}
    assert result["state"] == "valid"
    assert before == after


def test_atomic_replacement_restores_previous_tree(tmp_path, monkeypatch):
    output = tmp_path / "artifact"
    first = _run("invoice-total.request.json", output)
    assert first["state"] == "valid"
    previous = {
        item.relative_to(output).as_posix(): item.read_bytes()
        for item in output.rglob("*") if item.is_file()
    }
    replace = Path.replace

    def fail_stage(source, target):
        if ".stage-" in source.name:
            raise OSError("injected-publish-failure")
        return replace(source, target)

    monkeypatch.setattr(Path, "replace", fail_stage)
    failed = _run("invoice-total.request.py", output)
    restored = {
        item.relative_to(output).as_posix(): item.read_bytes()
        for item in output.rglob("*") if item.is_file()
    }
    assert failed["state"] == "invalid"
    assert failed["value"]["error"].startswith("materialize-failed:")
    assert previous == restored
    assert not list(tmp_path.glob(".artifact.stage-*"))
    assert not list(tmp_path.glob(".artifact.backup-*"))


def test_restricted_python_cannot_execute(tmp_path):
    marker = tmp_path / "executed"
    request = tmp_path / "bad.py"
    request.write_text(
        "from pathlib import Path\n"
        f"Path({str(marker)!r}).write_text('bad')\n"
        "STANDARD_TEN = {}\n",
        encoding="utf-8",
    )
    result = run_ephemeral(inward({"request_path": str(request)}))
    assert result["state"] == "invalid"
    assert result["value"]["error"].startswith("request-invalid:")
    assert not marker.exists()


@selftest.mark.parametrize(
    "document,error",
    (
        ({}, "request-fields-invalid"),
        ({"standard": "wrong", "declaration": "x", "host_input": {}}, "request-standard-invalid"),
        ({"standard": "uc.run-request/1", "declaration": "x.py", "host_input": {}}, "canonical-json-declaration-required"),
    ),
)
def test_expected_request_rejections(tmp_path, document, error):
    request = tmp_path / "request.json"
    request.write_text(json.dumps(document), encoding="utf-8")
    result = run_ephemeral(inward({"request_path": str(request)}))
    assert result["state"] == "invalid"
    assert result["value"]["error"] == error
    assert "artifact:materialized" not in result["evidence"]


def test_production_pipeline_has_no_user_classes_or_dynamic_execution():
    source = Path(run_ephemeral.__code__.co_filename).read_text(encoding="utf-8")
    tree = ast.parse(source)
    assert not [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
    calls = {
        node.func.id for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert "eval" not in calls
    assert "exec" not in calls
    assert "compile" not in calls


def test_cli_run_contract():
    assert _parse_argv(["run", "request.json"]) == {
        "command": "run",
        "request_path": "request.json",
        "materialize": None,
    }
    assert _parse_argv(
        ["run", "request.py", "--materialize", "build/request"]
    ) == {
        "command": "run",
        "request_path": "request.py",
        "materialize": "build/request",
    }
    assert _parse_argv(["run"])["error"] == "usage-run"
    assert _parse_argv(["run", "x", "--unknown"])["error"] == "unknown-flag:--unknown"
