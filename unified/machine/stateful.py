"""Generic seed-declared state transition semantics for the Python UEM host."""

from __future__ import annotations

import copy


SCALAR_INTEGER_MAX = 999_999_999_999_999
SCALAR_INTEGER_MIN = -SCALAR_INTEGER_MAX
ASCII_WHITESPACE = frozenset(" \t\n\v\f\r")


def _canonical_integer(raw):
    if not isinstance(raw, str) or not raw:
        return None
    negative = raw.startswith("-")
    digits = raw[1:] if negative else raw
    if not digits or len(digits) > 16:
        return None
    if (len(digits) > 1 and digits[0] == "0") or any(
        digit not in "0123456789" for digit in digits
    ):
        return None
    magnitude = int(digits)
    if magnitude > SCALAR_INTEGER_MAX:
        return None
    return -magnitude if negative else magnitude


def _ascii_whitespace_only(value):
    return not value or all(character in ASCII_WHITESPACE for character in value)


def _path(root, path):
    current = root
    for key in path:
        current = current[key]
    return current


def _value(spec, context):
    if isinstance(spec, dict) and set(spec) == {"$arg"}:
        return copy.deepcopy(context["arguments"][spec["$arg"]])
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
        parsed = _canonical_integer(raw)
    else:
        parsed = None
    if parsed is None:
        return None, rule.get("error", "invalid-argument")
    if (
        rule.get("non_empty")
        and isinstance(parsed, str)
        and _ascii_whitespace_only(parsed)
    ):
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
    rows = _path(context["state"], rule["path"])
    matches = [row for row in rows if _matches(row, rule["where"], context)]
    if rule["kind"] == "unique":
        return rule.get("error") if matches else None
    if rule["kind"] == "require":
        if not matches:
            return rule.get("error")
        context["selected"][rule["as"]] = matches[0]
        return None
    return "invalid-guard"


def _action(rule, context):
    if rule["kind"] == "append":
        _path(context["state"], rule["path"]).append(_value(rule["value"], context))
        return True
    target = context["selected"][rule["target"]]
    if rule["kind"] == "set":
        for field, spec in rule["values"].items():
            target[field] = _value(spec, context)
        return True
    if rule["kind"] == "increment":
        for field, spec in rule["values"].items():
            target[field] = target.get(field, 0) + _value(spec, context)
        return True
    return False


def transition(config, host):
    """Execute one raw command against one state and return a canonical envelope."""
    original = copy.deepcopy(host.get("resource_state") or {})
    command = config.get("commands", {}).get(host.get("command"))
    if command is None:
        return _failure(original, "unknown-command")
    raw_arguments = tuple(host.get("arguments") or ())
    rules = tuple(command.get("arguments") or ())
    if len(raw_arguments) != len(rules):
        return _failure(original, "invalid-arity")
    arguments = {}
    for raw, rule in zip(raw_arguments, rules):
        parsed, error = _argument(raw, rule)
        if error is not None:
            return _failure(original, error)
        arguments[rule["name"]] = parsed
    state = copy.deepcopy(original)
    context = {"arguments": arguments, "selected": {}, "state": state}
    for rule in command.get("guards") or ():
        error = _guard(rule, context)
        if error is not None:
            return _failure(original, error)
    changed = False
    for rule in command.get("actions") or ():
        changed = _action(rule, context) or changed
    return {
        "resource_state": state,
        "result": _value(command["result"], context),
        "state_changed": changed,
        "error": None,
    }


def _failure(state, error):
    return {
        "resource_state": copy.deepcopy(state),
        "result": None,
        "state_changed": False,
        "error": error,
    }
