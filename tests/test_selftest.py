"""The repository-owned test boundary is dependency-free and Standard Ten."""

import ast
import os
import threading
import time
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
        "__future__", "argparse", "concurrent", "contextlib", "importlib",
        "inspect", "io", "json", "os", "pathlib", "re", "subprocess",
        "sys", "tempfile", "time", "types", "unittest"
    }


def test_parallel_shards_are_concurrent_and_aggregated_in_source_order(monkeypatch):
    active = {"count": 0, "maximum": 0}
    lock = threading.Lock()

    def boundary(item):
        ordinal, paths, _profile = item
        with lock:
            active["count"] += 1
            active["maximum"] = max(active["maximum"], active["count"])
        time.sleep(0.01 if ordinal == 0 else 0.001)
        with lock:
            active["count"] -= 1
        return ordinal, {
            "passed": 1,
            "skipped": 0,
            "failed": 0,
            "total": 1,
            "failures": [],
            "ok": True,
            "results": [{"id": paths[0].name, "status": "pass", "error": None}],
        }

    monkeypatch.setattr(selftest, "_run_shard_boundary", boundary)
    reports = selftest._parallel_reports(
        (Path("second.py"), Path("first.py")), workers=2, profile="complete"
    )
    assert active["maximum"] == 2
    assert [report["results"][0]["id"] for report in reports] == [
        "second.py",
        "first.py",
    ]


def test_parallel_runner_preserves_failures_and_counts(tmp_path):
    passing = tmp_path / "test_a.py"
    failing = tmp_path / "test_b.py"
    passing.write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    failing.write_text("def test_bad():\n    assert False\n", encoding="utf-8")
    report = selftest.run((passing, failing), workers=2, profile="complete")
    assert report["passed"] == 1
    assert report["failed"] == 1
    assert report["total"] == 2
    assert report["workers"] == 2
    assert report["failures"][0]["id"] == "test_b.py::test_bad[0]"


def test_local_profile_excludes_physical_suites_and_complete_profile_keeps_them():
    local, local_name = selftest._files(("tests",), "local")
    complete, complete_name = selftest._files(("tests",), "complete")
    local_names = {path.name for path in local}
    complete_names = {path.name for path in complete}
    assert local_name == "local"
    assert complete_name == "complete"
    assert "test_application_assembly.py" not in local_names
    assert "test_l13.py" not in local_names
    assert "test_application_assembly.py" in complete_names
    assert "test_l13.py" in complete_names
    assert local_names < complete_names


def test_unknown_profile_fails_closed():
    with selftest.raises(ValueError, match="selftest:unknown-profile"):
        selftest._files(("tests",), "unregistered")


def test_complete_profile_is_bound_to_github_physical_evidence():
    root = Path(__file__).resolve().parents[1]
    graph = __import__("json").loads(
        (root / "seed/verification/PROOF_GRAPH.json").read_text()
    )
    repository = next(
        node for node in graph["evidence_nodes"] if node["id"] == "repository-tests"
    )
    assert repository["argv"][-2:] == ["--profile", "complete"]
    workflow = (root / ".github/workflows/test.yml").read_text()
    assert "physical_evidence:" in workflow
    assert 'UC_VERIFY_MATERIALIZE: "1"' in workflow
    assert "physical-proof-bundle" in workflow
