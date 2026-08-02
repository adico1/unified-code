"""Ephemeral request adapter over the existing declaration compiler and UEM.

The canonical application authority remains a JSON declaration. Request
adapters only select that authority and provide one host input; they never
define or execute application behavior.
"""

from __future__ import annotations

import ast
import hashlib
import json
import shutil
import tempfile
from pathlib import Path

from .boundary import inward, outward
from .generator.declaration import load_declaration_module
from .machine.compile_decl import compile_declaration, write_artifacts
from .machine.host import run_compiled
from .machine.thing import blank_thing


REQUEST_STANDARD = "uc.run-request/1"
PYTHON_BINDING = "STANDARD_TEN"


def canonical_bytes(value):
    """Return path- and insertion-order-independent JSON bytes."""
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def canonical_sha256(value):
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def adapt_request(thing):
    """Read JSON or restricted-Python request data. Thing -> Thing."""
    value = thing.get("value") if isinstance(thing.get("value"), dict) else {}
    raw_path = value.get("request_path")
    if not isinstance(raw_path, str) or not raw_path:
        return _invalid(thing, "request-path-required", "request:path-invalid")
    path = Path(raw_path).expanduser().resolve()
    if not path.is_file():
        return _invalid(thing, "request-not-found", "request:not-found")
    adapters = {".json": _read_json_request, ".py": _read_python_request}
    adapter = adapters.get(path.suffix.lower())
    if adapter is None:
        return _invalid(thing, "request-format-unsupported", "request:format-unsupported")
    try:
        request = adapter(path)
    except (OSError, UnicodeError, SyntaxError, ValueError, TypeError) as error:
        return _invalid(thing, f"request-invalid:{error}", "request:parse-rejected")
    error = _validate_request(request)
    if error is not None:
        return _invalid(thing, error, "request:contract-rejected")
    declaration_path = (path.parent / request["declaration"]).resolve()
    return {
        **thing,
        "value": {
            **value,
            "request_path": str(path),
            "request_format": path.suffix.lower()[1:],
            "request": request,
            "declaration_path": str(declaration_path),
        },
        "evidence": (
            *tuple(thing.get("evidence") or ()),
            "request:adapted",
            f"request:format:{path.suffix.lower()[1:]}",
        ),
        "state": "formed",
    }


def resolve_authority(thing):
    """Resolve the selected canonical JSON declaration. Thing -> Thing."""
    if thing.get("state") == "invalid":
        return thing
    value = thing.get("value") if isinstance(thing.get("value"), dict) else {}
    path = value.get("declaration_path")
    if not isinstance(path, str) or Path(path).suffix.lower() != ".json":
        return _invalid(thing, "canonical-json-declaration-required", "authority:rejected")
    loaded = load_declaration_module(inward({"declaration_path": path}))
    if loaded.get("state") != "formed":
        error = (loaded.get("value") or {}).get("error", "declaration-load-failed")
        return _invalid(thing, error, "authority:load-failed")
    declaration = loaded["value"]["declaration"]
    plain = json.loads(canonical_bytes(declaration).decode("utf-8"))
    seed_sha256 = canonical_sha256(plain)
    return {
        **thing,
        "value": {
            **value,
            "declaration": declaration,
            "canonical_declaration": plain,
            "canonical_seed_sha256": seed_sha256,
        },
        "evidence": (*tuple(thing.get("evidence") or ()), "authority:resolved"),
        "state": "formed",
    }


def compile_request(thing):
    """Compile through the existing UEM declaration compiler. Thing -> Thing."""
    if thing.get("state") == "invalid":
        return thing
    value = thing.get("value") if isinstance(thing.get("value"), dict) else {}
    compiled = compile_declaration(blank_thing({"declaration": value.get("declaration")}))
    if compiled.get("state") == "invalid":
        return _invalid(thing, "uem-compilation-failed", "compile:failed")
    return {
        **thing,
        "value": {**value, "compiled": compiled},
        "evidence": (*tuple(thing.get("evidence") or ()), "compile:uem"),
        "state": "formed",
    }


def execute_request(thing):
    """Execute the compiled UEM program with request host data. Thing -> Thing."""
    if thing.get("state") == "invalid":
        return thing
    value = thing.get("value") if isinstance(thing.get("value"), dict) else {}
    request = value.get("request") or {}
    executed = run_compiled(value["compiled"], request["host_input"])
    if executed.get("state") == "invalid":
        return _invalid(thing, "uem-execution-failed", "execute:failed")
    machine = executed.get("value") or {}
    runtime_result = {
        key: machine.get(key)
        for key in (
            "presentation", "stats", "error", "path", "ticket", "steps",
            "instruction_count", "outward_log", "events_emitted",
            "events_dequeued",
        )
    }
    compiled_value = value["compiled"]["value"]
    execution_identity = canonical_sha256(
        {
            "canonical_seed_sha256": value["canonical_seed_sha256"],
            "host_input": request["host_input"],
            "program_sha256": compiled_value["program_sha256"],
        }
    )
    return {
        **thing,
        "value": {
            **value,
            "program_sha256": compiled_value["program_sha256"],
            "execution_identity": execution_identity,
            "runtime_result": runtime_result,
        },
        "evidence": (*tuple(thing.get("evidence") or ()), "execute:uem"),
        "state": "formed",
    }


def materialize_request(thing):
    """Atomically retain compiled artifacts only when explicitly requested."""
    if thing.get("state") == "invalid":
        return thing
    value = thing.get("value") if isinstance(thing.get("value"), dict) else {}
    raw_output = value.get("materialize")
    if raw_output in (None, False):
        return {
            **thing,
            "value": {**value, "materialized": False, "artifact_path": None},
            "evidence": (*tuple(thing.get("evidence") or ()), "artifact:ephemeral"),
            "state": "valid",
        }
    if not isinstance(raw_output, str) or not raw_output:
        return _invalid(thing, "materialize-path-invalid", "artifact:path-invalid")
    output = Path(raw_output).expanduser().resolve()
    if output == Path(output.anchor):
        return _invalid(thing, "materialize-path-unsafe", "artifact:path-unsafe")
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{output.name}.stage-", dir=output.parent))
    backup = Path(tempfile.mkdtemp(prefix=f".{output.name}.backup-", dir=output.parent))
    backup.rmdir()
    try:
        write_artifacts(value["compiled"], str(stage))
        manifest = {
            "format": "uc.materialized-uem/1",
            "canonical_seed_sha256": value["canonical_seed_sha256"],
            "execution_identity": value["execution_identity"],
            "program_sha256": value["program_sha256"],
        }
        (stage / "manifest.json").write_bytes(canonical_bytes(manifest) + b"\n")
        if output.exists():
            output.replace(backup)
        stage.replace(output)
        if backup.exists():
            shutil.rmtree(backup)
    except Exception as error:
        if output.exists() and backup.exists():
            shutil.rmtree(output)
        if backup.exists():
            backup.replace(output)
        if stage.exists():
            shutil.rmtree(stage)
        return _invalid(thing, f"materialize-failed:{error}", "artifact:publish-failed")
    return {
        **thing,
        "value": {**value, "materialized": True, "artifact_path": str(output)},
        "evidence": (*tuple(thing.get("evidence") or ()), "artifact:materialized"),
        "state": "valid",
    }


def run_ephemeral(thing):
    """Adapt -> resolve -> compile -> execute -> optionally materialize."""
    formed = materialize_request(
        execute_request(compile_request(resolve_authority(adapt_request(thing))))
    )
    if formed.get("state") == "invalid":
        return outward(formed)
    value = formed["value"]
    public = {
        key: value.get(key)
        for key in (
            "request_format", "canonical_seed_sha256", "program_sha256",
            "execution_identity", "runtime_result", "materialized",
            "artifact_path",
        )
    }
    return outward({**formed, "value": public})


def _read_json_request(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _read_python_request(path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    body = [
        node for node in tree.body
        if not (
            isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        )
    ]
    if len(body) != 1 or not isinstance(body[0], ast.Assign):
        raise ValueError("python-request-shape")
    assignment = body[0]
    if (
        len(assignment.targets) != 1
        or not isinstance(assignment.targets[0], ast.Name)
        or assignment.targets[0].id != PYTHON_BINDING
    ):
        raise ValueError("python-request-binding")
    return json.loads(json.dumps(ast.literal_eval(assignment.value)))


def _validate_request(request):
    if not isinstance(request, dict):
        return "request-not-object"
    if set(request) != {"standard", "declaration", "host_input"}:
        return "request-fields-invalid"
    if request.get("standard") != REQUEST_STANDARD:
        return "request-standard-invalid"
    declaration = request.get("declaration")
    if not isinstance(declaration, str) or not declaration:
        return "request-declaration-invalid"
    if not isinstance(request.get("host_input"), dict):
        return "request-host-input-invalid"
    return None


def _invalid(thing, error, evidence):
    value = thing.get("value") if isinstance(thing.get("value"), dict) else {}
    return {
        **thing,
        "value": {**value, "error": error},
        "evidence": (*tuple(thing.get("evidence") or ()), evidence),
        "state": "invalid",
    }
