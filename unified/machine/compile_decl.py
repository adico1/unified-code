"""Compile Unified Code declarations → UEM symbolic program + image + bytecode."""

from __future__ import annotations

import json
from pathlib import Path

from .bytecode import encode_program
from .thing import blank_thing, with_evidence, with_state
from .validate import validate_symbolic


def compile_declaration(thing):
    """Thing in: value.declaration (normalized) → instructions, image, bytecode.

    Does not replace the generator; pure compile artifact.
    """
    value = thing.get("value") if isinstance(thing.get("value"), dict) else {}
    decl = value.get("declaration")
    if not isinstance(decl, dict):
        return with_state(with_evidence(thing, "compile:missing-declaration"), "invalid")

    try:
        instructions, image = _compile(decl)
    except ValueError as exc:
        return with_state(
            with_evidence(thing, f"compile:fail:{exc}"),
            "invalid",
        )

    built = {
        **thing,
        "value": {
            **value,
            "instructions": instructions,
            "image": image,
            "package": decl.get("package"),
            "project": (decl.get("project") or {}).get("name")
            if isinstance(decl.get("project"), dict)
            else decl.get("name"),
        },
        "state": "formed",
        "evidence": (*tuple(thing.get("evidence") or ()), "compile:symbolic"),
    }
    checked = validate_symbolic(built)
    if checked.get("state") == "invalid":
        return checked
    encoded = encode_program(checked)
    if encoded.get("state") == "invalid":
        return encoded
    return with_evidence(encoded, "compile:bytecode")


def compile_declaration_path(path: str):
    """Load declaration module and compile. Returns machine Thing."""
    from unified.boundary import inward
    from unified.generator.declaration import load_declaration_module

    loaded = load_declaration_module(
        inward({"declaration_path": str(path)})
    )
    if loaded.get("state") != "formed":
        return with_state(
            with_evidence(loaded, "compile:load-fail"),
            "invalid",
        )
    decl = loaded["value"].get("declaration")
    return compile_declaration(
        {
            **loaded,
            "value": {**loaded["value"], "declaration": decl},
        }
    )


def _compile(decl):
    features = list(decl.get("features") or ())
    if not features:
        raise ValueError("no-features")
    feat = features[0]
    tr = feat.get("transformation") or {}
    if tr.get("kind") != "expression":
        raise ValueError("unsupported-transformation")

    boundaries = list(decl.get("boundaries") or ())
    boundary = boundaries[0] if boundaries else {}
    bkind = boundary.get("kind") or "read_utf8_source"
    bname = boundary.get("name") or "boundary"

    if bkind == "read_utf8_source":
        effect = "read_utf8"
        target = boundary.get("text_field") or "text"
        source_field = boundary.get("source_field") or "source"
    elif bkind == "read_json_source":
        effect = "read_json"
        target = boundary.get("document_field") or "document"
        source_field = boundary.get("source_field") or "source"
    else:
        raise ValueError(f"unsupported-boundary:{bkind}")

    cli = decl.get("cli") or {}
    argv_cfg = (cli.get("argv") or {}) if isinstance(cli, dict) else {}
    presentation = decl.get("presentation") or {}
    verify = decl.get("verify") or {}
    part_name = feat.get("name") or "part"

    # Normalize expression AST to plain JSON-friendly data
    expression = _plain(tr.get("program") or tr.get("result"))
    raw_bindings = tr.get("bindings") or {}
    # Preserve declaration insertion order (JSON sort_keys must not change eval order)
    binding_order = list(raw_bindings.keys()) if isinstance(raw_bindings, dict) else []
    bindings = _plain(raw_bindings)

    image = {
        "source": {
            "field": argv_cfg.get("field") or source_field,
            "missing": (argv_cfg.get("errors") or {}).get("missing") or "missing-source",
            "extra": (argv_cfg.get("errors") or {}).get("extra") or "extra-source",
            "stdin_token": argv_cfg.get("stdin_token") or "-",
        },
        "boundary": {
            "name": bname,
            "kind": bkind,
            "source_field": source_field,
            "target_field": target,
            "effect": effect,
        },
        "input_key": tr.get("input_key") or "document",
        "merge_key": "stats" if tr.get("merge") == "stats" else (tr.get("merge") or "result"),
        "expression": expression,
        "bindings": bindings,
        "binding_order": binding_order,
        "part_name": part_name,
        "verify": {
            "require_value_field": verify.get("require_value_field"),
            "require_evidence_contains": list(verify.get("require_evidence_contains") or ()),
        },
        "presentation": {
            "success_from": presentation.get("success_from") or "stats",
            "success_keys": list(presentation.get("success_keys") or ()),
            "include_error_path": bool(presentation.get("include_error_path")),
        },
        "routes": {},
    }

    # Fixed linear program (no app-level loops). Pipeline:
    # load → mark inward → parse source → outward read → accept → letter →
    # eval → merge → mark evidence continuity → verify → present → stop
    instructions = (
        ("LOAD", "host_input"),
        ("WRITE", "host"),
        ("APPLY", "mark_inward"),
        ("APPLY", "require_source"),
        ("OUTWARD", effect),
        ("APPLY", "accept_outward"),
        ("APPLY", "letter"),
        ("APPLY", "eval_expression"),
        ("APPLY", "merge_result"),
        ("VERIFY", "result"),
        ("APPLY", "present_json"),
        ("STOP", None),
    )
    return instructions, image


def _plain(obj):
    """Convert to JSON-roundtrippable plain data (tuples → lists)."""
    return json.loads(json.dumps(obj, default=_default))


def _default(obj):
    if isinstance(obj, tuple):
        return list(obj)
    if isinstance(obj, set):
        return sorted(obj)
    raise TypeError(type(obj))


def write_artifacts(thing, out_dir: str):
    """Write bytecode + symbolic JSON artifacts (no manual edits expected)."""
    value = thing.get("value") if isinstance(thing.get("value"), dict) else {}
    root = Path(out_dir)
    root.mkdir(parents=True, exist_ok=True)
    raw = value.get("bytecode")
    if isinstance(raw, (bytes, bytearray)):
        (root / "program.uem").write_bytes(bytes(raw))
    meta = {
        "program_sha256": value.get("program_sha256"),
        "bytecode_size": value.get("bytecode_size"),
        "instructions": list(value.get("instructions") or ()),
        "image": value.get("image"),
        "package": value.get("package"),
    }
    (root / "program.symbolic.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return with_evidence(thing, f"artifacts:{out_dir}")
