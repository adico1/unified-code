"""Portable primitive registry — generic only; no domain vocabulary in source."""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal, InvalidOperation, ROUND_DOWN, ROUND_HALF_EVEN, ROUND_HALF_UP, ROUND_UP

from .thing import approx_size, deep_copy_data, value_of, with_evidence, with_state


_ROUNDING = {
    "ROUND_HALF_UP": ROUND_HALF_UP,
    "ROUND_DOWN": ROUND_DOWN,
    "ROUND_UP": ROUND_UP,
    "ROUND_HALF_EVEN": ROUND_HALF_EVEN,
}


def registry():
    """Closed map of portable primitives."""
    return {
        "identity": prim_identity,
        "letter": prim_letter,
        "mark_inward": prim_mark_inward,
        "require_source": prim_require_source,
        "eval_expression": prim_eval_expression,
        "merge_result": prim_merge_result,
        "verify_result": prim_verify_result,
        "present_json": prim_present_json,
        "mark_part": prim_mark_part,
        "accept_outward": prim_accept_outward,
    }


def apply_primitive(thing, name):
    reg = registry()
    if name not in reg:
        v = dict(value_of(thing))
        v["error"] = "unknown-primitive"
        v["pending_primitive"] = name
        return with_state(
            with_evidence({**thing, "value": v}, f"primitive:unknown:{name}"),
            "invalid",
        )
    return reg[name](thing)


def prim_identity(thing):
    return with_evidence(thing, "primitive:identity")


def prim_mark_inward(thing):
    return with_evidence(thing, "boundary:inward")


def prim_letter(thing):
    """Classify store document/host value states (L6)."""
    v = dict(value_of(thing))
    store = dict(v.get("store") or {})
    payload = store.get("document", store.get("text", store.get("host")))
    # prefer explicit host payload for classification when present
    if "host" in store and store.get("text") is None and store.get("document") is None:
        payload = store.get("host")
    evidence = tuple(thing.get("evidence") or ())
    if payload is None and store.get("error"):
        # already erred; keep
        return with_evidence({**thing, "value": v}, "letter:prior-error")
    if payload is None and not store:
        store_host = v.get("host_input")
        payload = store_host
    # classify
    if payload is None and "host_input" in v and v["host_input"] is None:
        v["store"] = store
        return with_state(
            with_evidence({**thing, "value": v}, "letter:absent"),
            "absent",
        )
    # use store fields as formed content
    if thing.get("state") in {"invalid", "absent", "false"}:
        return with_evidence(thing, "letter:skipped")
    v["store"] = store
    return with_state(
        with_evidence({**thing, "value": v}, "letter:distinguished"),
        "formed",
    )


def prim_require_source(thing):
    """Validate arity-1 source from host_input using image config (generic)."""
    v = dict(value_of(thing))
    image = v.get("image") or {}
    cfg = image.get("source") or {}
    field = cfg.get("field", "source")
    err_missing = cfg.get("missing", "missing-source")
    err_extra = cfg.get("extra", "extra-source")
    host = v.get("host_input")
    store = dict(v.get("store") or {})
    # Direct inject of payload (tests): skip path requirement
    if isinstance(host, dict) and isinstance(host.get("text"), str):
        store[field] = host.get(field) or "-"
        v["store"] = store
        return with_evidence({**thing, "value": v}, "source:ok")
    if isinstance(host, dict) and isinstance(host.get("document"), dict):
        store[field] = host.get(field) or "-"
        v["store"] = store
        return with_evidence({**thing, "value": v}, "source:ok")
    if isinstance(host, dict) and field in host and host[field] is not None:
        store[field] = host[field]
        v["store"] = store
        return with_evidence({**thing, "value": v}, "source:ok")
    argv = None
    if isinstance(host, dict) and "argv" in host:
        argv = host.get("argv")
    elif isinstance(host, (list, tuple)):
        argv = host
    if argv is None:
        store["error"] = err_missing
        v["store"] = store
        return with_state(
            with_evidence({**thing, "value": v}, "source:missing"),
            "invalid",
        )
    if not isinstance(argv, (list, tuple)):
        store["error"] = err_missing
        v["store"] = store
        return with_state(
            with_evidence({**thing, "value": v}, "source:bad-argv"),
            "invalid",
        )
    if len(argv) == 0:
        store["error"] = err_missing
        v["store"] = store
        return with_state(
            with_evidence({**thing, "value": v}, "source:missing"),
            "invalid",
        )
    if len(argv) > 1:
        store["error"] = err_extra
        v["store"] = store
        return with_state(
            with_evidence({**thing, "value": v}, "source:extra"),
            "invalid",
        )
    store[field] = argv[0]
    v["store"] = store
    return with_evidence({**thing, "value": v}, "source:ok")


def prim_accept_outward(thing):
    """Merge outward_result into store using image boundary config."""
    v = dict(value_of(thing))
    image = v.get("image") or {}
    boundary = image.get("boundary") or {}
    result = v.get("outward_result")
    store = dict(v.get("store") or {})
    evidence = tuple(thing.get("evidence") or ())
    bname = boundary.get("name") or "boundary"
    if result is None:
        store["error"] = store.get("error") or "outward-missing-result"
        v["store"] = store
        return with_state(
            with_evidence({**thing, "value": v}, "outward:missing"),
            "invalid",
        )
    if isinstance(result, dict) and result.get("error"):
        store["error"] = result["error"]
        if "path" in result:
            store["path"] = result["path"]
        v["store"] = store
        v["outward_result"] = None
        return with_state(
            with_evidence(
                {**thing, "value": v},
                f"boundary:{bname}",
                f"read:error:{result['error']}",
            ),
            "invalid",
        )
    target = boundary.get("target_field") or "payload"
    if isinstance(result, dict) and "data" in result:
        store[target] = result["data"]
    else:
        store[target] = result
    v["store"] = store
    v["outward_result"] = None
    v["outward_request"] = None
    return with_state(
        with_evidence(
            {**thing, "value": v},
            f"boundary:{bname}",
            "read:ok",
        ),
        "formed",
    )


def prim_eval_expression(thing):
    """Evaluate image expression program against store root."""
    if thing.get("state") in {"invalid", "absent", "false", "unknown"}:
        return with_evidence(thing, "eval:skipped")
    v = dict(value_of(thing))
    image = v.get("image") or {}
    store = dict(v.get("store") or {})
    if store.get("error"):
        return with_evidence(thing, "eval:prior-error")
    input_key = image.get("input_key") or "document"
    program = image.get("expression")
    bindings_ast = image.get("bindings") or {}
    part_name = image.get("part_name") or "part"
    if program is None:
        store["error"] = "missing-expression"
        v["store"] = store
        return with_state(
            with_evidence({**thing, "value": v}, "eval:missing-expression"),
            "invalid",
        )
    root = _resolve_root(store, input_key)
    if isinstance(root, dict) and root.get("__error__"):
        store["error"] = root["__error__"]
        v["store"] = store
        return with_state(
            with_evidence(
                {**thing, "value": v},
                f"part:{part_name}",
                f"{part_name}:missing-input",
            ),
            "absent" if root.get("__absent__") else "invalid",
        )
    ctx = {"root": root, "path": [], "bindings": {}}
    try:
        bound = {}
        # binding_order is canonical (compile topo-sort). Never sort keys:
        # alphabetical order breaks CSE deps (tax before tax_rate). If order
        # is absent, use dict insertion order only (not sorted).
        order = image.get("binding_order")
        if not isinstance(order, list) or not order:
            order = list(bindings_ast.keys()) if isinstance(bindings_ast, dict) else []
        for bname in order:
            if not isinstance(bname, str) or bname not in bindings_ast:
                continue
            # Evaluate into bound; JSON null is a present binding (key exists).
            bound[bname] = eval_expr(bindings_ast[bname], {**ctx, "bindings": bound})
            ctx = {**ctx, "bindings": bound}
        ctx = {**ctx, "bindings": bound}
        result = eval_expr(program, ctx)
    except Exception as exc:  # noqa: BLE001 — expr fail or machine fault
        if _is_expr_fail(exc):
            err, epath = args_error_path(exc)
            store["error"] = err
            store["path"] = list(epath)
            v["store"] = store
            return with_state(
                with_evidence(
                    {**thing, "value": v},
                    f"part:{part_name}",
                    f"{part_name}:error:{err}",
                ),
                "invalid",
            )
        # escalate as machine fault marker
        v["machine_fault"] = {
            "operation": "eval_expression",
            "error_type": type(exc).__name__,
            "message": str(exc),
        }
        return with_state(
            with_evidence({**thing, "value": v}, "eval:fault"),
            "invalid",
        )
    v["store"] = store
    v["_acc"] = result
    return with_evidence(
        {**thing, "value": v},
        f"part:{part_name}",
        f"{part_name}:ok",
    )


def prim_merge_result(thing):
    v = dict(value_of(thing))
    image = v.get("image") or {}
    key = image.get("merge_key") or "result"
    store = dict(v.get("store") or {})
    if thing.get("state") in {"invalid", "absent", "false"}:
        return with_evidence(thing, "merge:skipped")
    store[key] = v.get("_acc")
    v["store"] = store
    return with_evidence({**thing, "value": v}, "merge:ok")


def prim_verify_result(thing):
    """Expected validation rejection — never opens a ticket."""
    v = dict(value_of(thing))
    image = v.get("image") or {}
    cfg = image.get("verify") or {}
    store = dict(v.get("store") or {})
    field = cfg.get("require_value_field")
    required = tuple(cfg.get("require_evidence_contains") or ())
    evidence = tuple(thing.get("evidence") or ())
    if thing.get("state") in {"invalid", "absent", "false"}:
        return with_state(
            with_evidence(thing, "script-law:fail"),
            "invalid",
        )
    if store.get("error"):
        return with_state(
            with_evidence(thing, "script-law:fail"),
            "invalid",
        )
    if field and field not in store:
        return with_state(
            with_evidence(thing, "script-law:fail"),
            "invalid",
        )
    ok = all(mark in evidence for mark in required)
    if not ok:
        return with_state(
            with_evidence(thing, "script-law:fail"),
            "invalid",
        )
    return with_state(
        with_evidence(thing, "script-law:pass"),
        "valid",
    )


def prim_present_json(thing):
    v = dict(value_of(thing))
    image = v.get("image") or {}
    cfg = image.get("presentation") or {}
    store = dict(v.get("store") or {})
    keys = tuple(cfg.get("success_keys") or ())
    success_from = cfg.get("success_from") or "result"
    include_path = bool(cfg.get("include_error_path"))
    payload = None
    state = thing.get("state")
    if state == "valid":
        src = store.get(success_from)
        if isinstance(src, dict):
            payload = src
        elif keys and all(k in store for k in keys):
            payload = store
    if payload is not None and keys:
        ordered = {k: payload[k] for k in keys if k in payload}
        text = json.dumps(ordered, ensure_ascii=False, separators=(",", ":"))
        exit_code = 0
    else:
        err = store.get("error") or "invalid"
        body = {"error": err}
        if include_path and isinstance(store.get("path"), (list, tuple)):
            body["path"] = list(store["path"])
        # preserve key order: error then path
        text = json.dumps(body, ensure_ascii=False, separators=(",", ":"))
        exit_code = 1
    store["presentation"] = {"text": text, "exit_code": exit_code}
    v["store"] = store
    v["result"] = store["presentation"]
    return with_evidence({**thing, "value": v}, "present_result:ok")


def prim_mark_part(thing):
    v = dict(value_of(thing))
    image = v.get("image") or {}
    name = image.get("part_name") or "part"
    return with_evidence(thing, f"part:{name}")


def _resolve_root(store, input_key):
    if input_key == "text":
        if "text" not in store or not isinstance(store.get("text"), str):
            return {"__error__": "missing-text", "__absent__": True}
        return {"text": store["text"]}
    if input_key == "document":
        if "document" not in store:
            return {"__error__": "missing-document", "__absent__": True}
        doc = store["document"]
        if not isinstance(doc, dict):
            return {"__error__": "input-not-an-object"}
        return doc
    return store


# Plain-data expression fault (no class). Marker exception carries (error, path).
_EXPR_FAIL_MARK = "__uem_expr_fail__"


def _expr_fail(error, path=()):
    raise Exception((_EXPR_FAIL_MARK, error, tuple(path)))


def _is_expr_fail(exc):
    args = getattr(exc, "args", ())
    return (
        isinstance(exc, Exception)
        and len(args) == 1
        and isinstance(args[0], tuple)
        and len(args[0]) == 3
        and args[0][0] == _EXPR_FAIL_MARK
    )


def args_error_path(exc):
    _mark, error, path = exc.args[0]
    return error, path


def eval_expr(node, ctx):
    if not isinstance(node, dict) or "op" not in node:
        _expr_fail("bad-node", ctx.get("path") or ())
    op = node["op"]
    path = list(ctx.get("path") or ())
    if op == "literal":
        return node["value"]
    if op == "ref":
        bindings = ctx.get("bindings") or {}
        name = node["name"]
        if name not in bindings:
            _expr_fail("missing-binding", path + [name])
        return bindings[name]
    if op == "field":
        return _get_path(ctx, node["path"])
    if op == "object":
        out = {}
        for key in sorted(node["fields"].keys()) if False else node["fields"].keys():
            # preserve declared field order (dict insertion order)
            out[key] = eval_expr(node["fields"][key], ctx)
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
            _expr_fail(node.get("error", "missing"), err_path)
        return value
    if op == "as_int":
        value = eval_expr(node["of"], ctx)
        err_path = list(path) + list(node.get("path") or ())
        if value is None:
            _expr_fail(node.get("missing_error", "missing"), err_path)
        if isinstance(value, bool) or not isinstance(value, int):
            _expr_fail(node.get("type_error", "invalid-integer"), err_path)
        return value
    if op == "as_decimal":
        value = eval_expr(node["of"], ctx)
        err_path = list(path) + list(node.get("path") or ())
        if value is None:
            _expr_fail(node.get("missing_error", "missing"), err_path)
        if isinstance(value, Decimal):
            return value
        if not isinstance(value, str):
            _expr_fail(node.get("type_error", "not-decimal-string"), err_path)
        try:
            return Decimal(value)
        except InvalidOperation:
            _expr_fail(node.get("type_error", "not-decimal-string"), err_path)
    if op == "min_value":
        value = eval_expr(node["of"], ctx)
        bound = _bound(node["bound"])
        err_path = list(path) + list(node.get("path") or ())
        if value < bound:
            _expr_fail(node.get("error", "below-minimum"), err_path)
        return value
    if op == "max_value":
        value = eval_expr(node["of"], ctx)
        bound = _bound(node["bound"])
        err_path = list(path) + list(node.get("path") or ())
        if value > bound:
            _expr_fail(node.get("error", "above-maximum"), err_path)
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
            _expr_fail("items-not-a-list", coll_path)
        item_key = node.get("item_key", "item")
        total = Decimal(0)
        index = 0
        while index < len(collection):
            item = collection[index]
            if not isinstance(item, dict):
                _expr_fail("item-not-an-object", coll_path + [index])
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
            index += 1
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
            _expr_fail("invalid-text", path)
        return len(value)
    if op == "line_count":
        value = eval_expr(node["of"], ctx)
        if not isinstance(value, str):
            _expr_fail("invalid-text", path)
        return len(value.splitlines())
    if op == "word_count":
        value = eval_expr(node["of"], ctx)
        if not isinstance(value, str):
            _expr_fail("invalid-text", path)
        return len(value.split())
    if op == "unique_casefold_word_count":
        value = eval_expr(node["of"], ctx)
        if not isinstance(value, str):
            _expr_fail("invalid-text", path)
        # set via loop for clarity (audited iteration site)
        seen = set()
        for w in value.split():
            seen.add(w.casefold())
        return len(seen)
    _expr_fail("unknown-op", path)


def _bound(raw):
    if isinstance(raw, Decimal):
        return raw
    if isinstance(raw, int) and not isinstance(raw, bool):
        return Decimal(raw)
    if isinstance(raw, str):
        return Decimal(raw)
    return Decimal(str(raw))


def _get_path(ctx, path):
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


def construct_ticket_from_fault(thing):
    """TICKET opcode helper — pure, redacted, deterministic id."""
    v = dict(value_of(thing))
    fault = v.get("machine_fault") or {}
    evidence = tuple(thing.get("evidence") or ())
    operation = str(fault.get("operation") or "machine")
    error_type = str(fault.get("error_type") or "Fault")
    message = _redact(fault.get("message") or "unhandled")
    # Ticket identity from failure material only (cross-host stable).
    raw = "|".join([operation, error_type, message])
    cid = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
    ticket = {
        "kind": "unhandled-exception",
        "operation": operation,
        "error_type": error_type,
        "message": message,
        "evidence": list(evidence[-20:]),
        "correlation_id": cid,
        "ticket_id": cid,
        "occurred_at": "static",
        "acked": False,
    }
    if isinstance(v.get("ticket"), dict) and v["ticket"].get("correlation_id") == cid:
        ticket = v["ticket"]
    v["ticket"] = ticket
    v["event"] = "ticket.open"
    return with_state(
        with_evidence({**thing, "value": v}, "event:ticket.open", "event:ticket.construct"),
        "invalid",
    )


def _redact(message):
    text = str(message)
    banned = ("password", "token", "secret", "authorization", "api_key", "apikey")
    lower = text.lower()
    marked = lower
    for word in banned:
        marked = marked.replace(word, "[redacted]")
    if "[redacted]" in marked:
        return "[redacted-message]"
    return text[:500]
