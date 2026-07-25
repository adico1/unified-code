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
