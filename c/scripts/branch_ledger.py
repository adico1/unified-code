#!/usr/bin/env python3
"""Generate C core branch ledger from gcov -b output.

For each untaken branch arc, classify:

  reachable   — generate a semantic vector with exact assertions
  redundant   — simplify or delete the condition
  impossible  — encode the invariant earlier, then remove the defensive branch
  short-circuit — supply the missing operand combination or rewrite into a
                  named predicate whose outcomes are independently testable

L13 requires zero unresolved entries and 100% taken arcs before pass.
This tool produces the working ledger, not a greenwash.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

CROOT = Path(__file__).resolve().parents[1]
CORE = CROOT / "core"
BUILD = CROOT / "build"
OUT_MD = CROOT / "tests" / "BRANCH_LEDGER.md"
OUT_JSON = CROOT / "tests" / "branch_ledger.json"

# Hand-curated overrides: "file:line" or "file:line:bN" -> meta
KNOWN: dict[str, dict] = {
    # decode: reencode non-canonical under alloc (gated / defensive)
    "decode.c:329": {
        "class": "impossible",
        "via": "after image_is_canonical, reencode_match cannot fail without alloc fault",
        "test": "encode invariant earlier; remove or #if UEM_STRICT_REENCODE",
    },
    # alloc fully closed after assert_alloc_api + assert_oom_paths
}


def ensure_gcov() -> None:
    for cfile in sorted(CORE.glob("*.c")):
        stem = cfile.stem
        gcno = BUILD / f"{stem}.gcno"
        if not gcno.is_file():
            continue
        subprocess.run(
            ["gcov", "-b", "-o", str(gcno), str(cfile)],
            cwd=str(CROOT),
            capture_output=True,
            text=True,
        )


def parse_gcov_branches(gcov_path: Path) -> list[dict]:
    if not gcov_path.is_file():
        return []
    text = gcov_path.read_text(encoding="utf-8", errors="replace")
    entries: list[dict] = []
    current_src_line = 0
    current_expr = ""
    for ln in text.splitlines():
        m = re.match(r"^\s*([#\d\-]+):\s*(\d+):(.*)$", ln)
        if m:
            current_src_line = int(m.group(2))
            current_expr = m.group(3).strip()
            continue
        bm = re.match(
            r"^\s*branch\s+(\d+)\s+(taken\s+(\d+)%|never executed)(.*)$",
            ln,
            re.I,
        )
        if not bm or current_src_line <= 0:
            continue
        bid = int(bm.group(1))
        never = "never" in bm.group(2).lower()
        pct = 0 if never else int(bm.group(3) or 0)
        if pct > 0 and not never:
            continue
        # Infer missing arm: for a binary if, even/odd bids often true/false;
        # gcov labels are unreliable across compilers — record as "untaken arc".
        missing_arm = "never-executed" if never else "taken-0%"
        entries.append(
            {
                "file": gcov_path.name.replace(".gcov", ""),
                "line": current_src_line,
                "branch_id": bid,
                "expression": current_expr[:160],
                "missing": missing_arm,
                "missing_arc": missing_arm,
                "pct": pct,
            }
        )
    return entries


def classify(entry: dict) -> dict:
    expr = entry.get("expression") or ""
    file = entry["file"]
    line = entry["line"]
    bid = entry["branch_id"]
    key_line = f"{file}:{line}"
    key_br = f"{file}:{line}:b{bid}"

    classification = "unresolved"
    required = ""
    action = "generate semantic vector"

    # --- short-circuit / multi-operand (missing intermediate arcs) ---
    and_count = expr.count("&&")
    or_count = expr.count("||")
    if and_count + or_count >= 1 and (
        "never" in entry["missing"] or entry["pct"] == 0
    ):
        # Multi-clause: often need independent operand combos
        if and_count + or_count >= 2 or "never" in entry["missing"]:
            classification = "short-circuit"
            required = (
                f"missing operand combination for short-circuit in: {expr[:90]}"
            )
            action = (
                "supply operand combo or rewrite into named predicates "
                "with independent true/false tests"
            )

    # --- allocation / OOM ---
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

    # --- null / args guards ---
    elif re.search(
        r"if\s*\(\s*!?\s*(m|out|bytes|json|a|buf|s|err|v|mark|st)\s*(\|\||&&|==|!=|\))",
        expr,
    ) or re.search(r"!\s*(m|out|bytes|json)\s*(\|\||&&|\))", expr):
        classification = "reachable"
        required = "NULL / invalid-arg public API call"
        action = "null-arg and invalid-arg vectors with exact status asserts"

    # --- error snprintf optional buffer ---
    elif "if (err)" in expr or "err &&" in expr or "errlen" in expr:
        classification = "reachable"
        required = "call with err=NULL and err non-NULL"
        action = "both err-buffer and err-NULL vectors"

    # --- decode length / truncation ---
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

    # --- UTF-8 multi-byte short-circuit ---
    elif "0xc0" in expr or "valid_utf8" in expr or "0xc2" in expr:
        classification = "short-circuit"
        required = "UTF-8 sequences hitting each length/continuation failure independently"
        action = "mb_*.uem style vectors for each short-circuit arm"

    # --- cJSON / strcmp semantic ---
    elif "strcmp" in expr or "cJSON_Is" in expr or "cJSON_Get" in expr:
        classification = "reachable"
        required = f"host/image/config state that flips: {expr[:80]}"
        action = "semantic vector for true and false arms"

    # --- decimal overflow / scale / parse ---
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

    # --- machine opcode / operand defaults ---
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

    # --- expr nodes ---
    elif file == "expr.c":
        classification = "reachable"
        required = f"expression node shape that flips: {expr[:80]}"
        action = "assert_expr_error_arms / template fuzz for missing arm"

    # --- primitives ---
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

    # --- decode residual ---
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

    # --- empty / brace (compiler noise) ---
    elif not expr or expr in {"}", "{", "break;", "continue;", "return;", "else"}:
        classification = "short-circuit"
        required = "paired arm of adjacent condition"
        action = "ignore if parent condition covered; else rewrite"

    # --- residual ---
    elif classification == "unresolved" and expr:
        classification = "reachable"
        required = f"state that flips: {expr[:100]}"
        action = "semantic vector for true and false arms"
    elif classification == "unresolved":
        classification = "reachable"
        required = "inspect source and supply true/false vector"
        action = "semantic vector or refactor"

    # KNOWN overrides (most specific first)
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
    entry["source_line"] = key_line
    return entry


def main() -> int:
    ensure_gcov()
    all_entries: list[dict] = []
    for gcov in sorted(CROOT.glob("*.gcov")):
        if not any(
            gcov.name.startswith(s)
            for s in ("decode", "expr", "machine", "primitives", "decimal", "alloc")
        ):
            continue
        for e in parse_gcov_branches(gcov):
            all_entries.append(classify(e))

    unresolved = [e for e in all_entries if e["class"] == "unresolved"]
    by_class: dict[str, int] = Counter(e["class"] for e in all_entries)
    by_file: dict[str, int] = Counter(e["file"] for e in all_entries)

    # Per-file branch totals from gcov summaries if present
    per_file_totals: list[dict] = []
    for stem in ("alloc", "decimal", "decode", "expr", "machine", "primitives"):
        gcov = CROOT / f"{stem}.c.gcov"
        hit = total = None
        if gcov.is_file():
            # Count all branch lines
            text = gcov.read_text(encoding="utf-8", errors="replace")
            br_all = len(re.findall(r"^\s*branch\s+\d+\s+", text, re.M))
            br_miss = sum(1 for e in all_entries if e["file"] == f"{stem}.c")
            if br_all:
                total = br_all
                hit = br_all - br_miss
        per_file_totals.append(
            {
                "file": f"{stem}.c",
                "branches_hit": hit,
                "branches_total": total,
                "missing_arcs": by_file.get(f"{stem}.c", 0),
            }
        )

    # Terminology:
    #   missing_arcs       — still not taken by tests (open work)
    #   unclassified_arcs  — missing arcs without a class (must be 0)
    #   resolved_arcs      — arcs that were missing and are now taken (0 here;
    #                        this tool only lists current missing set)
    ledger = {
        "missing_arcs": len(all_entries),
        "unclassified_arcs": len(unresolved),
        "resolved_arcs": 0,
        "total_missing_arcs": len(all_entries),  # alias
        "unresolved_count": len(unresolved),  # alias of unclassified_arcs
        "by_class": dict(by_class),
        "by_file_missing": dict(by_file),
        "per_file_branch_approx": per_file_totals,
        "entries": all_entries,
        "pass_ready": len(unresolved) == 0 and len(all_entries) == 0,
        "l13_branch_gate": (
            "FAIL until missing_arcs==0 and unclassified_arcs==0; "
            "classified≠resolved — publish per-file hit/total, not aggregate only"
        ),
    }
    OUT_JSON.write_text(
        json.dumps(ledger, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    lines = [
        "# C Core Branch Ledger",
        "",
        "Generated by `c/scripts/branch_ledger.py` from gcov branch arcs.",
        "",
        "L13 requires **zero unresolved** entries and **100% taken arcs** before pass.",
        "Do not attack arcs blindly — use class to choose vector vs refactor.",
        "",
        f"- **missing_arcs:** {len(all_entries)} (still open — not taken)",
        f"- **unclassified_arcs:** {len(unresolved)} (must be 0; classification ≠ resolution)",
        f"- **resolved_arcs:** 0 (this report only lists currently missing arcs)",
        f"- By class: `{json.dumps(dict(by_class), sort_keys=True)}`",
        f"- By file: `{json.dumps(dict(by_file), sort_keys=True)}`",
        "",
        "## Per-file missing arcs",
        "",
        "| File | Missing arcs |",
        "| --- | ---: |",
    ]
    for f, n in sorted(by_file.items()):
        lines.append(f"| `{f}` | {n} |")

    lines += [
        "",
        "## Ledger",
        "",
        "Format: source:line · expression · missing arc · required input/state · class · test or refactor",
        "",
        "| source:line | b | missing arc | expression | class | required input/state | test or refactor |",
        "| --- | ---: | --- | --- | --- | --- | --- |",
    ]
    for e in sorted(all_entries, key=lambda x: (x["file"], x["line"], x["branch_id"])):
        expr = e["expression"].replace("|", "\\|")[:70]
        req = (e.get("required_input_state") or "").replace("|", "\\|")[:50]
        act = (e.get("test_or_refactor") or "").replace("|", "\\|")[:45]
        lines.append(
            f"| `{e['file']}:{e['line']}` | {e['branch_id']} | {e['missing_arc']} | "
            f"`{expr}` | **{e['class']}** | {req} | {act} |"
        )

    lines.append("")
    lines.append("## Unresolved (must be zero for L13 branch pass)")
    lines.append("")
    if not unresolved:
        lines.append("(none — all missing arcs classified)")
    else:
        for e in unresolved[:250]:
            lines.append(
                f"- `{e['key']}` `{e['expression'][:90]}` — classify: reachable | redundant | impossible | short-circuit"
            )
        if len(unresolved) > 250:
            lines.append(f"- … and {len(unresolved) - 250} more (see JSON)")

    lines += [
        "",
        "## Close order (recommended)",
        "",
        "1. **reachable + OOM** — finish fail_after sweeps (partial state + ASan).",
        "2. **reachable + decode rejects** — one vector per err string.",
        "3. **short-circuit** — operand combos or named predicates.",
        "4. **redundant / impossible** — delete or encode invariant; re-measure so totals do not collapse materially.",
        "5. Re-run ASan/UBSan with allocation failures, differential Python/C, mutation on new error paths.",
        "6. Publish per-file branch hit/total; require unresolved==0 and missing_arcs==0.",
        "",
    ]
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(
        json.dumps(
            {
                "missing_arcs": len(all_entries),
                "unclassified_arcs": len(unresolved),
                "resolved_arcs": 0,
                "by_class": dict(by_class),
                "by_file": dict(by_file),
                "md": str(OUT_MD),
                "json": str(OUT_JSON),
            },
            indent=2,
        )
    )
    # Exit 0 only when fully closed; non-zero while work remains (CI signal)
    return 0 if len(all_entries) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
