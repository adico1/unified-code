#!/usr/bin/env python3
"""Generate C core branch ledger from gcov branch arcs.

Reconciliation (must hold):
  missing_arcs_measured == missing_arcs_in_ledger + unmapped_arcs

Baseline conservation vs frozen 3a0bf81 (must hold):
  baseline_open + new_arcs
    == resolved_by_test + removed_by_refactor + current_open

L13 branch eligibility requires:
  missing_arcs_measured == 0
  unmapped_arcs == 0
  unclassified_arcs == 0
  ambiguous_arcs == 0

Arc identity: `{file}:{line}:b{branch_id}` — stable only while source layout
is unchanged. Baseline is frozen in branch_baseline.json (commit 3a0bf81);
normal ledger runs never rewrite that file.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

# Local import (same directory)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from gcov_arcs import (  # noqa: E402
    CORE_STEMS,
    collect_core_arcs,
    summarize_arcs,
)

CROOT = Path(__file__).resolve().parents[1]
OUT_MD = CROOT / "tests" / "BRANCH_LEDGER.md"
OUT_JSON = CROOT / "tests" / "branch_ledger.json"
HISTORY_JSON = CROOT / "tests" / "branch_ledger_history.json"
BASELINE_JSON = CROOT / "tests" / "branch_baseline.json"
BASELINE_COMMIT = "3a0bf81"

KNOWN: dict[str, dict] = {
    "decode.c:329": {
        "class": "impossible",
        "via": "after image_is_canonical, reencode_match cannot fail without alloc fault",
        "test": "encode invariant earlier; remove or #if UEM_STRICT_REENCODE",
    },
}


def classify(entry: dict) -> dict:
    expr = entry.get("expression") or ""
    file = entry["file"]
    line = entry["line"]
    bid = entry["branch_id"]
    key_line = f"{file}:{line}"
    key_br = entry.get("arc_id") or f"{file}:{line}:b{bid}"
    missing = entry.get("missing_arc") or entry.get("missing") or "taken-0%"

    classification = "unresolved"
    required = ""
    action = "generate semantic vector"

    and_count = expr.count("&&")
    or_count = expr.count("||")
    if and_count + or_count >= 1 and (
        "never" in str(missing) or entry.get("pct", 0) == 0
    ):
        if and_count + or_count >= 2 or "never" in str(missing):
            classification = "short-circuit"
            required = (
                f"missing operand combination for short-circuit in: {expr[:90]}"
            )
            action = (
                "supply operand combo or rewrite into named predicates "
                "with independent true/false tests"
            )

    if any(
        t in expr
        for t in (
            "malloc",
            "realloc",
            "calloc",
            "uem_mem_",
            "NOMEM",
            "!nb",
            "!keys",
            "!ne",
            "!nn",
            "!ni",
            "fail_after",
        )
    ):
        classification = "reachable"
        required = "allocator fail_after N covering this call site; assert cleanup + canonical error"
        action = "assert_oom_paths / fail_after sweep"
    elif re.search(
        r"if\s*\(\s*!?\s*(m|out|bytes|json|buf|err|mark|st)\s*(\|\||&&|==\s*NULL|!=\s*NULL|\))",
        expr,
    ) or re.search(r"!\s*(m|out|bytes|json)\s*(\|\||&&|\))", expr):
        classification = "reachable"
        required = "NULL / invalid-arg public API call"
        action = "null-arg and invalid-arg vectors with exact status asserts"
    elif "if (err)" in expr or "err &&" in expr or "errlen" in expr:
        classification = "reachable"
        required = "call with err=NULL and err non-NULL"
        action = "both err-buffer and err-NULL vectors"
    elif any(
        t in expr
        for t in (
            "off >= len",
            "off +",
            "truncated",
            "trailing",
            "bad-magic",
            "bad-version",
            "bad-flags",
            "bad-count",
            "bad-tag",
            "unknown-opcode",
            "invalid-utf8",
            "img_len",
        )
    ):
        classification = "reachable"
        required = "crafted bytecode vector for this reject arm"
        action = "decode reject vector + err string assert"
    elif "0xc0" in expr or "valid_utf8" in expr or "0xc2" in expr:
        classification = "short-circuit"
        required = "UTF-8 sequences hitting each length/continuation failure independently"
        action = "mb_*.uem style vectors for each short-circuit arm"
    elif "strcmp" in expr or "cJSON_Is" in expr or "cJSON_Get" in expr:
        classification = "reachable"
        required = f"state that flips: {expr[:80]}"
        action = "semantic vector for true and false arms"
    elif file == "decimal.c":
        if any(
            t in expr
            for t in (
                "INT64_MAX",
                "INT64_MIN",
                "mul_ok",
                "add_ok",
                "scale < 0",
                "unit <= 0",
                "div <= 0",
                "base <= 0",
                "!a.ok",
                "!b.ok",
            )
        ):
            classification = "reachable"
            required = "decimal edge: overflow, invalid scale, !ok operands, zero unit/div"
            action = "direct decimal unit tests (test_decimal) for each arm"
        elif "rounding" in expr or "ROUND_" in expr or "rem !=" in expr:
            classification = "reachable"
            required = "quantize with each rounding mode and rem==0 / rem!=0"
            action = "quantize matrix vectors"
        elif "*p ==" in expr or "isdigit" in expr or "*p !=" in expr:
            classification = "reachable"
            required = "decimal string with leading +, trailing junk, empty frac"
            action = "direct uem_dec_parse vectors"
        elif "scaled" in expr or "ipart" in expr:
            classification = "reachable"
            required = "negative value with zero integer part (-0.x format)"
            action = "decimal_str of -0.5 etc."
        elif "n < 0" in expr or "cap" in expr:
            classification = "reachable"
            required = "decimal_str with tiny cap buffer"
            action = "call format with cap < 4 and boundary cap"
        else:
            classification = "reachable"
            required = f"decimal state that flips: {expr[:90]}"
            action = "direct decimal unit tests"
    elif file == "machine.c":
        if "operand ?" in expr or "operand &&" in expr or "operand :" in expr:
            classification = "reachable"
            required = "instruction with null operand vs non-null operand for this opcode"
            action = "bytecode vector per opcode with/without operand"
        elif "evidence" in expr or "q_cap" in expr or "q_len" in expr:
            classification = "reachable"
            required = "fill evidence/event queue to force growth and OOM"
            action = "queue-pressure + fail_after vectors"
        elif "max_steps" in expr or "pc-out" in expr or "after-stop" in expr:
            classification = "reachable"
            required = "step after STOP / host max_steps / pc out of range"
            action = "assert_machine_semantics edge vectors"
        elif "outward" in expr or "ticket" in expr:
            classification = "reachable"
            required = "OUTWARD fulfill / missing result / handler error"
            action = "outward inject modes (utf8/json/err/raw)"
        elif "fseek" in expr or "fopen" in expr or "fread" in expr or "ftell" in expr:
            classification = "reachable"
            required = "outward file path that fails seek/read"
            action = "missing-file / unreadable path outward vector"
        elif "?" in expr and ":" in expr:
            classification = "reachable"
            required = f"both arms of ternary: {expr[:80]}"
            action = "semantic vector for true and false arms"
        elif any(
            t in expr
            for t in (
                "m->host",
                "m->acc",
                "operand",
                "events_emitted",
                "stop_reason",
                "program_sha",
                "n_instr",
                "m->instr",
                "snprintf",
            )
        ):
            classification = "reachable"
            required = f"machine field state for: {expr[:80]}"
            action = "load/store/emit/accessors with null machine and empty fields"
        elif re.search(r"if\s*\(\s*!?[a-zA-Z_][a-zA-Z0-9_\->]*\s*\)", expr):
            classification = "reachable"
            required = f"both truthy and falsey for guard: {expr[:80]}"
            action = "semantic vector for true and false arms"
        else:
            classification = "reachable"
            required = f"machine state that flips: {expr[:90]}"
            action = "assert_machine_semantics vector"
    elif file == "expr.c":
        classification = "reachable"
        required = f"expression node shape that flips: {expr[:80]}"
        action = "assert_expr_error_arms / template fuzz for missing arm"
    elif file == "primitives.c":
        if "password" in expr or "token" in expr or "secret" in expr or "api_key" in expr:
            classification = "short-circuit"
            required = "redact message containing each keyword independently"
            action = "one vector per keyword; rewrite OR-chain to table if needed"
        elif "unknown-primitive" in expr or "REGISTRY" in expr:
            classification = "reachable"
            required = "unknown primitive name"
            action = "assert_unkprim + direct uem_prim_apply"
        else:
            classification = "reachable"
            required = f"primitive config/host that flips: {expr[:80]}"
            action = "assert_primitives_eval_bindings + config variants"
    elif file == "decode.c":
        if "append_str" in expr:
            classification = "reachable"
            required = "fail_after during json_escape_append / canon_value growth"
            action = "assert_oom_paths sweeping fail_after across image with escapes"
        elif "ArrayForEach" in expr or "for (" in expr or "while (" in expr:
            classification = "reachable"
            required = "empty vs non-empty collection for this loop"
            action = "semantic vector with empty and multi-element inputs"
        elif "rd_u16" in expr or "rd_u32" in expr:
            classification = "short-circuit"
            required = "rd fail vs value mismatch independently"
            action = "truncated header vs bad-version/flags vectors"
        elif "m->instr" in expr or "free_partial" in expr:
            classification = "reachable"
            required = "partial decode free with and without instr array"
            action = "OOM after machine alloc before instr alloc"
        elif "cJSON_Delete" in expr:
            classification = "reachable"
            required = "parse success then type reject vs parse fail"
            action = "bad-image-json vectors (array root vs null root)"
        elif "ncap" in expr:
            classification = "reachable"
            required = "append larger than double growth (force while multi-iter)"
            action = "huge string under growth; or fail_after mid-growth"
        elif "op >=" in expr or "op <=" in expr or "0x01" in expr or "0x10" in expr:
            classification = "reachable"
            required = "opcode at boundary 0x01/0x10 and out-of-range"
            action = "unknown_opcode + valid range vectors"
        else:
            classification = "reachable"
            required = f"decode state that flips: {expr[:90]}"
            action = "decode reject / canon vector"
    elif file == "alloc.c":
        classification = "reachable"
        required = "assert_alloc_api / fail_after edge"
        action = "assert_alloc_api"
    elif not expr or expr in {"}", "{", "break;", "continue;", "return;", "else"}:
        classification = "short-circuit"
        required = "paired arm of adjacent condition"
        action = "ignore if parent condition covered; else rewrite"
    elif classification == "unresolved" and expr:
        classification = "reachable"
        required = f"state that flips: {expr[:100]}"
        action = "semantic vector for true and false arms"
    elif classification == "unresolved":
        classification = "reachable"
        required = "inspect source and supply true/false vector"
        action = "semantic vector or refactor"

    for k in (key_br, key_line):
        if k in KNOWN:
            meta = KNOWN[k]
            classification = meta.get("class", classification)
            action = meta.get("test", action)
            required = meta.get("via", required)
            break

    entry["class"] = classification
    entry["required_input_state"] = required
    entry["test_or_refactor"] = action
    entry["key"] = key_br
    entry["arc_id"] = key_br
    entry["source_line"] = key_line
    entry["status"] = "open"
    entry["missing"] = missing
    entry["missing_arc"] = missing
    return entry


def _load_baseline() -> dict:
    """Load frozen baseline. Never invent a new baseline here."""
    if not BASELINE_JSON.is_file():
        raise SystemExit(
            f"missing {BASELINE_JSON}: freeze baseline from {BASELINE_COMMIT} first"
        )
    data = json.loads(BASELINE_JSON.read_text(encoding="utf-8"))
    if data.get("baseline_commit") != BASELINE_COMMIT:
        raise SystemExit(
            f"baseline_commit is {data.get('baseline_commit')!r}, "
            f"expected {BASELINE_COMMIT!r} — refuse to proceed"
        )
    ids = set(data.get("open_arc_ids") or [])
    if int(data.get("baseline_open") or 0) != len(ids):
        raise SystemExit(
            f"baseline_open {data.get('baseline_open')} != len(open_arc_ids) {len(ids)}"
        )
    return data


def _expr_fingerprint(expr: str) -> str:
    """Normalize expression for soft remapping hints (informational only)."""
    e = re.sub(r"\s+", " ", (expr or "").strip())
    e = re.sub(r"\b0x[0-9a-fA-F]+\b", "HEX", e)
    e = re.sub(r"\b\d+\b", "N", e)
    return e[:120]


def _compute_baseline_progress(
    baseline: dict,
    arcs: list[dict],
    now_open: set[str],
) -> dict:
    """Progress against frozen baseline_open; never rewrites baseline file."""
    baseline_ids = set(baseline.get("open_arc_ids") or [])
    baseline_open = len(baseline_ids)
    baseline_expr = {
        e.get("arc_id"): _expr_fingerprint(e.get("expression") or "")
        for e in (baseline.get("entries") or [])
        if e.get("arc_id")
    }

    all_ids_present = {a["arc_id"] for a in arcs}
    now_taken = {a["arc_id"] for a in arcs if a["taken"]}
    now_open = set(now_open)

    # Baseline arcs that still exist and are taken → resolved by test coverage.
    resolved_by_test_ids = sorted(baseline_ids & now_taken)
    # Baseline arcs that no longer appear in gcov at all → identity lost (refactor).
    removed_by_refactor_ids = sorted(baseline_ids - all_ids_present)
    # Still open from baseline (same identity still missing).
    still_baseline_open = sorted(baseline_ids & now_open)
    # Current open not in baseline.
    new_arc_ids = sorted(now_open - baseline_ids)

    # Informational remapping: removed_by_refactor → new_arcs by expression fingerprint.
    new_by_fp: dict[str, list[str]] = defaultdict(list)
    open_expr = {e["arc_id"]: _expr_fingerprint(e.get("expression") or "") for e in
                 # will fill from arcs missing
                 []}
    for a in arcs:
        if not a["taken"]:
            open_expr[a["arc_id"]] = _expr_fingerprint(a.get("expression") or "")
    for aid in new_arc_ids:
        fp = open_expr.get(aid, "")
        if fp:
            new_by_fp[fp].append(aid)

    remapped: list[dict] = []
    ambiguous: list[dict] = []
    used_new: set[str] = set()
    for rid in removed_by_refactor_ids:
        fp = baseline_expr.get(rid, "")
        if not fp:
            continue
        candidates = [n for n in new_by_fp.get(fp, []) if n not in used_new]
        if len(candidates) == 1:
            remapped.append({"from": rid, "to": candidates[0], "fingerprint": fp})
            used_new.add(candidates[0])
        elif len(candidates) > 1:
            ambiguous.append({"from": rid, "candidates": candidates, "fingerprint": fp})

    progress = {
        "baseline_commit": baseline.get("baseline_commit"),
        "baseline_open": baseline_open,
        "resolved_by_test": len(resolved_by_test_ids),
        "resolved_by_test_ids": resolved_by_test_ids,
        "removed_by_refactor": len(removed_by_refactor_ids),
        "removed_by_refactor_ids": removed_by_refactor_ids,
        "new_arcs": len(new_arc_ids),
        "new_arc_ids": new_arc_ids,
        "remapped_arcs": len(remapped),
        "remapped": remapped,
        "ambiguous_arcs": len(ambiguous),
        "ambiguous": ambiguous,
        "current_open": len(now_open),
        "still_baseline_open": len(still_baseline_open),
        "still_baseline_open_ids": still_baseline_open,
        "conservation": {
            "equation": (
                "baseline_open + new_arcs "
                "== resolved_by_test + removed_by_refactor + current_open"
            ),
            "left": baseline_open + len(new_arc_ids),
            "right": (
                len(resolved_by_test_ids)
                + len(removed_by_refactor_ids)
                + len(now_open)
            ),
        },
    }
    progress["conservation"]["holds"] = (
        progress["conservation"]["left"] == progress["conservation"]["right"]
    )
    return progress


def main() -> int:
    arcs = collect_core_arcs(CORE_STEMS)
    summary = summarize_arcs(arcs)
    measured_missing = summary["missing"]
    branches_hit = summary["branches_hit"]
    branches_total = summary["branches_total"]
    missing_arcs_measured = summary["missing_arcs_measured"]

    # Every measured missing arc becomes a ledger entry (no silent drops).
    entries: list[dict] = []
    for a in measured_missing:
        e = {
            "file": a["file"],
            "line": a["line"],
            "branch_id": a["branch_id"],
            "arc_id": a["arc_id"],
            "key": a["arc_id"],
            "expression": a["expression"],
            "missing": a["missing_arc"],
            "missing_arc": a["missing_arc"],
            "pct": a["pct"],
        }
        entries.append(classify(e))

    ledger_ids = {e["arc_id"] for e in entries}
    measured_ids = {a["arc_id"] for a in measured_missing}
    unmapped_ids = sorted(measured_ids - ledger_ids)
    # Extra safety: if classify somehow dropped, re-add as unclassified
    for aid in unmapped_ids:
        a = next(x for x in measured_missing if x["arc_id"] == aid)
        e = {
            "file": a["file"],
            "line": a["line"],
            "branch_id": a["branch_id"],
            "arc_id": a["arc_id"],
            "key": a["arc_id"],
            "expression": a["expression"],
            "missing": a["missing_arc"],
            "missing_arc": a["missing_arc"],
            "pct": a["pct"],
            "class": "unresolved",
            "required_input_state": "unmapped during classify — fix generator",
            "test_or_refactor": "generator bug",
            "status": "open",
            "source_line": f"{a['file']}:{a['line']}",
        }
        entries.append(e)
        ledger_ids.add(aid)
    unmapped_ids = sorted(measured_ids - ledger_ids)
    missing_arcs_in_ledger = len(entries)
    unmapped_arcs = len(unmapped_ids)

    now_open = {e["arc_id"] for e in entries}
    baseline = _load_baseline()
    progress = _compute_baseline_progress(baseline, arcs, now_open)
    cons = progress["conservation"]

    unclassified = [e for e in entries if e.get("class") in (None, "", "unresolved")]
    by_class = Counter(e["class"] for e in entries)
    by_file = Counter(e["file"] for e in entries)

    # Identity invariant (measurement vs ledger)
    assert missing_arcs_measured == missing_arcs_in_ledger + unmapped_arcs, (
        missing_arcs_measured,
        missing_arcs_in_ledger,
        unmapped_arcs,
    )
    # Baseline conservation
    assert cons["holds"], cons
    assert progress["ambiguous_arcs"] == 0, progress["ambiguous"]

    per_file = [
        {
            "file": f,
            "branches_hit": summary["by_file"][f]["branches_hit"],
            "branches_total": summary["by_file"][f]["branches_total"],
            "missing_arcs": summary["by_file"][f]["missing_arcs"],
        }
        for f in sorted(summary["by_file"])
    ]

    eligible = (
        missing_arcs_measured == 0
        and unmapped_arcs == 0
        and len(unclassified) == 0
        and progress["ambiguous_arcs"] == 0
        and progress["still_baseline_open"] == 0
        and progress["new_arcs"] == 0
    )

    ledger = {
        "identity_scheme": "{file}:{line}:b{branch_id}",
        "baseline_commit": BASELINE_COMMIT,
        "branches_hit": branches_hit,
        "branches_total": branches_total,
        "missing_arcs_measured": missing_arcs_measured,
        "missing_arcs_in_ledger": missing_arcs_in_ledger,
        "unmapped_arcs": unmapped_arcs,
        "unmapped_arc_ids": unmapped_ids,
        "unclassified_arcs": len(unclassified),
        "open_arc_ids": sorted(now_open),
        "baseline_open": progress["baseline_open"],
        "resolved_by_test": progress["resolved_by_test"],
        "resolved_by_test_ids": progress["resolved_by_test_ids"],
        "removed_by_refactor": progress["removed_by_refactor"],
        "removed_by_refactor_ids": progress["removed_by_refactor_ids"],
        "new_arcs": progress["new_arcs"],
        "new_arc_ids": progress["new_arc_ids"],
        "remapped_arcs": progress["remapped_arcs"],
        "remapped": progress["remapped"],
        "ambiguous_arcs": progress["ambiguous_arcs"],
        "ambiguous": progress["ambiguous"],
        "current_open": progress["current_open"],
        "still_baseline_open": progress["still_baseline_open"],
        "still_baseline_open_ids": progress["still_baseline_open_ids"],
        "missing_arcs": missing_arcs_measured,
        "total_missing_arcs": missing_arcs_measured,
        "resolved_arcs": progress["resolved_by_test"],
        "resolved_arc_ids": progress["resolved_by_test_ids"],
        "unresolved_count": len(unclassified),
        "by_class": dict(by_class),
        "by_file_missing": dict(by_file),
        "per_file": per_file,
        "entries": entries,
        "reconciliation": {
            "equation": "missing_arcs_measured == missing_arcs_in_ledger + unmapped_arcs",
            "holds": missing_arcs_measured == missing_arcs_in_ledger + unmapped_arcs,
        },
        "baseline_conservation": cons,
        "l13_branch_eligible": eligible,
        "pass_ready": eligible,
        "l13_branch_gate": (
            "FAIL until missing_arcs_measured==0, unmapped_arcs==0, "
            "unclassified_arcs==0, ambiguous_arcs==0, and baseline fully "
            f"accounted (still_baseline_open==0, new_arcs==0); baseline={BASELINE_COMMIT}"
        ),
    }

    OUT_JSON.write_text(
        json.dumps(ledger, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    # History snapshot — never rewrites branch_baseline.json
    HISTORY_JSON.write_text(
        json.dumps(
            {
                "baseline_commit": BASELINE_COMMIT,
                "baseline_open": progress["baseline_open"],
                "resolved_by_test": progress["resolved_by_test"],
                "removed_by_refactor": progress["removed_by_refactor"],
                "new_arcs": progress["new_arcs"],
                "remapped_arcs": progress["remapped_arcs"],
                "ambiguous_arcs": progress["ambiguous_arcs"],
                "current_open": progress["current_open"],
                "still_baseline_open": progress["still_baseline_open"],
                "conservation_holds": cons["holds"],
                "open_arc_ids": sorted(now_open),
                "resolved_by_test_ids": progress["resolved_by_test_ids"],
                "removed_by_refactor_ids": progress["removed_by_refactor_ids"],
                "new_arc_ids": progress["new_arc_ids"],
                "branches_hit": branches_hit,
                "branches_total": branches_total,
                "missing_arcs_measured": missing_arcs_measured,
                "note": (
                    f"Baseline frozen at {BASELINE_COMMIT} in branch_baseline.json. "
                    "Do not regenerate baseline until all original open arcs are accounted for."
                ),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    lines = [
        "# C Core Branch Ledger",
        "",
        "Generated by `c/scripts/branch_ledger.py` from **enumerated gcov branch arcs**",
        "(same metric as L13 C branches — not rounded summary percentages).",
        "",
        f"**Baseline commit (frozen):** `{BASELINE_COMMIT}` — "
        "do not rewrite until all original open arcs are accounted for.",
        "",
        "L13 branch eligibility requires:",
        "",
        "```text",
        "missing_arcs_measured == 0",
        "unmapped_arcs == 0",
        "unclassified_arcs == 0",
        "ambiguous_arcs == 0",
        "still_baseline_open == 0 && new_arcs == 0",
        "```",
        "",
        "## Measurement reconciliation",
        "",
        f"- **branches_hit:** {branches_hit}",
        f"- **branches_total:** {branches_total}",
        f"- **missing_arcs_measured:** {missing_arcs_measured}",
        f"- **missing_arcs_in_ledger:** {missing_arcs_in_ledger}",
        f"- **unmapped_arcs:** {unmapped_arcs}",
        f"- **unclassified_arcs:** {len(unclassified)}",
        f"- Equation: `{missing_arcs_measured} == {missing_arcs_in_ledger} + {unmapped_arcs}` → "
        f"**{missing_arcs_measured == missing_arcs_in_ledger + unmapped_arcs}**",
        "",
        "## Baseline conservation (vs frozen open set)",
        "",
        f"- **baseline_open:** {progress['baseline_open']}",
        f"- **resolved_by_test:** {progress['resolved_by_test']}",
        f"- **removed_by_refactor:** {progress['removed_by_refactor']}",
        f"- **new_arcs:** {progress['new_arcs']}",
        f"- **remapped_arcs:** {progress['remapped_arcs']} (informational)",
        f"- **ambiguous_arcs:** {progress['ambiguous_arcs']} (must be 0)",
        f"- **current_open:** {progress['current_open']}",
        f"- **still_baseline_open:** {progress['still_baseline_open']}",
        f"- Conservation: `{cons['left']} == {cons['right']}` "
        f"(`baseline_open + new_arcs == resolved_by_test + removed_by_refactor + current_open`) → "
        f"**{cons['holds']}**",
        f"- L13 branch eligible: **{eligible}**",
        f"- Identity: `{ledger['identity_scheme']}` (stable only while source layout unchanged)",
        f"- By class: `{json.dumps(dict(by_class), sort_keys=True)}`",
        f"- By file: `{json.dumps(dict(by_file), sort_keys=True)}`",
        "",
        "## Per-file hit/total",
        "",
        "| File | Hit | Total | Missing |",
        "| --- | ---: | ---: | ---: |",
    ]
    for row in per_file:
        lines.append(
            f"| `{row['file']}` | {row['branches_hit']} | {row['branches_total']} | "
            f"{row['missing_arcs']} |"
        )

    if progress["resolved_by_test_ids"]:
        lines += ["", "## Resolved by test (baseline open → taken)", ""]
        for aid in progress["resolved_by_test_ids"][:100]:
            lines.append(f"- `{aid}`")
        if progress["resolved_by_test"] > 100:
            lines.append(f"- … and {progress['resolved_by_test'] - 100} more")

    if progress["removed_by_refactor_ids"]:
        lines += ["", "## Removed by refactor (baseline identity gone from gcov)", ""]
        for aid in progress["removed_by_refactor_ids"][:100]:
            lines.append(f"- `{aid}`")

    if progress["new_arc_ids"]:
        lines += ["", "## New arcs (not in baseline — investigate remaps)", ""]
        for aid in progress["new_arc_ids"][:100]:
            lines.append(f"- `{aid}`")

    if progress["remapped"]:
        lines += ["", "## Remapped (informational expression match)", ""]
        for r in progress["remapped"][:50]:
            lines.append(f"- `{r['from']}` → `{r['to']}`")

    if progress["ambiguous"]:
        lines += ["", "## Ambiguous remaps (must be zero)", ""]
        for a in progress["ambiguous"]:
            lines.append(f"- `{a['from']}` → {a['candidates']}")

    if unmapped_ids:
        lines += ["", "## Unmapped (generator defect — must be zero)", ""]
        for aid in unmapped_ids:
            lines.append(f"- `{aid}`")

    lines += [
        "",
        "## Open ledger (current)",
        "",
        "| arc_id | missing | expression | class | required input/state | test or refactor |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for e in sorted(entries, key=lambda x: (x["file"], x["line"], x["branch_id"])):
        expr = e["expression"].replace("|", "\\|")[:70]
        req = (e.get("required_input_state") or "").replace("|", "\\|")[:50]
        act = (e.get("test_or_refactor") or "").replace("|", "\\|")[:45]
        lines.append(
            f"| `{e['arc_id']}` | {e['missing_arc']} | `{expr}` | **{e['class']}** | "
            f"{req} | {act} |"
        )

    lines.append("")
    lines.append("## Unclassified (must be zero)")
    lines.append("")
    if not unclassified:
        lines.append("(none)")
    else:
        for e in unclassified[:200]:
            lines.append(
                f"- `{e['arc_id']}` `{e['expression'][:90]}` — assign reachable | redundant | impossible | short-circuit"
            )

    lines += [
        "",
        "## Branch-closure order",
        "",
        "1. Reachable rejection paths with exact error assertions.",
        "2. Short-circuit operand combinations.",
        "3. State-machine second arms and boundary outcomes.",
        "4. Decimal sign/rounding combinations.",
        "5. Redundant or invariant-impossible arcs through production simplification.",
        "",
        "## Notes",
        "",
        f"- Baseline frozen at `{BASELINE_COMMIT}` in `branch_baseline.json` — **never** regenerated as a fresh baseline after ordinary ledger runs.",
        "- `{file}:{line}:b{{branch_id}}` shifts if lines are added/deleted or the compiler renumbers branches; prefer tests over refactors until baseline is cleared.",
        "- `unclassified_arcs == 0` means every open arc has a class; it does **not** mean arcs are closed.",
        "- Progress is `open → resolved_by_test` (or `removed_by_refactor`) against the frozen baseline.",
        "",
    ]
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    print(
        json.dumps(
            {
                "baseline_commit": BASELINE_COMMIT,
                "branches_hit": branches_hit,
                "branches_total": branches_total,
                "missing_arcs_measured": missing_arcs_measured,
                "missing_arcs_in_ledger": missing_arcs_in_ledger,
                "unmapped_arcs": unmapped_arcs,
                "unclassified_arcs": len(unclassified),
                "baseline_open": progress["baseline_open"],
                "resolved_by_test": progress["resolved_by_test"],
                "removed_by_refactor": progress["removed_by_refactor"],
                "new_arcs": progress["new_arcs"],
                "remapped_arcs": progress["remapped_arcs"],
                "ambiguous_arcs": progress["ambiguous_arcs"],
                "current_open": progress["current_open"],
                "still_baseline_open": progress["still_baseline_open"],
                "conservation_holds": cons["holds"],
                "measurement_holds": missing_arcs_measured
                == missing_arcs_in_ledger + unmapped_arcs,
                "l13_branch_eligible": eligible,
                "md": str(OUT_MD),
                "json": str(OUT_JSON),
                "baseline": str(BASELINE_JSON),
            },
            indent=2,
        )
    )
    return 0 if eligible else 1


if __name__ == "__main__":
    raise SystemExit(main())
