"""Generator conformance tests. Uses temporary directories only."""

from __future__ import annotations

import subprocess
import sys
from inspect import Parameter, signature
from pathlib import Path

import pytest

from unified.boundary import inward, outward
from unified.generator import generate, run_command, validate, verify_plan, write_project
from unified.generator.cli import host_main
from unified.generator.names import is_valid_feature_name, is_valid_project_name
from unified.thing import is_thing


def _new_payload(tmp_path: Path, name: str = "demo-app") -> dict:
    return {"command": "new", "name": name, "parent": str(tmp_path)}


def _pipeline(host_value):
    return run_command(inward(host_value))


def test_uc_new_generates_expected_project(tmp_path):
    result = _pipeline(_new_payload(tmp_path, "demo-app"))
    assert result["state"] == "valid"
    root = tmp_path / "demo-app"
    assert root.is_dir()
    expected = {
        "pyproject.toml",
        "README.md",
        "demo_app/__init__.py",
        "demo_app/__main__.py",
        "demo_app/boundary.py",
        "demo_app/core.py",
        "demo_app/features.py",
        "demo_app/parts.py",
        "demo_app/compose.py",
        "tests/test_signature.py",
        "tests/test_program.py",
    }
    written = set(result["value"]["written"])
    assert expected == written
    for rel in expected:
        assert (root / rel).is_file()


def test_generated_project_imports_and_runs(tmp_path):
    result = _pipeline(_new_payload(tmp_path, "run-me"))
    assert result["state"] == "valid"
    root = tmp_path / "run-me"
    env = {**dict(**__import__("os").environ), "PYTHONPATH": str(root)}
    proc = subprocess.run(
        [sys.executable, "-m", "run_me"],
        cwd=str(root),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert "boundary:outward" in proc.stdout
    assert "part:transform" in proc.stdout


def test_generated_project_tests_pass(tmp_path):
    result = _pipeline(_new_payload(tmp_path, "test-me"))
    assert result["state"] == "valid"
    root = tmp_path / "test-me"
    proc = subprocess.run(
        [sys.executable, "-m", "pytest"],
        cwd=str(root),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_generated_public_operations_have_one_parameter(tmp_path):
    result = _pipeline(_new_payload(tmp_path, "sig-me"))
    assert result["state"] == "valid"
    root = tmp_path / "sig-me"
    sys.path.insert(0, str(root))
    try:
        import sig_me.boundary as boundary
        import sig_me.compose as compose
        import sig_me.core as core
        import sig_me.parts as parts
        from sig_me.features import FEATURES

        operations = [
            boundary.inward,
            boundary.outward,
            core.letter,
            core.verify,
            compose.program,
        ]
        for name in FEATURES:
            operations.append(getattr(parts, name))
        for operation in operations:
            parameters = tuple(signature(operation).parameters.values())
            assert len(parameters) == 1
            assert parameters[0].kind is Parameter.POSITIONAL_OR_KEYWORD
    finally:
        sys.path.remove(str(root))
        for key in list(sys.modules):
            if key == "sig_me" or key.startswith("sig_me."):
                del sys.modules[key]


def test_uc_add_creates_feature_once(tmp_path):
    created = _pipeline(_new_payload(tmp_path, "feat-me"))
    assert created["state"] == "valid"
    root = tmp_path / "feat-me"

    first = _pipeline(
        {"command": "add", "name": "double", "project_root": str(root)}
    )
    assert first["state"] == "valid"
    assert first["value"]["feature"] == "double"
    assert "double" in first["value"]["features"]

    parts_text = (root / "feat_me" / "parts.py").read_text(encoding="utf-8")
    assert parts_text.count("def double(") == 1
    compose_text = (root / "feat_me" / "compose.py").read_text(encoding="utf-8")
    assert compose_text.count("double(") == 1
    assert "double(transform(letter(inward(host_value))))" in compose_text.replace(
        " ", ""
    ) or "double(transform(" in compose_text

    second = _pipeline(
        {"command": "add", "name": "double", "project_root": str(root)}
    )
    assert second["state"] == "invalid"
    assert "validate:duplicate-feature" in second["evidence"]
    assert (root / "feat_me" / "parts.py").read_text(encoding="utf-8").count(
        "def double("
    ) == 1


def test_added_feature_is_one_in_one_out_and_in_composition(tmp_path):
    _pipeline(_new_payload(tmp_path, "one-out"))
    root = tmp_path / "one-out"
    added = _pipeline({"command": "add", "name": "mark", "project_root": str(root)})
    assert added["state"] == "valid"

    sys.path.insert(0, str(root))
    try:
        from one_out import parts
        from one_out.compose import program
        from one_out.features import FEATURES

        assert "mark" in FEATURES
        parameters = tuple(signature(parts.mark).parameters.values())
        assert len(parameters) == 1
        result = program("seed")
        assert result["state"] == "valid"
        assert "part:mark" in result["evidence"]
        assert "part:transform" in result["evidence"]
    finally:
        sys.path.remove(str(root))
        for key in list(sys.modules):
            if key == "one_out" or key.startswith("one_out."):
                del sys.modules[key]


def test_invalid_project_and_feature_names_rejected(tmp_path):
    bad_project = _pipeline(_new_payload(tmp_path, "Bad_Name"))
    assert bad_project["state"] == "invalid"
    assert "validate:invalid-project-name" in bad_project["evidence"]
    assert not (tmp_path / "Bad_Name").exists()

    ok = _pipeline(_new_payload(tmp_path, "good-name"))
    assert ok["state"] == "valid"
    root = tmp_path / "good-name"

    bad_feature = _pipeline(
        {"command": "add", "name": "NotGood", "project_root": str(root)}
    )
    assert bad_feature["state"] == "invalid"
    assert "validate:invalid-feature-name" in bad_feature["evidence"]

    reserved = _pipeline(
        {"command": "add", "name": "letter", "project_root": str(root)}
    )
    assert reserved["state"] == "invalid"


def test_filesystem_effects_only_through_write_boundary(tmp_path, monkeypatch):
    writes: list[str] = []
    original_write_text = Path.write_text

    def tracking_write_text(self, *args, **kwargs):
        writes.append(str(self))
        return original_write_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", tracking_write_text)

    admitted = inward(_new_payload(tmp_path, "no-write-yet"))
    validated = validate(admitted)
    planned = generate(validated)
    verified = verify_plan(planned)
    assert verified["state"] == "valid"
    assert writes == []

    written = write_project(verified)
    assert written["state"] == "valid"
    assert "boundary:write_project" in written["evidence"]
    assert writes
    assert all("no-write-yet" in path or ".uc-new-" in path for path in writes)


def test_generate_failure_does_not_leave_partial_project(tmp_path, monkeypatch):
    # Force failure during create after temp staging by breaking os.replace.
    import unified.generator.write_fs as write_fs

    admitted = inward(_new_payload(tmp_path, "partial-me"))
    verified = verify_plan(generate(validate(admitted)))
    assert verified["state"] == "valid"

    def boom(*_args, **_kwargs):
        raise OSError("simulated failure")

    monkeypatch.setattr(write_fs.os, "replace", boom)
    result = write_project(verified)
    assert result["state"] == "invalid"
    assert "write:failed:OSError" in result["evidence"]
    assert not (tmp_path / "partial-me").exists()
    leftovers = list(tmp_path.glob(".uc-new-*"))
    assert leftovers == []


def test_add_failure_rolls_back(tmp_path, monkeypatch):
    created = _pipeline(_new_payload(tmp_path, "roll-me"))
    assert created["state"] == "valid"
    root = tmp_path / "roll-me"
    before_parts = (root / "roll_me" / "parts.py").read_text(encoding="utf-8")

    admitted = inward(
        {"command": "add", "name": "extra", "project_root": str(root)}
    )
    verified = verify_plan(generate(validate(admitted)))
    assert verified["state"] == "valid"

    calls = {"n": 0}
    original = Path.write_text

    def flaky(self, *args, **kwargs):
        calls["n"] += 1
        if calls["n"] >= 3:
            raise OSError("fail mid-write")
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", flaky)
    result = write_project(verified)
    assert result["state"] == "invalid"
    assert "write:rolled-back" in result["evidence"]
    assert (root / "roll_me" / "parts.py").read_text(encoding="utf-8") == before_parts
    assert "def extra(" not in before_parts


def test_generator_public_ops_one_parameter():
    for operation in (validate, generate, verify_plan, write_project, run_command, outward, inward):
        parameters = tuple(signature(operation).parameters.values())
        assert len(parameters) == 1


def test_name_helpers():
    assert is_valid_project_name("demo")
    assert is_valid_project_name("demo-app")
    assert not is_valid_project_name("Demo")
    assert not is_valid_project_name("")
    assert is_valid_feature_name("double")
    assert not is_valid_feature_name("double-feature")
    assert not is_valid_feature_name("class")


def test_host_main_new_and_add(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    code = host_main(["new", "cli-demo"])
    assert code == 0
    assert (tmp_path / "cli-demo").is_dir()

    monkeypatch.chdir(tmp_path / "cli-demo")
    code = host_main(["add", "double"])
    assert code == 0
    code = host_main(["add", "double"])
    assert code == 1


def test_unknown_absent_false_remain_distinct_in_generator():
    absent = validate(inward(None))
    false = validate(inward(False))
    unknown = inward({"command": "new"})
    assert absent["state"] == "absent"
    assert false["state"] == "false"
    assert unknown["state"] == "unknown"
    assert len({absent["state"], false["state"], unknown["state"]}) == 3
