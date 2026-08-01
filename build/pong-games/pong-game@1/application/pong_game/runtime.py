"""Generated audited application capability runtime."""

import hashlib
import json
import os
import re
from pathlib import Path

from .specification import SPECIFICATION

LIBRARY_IDENTITY = None
dependency_invoke = None

STATES = frozenset(("unknown", "absent", "false", "formed", "valid", "invalid"))


def ticket_payload(error_type):
    identity = hashlib.sha256(("application-v3:" + error_type).encode("utf-8")).hexdigest()
    return {
        "ticket_id": identity,
        "correlation_id": identity,
        "message": "[redacted-message]",
        "error_type": error_type,
    }


def invalid(thing, error, mark):
    value = dict(thing.get("value") or {})
    return {**thing, "value": {**value, "error": error}, "evidence": (*thing.get("evidence", ()), mark), "state": "invalid"}


def inward(thing):
    valid = (
        isinstance(thing, dict)
        and isinstance(thing.get("value"), dict)
        and isinstance(thing.get("depths"), tuple)
        and isinstance(thing.get("axes"), tuple)
        and isinstance(thing.get("evidence"), tuple)
        and thing.get("state") in STATES
    )
    return {**thing, "evidence": (*thing["evidence"], "boundary:inward")} if valid else {
        "value": {"error": "not-a-thing"}, "depths": (), "axes": (),
        "evidence": ("boundary:inward:error",), "state": "invalid",
    }


def outward(thing):
    return {
        **thing,
        "evidence": (*thing.get("evidence", ()), "boundary:outward"),
        "state": "valid" if thing.get("state") == "formed" else thing.get("state"),
    }


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
    return {"operation": request["operation"], "result": result}


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
        return {
            "content": content, "encoding": encoding, "empty": not raw,
            "size": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
        }
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
    return {"content": changed, "saved": saved}


def _tokenize(text):
    compact = re.sub(r"\s+", "", text)
    tokens = re.findall(r"\d+|[()+*/%^-]", compact)
    if "".join(tokens) != compact:
        raise ValueError("invalid-token")
    return tokens


def _expression(spec, request):
    if LIBRARY_IDENTITY != None:
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
            values.append(dependency_invoke({"operation": aliases[symbol], "arguments": [value]})["result"])
            return
        right, left = values.pop(), values.pop()
        values.append(dependency_invoke({"operation": aliases[symbol], "arguments": [left, right]})["result"])

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
    return {"result": values[0]}


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
    temporary.write_text(json.dumps(state, separators=(",", ":"), sort_keys=True) + "\n")
    os.replace(temporary, state_path)
    return state


def _process(thing):
    value = thing.get("value") or {}
    request = value.get("outer_input")
    host = value.get("host") or {}
    if not isinstance(request, dict):
        return invalid(thing, "invalid-input", "stage:04_core_processing:error")
    program = SPECIFICATION["program"]
    try:
        handlers = {
            "document": _document,
            "numeric": lambda spec, item, edge: _numeric(spec, item),
            "expression": lambda spec, item, edge: _expression(spec, item),
            "world": _world,
        }
        output = handlers[program["engine"]](program, request, host)
    except (KeyError, OSError, TypeError, ValueError) as error:
        return invalid(thing, str(error), "stage:04_core_processing:error")
    return {**thing, "value": {**value, "_core_output": output}}


def advance(thing):
    if thing.get("state") != "formed":
        return thing
    specialization = (thing.get("value") or {}).get("_specialization") or {}
    index = specialization["index"]
    current = _process(thing) if index == 4 else thing
    if current.get("state") != "formed":
        return current
    value = dict(current.get("value") or {})
    if index == 7:
        value["outer_output"] = value.get("_core_output")
    value.pop("_specialization", None)
    return {**current, "value": value, "evidence": (*current["evidence"], "stage:" + specialization["name"])}
