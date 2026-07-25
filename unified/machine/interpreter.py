"""UEM-16 interpreter — linear program + audited dispatch table."""

from __future__ import annotations

import hashlib

from .opcodes import DEFAULT_LIMITS, NAME_TO_BYTE
from .primitives import apply_primitive, construct_ticket_from_fault, registry
from .thing import approx_size, blank_thing, deep_copy_data, value_of, with_evidence, with_state


def machine_load(thing):
    """Load decoded instructions + image + host_input into runnable machine."""
    value = dict(value_of(thing))
    instructions = value.get("instructions")
    if not isinstance(instructions, (list, tuple)):
        return with_state(with_evidence(thing, "load:no-instructions"), "invalid")
    image = deep_copy_data(value.get("image") or {})
    limits = dict(DEFAULT_LIMITS)
    limits.update(value.get("limits") or {})
    limits["steps"] = 0
    limits["depth"] = 0
    machine = {
        "pc": 0,
        "instructions": tuple(
            (a, b) for a, b in instructions
        ),
        "store": {},
        "event": None,
        "event_id": None,
        "event_queue": (),
        "event_seq": 0,
        "processed_event_ids": (),
        "routes": dict(image.get("routes") or {}),
        "pending_primitive": None,
        "outward_request": None,
        "outward_result": value.get("outward_result"),
        "ticket": None,
        "halted": False,
        "stop_reason": None,
        "result": None,
        "limits": limits,
        "image": image,
        "program_sha256": value.get("program_sha256"),
        "host_input": value.get("host_input"),
        "machine_fault": None,
        "_acc": None,
        "instruction_count": len(instructions),
        "event_count": 0,
        "outward_log": [],
        "events_emitted": [],
        "events_dequeued": [],
    }
    # Fresh evidence for a run — compile/encode marks are not execution evidence.
    return {
        **thing,
        "value": machine,
        "evidence": ("machine:load",),
        "state": "formed",
    }


def machine_step(thing):
    """Execute one instruction. Thing → Thing."""
    if thing.get("state") == "invalid" and value_of(thing).get("halted"):
        return thing
    v = dict(value_of(thing))
    if v.get("halted"):
        return with_state(
            with_evidence(thing, "execution-after-stop"),
            "invalid",
        )
    # pending outward — host must fulfill before continuing
    if v.get("outward_request") is not None and v.get("outward_result") is None:
        return with_evidence(thing, "machine:await-outward")

    limits = dict(v.get("limits") or DEFAULT_LIMITS)
    if limits.get("steps", 0) >= limits.get("max_steps", DEFAULT_LIMITS["max_steps"]):
        return _limit_stop(thing, v, "steps")

    instructions = v.get("instructions") or ()
    pc = int(v.get("pc") or 0)
    if pc < 0 or pc >= len(instructions):
        return _fault(thing, v, "pc", "pc-out-of-range")

    opcode, operand = instructions[pc]
    limits["steps"] = int(limits.get("steps") or 0) + 1
    v["limits"] = limits
    v["pc"] = pc + 1
    evidence_mark = f"op:{opcode}" if operand is None else f"op:{opcode}:{operand}"

    dispatch = _dispatch_table()
    if opcode not in dispatch:
        return with_state(
            with_evidence({**thing, "value": v}, f"unknown-opcode:{opcode}"),
            "invalid",
        )
    try:
        nxt = dispatch[opcode]({**thing, "value": v}, operand)
    except Exception as exc:  # noqa: BLE001
        bad = dict(value_of({**thing, "value": v}))
        bad["machine_fault"] = {
            "operation": opcode,
            "error_type": type(exc).__name__,
            "message": str(exc),
        }
        return with_state(
            with_evidence({**thing, "value": bad}, "machine:fault", evidence_mark),
            "invalid",
        )
    # memory limit
    nv = value_of(nxt)
    size = approx_size(nv.get("store")) + approx_size(nv.get("event_queue"))
    lim = dict(nv.get("limits") or {})
    if size > lim.get("max_memory", DEFAULT_LIMITS["max_memory"]):
        return _limit_stop(nxt, dict(nv), "memory")
    return with_evidence(nxt, evidence_mark)


# Machine run loop bound. Exposed for tests that assert the steps-limit path.
MACHINE_RUN_GUARD = 200_000


def machine_run(thing):
    """Run until halt, outward wait, or invalid terminal. Does not fulfill outward."""
    current = thing
    guard = 0
    max_guard = MACHINE_RUN_GUARD
    while guard < max_guard:
        guard += 1
        v = value_of(current)
        if v.get("halted"):
            return current
        if current.get("state") == "invalid" and v.get("stop_reason"):
            return current
        if v.get("outward_request") is not None and v.get("outward_result") is None:
            return current
        if current.get("state") == "invalid" and v.get("machine_fault") and not v.get("ticket"):
            # leave for TICKET instruction or auto-ticket if halted mid-fault
            stepped = machine_step(current)
            return stepped
        current = machine_step(current)
        if current.get("state") == "invalid" and not value_of(current).get("halted"):
            # continue only if still runnable; validation invalid may still STOP
            v2 = value_of(current)
            if v2.get("pc", 0) >= len(v2.get("instructions") or ()):
                return current
    return _limit_stop(current, dict(value_of(current)), "steps")


def _dispatch_table():
    return {
        "LOAD": _op_load,
        "READ": _op_read,
        "WRITE": _op_write,
        "DELETE": _op_delete,
        "EMIT": _op_emit,
        "ENQUEUE": _op_enqueue,
        "DEQUEUE": _op_dequeue,
        "ROUTE": _op_route,
        "APPLY": _op_apply,
        "MAP": _op_map,
        "FOLD": _op_fold,
        "VERIFY": _op_verify,
        "TICKET": _op_ticket,
        "OUTWARD": _op_outward,
        "ACK": _op_ack,
        "STOP": _op_stop,
    }


def _op_load(thing, operand):
    v = dict(value_of(thing))
    store = dict(v.get("store") or {})
    if operand == "host_input" or operand is None:
        v["_acc"] = deep_copy_data(v.get("host_input"))
        store["host"] = deep_copy_data(v.get("host_input"))
    elif operand.startswith("image:"):
        key = operand[6:]
        v["_acc"] = deep_copy_data((v.get("image") or {}).get(key))
    else:
        v["_acc"] = deep_copy_data(store.get(operand))
    v["store"] = store
    return {**thing, "value": v}


def _op_read(thing, operand):
    v = dict(value_of(thing))
    store = v.get("store") or {}
    v["_acc"] = _path_get(store, operand or "")
    return {**thing, "value": v}


def _op_write(thing, operand):
    v = dict(value_of(thing))
    store = dict(v.get("store") or {})
    _path_set(store, operand or "_acc", v.get("_acc"))
    v["store"] = store
    return {**thing, "value": v}


def _op_delete(thing, operand):
    v = dict(value_of(thing))
    store = dict(v.get("store") or {})
    _path_delete(store, operand or "")
    v["store"] = store
    return {**thing, "value": v}


def _op_emit(thing, operand):
    v = dict(value_of(thing))
    name = operand or "event"
    seq = int(v.get("event_seq") or 0)
    eid = _event_id(name, seq)
    v["event"] = name
    v["event_id"] = eid
    v["event_seq"] = seq + 1
    v["event_count"] = int(v.get("event_count") or 0) + 1
    emitted = list(v.get("events_emitted") or ())
    emitted.append(name)
    v["events_emitted"] = emitted
    return with_evidence({**thing, "value": v}, f"event:{name}")


def _op_enqueue(thing, operand):
    v = dict(value_of(thing))
    name = operand or v.get("event") or "event"
    queue = list(v.get("event_queue") or ())
    limits = v.get("limits") or {}
    if len(queue) >= limits.get("max_queue", DEFAULT_LIMITS["max_queue"]):
        return _limit_stop(thing, v, "queue")
    seq = int(v.get("event_seq") or 0)
    eid = v.get("event_id") or _event_id(name, seq)
    queue.append({"name": name, "id": eid})
    v["event_queue"] = tuple(queue)
    v["event_seq"] = seq + 1
    return with_evidence({**thing, "value": v}, f"event:enqueue:{name}")


def _op_dequeue(thing, operand):
    v = dict(value_of(thing))
    queue = list(v.get("event_queue") or ())
    if not queue:
        v["event"] = "quiet"
        v["event_id"] = "quiet"
        return with_evidence({**thing, "value": v}, "event:quiet")
    head = queue[0]
    rest = tuple(queue[1:])
    if isinstance(head, dict):
        name, eid = head.get("name"), head.get("id")
    else:
        name, eid = str(head), str(head)
    v["event_queue"] = rest
    v["event"] = name
    v["event_id"] = eid
    deq = list(v.get("events_dequeued") or ())
    deq.append(name)
    v["events_dequeued"] = deq
    return with_evidence({**thing, "value": v}, f"event:dequeue:{name}")


def _op_route(thing, operand):
    v = dict(value_of(thing))
    routes = v.get("routes") or (v.get("image") or {}).get("routes") or {}
    if operand:
        routes = (v.get("store") or {}).get(operand) or routes
    ev = v.get("event")
    if ev not in routes:
        v["error"] = "unknown-route"
        return with_state(
            with_evidence({**thing, "value": v}, f"event:unknown:{ev}"),
            "invalid",
        )
    v["pending_primitive"] = routes[ev]
    v["routes"] = routes
    return {**thing, "value": v}


def _op_apply(thing, operand):
    v = dict(value_of(thing))
    # skip duplicate event ids
    eid = v.get("event_id")
    processed = set(v.get("processed_event_ids") or ())
    if eid and eid in processed and v.get("event") not in (None, "quiet"):
        return with_evidence(thing, f"event:duplicate-skipped:{eid}")
    name = operand or v.get("pending_primitive")
    if not name:
        return with_state(
            with_evidence({**thing, "value": v}, "apply:missing-primitive"),
            "invalid",
        )
    if name not in registry():
        return with_state(
            with_evidence({**thing, "value": v}, f"primitive:unknown:{name}"),
            "invalid",
        )
    out = apply_primitive({**thing, "value": v}, name)
    ov = dict(value_of(out))
    if eid:
        processed.add(eid)
        ov["processed_event_ids"] = tuple(sorted(processed))
    ov["pending_primitive"] = None
    # escalate machine_fault
    if ov.get("machine_fault") and not ov.get("ticket"):
        return {**out, "value": ov}
    return {**out, "value": ov}


def _op_map(thing, operand):
    v = dict(value_of(thing))
    cfg = (v.get("image") or {}).get(operand or "map") or {}
    collection_key = cfg.get("collection_key") or "items"
    prim = cfg.get("primitive") or "identity"
    store = v.get("store") or {}
    root = store.get("document") if isinstance(store.get("document"), dict) else store
    collection = root.get(collection_key) if isinstance(root, dict) else None
    collection = collection if isinstance(collection, list) else []
    limits = v.get("limits") or {}
    if len(collection) > limits.get("max_items", DEFAULT_LIMITS["max_items"]):
        return _limit_stop(thing, v, "items")
    results = []
    index = 0
    current = {**thing, "value": v}
    while index < len(collection):
        item = collection[index]
        sv = dict(value_of(current))
        st = dict(sv.get("store") or {})
        st["item"] = item
        st["item_index"] = index
        sv["store"] = st
        step = apply_primitive({**current, "value": sv}, prim)
        results.append(value_of(step).get("_acc"))
        current = step
        index += 1
    nv = dict(value_of(current))
    nv["_acc"] = results
    return with_evidence({**current, "value": nv}, "map:complete")


def _op_fold(thing, operand):
    v = dict(value_of(thing))
    cfg = (v.get("image") or {}).get(operand or "fold") or {}
    collection_key = cfg.get("collection_key") or "items"
    prim = cfg.get("primitive") or "identity"
    initial = cfg.get("initial")
    store = v.get("store") or {}
    root = store.get("document") if isinstance(store.get("document"), dict) else store
    collection = root.get(collection_key) if isinstance(root, dict) else None
    collection = collection if isinstance(collection, list) else []
    acc = initial
    index = 0
    current = {**thing, "value": v}
    while index < len(collection):
        item = collection[index]
        sv = dict(value_of(current))
        st = dict(sv.get("store") or {})
        st["item"] = item
        st["item_index"] = index
        st["fold_acc"] = acc
        sv["store"] = st
        step = apply_primitive({**current, "value": sv}, prim)
        acc = value_of(step).get("_acc", acc)
        current = step
        index += 1
    nv = dict(value_of(current))
    nv["_acc"] = acc
    return with_evidence({**current, "value": nv}, "fold:complete")


def _op_verify(thing, operand):
    # VERIFY uses verify_result primitive with image config
    return apply_primitive(thing, "verify_result")


def _op_ticket(thing, operand):
    return construct_ticket_from_fault(thing)


def _op_outward(thing, operand):
    v = dict(value_of(thing))
    effect = operand or "effect"
    image = v.get("image") or {}
    boundary = image.get("boundary") or {}
    store = v.get("store") or {}
    source_field = boundary.get("source_field") or "source"
    request = {
        "effect": effect,
        "source": store.get(source_field),
        "config": boundary,
    }
    v["outward_request"] = request
    # clear previous result to force host fill
    if v.get("outward_result") is not None and not v.get("_outward_auto"):
        pass
    return with_evidence({**thing, "value": v}, f"outward:request:{effect}")


def _op_ack(thing, operand):
    v = dict(value_of(thing))
    ticket = dict(v.get("ticket") or {})
    external_id = v.get("ticket_external_id") or ticket.get("external_id")
    has_id = isinstance(external_id, str) and len(external_id.strip()) > 0
    if has_id:
        ticket["external_id"] = external_id.strip()
        ticket["acked"] = True
        mark = "event:ticket.acked"
    else:
        ticket["acked"] = False
        mark = "event:ticket.ack_pending"
    v["ticket"] = ticket
    return with_evidence({**thing, "value": v}, mark)


def _op_stop(thing, operand):
    v = dict(value_of(thing))
    v["halted"] = True
    v["stop_reason"] = operand or "stop"
    store = v.get("store") or {}
    v["result"] = store.get("presentation") or store.get("result") or v.get("_acc")
    # terminal state: keep valid if verify passed
    state = thing.get("state")
    if state not in {"valid", "invalid", "absent", "false"}:
        state = "formed"
    # step wrapper appends op:STOP once
    return with_state({**thing, "value": v}, state)


def _limit_stop(thing, v, kind):
    v = dict(v)
    v["halted"] = True
    v["stop_reason"] = f"limit:{kind}"
    v["error"] = f"limit:{kind}"
    return with_state(
        with_evidence({**thing, "value": v}, f"limit:{kind}"),
        "invalid",
    )


def _fault(thing, v, operation, message):
    v = dict(v)
    v["machine_fault"] = {
        "operation": operation,
        "error_type": "MachineFault",
        "message": message,
    }
    return with_state(
        with_evidence({**thing, "value": v}, f"machine:fault:{operation}"),
        "invalid",
    )


def _event_id(name, seq):
    return hashlib.sha256(f"{name}|{seq}".encode("utf-8")).hexdigest()[:16]


def _path_get(root, path):
    if not path:
        return root
    cur = root
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def _path_set(root, path, value):
    if not path or path == "_acc":
        root["_acc"] = value
        return
    parts = path.split(".")
    cur = root
    index = 0
    while index < len(parts) - 1:
        p = parts[index]
        if p not in cur or not isinstance(cur[p], dict):
            cur[p] = {}
        cur = cur[p]
        index += 1
    cur[parts[-1]] = value


def _path_delete(root, path):
    if not path:
        return
    parts = path.split(".")
    cur = root
    index = 0
    while index < len(parts) - 1:
        p = parts[index]
        if not isinstance(cur, dict) or p not in cur:
            return
        cur = cur[p]
        index += 1
    if isinstance(cur, dict):
        cur.pop(parts[-1], None)
