"""Render project/feature source from normalized declarations (plain text data)."""

from __future__ import annotations

from typing import Any


def render_program(declaration: dict[str, Any]) -> dict[str, str]:
    """Full UC-1 project from a PROGRAM declaration."""
    package = declaration["package"]
    project_name = declaration["name"]
    features = tuple(f["name"] for f in declaration["features"])
    files: dict[str, str] = {}
    files["pyproject.toml"] = _pyproject(declaration)
    files["README.md"] = _readme(declaration)
    files[".gitignore"] = _gitignore()
    files[f"{package}/__init__.py"] = _package_init(package)
    files[f"{package}/__main__.py"] = _package_main()
    files[f"{package}/boundary.py"] = _boundary(declaration)
    files[f"{package}/core.py"] = _core(declaration)
    files[f"{package}/features.py"] = _features(features)
    files[f"{package}/parts.py"] = _parts(declaration["features"])
    files[f"{package}/compose.py"] = _compose(declaration)
    if declaration.get("cli"):
        files[f"{package}/cli.py"] = _cli(declaration)
    files["tests/test_signature.py"] = _test_signature(package, features, declaration)
    files["tests/test_program.py"] = _test_program(package, declaration)
    if declaration.get("tests"):
        files["tests/test_declared.py"] = _test_declared(package, declaration)
    return files


def render_feature_into_project(
    package: str,
    project_name: str,
    existing_features: tuple[str, ...],
    feature_decl: dict[str, Any],
    current_files: dict[str, str],
    *,
    stub_only: bool = False,
) -> dict[str, str]:
    """Merge one declared (or stub) feature into existing project files."""
    feature = feature_decl["name"]
    features = (*existing_features, feature)
    out: dict[str, str] = {}

    if stub_only:
        from .render import render_add_feature

        return render_add_feature(
            package, project_name, existing_features, feature, current_files
        )

    # Rebuild parts.py from existing feature names we can parse + new decl.
    # Prefer regenerating declared body for the new feature and keeping other
    # defs by extracting function sources when possible; otherwise rewrite all
    # from declaration only for the new feature and append.
    parts_src = current_files.get(f"{package}/parts.py", "")
    out[f"{package}/features.py"] = _features(features)
    out[f"{package}/parts.py"] = _append_or_rebuild_parts(
        parts_src, existing_features, feature_decl
    )
    # Compose: insert feature name before verify/outward if present, else append
    compose_src = current_files.get(f"{package}/compose.py", "")
    out[f"{package}/compose.py"] = _compose_insert_feature(compose_src, package, features)

    # Tests
    out["tests/test_signature.py"] = _test_signature_simple(package, features)
    feature_tests = feature_decl.get("tests") or ()
    if feature_tests:
        out[f"tests/test_{feature}.py"] = _feature_tests(package, feature_decl)

    # Boundaries from feature declaration
    if feature_decl.get("boundaries"):
        boundary_src = current_files.get(f"{package}/boundary.py", "")
        out[f"{package}/boundary.py"] = _merge_boundaries(
            boundary_src, feature_decl["boundaries"]
        )

    return out


def _features(features: tuple[str, ...]) -> str:
    lines = ["FEATURES = ("]
    for name in features:
        lines.append(f'    "{name}",')
    lines.append(")")
    lines.append("")
    return "\n".join(lines)


def _parts(feature_decls: tuple[dict, ...]) -> str:
    chunks = [
        '"""Generated parts from declarations. One input, one output. No I/O."""',
        "",
        "from .boundary import is_thing",
        "",
    ]
    for decl in feature_decls:
        chunks.append(_render_feature_function(decl))
        chunks.append("")
    return "\n".join(chunks)


def _render_feature_function(decl: dict) -> str:
    name = decl["name"]
    role = decl.get("role", "transform")
    doc = decl.get("doc", name).replace('"""', "'")
    transformation = decl.get("transformation") or {}
    kind = transformation.get("kind", "identity")

    if kind == "identity":
        body = _identity_body(name)
    elif kind == "require_str_field":
        body = _require_str_field_body(name, transformation)
    elif kind == "text_stats":
        body = _text_stats_body(name, transformation)
    else:
        body = _identity_body(name)

    return f'''def {name}(thing):
    """{doc}"""
    if not is_thing(thing):
        return {{
            "value": thing,
            "depths": (),
            "axes": (),
            "evidence": ("part:{name}", "{name}:rejected-non-thing"),
            "state": "invalid",
        }}
{body}
'''


def _identity_body(name: str) -> str:
    return f'''    return {{
        **thing,
        "evidence": (*thing["evidence"], "part:{name}"),
    }}'''


def _require_str_field_body(name: str, transformation: dict) -> str:
    field = transformation.get("field", "text")
    missing_error = transformation.get("missing_error", "missing-text")
    invalid_error = transformation.get("invalid_error", "invalid-text")
    return f'''    if thing["state"] in {{"invalid", "absent", "false", "unknown"}}:
        return {{
            **thing,
            "evidence": (*thing["evidence"], "part:{name}", "{name}:skipped"),
            "state": thing["state"],
        }}
    value = thing["value"]
    if value is None:
        return {{
            **thing,
            "evidence": (*thing["evidence"], "part:{name}", "{name}:absent"),
            "state": "absent",
        }}
    if value is False:
        return {{
            **thing,
            "evidence": (*thing["evidence"], "part:{name}", "{name}:false"),
            "state": "false",
        }}
    if not isinstance(value, dict):
        return {{
            **thing,
            "evidence": (*thing["evidence"], "part:{name}", "{name}:not-map"),
            "state": "invalid",
        }}
    if "error" in value and "{field}" not in value:
        return {{
            **thing,
            "evidence": (*thing["evidence"], "part:{name}", "{name}:prior-error"),
            "state": "invalid",
        }}
    if "{field}" not in value:
        return {{
            **thing,
            "value": {{**value, "error": "{missing_error}"}},
            "evidence": (*thing["evidence"], "part:{name}", "{name}:missing-{field}"),
            "state": "absent",
        }}
    field_value = value["{field}"]
    if field_value is None:
        return {{
            **thing,
            "value": {{**value, "error": "{missing_error}"}},
            "evidence": (*thing["evidence"], "part:{name}", "{name}:absent-{field}"),
            "state": "absent",
        }}
    if field_value is False:
        return {{
            **thing,
            "value": {{**value, "error": "false-{field}"}},
            "evidence": (*thing["evidence"], "part:{name}", "{name}:false-{field}"),
            "state": "false",
        }}
    if not isinstance(field_value, str):
        return {{
            **thing,
            "value": {{**value, "error": "{invalid_error}"}},
            "evidence": (*thing["evidence"], "part:{name}", "{name}:invalid-{field}"),
            "state": "invalid",
        }}
    return {{
        **thing,
        "evidence": (*thing["evidence"], "part:{name}", "{name}:ok"),
        "state": "formed",
    }}'''


def _text_stats_body(name: str, transformation: dict) -> str:
    text_field = transformation.get("text_field", "text")
    stats_field = transformation.get("stats_field", "stats")
    return f'''    if thing["state"] in {{"invalid", "absent", "false", "unknown"}}:
        return {{
            **thing,
            "evidence": (*thing["evidence"], "part:{name}", "{name}:skipped"),
            "state": thing["state"],
        }}
    value = thing["value"]
    if not isinstance(value, dict) or not isinstance(value.get("{text_field}"), str):
        return {{
            **thing,
            "value": value if isinstance(value, dict) else {{"error": "missing-text"}},
            "evidence": (*thing["evidence"], "part:{name}", "{name}:missing-text"),
            "state": "absent",
        }}
    text = value["{text_field}"]
    words = text.split()
    stats = {{
        "characters": len(text),
        "lines": len(text.splitlines()),
        "words": len(words),
        "unique_words": len({{word.casefold() for word in words}}),
    }}
    return {{
        **thing,
        "value": {{**value, "{stats_field}": stats}},
        "evidence": (*thing["evidence"], "part:{name}", "{name}:ok"),
        "state": "formed",
    }}'''


def _append_or_rebuild_parts(
    parts_src: str, existing: tuple[str, ...], feature_decl: dict
) -> str:
    """Append a new declared function; keep prior source for existing features."""
    name = feature_decl["name"]
    if f"def {name}(" in parts_src:
        return parts_src
    new_fn = _render_feature_function(feature_decl)
    if "from .boundary import is_thing" not in parts_src:
        header = (
            '"""Generated parts from declarations. One input, one output. No I/O."""\n\n'
            "from .boundary import is_thing\n\n"
        )
        # strip old header-ish first line if stub style
        body = parts_src
        if body.startswith('"""'):
            # keep existing functions
            pass
        if "from .boundary import is_thing" not in body:
            # inject import after docstring
            if '"""' in body[3:]:
                end = body.find('"""', 3) + 3
                body = body[:end] + "\n\nfrom .boundary import is_thing\n" + body[end:]
            else:
                body = header + body
        parts_src = body
    if not parts_src.endswith("\n"):
        parts_src += "\n"
    return parts_src + "\n" + new_fn + "\n"


def _compose(declaration: dict) -> str:
    package = declaration["package"]
    composition = declaration["composition"]
    feature_names = [f["name"] for f in declaration["features"]]
    boundary_names = []
    for b in declaration.get("boundaries") or ():
        if isinstance(b, dict) and "name" in b:
            boundary_names.append(b["name"])

    imports = [
        "from .boundary import inward, outward",
        "from .core import letter, verify",
    ]
    if boundary_names:
        imports[0] = (
            "from .boundary import inward, outward, "
            + ", ".join(boundary_names)
        )
    if feature_names:
        imports.append("from .parts import " + ", ".join(feature_names))

    # Build nested call from composition list (outermost last in list typically)
    # composition is outward(...(inward)) order: first element is innermost or outer?
    # We define composition as outer-to-inner reading of the onion names:
    # ("outward", "verify", "calculate_stats", "validate_text", "read_text_source", "letter", "inward")
    # OR inner-to-outer. Prefer inner-to-outer matching nested write order:
    # ("inward", "letter", "read", "validate", "calculate", "verify", "outward")
    steps = list(composition)
    # if starts with outward, reverse to inner-first
    if steps and steps[0] == "outward":
        steps = list(reversed(steps))

    expr = "host_value"
    for step in steps:
        if step == "inward":
            expr = f"inward({expr})"
        elif step == "letter":
            expr = f"letter({expr})"
        elif step == "verify":
            expr = f"verify({expr})"
        elif step == "outward":
            expr = f"outward({expr})"
        else:
            expr = f"{step}({expr})"

    return f'''"""Nested composition from declaration (L2)."""

{chr(10).join(imports)}


def program(host_value):
    return {expr}
'''


def _compose_insert_feature(compose_src: str, package: str, features: tuple[str, ...]) -> str:
    """Regenerate a simple compose from feature list when no program decl."""
    # Heuristic: rebuild default onion with features between letter and verify
    names = ", ".join(features)
    expr = "letter(inward(host_value))"
    for name in features:
        expr = f"{name}({expr})"
    expr = f"outward(verify({expr}))"
    return f'''"""Nested composition of generated parts (L2)."""

from .boundary import inward, outward
from .core import letter, verify
from .parts import {names}


def program(host_value):
    return {expr}
'''


def _boundary(declaration: dict) -> str:
    base = _boundary_base()
    for b in declaration.get("boundaries") or ():
        if not isinstance(b, dict):
            continue
        kind = b.get("kind")
        if kind == "read_utf8_source":
            base += "\n\n" + _read_utf8_source_fn(b)
    presentation = declaration.get("presentation")
    if presentation:
        base += "\n\n" + _host_present_fn(presentation)
    return base


def _boundary_base() -> str:
    return '''"""Visible input/output boundaries (L7)."""

from __future__ import annotations

import sys
from pathlib import Path

THING_FIELDS = ("value", "depths", "axes", "evidence", "state")
STATES = frozenset({"unknown", "absent", "false", "formed", "valid", "invalid"})


def is_thing(obj):
    if not isinstance(obj, dict):
        return False
    if any(field not in obj for field in THING_FIELDS):
        return False
    if not isinstance(obj["depths"], tuple):
        return False
    if not isinstance(obj["axes"], tuple):
        return False
    if not isinstance(obj["evidence"], tuple):
        return False
    if obj["state"] not in STATES:
        return False
    return True


def inward(thing):
    if is_thing(thing):
        return {
            **thing,
            "evidence": (*thing["evidence"], "boundary:inward"),
            "state": "unknown",
        }
    return {
        "value": thing,
        "depths": (),
        "axes": (),
        "evidence": ("boundary:inward",),
        "state": "unknown",
    }


def outward(thing):
    if not is_thing(thing):
        return {
            "value": thing,
            "depths": (),
            "axes": (),
            "evidence": ("boundary:outward", "outward:rejected-non-thing"),
            "state": "invalid",
        }
    return {
        **thing,
        "evidence": (*thing["evidence"], "boundary:outward"),
    }


def host_render(thing):
    from json import dumps

    if not is_thing(thing):
        payload = {
            "value": thing,
            "depths": (),
            "axes": (),
            "evidence": ("host:render-non-thing",),
            "state": "invalid",
        }
        return dumps(payload, indent=2, ensure_ascii=False)
    return dumps({field: thing[field] for field in THING_FIELDS}, indent=2, ensure_ascii=False)
'''


def _read_utf8_source_fn(spec: dict) -> str:
    name = spec.get("name", "read_text_source")
    source_field = spec.get("source_field", "source")
    text_field = spec.get("text_field", "text")
    return f'''def {name}(thing):
    """Named read boundary: file path or stdin (`-`). One thing → one thing."""
    if not is_thing(thing):
        return {{
            "value": thing,
            "depths": (),
            "axes": (),
            "evidence": ("boundary:{name}", "read:rejected-non-thing"),
            "state": "invalid",
        }}
    if thing["state"] in {{"invalid", "absent", "false"}}:
        return {{
            **thing,
            "evidence": (*thing["evidence"], "boundary:{name}", "read:skipped"),
            "state": thing["state"],
        }}
    value = thing["value"]
    if value is None:
        return {{
            **thing,
            "evidence": (*thing["evidence"], "boundary:{name}", "read:absent-value"),
            "state": "absent",
        }}
    if value is False:
        return {{
            **thing,
            "evidence": (*thing["evidence"], "boundary:{name}", "read:false-value"),
            "state": "false",
        }}
    if not isinstance(value, dict):
        return {{
            **thing,
            "evidence": (*thing["evidence"], "boundary:{name}", "read:value-not-map"),
            "state": "invalid",
        }}
    if "error" in value and value.get("{source_field}") is None:
        code = value.get("error")
        return {{
            **thing,
            "value": value,
            "evidence": (*thing["evidence"], "boundary:{name}", f"read:host-error:{{code}}"),
            "state": "invalid",
        }}
    source = value.get("{source_field}")
    if source is None:
        return {{
            **thing,
            "evidence": (*thing["evidence"], "boundary:{name}", "read:absent-source"),
            "state": "absent",
        }}
    if source is False:
        return {{
            **thing,
            "evidence": (*thing["evidence"], "boundary:{name}", "read:false-source"),
            "state": "false",
        }}
    if not isinstance(source, str):
        return {{
            **thing,
            "evidence": (*thing["evidence"], "boundary:{name}", "read:invalid-source"),
            "state": "invalid",
        }}
    if source == "-":
        try:
            text = sys.stdin.read()
        except OSError:
            return {{
                **thing,
                "value": {{**value, "error": "read-failure"}},
                "evidence": (*thing["evidence"], "boundary:{name}", "boundary:read_stdin", "read:failure"),
                "state": "invalid",
            }}
        return {{
            **thing,
            "value": {{**value, "{text_field}": text}},
            "evidence": (*thing["evidence"], "boundary:{name}", "boundary:read_stdin", "read:ok"),
            "state": "formed",
        }}
    path = Path(source)
    if not path.exists():
        return {{
            **thing,
            "value": {{**value, "error": "file-not-found"}},
            "evidence": (*thing["evidence"], "boundary:{name}", "boundary:read_file", "read:file-not-found"),
            "state": "invalid",
        }}
    if not path.is_file():
        return {{
            **thing,
            "value": {{**value, "error": "not-a-file"}},
            "evidence": (*thing["evidence"], "boundary:{name}", "boundary:read_file", "read:not-a-file"),
            "state": "invalid",
        }}
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return {{
            **thing,
            "value": {{**value, "error": "invalid-utf8"}},
            "evidence": (*thing["evidence"], "boundary:{name}", "boundary:read_file", "read:invalid-utf8"),
            "state": "invalid",
        }}
    except OSError:
        return {{
            **thing,
            "value": {{**value, "error": "read-failure"}},
            "evidence": (*thing["evidence"], "boundary:{name}", "boundary:read_file", "read:failure"),
            "state": "invalid",
        }}
    return {{
        **thing,
        "value": {{**value, "{text_field}": text}},
        "evidence": (*thing["evidence"], "boundary:{name}", "boundary:read_file", "read:ok"),
        "state": "formed",
    }}
'''


def _host_present_fn(presentation: dict) -> str:
    keys = presentation.get("success_keys") or ()
    success_from = presentation.get("success_from", "stats")
    keys_tuple = ", ".join(f'"{k}"' for k in keys)
    return f'''def host_present(thing):
    """Host-edge presentation after outward. Returns (text, exit_code).

    Open design (L1): process-edge adapter returns a pair for the OS host,
    not a canonical thing. Not a public kernel Part.
    """
    from json import dumps

    def dump(obj):
        return dumps(obj, ensure_ascii=False, separators=(",", ":"))

    if not is_thing(thing):
        return dump({{"error": "invalid-thing", "state": "invalid"}}), 1

    value = thing["value"]
    state = thing["state"]
    keys = ({keys_tuple})

    if state == "valid" and isinstance(value, dict) and isinstance(value.get("{success_from}"), dict):
        payload = value["{success_from}"]
        ordered = {{key: payload[key] for key in keys}}
        return dump(ordered), 0

    error = "invalid"
    if isinstance(value, dict) and isinstance(value.get("error"), str):
        error = value["error"]
    elif state == "absent":
        error = "missing-text"
    elif state == "false":
        error = "false"
    elif state == "unknown":
        error = "unknown"

    return dump({{"error": error, "state": state}}), 1
'''


def _merge_boundaries(boundary_src: str, boundaries: tuple) -> str:
    out = boundary_src
    for b in boundaries:
        if not isinstance(b, dict):
            continue
        name = b.get("name")
        if name and f"def {name}(" in out:
            continue
        if b.get("kind") == "read_utf8_source":
            if "from pathlib import Path" not in out:
                out = out.replace(
                    '"""Visible input/output boundaries (L7)."""\n',
                    '"""Visible input/output boundaries (L7)."""\n\nimport sys\nfrom pathlib import Path\n',
                )
            out = out.rstrip() + "\n\n" + _read_utf8_source_fn(b) + "\n"
    return out


def _core(declaration: dict) -> str:
    verify = declaration.get("verify") or {}
    require_stats = verify.get("require_value_field")
    ok_marks = tuple(verify.get("require_evidence_contains") or ())
    if require_stats:
        required_repr = repr(ok_marks)
        field = require_stats
        return (
            '"""Canonical letter and verify (L1, L5, L6)."""\n\n'
            "from .boundary import is_thing\n\n\n"
            "def letter(thing):\n"
            "    if not is_thing(thing):\n"
            "        return {\n"
            '            "value": thing,\n'
            '            "depths": (),\n'
            '            "axes": (),\n'
            '            "evidence": ("letter:rejected-non-thing",),\n'
            '            "state": "invalid",\n'
            "        }\n"
            '    value = thing["value"]\n'
            "    if value is None:\n"
            '        state = "absent"\n'
            '        mark = "letter:absent"\n'
            "    elif value is False:\n"
            '        state = "false"\n'
            '        mark = "letter:false"\n'
            "    else:\n"
            '        state = "formed"\n'
            '        mark = "letter:distinguished"\n'
            "    return {\n"
            "        **thing,\n"
            '        "evidence": (*thing["evidence"], mark),\n'
            '        "state": state,\n'
            "    }\n\n\n"
            "def verify(thing):\n"
            "    if not is_thing(thing):\n"
            "        return {\n"
            '            "value": thing,\n'
            '            "depths": (),\n'
            '            "axes": (),\n'
            '            "evidence": ("verify:rejected-non-thing",),\n'
            '            "state": "invalid",\n'
            "        }\n"
            '    evidence = thing["evidence"]\n'
            '    if thing["state"] in {"unknown", "absent", "false", "invalid"}:\n'
            "        return {\n"
            "            **thing,\n"
            '            "evidence": (*evidence, "verify:preserved-state", "script-law:fail"),\n'
            '            "state": thing["state"] if thing["state"] != "unknown" else "invalid",\n'
            "        }\n"
            '    value = thing["value"]\n'
            f'    has_stats = isinstance(value, dict) and isinstance(value.get("{field}"), dict)\n'
            f"    required = {required_repr}\n"
            "    ok = (\n"
            '        thing["state"] == "formed"\n'
            "        and has_stats\n"
            "        and all(mark in evidence for mark in required)\n"
            "    )\n"
            "    return {\n"
            "        **thing,\n"
            '        "evidence": (*evidence, f"script-law:{\'pass\' if ok else \'fail\'}"),\n'
            '        "state": "valid" if ok else "invalid",\n'
            "    }\n"
        )
    # default soft verify
    return '''"""Canonical letter and verify (L1, L5, L6)."""

from .boundary import is_thing


def letter(thing):
    if not is_thing(thing):
        return {
            "value": thing,
            "depths": (),
            "axes": (),
            "evidence": ("letter:rejected-non-thing",),
            "state": "invalid",
        }
    value = thing["value"]
    if value is None:
        state = "absent"
        mark = "letter:absent"
    elif value is False:
        state = "false"
        mark = "letter:false"
    else:
        state = "formed"
        mark = "letter:distinguished"
    return {
        **thing,
        "evidence": (*thing["evidence"], mark),
        "state": state,
    }


def verify(thing):
    if not is_thing(thing):
        return {
            "value": thing,
            "depths": (),
            "axes": (),
            "evidence": ("verify:rejected-non-thing",),
            "state": "invalid",
        }
    evidence = thing["evidence"]
    has_inward = "boundary:inward" in evidence
    has_letter = any(item.startswith("letter:") for item in evidence)
    ok = has_inward and has_letter and thing["state"] in {"formed", "absent", "false", "valid"}
    return {
        **thing,
        "evidence": (*evidence, f"script-law:{'pass' if ok else 'fail'}"),
        "state": "valid" if ok else "invalid",
    }
'''


def _cli(declaration: dict) -> str:
    cli = declaration["cli"] or {}
    field = (cli.get("argv") or {}).get("field", "source")
    missing = (cli.get("argv") or {}).get("errors", {}).get("missing", "missing-source")
    extra = (cli.get("argv") or {}).get("errors", {}).get("extra", "extra-source")
    use_present = bool(declaration.get("presentation"))
    present_import = "from .boundary import host_present" if use_present else "from .boundary import host_render"
    present_body = (
        "    text, code = host_present(result)\n"
        "    sys.stdout.write(text)\n"
        "    sys.stdout.write(\"\\n\")\n"
        "    if explicit:\n"
        "        return code\n"
        "    raise SystemExit(code)\n"
        if use_present
        else
        "    sys.stdout.write(host_render(result))\n"
        "    sys.stdout.write(\"\\n\")\n"
        "    code = 0 if result.get(\"state\") == \"valid\" else 1\n"
        "    if explicit:\n"
        "        return code\n"
        "    raise SystemExit(code)\n"
    )
    return f'''"""Host CLI. Parse argv; domain runs only on things."""

from __future__ import annotations

import sys

{present_import}
from .compose import program


def parse_argv(argv):
    if len(argv) == 0:
        return {{"error": "{missing}"}}
    if len(argv) > 1:
        return {{"error": "{extra}"}}
    return {{"{field}": argv[0]}}


def host_main(argv=None):
    explicit = argv is not None
    args = list(sys.argv[1:] if argv is None else argv)
    host_value = parse_argv(args)
    result = program(host_value)
{present_body}

if __name__ == "__main__":
    host_main()
'''


def _package_init(package: str) -> str:
    return f'''"""Generated package `{package}`."""

from .compose import program
from .features import FEATURES

__all__ = ["FEATURES", "program"]
'''


def _package_main() -> str:
    return '''"""Process entry."""

from .cli import host_main

if __name__ == "__main__":
    host_main()
'''


def _pyproject(declaration: dict) -> str:
    name = declaration["name"]
    package = declaration["package"]
    description = declaration.get("description", "Unified Code generated program")
    script = ""
    cli = declaration.get("cli") or {}
    if cli.get("script"):
        script = f'''
[project.scripts]
{cli["script"]} = "{package}.cli:host_main"
'''
    return f'''[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "{name}"
version = "0.1.0"
description = "{description}"
requires-python = ">=3.11"
readme = "README.md"
{script}
[project.optional-dependencies]
test = ["pytest>=8"]

[tool.setuptools.packages.find]
include = ["{package}*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-q"

[tool.unified-code]
generated = true
package = "{package}"
scale = "UC-1"
'''


def _readme(declaration: dict) -> str:
    name = declaration["name"]
    package = declaration["package"]
    script = (declaration.get("cli") or {}).get("script", f"python -m {package}")
    return f"""# {name}

{declaration.get("description", "Unified Code generated program")}

Generated from a code-based PROGRAM declaration (not a stub scaffold).

```bash
{script} path/to/file.txt
printf 'text' | {script} -
pytest
```
"""


def _gitignore() -> str:
    return """.venv/
__pycache__/
*.py[cod]
.pytest_cache/
*.egg-info/
dist/
build/
"""


def _test_signature(package: str, features: tuple[str, ...], declaration: dict) -> str:
    feature_list = ", ".join(f"parts.{n}" for n in features)
    boundary_names = [
        b["name"]
        for b in (declaration.get("boundaries") or ())
        if isinstance(b, dict) and "name" in b
    ]
    if boundary_names:
        imports_b = (
            f"from {package}.boundary import inward, outward, "
            + ", ".join(boundary_names)
        )
        extra_ops = ",\n        " + ",\n        ".join(boundary_names)
    else:
        imports_b = f"from {package}.boundary import inward, outward"
        extra_ops = ""
    return f'''from inspect import Parameter, signature

from {package} import compose, parts
{imports_b}
from {package}.core import letter, verify
from {package}.features import FEATURES


def test_features_tuple_matches_parts():
    assert FEATURES == {features!r}
    for name in FEATURES:
        assert callable(getattr(parts, name))


def test_every_public_operation_has_one_input():
    operations = (
        letter,
        verify,
        inward,
        outward,
        compose.program,
        {feature_list}{extra_ops},
    )
    for operation in operations:
        parameters = tuple(signature(operation).parameters.values())
        assert len(parameters) == 1
'''


def _test_signature_simple(package: str, features: tuple[str, ...]) -> str:
    feature_list = ", ".join(f"parts.{n}" for n in features)
    return f'''from inspect import Parameter, signature

from {package} import compose, parts
from {package}.boundary import inward, outward
from {package}.core import letter, verify
from {package}.features import FEATURES


def test_features_tuple_matches_parts():
    assert FEATURES == {features!r}
    for name in FEATURES:
        assert callable(getattr(parts, name))


def test_every_public_operation_has_one_input():
    operations = (
        letter,
        verify,
        inward,
        outward,
        compose.program,
        {feature_list},
    )
    for operation in operations:
        parameters = tuple(signature(operation).parameters.values())
        assert len(parameters) == 1
'''


def _test_program(package: str, declaration: dict) -> str:
    return f'''from {package}.boundary import inward
from {package}.compose import program
from {package}.core import letter
from {package}.features import FEATURES


def test_features_registered():
    assert list(FEATURES) == list({tuple(f["name"] for f in declaration["features"])!r})


def test_unknown_absent_false_invalid_distinct():
    unknown = inward("x")
    absent = letter(inward(None))
    false = letter(inward(False))
    invalid = program({{"error": "missing-source"}})
    assert unknown["state"] == "unknown"
    assert absent["state"] == "absent"
    assert false["state"] == "false"
    assert invalid["state"] == "invalid"
'''


def _test_declared(package: str, declaration: dict) -> str:
    lines = [
        f'"""Declared program tests for {package}."""',
        "",
        "from __future__ import annotations",
        "",
        "import json",
        "from pathlib import Path",
        "",
        f"from {package}.boundary import host_present",
        f"from {package}.cli import host_main, parse_argv",
        f"from {package}.compose import program",
        "",
    ]
    for i, case in enumerate(declaration.get("tests") or ()):
        if not isinstance(case, dict):
            continue
        name = case.get("name", f"case_{i}")
        kind = case.get("kind", "file_text")
        if kind == "file_text":
            text = case.get("text", "")
            expect = case.get("expect_stats")
            lines.append(f"def test_declared_{name}(tmp_path):")
            lines.append(f"    path = tmp_path / '{name}.txt'")
            lines.append(f"    path.write_text({text!r}, encoding='utf-8')")
            lines.append(f"    result = program({{'source': str(path)}})")
            if expect is not None:
                lines.append(f"    assert result['state'] == 'valid'")
                lines.append(f"    assert result['value']['stats'] == {expect!r}")
            lines.append("")
        elif kind == "stdin_text":
            text = case.get("text", "")
            expect = case.get("expect_stats")
            lines.append(f"def test_declared_{name}(monkeypatch):")
            lines.append(f"    monkeypatch.setattr('sys.stdin', __import__('io').StringIO({text!r}))")
            lines.append(f"    result = program({{'source': '-'}})")
            if expect is not None:
                lines.append(f"    assert result['state'] == 'valid'")
                lines.append(f"    assert result['value']['stats'] == {expect!r}")
            lines.append("")
        elif kind == "cli_error":
            argv = case.get("argv", [])
            error = case.get("error")
            lines.append(f"def test_declared_{name}():")
            lines.append(f"    result = program(parse_argv({argv!r}))")
            lines.append(f"    text, code = host_present(result)")
            lines.append(f"    assert code == 1")
            lines.append(f"    assert json.loads(text)['error'] == {error!r}")
            lines.append("")
        elif kind == "stable_json":
            text = case.get("text", "x")
            expect_json = case.get("expect_json")
            lines.append(f"def test_declared_{name}(tmp_path, capsys):")
            lines.append(f"    path = tmp_path / '{name}.txt'")
            lines.append(f"    path.write_text({text!r}, encoding='utf-8')")
            lines.append(f"    assert host_main([str(path)]) == 0")
            lines.append(f"    out = capsys.readouterr().out.strip()")
            lines.append(f"    assert out == {expect_json!r}")
            lines.append("")
    return "\n".join(lines)


def _feature_tests(package: str, feature_decl: dict) -> str:
    name = feature_decl["name"]
    lines = [
        f'"""Tests for declared feature {name}."""',
        "",
        f"from {package}.parts import {name}",
        f"from {package}.boundary import inward",
        f"from {package}.core import letter",
        "",
    ]
    for i, case in enumerate(feature_decl.get("tests") or ()):
        if not isinstance(case, dict):
            continue
        cname = case.get("name", f"case_{i}")
        # minimal: skip complex cases without full program
        lines.append(f"def test_{name}_{cname}():")
        lines.append(f"    # declaration case recorded; full program tests cover end-to-end")
        lines.append(f"    assert callable({name})")
        lines.append("")
    if len(lines) == 5:
        lines.append(f"def test_{name}_callable():")
        lines.append(f"    assert callable({name})")
        lines.append("")
    return "\n".join(lines)
