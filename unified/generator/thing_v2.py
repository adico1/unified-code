"""Thing v2 compile-time seed specialization.

This module is the compiler boundary.  It may read and validate a JSON seed,
render specialized files, execute verification, and atomically publish a
generated tree.  Generated runtimes never import this module or retain the
source seed.
"""

from __future__ import annotations

import ast
import copy
import hashlib
import inspect
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from ..boundary import outward
from ..thing import is_thing


COMPILER_VERSION = "THING-V2-1"
STANDARD_VERSION = "TEN-1"
STAGE_NAMES = (
    "stage_01_outer_to_inner.py",
    "stage_02_inner_to_core.py",
    "stage_03_core_prepare.py",
    "stage_04_core_processing.py",
    "stage_05_core_collect.py",
    "stage_06_core_to_inner.py",
    "stage_07_inner_to_outer.py",
)
BOILERPLATE_FAMILIES = (
    "01_outer_to_inner",
    "02_inner_to_core",
    "03_core_prepare",
    "04_computation_core",
    "05_core_collect",
    "06_core_to_inner",
    "07_inner_to_outer",
)
SUCCESS_EVIDENCE = (
    "boundary:inward",
    "stage:01_outer_to_inner",
    "stage:02_inner_to_core",
    "stage:03_core_prepare",
    "stage:04_core_processing",
    "stage:05_core_collect",
    "stage:06_core_to_inner",
    "stage:07_inner_to_outer",
    "boundary:outward",
)
ALLOWED_CORE_MODES = frozenset({"native", "foreign_fixture"})
PACKAGE_RE = re.compile(r"^[a-z][a-z0-9_]*$")
NAME_RE = re.compile(r"^[a-z][a-z0-9-]*$")
HEX_64_RE = re.compile(r"^[0-9a-f]{64}$")
WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9_-]*")


def _canonical_bytes(value) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha_text(value: str) -> str:
    return _sha_bytes(value.encode("utf-8"))


def _section_hashes(seed: dict) -> dict[str, str]:
    computation = seed["computation_seed"]
    constants = seed["compile_time_constants"]
    sections = {
        "application.identity": {
            "name": seed["application"]["name"],
            "package": seed["application"]["package"],
        },
        "application.description": seed["application"]["description"],
        "formats.outer_input": seed["formats"]["outer_input"],
        "formats.inner_input": seed["formats"]["inner_input"],
        "formats.core_input": seed["formats"]["core_input"],
        "core": seed["core"],
        "computation_seed.operation": computation["operation"],
        "computation_seed.input_field": computation["input_field"],
        "computation_seed.output_field": computation["output_field"],
        "computation_seed.runtime_parameter": computation["runtime_parameter"],
        "computation_seed.coefficient": computation["coefficient"],
        "compile_time_constants.bias": constants["bias"],
        "compile_time_constants.fixture_failure_below": constants.get(
            "fixture_failure_below"
        ),
        "runtime_parameter_schema": seed["runtime_parameter_schema"],
        "formats.core_output": seed["formats"]["core_output"],
        "formats.inner_output": seed["formats"]["inner_output"],
        "formats.outer_output": seed["formats"]["outer_output"],
        "validation": seed["validation"],
        "evidence_requirements": seed["evidence_requirements"],
        "selected_adapters": seed["selected_adapters"],
        "acceptance": seed["acceptance"],
        "foreign_dependency": seed.get("foreign_dependency"),
    }
    return {
        name: _sha_bytes(_canonical_bytes(value))
        for name, value in sorted(sections.items())
    }


def _failure(thing: dict, value: dict, error: str, *marks: str) -> dict:
    return {
        **thing,
        "value": {**value, "error": error},
        "evidence": (*thing.get("evidence", ()), *marks),
        "state": "invalid",
    }


def _read_seed(seed_path: Path) -> tuple[dict | None, str | None]:
    try:
        value = json.loads(seed_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return None, f"seed-read:{type(exc).__name__}"
    if not isinstance(value, dict):
        return None, "seed-not-object"
    return value, None


def _required_evidence(seed: dict) -> tuple[str, ...]:
    value = seed.get("evidence_requirements")
    return tuple(value.get("exact") or ()) if isinstance(value, dict) else ()


def validate_seed(seed: dict) -> list[str]:
    """Return deterministic validation errors for the canonical Thing v2 seed."""
    errors = []
    required = (
        "thing_v2",
        "application",
        "formats",
        "core",
        "computation_seed",
        "compile_time_constants",
        "runtime_parameter_schema",
        "validation",
        "evidence_requirements",
        "selected_adapters",
        "acceptance",
    )
    errors.extend(f"missing:{key}" for key in required if key not in seed)
    if errors:
        return errors
    if seed.get("thing_v2") != 2:
        errors.append("thing_v2:not-2")
    application = seed.get("application")
    if not isinstance(application, dict):
        errors.append("application:not-object")
        return errors
    if not NAME_RE.fullmatch(str(application.get("name", ""))):
        errors.append("application.name:invalid")
    if not PACKAGE_RE.fullmatch(str(application.get("package", ""))):
        errors.append("application.package:invalid")
    if not isinstance(application.get("description"), str):
        errors.append("application.description:not-string")

    formats = seed.get("formats")
    format_contract = {
        "outer_input": {"object", "json_text"},
        "inner_input": {"object"},
        "core_input": {"number"},
        "core_output": {"number"},
        "inner_output": {"object"},
        "outer_output": {"object", "json_text"},
    }
    if not isinstance(formats, dict):
        errors.append("formats:not-object")
    else:
        for name, allowed in format_contract.items():
            entry = formats.get(name)
            if not isinstance(entry, dict) or entry.get("kind") not in allowed:
                errors.append(f"formats.{name}:invalid")

    core = seed.get("core")
    if not isinstance(core, dict) or core.get("mode") not in ALLOWED_CORE_MODES:
        errors.append("core.mode:invalid")
    computation = seed.get("computation_seed")
    if not isinstance(computation, dict):
        errors.append("computation_seed:not-object")
    else:
        if computation.get("operation") != "affine":
            errors.append("computation_seed.operation:unsupported")
        for key in ("input_field", "output_field", "runtime_parameter"):
            if not isinstance(computation.get(key), str) or not computation.get(key):
                errors.append(f"computation_seed.{key}:invalid")
        coefficient = computation.get("coefficient")
        if isinstance(coefficient, bool) or not isinstance(coefficient, (int, float)):
            errors.append("computation_seed.coefficient:not-number")

    constants = seed.get("compile_time_constants")
    if not isinstance(constants, dict):
        errors.append("compile_time_constants:not-object")
    else:
        bias = constants.get("bias")
        if isinstance(bias, bool) or not isinstance(bias, (int, float)):
            errors.append("compile_time_constants.bias:not-number")

    schema = seed.get("runtime_parameter_schema")
    if not isinstance(schema, dict) or not schema:
        errors.append("runtime_parameter_schema:invalid")
    elif isinstance(computation, dict):
        parameter = schema.get(computation.get("runtime_parameter"))
        if not isinstance(parameter, dict) or parameter.get("type") != "number":
            errors.append("runtime_parameter_schema:selected:invalid")

    validation = seed.get("validation")
    if not isinstance(validation, dict) or validation.get("input_type") != "number":
        errors.append("validation:invalid")
    adapters = seed.get("selected_adapters")
    if not isinstance(adapters, dict):
        errors.append("selected_adapters:not-object")
    elif isinstance(formats, dict):
        outer_input = formats.get("outer_input")
        outer_output = formats.get("outer_output")
        outer_input_kind = (
            outer_input.get("kind") if isinstance(outer_input, dict) else None
        )
        outer_output_kind = (
            outer_output.get("kind") if isinstance(outer_output, dict) else None
        )
        if adapters.get("outer_input") != outer_input_kind:
            errors.append("selected_adapters.outer_input:mismatch")
        if adapters.get("outer_output") != outer_output_kind:
            errors.append("selected_adapters.outer_output:mismatch")

    if _required_evidence(seed) != SUCCESS_EVIDENCE:
        errors.append("evidence_requirements.exact:mismatch")
    acceptance = seed.get("acceptance")
    if not isinstance(acceptance, list) or not acceptance:
        errors.append("acceptance:empty")
    else:
        for index, case in enumerate(acceptance):
            if not isinstance(case, dict):
                errors.append(f"acceptance[{index}]:not-object")
                continue
            for key in ("outer_input", "runtime_params", "expect"):
                if key not in case:
                    errors.append(f"acceptance[{index}].{key}:missing")
            expect = case.get("expect")
            if not isinstance(expect, dict):
                errors.append(f"acceptance[{index}].expect:not-object")
            else:
                if expect.get("state") not in {"valid", "invalid"}:
                    errors.append(f"acceptance[{index}].expect.state:invalid")
                if not isinstance(expect.get("evidence"), list):
                    errors.append(f"acceptance[{index}].expect.evidence:not-array")
                for key in ("output", "error"):
                    if key not in expect:
                        errors.append(f"acceptance[{index}].expect.{key}:missing")

    if isinstance(core, dict) and core.get("mode") == "foreign_fixture":
        dependency = seed.get("foreign_dependency")
        if not isinstance(dependency, dict):
            errors.append("foreign_dependency:missing")
        else:
            for key in ("name", "version", "source", "license"):
                if not isinstance(dependency.get(key), str) or not dependency.get(key):
                    errors.append(f"foreign_dependency.{key}:invalid")
            if not HEX_64_RE.fullmatch(str(dependency.get("sha256", ""))):
                errors.append("foreign_dependency.sha256:invalid")
            if dependency.get("effect") != "pure":
                errors.append("foreign_dependency.effect:invalid")
    return sorted(errors)


def _pyproject(seed: dict) -> str:
    application = seed["application"]
    return f"""[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = {application["name"]!r}
version = "0.1.0"
description = {application["description"]!r}
requires-python = ">=3.11"

[tool.setuptools.packages.find]
include = [{(application["package"] + "*")!r}]

"""


def _runtime_source(foreign: bool) -> str:
    foreign_import = (
        "from .foreign_fixture import invoke as _foreign_invoke\n"
        if foreign
        else ""
    )
    native_body = """
def _native_core(thing):
    if thing.get("state") != "formed":
        return thing
    value = thing.get("value") or {}
    prepared = value.get("_prepared") or {}
    spec = value.get("_stage") or {}
    try:
        result = (
            prepared.get("input")
            * prepared.get("parameter")
            * spec.get("coefficient")
            + prepared.get("bias")
        )
    except (TypeError, ValueError, OverflowError):
        return _invalid(thing, "native-core-failure", "stage:04_core_processing:error")
    return _advance(thing, {"_core_result": result}, "stage:04_core_processing")
"""
    foreign_body = """
def _foreign_core(thing):
    value = dict(thing.get("value") or {})
    prepared = value.get("_prepared") or {}
    spec = value.get("_stage") or {}
    try:
        raw = _foreign_invoke(
            (prepared.get("input"), prepared.get("parameter")),
            {
                "bias": prepared.get("bias"),
                "coefficient": spec.get("coefficient"),
                "failure_below": spec.get("failure_below"),
            },
        )
    except Exception:
        return _invalid(thing, "foreign-core-failure", "stage:04_core_processing:error")
    if not isinstance(raw, tuple) or len(raw) != 2 or raw[0] != "fixture-ok":
        return _invalid(thing, "foreign-core-invalid-output", "stage:04_core_processing:error")
    return _advance(
        thing,
        {"_core_result": raw[1]},
        "stage:04_core_processing",
    )
"""
    core_body = foreign_body if foreign else native_body
    return f'''"""Audited physical primitives for one specialized seven-stage target."""

import hashlib
import json

{foreign_import}
_THING_FIELDS = ("value", "depths", "axes", "evidence", "state")
_STATES = frozenset(("unknown", "absent", "false", "formed", "valid", "invalid"))


def _is_thing(thing):
    return (
        isinstance(thing, dict)
        and all(field in thing for field in _THING_FIELDS)
        and isinstance(thing.get("depths"), tuple)
        and isinstance(thing.get("axes"), tuple)
        and isinstance(thing.get("evidence"), tuple)
        and thing.get("state") in _STATES
    )


def _invalid(thing, error, mark):
    value = dict(thing.get("value") or {{}}) if isinstance(thing, dict) else {{}}
    evidence = tuple(thing.get("evidence") or ()) if isinstance(thing, dict) else ()
    return {{
        "value": {{**value, "error": error}},
        "depths": tuple(thing.get("depths") or ()) if isinstance(thing, dict) else (),
        "axes": tuple(thing.get("axes") or ()) if isinstance(thing, dict) else (),
        "evidence": (*evidence, mark),
        "state": "invalid",
    }}


def _advance(thing, updates, mark):
    value = dict(thing.get("value") or {{}})
    value.pop("_stage", None)
    return {{
        **thing,
        "value": {{**value, **updates}},
        "evidence": (*thing["evidence"], mark),
        "state": "formed",
    }}


def _inward(thing):
    if not _is_thing(thing):
        return _invalid({{}}, "not-a-thing", "boundary:inward:error")
    return {{
        **thing,
        "evidence": (*thing["evidence"], "boundary:inward"),
        "state": "formed",
    }}


def _outward(thing):
    if not _is_thing(thing):
        return _invalid({{}}, "not-a-thing", "boundary:outward:error")
    return {{
        **thing,
        "evidence": (*thing["evidence"], "boundary:outward"),
        "state": "valid" if thing["state"] == "formed" else thing["state"],
    }}


def _outer_object(thing):
    if thing.get("state") != "formed":
        return thing
    outer = (thing.get("value") or {{}}).get("outer_input")
    if not isinstance(outer, dict):
        return _invalid(thing, "invalid-outer-input", "stage:01_outer_to_inner:error")
    return _advance(thing, {{"_inner_input": dict(outer)}}, "stage:01_outer_to_inner")


def _outer_json(thing):
    if thing.get("state") != "formed":
        return thing
    outer = (thing.get("value") or {{}}).get("outer_input")
    if not isinstance(outer, str):
        return _invalid(thing, "invalid-outer-input", "stage:01_outer_to_inner:error")
    try:
        inner = json.loads(outer)
    except (TypeError, ValueError):
        return _invalid(thing, "invalid-outer-input", "stage:01_outer_to_inner:error")
    if not isinstance(inner, dict):
        return _invalid(thing, "invalid-outer-input", "stage:01_outer_to_inner:error")
    return _advance(thing, {{"_inner_input": inner}}, "stage:01_outer_to_inner")


def _inner_to_core(thing):
    if thing.get("state") != "formed":
        return thing
    value = thing.get("value") or {{}}
    spec = value.get("_stage") or {{}}
    inner = value.get("_inner_input") or {{}}
    params = value.get("runtime_params") or {{}}
    raw_input = inner.get(spec.get("input_field"))
    raw_parameter = params.get(spec.get("runtime_parameter"))
    if (
        isinstance(raw_input, bool)
        or not isinstance(raw_input, (int, float))
        or isinstance(raw_parameter, bool)
        or not isinstance(raw_parameter, (int, float))
    ):
        return _invalid(thing, "invalid-core-input", "stage:02_inner_to_core:error")
    minimum = spec.get("minimum")
    maximum = spec.get("maximum")
    if minimum is not None and raw_parameter < minimum:
        return _invalid(thing, "invalid-runtime-parameter", "stage:02_inner_to_core:error")
    if maximum is not None and raw_parameter > maximum:
        return _invalid(thing, "invalid-runtime-parameter", "stage:02_inner_to_core:error")
    return _advance(
        thing,
        {{"_core_input": {{"input": raw_input, "parameter": raw_parameter}}}},
        "stage:02_inner_to_core",
    )


def _core_prepare(thing):
    if thing.get("state") != "formed":
        return thing
    value = thing.get("value") or {{}}
    core = value.get("_core_input") or {{}}
    spec = value.get("_stage") or {{}}
    return _advance(
        thing,
        {{
            "_prepared": {{
                "input": core.get("input"),
                "parameter": core.get("parameter"),
                "bias": spec.get("bias"),
            }}
        }},
        "stage:03_core_prepare",
    )


{core_body}
def _core_collect(thing):
    if thing.get("state") != "formed":
        return thing
    result = (thing.get("value") or {{}}).get("_core_result")
    if isinstance(result, bool) or not isinstance(result, (int, float)):
        return _invalid(thing, "invalid-core-output", "stage:05_core_collect:error")
    return _advance(thing, {{"_collected": result}}, "stage:05_core_collect")


def _core_to_inner(thing):
    if thing.get("state") != "formed":
        return thing
    value = thing.get("value") or {{}}
    spec = value.get("_stage") or {{}}
    return _advance(
        thing,
        {{"_inner_output": {{spec.get("output_field"): value.get("_collected")}}}},
        "stage:06_core_to_inner",
    )


def _outer_output_object(thing):
    if thing.get("state") != "formed":
        return thing
    inner = (thing.get("value") or {{}}).get("_inner_output")
    return _advance(thing, {{"outer_output": inner}}, "stage:07_inner_to_outer")


def _outer_output_json(thing):
    if thing.get("state") != "formed":
        return thing
    inner = (thing.get("value") or {{}}).get("_inner_output")
    text = json.dumps(inner, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return _advance(thing, {{"outer_output": text}}, "stage:07_inner_to_outer")


def _ticket_payload(error_type):
    identity = hashlib.sha256(("thing-v2:" + error_type).encode("utf-8")).hexdigest()
    return {{
        "ticket_id": identity,
        "correlation_id": identity,
        "message": "[redacted-message]",
        "error_type": error_type,
    }}
'''


def _stage_source(primitive: str, spec: dict) -> str:
    return f'''"""Generated specialized Thing v2 stage."""

from .runtime import {primitive}


_SPECIALIZATION = {spec!r}


def part(thing):
    return {primitive}({{
        **thing,
        "value": {{**thing["value"], "_stage": _SPECIALIZATION}},
    }})
'''


def _compose_source(package: str) -> str:
    imports = "\n".join(
        f"from .{name[:-3]} import part as stage_{index:02d}"
        for index, name in enumerate(STAGE_NAMES, 1)
    )
    return f'''"""Generated nested Thing v2 composition."""

from .runtime import _inward, _outward
{imports}


def program(thing):
    return _outward(
        stage_07(
            stage_06(
                stage_05(
                    stage_04(
                        stage_03(
                            stage_02(
                                stage_01(
                                    _inward(thing)
                                )
                            )
                        )
                    )
                )
            )
        )
    )
'''


def _cli_source(package: str) -> str:
    return f'''"""Generated process boundary for the seedless Thing v2 target."""

import argparse
import json
import sys

from .compose import program
from .runtime import _ticket_payload


def _thing(host):
    return {{
        "value": {{
            "outer_input": host.get("outer_input"),
            "runtime_params": host.get("runtime_params") or {{}},
        }},
        "depths": (),
        "axes": (),
        "evidence": (),
        "state": "formed",
    }}


def _response(result):
    value = result.get("value") or {{}}
    return {{
        "state": result.get("state"),
        "output": value.get("outer_output"),
        "error": value.get("error"),
        "evidence": list(result.get("evidence") or ()),
    }}


def _execute(host):
    try:
        return _response(program(_thing(host)))
    except Exception as exc:
        ticket = _ticket_payload(type(exc).__name__)
        return {{
            "state": "invalid",
            "output": None,
            "error": "unhandled-failure",
            "evidence": ["ticket.open", "boundary:outward"],
            "ticket": ticket,
        }}


def main(argv=None):
    parser = argparse.ArgumentParser(prog={package!r})
    parser.add_argument("--input", required=True)
    parser.add_argument("--params", default="{{}}")
    args = parser.parse_args(argv)
    try:
        host = {{
            "outer_input": json.loads(args.input),
            "runtime_params": json.loads(args.params),
        }}
    except ValueError:
        payload = {{
            "state": "invalid",
            "output": None,
            "error": "invalid-host-json",
            "evidence": ["boundary:inward:error", "boundary:outward"],
        }}
    else:
        payload = _execute(host)
    sys.stdout.write(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        + "\\n"
    )
    return 0 if payload.get("state") == "valid" else 1
'''


def _foreign_fixture_source() -> str:
    return '''"""Foreign-API proof fixture; not a production third-party integration."""

FIXTURE_VERSION = "1"
FIXTURE_LICENSE = "CC0-1.0"


def invoke(payload, controls):
    if payload[0] < controls["failure_below"]:
        raise ValueError("raw fixture detail must not cross the adapter")
    return (
        "fixture-ok",
        payload[0] * payload[1] * controls["coefficient"] + controls["bias"],
    )
'''


def foreign_fixture_sha256() -> str:
    return _sha_text(_foreign_fixture_source())


def proof_application_vocabulary(seeds: tuple[dict, ...]) -> tuple[str, ...]:
    """Derive domain words from the proof declarations, never from a hand list."""
    words = set()
    for seed in seeds:
        application = seed["application"]
        computation = seed["computation_seed"]
        values = (
            application["name"],
            application["package"],
            computation["input_field"],
            computation["output_field"],
            computation["runtime_parameter"],
        )
        for value in values:
            words.update(
                segment.lower()
                for segment in re.split(r"[^A-Za-z0-9]+", str(value))
                if segment
            )
    return tuple(sorted(words))


def seedless_source_surfaces() -> dict[str, str]:
    """Return the permanent בלי_מה source surfaces audited for vocabulary."""
    compiler_parts = (
        validate_seed,
        _section_hashes,
        _dependency_edges,
        _stage_specs,
        render_files,
        _manifest,
        _materialize,
        _verify_tree,
        run_compile,
    )
    return {
        "seed_compiler": "\n".join(inspect.getsource(part) for part in compiler_parts),
        "transformation_boilerplate": inspect.getsource(_stage_source),
        "native_core_boilerplate": _runtime_source(False),
        "foreign_adapter_boilerplate": (
            _runtime_source(True) + "\n" + _foreign_fixture_source()
        ),
        "runtime_composition": _compose_source("seedless_target"),
    }


def vocabulary_report(
    seeds: tuple[dict, ...],
    surfaces: dict[str, str] | None = None,
) -> dict:
    """Prove proof-domain vocabulary is absent from permanent source surfaces."""
    vocabulary = proof_application_vocabulary(seeds)
    selected = seedless_source_surfaces() if surfaces is None else surfaces
    hits = []
    for surface, source in sorted(selected.items()):
        tokens = {token.lower() for token in WORD_RE.findall(source)}
        hits.extend(
            {"surface": surface, "term": term}
            for term in vocabulary
            if term in tokens
        )
    return {
        "ok": not hits,
        "vocabulary": list(vocabulary),
        "surfaces": sorted(selected),
        "hits": hits,
    }


def vocabulary_mutation_report(seeds: tuple[dict, ...]) -> dict:
    """Inject every derived term into every permanent surface and require a hit."""
    baseline = seedless_source_surfaces()
    cases = []
    for term in proof_application_vocabulary(seeds):
        for surface in sorted(baseline):
            mutated = {**baseline, surface: baseline[surface] + f"\n{term}\n"}
            report = vocabulary_report(seeds, mutated)
            detected = any(
                hit["surface"] == surface and hit["term"] == term
                for hit in report["hits"]
            )
            cases.append(
                {"surface": surface, "term": term, "detected": detected}
            )
    return {
        "ok": bool(cases) and all(case["detected"] for case in cases),
        "cases": cases,
        "detected": sum(case["detected"] for case in cases),
        "total": len(cases),
    }


def _acceptance_payload(seed: dict) -> dict:
    return {
        "compiler_version": COMPILER_VERSION,
        "package": seed["application"]["package"],
        "cases": copy.deepcopy(seed["acceptance"]),
    }


def _generated_tests_source(package: str) -> str:
    stage_imports = "\n".join(
        f"from {package} import {name[:-3]} as stage_{index:02d}"
        for index, name in enumerate(STAGE_NAMES, 1)
    )
    return f'''"""Generated Thing v2 acceptance and source-law tests."""

import ast
import inspect
import json
from pathlib import Path

from {package} import compose
from {package}.cli import _execute
{stage_imports}


ROOT = Path(__file__).resolve().parents[1]
ACCEPTANCE = json.loads(
    (ROOT / ".thing_v2" / "acceptance.json").read_text(encoding="utf-8")
)["cases"]
STAGES = (
    stage_01,
    stage_02,
    stage_03,
    stage_04,
    stage_05,
    stage_06,
    stage_07,
)


def test_acceptance_and_exact_evidence():
    for case in ACCEPTANCE:
        assert _execute(case) == case["expect"]


def test_public_parts_are_one_thing_in_one_thing_out():
    operations = [compose.program, *(module.part for module in STAGES)]
    for operation in operations:
        assert len(inspect.signature(operation).parameters) == 1


def test_stage_and_composition_source_laws():
    forbidden = (
        ast.ClassDef,
        ast.If,
        ast.For,
        ast.AsyncFor,
        ast.While,
        ast.Match,
        ast.IfExp,
        ast.Try,
        ast.ListComp,
        ast.SetComp,
        ast.DictComp,
        ast.GeneratorExp,
    )
    paths = [
        *(ROOT / {package!r} / name for name in {STAGE_NAMES!r}),
        ROOT / {package!r} / "compose.py",
    ]
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        assert not any(isinstance(node, forbidden) for node in ast.walk(tree))


def test_unhandled_failure_is_redacted_and_deterministic(monkeypatch):
    def explode(_thing):
        raise RuntimeError("token=secret-value")

    monkeypatch.setattr(compose, "stage_01", explode)
    first = _execute({{"outer_input": {{}}, "runtime_params": {{}}}})
    second = _execute({{"outer_input": {{}}, "runtime_params": {{}}}})
    assert first == second
    assert first["error"] == "unhandled-failure"
    assert first["ticket"]["message"] == "[redacted-message]"
    assert "secret-value" not in json.dumps(first)
'''


def _readme_source(seed: dict) -> str:
    application = seed["application"]
    return f'''# {application["name"]}

{application["description"]}

Generated by Thing v2 as a seven-stage compile-time specialization.
The installed runtime contains no source declaration and does not import the
compiler.

```text
outer input → inner input → core input → core processing
→ core output → inner output → outer output
```
'''


def _dependency_edges(seed: dict) -> dict[str, list[str]]:
    package = seed["application"]["package"]
    stage = lambda index: f"{package}/{STAGE_NAMES[index - 1]}"
    common_manifest = ".thing_v2/manifest.json"
    evidence = [".thing_v2/acceptance.json", "tests/test_thing_v2.py"]
    all_files = [
        "pyproject.toml",
        "README.md",
        f"{package}/__init__.py",
        f"{package}/__main__.py",
        f"{package}/runtime.py",
        f"{package}/compose.py",
        f"{package}/cli.py",
        *(stage(index) for index in range(1, 8)),
        *evidence,
    ]
    if seed["core"]["mode"] == "foreign_fixture":
        all_files.append(f"{package}/foreign_fixture.py")
    edges = {
        "application.identity": sorted(set(all_files + [common_manifest])),
        "application.description": ["README.md", "pyproject.toml", common_manifest],
        "formats.outer_input": [stage(1), common_manifest],
        "formats.inner_input": [stage(2), common_manifest],
        "formats.core_input": [stage(3), common_manifest],
        "core": [
            stage(4),
            f"{package}/runtime.py",
            common_manifest,
        ],
        "computation_seed.operation": [stage(4), common_manifest],
        "computation_seed.input_field": [stage(2), common_manifest],
        "computation_seed.output_field": [stage(6), common_manifest],
        "computation_seed.runtime_parameter": [stage(2), common_manifest],
        "computation_seed.coefficient": [stage(4), common_manifest],
        "compile_time_constants.bias": [stage(3), common_manifest],
        "compile_time_constants.fixture_failure_below": [stage(4), common_manifest],
        "runtime_parameter_schema": [stage(2), common_manifest],
        "formats.core_output": [stage(5), common_manifest],
        "formats.inner_output": [stage(6), common_manifest],
        "formats.outer_output": [stage(7), common_manifest],
        "validation": [stage(2), common_manifest],
        "evidence_requirements": [*evidence, common_manifest],
        "selected_adapters": [stage(1), stage(7), common_manifest],
        "acceptance": [*evidence, common_manifest],
        "foreign_dependency": [
            f"{package}/foreign_fixture.py",
            common_manifest,
        ]
        if seed["core"]["mode"] == "foreign_fixture"
        else [common_manifest],
    }
    return {key: sorted(set(value)) for key, value in sorted(edges.items())}


def _boilerplate_hashes() -> dict[str, str]:
    return {
        name: _sha_text(name + "\n" + inspect.getsource(_stage_source))
        for name in BOILERPLATE_FAMILIES
    }


def _support_template_hashes() -> dict[str, str]:
    renderers = {
        "audited-runtime": _runtime_source,
        "runtime-composition": _compose_source,
        "process-boundary": _cli_source,
        "generated-verification": _generated_tests_source,
        "foreign-fixture": _foreign_fixture_source,
        "generated-documentation": _readme_source,
    }
    return {
        name: _sha_text(inspect.getsource(renderer))
        for name, renderer in sorted(renderers.items())
    }


def _stage_specs(seed: dict) -> tuple[tuple[str, dict], ...]:
    computation = seed["computation_seed"]
    parameter_name = computation["runtime_parameter"]
    parameter_rule = seed["runtime_parameter_schema"][parameter_name]
    mode = seed["core"]["mode"]
    primitive_1 = (
        "_outer_object"
        if seed["formats"]["outer_input"]["kind"] == "object"
        else "_outer_json"
    )
    primitive_4 = "_native_core" if mode == "native" else "_foreign_core"
    primitive_7 = (
        "_outer_output_object"
        if seed["formats"]["outer_output"]["kind"] == "object"
        else "_outer_output_json"
    )
    return (
        (primitive_1, {"format": seed["formats"]["outer_input"]["kind"]}),
        (
            "_inner_to_core",
            {
                "input_field": computation["input_field"],
                "runtime_parameter": parameter_name,
                "minimum": parameter_rule.get("minimum"),
                "maximum": parameter_rule.get("maximum"),
            },
        ),
        (
            "_core_prepare",
            {"bias": seed["compile_time_constants"]["bias"]},
        ),
        (
            primitive_4,
            {
                "coefficient": computation["coefficient"],
                "failure_below": seed["compile_time_constants"].get(
                    "fixture_failure_below"
                ),
            },
        ),
        ("_core_collect", {"format": seed["formats"]["core_output"]["kind"]}),
        (
            "_core_to_inner",
            {"output_field": computation["output_field"]},
        ),
        (primitive_7, {"format": seed["formats"]["outer_output"]["kind"]}),
    )


def render_files(seed: dict) -> dict[str, str]:
    """Render one complete specialized target as deterministic text."""
    application = seed["application"]
    package = application["package"]
    mode = seed["core"]["mode"]
    files = {
        "pyproject.toml": _pyproject(seed),
        "README.md": _readme_source(seed),
        f"{package}/__init__.py": "from .compose import program\n\n__all__ = [\"program\"]\n",
        f"{package}/__main__.py": (
            "from .cli import main\n\n\n"
            "if __name__ == \"__main__\":\n"
            "    raise SystemExit(main())\n"
        ),
        f"{package}/runtime.py": _runtime_source(mode == "foreign_fixture"),
        f"{package}/compose.py": _compose_source(package),
        f"{package}/cli.py": _cli_source(package),
        "tests/test_thing_v2.py": _generated_tests_source(package),
        ".thing_v2/acceptance.json": (
            json.dumps(
                _acceptance_payload(seed),
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n"
        ),
    }
    for name, (primitive, spec) in zip(STAGE_NAMES, _stage_specs(seed)):
        files[f"{package}/{name}"] = _stage_source(primitive, spec)
    if mode == "foreign_fixture":
        files[f"{package}/foreign_fixture.py"] = _foreign_fixture_source()
    return dict(sorted(files.items()))


def _file_hashes(files: dict[str, str]) -> dict[str, str]:
    return {path: _sha_text(content) for path, content in sorted(files.items())}


def _tree_hash(file_hashes: dict[str, str]) -> str:
    aggregate = hashlib.sha256()
    for path, digest in sorted(file_hashes.items()):
        aggregate.update(path.encode("utf-8"))
        aggregate.update(b"\0")
        aggregate.update(digest.encode("ascii"))
        aggregate.update(b"\n")
    return aggregate.hexdigest()


def _churn_matrix(seed: dict, files: dict[str, str]) -> dict[str, list[str]]:
    probes = {}
    description = copy.deepcopy(seed)
    description["application"]["description"] += " [churn-probe]"
    probes["description_only"] = description

    outer = copy.deepcopy(seed)
    current = outer["formats"]["outer_output"]["kind"]
    outer["formats"]["outer_output"]["kind"] = (
        "json_text" if current == "object" else "object"
    )
    outer["selected_adapters"]["outer_output"] = outer["formats"]["outer_output"][
        "kind"
    ]
    probes["outer_output_format"] = outer

    computation = copy.deepcopy(seed)
    computation["computation_seed"]["coefficient"] += 1
    probes["computation_seed"] = computation

    base_hashes = _file_hashes(files)
    matrix = {}
    for name, probe in probes.items():
        changed = []
        for path, digest in _file_hashes(render_files(probe)).items():
            if base_hashes.get(path) != digest:
                changed.append(path)
        changed.extend(path for path in base_hashes if path not in render_files(probe))
        matrix[name] = sorted(set(changed))
    return matrix


def _manifest(seed: dict, seed_sha256: str, files: dict[str, str]) -> dict:
    hashes = _file_hashes(files)
    mode = seed["core"]["mode"]
    dependency = seed.get("foreign_dependency") if mode == "foreign_fixture" else None
    actual_fixture = foreign_fixture_sha256() if mode == "foreign_fixture" else None
    return {
        "thing_v2": 2,
        "compiler_version": COMPILER_VERSION,
        "standard_version": STANDARD_VERSION,
        "seed_sha256": seed_sha256,
        "boilerplate_family_hashes": _boilerplate_hashes(),
        "support_template_hashes": _support_template_hashes(),
        "seed_section_hashes": _section_hashes(seed),
        "generated_file_hashes": hashes,
        "dependency_edges": _dependency_edges(seed),
        "complete_tree_sha256": _tree_hash(hashes),
        "seven_generated_files": [
            f"{seed['application']['package']}/{name}" for name in STAGE_NAMES
        ],
        "churn_matrix": _churn_matrix(seed, files),
        "foreign_dependency": {
            **dependency,
            "actual_fixture_sha256": actual_fixture,
            "verified": dependency.get("sha256") == actual_fixture,
        }
        if dependency
        else None,
        "verification": {
            "source_laws": False,
            "generated_tests": False,
            "acceptance": False,
            "runtime_seed_absence": False,
            "seedless_copy": False,
            "fixed_point": False,
        },
    }


def _manifest_text(manifest: dict) -> str:
    return json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _changed_sections(previous: dict | None, current: dict) -> list[str]:
    if not previous:
        return sorted(current)
    return sorted(
        key for key, value in current.items()
        if (previous.get("seed_section_hashes") or {}).get(key) != value
    )


def _affected_files(
    changed_sections: list[str],
    edges: dict[str, list[str]],
    all_paths: set[str],
) -> set[str]:
    if not changed_sections:
        return {".thing_v2/manifest.json"}
    affected = {".thing_v2/manifest.json"}
    for section in changed_sections:
        affected.update(edges.get(section) or ())
    return affected & (all_paths | {".thing_v2/manifest.json"})


def _load_previous_manifest(output: Path) -> dict | None:
    path = output / ".thing_v2" / "manifest.json"
    if not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def _materialize(
    root: Path,
    output: Path,
    files: dict[str, str],
    manifest: dict,
) -> tuple[list[str], list[str], list[str]]:
    previous = _load_previous_manifest(output)
    sections = _changed_sections(previous, manifest["seed_section_hashes"])
    affected = _affected_files(
        sections,
        manifest["dependency_edges"],
        set(files),
    )
    reused = []
    written = []
    previous_hashes = (previous or {}).get("generated_file_hashes") or {}
    for rel, content in files.items():
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        prior = output / rel
        expected = manifest["generated_file_hashes"][rel]
        if (
            prior.is_file()
            and previous_hashes.get(rel) == expected
            and _sha_bytes(prior.read_bytes()) == expected
        ):
            shutil.copy2(prior, target)
            reused.append(rel)
        else:
            target.write_text(content, encoding="utf-8")
            written.append(rel)
    manifest_path = root / ".thing_v2" / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(_manifest_text(manifest), encoding="utf-8")
    written.append(".thing_v2/manifest.json")
    return sorted(written), sorted(reused), sorted(affected)


def _source_law_report(root: Path, package: str) -> dict:
    forbidden_nodes = (
        ast.ClassDef,
        ast.If,
        ast.For,
        ast.AsyncFor,
        ast.While,
        ast.Match,
        ast.IfExp,
        ast.Try,
        ast.ListComp,
        ast.SetComp,
        ast.DictComp,
        ast.GeneratorExp,
    )
    paths = [
        *(root / package / name for name in STAGE_NAMES),
        root / package / "compose.py",
    ]
    violations = []
    signatures = []
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        violations.extend(
            f"{path.name}:{type(node).__name__}"
            for node in ast.walk(tree)
            if isinstance(node, forbidden_nodes)
        )
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
                signatures.append(
                    {
                        "file": path.name,
                        "name": node.name,
                        "parameters": len(node.args.args),
                    }
                )
    signature_ok = all(item["parameters"] == 1 for item in signatures)
    return {
        "ok": not violations and signature_ok,
        "control_flow_violations": sorted(violations),
        "public_signatures": signatures,
    }


def _runtime_seed_absence(root: Path, package: str) -> dict:
    forbidden = (
        "unified.generator",
        "importlib",
        "eval(",
        "exec(",
        "compile(",
        "seed_path",
        "declaration_path",
    )
    hits = []
    for path in sorted((root / package).glob("*.py")):
        text = path.read_text(encoding="utf-8")
        for term in forbidden:
            if term in text:
                hits.append(f"{path.name}:{term}")
    return {"ok": not hits, "hits": hits}


def _python_executable() -> str:
    return sys.executable or "python3"


def _stable_selftest_detail(stdout: str, stderr: str, limit: int) -> str:
    try:
        report = json.loads(stdout)
    except json.JSONDecodeError:
        return (stdout + stderr)[-limit:]
    report.pop("duration_ns", None)
    return (json.dumps(report, separators=(",", ":"), sort_keys=True) + stderr)[
        -limit:
    ]


def _run_generated_tests(root: Path) -> dict:
    try:
        result = subprocess.run(
            [
                _python_executable(),
                str(Path(__file__).resolve().parents[2] / "unified" / "selftest.py"),
                "tests",
            ],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "exit": -1, "detail": f"{type(exc).__name__}:{exc}"}
    return {
        "ok": result.returncode == 0,
        "exit": result.returncode,
        "detail": _stable_selftest_detail(
            result.stdout or "", result.stderr or "", 1200
        ),
    }


def _run_acceptance(root: Path, package: str) -> dict:
    acceptance = json.loads(
        (root / ".thing_v2" / "acceptance.json").read_text(encoding="utf-8")
    )
    outputs = []
    env = {**os.environ, "PYTHONPATH": str(root)}
    for index, case in enumerate(acceptance["cases"]):
        result = subprocess.run(
            [
                _python_executable(),
                "-m",
                package,
                "--input",
                json.dumps(case["outer_input"], ensure_ascii=False, separators=(",", ":")),
                "--params",
                json.dumps(case["runtime_params"], ensure_ascii=False, separators=(",", ":")),
            ],
            cwd=str(root),
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        try:
            output = json.loads((result.stdout or "").strip())
        except ValueError:
            output = {"invalid_stdout": (result.stdout or "").strip()}
        outputs.append(
            {
                "index": index,
                "exit": result.returncode,
                "output": output,
            }
        )
        expected = case["expect"]
        expected_exit = 0 if expected.get("state") == "valid" else 1
        if result.returncode != expected_exit or output != expected:
            return {"ok": False, "outputs": outputs}
    return {"ok": True, "outputs": outputs}


def _seedless_copy_check(root: Path, package: str) -> dict:
    copy_parent = Path(tempfile.mkdtemp(prefix="uc-thing-v2-seedless-"))
    copied = copy_parent / "app"
    try:
        shutil.copytree(
            root,
            copied,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".uc-cache"),
        )
        result = _run_acceptance(copied, package)
        result["path"] = str(copied)
        return result
    finally:
        shutil.rmtree(copy_parent, ignore_errors=True)


def _fixed_point_check(seed: dict, manifest: dict) -> dict:
    files_a = render_files(seed)
    files_b = render_files(copy.deepcopy(seed))
    hashes_a = _file_hashes(files_a)
    hashes_b = _file_hashes(files_b)
    manifest_a = _manifest(seed, manifest["seed_sha256"], files_a)
    manifest_b = _manifest(copy.deepcopy(seed), manifest["seed_sha256"], files_b)
    equal = (
        hashes_a == hashes_b
        and _canonical_bytes(manifest_a) == _canonical_bytes(manifest_b)
    )
    return {
        "ok": equal,
        "tree_sha256_a": _tree_hash(hashes_a),
        "tree_sha256_b": _tree_hash(hashes_b),
        "manifest_sha256_a": _sha_bytes(_canonical_bytes(manifest_a)),
        "manifest_sha256_b": _sha_bytes(_canonical_bytes(manifest_b)),
    }


def _verify_tree(root: Path, seed: dict, manifest: dict) -> dict:
    package = seed["application"]["package"]
    source_laws = _source_law_report(root, package)
    absence = _runtime_seed_absence(root, package)
    tests = _run_generated_tests(root)
    acceptance = _run_acceptance(root, package)
    seedless = _seedless_copy_check(root, package)
    fixed_point = _fixed_point_check(seed, manifest)
    checks = {
        "source_laws": source_laws,
        "runtime_seed_absence": absence,
        "generated_tests": tests,
        "acceptance": acceptance,
        "seedless_copy": seedless,
        "fixed_point": fixed_point,
    }
    return {
        "ok": all(result.get("ok") for result in checks.values()),
        **checks,
    }


def _update_verified_manifest(root: Path, manifest: dict, verification: dict) -> dict:
    updated = copy.deepcopy(manifest)
    updated["verification"] = {
        name: bool((verification.get(name) or {}).get("ok"))
        for name in (
            "source_laws",
            "generated_tests",
            "acceptance",
            "runtime_seed_absence",
            "seedless_copy",
            "fixed_point",
        )
    }
    path = root / ".thing_v2" / "manifest.json"
    path.write_text(_manifest_text(updated), encoding="utf-8")
    return updated


def _atomic_publish(staging: Path, output: Path) -> None:
    backup = output.parent / f".{output.name}.thing-v2-prev"
    if backup.exists():
        shutil.rmtree(backup)
    if output.exists():
        output.rename(backup)
    try:
        staging.rename(output)
    except OSError:
        if output.exists():
            shutil.rmtree(output, ignore_errors=True)
        if backup.exists():
            backup.rename(output)
        raise
    if backup.exists():
        shutil.rmtree(backup, ignore_errors=True)


def run_compile(thing):
    """Compile and atomically publish one Thing v2 seed. Thing→Thing."""
    if not is_thing(thing):
        return {
            "value": thing,
            "depths": (),
            "axes": (),
            "evidence": ("thing_v2:rejected-non-thing",),
            "state": "invalid",
        }
    if thing.get("state") in {"invalid", "absent", "false"}:
        return {
            **thing,
            "evidence": (*thing["evidence"], "thing_v2:skipped"),
        }
    value = thing.get("value")
    if not isinstance(value, dict):
        return _failure(thing, {}, "compile-value-not-object", "thing_v2:invalid")
    if value.get("error"):
        return _failure(
            thing,
            value,
            str(value["error"]),
            "thing_v2:argv-invalid",
        )
    seed_raw = value.get("seed_path")
    output_raw = value.get("output")
    if not isinstance(seed_raw, str) or not isinstance(output_raw, str):
        return _failure(
            thing,
            value,
            "compile-paths-missing",
            "thing_v2:paths-invalid",
        )
    if not value.get("verify"):
        return _failure(
            thing,
            value,
            "compile-requires-verify",
            "thing_v2:verify-required",
        )
    seed_path = Path(seed_raw).expanduser().resolve()
    output = Path(output_raw).expanduser().resolve()
    if output == Path(output.anchor) or seed_path == output or output in seed_path.parents:
        return _failure(
            thing,
            {**value, "seed_path": str(seed_path), "output": str(output)},
            "unsafe-output-path",
            "thing_v2:paths-invalid",
        )
    if output.exists() and not output.is_dir():
        return _failure(
            thing,
            {**value, "seed_path": str(seed_path), "output": str(output)},
            "output-not-directory",
            "thing_v2:paths-invalid",
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=f".{output.name}.thing-v2-", dir=str(output.parent))
    )
    normalized = {
        **value,
        "seed_path": str(seed_path),
        "output": str(output),
        "diagnostics": str(staging),
    }
    seed, read_error = _read_seed(seed_path)
    if read_error:
        return _failure(
            thing,
            normalized,
            read_error,
            "thing_v2:seed-invalid",
        )
    errors = validate_seed(seed)
    if errors:
        return _failure(
            thing,
            {**normalized, "validation_errors": errors},
            "seed-validation-failed",
            "thing_v2:seed-validation-failed",
        )
    if (
        seed["core"]["mode"] == "foreign_fixture"
        and seed["foreign_dependency"]["sha256"] != foreign_fixture_sha256()
    ):
        return _failure(
            thing,
            normalized,
            "foreign-provenance-hash-mismatch",
            "thing_v2:foreign-provenance-invalid",
        )
    files = render_files(seed)
    seed_sha256 = _sha_bytes(seed_path.read_bytes())
    manifest = _manifest(seed, seed_sha256, files)
    written, reused, declared_affected = _materialize(
        staging, output, files, manifest
    )
    verification = _verify_tree(staging, seed, manifest)
    if not verification["ok"]:
        return _failure(
            thing,
            {
                **normalized,
                "manifest": manifest,
                "verification": verification,
                "written_files": written,
                "reused_files": reused,
                "declared_affected_files": declared_affected,
            },
            "compile-verification-failed",
            "thing_v2:verification-failed",
        )
    manifest = _update_verified_manifest(staging, manifest, verification)
    try:
        _atomic_publish(staging, output)
    except OSError as exc:
        return _failure(
            thing,
            {
                **normalized,
                "error_type": type(exc).__name__,
                "message": "[redacted-message]",
            },
            "compile-publish-failed",
            "thing_v2:publish-failed",
        )
    result = {
        **normalized,
        "project_path": str(output),
        "manifest_path": str(output / ".thing_v2" / "manifest.json"),
        "manifest": manifest,
        "verification": verification,
        "acceptance_outputs": verification["acceptance"]["outputs"],
        "seven_generated_files": manifest["seven_generated_files"],
        "tree_sha256": manifest["complete_tree_sha256"],
        "affected_files": written,
        "declared_affected_files": declared_affected,
        "reused_files": reused,
        "install": "ok",
    }
    return outward(
        {
            **thing,
            "value": result,
            "evidence": (
                *thing["evidence"],
                "thing_v2:seed-valid",
                "thing_v2:seven-specialized",
                "thing_v2:verification-pass",
                "thing_v2:atomic-install",
            ),
            "state": "valid",
        }
    )
