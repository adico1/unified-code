"""Request-to-manifestation pre-compilation contract."""

from __future__ import annotations

import json
from pathlib import Path

from unified.generator.application_language import seed_compiler
from unified.generator.application_language.precompile import (
    build_pipeline,
    verify_manifestation,
)


ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "seed" / "application_language" / "applications" / "normal.seed.json"


def resolved():
    declaration, authorities = seed_compiler.load_seed(SEED)
    return declaration, authorities


def test_request_unfolds_through_every_precompile_projection():
    declaration, authorities = resolved()
    pipeline = build_pipeline(declaration, authorities)

    assert tuple(pipeline) == (
        "request",
        "architecture",
        "systems",
        "interfaces",
        "full_specification",
        "specialized_specification",
        "manifestation_plan",
        "evidence",
    )
    assert pipeline["request"]["identity"] == declaration["identity"]
    assert pipeline["architecture"]["identity"] == declaration["identity"]["canonical"]
    assert pipeline["systems"]
    assert pipeline["interfaces"]
    assert pipeline["full_specification"]["declaration"] == declaration
    specialized = pipeline["specialized_specification"]["declaration"]
    assert specialized != declaration
    assert specialized["_assembly"] == {
        "profile": "expression",
        "stamps": declaration["_assembly"]["stamps"]
    }
    assert pipeline["request"]["meaning"] == declaration["_assembly"]["request"]
    assert pipeline["manifestation_plan"]["target"] == "python-tk"
    assert pipeline["evidence"]["events"] == [
        "request.received",
        "architecture.derived",
        "systems.enumerated",
        "interfaces.enumerated",
        "full-specification.formed",
        "specialized-specification.formed",
        "manifestation.planned",
    ]


def test_specialization_accounts_for_every_selected_capability_once():
    declaration, authorities = resolved()
    specialized = build_pipeline(declaration, authorities)[
        "specialized_specification"
    ]

    requirements = specialized["requirements"]
    assert len(requirements) == len(set(requirements))
    assert specialized["exactness"] == {
        "excess_capabilities": [],
        "missing_capabilities": [],
        "verdict": "pass",
    }
    assert "operation.add" in requirements
    assert "control.operator.expression.add" in requirements
    assert "interface.entrypoint.process.case" in requirements


def test_assembled_files_preserve_the_complete_precompile_chain():
    manifest, files = seed_compiler.assemble(SEED)

    expected = {
        "request.json",
        "system-architecture.json",
        "systems.json",
        "interfaces.json",
        "full-specification.json",
        "specialized-specification.json",
        "manifestation-plan.json",
    }
    assert expected < set(files)
    assert manifest["precompile"]["verdict"] == "pass"
    assert manifest["precompile"]["manifestation_exactness"]["verdict"] == "pass"
    specialized = json.loads(files["specialized-specification.json"])
    assert specialized["declaration"]["identity"]["canonical"] == (
        "uc://applications/normal@1"
    )
    source = files["main.py"].decode()
    assert "seed_compiler" not in source
    assert "specialized-specification.json" not in source


def test_precompile_pipeline_is_dictionary_order_independent():
    declaration, authorities = resolved()
    reordered = {key: declaration[key] for key in reversed(tuple(declaration))}

    first = build_pipeline(declaration, authorities)
    second = build_pipeline(reordered, authorities)

    assert seed_compiler.canonical(first) == seed_compiler.canonical(second)


def test_missing_public_interface_is_rejected_before_manifestation():
    declaration, authorities = resolved()
    declaration["program"].pop("case_entrypoint")

    try:
        build_pipeline(declaration, authorities)
    except ValueError as error:
        assert str(error) == "precompile-interface-missing"
    else:
        raise AssertionError("missing interface reached manifestation")


def test_removed_selected_operation_is_detected_as_missing_code():
    declaration, authorities = resolved()
    pipeline = build_pipeline(declaration, authorities)
    source, tree = seed_compiler.render_program(
        pipeline["specialized_specification"]["declaration"]
    )
    tests = seed_compiler.render_tests(declaration)
    trace = seed_compiler.trace_program(
        declaration, source, tree, authorities
    )
    mutated = source.replace(
        b"ast.Add: operator.add, ",
        b"",
        1,
    )

    result = verify_manifestation(pipeline, mutated, tests, trace)

    assert result["verdict"] == "invalid"
    assert result["missing_capabilities"] == ["mapping.BINARY"]


def test_unselected_operation_injected_into_source_is_detected_as_excess():
    declaration, authorities = resolved()
    pipeline = build_pipeline(declaration, authorities)
    source, tree = seed_compiler.render_program(
        pipeline["specialized_specification"]["declaration"]
    )
    tests = seed_compiler.render_tests(declaration)
    trace = seed_compiler.trace_program(
        declaration, source, tree, authorities
    )
    mutated = source.replace(
        b"BINARY = {",
        b"BINARY = {ast.Pow: operator.pow, ",
        1,
    )

    result = verify_manifestation(pipeline, mutated, tests, trace)

    assert result["verdict"] == "invalid"
    assert result["excess_capabilities"] == ["mapping.BINARY"]
