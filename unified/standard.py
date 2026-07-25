"""Standard Ten — non-bypassable governing contract helpers.

Thing → Thing. No OOP. When a feature cannot be expressed under Standard Ten,
call ``standard_gap`` — never fall back to conventional development.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

STANDARD_VERSION = "TEN-1"
UEM_VERSION = "UEM-16-v0.1"

PROVENANCE_CLASSES = frozenset(
    {
        "seed",
        "generated",
        "external-vendored",
        "physical-host-boundary",
        "evidence",
    }
)

# Paths that are never part of the product tree for classification
_SKIP_DIR_NAMES = frozenset(
    {
        ".git",
        ".venv",
        "__pycache__",
        ".pytest_cache",
        "unified_code.egg-info",
        "build",
        ".uc",
    }
)


def _blank(value=None):
    return {
        "value": {} if value is None else value,
        "depths": (),
        "axes": (),
        "evidence": (),
        "state": "formed",
    }


def standard_gap(thing):
    """Stop with standard.gap — the only authorized response to unsupported expression.

    Input thing value may include:
      rule, summary, gap_id, paths, detail

    Returns invalid Thing with event ticket material under value.gap and evidence
    mark ``standard.gap``. Does not implement the missing feature.
    """
    if not isinstance(thing, dict) or "value" not in thing:
        thing = _blank(thing)
    value = thing.get("value") if isinstance(thing.get("value"), dict) else {}
    gap_id = value.get("gap_id") or value.get("id") or "gap.unspecified"
    rule = str(value.get("rule") or "?")
    summary = str(value.get("summary") or "unsupported under Standard Ten")
    paths = list(value.get("paths") or ())
    detail = value.get("detail")
    gap = {
        "kind": "standard.gap",
        "gap_id": gap_id,
        "rule": rule,
        "summary": summary,
        "paths": paths,
        "standard_version": STANDARD_VERSION,
        "status": "open",
    }
    if detail is not None:
        gap["detail"] = detail
    # Deterministic ticket-like correlation from gap material only
    raw = "|".join([gap_id, rule, summary, ",".join(paths)])
    cid = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
    gap["correlation_id"] = cid
    ticket = {
        "kind": "standard.gap",
        "operation": "standard_ten",
        "error_type": "StandardGap",
        "message": summary[:500],
        "correlation_id": cid,
        "ticket_id": cid,
        "gap_id": gap_id,
        "acked": False,
    }
    evidence = tuple(thing.get("evidence") or ()) + (
        "standard.gap",
        f"standard.gap:{gap_id}",
        f"standard.rule:{rule}",
        "event:ticket.open",
    )
    return {
        **thing,
        "value": {
            **value,
            "gap": gap,
            "ticket": ticket,
            "error": "standard.gap",
            "event": "standard.gap",
        },
        "evidence": evidence,
        "state": "invalid",
    }


def seed_root_path(repo_root=None):
    root = Path(repo_root) if repo_root else Path(__file__).resolve().parents[1]
    return root / "seed" / "ROOT.seed.json"


def load_seed(thing):
    """Load canonical seed. Thing in: value.repo_root optional → value.seed + hashes."""
    if not isinstance(thing, dict) or "value" not in thing:
        thing = _blank(thing)
    value = dict(thing.get("value") or {})
    root = Path(value["repo_root"]) if value.get("repo_root") else Path(__file__).resolve().parents[1]
    path = root / "seed" / "ROOT.seed.json"
    if not path.is_file():
        return standard_gap(
            {
                **thing,
                "value": {
                    **value,
                    "gap_id": "gap.missing-seed",
                    "rule": "3",
                    "summary": f"canonical seed missing at {path}",
                    "paths": [str(path)],
                },
            }
        )
    raw = path.read_bytes()
    seed = json.loads(raw.decode("utf-8"))
    if seed.get("standard_version") != STANDARD_VERSION:
        return standard_gap(
            {
                **thing,
                "value": {
                    **value,
                    "gap_id": "gap.seed-version",
                    "rule": "3",
                    "summary": "seed standard_version mismatch",
                    "paths": [str(path)],
                },
            }
        )
    if seed.get("standard_ten") is not True:
        return standard_gap(
            {
                **thing,
                "value": {
                    **value,
                    "gap_id": "gap.seed-not-ten",
                    "rule": "3",
                    "summary": "seed.standard_ten must be true",
                    "paths": [str(path)],
                },
            }
        )
    return {
        **thing,
        "value": {
            **value,
            "seed": seed,
            "seed_path": str(path),
            "seed_sha256": hashlib.sha256(raw).hexdigest(),
            "standard_version": STANDARD_VERSION,
            "uem_version": seed.get("uem_version") or UEM_VERSION,
        },
        "evidence": (*tuple(thing.get("evidence") or ()), "standard:seed:loaded"),
        "state": "formed",
    }


def make_stamp(thing):
    """Build generation stamp dict from thing value fields. Pure."""
    value = thing.get("value") if isinstance(thing.get("value"), dict) else {}
    body = value.get("artifact_bytes")
    if isinstance(body, str):
        body_b = body.encode("utf-8")
    elif isinstance(body, (bytes, bytearray)):
        body_b = bytes(body)
    else:
        body_b = b""
    stamp = {
        "seed_sha256": value.get("seed_sha256") or "",
        "generator_sha256": value.get("generator_sha256") or "",
        "declaration_sha256": value.get("declaration_sha256") or "",
        "standard_version": STANDARD_VERSION,
        "uem_version": value.get("uem_version") or UEM_VERSION,
        "artifact_sha256": hashlib.sha256(body_b).hexdigest(),
    }
    return {
        **thing,
        "value": {**value, "stamp": stamp},
        "evidence": (*tuple(thing.get("evidence") or ()), "standard:stamp"),
        "state": thing.get("state") or "formed",
    }


def refuse_conventional(thing):
    """Explicit refusal of conventional-development fallback (non-fallback law)."""
    value = thing.get("value") if isinstance(thing, dict) and isinstance(thing.get("value"), dict) else {}
    return standard_gap(
        {
            "value": {
                **value,
                "gap_id": value.get("gap_id") or "gap.conventional-fallback-refused",
                "rule": "non-fallback",
                "summary": (
                    "Conventional development is not an authorized fallback. "
                    + str(value.get("summary") or "feature not expressible under Standard Ten")
                ),
                "paths": list(value.get("paths") or ()),
            },
            "evidence": tuple(thing.get("evidence") or ()) if isinstance(thing, dict) else (),
            "depths": (),
            "axes": (),
            "state": "formed",
        }
    )
