#!/usr/bin/env python3
"""Generate C core branch ledger from gcov branch arcs.

Reconciliation (must hold):
  missing_arcs_measured == missing_arcs_in_ledger + unmapped_arcs

L13 branch eligibility requires:
  missing_arcs_measured == 0
  unmapped_arcs == 0
  unclassified_arcs == 0

Arc identity is stable across runs: `{file}:{line}:b{branch_id}`.
Previous open arcs that are now taken are reported as resolved (not zeroed).
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
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


def _load_previous_open() -> set[str]:
    """Stable prior open set: prefer history file, else previous ledger entries."""
    open_ids: set[str] = set()
    if HISTORY_JSON.is_file():
        try:
            hist = json.loads(HISTORY_JSON.read_text(encoding="utf-8"))
            open_ids = set(hist.get("open_arc_ids") or [])
        except (json.JSONDecodeError, OSError):
            open_ids = set()
    if not open_ids and OUT_JSON.is_file():
        try:
            prev = json.loads(OUT_JSON.read_text(encoding="utf-8"))
            for e in prev.get("entries") or []:
                aid = e.get("arc_id") or e.get("key")
                if aid:
                    open_ids.add(aid)
            # also accept explicit open list
            open_ids |= set(prev.get("open_arc_ids") or [])
        except (json.JSONDecodeError, OSError):
            pass
    return open_ids


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

    # Stable progress: previous open ∩ now taken
    prev_open = _load_previous_open()
    now_taken = {a["arc_id"] for a in arcs if a["taken"]}
    now_open = {e["arc_id"] for e in entries}
    resolved_ids = sorted(prev_open & now_taken)
    still_open_from_prev = sorted(prev_open & now_open)
    newly_open = sorted(now_open - prev_open) if prev_open else sorted(now_open)

    unclassified = [e for e in entries if e.get("class") in (None, "", "unresolved")]
    by_class = Counter(e["class"] for e in entries)
    by_file = Counter(e["file"] for e in entries)

    # Identity invariant
    assert missing_arcs_measured == missing_arcs_in_ledger + unmapped_arcs, (
        missing_arcs_measured,
        missing_arcs_in_ledger,
        unmapped_arcs,
    )

    per_file = [
        {
            "file": f,
            "branches_hit": summary["by_file"][f]["branches_hit"],
            "branches_total": summary["by_file"][f]["branches_total"],
            "missing_arcs": summary["by_file"][f]["missing_arcs"],
        }
        for f in sorted(summary["by_file"])
    ]

    ledger = {
        "identity_scheme": "{file}:{line}:b{branch_id}",
        "branches_hit": branches_hit,
        "branches_total": branches_total,
        "missing_arcs_measured": missing_arcs_measured,
        "missing_arcs_in_ledger": missing_arcs_in_ledger,
        "unmapped_arcs": unmapped_arcs,
        "unmapped_arc_ids": unmapped_ids,
        "unclassified_arcs": len(unclassified),
        "resolved_arcs": len(resolved_ids),
        "resolved_arc_ids": resolved_ids,
        "newly_open_arc_ids": newly_open if prev_open else [],
        "still_open_from_previous": len(still_open_from_prev),
        "open_arc_ids": sorted(now_open),
        # aliases kept for older readers
        "missing_arcs": missing_arcs_measured,
        "total_missing_arcs": missing_arcs_measured,
        "unresolved_count": len(unclassified),
        "by_class": dict(by_class),
        "by_file_missing": dict(by_file),
        "per_file": per_file,
        "entries": entries,
        "reconciliation": {
            "equation": "missing_arcs_measured == missing_arcs_in_ledger + unmapped_arcs",
            "holds": missing_arcs_measured == missing_arcs_in_ledger + unmapped_arcs,
        },
        "l13_branch_eligible": (
            missing_arcs_measured == 0
            and unmapped_arcs == 0
            and len(unclassified) == 0
        ),
        "pass_ready": (
            missing_arcs_measured == 0
            and unmapped_arcs == 0
            and len(unclassified) == 0
        ),
        "l13_branch_gate": (
            "FAIL until missing_arcs_measured==0 and unmapped_arcs==0 "
            "and unclassified_arcs==0; open→resolved tracked by arc_id"
        ),
    }

    OUT_JSON.write_text(
        json.dumps(ledger, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    # Persist open set for next run's resolved detection
    HISTORY_JSON.write_text(
        json.dumps(
            {
                "open_arc_ids": sorted(now_open),
                "branches_hit": branches_hit,
                "branches_total": branches_total,
                "missing_arcs_measured": missing_arcs_measured,
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
        "L13 branch eligibility requires:",
        "",
        "```text",
        "missing_arcs_measured == 0",
        "unmapped_arcs == 0",
        "unclassified_arcs == 0",
        "```",
        "",
        "## Reconciliation",
        "",
        f"- **branches_hit:** {branches_hit}",
        f"- **branches_total:** {branches_total}",
        f"- **missing_arcs_measured:** {missing_arcs_measured}  (`total - hit`)",
        f"- **missing_arcs_in_ledger:** {missing_arcs_in_ledger}",
        f"- **unmapped_arcs:** {unmapped_arcs}",
        f"- **unclassified_arcs:** {len(unclassified)}",
        f"- **resolved_arcs (this run):** {len(resolved_ids)}  (were open, now taken)",
        f"- Equation holds: "
        f"`{missing_arcs_measured} == {missing_arcs_in_ledger} + {unmapped_arcs}` → "
        f"**{missing_arcs_measured == missing_arcs_in_ledger + unmapped_arcs}**",
        f"- L13 branch eligible: **{ledger['l13_branch_eligible']}**",
        f"- Identity: `{ledger['identity_scheme']}`",
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

    if resolved_ids:
        lines += ["", "## Resolved this run (open → taken)", ""]
        for aid in resolved_ids[:100]:
            lines.append(f"- `{aid}`")
        if len(resolved_ids) > 100:
            lines.append(f"- … and {len(resolved_ids) - 100} more")

    if unmapped_ids:
        lines += ["", "## Unmapped (generator defect — must be zero)", ""]
        for aid in unmapped_ids:
            lines.append(f"- `{aid}`")

    lines += [
        "",
        "## Open ledger",
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
        "## Notes",
        "",
        "- `unclassified_arcs == 0` means every **open** arc has a class; it does **not** mean arcs are closed.",
        "- `resolved_arcs` counts identities that transitioned open→taken since the previous ledger run.",
        "- Progress is `open → resolved` on stable `arc_id`, not a regenerated list with `resolved_arcs: 0`.",
        "",
    ]
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    print(
        json.dumps(
            {
                "branches_hit": branches_hit,
                "branches_total": branches_total,
                "missing_arcs_measured": missing_arcs_measured,
                "missing_arcs_in_ledger": missing_arcs_in_ledger,
                "unmapped_arcs": unmapped_arcs,
                "unclassified_arcs": len(unclassified),
                "resolved_arcs": len(resolved_ids),
                "equation_holds": missing_arcs_measured
                == missing_arcs_in_ledger + unmapped_arcs,
                "l13_branch_eligible": ledger["l13_branch_eligible"],
                "md": str(OUT_MD),
                "json": str(OUT_JSON),
            },
            indent=2,
        )
    )
    return 0 if ledger["l13_branch_eligible"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
