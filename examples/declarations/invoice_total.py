"""Invoice totals — generic expression composition with bindings (CSE).

No invoice-specific renderer kinds. Monetary fields are decimal *strings*.
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
    ref,
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
                    "type_error": "quantity-not-integer",
                    "missing_error": "missing-quantity",
                }
            ),
            "bound": 1,
            "path": ("quantity",),
            "error": "quantity-below-minimum",
        }
    )

    # --- per-item unit_price: required decimal *string* >= 0 ---
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
                    "type_error": "unit_price-not-decimal-string",
                    "missing_error": "missing-unit_price",
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

    # Bindings: compute once (CSE) — subtotal, tax_rate, tax, total
    bindings = {
        "subtotal": _node(
            quantize(
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
        ),
        "tax_rate": _node(
            max_value(
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
                                    "type_error": "tax_rate-not-decimal-string",
                                    "missing_error": "missing-tax_rate",
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
        ),
    }
    # tax depends on subtotal + tax_rate bindings
    bindings["tax"] = _node(
        quantize(
            {
                "of": mul(
                    {
                        "values": (
                            ref({"name": "subtotal"}),
                            ref({"name": "tax_rate"}),
                        )
                    }
                ),
                "exp": "0.01",
                "rounding": "ROUND_HALF_UP",
            }
        )
    )
    bindings["total"] = _node(
        quantize(
            {
                "of": add(
                    {
                        "values": (
                            ref({"name": "subtotal"}),
                            ref({"name": "tax"}),
                        )
                    }
                ),
                "exp": "0.01",
                "rounding": "ROUND_HALF_UP",
            }
        )
    )

    result = object_expr(
        {
            "fields": {
                "item_count": count({"of": items}),
                "subtotal": decimal_str({"of": ref({"name": "subtotal"}), "places": 2}),
                "tax": decimal_str({"of": ref({"name": "tax"}), "places": 2}),
                "total": decimal_str({"of": ref({"name": "total"}), "places": 2}),
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
                    "doc": "Validate document and compute totals via expression tree + bindings.",
                    "transformation": {
                        "kind": "expression",
                        "input_key": "document",
                        "merge": "stats",
                        "bindings": bindings,
                        "program": _node(result),
                    },
                    "invariants": (
                        "subtotal quantized to 0.01",
                        "tax ROUND_HALF_UP to 0.01",
                        "total = subtotal + tax",
                        "unit_price and tax_rate are decimal strings only",
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
                    "name": "exact_decimal_add",
                    "kind": "json_document",
                    "document": {
                        "tax_rate": "0.00",
                        "items": [
                            {"quantity": 1, "unit_price": "0.10"},
                            {"quantity": 1, "unit_price": "0.20"},
                        ],
                    },
                    "expect_stats": {
                        "item_count": 2,
                        "subtotal": "0.30",
                        "tax": "0.00",
                        "total": "0.30",
                    },
                },
                {
                    # 0.05 * 0.10 = 0.005 → ROUND_HALF_UP → 0.01
                    "name": "round_half_up_half_cent",
                    "kind": "json_document",
                    "document": {
                        "tax_rate": "0.10",
                        "items": [{"quantity": 1, "unit_price": "0.05"}],
                    },
                    "expect_stats": {
                        "item_count": 1,
                        "subtotal": "0.05",
                        "tax": "0.01",
                        "total": "0.06",
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
                    "name": "unicode_json",
                    "kind": "json_document",
                    "document": {
                        "tax_rate": "0.00",
                        "note": "חשבונית",
                        "items": [{"quantity": 1, "unit_price": "1.00", "label": "פריט"}],
                    },
                    "expect_stats": {
                        "item_count": 1,
                        "subtotal": "1.00",
                        "tax": "0.00",
                        "total": "1.00",
                    },
                },
                {
                    "name": "stdin_json",
                    "kind": "json_stdin",
                    "document": {
                        "tax_rate": "0.20",
                        "items": [{"quantity": 1, "unit_price": "5.00"}],
                    },
                    "expect_stats": {
                        "item_count": 1,
                        "subtotal": "5.00",
                        "tax": "1.00",
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
                    "name": "invalid_json",
                    "kind": "raw_file_error",
                    "raw": "{not json",
                    "error": "invalid-json",
                },
                {
                    "name": "not_object",
                    "kind": "raw_file_error",
                    "raw": "[1,2,3]",
                    "error": "input-not-an-object",
                },
                {
                    "name": "error_missing_items",
                    "kind": "json_error",
                    "document": {"tax_rate": "0.1"},
                    "error": "missing-items",
                },
                {
                    "name": "error_items_not_list",
                    "kind": "json_error",
                    "document": {"tax_rate": "0.1", "items": {}},
                    "error": "items-not-a-list",
                },
                {
                    "name": "error_item_not_object",
                    "kind": "json_error",
                    "document": {"tax_rate": "0.1", "items": [1]},
                    "error": "item-not-an-object",
                },
                {
                    "name": "error_missing_quantity",
                    "kind": "json_error",
                    "document": {
                        "tax_rate": "0.1",
                        "items": [{"unit_price": "1.00"}],
                    },
                    "error": "missing-quantity",
                },
                {
                    "name": "error_qty_not_int",
                    "kind": "json_error",
                    "document": {
                        "tax_rate": "0.1",
                        "items": [{"quantity": "2", "unit_price": "1.00"}],
                    },
                    "error": "quantity-not-integer",
                },
                {
                    "name": "error_qty_below_min",
                    "kind": "json_error",
                    "document": {
                        "tax_rate": "0.1",
                        "items": [{"quantity": 0, "unit_price": "1.00"}],
                    },
                    "error": "quantity-below-minimum",
                },
                {
                    "name": "error_missing_unit_price",
                    "kind": "json_error",
                    "document": {
                        "tax_rate": "0.1",
                        "items": [{"quantity": 1}],
                    },
                    "error": "missing-unit_price",
                },
                {
                    "name": "error_unit_price_not_string",
                    "kind": "json_error",
                    "document": {
                        "tax_rate": "0.1",
                        "items": [{"quantity": 1, "unit_price": 1.5}],
                    },
                    "error": "unit_price-not-decimal-string",
                },
                {
                    "name": "error_unit_price_int_rejected",
                    "kind": "json_error",
                    "document": {
                        "tax_rate": "0.1",
                        "items": [{"quantity": 1, "unit_price": 2}],
                    },
                    "error": "unit_price-not-decimal-string",
                },
                {
                    "name": "error_unit_price_below_min",
                    "kind": "json_error",
                    "document": {
                        "tax_rate": "0.1",
                        "items": [{"quantity": 1, "unit_price": "-0.01"}],
                    },
                    "error": "unit_price-below-minimum",
                },
                {
                    "name": "error_missing_tax_rate",
                    "kind": "json_error",
                    "document": {
                        "items": [{"quantity": 1, "unit_price": "1.00"}],
                    },
                    "error": "missing-tax_rate",
                },
                {
                    "name": "error_tax_rate_not_string",
                    "kind": "json_error",
                    "document": {
                        "tax_rate": 0.2,
                        "items": [{"quantity": 1, "unit_price": "1.00"}],
                    },
                    "error": "tax_rate-not-decimal-string",
                },
                {
                    "name": "error_tax_rate_below_0",
                    "kind": "json_error",
                    "document": {
                        "tax_rate": "-0.1",
                        "items": [{"quantity": 1, "unit_price": "1.00"}],
                    },
                    "error": "tax_rate-below-0",
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
