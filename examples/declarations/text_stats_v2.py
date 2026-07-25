"""Text statistics application — Unified Code declaration(thing) form.

Executable Python. One thing in, one thing out. Plain data only.
"""


def declaration(thing):
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
                    "name": "validate_text",
                    "role": "validate",
                    "doc": "Require readable text inside the thing. No I/O.",
                    "input_shape": {
                        "type": "map",
                        "fields": {"text": {"type": "str", "required": True}},
                    },
                    "transformation": {
                        "kind": "require_str_field",
                        "field": "text",
                        "missing_error": "missing-text",
                        "invalid_error": "invalid-text",
                    },
                    "invariants": ("text is str when formed",),
                    "errors": (
                        {"when": "missing text", "state": "absent", "error": "missing-text"},
                        {"when": "non-str text", "state": "invalid", "error": "invalid-text"},
                    ),
                    "boundaries": (),
                    "tests": (),
                },
                {
                    "name": "calculate_stats",
                    "role": "transform",
                    "doc": "Compute deterministic text statistics. No I/O.",
                    "input_shape": {
                        "type": "map",
                        "fields": {"text": {"type": "str", "required": True}},
                    },
                    "transformation": {
                        "kind": "text_stats",
                        "text_field": "text",
                        "stats_field": "stats",
                    },
                    "invariants": (
                        "characters == len(text)",
                        "lines == len(text.splitlines())",
                        "words == len(text.split())",
                        "unique_words uses casefold",
                    ),
                    "errors": (
                        {"when": "missing text", "state": "absent", "error": "missing-text"},
                    ),
                    "boundaries": (),
                    "tests": (),
                },
            ),
            "composition": (
                "inward",
                "letter",
                "read_text_source",
                "validate_text",
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
                    "part:validate_text",
                    "validate_text:ok",
                    "part:calculate_stats",
                    "calculate_stats:ok",
                ),
            },
            "errors": (
                "missing-source",
                "extra-source",
                "file-not-found",
                "not-a-file",
                "invalid-utf8",
                "read-failure",
                "missing-text",
            ),
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
                    "name": "trailing_nl",
                    "kind": "file_text",
                    "text": "line\n",
                    "expect_stats": {
                        "characters": 5,
                        "lines": 1,
                        "words": 1,
                        "unique_words": 1,
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
                    "name": "evidence_order",
                    "kind": "evidence_order",
                },
                {
                    "name": "idempotent",
                    "kind": "idempotent_output",
                },
            ),
        },
        "evidence": (*thing.get("evidence", ()), "declaration:text-stats-v2"),
        "state": "formed",
    }
