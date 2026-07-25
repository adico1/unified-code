"""Generate seed-locked artifacts under Standard Ten.

Only emits artifacts expressible from the canonical seed + declarations.
Unsupported requests → standard.gap (never conventional fallback).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .standard import (
    STANDARD_VERSION,
    UEM_VERSION,
    load_seed,
    make_stamp,
    refuse_conventional,
    standard_gap,
)


def _root():
    return Path(__file__).resolve().parents[1]


def _generator_sha256() -> str:
    """Hash of this module + compile_decl + bytecode as generator surface."""
    root = _root()
    h = hashlib.sha256()
    for rel in (
        "unified/standard_generate.py",
        "unified/standard.py",
        "unified/machine/compile_decl.py",
        "unified/machine/bytecode.py",
        "unified/machine/opcodes.py",
    ):
        p = root / rel
        if p.is_file():
            h.update(p.read_bytes())
    return h.hexdigest()


def load_declaration_json(thing):
    """Thing value.declaration_path → value.declaration (pure JSON file)."""
    value = thing.get("value") if isinstance(thing.get("value"), dict) else {}
    path = value.get("declaration_path")
    if not path:
        return standard_gap(
            {
                **thing,
                "value": {
                    **value,
                    "gap_id": "gap.missing-declaration-path",
                    "rule": "3",
                    "summary": "declaration_path required",
                },
            }
        )
    p = Path(path)
    if not p.is_file():
        return standard_gap(
            {
                **thing,
                "value": {
                    **value,
                    "gap_id": "gap.declaration-missing",
                    "rule": "3",
                    "summary": f"declaration file missing: {path}",
                    "paths": [str(path)],
                },
            }
        )
    raw = p.read_bytes()
    decl = json.loads(raw.decode("utf-8"))
    return {
        **thing,
        "value": {
            **value,
            "declaration": decl,
            "declaration_sha256": hashlib.sha256(raw).hexdigest(),
            "declaration_path": str(p),
        },
        "evidence": (*tuple(thing.get("evidence") or ()), "standard:declaration:loaded"),
        "state": "formed",
    }


def generate_uem_from_seed_declaration(thing):
    """Compile one seed JSON declaration → UEM artifacts + stamps.

    Uses existing compile surface. Does not write domain-specific branches.
    """
    from .machine.compile_decl import compile_declaration, write_artifacts
    from .machine.thing import blank_thing

    loaded = load_seed(thing if isinstance(thing, dict) else {"value": {}})
    if loaded.get("state") == "invalid":
        return loaded
    value = dict(loaded.get("value") or {})
    decl_path = value.get("declaration_path")
    if not decl_path:
        return standard_gap(
            {
                **loaded,
                "value": {
                    **value,
                    "gap_id": "gap.missing-declaration-path",
                    "rule": "3",
                    "summary": "declaration_path required for UEM generation",
                },
            }
        )
    dthing = load_declaration_json(
        {
            **loaded,
            "value": {**value, "declaration_path": decl_path},
        }
    )
    if dthing.get("state") == "invalid":
        return dthing
    decl = dthing["value"]["declaration"]
    # compile_declaration expects declaration inside value
    compiled = compile_declaration(
        blank_thing({"declaration": decl})
    )
    if compiled.get("state") == "invalid":
        return compiled
    out_dir = value.get("out_dir")
    if not out_dir:
        # default artifacts/uem/<id>
        decl_id = Path(decl_path).stem
        out_dir = str(_root() / "artifacts" / "uem" / decl_id)
    written = write_artifacts(compiled, out_dir)
    # stamps
    gen_sha = _generator_sha256()
    seed_sha = dthing["value"].get("seed_sha256") or value.get("seed_sha256")
    decl_sha = dthing["value"]["declaration_sha256"]
    stamps = []
    for name in ("program.uem", "program.symbolic.json"):
        art = Path(out_dir) / name
        if not art.is_file():
            continue
        body = art.read_bytes()
        stamped = make_stamp(
            {
                "value": {
                    "seed_sha256": seed_sha,
                    "generator_sha256": gen_sha,
                    "declaration_sha256": decl_sha,
                    "uem_version": UEM_VERSION,
                    "artifact_bytes": body,
                },
                "depths": (),
                "axes": (),
                "evidence": (),
                "state": "formed",
            }
        )
        stamp = stamped["value"]["stamp"]
        stamp_path = Path(out_dir) / f"{name}.stamp.json"
        stamp_path.write_text(
            json.dumps(stamp, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        stamps.append({"artifact": name, "stamp": stamp, "stamp_path": str(stamp_path)})
    # lock generator hash
    lock = _root() / "seed" / "stamps" / "generator.lock.json"
    lock.parent.mkdir(parents=True, exist_ok=True)
    lock.write_text(
        json.dumps(
            {
                "generator_sha256": gen_sha,
                "standard_version": STANDARD_VERSION,
                "uem_version": UEM_VERSION,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        **written,
        "value": {
            **(written.get("value") or {}),
            "out_dir": out_dir,
            "stamps": stamps,
            "seed_sha256": seed_sha,
            "generator_sha256": gen_sha,
            "declaration_sha256": decl_sha,
            "standard_version": STANDARD_VERSION,
        },
        "evidence": (
            *tuple(written.get("evidence") or ()),
            "standard:generate:uem",
        ),
        "state": written.get("state") or "formed",
    }


def generate_all_seed_declarations(thing=None):
    """Generate UEM for every declaration listed in ROOT.seed.json."""
    base = {
        "value": {},
        "depths": (),
        "axes": (),
        "evidence": (),
        "state": "formed",
    }
    if isinstance(thing, dict):
        base = {**base, **thing, "value": {**(thing.get("value") or {})}}
    loaded = load_seed(base)
    if loaded.get("state") == "invalid":
        return loaded
    seed = loaded["value"]["seed"]
    root = _root()
    results = []
    for d in seed.get("declarations") or ():
        path = root / d["path"]
        out = generate_uem_from_seed_declaration(
            {
                **loaded,
                "value": {
                    **loaded["value"],
                    "declaration_path": str(path),
                    "out_dir": str(root / "artifacts" / "uem" / d["id"]),
                },
            }
        )
        results.append(
            {
                "id": d["id"],
                "state": out.get("state"),
                "out_dir": (out.get("value") or {}).get("out_dir"),
                "evidence_tail": list((out.get("evidence") or ())[-3:]),
            }
        )
        if out.get("state") == "invalid" and (out.get("value") or {}).get("gap"):
            return out
    return {
        **loaded,
        "value": {
            **loaded["value"],
            "generated": results,
            "generator_sha256": _generator_sha256(),
        },
        "evidence": (*tuple(loaded.get("evidence") or ()), "standard:generate:all-declarations"),
        "state": "formed",
    }


def request_feature(thing):
    """Public entry for feature requests. Unexpressible → standard.gap only."""
    value = thing.get("value") if isinstance(thing, dict) and isinstance(thing.get("value"), dict) else {}
    kind = value.get("kind") or value.get("feature")
    if kind in {"uem_from_declaration", "generate_uem"}:
        return generate_uem_from_seed_declaration(thing)
    if kind in {"generate_all", "all_declarations"}:
        return generate_all_seed_declarations(thing)
    if kind in {"audit"}:
        from .standard_audit import run_audit

        return run_audit(thing)
    # Everything else is a gap — no conventional implementation
    return refuse_conventional(
        {
            "value": {
                **value,
                "gap_id": f"gap.unsupported-feature:{kind}",
                "rule": "non-fallback",
                "summary": f"feature {kind!r} is not expressible under Standard Ten yet",
                "paths": list(value.get("paths") or ()),
            },
            "depths": (),
            "axes": (),
            "evidence": (),
            "state": "formed",
        }
    )
