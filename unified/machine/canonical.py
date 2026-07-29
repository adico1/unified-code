"""L11 canonical observable result — identical across conforming hosts.

Serialization: JSON object, sort_keys=True, separators=(',', ':'), UTF-8,
ensure_ascii=False, trailing newline forbidden in the hash body.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from generated.uem_surface.unified.machine.generated_surface import (
    CANONICAL_RESULT_FIELDS,
    REGISTRY_VERSION,
    UNICODE_PROFILE,
)

CANONICAL_VERSION = 1

# Evidence marks retained for cross-host equivalence (ordered).
_EV_KEEP = re.compile(
    r"^(?:"
    r"op:.+"
    r"|event:.+"
    r"|boundary:(?!load).*"
    r"|letter:.+"
    r"|source:.+"
    r"|part:.+"
    r"|merge:.+"
    r"|script-law:.+"
    r"|present_result:.+"
    r"|read:.+"
    r"|outward:.+"
    r"|host:fulfill"
    r"|limit:.+"
    r"|primitive:.+"
    r"|map:.+"
    r"|fold:.+"
    r"|apply:.+"
    r"|execution-after-stop"
    r"|eval:.+"
    # feature result marks (not load/encode/compile noise)
    r"|(?!load:|encode:|decode:|compile:|validate:|machine:|prepare_|generate:)"
    r"[a-z_][a-z0-9_]*:(?:ok|skipped|error:.+|missing-input|missing-text|missing-document)"
    r")$"
)

_OP_NUM = re.compile(r"^op:(\d+)(?::(.*))?$")
_OP_NAMES = {
    1: "LOAD",
    2: "READ",
    3: "WRITE",
    4: "DELETE",
    5: "EMIT",
    6: "ENQUEUE",
    7: "DEQUEUE",
    8: "ROUTE",
    9: "APPLY",
    10: "MAP",
    11: "FOLD",
    12: "VERIFY",
    13: "TICKET",
    14: "OUTWARD",
    15: "ACK",
    16: "STOP",
}


def normalize_evidence_mark(mark: str) -> str | None:
    if not isinstance(mark, str):
        return None
    m = _OP_NUM.match(mark)
    if m:
        code = int(m.group(1))
        name = _OP_NAMES.get(code, str(code))
        rest = m.group(2)
        return f"op:{name}" if rest is None else f"op:{name}:{rest}"
    if mark == "op:STOP":
        return "op:STOP"
    if not _EV_KEEP.match(mark):
        return None
    return mark


def normalize_evidence(evidence) -> list[str]:
    out: list[str] = []
    for item in evidence or ():
        n = normalize_evidence_mark(str(item))
        if n is not None:
            out.append(n)
    return out


def build_canonical(
    *,
    program_sha256: str | None,
    state: str | None,
    stop_reason: str | None,
    presentation: dict | None,
    stats: Any,
    error: Any,
    path: Any,
    ticket: Any,
    outward_log: list | None,
    events_emitted: list | None,
    events_dequeued: list | None,
    evidence,
    limit_hit: str | None,
    steps: int | None,
    instruction_count: int | None,
    reject: str | None = None,
) -> dict:
    """Build the L11 canonical object (plain data)."""
    pres = None
    if isinstance(presentation, dict):
        pres = {
            "text": presentation.get("text"),
            "exit_code": presentation.get("exit_code"),
        }
    tick = None
    if isinstance(ticket, dict):
        # only stable ticket fields
        tick = {
            "kind": ticket.get("kind"),
            "operation": ticket.get("operation"),
            "error_type": ticket.get("error_type"),
            "message": ticket.get("message"),
            "correlation_id": ticket.get("correlation_id"),
            "ticket_id": ticket.get("ticket_id"),
            "acked": bool(ticket.get("acked")),
        }
    return {
        "canonical_version": CANONICAL_VERSION,
        "registry_version": REGISTRY_VERSION,
        "unicode_profile": UNICODE_PROFILE,
        "program_sha256": program_sha256,
        "state": state,
        "stop_reason": stop_reason or None,
        "presentation": pres,
        "stats": stats if stats is not None else None,
        "error": error if error is not None else None,
        "path": path if path is not None else None,
        "ticket": tick,
        "outward_log": list(outward_log or ()),
        "events_emitted": list(events_emitted or ()),
        "events_dequeued": list(events_dequeued or ()),
        "evidence": normalize_evidence(evidence),
        "limit_hit": limit_hit,
        "steps": steps,
        "instruction_count": instruction_count,
        "reject": reject,
    }


def canonical_bytes(obj: dict) -> bytes:
    text = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return text.encode("utf-8")


def canonical_sha256(obj: dict) -> str:
    return hashlib.sha256(canonical_bytes(obj)).hexdigest()


def from_python_run(compiled: dict, result: dict) -> dict:
    """Extract L11 canonical from Python machine result Thing."""
    from .thing import value_of

    cv = value_of(compiled) if isinstance(compiled, dict) else {}
    rv = value_of(result) if isinstance(result, dict) else {}
    store = rv.get("store") if isinstance(rv.get("store"), dict) else {}
    stop = rv.get("stop_reason")
    limit_hit = None
    if isinstance(stop, str) and stop.startswith("limit:"):
        limit_hit = stop.split(":", 1)[1]
    evidence = result.get("evidence") or rv.get("evidence") or ()
    return build_canonical(
        program_sha256=cv.get("program_sha256") or rv.get("program_sha256"),
        state=result.get("state"),
        stop_reason=stop,
        presentation=rv.get("presentation") or store.get("presentation"),
        stats=rv.get("stats") if rv.get("stats") is not None else store.get("stats"),
        error=rv.get("error") if rv.get("error") is not None else store.get("error"),
        path=rv.get("path") if rv.get("path") is not None else store.get("path"),
        ticket=rv.get("ticket"),
        outward_log=rv.get("outward_log"),
        events_emitted=rv.get("events_emitted"),
        events_dequeued=rv.get("events_dequeued"),
        evidence=evidence,
        limit_hit=limit_hit,
        steps=(rv.get("limits") or {}).get("steps") if isinstance(rv.get("limits"), dict) else rv.get("steps"),
        instruction_count=rv.get("instruction_count") or len(cv.get("instructions") or ()),
        reject=rv.get("reject"),
    )


def from_c_json(obj: dict) -> dict:
    """Normalize C host JSON into L11 canonical (same shape)."""
    stop = obj.get("stop_reason")
    limit_hit = None
    if isinstance(stop, str) and stop.startswith("limit:"):
        limit_hit = stop.split(":", 1)[1]
    return build_canonical(
        program_sha256=obj.get("program_sha256"),
        state=obj.get("state"),
        stop_reason=stop,
        presentation=obj.get("presentation"),
        stats=obj.get("stats"),
        error=obj.get("error"),
        path=obj.get("path"),
        ticket=obj.get("ticket"),
        outward_log=obj.get("outward_log"),
        events_emitted=obj.get("events_emitted"),
        events_dequeued=obj.get("events_dequeued"),
        evidence=obj.get("evidence"),
        limit_hit=limit_hit,
        steps=obj.get("steps"),
        instruction_count=obj.get("instruction_count"),
        reject=obj.get("reject"),
    )
