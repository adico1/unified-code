"""The repository-owned test boundary is dependency-free and Standard Ten."""

import ast
import os
from pathlib import Path

from unified import selftest


@selftest.mark.parametrize("value", (1, 2, 3))
def test_parametrization_and_plain_assertions(value):
    assert value in {1, 2, 3}


def test_raises_contract():
    with selftest.raises(ValueError, match="registered-error") as observed:
        raise ValueError("registered-error")
    assert str(observed.value) == "registered-error"


def test_owned_fixtures_restore_process_state(tmp_path, monkeypatch, capsys):
    original = Path.cwd()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("UC_SELFTEST_PROBE", "formed")
    print("visible")
    captured = capsys.readouterr()
    assert captured.out == "visible\n"
    assert os.environ["UC_SELFTEST_PROBE"] == "formed"
    monkeypatch.chdir(original)


def test_runner_has_no_user_defined_classes_or_third_party_imports():
    source = Path(selftest.__file__).read_text()
    tree = ast.parse(source)
    assert not [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
    imports = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imports |= {
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    assert imports <= {
        "__future__", "argparse", "contextlib", "importlib", "inspect", "io",
        "json", "os", "pathlib", "re", "sys", "tempfile", "time", "types",
        "unittest"
    }
