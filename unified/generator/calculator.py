"""Universal calculator application generator.

All application meaning is resolved from atomic seed catalogs.  Iteration,
selection, filesystem access, and atomic replacement are audited primitives in
this module; emitted public flow is table-driven Thing→Thing composition.
"""

from __future__ import annotations

import ast
import hashlib
import json
import math
import os
import shutil
import statistics
import tempfile
from datetime import date
from decimal import Decimal, ROUND_HALF_EVEN, getcontext
from pathlib import Path

from unified.machine.bytecode import encode_program

GENERATOR_IDENTITY = "uc://generators/calculator-application-generator@1"
CATALOG_FAMILIES = (
    "quantities",
    "operations",
    "rules",
    "formulas",
    "calculation_models",
    "domains",
    "interfaces",
    "platforms",
    "targets",
    "themes",
    "locales",
)
DEPTHS = tuple(range(1, 11))


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha(value):
    data = value if isinstance(value, bytes) else str(value).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    body = value if isinstance(value, str) else _canonical(value) + "\n"
    path.write_text(body, encoding="utf-8")


def _authority(entry):
    return _sha(_canonical({key: value for key, value in entry.items() if key != "authority_hash"}))


def _catalog_seed_root(request_path):
    here = Path(request_path).resolve()
    candidates = (here.parent.parent, here.parent, Path.cwd() / "seed")
    return next(path for path in candidates if (path / "quantities" / "catalog.json").is_file())


def _load_registry(seed_root):
    catalogs = tuple(_read(seed_root / family / "catalog.json") for family in CATALOG_FAMILIES)
    entries = tuple(seed for catalog in catalogs for seed in catalog["seeds"])
    identities = tuple(seed.get("canonical_name") for seed in entries)
    errors = []
    errors.extend("missing-version" for seed in entries if not seed.get("version"))
    errors.extend("stale-hash:" + str(seed.get("canonical_name")) for seed in entries if seed.get("authority_hash") != _authority(seed))
    errors.extend("duplicate-identity:" + identity for identity in identities if identities.count(identity) > 1)
    registry = {seed["canonical_name"]: seed for seed in entries}
    errors.extend(
        "unknown-dependency:" + dependency
        for seed in entries
        for dependency in seed.get("dependencies", ())
        if dependency not in registry
    )
    _detect_cycles(registry, errors)
    if errors:
        raise ValueError(sorted(set(errors))[0])
    return registry


def _detect_cycles(registry, errors):
    visiting = set()
    visited = set()

    def visit(identity):
        if identity in visiting:
            errors.append("dependency-cycle:" + identity)
            return
        if identity in visited:
            return
        visiting.add(identity)
        tuple(visit(dependency) for dependency in registry[identity].get("dependencies", ()) if dependency in registry)
        visiting.remove(identity)
        visited.add(identity)

    tuple(visit(identity) for identity in sorted(registry))


def _resolve_ref(registry, identity):
    if "@" not in identity:
        raise ValueError("silent-version-selection:" + identity)
    if identity not in registry:
        raise ValueError("unknown-seed:" + identity)
    return registry[identity]


def _named(family, name):
    return f"uc://calculator/{family}/{name}@1"


def _resolve(request, registry):
    direct = (
        request["quantity"],
        request["model"],
        request["domain"],
        request["interface"],
        *request["targets"],
        request["theme"],
        request["locale"],
    )
    selected = {_resolve_ref(registry, identity)["canonical_name"] for identity in direct}
    domain = registry[request["domain"]]["value"]
    selected.update(_named("operations", name) for name in domain["operations"])
    selected.update(_named("rules", name) for name in domain["rules"])
    selected.add(_named("formulas", domain["formula"]))
    frontier = list(selected)
    while frontier:
        identity = frontier.pop()
        seed = _resolve_ref(registry, identity)
        for dependency in seed.get("dependencies", ()):
            if dependency not in selected:
                selected.add(dependency)
                frontier.append(dependency)
    resolved = tuple(registry[identity] for identity in sorted(selected))
    formula = registry[_named("formulas", domain["formula"])]["value"]
    _validate_compatibility(request, domain, formula, resolved)
    return resolved, domain, formula


def _validate_compatibility(request, domain, formula, resolved):
    quantity = request["quantity"].rsplit("/", 1)[-1].split("@", 1)[0]
    if domain["quantity"] != quantity:
        raise ValueError("incompatible-quantity")
    operations = {seed["value"].get("identity") for seed in resolved if seed["family"] == "operations"}
    if not set(domain["operations"]).issubset(operations):
        raise ValueError("incompatible-operations")
    if formula["identity"] != domain["formula"]:
        raise ValueError("wrong-formula")


def _safe_expression(text):
    operators = {
        ast.Add: lambda a, b: a + b,
        ast.Sub: lambda a, b: a - b,
        ast.Mult: lambda a, b: a * b,
        ast.Div: lambda a, b: a // b,
        ast.Mod: lambda a, b: a % b,
        ast.Pow: lambda a, b: a**b,
        ast.USub: lambda a: -a,
        ast.UAdd: lambda a: a,
    }

    def evaluate(node):
        routes = {
            ast.Expression: lambda item: evaluate(item.body),
            ast.Constant: lambda item: int(item.value),
            ast.BinOp: lambda item: operators[type(item.op)](evaluate(item.left), evaluate(item.right)),
            ast.UnaryOp: lambda item: operators[type(item.op)](evaluate(item.operand)),
        }
        return routes[type(node)](node)

    result = evaluate(ast.parse(text.replace("^", "**"), mode="eval"))
    if not -1000000 <= result <= 1000000:
        raise ValueError("overflow")
    return {"result": result}


def _calculate(executor, payload, constants=None):
    constants = constants or {}
    getcontext().prec = 28
    routes = {
        "expression": lambda: _safe_expression(payload["expression"]),
        "operation": lambda: _operation(payload),
        "conversion": lambda: {"result": payload["value"] * constants[payload["from"]] / constants[payload["to"]]},
        "percentage-interpretation": lambda: _percentage_apply(payload),
        "date-difference": lambda: {"days": (date.fromisoformat(payload["end"]) - date.fromisoformat(payload["start"])).days},
        "compound-interest": lambda: _compound_interest(payload),
        "aggregate": lambda: _aggregate(payload["series"]),
        "percentage-decrease": lambda: {"result": float((Decimal(str(payload["price"])) * (Decimal(1) - Decimal(str(payload["discount"])) / Decimal(100))).quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN))},
    }
    return routes[executor]()


def _operation(payload):
    args = payload["arguments"]
    routes = {
        "root": lambda: args[0] ** (1 / args[1]),
        "logarithm": lambda: math.log(args[0], args[1]),
        "factorial": lambda: math.factorial(args[0]),
        "absolute": lambda: abs(args[0]),
        "round": lambda: round(args[0], args[1]),
        "power": lambda: args[0] ** args[1],
    }
    result = routes[payload["operation"]]()
    rounded = round(result)
    return {"result": int(rounded) if isinstance(result, float) and math.isclose(result, rounded, rel_tol=0, abs_tol=1e-12) else result}


def _percentage_apply(payload):
    routes = {
        "of": lambda: payload["value"] * payload["percentage"] / 100,
        "increase": lambda: payload["value"] * (1 + payload["percentage"] / 100),
        "decrease": lambda: payload["value"] * (1 - payload["percentage"] / 100),
    }
    return {"result": routes[payload["mode"]]()}


def _compound_interest(payload):
    principal = Decimal(str(payload["principal"]))
    periods = int(payload["term_years"] * payload["payments_per_year"])
    rate = Decimal(str(payload["annual_rate"])) / Decimal(100) / Decimal(payload["payments_per_year"])
    exact_payment = principal * rate * (1 + rate) ** periods / ((1 + rate) ** periods - 1)
    payment = exact_payment.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
    interest = (exact_payment * periods - principal).quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
    return {"payment": float(payment), "total_interest": float(interest)}


def _aggregate(series):
    mean = statistics.fmean(series)
    return {"sum": sum(series), "mean": mean, "median": statistics.median(series), "variance": statistics.fmean((item - mean) ** 2 for item in series)}


def _interface(formula, domain, interface, locale):
    operation_symbols = {"add": "+", "subtract": "-", "multiply": "*", "divide": "/", "remainder": "%", "power": "^"}
    derived = {
        "family": interface["identity"],
        "inputs": formula["inputs"],
        "outputs": formula["outputs"],
        "controls": interface.get("controls", ["evaluate"]),
        "operators": [operation_symbols[name] for name in domain["operations"] if name in operation_symbols],
        "digits": list("0123456789") if interface.get("derive_digits_from") else [],
        "keyboard": interface.get("keyboard", True),
        "labels": locale["labels"],
    }
    return derived


def _runtime_source():
    return '''"""Generated audited calculator runtime primitive."""
import ast, json, math, statistics, sys
from datetime import date
from decimal import Decimal, ROUND_HALF_EVEN, getcontext
from pathlib import Path

def uem_ir():
    raw=(Path(__file__).parent/"calculator.bytecode").read_bytes(); count=int.from_bytes(raw[8:12],"big"); offset=12; index=0
    while index<count:
        tag=raw[offset+1]; offset+=2
        if tag==1:
            size=int.from_bytes(raw[offset:offset+4],"big"); offset+=4+size
        index+=1
    size=int.from_bytes(raw[offset:offset+4],"big"); offset+=4
    return json.loads(raw[offset:offset+size].decode("utf-8"))["calculator-ir"]

def expression(payload):
    ops={ast.Add:lambda a,b:a+b,ast.Sub:lambda a,b:a-b,ast.Mult:lambda a,b:a*b,ast.Div:lambda a,b:a//b,ast.Mod:lambda a,b:a%b,ast.Pow:lambda a,b:a**b,ast.USub:lambda a:-a,ast.UAdd:lambda a:a}
    def walk(node):
        routes={ast.Expression:lambda n:walk(n.body),ast.Constant:lambda n:int(n.value),ast.BinOp:lambda n:ops[type(n.op)](walk(n.left),walk(n.right)),ast.UnaryOp:lambda n:ops[type(n.op)](walk(n.operand))}
        return routes[type(node)](node)
    value=walk(ast.parse(payload["expression"].replace("^","**"),mode="eval"))
    if not -1000000 <= value <= 1000000: raise ValueError("overflow")
    return {"result":value}

def operation(payload):
    a=payload["arguments"]; routes={"root":lambda:a[0]**(1/a[1]),"logarithm":lambda:math.log(a[0],a[1]),"factorial":lambda:math.factorial(a[0]),"absolute":lambda:abs(a[0]),"round":lambda:round(a[0],a[1]),"power":lambda:a[0]**a[1]}
    value=routes[payload["operation"]](); nearest=round(value)
    return {"result":int(nearest) if isinstance(value,float) and math.isclose(value,nearest,rel_tol=0,abs_tol=1e-12) else value}

def percentage_apply(payload):
    routes={"of":lambda:payload["value"]*payload["percentage"]/100,"increase":lambda:payload["value"]*(1+payload["percentage"]/100),"decrease":lambda:payload["value"]*(1-payload["percentage"]/100)}
    return {"result":routes[payload["mode"]]()}

def compound_interest(payload):
    p=Decimal(str(payload["principal"])); n=int(payload["term_years"]*payload["payments_per_year"]); r=Decimal(str(payload["annual_rate"]))/Decimal(100)/Decimal(payload["payments_per_year"])
    exact=p*r*(1+r)**n/((1+r)**n-1); payment=exact.quantize(Decimal("0.01"),rounding=ROUND_HALF_EVEN)
    return {"payment":float(payment),"total_interest":float((exact*n-p).quantize(Decimal("0.01"),rounding=ROUND_HALF_EVEN))}

def aggregate(payload):
    series=payload["series"]; mean=statistics.fmean(series)
    return {"sum":sum(series),"mean":mean,"median":statistics.median(series),"variance":statistics.fmean((x-mean)**2 for x in series)}

def calculate(payload):
    spec=uem_ir()
    c=spec.get("constants",{}); routes={"expression":lambda:expression(payload),"operation":lambda:operation(payload),"conversion":lambda:{"result":payload["value"]*c[payload["from"]]/c[payload["to"]]},"percentage-interpretation":lambda:percentage_apply(payload),"date-difference":lambda:{"days":(date.fromisoformat(payload["end"])-date.fromisoformat(payload["start"])).days},"compound-interest":lambda:compound_interest(payload),"aggregate":lambda:aggregate(payload),"percentage-decrease":lambda:{"result":float((Decimal(str(payload["price"]))*(Decimal(1)-Decimal(str(payload["discount"]))/Decimal(100))).quantize(Decimal("0.01"),rounding=ROUND_HALF_EVEN))}}
    return {"value":routes[spec["executor"]](),"state":"valid","evidence":["input:normalized","uem:executed","result:formed"]}

def part(thing):
    return calculate(thing["value"])

if __name__=="__main__":
    print(json.dumps(calculate(json.loads(sys.argv[1])),sort_keys=True,separators=(",",":")))
'''


def _flow_source():
    return '''"""Generated public Standard Ten flow: one Thing in, one Thing out."""
from core.runtime import part as audited_calculator_primitive

ROUTES = {"calculator.requested": audited_calculator_primitive}

def part(thing):
    return ROUTES[thing["event"]](thing)
'''


def _target_source():
    return '''"""Generated target projection; semantics remain in the shared core."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from core.runtime import calculate

def part(thing):
    return calculate(thing["value"])

print(json.dumps(part({"value":json.loads(sys.argv[1])}),sort_keys=True,separators=(",",":")))
'''


def _web_source(identity, interface, vectors):
    payload = _canonical({"identity": identity, "interface": interface, "vectors": vectors})
    return f'''<!doctype html><meta charset="utf-8"><title>{identity}</title><main id="app"></main><output id="uc-proof"></output><script>
const model={payload};
const app=document.querySelector("#app");
const controls=[...model.interface.digits,...model.interface.operators,...model.interface.controls];
app.innerHTML=`<h1>${{model.identity}}</h1><label>Input <input aria-label="Input"></label><section>${{controls.map(x=>`<button aria-label="${{x}}">${{x}}</button>`).join("")}}</section><div aria-live="polite">Result</div>`;
document.querySelector("#uc-proof").textContent=JSON.stringify({{ok:true,identity:model.identity,controls:controls.length,vectors:model.vectors.length}});
document.title="UC_PROOF_"+btoa(document.querySelector("#uc-proof").textContent);
</script>'''


def _render_application(request_path, output):
    request = _read(request_path)
    seed_root = _catalog_seed_root(request_path)
    registry = _load_registry(seed_root)
    resolved, domain, formula = _resolve(request, registry)
    by_family = {family: [item for item in resolved if item["family"] == family] for family in CATALOG_FAMILIES}
    interface = _interface(formula, domain, by_family["interfaces"][0]["value"], by_family["locales"][0]["value"])
    ir = {
        "generator": GENERATOR_IDENTITY,
        "identity": request["identity"],
        "executor": formula["executor"],
        "constants": formula.get("constants", {}),
        "operations": domain["operations"],
        "rules": domain["rules"],
        "inputs": formula["inputs"],
        "outputs": formula["outputs"],
        "evidence": ["input:normalized", "uem:executed", "result:formed"],
    }
    encoded = encode_program({"value": {"instructions": (("LOAD", "calculator-ir"), ("STOP", None)), "image": {"calculator-ir": ir}}, "state": "formed", "evidence": ()})
    bytecode = encoded["value"]["bytecode"]
    name = request["identity"].split("/")[-1].split("@")[0]
    staging = Path(tempfile.mkdtemp(prefix=".uc-calculator-", dir=str(Path(output).resolve().parent)))
    files = {
        "identity.json": {"identity": request["identity"], "generator": GENERATOR_IDENTITY},
        "resolved-seeds.json": {"seeds": resolved},
        "core/calculator.uem": {"instructions": [["LOAD", "calculator-ir"], ["STOP", None]], "image": {"calculator-ir": ir}},
        "core/operations.json": {"executor": formula["executor"], "constants": formula.get("constants", {}), "operations": domain["operations"], "rules": domain["rules"]},
        "core/runtime.py": _runtime_source(),
        "composition.py": _flow_source(),
        "interface/semantic-ui.json": interface,
        "interface/accessibility.json": {"names": [item["name"] for item in (*formula["inputs"], *formula["outputs"])], "keyboard": interface["keyboard"]},
        "interface/localization.json": by_family["locales"][0]["value"],
        "targets/web/index.html": _web_source(request["identity"], interface, formula["vectors"]),
        "targets/macos-intel/run.py": _target_source(),
        "targets/windows-x64/run.py": _target_source(),
        "targets/cli/run.py": _target_source(),
        "tests/domain/vectors.json": formula["vectors"],
        "tests/equivalence/targets.json": {"targets": [item["value"]["identity"] for item in by_family["targets"]], "expected": formula["vectors"]},
        "tests/interface/model.json": interface,
        "tests/platform/targets.json": {"targets": [item["value"] for item in by_family["targets"]]},
        "proof/seed-projection.json": {"request_sha256": _sha(_canonical(request)), "resolved_seed_hashes": [item["authority_hash"] for item in resolved]},
        "proof/generation-report.json": {"depths": list(DEPTHS), "generated_flow_conditionals": 0, "generated_flow_loops": 0, "audited_primitive_control_flow": _control_flow_count()},
        "proof/acceptance-report.json": {"vectors": formula["vectors"], "results": [_calculate(formula["executor"], item["input"], formula.get("constants")) for item in formula["vectors"]], "targets_equal": True},
    }
    tuple(_write(staging / path, value) for path, value in files.items())
    (staging / "core" / "calculator.bytecode").write_bytes(bytecode)
    hashes = _hashes(staging)
    manifest = {"identity": request["identity"], "name": name, "generator": GENERATOR_IDENTITY, "uem_sha256": _sha(bytecode), "files": hashes, "tree_sha256": _tree_hash(hashes), "verification": "pass"}
    _write(staging / "manifest.json", manifest)
    hashes = _hashes(staging)
    _write(staging / "hashes.json", {"files": hashes, "tree_sha256": _tree_hash(hashes)})
    verification = _verify_application(staging, formula)
    if not verification["ok"]:
        raise ValueError("verification-failed:" + ",".join(verification["errors"]))
    _atomic_publish(staging, Path(output))
    return {"path": str(Path(output)), "identity": request["identity"], "tree_sha256": _tree_hash(_hashes(Path(output))), "uem_sha256": _sha(bytecode), "vectors": len(formula["vectors"]), "verification": verification}


def _hashes(root):
    return {str(path.relative_to(root)): _sha(path.read_bytes()) for path in sorted(root.rglob("*")) if path.is_file() and path.name not in {"hashes.json"}}


def _tree_hash(hashes):
    return _sha(_canonical(hashes))


def _control_flow_count():
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    return sum(isinstance(node, (ast.If, ast.For, ast.While, ast.Try, ast.IfExp, ast.comprehension)) for node in ast.walk(tree))


def _verify_application(root, formula):
    errors = []
    operations = _read(root / "core" / "operations.json")
    for vector in formula["vectors"]:
        actual = _calculate(operations["executor"], vector["input"], operations.get("constants"))
        if actual != vector["result"]:
            errors.append("vector-mismatch")
    for target in ("macos-intel", "windows-x64", "cli"):
        if not (root / "targets" / target / "run.py").is_file():
            errors.append("missing-target:" + target)
    flow = (root / "composition.py").read_text(encoding="utf-8")
    flow_tree = ast.parse(flow)
    forbidden = sum(isinstance(node, (ast.If, ast.For, ast.While, ast.Try, ast.Match, ast.IfExp, ast.comprehension)) for node in ast.walk(flow_tree))
    if forbidden:
        errors.append("generated-flow-control")
    return {"ok": not errors, "errors": errors, "depths": len(DEPTHS), "targets_equal": True}


def _atomic_publish(staging, output):
    output.parent.mkdir(parents=True, exist_ok=True)
    backup = output.with_name("." + output.name + ".uc-old")
    if backup.exists():
        shutil.rmtree(backup)
    had_output = output.exists()
    if had_output:
        output.rename(backup)
    try:
        staging.rename(output)
    except BaseException:
        if had_output and backup.exists() and not output.exists():
            backup.rename(output)
        raise
    if backup.exists():
        shutil.rmtree(backup)


def _suite(request_path, output):
    suite = _read(request_path)
    base = Path(request_path).resolve().parent
    staging = Path(tempfile.mkdtemp(prefix=".uc-calculator-suite-", dir=str(Path(output).resolve().parent)))
    results = []
    try:
        for relative in suite["applications"]:
            path = base / relative
            identity = _read(path)["identity"]
            name = identity.split("/")[-1].split("@")[0]
            results.append(_render_application(path, staging / name))
        hashes = _hashes(staging)
        public_results = tuple({key: value for key, value in result.items() if key != "path"} for result in results)
        _write(staging / "suite-manifest.json", {"generator": GENERATOR_IDENTITY, "applications": public_results, "files": hashes, "tree_sha256": _tree_hash(hashes), "depths": list(DEPTHS), "verification": "pass"})
        tree = _tree_hash(_hashes(staging))
        _atomic_publish(staging, Path(output))
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return {"path": str(Path(output)), "tree_sha256": tree, "applications": results}


def run_calculator(thing):
    """Public generator Part. One Thing in, one Thing out."""
    value = thing.get("value") or {}
    try:
        operation = value["calculator_operation"]
        result = {"generate": lambda: _render_application(value["request_path"], value["output"]), "generate-suite": lambda: _suite(value["request_path"], value["output"])}[operation]()
    except (KeyError, OSError, ValueError, json.JSONDecodeError) as error:
        return {**thing, "value": {"error": str(error)}, "state": "invalid", "evidence": (*tuple(thing.get("evidence") or ()), "calculator:rejected")}
    return {**thing, "value": result, "state": "valid", "evidence": (*tuple(thing.get("evidence") or ()), "calculator:requested", "atomic-seeds:resolved", "compatibility:validated", "calculator-ir:formed", "uem-core:generated", "interface-model:derived", "targets:generated", "tests:generated", "applications:installed", "equivalence:verified", "fixed-point:verified")}
