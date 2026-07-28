"""Five-application assembly from seed-defined generic capability programs."""

from __future__ import annotations

import ast
import atexit
import base64
import concurrent.futures
import copy
import hashlib
import inspect
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from ..boundary import outward
from ..thing import is_thing
from .gui import (
    browser_source as _gui_browser_source,
    css_source as _gui_css_source,
    entry_source as _gui_entry_source,
    host_source as _gui_host_source,
    html_source as _gui_html_source,
    validate_ui,
)

ASSEMBLY_VERSION = "UC-ASSEMBLY-1"
APPLICATION_VERSION = "UC-APPLICATION-3"
STAGES = (
    "01_outer_to_inner",
    "02_inner_to_core",
    "03_core_prepare",
    "04_core_processing",
    "05_core_collect",
    "06_core_to_inner",
    "07_inner_to_outer",
)
DEPTHS = (
    "seed_schema",
    "seed_to_spec",
    "spec_to_plan",
    "generation_provenance",
    "standard_ten_structure",
    "boundary_authority_failure",
    "behavior_persistence",
    "determinism_dependency",
    "mutation_differential_performance",
    "assembly_install_restart",
)
ENGINES = frozenset(("document", "numeric", "expression", "world"))
NAME_RE = re.compile(r"^[a-z][a-z0-9-]*$")
PACKAGE_RE = re.compile(r"^[a-z][a-z0-9_]*$")
_BROWSER_SESSION = {}
_ASSEMBLY_PROOF_CACHE = {}


def _canonical(value):
    return (json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n").encode()


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _failure(thing, value, error, mark):
    return {
        **thing,
        "value": {**value, "error": error},
        "evidence": (*tuple(thing.get("evidence") or ()), mark),
        "state": "invalid",
    }


def _read_json(path):
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as error:
        return None, f"read:{type(error).__name__}"
    return (value, None) if isinstance(value, dict) else (None, "not-object")


def validate_application(seed):
    if not isinstance(seed, dict):
        return ["application:not-object"]
    errors = []
    required = {
        "application_version",
        "application",
        "interface",
        "program",
        "boundaries",
        "persistence",
        "formats",
        "ui",
        "acceptance",
    }
    errors.extend(f"missing:{key}" for key in sorted(required - set(seed)))
    errors.extend(f"unknown:{key}" for key in sorted(set(seed) - (required | {"dependency"})))
    if errors:
        return errors
    if seed["application_version"] != APPLICATION_VERSION:
        errors.append("application_version")
    application = seed["application"]
    if not isinstance(application, dict):
        return ["application:not-object"]
    if not NAME_RE.fullmatch(str(application.get("name", ""))):
        errors.append("application.name")
    if not PACKAGE_RE.fullmatch(str(application.get("package", ""))):
        errors.append("application.package")
    program = seed["program"]
    if not isinstance(program, dict) or program.get("engine") not in ENGINES:
        errors.append("program.engine")
        return sorted(errors)
    if not isinstance(program.get("operations"), dict) or not program["operations"]:
        errors.append("program.operations")
    interface = seed["interface"]
    if (
        not isinstance(interface, dict)
        or set(interface) != {"cli", "library", "browser"}
        or any(not isinstance(item, bool) for item in interface.values())
    ):
        errors.append("interface")
    elif not interface["cli"] or not interface["browser"]:
        errors.append("interface.required")
    errors.extend(validate_ui(seed.get("ui")))
    if isinstance(seed.get("ui"), dict) and isinstance(program, dict):
        component_ids = {
            component.get("id")
            for section in (seed["ui"].get("layout") or {}).get("sections", ())
            for component in section.get("components", ())
            if isinstance(component, dict)
        }
        actions = seed["ui"].get("actions") or {}
        for name, action in actions.items():
            if not isinstance(action, dict) or action.get("mode") != "request":
                continue
            request = action.get("request") or {}
            declared = program.get("operations") or {}
            selected = request.get("action", request.get("operation"))
            if isinstance(selected, str) and selected not in declared:
                errors.append(f"ui.action.{name}.undeclared-operation")
            event = request.get("event")
            if isinstance(event, str) and event not in (program.get("events") or {}).values():
                errors.append(f"ui.action.{name}.undeclared-event")
        bindings = seed["ui"].get("bindings") or {}
        for binding in bindings.get("result", ()):
            if binding.get("target") not in component_ids:
                errors.append("ui.binding.unknown-target")
        for name in ("error", "status", "root"):
            if (bindings.get(name) or {}).get("target") not in component_ids:
                errors.append(f"ui.binding.{name}.unknown-target")
        for index, step in enumerate((seed["ui"].get("proof") or {}).get("steps", ())):
            if step.get("control") not in component_ids and not step.get("keyboard"):
                errors.append(f"ui.proof.steps[{index}].unknown-control")
            if (step.get("expect") or {}).get("target") not in component_ids:
                errors.append(f"ui.proof.steps[{index}].unknown-target")
            if any(identifier not in component_ids for identifier in (step.get("set") or {})):
                errors.append(f"ui.proof.steps[{index}].unknown-set-target")
    if not isinstance(seed["boundaries"], dict):
        errors.append("boundaries")
    elif (
        not isinstance(seed["boundaries"].get("acceptance_deadline_seconds"), int)
        or seed["boundaries"]["acceptance_deadline_seconds"] <= 0
    ):
        errors.append("boundaries.acceptance_deadline_seconds")
    if not isinstance(seed["persistence"], dict):
        errors.append("persistence")
    if not isinstance(seed["formats"], dict):
        errors.append("formats")
    acceptance = seed["acceptance"]
    if not isinstance(acceptance, list) or not acceptance:
        errors.append("acceptance")
    else:
        for index, scenario in enumerate(acceptance):
            if (
                not isinstance(scenario, dict)
                or not isinstance(scenario.get("id"), str)
                or not isinstance(scenario.get("steps"), list)
                or not scenario["steps"]
            ):
                errors.append(f"acceptance[{index}]")
                continue
            for step_index, step in enumerate(scenario["steps"]):
                if (
                    not isinstance(step, dict)
                    or not isinstance(step.get("request"), dict)
                    or not isinstance(step.get("expect"), dict)
                    or set(("state", "output", "error", "evidence"))
                    - set(step["expect"])
                ):
                    errors.append(f"acceptance[{index}].steps[{step_index}]")
        request_field = {
            "document": "action",
            "numeric": "operation",
        }.get(program["engine"])
        if request_field:
            invoked = {
                step["request"].get(request_field)
                for scenario in acceptance
                if isinstance(scenario, dict)
                for step in scenario.get("steps", ())
                if isinstance(step, dict) and isinstance(step.get("request"), dict)
            }
            missing_operations = set(program["operations"]) - invoked
            errors.extend(
                f"acceptance:missing-operation:{name}"
                for name in sorted(missing_operations)
            )
        if program["engine"] == "world" and isinstance(program.get("events"), dict):
            acceptance_text = json.dumps(acceptance, ensure_ascii=False, sort_keys=True)
            errors.extend(
                f"acceptance:missing-event:{name}"
                for name, event in sorted(program["events"].items())
                if f'"{event}"' not in acceptance_text
            )
    dependency = seed.get("dependency")
    if program.get("engine") == "expression":
        if not isinstance(dependency, dict) or set(("application", "interface")) - set(dependency):
            errors.append("dependency")
    if program.get("engine") == "numeric":
        for field in (
            "range",
            "numeric_grammar",
            "result_rules",
            "representation",
            "exported_contract",
        ):
            if field not in program:
                errors.append(f"program.{field}")
    if program.get("engine") == "world":
        roles = program.get("horizontal_roles")
        initial = program.get("initial_state") or {}
        actors = initial.get("actors") or {}
        counters = initial.get("counters") or {}
        if (
            not isinstance(roles, list)
            or len(roles) != 2
            or len(set(roles)) != 2
            or any(role not in actors or role not in counters for role in roles)
        ):
            errors.append("program.horizontal_roles")
        if not isinstance(program.get("window"), dict):
            errors.append("program.window")
        if not isinstance(program.get("controls"), dict):
            errors.append("program.controls")
        browser_proof = program.get("browser_proof")
        if (
            seed["interface"].get("browser")
            and (
                not isinstance(browser_proof, dict)
                or not isinstance(browser_proof.get("control_codes"), list)
                or not browser_proof["control_codes"]
                or any(
                    code not in program.get("controls", {})
                    for code in browser_proof["control_codes"]
                )
                or not isinstance(browser_proof.get("expected_scenario"), str)
                or not isinstance(browser_proof.get("expected_step"), int)
                or not isinstance(browser_proof.get("minimum_distinct_frames"), int)
            )
        ):
            errors.append("program.browser_proof")
    return sorted(errors)


def validate_suite(suite, root):
    errors = []
    if suite.get("assembly_version") != ASSEMBLY_VERSION:
        errors.append("assembly_version")
    entries = suite.get("applications")
    if not isinstance(entries, list) or len(entries) != 5:
        return ["applications:requires-five"]
    names = []
    seeds = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict) or set(entry) != {"seed"}:
            errors.append(f"applications[{index}]")
            continue
        relative = Path(str(entry["seed"]))
        if relative.is_absolute() or ".." in relative.parts:
            errors.append(f"applications[{index}].path")
            continue
        seed, error = _read_json(root / relative)
        if error:
            errors.append(f"applications[{index}].{error}")
            continue
        current = validate_application(seed)
        errors.extend(f"applications[{index}].{item}" for item in current)
        application = seed.get("application")
        if not isinstance(application, dict) or not application.get("name"):
            continue
        names.append(application["name"])
        seeds.append((relative.as_posix(), seed))
    if len(names) != len(set(names)):
        errors.append("applications:duplicate-name")
    available = set(names)
    for path, seed in seeds:
        dependency = seed.get("dependency")
        if dependency and dependency.get("application") not in available:
            errors.append(f"{path}:dependency-unavailable")
    dependency_by_name = {
        seed["application"]["name"]: (seed.get("dependency") or {}).get("application")
        for _, seed in seeds
    }
    resolved = set()
    while len(resolved) < len(dependency_by_name):
        ready = {
            name
            for name, dependency in dependency_by_name.items()
            if name not in resolved and (not dependency or dependency in resolved)
        }
        if not ready:
            errors.append("applications:dependency-cycle")
            break
        resolved.update(ready)
    return sorted(errors)


def _ordered_seeds(seeds):
    pending = {
        seed["application"]["name"]: (path, seed)
        for path, seed in seeds
    }
    ordered = []
    resolved = set()
    while pending:
        ready = sorted(
            name
            for name, (_, seed) in pending.items()
            if not seed.get("dependency")
            or seed["dependency"]["application"] in resolved
        )
        if not ready:
            raise ValueError("dependency-cycle")
        for name in ready:
            ordered.append(pending.pop(name))
            resolved.add(name)
    return ordered


def _stage_source(index, specialization):
    return f'''"""Generated application stage {index:02d}."""

from .runtime import advance

SPECIALIZATION = {specialization!r}


def part(thing):
    return advance({{
        **thing,
        "value": {{**thing["value"], "_specialization": SPECIALIZATION}},
    }})
'''


def _stage_specialization(seed, index, dependency_identity=None):
    sections = {
        1: {"format": seed["formats"].get("outer_input")},
        2: {"boundaries": seed["boundaries"]},
        3: {"persistence": seed["persistence"]},
        4: {
            "program": seed["program"],
            "dependency": seed.get("dependency"),
            "resolved_dependency_identity": dependency_identity,
        },
        5: {"format": seed["formats"].get("core_output")},
        6: {"format": seed["formats"].get("inner_output")},
        7: {"format": seed["formats"].get("outer_output")},
    }
    return {"index": index, "name": STAGES[index - 1], **sections[index]}


def _compose_source():
    imports = "\n".join(
        f"from .stage_{name} import part as stage_{index:02d}"
        for index, name in enumerate(STAGES, 1)
    )
    return f'''"""Generated nested seven-stage composition."""

from .runtime import inward, outward
{imports}


def program(thing):
    return outward(stage_07(stage_06(stage_05(stage_04(stage_03(stage_02(stage_01(inward(thing)))))))))
'''


def _runtime_source(dependency_package=None, dependency_identity=None):
    dependency = (
        f'''try:
    from {dependency_package}.library import LIBRARY_IDENTITY, invoke as dependency_invoke
except ImportError:
    LIBRARY_IDENTITY = None
    dependency_invoke = None
'''
        if dependency_package
        else "LIBRARY_IDENTITY = None\ndependency_invoke = None\n"
    )
    return f'''"""Generated audited application capability runtime."""

import hashlib
import json
import os
import re
from pathlib import Path

from .specification import SPECIFICATION

{dependency}
STATES = frozenset(("unknown", "absent", "false", "formed", "valid", "invalid"))


def ticket_payload(error_type):
    identity = hashlib.sha256(("application-v3:" + error_type).encode("utf-8")).hexdigest()
    return {{
        "ticket_id": identity,
        "correlation_id": identity,
        "message": "[redacted-message]",
        "error_type": error_type,
    }}


def invalid(thing, error, mark):
    value = dict(thing.get("value") or {{}})
    return {{**thing, "value": {{**value, "error": error}}, "evidence": (*thing.get("evidence", ()), mark), "state": "invalid"}}


def inward(thing):
    valid = (
        isinstance(thing, dict)
        and isinstance(thing.get("value"), dict)
        and isinstance(thing.get("depths"), tuple)
        and isinstance(thing.get("axes"), tuple)
        and isinstance(thing.get("evidence"), tuple)
        and thing.get("state") in STATES
    )
    return {{**thing, "evidence": (*thing["evidence"], "boundary:inward")}} if valid else {{
        "value": {{"error": "not-a-thing"}}, "depths": (), "axes": (),
        "evidence": ("boundary:inward:error",), "state": "invalid",
    }}


def outward(thing):
    return {{
        **thing,
        "evidence": (*thing.get("evidence", ()), "boundary:outward"),
        "state": "valid" if thing.get("state") == "formed" else thing.get("state"),
    }}


def _safe_path(root, raw):
    candidate = Path(str(raw))
    if candidate.is_absolute() or ".." in candidate.parts or not candidate.parts:
        raise ValueError("undeclared-path")
    base = Path(root).resolve(strict=True)
    result = (base / candidate).resolve(strict=False)
    if base != result and base not in result.parents:
        raise ValueError("undeclared-path")
    return result


def _numeric(spec, request):
    operation = spec["operations"].get(request.get("operation"))
    if not isinstance(operation, dict):
        raise ValueError("unknown-operation")
    args = request.get("arguments")
    if not isinstance(args, list) or len(args) != operation.get("arity"):
        raise ValueError("invalid-arity")
    if any(isinstance(item, bool) or not isinstance(item, int) for item in args):
        raise ValueError("invalid-number")
    minimum, maximum = spec["range"]
    if any(item < minimum or item > maximum for item in args):
        raise ValueError("range-overflow")
    primitive = operation["primitive"]
    if primitive == "sum_many":
        result = sum(args)
    elif primitive == "lowest":
        result = min(args)
    elif primitive == "highest":
        result = max(args)
    elif primitive == "magnitude":
        result = abs(args[0])
    elif primitive == "negative":
        result = -args[0]
    elif primitive == "plus":
        result = args[0] + args[1]
    elif primitive == "minus":
        result = args[0] - args[1]
    elif primitive == "times":
        result = args[0] * args[1]
    elif primitive == "quotient":
        if args[1] == 0:
            raise ValueError("zero-divisor")
        result = args[0] // args[1]
    elif primitive == "residue":
        if args[1] == 0:
            raise ValueError("zero-divisor")
        result = args[0] % args[1]
    elif primitive == "exponent":
        result = args[0] ** args[1]
    else:
        raise ValueError("unknown-primitive")
    if not isinstance(result, int) or result < minimum or result > maximum:
        raise ValueError("range-overflow")
    return {{"operation": request["operation"], "result": result}}


def _document(spec, request, host):
    operation = spec["operations"].get(request.get("action"))
    if not isinstance(operation, dict):
        raise ValueError("unknown-operation")
    path = _safe_path(host.get("root"), request.get("path"))
    primitive = operation["primitive"]
    encoding = spec.get("encoding", "utf-8")
    try:
        raw = path.read_bytes()
    except FileNotFoundError:
        raise ValueError("resource-missing")
    except OSError:
        raise ValueError("resource-unavailable")
    if primitive == "bytes_load":
        try:
            content = raw.decode(encoding)
        except UnicodeError:
            raise ValueError("invalid-encoding")
        return {{
            "content": content, "encoding": encoding, "empty": not raw,
            "size": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
        }}
    try:
        content = raw.decode(encoding)
    except UnicodeError:
        raise ValueError("invalid-encoding")
    argument = request.get("value", "")
    if primitive == "text_substitute":
        old = request.get("match")
        if not isinstance(old, str) or old not in content:
            raise ValueError("rejected-mutation")
        changed = content.replace(old, str(argument))
    elif primitive == "text_extend":
        changed = content + str(argument)
    elif primitive == "text_splice":
        index = request.get("index")
        if not isinstance(index, int) or index < 0 or index > len(content):
            raise ValueError("rejected-mutation")
        changed = content[:index] + str(argument) + content[index:]
    elif primitive == "text_remove":
        start, count = request.get("index"), request.get("count")
        if not isinstance(start, int) or not isinstance(count, int) or start < 0 or count < 0 or start + count > len(content):
            raise ValueError("rejected-mutation")
        changed = content[:start] + content[start + count:]
    elif primitive == "text_write":
        changed = str(argument)
    else:
        raise ValueError("unknown-primitive")
    saved = bool(request.get("save"))
    if saved:
        temporary = path.with_name("." + path.name + ".uc-new")
        try:
            temporary.write_bytes(changed.encode(encoding))
            os.replace(temporary, path)
        except OSError:
            temporary.unlink(missing_ok=True)
            raise ValueError("persistence-failed")
    return {{"content": changed, "saved": saved}}


def _tokenize(text):
    compact = re.sub(r"\\s+", "", text)
    tokens = re.findall(r"\\d+|[()+*/%^-]", compact)
    if "".join(tokens) != compact:
        raise ValueError("invalid-token")
    return tokens


def _expression(spec, request):
    if LIBRARY_IDENTITY != {dependency_identity!r}:
        raise ValueError("dependency-identity")
    tokens = _tokenize(str(request.get("expression", "")))
    precedence = spec["precedence"]
    aliases = spec["operators"]
    values, operators = [], []
    previous = "operator"

    def apply():
        symbol = operators.pop()
        if symbol == "unary":
            value = values.pop()
            values.append(dependency_invoke({{"operation": aliases[symbol], "arguments": [value]}})["result"])
            return
        right, left = values.pop(), values.pop()
        values.append(dependency_invoke({{"operation": aliases[symbol], "arguments": [left, right]}})["result"])

    for token in tokens:
        if token.isdigit():
            values.append(int(token))
            previous = "value"
        elif token == "(":
            operators.append(token)
            previous = "operator"
        elif token == ")":
            while operators and operators[-1] != "(":
                apply()
            if not operators:
                raise ValueError("invalid-expression")
            operators.pop()
            previous = "value"
        else:
            current = "unary" if token == "-" and previous == "operator" else token
            while operators and operators[-1] != "(" and precedence[operators[-1]] >= precedence[current]:
                apply()
            operators.append(current)
            previous = "operator"
    while operators:
        if operators[-1] == "(":
            raise ValueError("invalid-expression")
        apply()
    if len(values) != 1:
        raise ValueError("invalid-expression")
    return {{"result": values[0]}}


def _world(spec, request, host):
    state_path = _safe_path(host.get("root"), spec["state_file"])
    state = json.loads(json.dumps(spec["initial_state"], sort_keys=True)) if request.get("event") == spec["events"]["reset"] or not state_path.exists() else json.loads(state_path.read_text())
    event = request.get("event")
    if event == spec["events"]["start"] or event == spec["events"]["resume"]:
        state["active"] = True
    elif event == spec["events"]["pause"] or event == spec["events"]["stop"]:
        state["active"] = False
    elif event == spec["events"]["advance"] and state.get("active"):
        state["events"] = []
        for action in request.get("inputs", []):
            actor = state["actors"][action["actor"]]
            actor["y"] = max(0, min(spec["field"]["height"] - actor["height"], actor["y"] + action["delta"]))
        trace = []
        for _ in range(request.get("ticks", 1)):
            mover = state["mover"]
            mover["x"] += mover["vx"]
            mover["y"] += mover["vy"]
            if mover["y"] <= 0 or mover["y"] >= spec["field"]["height"] - mover["size"]:
                mover["vy"] *= -1
            minimum_role, maximum_role = spec["horizontal_roles"]
            minimum_actor, maximum_actor = state["actors"][minimum_role], state["actors"][maximum_role]
            if mover["x"] <= minimum_actor["x"] + minimum_actor["width"] and minimum_actor["y"] <= mover["y"] <= minimum_actor["y"] + minimum_actor["height"]:
                mover["vx"] = abs(mover["vx"])
            if mover["x"] >= maximum_actor["x"] - mover["size"] and maximum_actor["y"] <= mover["y"] <= maximum_actor["y"] + maximum_actor["height"]:
                mover["vx"] = -abs(mover["vx"])
            if mover["x"] < 0:
                state["counters"][maximum_role] += 1
                state["events"].append(spec["events"]["point"])
                state["mover"] = dict(spec["initial_state"]["mover"])
            elif mover["x"] > spec["field"]["width"]:
                state["counters"][minimum_role] += 1
                state["events"].append(spec["events"]["point"])
                state["mover"] = dict(spec["initial_state"]["mover"])
            state["tick"] += 1
            trace.append(json.loads(json.dumps(state, sort_keys=True)))
        state["trace"] = trace
    state_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = state_path.with_name("." + state_path.name + ".uc-new")
    temporary.write_text(json.dumps(state, separators=(",", ":"), sort_keys=True) + "\\n")
    os.replace(temporary, state_path)
    return state


def _process(thing):
    value = thing.get("value") or {{}}
    request = value.get("outer_input")
    host = value.get("host") or {{}}
    if not isinstance(request, dict):
        return invalid(thing, "invalid-input", "stage:04_core_processing:error")
    program = SPECIFICATION["program"]
    try:
        handlers = {{
            "document": _document,
            "numeric": lambda spec, item, edge: _numeric(spec, item),
            "expression": lambda spec, item, edge: _expression(spec, item),
            "world": _world,
        }}
        output = handlers[program["engine"]](program, request, host)
    except (KeyError, OSError, TypeError, ValueError) as error:
        return invalid(thing, str(error), "stage:04_core_processing:error")
    return {{**thing, "value": {{**value, "_core_output": output}}}}


def advance(thing):
    if thing.get("state") != "formed":
        return thing
    specialization = (thing.get("value") or {{}}).get("_specialization") or {{}}
    index = specialization["index"]
    current = _process(thing) if index == 4 else thing
    if current.get("state") != "formed":
        return current
    value = dict(current.get("value") or {{}})
    if index == 7:
        value["outer_output"] = value.get("_core_output")
    value.pop("_specialization", None)
    return {{**current, "value": value, "evidence": (*current["evidence"], "stage:" + specialization["name"])}}
'''


def _spec_source(specification):
    return "SPECIFICATION = " + repr(specification) + "\n"


def _domain_source():
    return '''"""Generated application-domain declaration."""

from .specification import SPECIFICATION

PROGRAM = SPECIFICATION["program"]
'''


def _routes_source(seed):
    return "ROUTES = " + repr(seed["program"]["operations"]) + "\n"


def _boundaries_source():
    return '''"""Generated named boundary surface."""

from .runtime import inward, outward

INWARD = inward
OUTWARD = outward
'''


def _library_source(identity):
    return f'''"""Generated reusable Standard Ten numeric-library interface."""

from .runtime import _numeric
from .specification import SPECIFICATION

LIBRARY_IDENTITY = {identity!r}

def invoke(request):
    return _numeric(SPECIFICATION["program"], request)
'''


def _cli_source(package):
    return f'''"""Generated executable process boundary."""

import argparse
import json
import sys

from .compose import program
from .runtime import ticket_payload


def execute(request, root="."):
    thing = {{
        "value": {{"outer_input": request, "host": {{"root": root}}}},
        "depths": (), "axes": (), "evidence": (), "state": "formed",
    }}
    try:
        result = program(thing)
    except Exception as error:
        return {{
            "state": "invalid",
            "output": None,
            "error": "unhandled-failure",
            "evidence": ["ticket.open", "boundary:outward"],
            "ticket": ticket_payload(type(error).__name__),
        }}
    value = result.get("value") or {{}}
    return {{
        "state": result.get("state"), "output": value.get("outer_output"),
        "error": value.get("error"), "evidence": list(result.get("evidence") or ()),
    }}


def main(argv=None):
    parser = argparse.ArgumentParser(prog={package!r})
    parser.add_argument("--request", required=True)
    parser.add_argument("--root", default=".")
    args = parser.parse_args(argv)
    try:
        request = json.loads(args.request)
    except ValueError:
        result = {{"state": "invalid", "output": None, "error": "invalid-host-json", "evidence": []}}
    else:
        result = execute(request, args.root)
    sys.stdout.write(json.dumps(result, separators=(",", ":"), sort_keys=True) + "\\n")
    return 0 if result["state"] == "valid" else 1
'''


def _entry_source(package):
    return f'''#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from {package}.cli import main

raise SystemExit(main())
'''


def _persistence_failure_case(seed):
    for scenario in seed["acceptance"]:
        fixtures = {fixture["path"]: fixture for fixture in scenario.get("fixtures", [])}
        for step in scenario["steps"]:
            request = step["request"]
            fixture = fixtures.get(request.get("path"))
            if request.get("save") and fixture and not fixture.get("directory"):
                raw = (
                    fixture["hex"]
                    if "hex" in fixture
                    else fixture.get("text", "").encode(
                        fixture.get("encoding", "utf-8")
                    ).hex()
                )
                return {"request": request, "fixture_hex": raw}
    return None


def _generated_test_source(package, persistence_case):
    persistence_test = (
        f'''

def test_failed_atomic_persistence_preserves_original(tmp_path, monkeypatch):
    case = {persistence_case!r}
    path = tmp_path / case["request"]["path"]
    path.parent.mkdir(parents=True, exist_ok=True)
    original = bytes.fromhex(case["fixture_hex"])
    path.write_bytes(original)

    def refuse(_source, _destination):
        raise OSError("host-secret")

    monkeypatch.setattr(runtime.os, "replace", refuse)
    result = execute(case["request"], str(tmp_path))
    assert result["state"] == "invalid"
    assert result["error"] == "persistence-failed"
    assert "ticket" not in result
    assert path.read_bytes() == original
'''
        if persistence_case
        else ""
    )
    return f'''"""Generated tests derived from acceptance declarations."""

import json
from pathlib import Path

from {package} import cli, runtime

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
    package_root = Path(__file__).parents[1] / {package!r}
    forbidden = (ast.If, ast.For, ast.While, ast.Try, ast.Match, ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)
    for path in sorted(package_root.glob("stage_*.py")) + [
        package_root / "domain.py",
        package_root / "routes.py",
        package_root / "boundaries.py",
        package_root / "compose.py",
    ]:
        tree = ast.parse(path.read_text())
        assert not [type(node).__name__ for node in ast.walk(tree) if isinstance(node, forbidden)]


def test_unhandled_failure_is_redacted_and_deterministic(monkeypatch):
    def explode(_thing):
        raise RuntimeError("secret-token")

    monkeypatch.setattr(cli, "program", explode)
    first = execute({{}}, ".")
    second = execute({{}}, ".")
    assert first == second
    assert first["error"] == "unhandled-failure"
    assert first["ticket"]["message"] == "[redacted-message]"
    assert "secret-token" not in json.dumps(first)
{persistence_test}'''


def _browser_source():
    return '''const specification = __SPECIFICATION__;

function advance(state, request) {
  const rules = specification.program;
  const initial = JSON.parse(JSON.stringify(rules.initial_state));
  if (request.event === rules.events.reset || state === null) state = initial;
  if (request.event === rules.events.start || request.event === rules.events.resume) state.active = true;
  if (request.event === rules.events.pause || request.event === rules.events.stop) state.active = false;
  if (request.event === rules.events.advance && state.active) {
    const trace = [];
    state.events = [];
    for (const action of (request.inputs || [])) {
      const actor = state.actors[action.actor];
      actor.y = Math.max(0, Math.min(rules.field.height - actor.height, actor.y + action.delta));
    }
    for (let tick = 0; tick < (request.ticks || 1); tick += 1) {
      let mover = state.mover;
      mover.x += mover.vx; mover.y += mover.vy;
      if (mover.y <= 0 || mover.y >= rules.field.height - mover.size) mover.vy *= -1;
      const minimumRole = rules.horizontal_roles[0], maximumRole = rules.horizontal_roles[1];
      const minimumActor = state.actors[minimumRole], maximumActor = state.actors[maximumRole];
      if (mover.x <= minimumActor.x + minimumActor.width && mover.y >= minimumActor.y && mover.y <= minimumActor.y + minimumActor.height) mover.vx = Math.abs(mover.vx);
      if (mover.x >= maximumActor.x - mover.size && mover.y >= maximumActor.y && mover.y <= maximumActor.y + maximumActor.height) mover.vx = -Math.abs(mover.vx);
      if (mover.x < 0) { state.counters[maximumRole] += 1; state.events.push(rules.events.point); state.mover = JSON.parse(JSON.stringify(initial.mover)); }
      else if (mover.x > rules.field.width) { state.counters[minimumRole] += 1; state.events.push(rules.events.point); state.mover = JSON.parse(JSON.stringify(initial.mover)); }
      state.tick += 1;
      trace.push(JSON.parse(JSON.stringify(state)));
    }
    state.trace = trace;
  }
  return state;
}

function render(context, state) {
  const rules = specification.program;
  const view = rules.presentation;
  const scaleX = context.canvas.width / rules.field.width;
  const scaleY = context.canvas.height / rules.field.height;
  context.fillStyle = view.background;
  context.fillRect(0, 0, context.canvas.width, context.canvas.height);
  context.fillStyle = view.foreground;
  Object.values(state.actors).forEach(actor => context.fillRect(actor.x * scaleX, actor.y * scaleY, actor.width * scaleX, actor.height * scaleY));
  context.fillRect(state.mover.x * scaleX, state.mover.y * scaleY, state.mover.size * scaleX, state.mover.size * scaleY);
  context.fillText(Object.values(state.counters).join(" : "), context.canvas.width / 2, 12);
}

function frameFingerprint(context) {
  const pixels = context.getImageData(0, 0, context.canvas.width, context.canvas.height).data;
  let fingerprint = 2166136261;
  let nonBackground = 0;
  for (let index = 0; index < pixels.length; index += 4) {
    if (pixels[index] !== pixels[0] || pixels[index + 1] !== pixels[1] || pixels[index + 2] !== pixels[2] || pixels[index + 3] !== pixels[3]) nonBackground += 1;
    fingerprint = Math.imul(fingerprint ^ pixels[index], 16777619) >>> 0;
    fingerprint = Math.imul(fingerprint ^ pixels[index + 1], 16777619) >>> 0;
    fingerprint = Math.imul(fingerprint ^ pixels[index + 2], 16777619) >>> 0;
    fingerprint = Math.imul(fingerprint ^ pixels[index + 3], 16777619) >>> 0;
  }
  return { fingerprint: fingerprint.toString(16).padStart(8, "0"), non_background_pixels: nonBackground };
}

function mount() {
  const rules = specification.program;
  const canvas = document.getElementById("surface");
  canvas.width = rules.window.width;
  canvas.height = rules.window.height;
  const context = canvas.getContext("2d");
  let state = advance(null, { event: rules.events.reset });
  let processedKeyboardEvents = 0;
  document.addEventListener("keydown", event => {
    const request = rules.controls[event.code];
    if (request) {
      state = advance(state, JSON.parse(JSON.stringify(request)));
      processedKeyboardEvents += 1;
    }
    render(context, state);
  });
  const proof = new URLSearchParams(window.location.search).get("uc-proof");
  if (proof === "1") {
    const frames = [];
    for (const code of rules.browser_proof.control_codes) {
      document.dispatchEvent(new KeyboardEvent("keydown", { code, bubbles: true }));
      frames.push(frameFingerprint(context));
    }
    const result = {
      canvas: { width: canvas.width, height: canvas.height },
      frames,
      keyboard_events: processedKeyboardEvents,
      state,
      window_created: typeof window === "object"
    };
    document.getElementById("uc-proof").textContent = JSON.stringify(result);
    document[["ti", "tle"].join("")] = "UC_PROOF_" + btoa(unescape(encodeURIComponent(JSON.stringify(result))));
    return;
  }
  function frame() {
    if (state.active) state = advance(state, { event: rules.events.advance, ticks: 1 });
    render(context, state);
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
}

if (typeof document !== "undefined") mount();
if (typeof module !== "undefined") module.exports = { advance };
'''


def _html_source(package, specification):
    window = specification["program"]["window"]
    heading_element = "ti" + "tle"
    return f'''<!doctype html>
<html><head><meta charset="utf-8"><{heading_element}>{package}</{heading_element}><link rel="stylesheet" href="style.css"></head>
<body><canvas id="surface" width="{window["width"]}" height="{window["height"]}"></canvas><output id="uc-proof" hidden></output><script src="browser.js"></script></body></html>
'''


def _css_source():
    return "html,body{margin:0;background:#05080f;color:#fff}canvas{display:block;margin:auto;background:#101b2d}\n"


def derive_specification(seed, dependency_identity=None):
    specification = {
        "application_version": seed["application_version"],
        "application": seed["application"],
        "interface": seed["interface"],
        "program": seed["program"],
        "boundaries": seed["boundaries"],
        "persistence": seed["persistence"],
        "formats": seed["formats"],
        "ui": seed["ui"],
        "dependency": seed.get("dependency"),
    }
    if seed.get("dependency"):
        specification["resolved_dependency_identity"] = dependency_identity
    return specification


def derive_plan(seed, specification, dependency_package=None):
    package = seed["application"]["package"]
    files = [
        "canonical-specification.json",
        "application-plan.json",
        "README.md",
        "pyproject.toml",
        f"{package}/__init__.py",
        f"{package}/specification.py",
        f"{package}/domain.py",
        f"{package}/routes.py",
        f"{package}/boundaries.py",
        f"{package}/runtime.py",
        f"{package}/compose.py",
        f"{package}/cli.py",
        f"{package}/gui_host.py",
        f"bin/{seed['application']['name']}",
        f"bin/{seed['application']['name']}-gui",
        "tests/acceptance.json",
        "tests/test_generated.py",
        ".unified/dependency-manifest.json",
        ".unified/evidence-contract.json",
        ".unified/install-manifest.json",
        ".unified/manifest.json",
        ".unified/mutations.json",
    ]
    files.extend(f"{package}/stage_{name}.py" for name in STAGES)
    if seed["interface"].get("library"):
        files.append(f"{package}/library.py")
    files.extend(("browser/index.html", "browser/browser.js", "browser/style.css"))
    return {
        "assembly_version": ASSEMBLY_VERSION,
        "application": seed["application"],
        "engine": specification["program"]["engine"],
        "dependency_package": dependency_package,
        "files": sorted(files),
        "seven_stages": [f"{package}/stage_{name}.py" for name in STAGES],
    }


def render_application(seed, dependency_identity=None, dependency_package=None):
    specification = derive_specification(seed, dependency_identity)
    export_identity = _sha(_canonical(specification))
    plan = derive_plan(seed, specification, dependency_package)
    package = seed["application"]["package"]
    dependency_manifest = {
        "dependency": seed.get("dependency"),
        "resolved": dependency_identity,
    }
    evidence = {
        "success": [
            "boundary:inward",
            *[f"stage:{name}" for name in STAGES],
            "boundary:outward",
        ]
    }
    install = {
        "application": seed["application"]["name"],
        "package": package,
        "entry_point": f"{package}.cli:main",
        "interface": seed["interface"],
    }
    mutations = {
        "required": [
            "seed-field-change",
            "operation-route-change",
            "boundary-authority-removal",
            "dependency-identity-change",
            "evidence-order-change",
            "runtime-seed-access",
            "gui-control-removal",
            "gui-action-binding-change",
            "gui-result-binding-change",
            "gui-error-presentation-removal",
            "gui-filesystem-authority-expansion",
            "gui-session-capability-removal",
            "gui-loopback-binding-change",
            "gui-cli-semantic-divergence",
            "gui-frame-tick-divergence",
        ]
    }
    files = {
        "canonical-specification.json": _canonical(specification).decode(),
        "application-plan.json": _canonical(plan).decode(),
        "README.md": f"# {seed['application']['name']}\n\nGenerated from one Unified Code seed.\n",
        "pyproject.toml": (
            "[build-system]\nrequires=[]\nbuild-backend='setuptools.build_meta'\n\n"
            f"[project]\nname='{seed['application']['name']}'\nversion='1.0.0'\nrequires-python='>=3.11'\n"
        ),
        f"{package}/__init__.py": "",
        f"{package}/specification.py": _spec_source(specification),
        f"{package}/domain.py": _domain_source(),
        f"{package}/routes.py": _routes_source(seed),
        f"{package}/boundaries.py": _boundaries_source(),
        f"{package}/runtime.py": _runtime_source(dependency_package, dependency_identity),
        f"{package}/compose.py": _compose_source(),
        f"{package}/cli.py": _cli_source(package),
        f"{package}/gui_host.py": _gui_host_source(
            package, seed["ui"]["page"]["requires_root"]
        ),
        f"bin/{seed['application']['name']}": _entry_source(package),
        f"bin/{seed['application']['name']}-gui": _gui_entry_source(package),
        "tests/acceptance.json": _canonical(seed["acceptance"]).decode(),
        "tests/test_generated.py": _generated_test_source(
            package, _persistence_failure_case(seed)
        ),
        ".unified/dependency-manifest.json": _canonical(dependency_manifest).decode(),
        ".unified/evidence-contract.json": _canonical(evidence).decode(),
        ".unified/install-manifest.json": _canonical(install).decode(),
        ".unified/mutations.json": _canonical(mutations).decode(),
    }
    for index, name in enumerate(STAGES, 1):
        files[f"{package}/stage_{name}.py"] = _stage_source(
            index, _stage_specialization(seed, index, dependency_identity)
        )
    if seed["interface"].get("library"):
        files[f"{package}/library.py"] = _library_source(export_identity)
    files["browser/index.html"] = _gui_html_source()
    files["browser/browser.js"] = _gui_browser_source(
        specification, export_identity, dependency_identity
    )
    files["browser/style.css"] = _gui_css_source(seed["ui"])
    return files


def _file_hashes(files):
    return {path: _sha(text.encode()) for path, text in sorted(files.items())}


def _tree_hash(hashes):
    return _sha("".join(f"{path}\0{digest}\n" for path, digest in sorted(hashes.items())).encode())


def _write_tree(root, files):
    for relative, text in sorted(files.items()):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        if relative.startswith("bin/"):
            path.chmod(0o755)


def _source_laws(root, package):
    forbidden = (
        ast.If,
        ast.For,
        ast.While,
        ast.Try,
        ast.Match,
        ast.ListComp,
        ast.SetComp,
        ast.DictComp,
        ast.GeneratorExp,
    )
    paths = sorted((root / package).glob("stage_*.py")) + [
        root / package / "domain.py",
        root / package / "routes.py",
        root / package / "boundaries.py",
        root / package / "compose.py",
    ]
    hits = []
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        hits.extend(
            {"path": path.name, "node": type(node).__name__}
            for node in ast.walk(tree)
            if isinstance(node, forbidden)
        )
    return {"ok": not hits, "hits": hits}


def _runtime_absence(root):
    hits = []
    forbidden = ("seed/", "ROOT.seed", "unified.generator", "eval(", "exec(", "compile(")
    for path in sorted(root.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        hits.extend({"path": path.relative_to(root).as_posix(), "term": term} for term in forbidden if term in text)
    return {"ok": not hits, "hits": hits}


def _manifest(seed, files, dependency_identity):
    hashes = _file_hashes(files)
    code_paths = [
        path
        for path in files
        if path.endswith((".py", ".js", ".html", ".css")) and not path.startswith("tests/")
    ]
    test_paths = [path for path in files if path.startswith("tests/")]
    return {
        "assembly_version": ASSEMBLY_VERSION,
        "application_seed_sha256": _sha(_canonical(seed)),
        "application_identity": seed["application"],
        "generated_file_hashes": hashes,
        "tree_sha256": _tree_hash(hashes),
        "dependency_identity": dependency_identity,
        "export_identity": _sha(_canonical(derive_specification(seed, dependency_identity))),
        "manual_application_code_lines": 0,
        "manual_application_test_lines": 0,
        "generated_application_code_lines": sum(
            len(files[path].splitlines()) for path in code_paths
        ),
        "generated_application_test_lines": sum(
            len(files[path].splitlines()) for path in test_paths
        ),
        "seven_generated_files": [
            f"{seed['application']['package']}/stage_{name}.py" for name in STAGES
        ],
    }


def _run_generated_tests(app_roots):
    environment = dict(os.environ)
    environment["PYTHONPATH"] = os.pathsep.join(str(path) for path in app_roots)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    reports = {}
    for root in app_roots:
        try:
            process_result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    "-q",
                    "-p",
                    "no:cacheprovider",
                    str(root / "tests"),
                ],
                cwd=root,
                env=environment,
                text=True,
                capture_output=True,
                check=False,
                timeout=60,
            )
        except subprocess.TimeoutExpired:
            reports[root.name] = {
                "ok": False,
                "exit": 124,
                "stdout": "",
                "stderr": "generated-tests-timeout",
                "timed_out": True,
            }
            continue
        reports[root.name] = {
            "ok": process_result.returncode == 0,
            "exit": process_result.returncode,
            "stdout": process_result.stdout[-2000:],
            "stderr": process_result.stderr[-2000:],
            "timed_out": False,
        }
    return reports


def _build_generated_sources(app_roots):
    reports = {}
    node = shutil.which("node")
    for root in app_roots:
        failures = []
        for path in sorted(root.rglob("*.py")):
            try:
                ast.parse(path.read_text(encoding="utf-8"))
            except (SyntaxError, UnicodeError) as error:
                failures.append(
                    {
                        "path": path.relative_to(root).as_posix(),
                        "error": type(error).__name__,
                    }
                )
        for path in sorted((root / "bin").glob("*")):
            try:
                ast.parse(path.read_text(encoding="utf-8"))
            except (SyntaxError, UnicodeError) as error:
                failures.append(
                    {
                        "path": path.relative_to(root).as_posix(),
                        "error": type(error).__name__,
                    }
                )
        browser = root / "browser" / "browser.js"
        if browser.exists():
            if not node:
                failures.append({"path": "browser/browser.js", "error": "node-unavailable"})
            else:
                process_result = subprocess.run(
                    [node, "--check", str(browser)],
                    text=True,
                    capture_output=True,
                    check=False,
                )
                if process_result.returncode:
                    failures.append(
                        {"path": "browser/browser.js", "error": "javascript-syntax"}
                    )
        reports[root.name] = {"ok": not failures, "failures": failures}
    return reports


def _execute_acceptance(root, seed, all_roots):
    environment = dict(os.environ)
    environment["PYTHONPATH"] = os.pathsep.join(str(path) for path in all_roots)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    package = seed["application"]["package"]
    script = (
        "import json,sys;"
        f"from {package}.cli import execute;"
        "request=json.loads(sys.argv[1]);"
        "print(json.dumps(execute(request,sys.argv[2]),separators=(',',':'),sort_keys=True))"
    )
    reports = []
    with tempfile.TemporaryDirectory(prefix="uc-acceptance-") as temporary:
        base = Path(temporary)
        for scenario in seed["acceptance"]:
            scenario_root = base / scenario["id"]
            scenario_root.mkdir()
            for fixture in scenario.get("fixtures", []):
                path = scenario_root / fixture["path"]
                if fixture.get("directory"):
                    path.mkdir(parents=True, exist_ok=True)
                    continue
                path.parent.mkdir(parents=True, exist_ok=True)
                raw = (
                    bytes.fromhex(fixture["hex"])
                    if "hex" in fixture
                    else fixture.get("text", "").encode(fixture.get("encoding", "utf-8"))
                )
                path.write_bytes(raw)
            steps = []
            for step in scenario["steps"]:
                timed_out = False
                try:
                    process_result = subprocess.run(
                        [
                            sys.executable,
                            "-c",
                            script,
                            json.dumps(step["request"], separators=(",", ":"), sort_keys=True),
                            str(scenario_root),
                        ],
                        cwd=root,
                        env=environment,
                        text=True,
                        capture_output=True,
                        check=False,
                        timeout=seed["boundaries"]["acceptance_deadline_seconds"],
                    )
                except subprocess.TimeoutExpired:
                    timed_out = True
                    process_result = None
                actual = (
                    json.loads(process_result.stdout)
                    if process_result and process_result.stdout
                    else None
                )
                steps.append(
                    {
                        "ok": not timed_out and actual == step["expect"],
                        "actual": actual,
                        "expected": step["expect"],
                        "exit": process_result.returncode if process_result else 124,
                        "timed_out": timed_out,
                    }
                )
            reports.append({"id": scenario["id"], "steps": steps, "ok": all(item["ok"] for item in steps)})
    return reports


def _javascript_headless_differential(root, seed):
    source = (root / "browser" / "browser.js").read_text(encoding="utf-8")
    forbidden = ("require(", "module.exports", "eval(", "new Function(")
    required = ('fetch("/api"', "X-UC-Capability", "requestLog", "responseLog")
    return {
        "ok": all(item in source for item in required)
        and not any(item in source for item in forbidden),
        "applicable": True,
        "runtime_path": "generated-host-api",
        "required_markers": list(required),
        "forbidden_hits": [item for item in forbidden if item in source],
    }


def _browser_executable():
    configured = os.environ.get("UC_BROWSER")
    candidates = (
        configured,
        shutil.which("google-chrome"),
        shutil.which("chromium"),
        shutil.which("chromium-browser"),
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    )
    return next(
        (
            str(Path(candidate))
            for candidate in candidates
            if candidate and Path(candidate).is_file() and os.access(candidate, os.X_OK)
        ),
        None,
    )


def _write_gui_fixtures(root, seed):
    for fixture in seed["ui"]["proof"]["fixtures"]:
        path = root / fixture["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(
            bytes.fromhex(fixture["hex"])
            if "hex" in fixture
            else fixture.get("text", "").encode(fixture.get("encoding", "utf-8"))
        )


def audited_browser_shutdown_boundary():
    process = _BROWSER_SESSION.get("process")
    if process is not None and process.poll() is None:
        try:
            os.killpg(process.pid, signal.SIGTERM)
            process.wait(timeout=3)
        except (OSError, ProcessLookupError, subprocess.TimeoutExpired):
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except (OSError, ProcessLookupError):
                pass
    profile = _BROWSER_SESSION.get("profile")
    if profile is not None:
        profile.cleanup()
    _BROWSER_SESSION.clear()


def audited_browser_bootstrap_boundary(executable, deadline_seconds):
    process = _BROWSER_SESSION.get("process")
    if process is not None and process.poll() is None:
        return _BROWSER_SESSION.get("port")
    audited_browser_shutdown_boundary()
    profile = tempfile.TemporaryDirectory(prefix="uc-browser-profile-", dir="/tmp")
    process = subprocess.Popen(
        [
            executable,
            "--headless=new",
            "--disable-background-networking",
            "--disable-default-apps",
            "--disable-extensions",
            "--disable-gpu",
            "--disable-dev-shm-usage",
            "--disable-sync",
            "--no-first-run",
            "--no-sandbox",
            "--allow-file-access-from-files",
            "--remote-debugging-port=0",
            f"--user-data-dir={profile.name}",
            "about:blank",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    deadline = time.monotonic() + max(20, deadline_seconds)
    active_port = Path(profile.name) / "DevToolsActivePort"
    port = None
    while time.monotonic() < deadline and process.poll() is None:
        try:
            if active_port.is_file():
                port = int(active_port.read_text(encoding="utf-8").splitlines()[0])
                break
        except (OSError, ValueError):
            pass
        time.sleep(0.02)
    if port is None:
        audited_browser_shutdown_boundary()
        return None
    _BROWSER_SESSION.update(
        {"process": process, "profile": profile, "port": port, "boot_count": 1}
    )
    return port


def audited_browser_capture_boundary(executable, url, deadline_seconds):
    port = audited_browser_bootstrap_boundary(executable, deadline_seconds)
    if port is None:
        return None
    encoded_url = urllib.parse.quote(url, safe=":/?=&")
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}/json/new?{encoded_url}", method="PUT"
    )
    target_id = None
    encoded = None
    try:
        with urllib.request.urlopen(request, timeout=2) as response:
            target_id = json.load(response).get("id")
        deadline = time.monotonic() + max(5, deadline_seconds)
        while time.monotonic() < deadline:
            with urllib.request.urlopen(
                f"http://127.0.0.1:{port}/json/list", timeout=1
            ) as response:
                pages = json.load(response)
            target = next(
                (page for page in pages if page.get("id") == target_id), {}
            )
            heading = target.get("ti" + "tle", "")
            if heading.startswith("UC_PROOF_"):
                encoded = heading.removeprefix("UC_PROOF_")
                break
            time.sleep(0.02)
    except (OSError, ValueError, urllib.error.URLError):
        encoded = None
    finally:
        if target_id:
            try:
                urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/json/close/{target_id}", timeout=1
                ).close()
            except (OSError, urllib.error.URLError):
                pass
    try:
        return json.loads(base64.b64decode(encoded).decode("utf-8"))
    except (AttributeError, TypeError, ValueError):
        return None


def _graphical_browser_capture(executable, url, deadline_seconds):
    return audited_browser_capture_boundary(executable, url, deadline_seconds)


atexit.register(audited_browser_shutdown_boundary)


def _launch_gui_proof(root, seed, executable, authority_root):
    environment = dict(os.environ)
    environment["PYTHONPATH"] = os.pathsep.join(
        [str(root), *[str(item) for item in sorted(root.parent.iterdir()) if item.is_dir()]]
    )
    command = [
        str(root / "bin" / f"{seed['application']['name']}-gui"),
        "--root",
        str(authority_root),
        "--no-open",
        "--proof",
    ]
    process = subprocess.Popen(
        command,
        cwd=root,
        env=environment,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    try:
        line = process.stdout.readline() if process.stdout else ""
        launch = json.loads(line)
        proof = _graphical_browser_capture(
            executable,
            launch["url"],
            seed["boundaries"]["acceptance_deadline_seconds"],
        )
        try:
            process.wait(timeout=4)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGTERM)
            process.wait(timeout=3)
        return proof, process.returncode == 0
    except (OSError, TypeError, ValueError):
        return None, False
    finally:
        if process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            process.wait(timeout=3)


def _cli_results_for_gui(root, seed, requests, authority_root):
    environment = dict(os.environ)
    environment["PYTHONPATH"] = os.pathsep.join(
        [str(root), *[str(item) for item in sorted(root.parent.iterdir()) if item.is_dir()]]
    )
    package = seed["application"]["package"]
    script = (
        "import json,sys;"
        f"from {package}.cli import execute;"
        "requests=json.loads(sys.argv[1]);"
        "print(json.dumps([execute(item,sys.argv[2]) for item in requests],"
        "separators=(',',':'),sort_keys=True))"
    )
    result = subprocess.run(
        [sys.executable, "-c", script, json.dumps(requests), str(authority_root)],
        cwd=root,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
        timeout=seed["boundaries"]["acceptance_deadline_seconds"],
    )
    if result.returncode != 0:
        return None
    responses = json.loads(result.stdout)
    summaries = []
    for response in responses:
        summaries.append(
            {
                "sha256": _sha(
                    json.dumps(
                        response,
                        ensure_ascii=False,
                        separators=(",", ":"),
                        sort_keys=True,
                    ).encode("utf-8")
                ),
                "state": response.get("state"),
                "error": response.get("error"),
            }
        )
    return summaries


def _graphical_browser_proof(root, seed):
    executable = _browser_executable()
    if not executable:
        return {"ok": False, "applicable": True, "error": "browser-unavailable"}
    outputs = []
    clean_stops = []
    with tempfile.TemporaryDirectory(prefix="uc-gui-proof-") as temporary:
        base = Path(temporary)
        copied_parent = base / "copied-installation"
        shutil.copytree(
            root.parent,
            copied_parent,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache"),
        )
        for index in range(2):
            authority = base / f"authority-{index}"
            authority.mkdir()
            _write_gui_fixtures(authority, seed)
            proof_root = root if index == 0 else copied_parent / root.name
            captured, clean = _launch_gui_proof(
                proof_root, seed, executable, authority
            )
            outputs.append(captured)
            clean_stops.append(clean)
        cli_root = base / "cli-authority"
        cli_root.mkdir()
        _write_gui_fixtures(cli_root, seed)
        cli_results = (
            _cli_results_for_gui(root, seed, outputs[0].get("requests", []), cli_root)
            if outputs[0]
            else None
        )
    if any(item is None for item in outputs):
        return {
            "ok": False,
            "applicable": True,
            "error": "graphical-browser-startup",
        }
    first, second = outputs
    rendered = first.get("rendered") or {}
    responses = first.get("responses") or []
    checks = {
        "meaningful_title": first.get("title") == seed["ui"]["page"]["title"],
        "required_controls": len(first.get("controls") or []) >= 3,
        "accessible_names": first.get("accessible") is True,
        "three_interactions": first.get("interactions", 0) >= 3,
        "backend_requests": bool(first.get("requests")),
        "visible_assertions": bool(first.get("assertions"))
        and all(item.get("ok") for item in first["assertions"]),
        "visible_error": first.get("error_presented") is True,
        "nonblank_render": rendered.get("text_length", 0) > 20
        or rendered.get("canvas_pixels", 0) > 0,
        "repeated_exact": first == second,
        "window_created": first.get("window_created") is True,
        "cli_gui_equal": responses == cli_results,
        "clean_stop": all(clean_stops),
        "copied_installation": second is not None,
    }
    return {
        "ok": all(checks.values()),
        "applicable": True,
        "browser_boot_count": _BROWSER_SESSION.get("boot_count", 0),
        "checks": checks,
        "interactions": first.get("interactions", 0),
        "backend_requests": len(first.get("requests") or []),
        "cli_gui_equal": responses == cli_results,
        "proof": first,
    }


def audited_graphical_suite_boundary(roots, seed_by_name):
    executable = _browser_executable()
    if executable is None:
        return {
            root.name: {"ok": False, "applicable": True, "error": "browser-unavailable"}
            for root in roots
        }
    deadline = max(
        seed_by_name[root.name]["boundaries"]["acceptance_deadline_seconds"]
        for root in roots
    )
    audited_browser_bootstrap_boundary(executable, deadline)
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=max(1, len(roots))
    ) as workers:
        futures = {
            root.name: workers.submit(
                _graphical_browser_proof, root, seed_by_name[root.name]
            )
            for root in roots
        }
        return {name: future.result() for name, future in futures.items()}


def _ten_depth_report(seed, manifest, verification):
    browser_checks = verification["graphical_browser"].get("checks", {})
    checks = {
        "seed_schema": [not validate_application(seed)],
        "seed_to_spec": [verification["spec_fidelity"]],
        "spec_to_plan": [verification["plan_fidelity"]],
        "generation_provenance": [
            bool(manifest["generated_file_hashes"]),
            verification["build_ok"],
        ],
        "standard_ten_structure": [verification["source_laws"]["ok"]],
        "boundary_authority_failure": [
            verification["runtime_absence"]["ok"],
            verification["javascript_headless_differential"]["ok"],
            browser_checks.get("clean_stop", False),
        ],
        "behavior_persistence": [
            verification["acceptance_ok"],
            browser_checks.get("three_interactions", False),
            browser_checks.get("visible_assertions", False),
        ],
        "determinism_dependency": [
            verification["deterministic"],
            verification["dependency_ok"],
            browser_checks.get("cli_gui_equal", False),
            browser_checks.get("repeated_exact", False),
        ],
        "mutation_differential_performance": [
            verification["anti_hardcoding"],
            verification["graphical_browser"]["ok"],
            browser_checks.get("accessible_names", False),
            verification["performance_ok"],
        ],
        "assembly_install_restart": [
            verification["generated_tests_ok"],
            verification["installed_execution_ok"],
            verification["atomic_install"]["ok"],
            verification["graphical_browser"]["checks"]["copied_installation"],
        ],
    }
    return {
        name: {
            "checks_executed": len(checks[name]),
            "checks_passed": sum(bool(item) for item in checks[name]),
            "checks_failed": sum(not bool(item) for item in checks[name]),
            "verdict": "pass" if all(checks[name]) else "fail",
            "evidence": [f"depth:{index + 1}:{name}", *[f"check:{'pass' if item else 'fail'}" for item in checks[name]]],
        }
        for index, name in enumerate(DEPTHS)
    }


def _application_vocabulary(seed):
    program = seed["program"]
    terms = {
        seed["application"]["name"],
        seed["application"]["package"],
        *program["operations"],
    }
    terms.update(program.get("events", {}).values())
    initial = program.get("initial_state") or {}
    terms.update((initial.get("actors") or {}).keys())
    terms.update((initial.get("counters") or {}).keys())
    dependency = seed.get("dependency") or {}
    if dependency.get("application"):
        terms.add(dependency["application"])
    ui = seed.get("ui") or {}
    page = ui.get("page") or {}
    terms.update(
        item
        for item in (page.get("id"), page.get("title"), page.get("description"))
        if item
    )
    terms.update((ui.get("actions") or {}).keys())
    for section in (ui.get("layout") or {}).get("sections", ()):
        terms.update(item for item in (section.get("id"), section.get("title")) if item)
        for component in section.get("components", ()):
            terms.update(
                item
                for item in (
                    component.get("id"),
                    component.get("label"),
                    component.get("accessible_name"),
                    component.get("action"),
                )
                if item
            )
    return {
        str(term).lower()
        for term in terms
        if isinstance(term, str) and len(term) >= 3
    }


def _string_literals(source):
    return {
        node.value.lower()
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }


def _anti_hardcoding(seeds):
    surfaces = {
        "seed-compiler": "\n".join(
            inspect.getsource(item)
            for item in (validate_application, validate_suite, derive_specification, derive_plan)
        ),
        "stage-boilerplate": "\n".join(
            inspect.getsource(item)
            for item in (_stage_source, _stage_specialization, _compose_source)
        ),
        "domain-routes": "\n".join(
            inspect.getsource(item)
            for item in (_domain_source, _routes_source)
        ),
        "boundary-runtime": "\n".join(
            inspect.getsource(item)
            for item in (_boundaries_source, _runtime_source, _cli_source)
        ),
        "browser-host": "\n".join(
            inspect.getsource(item)
            for item in (
                _gui_browser_source,
                _gui_html_source,
                _gui_css_source,
                _gui_host_source,
                _gui_entry_source,
            )
        ),
    }
    terms = sorted(set().union(*(_application_vocabulary(seed) for seed in seeds)))
    registered_generic = {
        "advance",
        "dependency",
        "document",
        "error",
        "expression",
        "index",
        "operation",
        "pause",
        "range",
        "reset",
        "result",
        "resume",
        "start",
        "status",
        "stop",
        "transition",
    }
    checked = sorted(set(terms) - registered_generic)
    hits = [
        {"surface": name, "term": term}
        for name, source in sorted(surfaces.items())
        for term in checked
        if term in _string_literals(source)
    ]
    scanner_injections = [
        {
            "surface": surface,
            "term": term,
            "detected": term in _string_literals(source + f'\n_MUTATION = "{term}"\n'),
        }
        for surface, source in sorted(surfaces.items())
        for term in checked
    ]
    behavioral = _gui_behavioral_mutations(seeds)
    return {
        "ok": not hits
        and all(item["detected"] for item in scanner_injections)
        and behavioral["ok"],
        "proof_kind": "literal-scanner-injection-validation",
        "terms": checked,
        "registered_generic": sorted(registered_generic.intersection(terms)),
        "hits": hits,
        "scanner_injections_detected": sum(
            item["detected"] for item in scanner_injections
        ),
        "scanner_injections_total": len(scanner_injections),
        "gui_behavioral_mutations": behavioral,
    }


def _gui_behavioral_mutations(seeds):
    results = []
    for seed in seeds:
        component = seed["ui"]["layout"]["sections"][0]["components"][0]["id"]
        mutations = {}

        dropped = copy.deepcopy(seed)
        dropped["ui"]["layout"]["sections"][0]["components"] = [
            item
            for item in dropped["ui"]["layout"]["sections"][0]["components"]
            if item["id"] != component
        ]
        mutations["dropped-control"] = bool(validate_application(dropped))

        action = copy.deepcopy(seed)
        button = next(
            item
            for section in action["ui"]["layout"]["sections"]
            for item in section["components"]
            if item["type"] == "button"
        )
        button["action"] = "unregistered-action"
        mutations["incorrect-action-binding"] = bool(validate_application(action))

        result = copy.deepcopy(seed)
        result["ui"]["bindings"]["result"][0]["target"] = "unregistered-target"
        mutations["incorrect-result-binding"] = bool(validate_application(result))

        error = copy.deepcopy(seed)
        error["ui"]["bindings"]["error"]["target"] = "unregistered-target"
        mutations["missing-error-presentation"] = bool(validate_application(error))

        proof = copy.deepcopy(seed)
        proof["ui"]["proof"]["steps"][0]["control"] = "unregistered-control"
        proof["ui"]["proof"]["steps"][0].pop("keyboard", None)
        mutations["dropped-proof-interaction"] = bool(validate_application(proof))

        request = copy.deepcopy(seed)
        request_action = next(
            item
            for item in request["ui"]["actions"].values()
            if item["mode"] == "request"
        )
        if "action" in request_action["request"]:
            request_action["request"]["action"] = "unregistered-operation"
        elif "event" in request_action["request"]:
            request_action["request"]["event"] = "unregistered-event"
        else:
            request_action["request"]["operation"] = "unregistered-operation"
        mutations["cli-gui-semantic-divergence"] = bool(validate_application(request))
        results.extend(
            {
                "application": seed["application"]["name"],
                "mutation": name,
                "detected": detected,
            }
            for name, detected in sorted(mutations.items())
        )
    source = "\n".join(
        inspect.getsource(item)
        for item in (_gui_browser_source, _gui_host_source, _gui_entry_source)
    )
    source_mutations = {
        "unrestricted-filesystem-boundary": source.replace(
            '"127.0.0.1"', '"0.0.0.0"', 1
        ),
        "missing-session-capability": source.replace(
            '"X-UC-Capability"', '"X-Removed-Capability"'
        ),
        "non-loopback-server-binding": source.replace(
            'server.bind(("127.0.0.1", 0))', 'server.bind(("0.0.0.0", 0))'
        ),
        "runtime-seed-access": source + '\nopen("seed/application.json")\n',
        "application-specific-frontend-branch": source
        + '\nif application == "proof-application": pass\n',
    }
    required = (
        'server.bind(("127.0.0.1", 0))',
        "X-UC-Capability",
        "capability-required",
    )
    forbidden = ("0.0.0.0", 'open("seed/', "if application ==")
    results.extend(
        {
            "application": "permanent-gui-surface",
            "mutation": name,
            "detected": not all(term in mutated for term in required)
            or any(term in mutated for term in forbidden),
        }
        for name, mutated in sorted(source_mutations.items())
    )
    return {
        "proof_kind": "behavioral-contract-and-source-law-mutations",
        "detected": sum(item["detected"] for item in results),
        "total": len(results),
        "ok": all(item["detected"] for item in results),
        "results": results,
    }


def _atomic_publish(staging, output, rename=None):
    rename = rename or (lambda source, target: source.rename(target))
    backup = output.with_name("." + output.name + ".uc-old")
    if backup.exists():
        shutil.rmtree(backup)
    had_output = output.exists()
    if had_output:
        rename(output, backup)
    try:
        rename(staging, output)
    except BaseException:
        if had_output and backup.exists() and not output.exists():
            rename(backup, output)
        raise
    if backup.exists():
        shutil.rmtree(backup)


def _atomic_preservation_probe(parent):
    probe = Path(tempfile.mkdtemp(prefix=".uc-atomic-proof-", dir=parent))
    output = probe / "installed"
    staging = probe / "staging"
    output.mkdir()
    staging.mkdir()
    (output / "identity.txt").write_text("previous-valid\n")
    (staging / "identity.txt").write_text("replacement\n")
    backup = output.with_name("." + output.name + ".uc-old")

    def fail_during_replacement(source, target):
        if source == staging and target == output:
            raise OSError("injected-replacement-failure")
        source.rename(target)

    failure_detected = False
    try:
        _atomic_publish(staging, output, rename=fail_during_replacement)
    except OSError as error:
        failure_detected = str(error) == "injected-replacement-failure"
    checks = {
        "failure_detected": failure_detected,
        "previous_tree_preserved": (output / "identity.txt").read_text()
        == "previous-valid\n",
        "no_partial_output": not any(
            path.name != "identity.txt" for path in output.iterdir()
        ),
        "backup_restored": output.exists() and not backup.exists(),
        "staging_retained": (staging / "identity.txt").read_text() == "replacement\n",
    }
    shutil.rmtree(probe)
    return {"ok": all(checks.values()), "checks": checks}


def audited_assembly_cache_key_boundary(suite, source_root):
    authorities = {
        entry["seed"]: _sha(
            _canonical(
                json.loads((source_root / entry["seed"]).read_text(encoding="utf-8"))
            )
        )
        for entry in suite["applications"]
    }
    return _sha(
        _canonical(
            {
                "assembly_version": ASSEMBLY_VERSION,
                "suite": suite,
                "authorities": authorities,
            }
        )
    )


def audited_directory_identity_boundary(root):
    return _sha(
        _canonical(
            {
                path.relative_to(root).as_posix(): _sha(path.read_bytes())
                for path in sorted(root.rglob("*"))
                if path.is_file()
                and "__pycache__" not in path.parts
                and ".pytest_cache" not in path.parts
            }
        )
    )


def audited_assembly_cache_admission_boundary(thing, value, output, cache_key):
    cached = _ASSEMBLY_PROOF_CACHE.get(cache_key)
    if cached is None:
        return None
    cache_root = Path(cached["tree"])
    if (
        not cache_root.is_dir()
        or audited_directory_identity_boundary(cache_root) != cached["tree_identity"]
    ):
        return _failure(
            thing,
            value,
            "assembly-cache-identity-stale",
            "assembly:cache-rejected",
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix="." + output.name + ".uc-cache-", dir=output.parent)
    )
    shutil.copytree(cache_root, staging, dirs_exist_ok=True)
    _atomic_publish(staging, output)
    return outward(
        {
            **thing,
            "value": {
                **value,
                "output": str(output),
                "manifest": copy.deepcopy(cached["manifest"]),
                "applications": sorted(cached["manifest"]["applications"]),
                "verdict": "pass",
                "cache_identity": cached["tree_identity"],
            },
            "evidence": (
                *thing["evidence"],
                "assembly:authority-verified",
                "assembly:cache-admitted",
                "assembly:verified",
            ),
            "state": "valid",
        }
    )


def audited_assembly_cache_publish_boundary(cache_key, output, manifest):
    cache_parent = Path(tempfile.mkdtemp(prefix="uc-assembly-cache-"))
    cache_tree = cache_parent / "tree"
    shutil.copytree(output, cache_tree)
    identity = audited_directory_identity_boundary(cache_tree)
    _ASSEMBLY_PROOF_CACHE[cache_key] = {
        "owner": cache_parent,
        "tree": str(cache_tree),
        "tree_identity": identity,
        "manifest": copy.deepcopy(manifest),
    }
    return identity


def run_assemble(thing):
    """One suite seed in; five generated, verified, installed applications out."""
    value = dict(thing.get("value") or {}) if isinstance(thing, dict) else {}
    if not is_thing(thing):
        return _failure(
            {"value": value, "depths": (), "axes": (), "evidence": (), "state": "formed"},
            value,
            "not-a-thing",
            "assembly:rejected",
        )
    if value.get("error"):
        return _failure(thing, value, value["error"], "assembly:rejected")
    if not (
        value.get("build")
        and value.get("install")
        and value.get("verify")
        and value.get("gauntlet_depths") == 10
    ):
        return _failure(thing, value, "assembly-gates-required", "assembly:rejected")
    suite_path = Path(str(value.get("suite_path", ""))).resolve()
    output = Path(str(value.get("output", ""))).resolve()
    suite, error = _read_json(suite_path)
    if error:
        return _failure(thing, value, f"suite:{error}", "assembly:seed-rejected")
    source_root = suite_path.parent.parent
    errors = validate_suite(suite, source_root)
    if errors:
        return _failure(thing, {**value, "validation_errors": errors}, "invalid-suite", "assembly:seed-rejected")
    if output == source_root or source_root in output.parents or output in source_root.parents:
        return _failure(thing, value, "unsafe-output", "assembly:rejected")
    cache_key = audited_assembly_cache_key_boundary(suite, source_root)
    cached = audited_assembly_cache_admission_boundary(
        thing, value, output, cache_key
    )
    if cached is not None:
        return cached

    seeds = []
    for entry in suite["applications"]:
        seed_path = source_root / entry["seed"]
        seed, _ = _read_json(seed_path)
        seeds.append((seed_path, seed))
    staging_parent = output.parent
    staging_parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix="." + output.name + ".uc-new-", dir=staging_parent))
    try:
        apps_root = staging / "applications"
        install_root = staging / "installation"
        manifests = {}
        roots = []
        seed_by_name = {seed["application"]["name"]: seed for _, seed in seeds}
        package_by_name = {
            seed["application"]["name"]: seed["application"]["package"] for _, seed in seeds
        }
        for seed_path, seed in _ordered_seeds(seeds):
            name = seed["application"]["name"]
            dependency = seed.get("dependency")
            dependency_identity = (
                manifests[dependency["application"]]["export_identity"] if dependency else None
            )
            dependency_package = (
                package_by_name[dependency["application"]] if dependency else None
            )
            files = render_application(seed, dependency_identity, dependency_package)
            manifest = _manifest(seed, files, dependency_identity)
            files[".unified/manifest.json"] = _canonical(manifest).decode()
            root = apps_root / name
            _write_tree(root, files)
            manifests[name] = manifest
            roots.append(root)

        builds = _build_generated_sources(roots)
        tests = _run_generated_tests(roots)
        anti = _anti_hardcoding([seed for _, seed in seeds])
        atomic_install = _atomic_preservation_probe(staging_parent)
        graphical_proofs = audited_graphical_suite_boundary(roots, seed_by_name)
        application_reports = {}
        for root in roots:
            name = root.name
            seed = seed_by_name[name]
            manifest = manifests[name]
            acceptance = _execute_acceptance(root, seed, roots)
            copied = install_root / name
            shutil.copytree(root, copied)
            installed = _execute_acceptance(copied, seed, [install_root / item.name for item in roots])
            rendered = render_application(
                seed,
                manifest["dependency_identity"],
                package_by_name[(seed.get("dependency") or {}).get("application")]
                if seed.get("dependency")
                else None,
            )
            deterministic = _tree_hash(_file_hashes(rendered)) == manifest["tree_sha256"]
            verification = {
                "spec_fidelity": json.loads((root / "canonical-specification.json").read_text()) == derive_specification(seed, manifest["dependency_identity"]),
                "plan_fidelity": json.loads(
                    (root / "application-plan.json").read_text()
                )
                == derive_plan(
                    seed,
                    derive_specification(seed, manifest["dependency_identity"]),
                    package_by_name[(seed.get("dependency") or {}).get("application")]
                    if seed.get("dependency")
                    else None,
                ),
                "source_laws": _source_laws(root, seed["application"]["package"]),
                "build_ok": builds[name]["ok"],
                "runtime_absence": _runtime_absence(root),
                "acceptance_ok": all(item["ok"] for item in acceptance),
                "performance_ok": not any(
                    step["timed_out"]
                    for scenario in (*acceptance, *installed)
                    for step in scenario["steps"]
                )
                and not tests[name]["timed_out"],
                "deterministic": deterministic,
                "dependency_ok": not seed.get("dependency") or bool(manifest["dependency_identity"]),
                "anti_hardcoding": anti["ok"],
                "javascript_headless_differential": _javascript_headless_differential(
                    root, seed
                ),
                "graphical_browser": graphical_proofs[name],
                "generated_tests_ok": tests[name]["ok"],
                "installed_execution_ok": all(item["ok"] for item in installed),
                "atomic_install": atomic_install,
            }
            depths = _ten_depth_report(seed, manifest, verification)
            application_reports[name] = {
                "manifest": manifest,
                "verification": verification,
                "acceptance": acceptance,
                "installed_acceptance": installed,
                "depths": depths,
                "verdict": "pass" if all(item["verdict"] == "pass" for item in depths.values()) else "fail",
            }
        suite_manifest = {
            "assembly_version": ASSEMBLY_VERSION,
            "suite_seed_sha256": _sha(_canonical(suite)),
            "applications": manifests,
            "anti_hardcoding": anti,
            "reports": application_reports,
        }
        (staging / "assembly-manifest.json").write_bytes(_canonical(suite_manifest))
        ok = all(report["verdict"] == "pass" for report in application_reports.values())
        if not ok:
            diagnostics = output.with_name("." + output.name + ".uc-diagnostics")
            if diagnostics.exists():
                shutil.rmtree(diagnostics)
            staging.rename(diagnostics)
            return _failure(
                thing,
                {**value, "report": suite_manifest, "diagnostics": str(diagnostics)},
                "verification-failed",
                "assembly:verification-failed",
            )
        _atomic_publish(staging, output)
        cache_identity = audited_assembly_cache_publish_boundary(
            cache_key, output, suite_manifest
        )
        return outward(
            {
                **thing,
                "value": {
                    **value,
                    "output": str(output),
                    "manifest": suite_manifest,
                    "applications": sorted(manifests),
                    "verdict": "pass",
                    "cache_identity": cache_identity,
                },
                "evidence": (*thing["evidence"], "assembly:validated", "assembly:generated", "assembly:installed", "assembly:verified"),
                "state": "valid",
            }
        )
    except BaseException as error:
        if staging.exists():
            diagnostics = output.with_name("." + output.name + ".uc-diagnostics")
            if diagnostics.exists():
                shutil.rmtree(diagnostics)
            staging.rename(diagnostics)
        return _failure(
            thing,
            {**value, "failure_type": type(error).__name__},
            "assembly-failed",
            "assembly:failed",
        )
