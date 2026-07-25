"""Generic expression constructors and compilation tests."""

from unified.generator.expr import (
    add,
    as_decimal,
    as_int,
    count,
    decimal_str,
    field,
    min_value,
    mul,
    object_expr,
    quantize,
    require,
    str_len,
    sum_each,
    unique_casefold_word_count,
    unwrap_expr,
    validate_expression,
    word_count,
)


def test_field_and_str_len_compose():
    text = field({"path": ("text",)})
    n = unwrap_expr(str_len({"of": text}))
    assert n["op"] == "str_len"
    assert validate_expression(n) == ()


def test_invoice_style_tree_validates():
    qty = min_value(
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
    price = as_decimal(
        {
            "of": field({"path": ("unit_price",)}),
            "path": ("unit_price",),
        }
    )
    line = mul({"values": (qty, price)})
    sub = quantize(
        {
            "of": sum_each(
                {
                    "collection": field({"path": ("items",)}),
                    "each": line,
                    "path": ("items",),
                }
            ),
            "exp": "0.01",
            "rounding": "ROUND_HALF_UP",
        }
    )
    tree = unwrap_expr(
        object_expr(
            {
                "fields": {
                    "item_count": count({"of": field({"path": ("items",)})}),
                    "subtotal": decimal_str({"of": sub, "places": 2}),
                    "words": word_count({"of": field({"path": ("text",)})}),
                    "uniq": unique_casefold_word_count({"of": field({"path": ("text",)})}),
                    "sumish": add({"values": (sub, sub)}),
                }
            }
        )
    )
    assert validate_expression(tree) == ()


def test_unknown_op_rejected():
    errs = validate_expression({"op": "not_a_real_op"})
    assert errs


def test_as_decimal_strict_string_in_runtime():
    """Generated runtime must reject JSON ints for as_decimal (no custom class)."""
    import tempfile
    from pathlib import Path

    from unified.boundary import inward
    from unified.generator import run_build
    from unified.generator.expr_emit import emit_expr_runtime_module

    src = emit_expr_runtime_module()
    assert "class " not in src
    assert "expr_fail" in src
    assert "not-decimal-string" in src or "isinstance(value, str)" in src

    # smoke eval
    ns = {}
    exec(compile(src, "expr_runtime.py", "exec"), ns, ns)
    eval_expr = ns["eval_expr"]
    is_expr_fail = ns["is_expr_fail"]
    node = {"op": "as_decimal", "of": {"op": "literal", "value": 2}, "path": ("x",)}
    try:
        eval_expr(node, {"root": {}, "path": []})
        assert False, "expected failure"
    except ValueError as exc:
        assert is_expr_fail(exc)
        assert exc.uc_expr_error == "not-decimal-string"

    node2 = {
        "op": "as_decimal",
        "of": {"op": "literal", "value": "2.50"},
        "path": ("x",),
    }
    assert str(eval_expr(node2, {"root": {}, "path": []})) == "2.50"
