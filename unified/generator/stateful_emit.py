"""Render application-neutral persistent state machines from declarations."""

from __future__ import annotations

import json


def _canonical(value):
    if isinstance(value, dict):
        return {key: _canonical(value[key]) for key in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [_canonical(item) for item in value]
    return value


def is_stateful_resource(declaration: dict) -> bool:
    return any(
        isinstance(feature.get("transformation"), dict)
        and feature["transformation"].get("kind") == "stateful_resource"
        for feature in declaration.get("features") or ()
        if isinstance(feature, dict)
    )


def render_stateful_files(declaration: dict, boundary_base: str) -> dict[str, str]:
    package = declaration["package"]
    feature = next(
        item
        for item in declaration["features"]
        if item["transformation"].get("kind") == "stateful_resource"
    )
    config = _canonical(dict(feature["transformation"]))
    config.pop("kind", None)
    _validate_config(config)
    feature_name = feature["name"]
    script = (declaration.get("cli") or {}).get("script", declaration["name"])
    acceptance = {
        "script": script,
        "package": package,
        "commands": config["acceptance"],
    }
    return {
        f"{package}/boundary.py": _boundary(boundary_base, config),
        f"{package}/parts.py": _parts(feature_name, repr(config)),
        f"{package}/compose.py": _compose(feature_name, declaration["composition"]),
        f"{package}/state_runtime.py": _state_runtime(),
        f"{package}/cli.py": _cli(package),
        f"{package}/core.py": _core(),
        "tests/test_stateful.py": _tests(package, config),
        ".uc/acceptance.json": json.dumps(
            acceptance, ensure_ascii=False, indent=2, sort_keys=True
        )
        + "\n",
        "README.md": _readme(declaration, script, config),
    }


def _validate_config(config: dict) -> None:
    required = (
        "acceptance",
        "commands",
        "failure_probe",
        "persistence",
        "rejections",
        "state",
    )
    missing = tuple(key for key in required if key not in config)
    if missing:
        raise ValueError(f"stateful declaration missing: {missing!r}")
    if not isinstance(config["commands"], dict) or not config["commands"]:
        raise ValueError("stateful commands must be a non-empty map")
    persistence = config["persistence"]
    if not isinstance(persistence, dict):
        raise ValueError("stateful persistence must be a map")
    for key in ("environment", "default_path"):
        if not isinstance(persistence.get(key), str) or not persistence[key]:
            raise ValueError(f"stateful persistence.{key} must be text")
    state = config["state"]
    if not isinstance(state, dict) or not isinstance(state.get("initial"), dict):
        raise ValueError("stateful state.initial must be a map")
    for name, command in config["commands"].items():
        if not isinstance(name, str) or not name:
            raise ValueError("stateful command names must be text")
        if not isinstance(command, dict):
            raise ValueError(f"stateful command {name!r} must be a map")
        if not isinstance(command.get("arguments", []), list):
            raise ValueError(f"stateful command {name!r} arguments must be a sequence")
        if not isinstance(command.get("guards", []), list):
            raise ValueError(f"stateful command {name!r} guards must be a sequence")
        if not isinstance(command.get("actions", []), list):
            raise ValueError(f"stateful command {name!r} actions must be a sequence")
        if "result" not in command:
            raise ValueError(f"stateful command {name!r} missing result")


def _parts(feature_name: str, config_literal: str) -> str:
    return f'''"""Generated domain part. Thing→Thing; no explicit control flow."""


def {feature_name}(thing):
    """Apply one seed-declared transition through the audited primitive."""
    from .state_runtime import apply_stateful_resource
    return apply_stateful_resource(thing, {config_literal}, {feature_name!r})
'''


def _compose(feature_name: str, composition) -> str:
    names = tuple(composition)
    known = {
        "inward": ("boundary", "inward"),
        "parse_host_argv": ("boundary", "parse_host_argv"),
        "load_state": ("boundary", "load_state"),
        feature_name: ("parts", feature_name),
        "persist_state": ("boundary", "persist_state"),
        "verify": ("core", "verify"),
        "present_result": ("boundary", "present_result"),
        "outward": ("boundary", "outward"),
    }
    unknown = tuple(name for name in names if name not in known)
    if unknown:
        raise ValueError(f"stateful composition has unsupported parts: {unknown!r}")
    imports = []
    for module in ("boundary", "core", "parts"):
        members = tuple(
            symbol for name, (owner, symbol) in known.items() if owner == module and name in names
        )
        if members:
            imports.append(f"from .{module} import {', '.join(members)}")
    routes = []
    route_pairs = []
    for index, name in enumerate(names):
        event = "program.start" if index == 0 else f"flow.{index}"
        next_event = "program.done" if index + 1 == len(names) else f"flow.{index + 1}"
        routes.append(
            f"def route_{index}(thing):\n"
            f"    return call_part(thing, {known[name][1]}, {next_event!r})\n"
        )
        route_pairs.append(f"    {event!r}: route_{index},")
    return f'''"""Generated event composition. The seed-declared order is authoritative."""

{chr(10).join(imports)}
from .event_runtime import (
    ack_ticket,
    call_part,
    construct_ticket,
    emit,
    emergency_persist_result,
    enqueue,
    fail_with_ticket,
    outward_ticket_store,
    preserve_for_retry,
    until_quiet,
)


{chr(10).join(routes)}
def failed(thing):
    return enqueue(emit(outward(thing), "program.done"), "program.done")


def done(thing):
    return emit(thing, "program.done")


ROUTES = {{
{chr(10).join(route_pairs)}
    "validation.failed": done,
    "exception.unhandled": construct_ticket,
    "ticket.persist.requested": outward_ticket_store,
    "ticket.persisted": fail_with_ticket,
    "ticket.persist.failed": emergency_persist_result,
    "ticket.delivery_failed": preserve_for_retry,
    "ticket.ack_requested": ack_ticket,
    "processing.failed": failed,
    "program.done": done,
}}


def program(thing):
    seeded = enqueue(emit(thing, "program.start"), "program.start")
    return until_quiet(seeded, ROUTES)
'''


def _boundary(boundary_base: str, config: dict) -> str:
    initial = config["state"]["initial"]
    schema = config["state"].get("schema", [])
    persistence = config["persistence"]
    arity = {
        name: len(command.get("arguments") or ())
        for name, command in config["commands"].items()
    }
    return boundary_base + f'''


STATE_INITIAL = {initial!r}
STATE_SCHEMA = {schema!r}
COMMAND_ARITY = {arity!r}
PERSISTENCE = {persistence!r}


def parse_host_argv(thing):
    """INWARD host grammar boundary for one declared command."""
    import os

    if not is_thing(thing):
        return inward(thing)
    raw = thing["value"]
    argv = raw.get("argv") if isinstance(raw, dict) else raw
    if not isinstance(argv, (list, tuple)):
        return {{**thing, "value": {{"error": "invalid-argv"}}, "state": "invalid"}}
    args = list(argv)
    state_path = os.environ.get(PERSISTENCE["environment"], PERSISTENCE["default_path"])
    if len(args) >= 2 and args[0] == "--state":
        state_path = args[1]
        args = args[2:]
    if not args:
        return {{
            **thing,
            "value": {{"error": "missing-command", "state_path": state_path}},
            "evidence": (*thing["evidence"], "boundary:parse", "parse:missing-command"),
            "state": "invalid",
        }}
    command = args[0]
    supplied = args[1:]
    arity = COMMAND_ARITY.get(command)
    if arity is None:
        return {{
            **thing,
            "value": {{"error": "unknown-command", "command": command, "state_path": state_path}},
            "evidence": (*thing["evidence"], "boundary:parse", "parse:unknown-command"),
            "state": "invalid",
        }}
    if len(supplied) != arity:
        return {{
            **thing,
            "value": {{"error": "invalid-arity", "command": command, "state_path": state_path}},
            "evidence": (*thing["evidence"], "boundary:parse", "parse:invalid-arity"),
            "state": "invalid",
        }}
    state = Path(state_path).expanduser().resolve()
    return {{
        **thing,
        "value": {{
            "command": command,
            "arguments": supplied,
            "state_path": str(state),
            "ticket_outbox": str(state.parent / ".uc-tickets"),
        }},
        "evidence": (*thing["evidence"], "boundary:parse", "parse:ok"),
        "state": "formed",
    }}


def _path_value(root, path):
    current = root
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def _valid_state(value):
    if not isinstance(value, dict):
        return False
    type_map = {{
        "array": list,
        "object": dict,
        "string": str,
        "integer": int,
        "boolean": bool,
    }}
    for entry in STATE_SCHEMA:
        expected = type_map.get(entry.get("type"))
        actual = _path_value(value, entry.get("path") or ())
        if expected is None or not isinstance(actual, expected):
            return False
    return True


def load_state(thing):
    """OUTWARD read boundary. Missing storage is the declared initial state."""
    import copy
    import json

    if thing.get("state") in {{"invalid", "absent", "false"}}:
        return {{**thing, "evidence": (*thing["evidence"], "boundary:outward:state.read", "state.read:skipped")}}
    value = dict(thing["value"])
    path = Path(value["state_path"])
    if path.exists():
        state_data = json.loads(path.read_text(encoding="utf-8"))
    else:
        state_data = copy.deepcopy(STATE_INITIAL)
    if not _valid_state(state_data):
        return {{
            **thing,
            "value": {{**value, "error": "invalid-state"}},
            "evidence": (*thing["evidence"], "boundary:outward:state.read", "state.read:invalid"),
            "state": "invalid",
        }}
    return {{
        **thing,
        "value": {{**value, "resource_state": state_data}},
        "evidence": (*thing["evidence"], "boundary:outward:state.read", "state.read:ok"),
        "state": "formed",
    }}


def persist_state(thing):
    """OUTWARD atomic write boundary; validation failures never write."""
    import json
    import os

    if thing.get("state") != "formed":
        return {{**thing, "evidence": (*thing["evidence"], "boundary:outward:state.write", "state.write:skipped")}}
    value = dict(thing["value"])
    if not value.get("state_changed"):
        return {{**thing, "evidence": (*thing["evidence"], "boundary:outward:state.write", "state.write:unchanged")}}
    path = Path(value["state_path"])
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name("." + path.name + ".uc-tmp")
    payload = json.dumps(value["resource_state"], ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\\n"
    with temporary.open("w", encoding="utf-8") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    return {{
        **thing,
        "evidence": (*thing["evidence"], "boundary:outward:state.write", "state.write:ok"),
        "state": "formed",
    }}


def present_result(thing):
    """Canonical JSON presentation boundary."""
    import json

    value = dict(thing.get("value") or {{}})
    if thing.get("state") == "valid" and "result" in value:
        payload = value["result"]
        code = 0
    else:
        payload = {{"error": value.get("error", "invalid"), "state": thing.get("state", "invalid")}}
        code = 1
    value["presentation"] = {{
        "text": json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True),
        "exit_code": code,
    }}
    return {{
        **thing,
        "value": value,
        "evidence": (*thing.get("evidence", ()), "boundary:present"),
    }}
'''


def _state_runtime() -> str:
    return '''"""Audited generic transition-expression primitive.

This module is pure: no filesystem, environment, stdout, or ticket I/O.
"""

import copy


def _path(root, path):
    current = root
    for key in path:
        current = current[key]
    return current


def _value(spec, context):
    if isinstance(spec, dict) and set(spec) == {"$arg"}:
        return context["arguments"][spec["$arg"]]
    if isinstance(spec, dict) and set(spec) == {"$literal"}:
        return copy.deepcopy(spec["$literal"])
    if isinstance(spec, dict) and set(spec) == {"$state"}:
        return copy.deepcopy(_path(context["state"], spec["$state"]))
    if isinstance(spec, dict) and set(spec) == {"$selected"}:
        selected = context["selected"][spec["$selected"]["name"]]
        return copy.deepcopy(selected.get(spec["$selected"]["field"]))
    if isinstance(spec, dict) and set(spec) == {"$project"}:
        node = spec["$project"]
        rows = _path(context["state"], node["path"])
        return [
            {field: copy.deepcopy(row.get(field)) for field in node["fields"]}
            for row in rows
        ]
    if isinstance(spec, dict):
        return {key: _value(value, context) for key, value in spec.items()}
    if isinstance(spec, list):
        return [_value(item, context) for item in spec]
    return copy.deepcopy(spec)


def _argument(raw, rule):
    kind = rule.get("type", "string")
    if kind == "string":
        parsed = raw if isinstance(raw, str) else None
    elif kind == "integer":
        try:
            parsed = int(raw)
        except (TypeError, ValueError):
            parsed = None
    else:
        parsed = None
    if parsed is None:
        return None, rule.get("error", "invalid-argument")
    if rule.get("non_empty") and isinstance(parsed, str) and not parsed.strip():
        return None, rule.get("error", "invalid-argument")
    if "minimum" in rule and parsed < rule["minimum"]:
        return None, rule.get("error", "invalid-argument")
    return parsed, None


def _matches(row, where, context):
    return all(
        row.get(clause["field"]) == _value(clause["equals"], context)
        for clause in where
    )


def _guard(rule, context):
    kind = rule["kind"]
    rows = _path(context["state"], rule["path"])
    matches = [row for row in rows if _matches(row, rule["where"], context)]
    if kind == "unique":
        return rule.get("error") if matches else None
    if kind == "require":
        if not matches:
            return rule.get("error")
        context["selected"][rule["as"]] = matches[0]
        return None
    return "invalid-guard"


def _action(rule, context):
    kind = rule["kind"]
    if kind == "append":
        _path(context["state"], rule["path"]).append(_value(rule["value"], context))
        return True
    target = context["selected"][rule["target"]]
    if kind == "set":
        for field, spec in rule["values"].items():
            target[field] = _value(spec, context)
        return True
    if kind == "increment":
        for field, spec in rule["values"].items():
            target[field] = target.get(field, 0) + _value(spec, context)
        return True
    return False


def apply_stateful_resource(thing, config, part_name):
    value = dict(thing.get("value") or {})
    evidence = (*tuple(thing.get("evidence") or ()), f"part:{part_name}")
    if thing.get("state") != "formed":
        return {**thing, "evidence": (*evidence, f"{part_name}:skipped")}
    command = config["commands"].get(value.get("command"))
    if command is None:
        return {
            **thing,
            "value": {**value, "error": "unknown-command"},
            "evidence": (*evidence, f"{part_name}:validation-failed"),
            "state": "invalid",
        }
    raw_arguments = tuple(value.get("arguments") or ())
    arguments = {}
    for raw, rule in zip(raw_arguments, command.get("arguments") or ()):
        parsed, error = _argument(raw, rule)
        if error is not None:
            return {
                **thing,
                "value": {**value, "error": error},
                "evidence": (*evidence, f"{part_name}:validation-failed"),
                "state": "invalid",
            }
        arguments[rule["name"]] = parsed
    state = copy.deepcopy(value.get("resource_state") or {})
    context = {"arguments": arguments, "selected": {}, "state": state}
    for rule in command.get("guards") or ():
        error = _guard(rule, context)
        if error is not None:
            return {
                **thing,
                "value": {**value, "error": error},
                "evidence": (*evidence, f"{part_name}:validation-failed"),
                "state": "invalid",
            }
    changed = False
    for rule in command.get("actions") or ():
        changed = _action(rule, context) or changed
    result = _value(command["result"], context)
    return {
        **thing,
        "value": {
            **value,
            "resource_state": state,
            "result": result,
            "state_changed": changed,
        },
        "evidence": (*evidence, f"{part_name}:ok"),
        "state": "formed",
    }
'''


def _core() -> str:
    return '''"""Generated verification part."""

from .boundary import is_thing


def letter(thing):
    value = thing.get("value")
    if value is None:
        state, mark = "absent", "letter:absent"
    elif value is False:
        state, mark = "false", "letter:false"
    else:
        state, mark = "formed", "letter:distinguished"
    return {
        **thing,
        "evidence": (*thing.get("evidence", ()), mark),
        "state": state,
    }


def verify(thing):
    if not is_thing(thing):
        return {
            "value": thing,
            "depths": (),
            "axes": (),
            "evidence": ("verify:rejected-non-thing",),
            "state": "invalid",
        }
    ok = thing["state"] == "formed" and isinstance(thing.get("value"), dict) and "result" in thing["value"]
    return {
        **thing,
        "evidence": (*thing["evidence"], f"script-law:{'pass' if ok else 'fail'}"),
        "state": "valid" if ok else thing["state"],
    }
'''


def _cli(package: str) -> str:
    return f'''"""Generated process edge."""

from __future__ import annotations

import sys

from .compose import program


def host_main(argv=None):
    explicit = argv is not None
    args = list(sys.argv[1:] if argv is None else argv)
    result = program({{"argv": args}})
    value = result.get("value") if isinstance(result, dict) else {{}}
    presentation = value.get("presentation") if isinstance(value, dict) else None
    text = presentation.get("text", '{{"error":"missing-presentation","state":"invalid"}}') if isinstance(presentation, dict) else '{{"error":"missing-presentation","state":"invalid"}}'
    code = int(presentation.get("exit_code", 1)) if isinstance(presentation, dict) else 1
    sys.stdout.write(str(text) + ("" if str(text).endswith("\\n") else "\\n"))
    if explicit:
        return code
    raise SystemExit(code)


if __name__ == "__main__":
    host_main()
'''


def _tests(package: str, config: dict) -> str:
    return f'''"""Generated stateful acceptance, failure, and source-law tests."""

from __future__ import annotations

import ast
import json
from pathlib import Path

from {package}.cli import host_main
from {package}.compose import program


ACCEPTANCE = {config["acceptance"]!r}
REJECTIONS = {config["rejections"]!r}
EXPECT_STATE = {config["state"].get("expect")!r}
FAILURE_PROBE = {config["failure_probe"]!r}


def _invoke(state, argv, capsys):
    code = host_main(["--state", str(state), *argv])
    text = capsys.readouterr().out.strip()
    return code, json.loads(text)


def test_complete_stateful_proof_and_restart(tmp_path, capsys):
    state = tmp_path / "state.json"
    outputs = []
    rejected = False
    for case in ACCEPTANCE:
        before = state.read_bytes() if state.exists() else None
        code, payload = _invoke(state, case["argv"], capsys)
        assert code == case.get("exit", 0)
        assert payload == case["expect"]
        if code != 0:
            after = state.read_bytes() if state.exists() else None
            assert after == before
            assert not (tmp_path / ".uc-tickets").exists()
            rejected = True
        elif rejected:
            rejected = False
        outputs.append(payload)
    assert rejected is False
    assert json.loads(state.read_text(encoding="utf-8")) == EXPECT_STATE
    assert outputs[-1] == outputs[-2]


def test_declared_validation_failures_create_no_ticket_or_state(tmp_path, capsys):
    for index, case in enumerate(REJECTIONS):
        root = tmp_path / str(index)
        state = root / "state.json"
        code, payload = _invoke(state, case["argv"], capsys)
        assert code == case.get("exit", 1)
        assert payload == case["expect"]
        assert not state.exists()
        assert not (root / ".uc-tickets").exists()


def test_unhandled_failure_is_redacted_and_deduplicated(tmp_path, monkeypatch):
    from {package} import state_runtime

    state = tmp_path / "state.json"

    def explode(*_args):
        raise RuntimeError("token=super-secret")

    monkeypatch.setattr(state_runtime, "apply_stateful_resource", explode)
    first = program({{"argv": ["--state", str(state), *FAILURE_PROBE]}})
    second = program({{"argv": ["--state", str(state), *FAILURE_PROBE]}})
    assert first["state"] == second["state"] == "invalid"
    tickets = list((tmp_path / ".uc-tickets").glob("*.json"))
    assert len(tickets) == 1
    text = tickets[0].read_text(encoding="utf-8")
    assert "super-secret" not in text
    assert "[redacted-message]" in text


def test_domain_and_composition_have_no_explicit_control_flow():
    root = Path(__file__).resolve().parents[1] / {package!r}
    for name in ("parts.py", "compose.py"):
        tree = ast.parse((root / name).read_text(encoding="utf-8"))
        forbidden = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.Match, ast.IfExp)
        assert not any(isinstance(node, forbidden) for node in ast.walk(tree))
'''


def _readme(declaration: dict, script: str, config: dict) -> str:
    examples = "\n".join(
        f"{script} --state state.json " + " ".join(case["argv"])
        for case in config["acceptance"]
    )
    return f'''# {declaration["name"]}

{declaration.get("description", "Generated persistent application")}

This application, its tests, routing, persistence identity, transition rules,
and acceptance sequence are generated from the JSON seed.

```bash
{examples}
```
'''
