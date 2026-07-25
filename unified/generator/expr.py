"""Domain-neutral expression constructors and validation.

Public constructors accept one input (a thing, or a plain config map that is
wrapped) and return one thing whose value is a validated expression node.

No string eval. No classes. Nodes are plain dicts with an "op" field.
"""

from __future__ import annotations

from typing import Any

from ..thing import STATES, is_thing

OPS = frozenset(
    {
        "literal",
        "field",
        "ref",
        "object",
        "count",
        "as_int",
        "as_decimal",
        "require",
        "min_value",
        "max_value",
        "mul",
        "add",
        "sum_each",
        "quantize",
        "decimal_str",
        "str_len",
        "line_count",
        "word_count",
        "unique_casefold_word_count",
        "coalesce",
        "const_path",
    }
)


def _wrap(raw: Any) -> dict:
    if is_thing(raw):
        return raw
    return {
        "value": raw,
        "depths": (),
        "axes": (),
        "evidence": (),
        "state": "unknown",
    }


def _cfg(thing) -> dict:
    thing = _wrap(thing)
    value = thing.get("value")
    if not isinstance(value, dict):
        return {}
    return value


def _node_from(x: Any) -> dict | None:
    if is_thing(x):
        v = x.get("value")
        if isinstance(v, dict) and "op" in v:
            return v
        return None
    if isinstance(x, dict) and "op" in x:
        return x
    return None


def _expr_result(node: dict, mark: str, base=None) -> dict:
    evidence = ()
    if is_thing(base):
        evidence = base.get("evidence") or ()
    return {
        "value": node,
        "depths": (),
        "axes": (),
        "evidence": (*evidence, f"expr:{mark}"),
        "state": "formed",
    }


def _reject(mark: str, raw=None) -> dict:
    return {
        "value": raw,
        "depths": (),
        "axes": (),
        "evidence": (f"expr:{mark}",),
        "state": "invalid",
    }


def literal(thing):
    """literal({"value": <any>})"""
    thing = _wrap(thing)
    cfg = _cfg(thing)
    if "value" not in cfg:
        return _reject("literal-missing-value", cfg)
    return _expr_result({"op": "literal", "value": cfg["value"]}, "literal", thing)


def field(thing):
    """field({"path": ("a", 0, "b")}) — path into evaluation context root or item."""
    thing = _wrap(thing)
    cfg = _cfg(thing)
    path = cfg.get("path")
    if not isinstance(path, (list, tuple)) or not path:
        return _reject("field-bad-path", cfg)
    path_t = tuple(path)
    for part in path_t:
        if not isinstance(part, (str, int)) or isinstance(part, bool):
            return _reject("field-bad-path-part", cfg)
    return _expr_result({"op": "field", "path": path_t}, "field", thing)


def ref(thing):
    """ref({"name": "subtotal"}) — reference a named binding (CSE)."""
    thing = _wrap(thing)
    cfg = _cfg(thing)
    name = cfg.get("name")
    if not isinstance(name, str) or not name.isidentifier():
        return _reject("ref-bad-name", cfg)
    return _expr_result({"op": "ref", "name": name}, "ref", thing)


def object_expr(thing):
    """object_expr({"fields": {name: expr_node_or_thing, ...}})"""
    thing = _wrap(thing)
    cfg = _cfg(thing)
    fields = cfg.get("fields")
    if not isinstance(fields, dict) or not fields:
        return _reject("object-bad-fields", cfg)
    out = {}
    for key, val in fields.items():
        if not isinstance(key, str) or not key:
            return _reject("object-bad-key", cfg)
        node = _node_from(val)
        if node is None:
            return _reject("object-bad-child", cfg)
        out[key] = node
    return _expr_result({"op": "object", "fields": out}, "object", thing)


def count(thing):
    """count({"of": expr})"""
    thing = _wrap(thing)
    cfg = _cfg(thing)
    of = _node_from(cfg.get("of"))
    if of is None:
        return _reject("count-bad-of", cfg)
    return _expr_result({"op": "count", "of": of}, "count", thing)


def as_int(thing):
    """as_int({"of": expr, "path": optional, "type_error": ..., "missing_error": ...})"""
    thing = _wrap(thing)
    cfg = _cfg(thing)
    of = _node_from(cfg.get("of"))
    if of is None:
        return _reject("as_int-bad-of", cfg)
    path = cfg.get("path", ())
    if not isinstance(path, (list, tuple)):
        return _reject("as_int-bad-path", cfg)
    node = {"op": "as_int", "of": of, "path": tuple(path)}
    if isinstance(cfg.get("type_error"), str):
        node["type_error"] = cfg["type_error"]
    if isinstance(cfg.get("missing_error"), str):
        node["missing_error"] = cfg["missing_error"]
    return _expr_result(node, "as_int", thing)


def as_decimal(thing):
    """as_decimal({"of": expr, "path": ...}) — Decimal from decimal *string* only."""
    thing = _wrap(thing)
    cfg = _cfg(thing)
    of = _node_from(cfg.get("of"))
    if of is None:
        return _reject("as_decimal-bad-of", cfg)
    path = cfg.get("path", ())
    if not isinstance(path, (list, tuple)):
        return _reject("as_decimal-bad-path", cfg)
    node = {"op": "as_decimal", "of": of, "path": tuple(path)}
    if isinstance(cfg.get("type_error"), str):
        node["type_error"] = cfg["type_error"]
    if isinstance(cfg.get("missing_error"), str):
        node["missing_error"] = cfg["missing_error"]
    return _expr_result(node, "as_decimal", thing)


def require(thing):
    """require({"of": expr, "path": (...), "error": "missing-..."})"""
    thing = _wrap(thing)
    cfg = _cfg(thing)
    of = _node_from(cfg.get("of"))
    if of is None:
        return _reject("require-bad-of", cfg)
    path = cfg.get("path", ())
    error = cfg.get("error", "missing")
    if not isinstance(path, (list, tuple)) or not isinstance(error, str):
        return _reject("require-bad-meta", cfg)
    return _expr_result(
        {"op": "require", "of": of, "path": tuple(path), "error": error},
        "require",
        thing,
    )


def min_value(thing):
    """min_value({"of": expr, "bound": number|str, "path": (...), "error": "..."})"""
    thing = _wrap(thing)
    cfg = _cfg(thing)
    of = _node_from(cfg.get("of"))
    if of is None:
        return _reject("min-bad-of", cfg)
    if "bound" not in cfg:
        return _reject("min-missing-bound", cfg)
    path = cfg.get("path", ())
    error = cfg.get("error", "below-minimum")
    if not isinstance(path, (list, tuple)) or not isinstance(error, str):
        return _reject("min-bad-meta", cfg)
    return _expr_result(
        {
            "op": "min_value",
            "of": of,
            "bound": cfg["bound"],
            "path": tuple(path),
            "error": error,
        },
        "min_value",
        thing,
    )


def max_value(thing):
    """max_value({"of": expr, "bound": number|str, "path": (...), "error": "..."})"""
    thing = _wrap(thing)
    cfg = _cfg(thing)
    of = _node_from(cfg.get("of"))
    if of is None:
        return _reject("max-bad-of", cfg)
    if "bound" not in cfg:
        return _reject("max-missing-bound", cfg)
    path = cfg.get("path", ())
    error = cfg.get("error", "above-maximum")
    if not isinstance(path, (list, tuple)) or not isinstance(error, str):
        return _reject("max-bad-meta", cfg)
    return _expr_result(
        {
            "op": "max_value",
            "of": of,
            "bound": cfg["bound"],
            "path": tuple(path),
            "error": error,
        },
        "max_value",
        thing,
    )


def mul(thing):
    """mul({"values": (expr, expr, ...)})"""
    thing = _wrap(thing)
    cfg = _cfg(thing)
    values = cfg.get("values")
    if not isinstance(values, (list, tuple)) or len(values) < 2:
        return _reject("mul-bad-values", cfg)
    nodes = []
    for v in values:
        n = _node_from(v)
        if n is None:
            return _reject("mul-bad-child", cfg)
        nodes.append(n)
    return _expr_result({"op": "mul", "values": tuple(nodes)}, "mul", thing)


def add(thing):
    """add({"values": (expr, expr, ...)})"""
    thing = _wrap(thing)
    cfg = _cfg(thing)
    values = cfg.get("values")
    if not isinstance(values, (list, tuple)) or len(values) < 2:
        return _reject("add-bad-values", cfg)
    nodes = []
    for v in values:
        n = _node_from(v)
        if n is None:
            return _reject("add-bad-child", cfg)
        nodes.append(n)
    return _expr_result({"op": "add", "values": tuple(nodes)}, "add", thing)


def sum_each(thing):
    """sum_each({"collection": expr, "each": expr, "item_key": "item"})"""
    thing = _wrap(thing)
    cfg = _cfg(thing)
    collection = _node_from(cfg.get("collection"))
    each = _node_from(cfg.get("each"))
    if collection is None or each is None:
        return _reject("sum_each-bad", cfg)
    item_key = cfg.get("item_key", "item")
    if not isinstance(item_key, str) or not item_key:
        return _reject("sum_each-bad-item-key", cfg)
    path = cfg.get("path", ("items",))
    if not isinstance(path, (list, tuple)):
        return _reject("sum_each-bad-path", cfg)
    return _expr_result(
        {
            "op": "sum_each",
            "collection": collection,
            "each": each,
            "item_key": item_key,
            "path": tuple(path),
        },
        "sum_each",
        thing,
    )


def quantize(thing):
    """quantize({"of": expr, "exp": "0.01", "rounding": "ROUND_HALF_UP"})"""
    thing = _wrap(thing)
    cfg = _cfg(thing)
    of = _node_from(cfg.get("of"))
    if of is None:
        return _reject("quantize-bad-of", cfg)
    exp = cfg.get("exp", "0.01")
    rounding = cfg.get("rounding", "ROUND_HALF_UP")
    if not isinstance(exp, str) or not isinstance(rounding, str):
        return _reject("quantize-bad-meta", cfg)
    if rounding not in {"ROUND_HALF_UP", "ROUND_DOWN", "ROUND_UP", "ROUND_HALF_EVEN"}:
        return _reject("quantize-bad-rounding", cfg)
    return _expr_result(
        {"op": "quantize", "of": of, "exp": exp, "rounding": rounding},
        "quantize",
        thing,
    )


def decimal_str(thing):
    """decimal_str({"of": expr, "places": 2}) — fixed-point string."""
    thing = _wrap(thing)
    cfg = _cfg(thing)
    of = _node_from(cfg.get("of"))
    if of is None:
        return _reject("decimal_str-bad-of", cfg)
    places = cfg.get("places", 2)
    if not isinstance(places, int) or isinstance(places, bool) or places < 0 or places > 12:
        return _reject("decimal_str-bad-places", cfg)
    return _expr_result(
        {"op": "decimal_str", "of": of, "places": places},
        "decimal_str",
        thing,
    )


def str_len(thing):
    """str_len({"of": expr})"""
    thing = _wrap(thing)
    cfg = _cfg(thing)
    of = _node_from(cfg.get("of"))
    if of is None:
        return _reject("str_len-bad-of", cfg)
    return _expr_result({"op": "str_len", "of": of}, "str_len", thing)


def line_count(thing):
    """line_count({"of": expr}) — len(text.splitlines())."""
    thing = _wrap(thing)
    cfg = _cfg(thing)
    of = _node_from(cfg.get("of"))
    if of is None:
        return _reject("line_count-bad-of", cfg)
    return _expr_result({"op": "line_count", "of": of}, "line_count", thing)


def word_count(thing):
    """word_count({"of": expr}) — len(text.split())."""
    thing = _wrap(thing)
    cfg = _cfg(thing)
    of = _node_from(cfg.get("of"))
    if of is None:
        return _reject("word_count-bad-of", cfg)
    return _expr_result({"op": "word_count", "of": of}, "word_count", thing)


def unique_casefold_word_count(thing):
    """unique_casefold_word_count({"of": expr})."""
    thing = _wrap(thing)
    cfg = _cfg(thing)
    of = _node_from(cfg.get("of"))
    if of is None:
        return _reject("unique_casefold_word_count-bad-of", cfg)
    return _expr_result(
        {"op": "unique_casefold_word_count", "of": of},
        "unique_casefold_word_count",
        thing,
    )


def validate_expression(node: Any, *, path: tuple = ()) -> tuple[str, ...]:
    """Return validation error marks; empty means OK. No eval."""
    if not isinstance(node, dict) or "op" not in node:
        return (f"expr-invalid-node:{path}",)
    op = node["op"]
    if op not in OPS:
        return (f"expr-unknown-op:{op}",)
    errors: list[str] = []

    def child(key, required=True):
        if key not in node:
            if required:
                errors.append(f"expr-missing:{op}:{key}:{path}")
            return
        sub = node[key]
        if isinstance(sub, dict) and "op" in sub:
            errors.extend(validate_expression(sub, path=path + (key,)))
        elif isinstance(sub, (list, tuple)):
            for i, item in enumerate(sub):
                if isinstance(item, dict) and "op" in item:
                    errors.extend(validate_expression(item, path=path + (key, i)))
        elif key == "fields" and isinstance(sub, dict):
            for fk, fv in sub.items():
                if isinstance(fv, dict) and "op" in fv:
                    errors.extend(validate_expression(fv, path=path + (key, fk)))

    if op == "literal":
        if "value" not in node:
            errors.append(f"expr-literal-no-value:{path}")
    elif op == "field":
        p = node.get("path")
        if not isinstance(p, tuple) or not p:
            errors.append(f"expr-field-path:{path}")
    elif op == "ref":
        name = node.get("name")
        if not isinstance(name, str) or not name.isidentifier():
            errors.append(f"expr-ref-name:{path}")
    elif op == "object":
        fields = node.get("fields")
        if not isinstance(fields, dict) or not fields:
            errors.append(f"expr-object-fields:{path}")
        else:
            child("fields")
    elif op in {
        "count",
        "as_int",
        "as_decimal",
        "require",
        "min_value",
        "max_value",
        "quantize",
        "decimal_str",
        "str_len",
        "line_count",
        "word_count",
        "unique_casefold_word_count",
    }:
        child("of")
    elif op in {"mul", "add"}:
        vals = node.get("values")
        if not isinstance(vals, tuple) or len(vals) < 2:
            errors.append(f"expr-{op}-values:{path}")
        else:
            child("values")
    elif op == "sum_each":
        child("collection")
        child("each")
    return tuple(errors)


def unwrap_expr(x: Any) -> dict | None:
    """Extract expression node from constructor result or bare node."""
    return _node_from(x)


# Alias used in declarations for clarity
object_ = object_expr
