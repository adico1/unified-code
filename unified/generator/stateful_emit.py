"""Render the generic stateful-resource application profile.

The application declaration supplies command names, field names, defaults, and
acceptance cases.  Generated domain/composition modules only connect audited
primitives; selection, iteration, and filesystem effects live in the generated
runtime and OUTWARD boundary modules respectively.
"""

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
        feature
        for feature in declaration["features"]
        if feature["transformation"].get("kind") == "stateful_resource"
    )
    config = dict(feature["transformation"])
    config.pop("kind", None)
    config = _canonical(config)
    config_literal = repr(config)
    feature_name = feature["name"]
    script = (declaration.get("cli") or {}).get("script", declaration["name"])
    acceptance = {
        "script": script,
        "package": package,
        "commands": list(config.get("acceptance") or ()),
    }
    return {
        f"{package}/boundary.py": _boundary(boundary_base, config),
        f"{package}/parts.py": _parts(feature_name, config_literal),
        f"{package}/compose.py": _compose(feature_name),
        f"{package}/state_runtime.py": _state_runtime(),
        f"{package}/cli.py": _cli(package),
        f"{package}/core.py": _core(),
        "tests/test_stateful.py": _tests(package, feature_name, config),
        ".uc/acceptance.json": json.dumps(
            acceptance, ensure_ascii=False, indent=2, sort_keys=True
        )
        + "\n",
        "README.md": _readme(declaration, script),
    }


def _parts(feature_name: str, config_literal: str) -> str:
    return f'''"""Generated domain parts. Thing→Thing; no explicit control flow."""


def {feature_name}(thing):
    """Apply one declared state transition through the audited primitive."""
    from .state_runtime import apply_stateful_resource
    return apply_stateful_resource(thing, {config_literal}, {feature_name!r})
'''


def _compose(feature_name: str) -> str:
    return f'''"""Generated event composition. Routing is data; no explicit control flow."""

from .boundary import (
    inward,
    load_state,
    outward,
    parse_host_argv,
    persist_state,
    present_result,
)
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
from .parts import {feature_name}


def start(thing):
    return enqueue(emit(thing, "step.inward"), "step.inward")


def step_inward(thing):
    return call_part(thing, inward, "step.parse")


def step_parse(thing):
    return call_part(thing, parse_host_argv, "step.load")


def step_load(thing):
    return call_part(thing, load_state, "step.apply")


def step_apply(thing):
    return call_part(thing, {feature_name}, "step.persist")


def step_persist(thing):
    return call_part(thing, persist_state, "step.verify")


def step_verify(thing):
    from .core import verify
    return call_part(thing, verify, "step.present")


def step_present(thing):
    return call_part(thing, present_result, "step.outward")


def step_outward(thing):
    return call_part(thing, outward, "program.done")


def reject(thing):
    return enqueue(emit(thing, "program.done"), "program.done")


def failed(thing):
    return enqueue(emit(outward(thing), "program.done"), "program.done")


def done(thing):
    return emit(thing, "program.done")


ROUTES = {{
    "program.start": start,
    "step.inward": step_inward,
    "step.parse": step_parse,
    "step.load": step_load,
    "step.apply": step_apply,
    "step.persist": step_persist,
    "step.verify": step_verify,
    "step.present": step_present,
    "step.outward": step_outward,
    "validation.failed": reject,
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
    default_state = config.get("default_state", {"tasks": []})
    commands = config.get(
        "commands", {"add": 1, "complete": 1, "list": 0}
    )
    return boundary_base + f'''


STATE_DEFAULT = {default_state!r}
COMMAND_ARITY = {commands!r}


def parse_host_argv(thing):
    """INWARD host grammar boundary for one stateful command."""
    import os

    if not is_thing(thing):
        return inward(thing)
    raw = thing["value"]
    argv = raw.get("argv") if isinstance(raw, dict) else raw
    if not isinstance(argv, (list, tuple)):
        return {{**thing, "value": {{"error": "invalid-argv"}}, "state": "invalid"}}
    args = list(argv)
    state_path = os.environ.get("UC_TASK_LEDGER_STATE", ".uc-task-ledger.json")
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


def load_state(thing):
    """OUTWARD read boundary. Missing storage is the declared initial state."""
    import json

    if thing.get("state") in {{"invalid", "absent", "false"}}:
        return {{**thing, "evidence": (*thing["evidence"], "boundary:outward:state.read", "state.read:skipped")}}
    value = dict(thing["value"])
    path = Path(value["state_path"])
    if path.exists():
        state_data = json.loads(path.read_text(encoding="utf-8"))
    else:
        state_data = {default_state!r}
    if not isinstance(state_data, dict) or not isinstance(state_data.get("tasks"), list):
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
    """OUTWARD atomic write boundary; pure validation failures never write."""
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
    return '''"""Audited state-transition primitive.

Selection and iteration are centralized here and tested through generated
mutations.  It is pure: no filesystem, environment, stdout, or ticket I/O.
"""


def apply_stateful_resource(thing, config, part_name):
    value = dict(thing.get("value") or {})
    evidence = (*tuple(thing.get("evidence") or ()), f"part:{part_name}")
    if thing.get("state") != "formed":
        return {**thing, "evidence": (*evidence, f"{part_name}:skipped")}
    resource = dict(value.get("resource_state") or {})
    tasks = [dict(task) for task in resource.get("tasks") or ()]
    command = value.get("command")
    arguments = list(value.get("arguments") or ())
    result = None
    changed = False
    error = None
    if command == "add":
        title = arguments[0] if arguments else ""
        if not isinstance(title, str) or not title.strip():
            error = "invalid-title"
        elif any(task.get("title") == title for task in tasks):
            error = "duplicate-title"
        else:
            task = {"completed": False, "title": title}
            tasks.append(task)
            result = {"added": title, "completed": False}
            changed = True
    elif command == "complete":
        title = arguments[0] if arguments else ""
        selected = next(
            (task for task in tasks if task.get("title") == title and not task.get("completed")),
            None,
        )
        if selected is None:
            error = "task-not-open"
        else:
            selected["completed"] = True
            result = {"completed": title}
            changed = True
    elif command == "list":
        result = {"tasks": [{"completed": bool(task.get("completed")), "title": task.get("title")} for task in tasks]}
    else:
        error = "unknown-command"
    if error is not None:
        return {
            **thing,
            "value": {**value, "error": error},
            "evidence": (*evidence, f"{part_name}:validation-failed"),
            "state": "invalid",
        }
    resource["tasks"] = tasks
    return {
        **thing,
        "value": {
            **value,
            "resource_state": resource,
            "result": result,
            "state_changed": changed,
        },
        "evidence": (*evidence, f"{part_name}:ok"),
        "state": "formed",
    }
'''


def _core() -> str:
    return '''"""Generated verification Part."""

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


def _tests(package: str, feature_name: str, config: dict) -> str:
    acceptance = list(config.get("acceptance") or ())
    return f'''"""Generated stateful acceptance, failure, and source-law tests."""

from __future__ import annotations

import ast
import json
from pathlib import Path

from {package}.cli import host_main
from {package}.compose import program


ACCEPTANCE = {acceptance!r}


def _invoke(state, argv, capsys):
    code = host_main(["--state", str(state), *argv])
    text = capsys.readouterr().out.strip()
    return code, json.loads(text)


def test_complete_stateful_proof_and_restart(tmp_path, capsys):
    state = tmp_path / "ledger.json"
    outputs = []
    for case in ACCEPTANCE:
        code, payload = _invoke(state, case["argv"], capsys)
        assert code == case.get("exit", 0)
        assert payload == case["expect"]
        outputs.append(payload)
    assert json.loads(state.read_text(encoding="utf-8")) == {{
        "tasks": [
            {{"completed": True, "title": "A"}},
            {{"completed": False, "title": "B"}},
        ]
    }}
    assert outputs[-1] == outputs[-2]


def test_validation_failure_creates_no_ticket_or_state(tmp_path, capsys):
    state = tmp_path / "ledger.json"
    code, payload = _invoke(state, ["add", ""], capsys)
    assert code == 1
    assert payload["error"] == "invalid-title"
    assert not state.exists()
    assert not (tmp_path / ".uc-tickets").exists()


def test_unhandled_failure_is_redacted_and_deduplicated(tmp_path, monkeypatch):
    from {package} import state_runtime

    state = tmp_path / "ledger.json"

    def explode(*_args):
        raise RuntimeError("token=super-secret")

    monkeypatch.setattr(state_runtime, "apply_stateful_resource", explode)
    first = program({{"argv": ["--state", str(state), "list"]}})
    second = program({{"argv": ["--state", str(state), "list"]}})
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


def _readme(declaration: dict, script: str) -> str:
    return f'''# {declaration["name"]}

{declaration.get("description", "Generated stateful application")}

This application, its tests, routing, persistence boundaries, and acceptance
sequence are generated from the JSON seed.

```bash
{script} --state ledger.json add A
{script} --state ledger.json add B
{script} --state ledger.json list
{script} --state ledger.json complete A
{script} --state ledger.json list
```
'''
