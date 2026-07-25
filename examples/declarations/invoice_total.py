"""Invoice totals — generic expression composition only.

No invoice-specific renderer kinds. Behavior is declared by composing
domain-neutral expression operators.
"""

from unified.generator.expr import (
    add,
    as_decimal,
    as_int,
    count,
    decimal_str,
    field,
    max_value,
    min_value,
    mul,
    object_expr,
    quantize,
    require,
    sum_each,
    unwrap_expr,
)


def _node(x):
    n = unwrap_expr(x)
    if n is None:
        raise ValueError(f"expected expression node, got {x!r}")
    return n


def declaration(thing):
    # --- per-item quantity: required int >= 1 ---
    quantity = min_value(
        {
            "of": as_int(
                {
                    "of": require(
                        {
                            "of": field({"path": ("quantity",)}),
                            "path": ("quantity",),
                            "error": "missing-quantity",
                        }
                    ),
                    "path": ("quantity",),
                }
            ),
            "bound": 1,
            "path": ("quantity",),
            "error": "quantity-below-minimum",
        }
    )

    # --- per-item unit_price: required decimal string >= 0 ---
    unit_price = min_value(
        {
            "of": as_decimal(
                {
                    "of": require(
                        {
                            "of": field({"path": ("unit_price",)}),
                            "path": ("unit_price",),
                            "error": "missing-unit_price",
                        }
                    ),
                    "path": ("unit_price",),
                }
            ),
            "bound": "0",
            "path": ("unit_price",),
            "error": "unit_price-below-minimum",
        }
    )

    line_amount = mul({"values": (quantity, unit_price)})

    items = require(
        {
            "of": field({"path": ("items",)}),
            "path": ("items",),
            "error": "missing-items",
        }
    )

    subtotal = quantize(
        {
            "of": sum_each(
                {
                    "collection": items,
                    "each": line_amount,
                    "path": ("items",),
                }
            ),
            "exp": "0.01",
            "rounding": "ROUND_HALF_UP",
        }
    )

    tax_rate = max_value(
        {
            "of": min_value(
                {
                    "of": as_decimal(
                        {
                            "of": require(
                                {
                                    "of": field({"path": ("tax_rate",)}),
                                    "path": ("tax_rate",),
                                    "error": "missing-tax_rate",
                                }
                            ),
                            "path": ("tax_rate",),
                        }
                    ),
                    "bound": "0",
                    "path": ("tax_rate",),
                    "error": "tax_rate-below-0",
                }
            ),
            "bound": "1",
            "path": ("tax_rate",),
            "error": "tax_rate-above-1",
        }
    )

    tax = quantize(
        {
            "of": mul({"values": (subtotal, tax_rate)}),
            "exp": "0.01",
            "rounding": "ROUND_HALF_UP",
        }
    )

    total = quantize(
        {
            "of": add({"values": (subtotal, tax)}),
            "exp": "0.01",
            "rounding": "ROUND_HALF_UP",
        }
    )

    result = object_expr(
        {
            "fields": {
                "item_count": count({"of": items}),
                "subtotal": decimal_str({"of": subtotal, "places": 2}),
                "tax": decimal_str({"of": tax, "places": 2}),
                "total": decimal_str({"of": total, "places": 2}),
            }
        }
    )

    return {
        **thing,
        "value": {
            "project": {
                "name": "uc-invoice-total",
                "package": "uc_invoice_total",
                "description": "Deterministic invoice totals via generic expression composition.",
            },
            "inputs": {
                "cli": {
                    "script": "uc-invoice-total",
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
                    "kind": "read_json_source",
                    "name": "read_json_source",
                    "source_field": "source",
                    "document_field": "document",
                },
            ),
            "features": (
                {
                    "name": "calculate_totals",
                    "role": "transform",
                    "doc": "Validate document and compute invoice totals via expression tree.",
                    "transformation": {
                        "kind": "expression",
                        "input_key": "document",
                        "merge": "stats",
                        "program": _node(result),
                    },
                    "invariants": (
                        "subtotal quantized to 0.01",
                        "tax ROUND_HALF_UP to 0.01",
                        "total = subtotal + tax",
                    ),
                    "errors": (),
                    "boundaries": (),
                    "tests": (),
                },
            ),
            "composition": (
                "inward",
                "letter",
                "read_json_source",
                "calculate_totals",
                "verify",
                "outward",
            ),
            "presentation": {
                "success_from": "stats",
                "success_keys": ("item_count", "subtotal", "tax", "total"),
                "include_error_path": True,
            },
            "verify": {
                "require_value_field": "stats",
                "require_evidence_contains": (
                    "boundary:inward",
                    "letter:distinguished",
                    "boundary:read_json_source",
                    "read:ok",
                    "part:calculate_totals",
                    "calculate_totals:ok",
                ),
            },
            "tests": (
                {
                    "name": "empty_items",
                    "kind": "json_document",
                    "document": {"tax_rate": "0.20", "items": []},
                    "expect_stats": {
                        "item_count": 0,
                        "subtotal": "0.00",
                        "tax": "0.00",
                        "total": "0.00",
                    },
                },
                {
                    "name": "one_item",
                    "kind": "json_document",
                    "document": {
                        "tax_rate": "0.10",
                        "items": [{"quantity": 1, "unit_price": "10.00"}],
                    },
                    "expect_stats": {
                        "item_count": 1,
                        "subtotal": "10.00",
                        "tax": "1.00",
                        "total": "11.00",
                    },
                },
                {
                    "name": "multiple_items",
                    "kind": "json_document",
                    "document": {
                        "tax_rate": "0.20",
                        "items": [
                            {"quantity": 2, "unit_price": "3.50"},
                            {"quantity": 1, "unit_price": "4.00"},
                        ],
                    },
                    "expect_stats": {
                        "item_count": 2,
                        "subtotal": "11.00",
                        "tax": "2.20",
                        "total": "13.20",
                    },
                },
                {
                    "name": "round_half_up",
                    "kind": "json_document",
                    "document": {
                        "tax_rate": "0.15",
                        "items": [{"quantity": 1, "unit_price": "1.00"}],
                    },
                    "expect_stats": {
                        "item_count": 1,
                        "subtotal": "1.00",
                        "tax": "0.15",
                        "total": "1.15",
                    },
                },
                {
                    "name": "zero_tax",
                    "kind": "json_document",
                    "document": {
                        "tax_rate": "0",
                        "items": [{"quantity": 2, "unit_price": "5.00"}],
                    },
                    "expect_stats": {
                        "item_count": 1,
                        "subtotal": "10.00",
                        "tax": "0.00",
                        "total": "10.00",
                    },
                },
                {
                    "name": "tax_one",
                    "kind": "json_document",
                    "document": {
                        "tax_rate": "1",
                        "items": [{"quantity": 1, "unit_price": "3.00"}],
                    },
                    "expect_stats": {
                        "item_count": 1,
                        "subtotal": "3.00",
                        "tax": "3.00",
                        "total": "6.00",
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
                    "kind": "json_stable",
                    "document": {
                        "tax_rate": "0.20",
                        "items": [
                            {"quantity": 2, "unit_price": "3.50"},
                            {"quantity": 1, "unit_price": "4.00"},
                        ],
                    },
                    "expect_json": '{"item_count":2,"subtotal":"11.00","tax":"2.20","total":"13.20"}',
                },
                {
                    "name": "idempotent",
                    "kind": "json_idempotent",
                    "document": {
                        "tax_rate": "0.20",
                        "items": [{"quantity": 1, "unit_price": "1.00"}],
                    },
                },
                {
                    "name": "error_missing_items",
                    "kind": "json_error",
                    "document": {"tax_rate": "0.1"},
                    "error": "missing-items",
                },
                {
                    "name": "error_qty_type",
                    "kind": "json_error",
                    "document": {
                        "tax_rate": "0.1",
                        "items": [{"quantity": "2", "unit_price": "1.00"}],
                    },
                    "error": "invalid-integer",
                },
                {
                    "name": "error_tax_high",
                    "kind": "json_error",
                    "document": {
                        "tax_rate": "1.5",
                        "items": [{"quantity": 1, "unit_price": "1.00"}],
                    },
                    "error": "tax_rate-above-1",
                },
                {
                    "name": "evidence_order",
                    "kind": "json_evidence_order",
                    "document": {
                        "tax_rate": "0.0",
                        "items": [],
                    },
                    "required": (
                        "boundary:inward",
                        "letter:distinguished",
                        "boundary:read_json_source",
                        "read:ok",
                        "part:calculate_totals",
                        "calculate_totals:ok",
                        "script-law:pass",
                        "present_result:ok",
                        "boundary:outward",
                    ),
                },
            ),
        },
        "evidence": (*thing.get("evidence", ()), "declaration:invoice-total"),
        "state": "formed",
    }
