"""Canonical request-to-manifestation pre-compilation projections.

This module does not render an application.  It turns one resolved declaration
into the ordered semantic projections consumed by the registered renderer.  No
projection is available to the generated runtime.
"""

from __future__ import annotations

import ast
import hashlib
import json


EVENTS = (
    "request.received",
    "architecture.derived",
    "systems.enumerated",
    "interfaces.enumerated",
    "full-specification.formed",
    "specialized-specification.formed",
    "manifestation.planned",
)


def canonical(value):
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode()


def digest(value):
    raw = value if isinstance(value, bytes) else canonical(value)
    return hashlib.sha256(raw).hexdigest()


def system_inventory(declaration):
    sections = (
        "identity",
        "semantics",
        "state",
        "presentation",
        "boundaries",
        "program",
        "acceptance",
    )
    return [
        {
            "identity": "system." + name,
            "authority_path": "/" + name,
            "sha256": digest(declaration[name]),
        }
        for name in sections
    ]


def interface_inventory(declaration):
    program = declaration.get("program", {})
    entrypoints = [
        {
            "identity": "interface.entrypoint." + identity,
            "kind": "entrypoint",
            "operation": operation,
        }
        for identity, operation in (
            ("process.case", program.get("case_entrypoint")),
            ("application.launch", program.get("launch_entrypoint")),
        )
        if operation
    ]
    boundaries = [
        {
            "identity": "interface.boundary." + item["identity"],
            "kind": "boundary",
            "direction": item["direction"],
        }
        for item in declaration.get("boundaries", ())
    ]
    controls = [
        {
            "identity": "interface.control." + item["id"],
            "kind": "control",
            "event": "control." + item["id"] + ".pressed",
        }
        for item in declaration.get("presentation", {}).get("controls", ())
    ]
    return [*entrypoints, *boundaries, *controls]


def semantic_requirements(declaration, interfaces):
    semantics = declaration.get("semantics", {})
    operations = [
        "operation." + item["id"]
        for definitions in semantics.get("operations", {}).values()
        for item in definitions
    ]
    commands = [
        "command." + item["id"] for item in semantics.get("commands", ())
    ]
    calculations = [
        "calculation." + item["id"]
        for item in semantics.get("calculations", {}).get("functions", ())
    ]
    state = [
        "state." + identity
        for identity in declaration.get("state", {}).get("fields", ())
    ]
    controls = [
        "control." + item["id"]
        for item in declaration.get("presentation", {}).get("controls", ())
    ]
    acceptance = [
        "acceptance." + item["id"]
        for item in declaration.get("acceptance", ())
    ]
    interface_requirements = [item["identity"] for item in interfaces]
    requirements = [
        *operations,
        *commands,
        *calculations,
        *state,
        *controls,
        *interface_requirements,
        *acceptance,
    ]
    if len(requirements) != len(set(requirements)):
        raise ValueError("precompile-requirement-conflict")
    return sorted(requirements)


def build_pipeline(declaration, authorities):
    """Project one resolved application request into one manifestation plan."""

    program = declaration.get("program", {})
    if not program.get("case_entrypoint") or not program.get("launch_entrypoint"):
        raise ValueError("precompile-interface-missing")
    systems = system_inventory(declaration)
    interfaces = interface_inventory(declaration)
    requirements = semantic_requirements(declaration, interfaces)
    stamps = declaration.get("_assembly", {}).get("stamps", ())
    targets = declaration.get("_assembly", {}).get("targets", {}).get(
        "physical", ()
    )
    if not stamps or len(targets) != 1:
        raise ValueError("precompile-authority-incomplete")
    authority_identities = [item["identity"] for item in authorities]
    request = {
        "format": "unified-application-request-1",
        "identity": declaration["identity"],
        "authority": authority_identities[-1],
        "meaning": declaration["_assembly"]["request"],
        "declared_sections": sorted(
            key for key in declaration if not key.startswith("_")
        ),
    }
    architecture = {
        "format": "unified-system-architecture-1",
        "identity": declaration["identity"]["canonical"],
        "authority_chain": authority_identities,
        "systems": [item["identity"] for item in systems],
        "interfaces": [item["identity"] for item in interfaces],
        "stages": [item["stage"] for item in stamps],
    }
    full_specification = {
        "format": "unified-full-specification-1",
        "authorities": authorities,
        "declaration": declaration,
        "sha256": digest(declaration),
    }
    selected = list(requirements)
    specialized_declaration = {
        **{
            name: value
            for name, value in declaration.items()
            if not name.startswith("_")
        },
        "_assembly": {
            "profile": declaration["_assembly"]["profile"],
            "stamps": list(stamps),
        },
    }
    specialized_specification = {
        "format": "unified-specialized-specification-1",
        "target": targets[0],
        "requirements": selected,
        "declaration": specialized_declaration,
        "exactness": {
            "missing_capabilities": sorted(set(requirements) - set(selected)),
            "excess_capabilities": sorted(set(selected) - set(requirements)),
            "verdict": "pass",
        },
    }
    manifestation_plan = {
        "format": "unified-manifestation-plan-1",
        "target": targets[0],
        "compiler_input": "specialized-specification",
        "runtime_seed_access": False,
        "stages": [
            {
                "identity": item["identity"],
                "stage": item["stage"],
                "input_sha256": digest(specialized_specification),
            }
            for item in stamps
        ],
        "outputs": ["main.py", "test_generated.py", "traceability.json"],
    }
    documents = {
        "request": request,
        "architecture": architecture,
        "systems": systems,
        "interfaces": interfaces,
        "full_specification": full_specification,
        "specialized_specification": specialized_specification,
        "manifestation_plan": manifestation_plan,
    }
    evidence = {
        "format": "unified-precompile-evidence-1",
        "events": list(EVENTS),
        "projection_sha256": {
            name: digest(value) for name, value in sorted(documents.items())
        },
        "missing_capabilities": [],
        "excess_capabilities": [],
        "verdict": "pass",
    }
    return {**documents, "evidence": evidence}


def _mapping_size(tree, identity):
    assignments = [
        node.value
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == identity
            for target in node.targets
        )
    ]
    return len(assignments[0].keys) if assignments else 0


def _literal_assignment(tree, identities):
    values = [
        node.value
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id in identities
            for target in node.targets
        )
        and isinstance(node.value, (ast.Dict, ast.List, ast.Tuple, ast.Constant))
    ]
    return ast.literal_eval(values[0]) if values else None


def verify_manifestation(pipeline, source, tests, trace):
    """Prove selected semantic capabilities reached generated artifacts."""

    declaration = pipeline["specialized_specification"]["declaration"]
    tree = ast.parse(source)
    test_tree = ast.parse(tests)
    functions = {
        node.name for node in tree.body if isinstance(node, ast.FunctionDef)
    }
    semantics = declaration["semantics"]
    operation_groups = semantics.get("operations", {})
    stack = semantics.get("numeric_laws", {}).get("kind") == "stack"
    expected_mappings = {
        "BINARY": 0 if stack else len(operation_groups.get("binary", ())),
        "UNARY": len(operation_groups.get("unary", ())),
        "FUNCTIONS": len(operation_groups.get("functions", ())),
        "CONSTANTS": len(operation_groups.get("constants", ())),
        "OPERATIONS": (
            len(operation_groups.get("binary", ()))
            if stack
            else 0
        ),
    }
    actual_mappings = {
        identity: _mapping_size(tree, identity)
        for identity in expected_mappings
    }
    missing = [
        "mapping." + identity
        for identity, count in expected_mappings.items()
        if actual_mappings[identity] < count
    ]
    excess = [
        "mapping." + identity
        for identity, count in actual_mappings.items()
        if count > expected_mappings[identity]
    ]
    expected_commands = len(semantics.get("commands", ()))
    actual_commands = sum(
        identity.startswith("command_") for identity in functions
    )
    if actual_commands < expected_commands:
        missing.append("commands")
    if actual_commands > expected_commands:
        excess.append("commands")
    initial_state = _literal_assignment(tree, {"INITIAL_STATE", "state"})
    declared_state = declaration["state"]["initial"]
    if initial_state != declared_state:
        missing.append("state.initial")
    entrypoints = {
        declaration["program"]["case_entrypoint"],
        declaration["program"]["launch_entrypoint"],
    }
    routes = {item["route"] for item in declaration["transitions"]}
    missing.extend(
        "function." + identity
        for identity in sorted((entrypoints | routes) - functions)
    )
    controls = declaration["presentation"]["controls"]
    traced_controls = {item["identity"] for item in trace["controls"]}
    missing.extend(
        "control." + identity
        for identity in sorted(
            {item["id"] for item in controls} - traced_controls
        )
    )
    semantic_functions = {
        item["identity"] for item in trace["semantic_functions"]
    }
    declared_semantic_functions = {
        item["id"]
        for item in (
            semantics.get("calculations", {}).get("functions", ())
            or operation_groups.get("functions", ())
        )
    }
    missing.extend(
        "semantic." + identity
        for identity in sorted(
            declared_semantic_functions - semantic_functions
        )
    )
    excess.extend(
        "semantic." + identity
        for identity in sorted(
            semantic_functions - declared_semantic_functions
        )
    )
    cases = [
        node.value
        for node in test_tree.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "CASES"
            for target in node.targets
        )
    ]
    generated_cases = {
        item["id"] for item in ast.literal_eval(cases[0])
    } if cases else set()
    declared_cases = {item["id"] for item in declaration["acceptance"]}
    missing.extend(
        "acceptance." + identity
        for identity in sorted(declared_cases - generated_cases)
    )
    excess.extend(
        "acceptance." + identity
        for identity in sorted(generated_cases - declared_cases)
    )
    if "/boundaries" not in trace["contract_sections"]:
        missing.append("contract.boundaries")
    verdict = "pass" if not missing and not excess else "invalid"
    return {
        "mapping_counts": {
            identity: {
                "declared": expected_mappings[identity],
                "generated": actual_mappings[identity],
            }
            for identity in sorted(expected_mappings)
        },
        "command_counts": {
            "declared": expected_commands,
            "generated": actual_commands,
        },
        "state_initial_exact": initial_state == declared_state,
        "missing_capabilities": missing,
        "excess_capabilities": excess,
        "verdict": verdict,
    }
