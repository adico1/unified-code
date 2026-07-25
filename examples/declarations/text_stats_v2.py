"""Text statistics — rewritten with generic expression operators only.

No kind: text_stats. Uses str_len / line_count / word_count /
unique_casefold_word_count expression nodes.
"""

from unified.generator.expr import (
    field,
    line_count,
    object_expr,
    str_len,
    unique_casefold_word_count,
    unwrap_expr,
    word_count,
)


def _node(x):
    n = unwrap_expr(x)
    if n is None:
        raise ValueError(f"expected expression node, got {x!r}")
    return n


def declaration(thing):
    text = field({"path": ("text",)})
    result = object_expr(
        {
            "fields": {
                "characters": str_len({"of": text}),
                "lines": line_count({"of": text}),
                "words": word_count({"of": text}),
                "unique_words": unique_casefold_word_count({"of": text}),
            }
        }
    )
    return {
        **thing,
        "value": {
            "project": {
                "name": "uc-text-stats-v2",
                "package": "uc_text_stats_v2",
                "description": (
                    "Read UTF-8 text from a file or stdin; "
                    "emit deterministic JSON text statistics."
                ),
            },
            "inputs": {
                "cli": {
                    "script": "uc-text-stats-v2",
                    "argv": {
                        "field": "source",
                        "arity": 1,
                        "stdin_token": "-",
                        "errors": {
                            "missing": "missing-source",
                            "extra": "extra-source",
                        },
                    },
                },
            },
            "boundaries": (
                {
                    "kind": "read_utf8_source",
                    "name": "read_text_source",
                    "source_field": "source",
                    "text_field": "text",
                },
            ),
            "features": (
                {
                    "name": "calculate_stats",
                    "role": "transform",
                    "doc": "Compute text statistics via generic string expressions.",
                    "transformation": {
                        "kind": "expression",
                        "input_key": "text",
                        "merge": "stats",
                        "program": _node(result),
                    },
                    "invariants": (),
                    "errors": (),
                    "boundaries": (),
                    "tests": (),
                },
            ),
            "composition": (
                "inward",
                "letter",
                "read_text_source",
                "calculate_stats",
                "verify",
                "outward",
            ),
            "presentation": {
                "success_from": "stats",
                "success_keys": ("characters", "lines", "words", "unique_words"),
            },
            "verify": {
                "require_value_field": "stats",
                "require_evidence_contains": (
                    "boundary:inward",
                    "letter:distinguished",
                    "boundary:read_text_source",
                    "read:ok",
                    "part:calculate_stats",
                    "calculate_stats:ok",
                ),
            },
            "tests": (
                {
                    "name": "empty",
                    "kind": "file_text",
                    "text": "",
                    "expect_stats": {
                        "characters": 0,
                        "lines": 0,
                        "words": 0,
                        "unique_words": 0,
                    },
                },
                {
                    "name": "one_line",
                    "kind": "file_text",
                    "text": "hello world",
                    "expect_stats": {
                        "characters": 11,
                        "lines": 1,
                        "words": 2,
                        "unique_words": 2,
                    },
                },
                {
                    "name": "casefold",
                    "kind": "file_text",
                    "text": "Go go GO",
                    "expect_stats": {
                        "characters": 8,
                        "lines": 1,
                        "words": 3,
                        "unique_words": 1,
                    },
                },
                {
                    "name": "unicode",
                    "kind": "file_text",
                    "text": "שלום עולם",
                    "expect_stats": {
                        "characters": 9,
                        "lines": 1,
                        "words": 2,
                        "unique_words": 2,
                    },
                },
                {
                    "name": "stdin_words",
                    "kind": "stdin_text",
                    "text": "stdin words here",
                    "expect_stats": {
                        "characters": 16,
                        "lines": 1,
                        "words": 3,
                        "unique_words": 3,
                    },
                },
                {
                    "name": "missing_arg",
                    "kind": "cli_error",
                    "argv": [],
                    "error": "missing-source",
                },
                {
                    "name": "extra_arg",
                    "kind": "cli_error",
                    "argv": ["a", "b"],
                    "error": "extra-source",
                },
                {
                    "name": "missing_file",
                    "kind": "missing_file",
                },
                {
                    "name": "directory",
                    "kind": "directory",
                },
                {
                    "name": "invalid_utf8",
                    "kind": "invalid_utf8",
                },
                {
                    "name": "stable_json",
                    "kind": "stable_json",
                    "text": "x",
                    "expect_json": '{"characters":1,"lines":1,"words":1,"unique_words":1}',
                },
                {
                    "name": "idempotent",
                    "kind": "idempotent_output",
                },
                {
                    "name": "evidence_order",
                    "kind": "evidence_order",
                    "required": (
                        "boundary:inward",
                        "letter:distinguished",
                        "boundary:read_text_source",
                        "read:ok",
                        "part:calculate_stats",
                        "calculate_stats:ok",
                        "script-law:pass",
                        "present_result:ok",
                        "boundary:outward",
                    ),
                },
            ),
        },
        "evidence": (*thing.get("evidence", ()), "declaration:text-stats-v2-expr"),
        "state": "formed",
    }
