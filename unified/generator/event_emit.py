"""Emit audited L10 event-runtime primitives for generated applications.

Control flow (selection/iteration) lives ONLY here and in expr_runtime as
named, *contract-tested* primitives. Domain parts and compose must not use
if/for/while.

“Audited” means: formal contract + direct tests for termination, ordering,
duplication, and failure — not merely a name.
"""

from __future__ import annotations


# Formal contracts embedded in generated runtime and mirrored in SPEC.md.
PRIMITIVE_CONTRACTS = r"""
L10 KERNEL CONTRACTS (audited = named + specified + tested)

emit(thing, event) -> thing
  - Sets value.event; appends evidence event:{name} in order.
  - Pure: no I/O.

enqueue(thing, event, event_id=None) -> thing
  - Appends {name, id} to value.event_queue (FIFO).
  - id defaults to deterministic hash(name, queue_len, seq).
  - Pure: no I/O.

dequeue(thing) -> thing
  - Pops FIFO head into value.event / value.event_id.
  - Empty queue => event "quiet" (queue exhaustion signal).
  - Pure: no I/O.

route(thing, routes) -> thing
  - handlers[event](thing); missing => unknown_event invalid Thing.
  - Does not catch handler exceptions (call_part / until_quiet do).

until_quiet(thing, routes, max_steps=DEFAULT_MAX_STEPS) -> thing
  - Processes queue until quiet OR step limit.
  - Queue exhaustion evidence: event:until_quiet:queue_exhausted
  - Limit exhaustion evidence: event:until_quiet:limit_exhausted
    (distinct; does NOT open a ticket).
  - Event identity: each event_id routed at most once per invocation;
    duplicates => event:duplicate-skipped (no re-route).
  - max_steps is finite and deterministic (default 10000).
  - No recursion as loop substitute.

map_event / fold_event
  - Deterministic index order 0..n-1; pure relative to routes.
  - Item event_id includes index to allow same event name per item.

call_part(thing, part, done_event) -> thing
  - Success => enqueue done_event.
  - Unhandled exception => exception payload + exception.unhandled
    (no domain vocabulary; no I/O).

construct_ticket(thing) -> thing
  - PURE: builds ticket object; redacts BEFORE ticket fields and evidence.
  - Ticket identity = correlation_id derived deterministically from failure
    (operation|error_type|redacted_message|evidence_tail).
  - One logical ticket: existing ticket with same id kept.
  - Emits event ticket.persist.requested (no filesystem write).

outward_ticket_store(thing) -> thing
  - OUTWARD boundary: atomic persist of already-constructed ticket.
  - Success => ticket.persisted.
  - Failure => ticket.persist.failed + emergency result;
    MUST NOT construct/open another ticket (no recursion).

reload_unacked_tickets(thing) -> thing
  - OUTWARD read: loads outbox entries without acked=true into value.
  - Restart path for unacknowledged work.

ack_ticket(thing) -> thing
  - acked=true only if external_id is a non-empty str (real provider id).
  - Otherwise ticket.ack_pending.

fail_with_ticket(thing) -> thing
  - Terminal processing.failed carrying ticket; pure.

emergency_persist_result(thing) -> thing
  - Observable failure of ticket write; no new ticket construction.

Domain vocabulary is forbidden in this module body (no app field names).
"""


def emit_event_runtime_module() -> str:
    """Self-contained event kernel. Functions + plain data. No user classes."""
    return '''"""L10 event runtime — contract-tested deterministic control primitives.

Application/domain code must not use explicit if/for/while/match/comprehensions.
Selection and iteration exist only as these audited primitives (see CONTRACTS).

Audited means: formal contract + tests for termination, ordering, duplication,
and failure — not merely a function name.

L8: no user-defined classes.
L7: only outward_ticket_store / reload_unacked_tickets perform ticket I/O.
L10: construct_ticket is pure; persistence is a separate outward boundary.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

# --- contracts (machine-readable summary) ---
DEFAULT_MAX_STEPS = 10000
CONTRACTS = """
emit enqueue dequeue route until_quiet map_event fold_event call_part
construct_ticket outward_ticket_store reload_unacked_tickets ack_ticket
fail_with_ticket emergency_persist_result
queue_exhausted != limit_exhausted
event identity prevents duplicate route
ticket identity = deterministic correlation_id
redaction before persist and evidence
persist failure => emergency, not recursive ticket
ack requires non-empty external_id
"""


def _value(thing):
    return thing.get("value") if isinstance(thing.get("value"), dict) else {}


def _event_name(thing):
    v = _value(thing)
    return v.get("event") or thing.get("event") or "unknown"


def _event_id_of(thing):
    v = _value(thing)
    return v.get("event_id") or _event_name(thing)


def _make_event_id(name, seq, salt=""):
    raw = f"{name}|{seq}|{salt}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def emit(thing, event, **extra):
    """Set current event and append evidence. Pure. Thing → Thing."""
    value = dict(_value(thing))
    value["event"] = event
    if "event_id" not in extra and "event_id" not in value:
        seq = int(value.get("event_seq") or 0)
        value["event_id"] = _make_event_id(event, seq)
        value["event_seq"] = seq + 1
    value.update(extra)
    evidence = tuple(thing.get("evidence") or ())
    return {
        **thing,
        "value": value,
        "evidence": (*evidence, f"event:{event}"),
        "state": thing.get("state", "formed"),
    }


def enqueue(thing, event, event_id=None):
    """Append named event with identity to deterministic FIFO queue. Pure."""
    value = dict(_value(thing))
    queue = list(value.get("event_queue") or ())
    seq = int(value.get("event_seq") or 0)
    eid = event_id or _make_event_id(event, seq, salt=str(len(queue)))
    queue.append({"name": event, "id": eid})
    value["event_queue"] = tuple(queue)
    value["event_seq"] = seq + 1
    evidence = tuple(thing.get("evidence") or ())
    return {
        **thing,
        "value": value,
        "evidence": (*evidence, f"event:enqueue:{event}"),
        "state": thing.get("state", "formed"),
    }


def dequeue(thing):
    """Pop next queued event. Empty → quiet (queue exhaustion). Pure."""
    value = dict(_value(thing))
    queue = list(value.get("event_queue") or ())
    empty = len(queue) == 0
    if empty:
        next_name, next_id = "quiet", "quiet"
        rest = ()
    else:
        head = queue[0]
        rest = tuple(queue[1:])
        if isinstance(head, dict):
            next_name = head.get("name") or "unknown"
            next_id = head.get("id") or next_name
        else:
            next_name = str(head)
            next_id = str(head)
    value["event_queue"] = rest
    value["event"] = next_name
    value["event_id"] = next_id
    evidence = tuple(thing.get("evidence") or ())
    mark = "event:quiet" if empty else f"event:dequeue:{next_name}"
    return {
        **thing,
        "value": value,
        "evidence": (*evidence, mark),
        "state": thing.get("state", "formed"),
    }


def unknown_event(thing):
    """Explicit invalid for unknown routes. Pure."""
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
    """Declarative route table. Unknown → invalid Thing. Pure (no catch)."""
    handler = routes.get(_event_name(thing), unknown_event)
    return handler(thing)


def until_quiet(thing, routes, max_steps=None):
    """Process event_queue until quiet or step limit (audited loop).

    Contracts:
      - max_steps defaults to DEFAULT_MAX_STEPS (deterministic finite bound).
      - Queue exhaustion ≠ limit exhaustion (distinct evidence marks).
      - Each event_id is routed at most once; duplicates are skipped.
      - Limit exhaustion does not open a ticket.
      - No recursion.
    """
    limit = DEFAULT_MAX_STEPS if max_steps is None else int(max_steps)
    steps = 0
    current = thing
    value = dict(_value(current))
    queue = list(value.get("event_queue") or ())
    has_current = value.get("event") not in (None, "quiet", "")
    if len(queue) == 0 and has_current:
        current = enqueue(current, value["event"], event_id=value.get("event_id"))
    processed = set(value.get("processed_event_ids") or ())
    while steps < limit:
        steps += 1
        current = dequeue(current)
        ev = _event_name(current)
        eid = _event_id_of(current)
        if ev == "quiet":
            v = dict(_value(current))
            v["processed_event_ids"] = tuple(sorted(processed))
            v["until_quiet_end"] = "queue_exhausted"
            v["until_quiet_steps"] = steps
            return {
                **current,
                "value": v,
                "evidence": (
                    *tuple(current.get("evidence") or ()),
                    "event:until_quiet:queue_exhausted",
                    "event:until_quiet:done",
                ),
            }
        if eid in processed:
            current = {
                **current,
                "evidence": (
                    *tuple(current.get("evidence") or ()),
                    f"event:duplicate-skipped:{eid}",
                ),
            }
            continue
        processed.add(eid)
        try:
            current = route(current, routes)
        except Exception as exc:  # noqa: BLE001 — audited catch
            current = _exception_thing(current, "route", exc)
            current = enqueue(current, "exception.unhandled")
        # refresh processed into value for observability
        v = dict(_value(current))
        v["processed_event_ids"] = tuple(sorted(processed))
        current = {**current, "value": v}
    # limit exhaustion — distinct from queue quiet; no ticket
    value = dict(_value(current))
    value["error"] = "event-step-limit"
    value["event"] = "until_quiet.limit_exhausted"
    value["until_quiet_end"] = "limit_exhausted"
    value["until_quiet_steps"] = steps
    value["processed_event_ids"] = tuple(sorted(processed))
    return {
        **current,
        "value": value,
        "evidence": (
            *tuple(current.get("evidence") or ()),
            "event:until_quiet:limit_exhausted",
        ),
        "state": "invalid",
    }


def map_event(thing, collection_key, item_event, routes):
    """Deterministic map over a list under root[collection_key]."""
    value = dict(_value(thing))
    root = value.get("root") if isinstance(value.get("root"), dict) else value
    collection = root.get(collection_key) if isinstance(root, dict) else None
    collection = collection if isinstance(collection, list) else []
    results = []
    index = 0
    while index < len(collection):
        item = collection[index]
        item_id = _make_event_id(item_event, index, salt="map")
        item_thing = {
            **thing,
            "value": {
                **value,
                "event": item_event,
                "event_id": item_id,
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
    """Deterministic fold over a list under root[collection_key]."""
    value = dict(_value(thing))
    root = value.get("root") if isinstance(value.get("root"), dict) else value
    collection = root.get(collection_key) if isinstance(root, dict) else None
    collection = collection if isinstance(collection, list) else []
    acc = initial
    index = 0
    while index < len(collection):
        item = collection[index]
        item_id = _make_event_id(item_event, index, salt="fold")
        step = {
            **thing,
            "value": {
                **value,
                "event": item_event,
                "event_id": item_id,
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
    """Invoke a Part; unhandled exception → exception.unhandled (no I/O)."""
    try:
        out = part(thing)
    except Exception as exc:  # noqa: BLE001
        bad = _exception_thing(thing, getattr(part, "__name__", "part"), exc)
        return enqueue(emit(bad, "exception.unhandled"), "exception.unhandled")
    return enqueue(emit(out, done_event), done_event)


def require_str_field(
    thing, name, field, missing_error="missing-field", invalid_error="invalid-field"
):
    """Audited string-field guard (generic; callers supply field/errors)."""
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
    """Redact secrets before any ticket field or evidence may record them."""
    text = str(message)
    banned = ("password", "token", "secret", "authorization", "api_key", "apikey")
    lower = text.lower()
    marked = lower
    for word in banned:
        marked = marked.replace(word, "[redacted]")
    if "[redacted]" in marked:
        return "[redacted-message]"
    return text[:500]


def _correlation_from_failure(operation, error_type, redacted_message, evidence):
    """Deterministic ticket identity from failure material (already redacted)."""
    raw = "|".join(
        [
            str(operation),
            str(error_type),
            str(redacted_message),
            "|".join(str(x) for x in (evidence or ())[-8:]),
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _exception_thing(thing, operation, exc):
    value = dict(_value(thing))
    # redact at the moment of capture — before ticket construct/evidence
    redacted = _redact(str(exc))
    value["exception"] = {
        "operation": str(operation),
        "error_type": type(exc).__name__,
        "message": redacted,
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


def construct_ticket(thing):
    """PURE: build redacted ticket; request persist. No filesystem I/O.

    event chain: exception.unhandled → ticket.persist.requested
    """
    value = dict(_value(thing))
    existing = value.get("ticket")
    evidence = tuple(thing.get("evidence") or ())
    payload = value.get("exception") or {}
    operation = str(payload.get("operation") or value.get("operation") or "unknown")
    error_type = str(payload.get("error_type") or "Exception")
    # redaction BEFORE ticket fields and any further evidence
    raw_message = payload.get("message") or value.get("error") or "unhandled"
    redacted_message = _redact(raw_message)
    correlation = _correlation_from_failure(
        operation, error_type, redacted_message, evidence
    )
    ticket = {
        "kind": "unhandled-exception",
        "operation": operation,
        "error_type": error_type,
        "message": redacted_message,
        "evidence": list(evidence[-20:]),
        "correlation_id": correlation,
        "ticket_id": correlation,
        "occurred_at": str(payload.get("occurred_at") or "static"),
        "acked": False,
    }
    # one failure → one ticket identity
    if isinstance(existing, dict) and existing.get("correlation_id") == correlation:
        ticket_out = existing
    elif isinstance(existing, dict) and existing.get("ticket_id"):
        ticket_out = existing
    else:
        ticket_out = ticket
    value["ticket"] = ticket_out
    value["correlation_id"] = ticket_out.get("correlation_id") or correlation
    value["event"] = "ticket.persist.requested"
    built = {
        **thing,
        "value": value,
        "evidence": (
            *evidence,
            "event:ticket.construct",
            "event:ticket.persist.requested",
        ),
        "state": "invalid",
    }
    # continue pipeline: request persist as next queue event
    return enqueue(built, "ticket.persist.requested")


def outward_ticket_store(thing):
    """OUTWARD boundary: atomic persist of constructed ticket.

    Success → ticket.persisted.
    Failure → ticket.persist.failed + emergency (never recursive ticket).
    """
    value = dict(_value(thing))
    ticket = value.get("ticket")
    evidence = tuple(thing.get("evidence") or ())
    if not isinstance(ticket, dict):
        return enqueue(
            emergency_persist_result(
                {
                    **thing,
                    "value": {
                        **value,
                        "event": "ticket.persist.failed",
                        "emergency": {
                            "kind": "ticket-persist-failed",
                            "reason": "missing-ticket",
                        },
                    },
                    "evidence": (*evidence, "boundary:ticket.persist"),
                    "state": "invalid",
                }
            ),
            "ticket.persist.failed",
        )
    # ensure message already redacted (defense in depth)
    ticket = dict(ticket)
    ticket["message"] = _redact(ticket.get("message") or "")
    value["ticket"] = ticket
    outbox_path = value.get("ticket_outbox") or ".uc/tickets"
    written = _atomic_write_ticket(outbox_path, ticket)
    if written:
        value["event"] = "ticket.persisted"
        value["ticket_outbox_written"] = True
        out = {
            **thing,
            "value": value,
            "evidence": (
                *evidence,
                "boundary:ticket.persist",
                "event:ticket.persisted",
            ),
            "state": "invalid",
        }
        return enqueue(out, "ticket.persisted")
    # failed write — emergency, do NOT construct another ticket
    value["event"] = "ticket.persist.failed"
    value["ticket_outbox_written"] = False
    value["emergency"] = {
        "kind": "ticket-persist-failed",
        "reason": "write-failed",
        "correlation_id": ticket.get("correlation_id"),
    }
    out = {
        **thing,
        "value": value,
        "evidence": (
            *evidence,
            "boundary:ticket.persist",
            "event:ticket.persist.failed",
            "emergency:ticket-persist-failed",
        ),
        "state": "invalid",
    }
    return enqueue(out, "ticket.persist.failed")


def emergency_persist_result(thing):
    """Terminal observable emergency for persist failure. No new ticket."""
    value = dict(_value(thing))
    value["event"] = "ticket.persist.failed"
    if "emergency" not in value:
        value["emergency"] = {
            "kind": "ticket-persist-failed",
            "reason": "emergency",
            "correlation_id": (value.get("ticket") or {}).get("correlation_id"),
        }
    evidence = tuple(thing.get("evidence") or ())
    return {
        **thing,
        "value": value,
        "evidence": (*evidence, "event:emergency:ticket-persist-failed"),
        "state": "invalid",
    }


def preserve_for_retry(thing):
    """Re-request persist of existing ticket (idempotent; no reconstruct)."""
    value = dict(_value(thing))
    value["event"] = "ticket.persist.requested"
    evidence = tuple(thing.get("evidence") or ())
    out = {
        **thing,
        "value": value,
        "evidence": (
            *evidence,
            "event:ticket.delivery_failed",
            "event:ticket.persist.requested",
        ),
        "state": "invalid",
    }
    return enqueue(out, "ticket.persist.requested")


def reload_unacked_tickets(thing):
    """OUTWARD read: load unacked tickets from outbox for restart."""
    value = dict(_value(thing))
    outbox_path = value.get("ticket_outbox") or ".uc/tickets"
    loaded = _load_unacked(outbox_path)
    value["unacked_tickets"] = loaded
    value["event"] = "ticket.reload.done"
    evidence = tuple(thing.get("evidence") or ())
    return {
        **thing,
        "value": value,
        "evidence": (
            *evidence,
            "boundary:ticket.reload",
            f"event:ticket.reload:{len(loaded)}",
        ),
        "state": thing.get("state", "formed"),
    }


def ack_ticket(thing):
    """Acknowledge only when a real non-empty external ticket id is present."""
    value = dict(_value(thing))
    ticket = dict(value.get("ticket") or {})
    external_id = value.get("ticket_external_id") or ticket.get("external_id")
    # real external id: non-empty string (not bool/int zero masquerading)
    has_id = isinstance(external_id, str) and len(external_id.strip()) > 0
    if has_id:
        ticket["external_id"] = external_id.strip()
        ticket["acked"] = True
        value["event"] = "ticket.acked"
        mark = "event:ticket.acked"
    else:
        ticket["acked"] = False
        value["event"] = "ticket.ack_pending"
        mark = "event:ticket.ack_pending"
    value["ticket"] = ticket
    evidence = tuple(thing.get("evidence") or ())
    # also update outbox ack flag if possible (best-effort outward)
    outbox_path = value.get("ticket_outbox") or ".uc/tickets"
    if has_id and ticket.get("correlation_id"):
        _atomic_write_ticket(outbox_path, ticket)
    return {
        **thing,
        "value": value,
        "evidence": (*evidence, mark),
        "state": thing.get("state", "invalid"),
    }


def fail_with_ticket(thing):
    """Terminal processing.failed carrying ticket. Pure (no further enqueue)."""
    value = dict(_value(thing))
    value["event"] = "processing.failed"
    evidence = tuple(thing.get("evidence") or ())
    return {
        **thing,
        "value": value,
        "evidence": (*evidence, "event:processing.failed"),
        "state": "invalid",
    }


# Back-compat name: pure construct only (does not persist).
def open_ticket(thing):
    """Deprecated alias: construct_ticket only. Persistence is separate."""
    return construct_ticket(thing)


def _atomic_write_ticket(outbox_path, ticket):
    """Atomic persist: write temp file then os.replace. Returns bool.

    Same correlation_id always maps to one file; content is replaced atomically
    so ack updates are visible to reload_unacked_tickets.
    """
    if not isinstance(ticket, dict):
        return False
    try:
        path = Path(outbox_path)
        path.mkdir(parents=True, exist_ok=True)
        cid = ticket.get("correlation_id") or ticket.get("ticket_id") or "unknown"
        target = path / f"{cid}.json"
        tmp = path / f".{cid}.json.tmp"
        payload = json.dumps(ticket, ensure_ascii=False, indent=2, sort_keys=True) + "\\n"
        fd = os.open(str(tmp), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        try:
            os.write(fd, payload.encode("utf-8"))
            os.fsync(fd)
        finally:
            os.close(fd)
        os.replace(str(tmp), str(target))
        return True
    except OSError:
        return False


def _load_unacked(outbox_path):
    """Load tickets from outbox that are not acked."""
    path = Path(outbox_path)
    if not path.is_dir():
        return []
    loaded = []
    try:
        names = sorted(path.glob("*.json"))
    except OSError:
        return []
    index = 0
    while index < len(names):
        fpath = names[index]
        index += 1
        try:
            data = json.loads(fpath.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict) and not data.get("acked"):
            loaded.append(data)
    return loaded
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

    routes: list[tuple[str, str]] = [
        ('"program.start"', "on_program_start"),
        ('"step.inward"', "on_inward"),
    ]
    if has_cli:
        routes.append(('"step.parse"', "on_parse"))
    routes.append(('"step.letter"', "on_letter"))
    if read_name:
        routes.append(('"step.read"', "on_read"))
    for fname in features:
        routes.append((f'"step.feature.{fname}"', f"on_feature_{fname}"))
    routes.append(('"step.verify"', "on_verify"))
    if has_present:
        routes.append(('"step.present"', "on_present"))
    routes.append(('"step.outward"', "on_outward"))
    routes.extend(
        [
            ('"validation.failed"', "on_reject"),
            # L10 ticket chain: construct (pure) → persist (outward) → failed
            ('"exception.unhandled"', "construct_ticket"),
            ('"ticket.persist.requested"', "outward_ticket_store"),
            ('"ticket.persisted"', "fail_with_ticket"),
            ('"ticket.persist.failed"', "emergency_persist_result"),
            ('"ticket.delivery_failed"', "preserve_for_retry"),
            ('"ticket.ack_requested"', "ack_ticket"),
            ('"processing.failed"', "on_failed"),
            ('"program.done"', "on_done"),
        ]
    )
    routes_lines = ",\n    ".join(f"{k}: {v}" for k, v in routes)

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
        '''
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
    construct_ticket,
    emit,
    emergency_persist_result,
    enqueue,
    fail_with_ticket,
    outward_ticket_store,
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
