"""Emit audited L10 event-runtime primitives for generated applications.

Control flow (selection/iteration) lives ONLY here and in expr_runtime as
named, audited primitives. Domain parts and compose must not use if/for/while.
"""

from __future__ import annotations


def emit_event_runtime_module() -> str:
    """Self-contained event kernel. Functions + plain data. No user classes."""
    return '''"""L10 event runtime — audited deterministic control primitives.

Application/domain code must not use explicit if/for/while/match/comprehensions.
Selection and iteration exist only as these named primitives:

  route(thing)         — table lookup by event name
  emit(thing, event)   — set event + append evidence
  enqueue(thing, event)— append to deterministic queue
  until_quiet(thing)   — process queue until empty (audited loop)
  map_event(...)       — deterministic map over a collection via item events
  fold_event(...)      — deterministic fold/reduction via item events
  call_part(...)       — invoke a Part; unhandled exceptions → ticket path
  require_str_field(...)— audited field guard (Thing → Thing)
  open_ticket(thing)   — outward ticket boundary for unhandled exceptions
  preserve_for_retry(...)— local outbox when delivery fails
  ack_ticket(thing)    — acknowledge after external id

L8: no user-defined classes. L7: ticket outbox is an outward boundary.
L10 exception policy: unhandled → ticket.open; validation failures do not ticket.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


def _value(thing):
    return thing.get("value") if isinstance(thing.get("value"), dict) else {}


def _event_name(thing):
    v = _value(thing)
    return v.get("event") or thing.get("event") or "unknown"


def emit(thing, event, **extra):
    """Set current event and append evidence. Thing → Thing."""
    value = dict(_value(thing))
    value["event"] = event
    value.update(extra)
    evidence = tuple(thing.get("evidence") or ())
    return {
        **thing,
        "value": value,
        "evidence": (*evidence, f"event:{event}"),
        "state": thing.get("state", "formed"),
    }


def enqueue(thing, event):
    """Append event name to deterministic queue in the thing."""
    value = dict(_value(thing))
    queue = list(value.get("event_queue") or ())
    queue.append(event)
    value["event_queue"] = tuple(queue)
    evidence = tuple(thing.get("evidence") or ())
    return {
        **thing,
        "value": value,
        "evidence": (*evidence, f"event:enqueue:{event}"),
        "state": thing.get("state", "formed"),
    }


def dequeue(thing):
    """Pop next queued event into current event field. Empty → quiet."""
    value = dict(_value(thing))
    queue = list(value.get("event_queue") or ())
    empty = len(queue) == 0
    next_event = (queue or ["quiet"])[0]
    rest = tuple(queue[1:])
    value["event_queue"] = rest
    value["event"] = next_event
    evidence = tuple(thing.get("evidence") or ())
    mark = "event:quiet" if empty else f"event:dequeue:{next_event}"
    return {
        **thing,
        "value": value,
        "evidence": (*evidence, mark),
        "state": thing.get("state", "formed"),
    }


def unknown_event(thing):
    """Explicit invalid for unknown routes."""
    value = dict(_value(thing))
    ev = _event_name(thing)
    value["error"] = "unknown-event"
    value["event"] = "unknown.event"
    evidence = tuple(thing.get("evidence") or ())
    return {
        **thing,
        "value": value,
        "evidence": (*evidence, f"event:unknown:{ev}"),
        "state": "invalid",
    }


def route(thing, routes):
    """Declarative route table: EVENTS[event](thing). Unknown → invalid Thing."""
    handler = routes.get(_event_name(thing), unknown_event)
    return handler(thing)


def until_quiet(thing, routes, *, max_steps=10000):
    """Process event_queue until quiet or max_steps (audited loop primitive).

    This is the sole general-purpose iteration over application events.
    Recursion is not used as a loop substitute.
    """
    steps = 0
    current = thing
    value = dict(_value(current))
    queue = list(value.get("event_queue") or ())
    has_current = value.get("event") not in (None, "quiet", "")
    seed = (
        enqueue(current, value["event"])
        if (len(queue) == 0 and has_current)
        else current
    )
    current = seed
    while steps < max_steps:
        steps += 1
        current = dequeue(current)
        ev = _event_name(current)
        if ev == "quiet":
            return {
                **current,
                "evidence": (
                    *tuple(current.get("evidence") or ()),
                    "event:until_quiet:done",
                ),
            }
        try:
            current = route(current, routes)
        except Exception as exc:  # noqa: BLE001 — audited boundary
            current = _exception_thing(current, "route", exc)
            current = enqueue(current, "exception.unhandled")
    value = dict(_value(current))
    value["error"] = "event-overflow"
    value["event"] = "exception.unhandled"
    return {
        **current,
        "value": value,
        "evidence": (
            *tuple(current.get("evidence") or ()),
            "event:until_quiet:overflow",
        ),
        "state": "invalid",
    }


def map_event(thing, collection_key, item_event, routes):
    """Deterministic map: for each item emit item_event via routes (audited)."""
    value = dict(_value(thing))
    root = value.get("document") or value.get("root") or value
    collection = root.get(collection_key) if isinstance(root, dict) else None
    collection = collection if isinstance(collection, list) else []
    results = []
    index = 0
    while index < len(collection):
        item = collection[index]
        item_thing = {
            **thing,
            "value": {
                **value,
                "event": item_event,
                "item": item,
                "item_index": index,
            },
            "evidence": (
                *tuple(thing.get("evidence") or ()),
                f"event:map_item:{index}",
            ),
        }
        out = route(item_thing, routes)
        results.append(out)
        index += 1
    value["map_results"] = results
    value["event"] = "map.complete"
    return {
        **thing,
        "value": value,
        "evidence": (*tuple(thing.get("evidence") or ()), "event:map.complete"),
        "state": thing.get("state", "formed"),
    }


def fold_event(thing, collection_key, item_event, routes, initial):
    """Deterministic fold over a collection (audited loop primitive)."""
    value = dict(_value(thing))
    root = value.get("document") or value.get("root") or value
    collection = root.get(collection_key) if isinstance(root, dict) else None
    collection = collection if isinstance(collection, list) else []
    acc = initial
    index = 0
    while index < len(collection):
        item = collection[index]
        step = {
            **thing,
            "value": {
                **value,
                "event": item_event,
                "item": item,
                "item_index": index,
                "fold_acc": acc,
            },
            "evidence": (
                *tuple(thing.get("evidence") or ()),
                f"event:fold_item:{index}",
            ),
        }
        out = route(step, routes)
        acc = _value(out).get("fold_acc", acc)
        index += 1
    value["fold_result"] = acc
    value["event"] = "fold.complete"
    return {
        **thing,
        "value": value,
        "evidence": (*tuple(thing.get("evidence") or ()), "event:fold.complete"),
        "state": thing.get("state", "formed"),
    }


def call_part(thing, part, done_event):
    """Invoke a Part; domain validation stays on the thing; unhandled → ticket."""
    try:
        out = part(thing)
    except Exception as exc:  # noqa: BLE001
        bad = _exception_thing(thing, getattr(part, "__name__", "part"), exc)
        return enqueue(emit(bad, "exception.unhandled"), "exception.unhandled")
    return enqueue(emit(out, done_event), done_event)


def require_str_field(thing, name, field, missing_error="missing-text", invalid_error="invalid-text"):
    """Audited string-field guard used by generated domain parts (no if in domain)."""
    from .boundary import is_thing

    if not is_thing(thing):
        return {
            "value": thing,
            "depths": (),
            "axes": (),
            "evidence": (f"part:{name}", f"{name}:rejected-non-thing"),
            "state": "invalid",
        }
    if thing["state"] in {"invalid", "absent", "false", "unknown"}:
        return {
            **thing,
            "evidence": (*thing["evidence"], f"part:{name}", f"{name}:skipped"),
            "state": thing["state"],
        }
    value = thing["value"]
    if value is None:
        return {
            **thing,
            "evidence": (*thing["evidence"], f"part:{name}", f"{name}:absent"),
            "state": "absent",
        }
    if value is False:
        return {
            **thing,
            "evidence": (*thing["evidence"], f"part:{name}", f"{name}:false"),
            "state": "false",
        }
    if not isinstance(value, dict):
        return {
            **thing,
            "evidence": (*thing["evidence"], f"part:{name}", f"{name}:not-map"),
            "state": "invalid",
        }
    if "error" in value and field not in value:
        return {
            **thing,
            "evidence": (*thing["evidence"], f"part:{name}", f"{name}:prior-error"),
            "state": "invalid",
        }
    if field not in value:
        return {
            **thing,
            "value": {**value, "error": missing_error},
            "evidence": (*thing["evidence"], f"part:{name}", f"{name}:missing-{field}"),
            "state": "absent",
        }
    field_value = value[field]
    if field_value is None:
        return {
            **thing,
            "value": {**value, "error": missing_error},
            "evidence": (*thing["evidence"], f"part:{name}", f"{name}:absent-{field}"),
            "state": "absent",
        }
    if field_value is False:
        return {
            **thing,
            "value": {**value, "error": f"false-{field}"},
            "evidence": (*thing["evidence"], f"part:{name}", f"{name}:false-{field}"),
            "state": "false",
        }
    if not isinstance(field_value, str):
        return {
            **thing,
            "value": {**value, "error": invalid_error},
            "evidence": (*thing["evidence"], f"part:{name}", f"{name}:invalid-{field}"),
            "state": "invalid",
        }
    return {
        **thing,
        "evidence": (*thing["evidence"], f"part:{name}", f"{name}:ok"),
        "state": "formed",
    }


def identity_part(thing, name):
    """Identity feature body without domain branching."""
    from .boundary import is_thing

    if not is_thing(thing):
        return {
            "value": thing,
            "depths": (),
            "axes": (),
            "evidence": (f"part:{name}", f"{name}:rejected-non-thing"),
            "state": "invalid",
        }
    return {
        **thing,
        "evidence": (*thing["evidence"], f"part:{name}", f"{name}:ok"),
    }


def _redact(message):
    """Strip likely secrets from ticket messages (plain data transform)."""
    text = str(message)
    banned = ("password", "token", "secret", "authorization", "api_key", "apikey")
    lower = text.lower()
    marked = lower
    for word in banned:
        marked = marked.replace(word, "[redacted]")
    redacted = "[redacted]" in marked
    return "[redacted-message]" if redacted else text[:500]


def _correlation(evidence):
    raw = "|".join(str(x) for x in evidence[-8:])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _write_ticket_outbox(outbox_path, ticket):
    """Deterministic local ticket outbox (outward boundary)."""
    if not isinstance(ticket, dict):
        return False
    try:
        path = Path(outbox_path)
        path.mkdir(parents=True, exist_ok=True)
        cid = ticket.get("correlation_id") or "unknown"
        target = path / f"{cid}.json"
        if target.exists():
            return True
        target.write_text(
            json.dumps(ticket, ensure_ascii=False, indent=2, sort_keys=True) + "\\n",
            encoding="utf-8",
        )
        return True
    except OSError:
        return False


def _exception_thing(thing, operation, exc):
    value = dict(_value(thing))
    value["exception"] = {
        "operation": operation,
        "error_type": type(exc).__name__,
        "message": str(exc),
        "occurred_at": "static",
    }
    value["event"] = "exception.unhandled"
    evidence = tuple(thing.get("evidence") or ())
    return {
        **thing,
        "value": value,
        "evidence": (*evidence, f"event:exception.unhandled:{operation}"),
        "state": "invalid",
    }


def open_ticket(thing):
    """Outward ticket boundary: one ticket for unhandled exception."""
    value = dict(_value(thing))
    existing = value.get("ticket")
    has_ticket = existing is not None
    evidence = tuple(thing.get("evidence") or ())
    payload = value.get("exception") or {}
    correlation = value.get("correlation_id") or _correlation(evidence)
    ticket = {
        "kind": "unhandled-exception",
        "operation": str(
            payload.get("operation") or value.get("operation") or "unknown"
        ),
        "error_type": str(payload.get("error_type") or "Exception"),
        "message": _redact(payload.get("message") or value.get("error") or "unhandled"),
        "evidence": list(evidence[-20:]),
        "correlation_id": correlation,
        "occurred_at": str(payload.get("occurred_at") or "static"),
    }
    ticket_out = existing if has_ticket else ticket
    value["ticket"] = ticket_out
    value["event"] = "ticket.opened"
    outbox_path = value.get("ticket_outbox") or ".uc/tickets"
    written = _write_ticket_outbox(outbox_path, ticket_out)
    value["ticket_outbox_written"] = written
    return {
        **thing,
        "value": value,
        "evidence": (*evidence, "boundary:ticket.open", "event:ticket.opened"),
        "state": "invalid",
    }


def preserve_for_retry(thing):
    """Delivery failure: keep ticket in outbox (idempotent)."""
    value = dict(_value(thing))
    ticket = value.get("ticket")
    outbox_path = value.get("ticket_outbox") or ".uc/tickets"
    written = _write_ticket_outbox(outbox_path, ticket) if ticket else False
    value["event"] = "ticket.delivery_failed"
    value["ticket_outbox_written"] = written
    evidence = tuple(thing.get("evidence") or ())
    return {
        **thing,
        "value": value,
        "evidence": (*evidence, "event:ticket.delivery_failed"),
        "state": "invalid",
    }


def ack_ticket(thing):
    """Acknowledge only after external id is present."""
    value = dict(_value(thing))
    ticket = dict(value.get("ticket") or {})
    external_id = value.get("ticket_external_id") or ticket.get("external_id")
    has_id = external_id not in (None, "")
    ticket["external_id"] = external_id if has_id else ticket.get("external_id")
    ticket["acked"] = has_id
    value["ticket"] = ticket
    value["event"] = "ticket.acked" if has_id else "ticket.ack_pending"
    evidence = tuple(thing.get("evidence") or ())
    mark = "event:ticket.acked" if has_id else "event:ticket.ack_pending"
    return {
        **thing,
        "value": value,
        "evidence": (*evidence, mark),
        "state": thing.get("state", "invalid"),
    }


def fail_with_ticket(thing):
    """Terminal failure carrying ticket."""
    value = dict(_value(thing))
    value["event"] = "processing.failed"
    evidence = tuple(thing.get("evidence") or ())
    return {
        **thing,
        "value": value,
        "evidence": (*evidence, "event:processing.failed"),
        "state": "invalid",
    }
'''


def emit_event_compose(declaration: dict) -> str:
    """Compose module: ROUTES data + until_quiet — no if/for in this file."""
    features = [f["name"] for f in declaration["features"]]
    boundaries = [
        b["name"]
        for b in (declaration.get("boundaries") or ())
        if isinstance(b, dict) and "name" in b
    ]
    has_cli = bool(declaration.get("cli"))
    has_present = bool(declaration.get("presentation"))
    read_name = boundaries[0] if boundaries else None

    b_imports = ["inward", "outward"]
    if has_cli:
        b_imports.append("parse_host_argv")
    if read_name:
        b_imports.append(read_name)
    if has_present:
        b_imports.append("present_result")
    import_boundary = "from .boundary import " + ", ".join(b_imports)
    import_parts = (
        "from .parts import " + ", ".join(features)
        if features
        else "from . import parts  # noqa: F401"
    )

    # Pipeline events as pure data
    routes: list[tuple[str, str]] = [
        ('"program.start"', "on_program_start"),
        ('"step.inward"', "on_inward"),
    ]
    if has_cli:
        routes.append(('"step.parse"', "on_parse"))
    routes.append(('"step.letter"', "on_letter"))
    if read_name:
        routes.append(('"step.read"', "on_read"))
    for i, fname in enumerate(features):
        routes.append((f'"step.feature.{fname}"', f"on_feature_{fname}"))
    routes.append(('"step.verify"', "on_verify"))
    if has_present:
        routes.append(('"step.present"', "on_present"))
    routes.append(('"step.outward"', "on_outward"))
    routes.extend(
        [
            ('"validation.failed"', "on_reject"),
            ('"exception.unhandled"', "open_ticket"),
            ('"ticket.opened"', "fail_with_ticket"),
            ('"ticket.delivery_failed"', "preserve_for_retry"),
            ('"ticket.ack_requested"', "ack_ticket"),
            ('"processing.failed"', "on_failed"),
            ('"program.done"', "on_done"),
        ]
    )
    routes_lines = ",\n    ".join(f"{k}: {v}" for k, v in routes)

    # Build sequential next-event chain for handlers
    chain = ["step.inward"]
    if has_cli:
        chain.append("step.parse")
    chain.append("step.letter")
    if read_name:
        chain.append("step.read")
    for fname in features:
        chain.append(f"step.feature.{fname}")
    chain.append("step.verify")
    if has_present:
        chain.append("step.present")
    chain.append("step.outward")
    chain.append("program.done")

    def next_of(current: str) -> str:
        idx = chain.index(current)
        return chain[idx + 1] if idx + 1 < len(chain) else "program.done"

    handlers = []
    handlers.append(
        f'''
def on_program_start(thing):
    return enqueue(emit(thing, "step.inward"), "step.inward")
'''
    )
    handlers.append(
        f'''
def on_inward(thing):
    return enqueue(emit(inward(thing), "{next_of("step.inward")}"), "{next_of("step.inward")}")
'''
    )
    if has_cli:
        handlers.append(
            f'''
def on_parse(thing):
    return enqueue(emit(parse_host_argv(thing), "{next_of("step.parse")}"), "{next_of("step.parse")}")
'''
        )
    handlers.append(
        f'''
def on_letter(thing):
    from .core import letter
    return enqueue(emit(letter(thing), "{next_of("step.letter")}"), "{next_of("step.letter")}")
'''
    )
    if read_name:
        handlers.append(
            f'''
def on_read(thing):
    return enqueue(emit({read_name}(thing), "{next_of("step.read")}"), "{next_of("step.read")}")
'''
        )
    for fname in features:
        step = f"step.feature.{fname}"
        handlers.append(
            f'''
def on_feature_{fname}(thing):
    return call_part(thing, {fname}, "{next_of(step)}")
'''
        )
    handlers.append(
        f'''
def on_verify(thing):
    from .core import verify
    return enqueue(emit(verify(thing), "{next_of("step.verify")}"), "{next_of("step.verify")}")
'''
    )
    if has_present:
        handlers.append(
            f'''
def on_present(thing):
    return enqueue(emit(present_result(thing), "{next_of("step.present")}"), "{next_of("step.present")}")
'''
        )
    handlers.append(
        '''
def on_outward(thing):
    return enqueue(emit(outward(thing), "program.done"), "program.done")


def on_reject(thing):
    return enqueue(emit(thing, "program.done"), "program.done")


def on_failed(thing):
    return enqueue(emit(outward(thing), "program.done"), "program.done")


def on_done(thing):
    return emit(thing, "program.done")
'''
    )

    handler_block = "\n".join(handlers)

    return f'''"""L10 event-driven composition — routes as data, no if/for/while here."""

{import_boundary}
from .event_runtime import (
    ack_ticket,
    call_part,
    emit,
    enqueue,
    fail_with_ticket,
    open_ticket,
    preserve_for_retry,
    until_quiet,
)
{import_parts}

{handler_block}

ROUTES = {{
    {routes_lines}
}}


def program(thing):
    """Start event pipeline and process until quiet (Thing → Thing)."""
    started = enqueue(emit(thing, "program.start"), "program.start")
    return until_quiet(started, ROUTES)
'''
