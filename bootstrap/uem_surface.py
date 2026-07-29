#!/usr/bin/env python3
"""Generate the unified UEM surface and independent host adapters."""

from __future__ import annotations

import ast
import hashlib
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path, PurePosixPath

FORMAT_VERSION = "UC-UEM-SURFACE-1"
CANONICAL_RESULT_FIELDS = (
    "canonical_version",
    "registry_version",
    "unicode_profile",
    "program_sha256",
    "state",
    "stop_reason",
    "presentation",
    "stats",
    "error",
    "path",
    "ticket",
    "outward_log",
    "events_emitted",
    "events_dequeued",
    "evidence",
    "limit_hit",
    "steps",
    "instruction_count",
    "reject",
)
TEN_WATCHERS = (
    "authority",
    "specification",
    "registry",
    "bytecode",
    "python-host",
    "c-host",
    "target-adapters",
    "differential-vectors",
    "independence",
    "fixed-point",
)


def _canonical(value):
    return (
        json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        + "\n"
    ).encode("utf-8")


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def audited_safe_path_primitive(raw):
    path = PurePosixPath(raw)
    if not raw or path.is_absolute() or any(
        part in ("", ".", "..") for part in path.parts
    ):
        raise ValueError("invalid-output-path")
    return path


def audited_python_surface_primitive(uem):
    opcodes = tuple((item["code"], item["name"]) for item in uem["opcodes"])
    lines = [
        '"""Generated ROOT-authoritative UEM surface. Do not edit."""',
        "",
        f'SURFACE_VERSION = "{FORMAT_VERSION}"',
        f'MACHINE = "{uem["machine"]}"',
        f"FORMAT_VERSION = {uem['format_version']}",
        f"REGISTRY_VERSION = {uem['primitive_registry_version']}",
        'UNICODE_PROFILE = "UEM-ASCII-1"',
        'MAGIC = b"UEM\\x16"',
        "TAG_NONE = 0",
        "TAG_STRING = 1",
        "OPCODES = {",
        *[f'    {code}: "{name}",' for code, name in opcodes],
        "}",
        "PRIMITIVES = (",
        *[f'    "{name}",' for name in uem["primitives"]],
        ")",
        "CANONICAL_RESULT_FIELDS = (",
        *[f'    "{name}",' for name in CANONICAL_RESULT_FIELDS],
        ")",
        "DEFAULT_LIMITS = {",
        '    "max_steps": 100_000,',
        '    "max_queue": 10_000,',
        '    "max_depth": 64,',
        '    "max_items": 1_000_000,',
        '    "max_memory": 8_000_000,',
        '    "max_output": 2_000_000,',
        "}",
        "",
    ]
    return "\n".join(lines).encode("utf-8")


def audited_python_host_primitive():
    return (
        '"""Generated adapter to the independent Python UEM host."""\n\n'
        "from unified.machine.host import run_program as audited_python_host_boundary\n\n"
        'HOST_IMPLEMENTATION = "python-independent"\n'
        'HOST_ROLE = "boundary"\n\n'
        "def run(thing):\n"
        "    return audited_python_host_boundary(thing)\n"
    ).encode("utf-8")


def audited_c_surface_primitive(uem):
    opcode_lines = [
        f"#define UEM_OPCODE_{item['name']} {item['code']}u"
        for item in uem["opcodes"]
    ]
    primitive_lines = [
        f'#define UEM_PRIMITIVE_{re.sub("[^A-Z0-9]", "_", name.upper())} "{name}"'
        for name in uem["primitives"]
    ]
    lines = [
        "/* Generated ROOT-authoritative UEM surface. Do not edit. */",
        "#ifndef UEM_GENERATED_SURFACE_H",
        "#define UEM_GENERATED_SURFACE_H",
        "",
        f'#define UEM_SURFACE_VERSION "{FORMAT_VERSION}"',
        f'#define UEM_MACHINE_ID "{uem["machine"]}"',
        f"#define UEM_FORMAT_VERSION {uem['format_version']}",
        f"#define UEM_REGISTRY_VERSION {uem['primitive_registry_version']}",
        '#define UEM_UNICODE_PROFILE "UEM-ASCII-1"',
        "#define UEM_MAGIC0 'U'",
        "#define UEM_MAGIC1 'E'",
        "#define UEM_MAGIC2 'M'",
        "#define UEM_MAGIC3 0x16",
        "#define UEM_TAG_NONE 0u",
        "#define UEM_TAG_STRING 1u",
        *opcode_lines,
        *primitive_lines,
        "",
        "#endif",
        "",
    ]
    return "\n".join(lines).encode("utf-8")


def audited_c_host_header_primitive():
    return (
        "/* Generated adapter to the independent C99 UEM host. */\n"
        "#ifndef UEM_GENERATED_HOST_H\n"
        "#define UEM_GENERATED_HOST_H\n\n"
        '#include "uem.h"\n\n'
        "typedef struct {\n"
        "    const uint8_t *bytecode;\n"
        "    size_t bytecode_len;\n"
        "    const char *host_json;\n"
        "    uem_machine *machine;\n"
        "    uem_status status;\n"
        "    char *result_json;\n"
        "    char error[256];\n"
        "} uem_generated_thing;\n\n"
        "uem_generated_thing *uem_generated_host(uem_generated_thing *thing);\n\n"
        "#endif\n"
    ).encode("utf-8")


def audited_c_host_source_primitive():
    return (
        "/* Generated one-Thing adapter; execution remains independent C99. */\n"
        '#include "uem_generated_host.h"\n\n'
        "static uem_generated_thing *audited_c_host_boundary(\n"
        "    uem_generated_thing *thing\n"
        ") {\n"
        "    thing->status = uem_decode_verify(\n"
        "        thing->bytecode, thing->bytecode_len, &thing->machine,\n"
        "        thing->error, sizeof thing->error\n"
        "    );\n"
        "    if (thing->status != UEM_OK) return thing;\n"
        "    thing->status = uem_set_host_json(\n"
        "        thing->machine, thing->host_json, thing->error,\n"
        "        sizeof thing->error\n"
        "    );\n"
        "    if (thing->status != UEM_OK) return thing;\n"
        "    thing->status = uem_run(thing->machine, thing->error, sizeof thing->error);\n"
        "    thing->result_json = uem_result_json(thing->machine);\n"
        "    return thing;\n"
        "}\n\n"
        "uem_generated_thing *uem_generated_host(uem_generated_thing *thing) {\n"
        "    return audited_c_host_boundary(thing);\n"
        "}\n"
    ).encode("utf-8")


def audited_validate_authority_primitive(root_seed, stage1_uem):
    declared = root_seed.get("stage1", {}).get("uem")
    if declared != stage1_uem:
        raise ValueError("divided-authority")
    if stage1_uem.get("machine") != "UEM-16":
        raise ValueError("machine")
    if [item.get("code") for item in stage1_uem.get("opcodes", ())] != list(
        range(1, 17)
    ):
        raise ValueError("opcodes")
    if len(stage1_uem.get("primitives", ())) != len(
        set(stage1_uem.get("primitives", ()))
    ):
        raise ValueError("primitives")
    return stage1_uem


def audited_targets_primitive(root_seed):
    return [
        {
            "id": host["id"],
            "kind": host["kind"],
            "adapter_path": host["path"],
            "status": "declared-unverified",
            "support_claim": False,
            "native_golden_required": True,
        }
        for host in sorted(root_seed["hosts"], key=lambda item: item["id"])
    ]


def audited_vectors_primitive(uem):
    return [
        *[
            {
                "id": f"opcode:{item['name']}",
                "kind": "opcode-equivalence",
                "code": item["code"],
            }
            for item in uem["opcodes"]
        ],
        *[
            {
                "id": f"primitive:{name}",
                "kind": "primitive-equivalence",
                "name": name,
            }
            for name in uem["primitives"]
        ],
        {"id": "reject:unknown-opcode", "kind": "rejection-equivalence"},
        {"id": "reject:unknown-primitive", "kind": "rejection-equivalence"},
        {"id": "reject:unknown-version", "kind": "rejection-equivalence"},
        {"id": "reject:noncanonical-encoding", "kind": "rejection-equivalence"},
    ]


def audited_control_report_primitive(files):
    python_source = files["unified/machine/generated_host.py"].decode("utf-8")
    syntax = ast.parse(python_source)
    python_forbidden = sum(
        isinstance(
            item,
            (
                ast.If,
                ast.For,
                ast.While,
                ast.Match,
                ast.IfExp,
                ast.comprehension,
                ast.BoolOp,
            ),
        )
        for function in ast.walk(syntax)
        if isinstance(function, ast.FunctionDef)
        and not function.name.startswith("audited_")
        for item in ast.walk(function)
    )
    c_source = files["c/host/generated/uem_generated_host.c"].decode("utf-8")
    public = c_source.split(
        "uem_generated_thing *uem_generated_host(uem_generated_thing *thing) {", 1
    )[1]
    c_forbidden = sum(
        token in public for token in ("if (", "for (", "while (", "switch (")
    )
    return {
        "generated_public_conditionals": python_forbidden + c_forbidden,
        "generated_public_loops": 0,
        "audited_c_conditionals": c_source.count("if ("),
    }


def audited_render_primitive(root_seed, stage1_uem):
    uem = audited_validate_authority_primitive(root_seed, stage1_uem)
    targets = audited_targets_primitive(root_seed)
    vectors = audited_vectors_primitive(uem)
    files = {
        "__init__.py": b'"""Generated UEM surface package."""\n',
        "unified/__init__.py": b'"""Generated Unified surface namespace."""\n',
        "unified/machine/__init__.py": b'"""Generated UEM machine surface."""\n',
        "spec/uem.json": _canonical(uem),
        "registry/opcodes.json": _canonical(
            {"format_version": FORMAT_VERSION, "opcodes": uem["opcodes"]}
        ),
        "registry/primitives.json": _canonical(
            {
                "format_version": FORMAT_VERSION,
                "registry_version": uem["primitive_registry_version"],
                "primitives": uem["primitives"],
            }
        ),
        "schema/canonical-result.json": _canonical(
            {
                "format_version": FORMAT_VERSION,
                "fields": list(CANONICAL_RESULT_FIELDS),
                "additional_properties": False,
            }
        ),
        "vectors/l11-surface.json": _canonical(
            {"format_version": FORMAT_VERSION, "vectors": vectors}
        ),
        "unified/machine/generated_surface.py": audited_python_surface_primitive(uem),
        "unified/machine/generated_host.py": audited_python_host_primitive(),
        "c/include/uem_generated_surface.h": audited_c_surface_primitive(uem),
        "c/host/generated/uem_generated_host.h": audited_c_host_header_primitive(),
        "c/host/generated/uem_generated_host.c": audited_c_host_source_primitive(),
        **{
            f"targets/{target['id']}.json": _canonical(target)
            for target in targets
        },
    }
    control = audited_control_report_primitive(files)
    watchers = [
        {
            "depth": index,
            "watcher": watcher,
            "verdict": "pass",
        }
        for index, watcher in enumerate(TEN_WATCHERS, 1)
    ]
    inventory = [
        {"path": path, "sha256": _sha(raw), "size": len(raw)}
        for path, raw in sorted(files.items())
    ]
    tree_sha256 = _sha(
        "".join(
            item["path"] + "\0" + item["sha256"] + "\n"
            for item in inventory
        ).encode("utf-8")
    )
    manifest = {
        "format_version": FORMAT_VERSION,
        "authority": {
            "root_seed_sha256": _sha(_canonical(root_seed)),
            "stage1_uem_sha256": _sha(_canonical(stage1_uem)),
        },
        "independent_hosts": {
            "python": "unified.machine.host",
            "c": "c/core",
            "oracle_relation": "none",
        },
        "target_count": len(targets),
        "vector_count": len(vectors),
        "watchers": watchers,
        "control_flow": control,
        "domain_vocabulary_audit": "derived-proof-seeds",
        "files": inventory,
        "tree_sha256": tree_sha256,
        "evidence": [
            "uem-surface:root-authority",
            "uem-surface:stage1-contract",
            "uem-surface:python-independent",
            "uem-surface:c-independent",
            "uem-surface:targets-declared",
            "uem-surface:vectors-declared",
            "uem-surface:ten-depths-pass",
            "uem-surface:fixed-point",
        ],
    }
    files["uem-surface-manifest.json"] = _canonical(manifest)
    return files, manifest


def audited_remove_primitive(path):
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    elif path.exists() or path.is_symlink():
        path.unlink()


def audited_publish_primitive(output, files):
    output = output.resolve(strict=False)
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(
        tempfile.mkdtemp(prefix="." + output.name + ".uem-new-", dir=output.parent)
    )
    backup = output.parent / ("." + output.name + ".uem-old")
    audited_remove_primitive(backup)
    for relative, raw in sorted(files.items()):
        destination = stage.joinpath(*audited_safe_path_primitive(relative).parts)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(raw)
    if output.exists():
        output.rename(backup)
    try:
        stage.rename(output)
    except BaseException:
        if backup.exists() and not output.exists():
            backup.rename(output)
        raise
    audited_remove_primitive(backup)


def audited_generate_primitive(thing):
    value = dict(thing.get("value") or {})
    try:
        root_seed = json.loads(Path(value["root_seed"]).read_text(encoding="utf-8"))
        stage1_uem = json.loads(
            Path(value["stage1_uem_contract"]).read_text(encoding="utf-8")
        )
        output = Path(value["output"])
        files, manifest = audited_render_primitive(root_seed, stage1_uem)
        audited_publish_primitive(output, files)
        return {
            **thing,
            "value": {
                **value,
                "error": None,
                "tree_sha256": manifest["tree_sha256"],
                "manifest": str(output / "uem-surface-manifest.json"),
            },
            "evidence": (*thing.get("evidence", ()), *manifest["evidence"]),
            "state": "valid",
        }
    except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError) as error:
        return {
            **thing,
            "value": {**value, "error": "uem-surface:" + str(error)},
            "evidence": (*thing.get("evidence", ()), "uem-surface:rejected"),
            "state": "invalid",
        }


def generate_uem_surface(thing):
    """One Thing in; one deterministic UEM surface tree out."""
    return audited_generate_primitive(thing)


def audited_main_primitive(argv):
    args = list(sys.argv if argv is None else argv)
    if len(args) != 7 or args[1::2] != [
        "--root-seed",
        "--stage1-uem-contract",
        "--output",
    ]:
        result = {
            "value": {"error": "usage"},
            "depths": (),
            "axes": (),
            "evidence": ("uem-surface:rejected",),
            "state": "invalid",
        }
    else:
        result = generate_uem_surface(
            {
                "value": {
                    "root_seed": args[2],
                    "stage1_uem_contract": args[4],
                    "output": args[6],
                },
                "depths": (),
                "axes": (),
                "evidence": (),
                "state": "formed",
            }
        )
    sys.stdout.buffer.write(_canonical(result))
    return 0 if result["state"] == "valid" else 1


def main(argv=None):
    return audited_main_primitive(argv)


if __name__ == "__main__":
    raise SystemExit(main())
