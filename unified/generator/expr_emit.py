"""Emit domain-neutral expression runtime and feature bodies as Python source."""

from __future__ import annotations

import json
from typing import Any

from .expr import validate_expression


def emit_expr_runtime_module() -> str:
    """Self-contained evaluator for generated applications (no unified import).

    L8: no user-defined classes. Errors use ValueError with plain attributes.
    """
    return '''"""Generated expression runtime — domain-neutral. No Unified Code dependency.

L8: functions and plain data only — no user-defined classes.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_DOWN, ROUND_HALF_EVEN, ROUND_HALF_UP, ROUND_UP


_ROUNDING = {
    "ROUND_HALF_UP": ROUND_HALF_UP,
    "ROUND_DOWN": ROUND_DOWN,
    "ROUND_UP": ROUND_UP,
    "ROUND_HALF_EVEN": ROUND_HALF_EVEN,
}


def expr_fail(error, path=()):
    """Raise a structured expression failure without defining a custom class."""
    err = ValueError(error)
    err.uc_expr_error = error
    err.uc_expr_path = tuple(path)
    raise err


def is_expr_fail(exc):
    return isinstance(exc, ValueError) and getattr(exc, "uc_expr_error", None) is not None


def eval_expr(node, ctx):
    """Evaluate a plain expression node against context.

    ctx keys:
      root: document root
      item: current item (for sum_each), optional
      path: current error path prefix
      bindings: named precomputed values (CSE)
    """
    op = node["op"]
    path = list(ctx.get("path") or ())

    if op == "literal":
        return node["value"]

    if op == "ref":
        bindings = ctx.get("bindings") or {}
        name = node["name"]
        if name not in bindings:
            expr_fail("missing-binding", path + [name])
        return bindings[name]

    if op == "field":
        return _get_path(ctx, node["path"])

    if op == "object":
        out = {}
        for key, child in node["fields"].items():
            out[key] = eval_expr(child, ctx)
        return out

    if op == "count":
        value = eval_expr(node["of"], ctx)
        if value is None:
            return 0
        return len(value)

    if op == "require":
        value = eval_expr(node["of"], ctx)
        err_path = list(path) + list(node.get("path") or ())
        if value is None:
            expr_fail(node.get("error", "missing"), err_path)
        return value

    if op == "as_int":
        value = eval_expr(node["of"], ctx)
        err_path = list(path) + list(node.get("path") or ())
        if value is None:
            expr_fail(node.get("missing_error", "missing"), err_path)
        if isinstance(value, bool) or not isinstance(value, int):
            expr_fail(node.get("type_error", "invalid-integer"), err_path)
        return value

    if op == "as_decimal":
        # Strict: only decimal *strings* (and Decimal already formed by prior ops).
        # JSON integers/floats are rejected — declared money fields are strings.
        value = eval_expr(node["of"], ctx)
        err_path = list(path) + list(node.get("path") or ())
        if value is None:
            expr_fail(node.get("missing_error", "missing"), err_path)
        if isinstance(value, Decimal):
            return value
        if not isinstance(value, str):
            expr_fail(node.get("type_error", "not-decimal-string"), err_path)
        try:
            return Decimal(value)
        except InvalidOperation:
            expr_fail(node.get("type_error", "not-decimal-string"), err_path)

    if op == "min_value":
        value = eval_expr(node["of"], ctx)
        bound = _bound(node["bound"])
        err_path = list(path) + list(node.get("path") or ())
        if value < bound:
            expr_fail(node.get("error", "below-minimum"), err_path)
        return value

    if op == "max_value":
        value = eval_expr(node["of"], ctx)
        bound = _bound(node["bound"])
        err_path = list(path) + list(node.get("path") or ())
        if value > bound:
            expr_fail(node.get("error", "above-maximum"), err_path)
        return value

    if op == "mul":
        total = Decimal(1)
        for child in node["values"]:
            part = eval_expr(child, ctx)
            if not isinstance(part, Decimal):
                part = Decimal(part)
            total *= part
        return total

    if op == "add":
        total = Decimal(0)
        for child in node["values"]:
            part = eval_expr(child, ctx)
            if not isinstance(part, Decimal):
                part = Decimal(part)
            total += part
        return total

    if op == "sum_each":
        collection = eval_expr(node["collection"], ctx)
        coll_path = list(node.get("path") or path) or ["items"]
        if not isinstance(collection, list):
            expr_fail("items-not-a-list", coll_path)
        item_key = node.get("item_key", "item")
        total = Decimal(0)
        for index, item in enumerate(collection):
            if not isinstance(item, dict):
                expr_fail("item-not-an-object", coll_path + [index])
            child_ctx = {
                **ctx,
                item_key: item,
                "__item__": item,
                "__in_each__": True,
                "path": coll_path + [index],
            }
            part = eval_expr(node["each"], child_ctx)
            if not isinstance(part, Decimal):
                part = Decimal(part)
            total += part
        return total

    if op == "quantize":
        value = eval_expr(node["of"], ctx)
        if not isinstance(value, Decimal):
            value = Decimal(value)
        exp = Decimal(node.get("exp", "0.01"))
        rounding = _ROUNDING[node.get("rounding", "ROUND_HALF_UP")]
        return value.quantize(exp, rounding=rounding)

    if op == "decimal_str":
        value = eval_expr(node["of"], ctx)
        if not isinstance(value, Decimal):
            value = Decimal(value)
        places = int(node.get("places", 2))
        q = Decimal(10) ** -places
        value = value.quantize(q)
        return f"{value:.{places}f}"

    if op == "str_len":
        value = eval_expr(node["of"], ctx)
        if not isinstance(value, str):
            expr_fail("invalid-text", path)
        return len(value)

    if op == "line_count":
        value = eval_expr(node["of"], ctx)
        if not isinstance(value, str):
            expr_fail("invalid-text", path)
        return len(value.splitlines())

    if op == "word_count":
        value = eval_expr(node["of"], ctx)
        if not isinstance(value, str):
            expr_fail("invalid-text", path)
        return len(value.split())

    if op == "unique_casefold_word_count":
        value = eval_expr(node["of"], ctx)
        if not isinstance(value, str):
            expr_fail("invalid-text", path)
        return len({w.casefold() for w in value.split()})

    expr_fail("unknown-op", path)


def _bound(raw):
    if isinstance(raw, Decimal):
        return raw
    if isinstance(raw, int) and not isinstance(raw, bool):
        return Decimal(raw)
    if isinstance(raw, str):
        return Decimal(raw)
    return Decimal(str(raw))


def _get_path(ctx, path):
    """Resolve path against root, or against current item inside sum_each."""
    path = tuple(path)
    root = ctx.get("root")
    item = ctx.get("item", ctx.get("__item__"))
    if path and path[0] == "item":
        return _dig(item, path[1:])
    if ctx.get("__in_each__") and item is not None:
        got = _dig(item, path)
        if got is not None or (isinstance(item, dict) and path and path[0] in item):
            return got
    return _dig(root, path)


def _dig(obj, path):
    cur = obj
    for part in path:
        if cur is None:
            return None
        if isinstance(part, int):
            if not isinstance(cur, list) or part < 0 or part >= len(cur):
                return None
            cur = cur[part]
        else:
            if not isinstance(cur, dict) or part not in cur:
                return None
            cur = cur[part]
    return cur
'''


def emit_expression_feature_body(name: str, transformation: dict) -> str:
    """Emit feature function body for kind=expression."""
    program = transformation.get("program")
    if program is None:
        # allow bindings + result form
        bindings = transformation.get("bindings") or {}
        result = transformation.get("result")
        if result is None:
            raise ValueError("expression transformation requires program or result")
        # Synthesize object program from bindings by inlining
        # For simplicity require program key
        program = result

    errors = validate_expression(program)
    if errors:
        raise ValueError(f"invalid expression: {errors}")

    # Also validate binding expressions if present
    bindings = transformation.get("bindings") or {}
    for bname, bnode in bindings.items():
        errs = validate_expression(bnode)
        if errs:
            raise ValueError(f"invalid binding {bname}: {errs}")

    input_key = transformation.get("input_key", "document")  # document | text | value
    merge_mode = transformation.get("merge", "replace_stats")  
    # merge modes: replace_stats (put in value["stats"]), merge_value, set_value

    program_literal = _py_literal(program)
    bindings_literal = _py_literal(bindings)

    return f'''    if thing["state"] in {{"invalid", "absent", "false", "unknown"}}:
        return {{
            **thing,
            "evidence": (*thing["evidence"], "part:{name}", "{name}:skipped"),
            "state": thing["state"],
        }}
    value = thing["value"]
    if not isinstance(value, dict):
        return {{
            **thing,
            "value": {{"error": "invalid-internal-thing"}},
            "evidence": (*thing["evidence"], "part:{name}", "{name}:bad-value"),
            "state": "invalid",
        }}
    if "error" in value and "{input_key}" not in value and "text" not in value and "document" not in value:
        return {{
            **thing,
            "evidence": (*thing["evidence"], "part:{name}", "{name}:prior-error"),
            "state": "invalid",
        }}

    # Resolve evaluation root
    if "{input_key}" == "text":
        if "text" not in value or not isinstance(value.get("text"), str):
            return {{
                **thing,
                "value": {{**value, "error": "missing-text"}},
                "evidence": (*thing["evidence"], "part:{name}", "{name}:missing-text"),
                "state": "absent",
            }}
        root = {{"text": value["text"]}}
    elif "{input_key}" == "document":
        if "document" not in value:
            return {{
                **thing,
                "value": {{**value, "error": "missing-document"}},
                "evidence": (*thing["evidence"], "part:{name}", "{name}:missing-document"),
                "state": "absent",
            }}
        root = value["document"]
        if not isinstance(root, dict):
            return {{
                **thing,
                "value": {{**value, "error": "input-not-an-object", "path": []}},
                "evidence": (*thing["evidence"], "part:{name}", "{name}:not-object"),
                "state": "invalid",
            }}
    else:
        root = value

    from .expr_runtime import eval_expr, is_expr_fail

    program = {program_literal}
    bindings = {bindings_literal}
    ctx = {{"root": root, "path": []}}
    try:
        bound = {{}}
        for bname, bnode in bindings.items():
            bound[bname] = eval_expr(bnode, ctx)
            # later bindings may ref earlier ones
            ctx = {{**ctx, "bindings": bound}}
        ctx = {{**ctx, "bindings": bound}}
        result = eval_expr(program, ctx)
    except ValueError as exc:
        if not is_expr_fail(exc):
            raise
        err_value = {{
            **value,
            "error": exc.uc_expr_error,
            "path": list(exc.uc_expr_path),
        }}
        return {{
            **thing,
            "value": err_value,
            "evidence": (*thing["evidence"], "part:{name}", f"{name}:error:{{exc.uc_expr_error}}"),
            "state": "invalid",
        }}

    if "{merge_mode}" == "stats":
        new_value = {{**value, "stats": result}}
    elif "{merge_mode}" == "merge":
        if not isinstance(result, dict):
            return {{
                **thing,
                "value": {{**value, "error": "invalid-internal-thing"}},
                "evidence": (*thing["evidence"], "part:{name}", "{name}:bad-result"),
                "state": "invalid",
            }}
        new_value = {{**value, **result}}
    else:
        new_value = {{**value, "result": result}}

    return {{
        **thing,
        "value": new_value,
        "evidence": (*thing["evidence"], "part:{name}", "{name}:ok"),
        "state": "formed",
    }}
'''


def _py_literal(obj: Any) -> str:
    """Stable Python literal for embedding AST nodes (tuples not lists)."""
    if obj is None or isinstance(obj, (bool, int, float)):
        return repr(obj)
    if isinstance(obj, str):
        return json.dumps(obj, ensure_ascii=False)
    if isinstance(obj, tuple):
        if not obj:
            return "()"
        if len(obj) == 1:
            return f"({_py_literal(obj[0])},)"
        return "(" + ", ".join(_py_literal(x) for x in obj) + ")"
    if isinstance(obj, list):
        return "[" + ", ".join(_py_literal(x) for x in obj) + "]"
    if isinstance(obj, dict):
        items = ", ".join(f"{_py_literal(k)}: {_py_literal(v)}" for k, v in obj.items())
        return "{" + items + "}"
    raise TypeError(f"cannot literalize {type(obj)}")
