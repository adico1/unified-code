#!/usr/bin/env python3
"""Measure one exact semantic-reuse coordinate without third-party runtime code."""

from __future__ import annotations

import argparse
import ast
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tarfile
import urllib.request
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "seed/economics/semantic-reuse-pilot.seed.json"
REPORT = ROOT / "artifacts/economics/semantic-reuse-pilot.json"
FORMAT = "uc-semantic-reuse-pilot-1"


def canonical_bytes(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def sha256_bytes(value):
    return hashlib.sha256(value).hexdigest()


def sha256_value(value):
    return sha256_bytes(canonical_bytes(value))


def _selected_nodes(source, symbols):
    tree = ast.parse(source)
    selected = []
    for symbol in symbols:
        if "." in symbol:
            class_name, function_name = symbol.split(".", 1)
            class_node = next(
                node for node in tree.body
                if isinstance(node, ast.ClassDef) and node.name == class_name
            )
            selected.append(
                next(
                    node for node in class_node.body
                    if isinstance(node, ast.FunctionDef) and node.name == function_name
                )
            )
        else:
            selected.append(
                next(
                    node for node in tree.body
                    if isinstance(node, ast.FunctionDef) and node.name == symbol
                )
            )
    return selected


def audited_source_primitive(witness, archive):
    if sha256_bytes(archive) != witness["archive_sha256"]:
        raise ValueError("witness:archive-sha256")
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as bundle:
        members = [
            member for member in bundle.getmembers()
            if member.isfile() and member.name.endswith("/" + witness["path"])
        ]
        if len(members) != 1:
            raise ValueError("witness:path")
        source_bytes = bundle.extractfile(members[0]).read()
    if sha256_bytes(source_bytes) != witness["file_sha256"]:
        raise ValueError("witness:file-sha256")
    source = source_bytes.decode("utf-8-sig")
    nodes = _selected_nodes(source, witness["symbols"])
    selected_identity = sha256_bytes(
        ast.dump(
            ast.Module(body=nodes, type_ignores=[]),
            annotate_fields=True,
            include_attributes=False,
        ).encode()
    )
    if selected_identity != witness["selected_ast_sha256"]:
        raise ValueError("witness:selected-ast-sha256")
    return nodes


def github_archive_boundary(witness):
    url = (
        f"https://codeload.github.com/{witness['repository']}/tar.gz/"
        f"{witness['commit_sha']}"
    )
    request = urllib.request.Request(url, headers={"User-Agent": "UC-SEMANTIC-REUSE-PILOT-1"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def _safe_builtins():
    return {
        "eval": eval,
        "str": str,
        "int": int,
        "range": range,
        "print": lambda *_args, **_kwargs: None,
        "SyntaxError": SyntaxError,
        "ValueError": ValueError,
        "ZeroDivisionError": ZeroDivisionError,
        "Exception": Exception,
    }


def _display(initial):
    value = [initial]
    return SimpleNamespace(
        text=lambda: value[0],
        get=lambda: value[0],
        setText=lambda item: value.__setitem__(0, item),
        set=lambda item: value.__setitem__(0, item),
        value=value,
    )


def audited_execute_witness_primitive(witness, nodes, expression):
    if re.fullmatch(r"[0-9]+(?:[+*-][0-9]+)*", expression) is None:
        raise ValueError("contract:expression-grammar")
    module = ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[]))
    namespace = {"__builtins__": _safe_builtins(), "calculation": expression}
    exec(compile(module, f"<{witness['repository']}>", "exec"), namespace)
    routes = {
        "fluxcalc-equals": lambda: namespace["_btnEqualsInput"]()[0],
        "ultimate-equals": lambda: _run_method(namespace["equals"], expression, "lineEdit"),
        "akash-result": lambda: _run_method(namespace["result"], expression, "display"),
    }
    return routes[witness["adapter"]]()


def _run_method(function, expression, argument_name):
    display = _display(expression)
    receiver = SimpleNamespace(**{argument_name: display})
    function(receiver) if argument_name == "lineEdit" else function(receiver, display)
    return int(display.value[0])


def _generated_calculator(contract):
    application = ROOT / "build/calculators/bounded-integer-expression-calculator@1/application"
    library = ROOT / "build/libraries/math-library@1/application"
    request = json.dumps(
        {"expression": f"{contract['inputs']['left']}*{contract['inputs']['right']}"},
        separators=(",", ":"),
    )
    result = subprocess.run(
        [sys.executable, str(application / "bin" / "calculator"), "--request", request],
        cwd=application,
        env={**os.environ, "PYTHONPATH": os.pathsep.join((str(application), str(library)))},
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    if result.returncode != 0:
        raise ValueError("generated:calculator-execution")
    return json.loads(result.stdout)["output"]["result"]


def _generated_todo(contract):
    path = ROOT / "build/todos/costed-todo@1/application/main.py"
    source = path.read_text(encoding="utf-8")
    node = next(
        item for item in ast.parse(source).body
        if isinstance(item, ast.FunctionDef) and item.name == "_calculation_0"
    )
    namespace = {"__builtins__": {}}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[])), str(path), "exec"), namespace)
    return namespace["_calculation_0"](
        contract["inputs"]["left"], contract["inputs"]["right"]
    )


def _file_sha(path):
    return sha256_bytes((ROOT / path).read_bytes())


def acquire(seed):
    contract = seed["contract"]
    for projection in seed["generated_projections"]:
        if _file_sha(projection["seed"]) != projection["seed_sha256"]:
            raise ValueError("generated:seed-sha256")
        if _file_sha(projection["generated_file"]) != projection["generated_file_sha256"]:
            raise ValueError("generated:file-sha256")
    witnesses = []
    for witness in seed["public_witnesses"]:
        archive = github_archive_boundary(witness)
        nodes = audited_source_primitive(witness, archive)
        actual = audited_execute_witness_primitive(
            witness,
            nodes,
            f"{contract['inputs']['left']}*{contract['inputs']['right']}",
        )
        witnesses.append(
            {
                "repository": witness["repository"],
                "commit_sha": witness["commit_sha"],
                "file_sha256": witness["file_sha256"],
                "selected_ast_sha256": witness["selected_ast_sha256"],
                "actual": actual,
                "classification": "equivalent" if actual == contract["expected"] else "different",
            }
        )
    projections = [
        {
            "identity": seed["generated_projections"][0]["identity"],
            "actual": _generated_calculator(contract),
            "seed_sha256": _file_sha(seed["generated_projections"][0]["seed"]),
            "generated_file": seed["generated_projections"][0]["generated_file"],
            "generated_file_sha256": seed["generated_projections"][0]["generated_file_sha256"],
        },
        {
            "identity": seed["generated_projections"][1]["identity"],
            "actual": _generated_todo(contract),
            "seed_sha256": _file_sha(seed["generated_projections"][1]["seed"]),
            "generated_file": seed["generated_projections"][1]["generated_file"],
            "generated_file_sha256": seed["generated_projections"][1]["generated_file_sha256"],
        },
    ]
    report = {
        "format": FORMAT,
        "seed_sha256": sha256_value(seed),
        "contract": contract,
        "public_witnesses": witnesses,
        "generated_projections": projections,
        "public_equivalent": all(item["classification"] == "equivalent" for item in witnesses),
        "generated_equivalent": all(item["actual"] == contract["expected"] for item in projections),
        "application_behavior_compiler_changes": 0,
        "source_code_published": False,
        "third_party_runtime_dependencies": [],
        "claim_boundary": seed["claim_boundary"],
    }
    return {**report, "report_sha256": sha256_value(report)}


def validate(seed, report):
    if report.get("format") != FORMAT:
        raise ValueError("report:format")
    identity = report.get("report_sha256")
    body = {key: value for key, value in report.items() if key != "report_sha256"}
    if identity != sha256_value(body):
        raise ValueError("report:sha256")
    if report.get("seed_sha256") != sha256_value(seed):
        raise ValueError("report:seed-sha256")
    if not report.get("public_equivalent") or not report.get("generated_equivalent"):
        raise ValueError("report:equivalence")
    if len(report.get("public_witnesses", ())) != 3 or len(report.get("generated_projections", ())) != 2:
        raise ValueError("report:inventory")
    if report.get("source_code_published") is not False or report.get("third_party_runtime_dependencies") != []:
        raise ValueError("report:third-party-boundary")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--acquire", action="store_true")
    arguments = parser.parse_args(argv)
    seed = json.loads(SEED.read_text(encoding="utf-8"))
    if arguments.acquire:
        report = acquire(seed)
        REPORT.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
    else:
        report = json.loads(REPORT.read_text(encoding="utf-8"))
    validate(seed, report)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
