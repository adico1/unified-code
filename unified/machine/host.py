"""Host adapter for OUTWARD effects — not part of the chip-neutral core.

Fulfills read_utf8 / read_json / ticket.persist requests then resumes.
"""

from __future__ import annotations

import json
from pathlib import Path

from .interpreter import machine_load, machine_run, machine_step
from .thing import value_of, with_evidence, with_state


def run_program(thing):
    """Execute compiled program with host_input; fulfill outward reads.

    host_input forms:
      {"source": path_or_dash}
      {"argv": [path]}
      {"text": "..."}  # inject text without file (test helper)
      {"document": {...}}  # inject document without file
    """
    loaded = machine_load(thing)
    if loaded.get("state") == "invalid":
        return loaded
    current = loaded
    guard = 0
    while guard < 200_000:
        guard += 1
        current = machine_run(current)
        v = value_of(current)
        if v.get("halted"):
            return _finalize(current)
        req = v.get("outward_request")
        if req is None:
            if current.get("state") == "invalid":
                return _finalize(current)
            # progress?
            if v.get("pc", 0) >= len(v.get("instructions") or ()):
                return _finalize(current)
            current = machine_step(current)
            continue
        # fulfill outward
        result = _fulfill(req, v)
        nv = dict(v)
        nv["outward_result"] = result
        # keep request until accept_outward clears it
        current = {**current, "value": nv}
        current = with_evidence(current, f"host:fulfill:{req.get('effect')}")
    return with_state(with_evidence(current, "host:guard-limit"), "invalid")


def _fulfill(req, machine_value):
    effect = req.get("effect")
    source = req.get("source")
    cfg = req.get("config") or {}
    # inject shortcuts from host_input
    host = machine_value.get("host_input")
    if isinstance(host, dict):
        if effect == "read_utf8" and isinstance(host.get("text"), str):
            return {"data": host["text"]}
        if effect == "read_json" and isinstance(host.get("document"), dict):
            return {"data": host["document"]}
    if effect == "read_utf8":
        return _read_utf8(source, cfg)
    if effect == "read_json":
        return _read_json(source, cfg)
    if effect == "ticket.persist":
        # host may write; machine remains pure
        return {"ok": True, "external_id": None}
    return {"error": "unknown-effect"}


def _read_utf8(source, cfg):
    stdin_token = (cfg.get("stdin_token") if False else None)
    # token from image source config lives on machine; use "-" default
    if source is None:
        return {"error": "missing-source"}
    if source == "-":
        # host must have injected text; otherwise empty
        return {"error": "stdin-not-provided"}
    path = Path(str(source))
    if not path.exists():
        return {"error": "missing-file"}
    if not path.is_file():
        return {"error": "not-a-file"}
    try:
        data = path.read_bytes()
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return {"error": "invalid-utf8"}
    except OSError:
        return {"error": "read-error"}
    return {"data": text}


def _read_json(source, cfg):
    if source is None:
        return {"error": "missing-source"}
    if source == "-":
        return {"error": "stdin-not-provided"}
    path = Path(str(source))
    if not path.exists():
        return {"error": "missing-file"}
    if not path.is_file():
        return {"error": "not-a-file"}
    try:
        text = path.read_text(encoding="utf-8")
        doc = json.loads(text)
    except UnicodeDecodeError:
        return {"error": "invalid-utf8"}
    except json.JSONDecodeError:
        return {"error": "invalid-json"}
    except OSError:
        return {"error": "read-error"}
    if not isinstance(doc, dict):
        return {"error": "input-not-an-object", "path": []}
    return {"data": doc}


def _finalize(thing):
    v = dict(value_of(thing))
    store = v.get("store") or {}
    presentation = store.get("presentation")
    # expose presentation at top-level value for compatibility probes
    out_value = {
        **v,
        "presentation": presentation,
        "stats": store.get("stats"),
        "error": store.get("error"),
        "path": store.get("path"),
        "ticket": v.get("ticket"),
    }
    return {
        **thing,
        "value": out_value,
        "evidence": (*tuple(thing.get("evidence") or ()), "host:done"),
    }


def run_compiled(compiled_thing, host_input):
    """Convenience: compiled program Thing + host_input → result Thing."""
    value = dict(value_of(compiled_thing))
    value["host_input"] = host_input
    return run_program({**compiled_thing, "value": value, "state": "formed"})
