"""Restricted request adapter fixture: parsed as data and never executed."""

STANDARD_TEN = {
    "standard": "uc.run-request/1",
    "declaration": "../../seed/declarations/invoice_total.json",
    "host_input": {
        "document": {
            "items": [{"quantity": 2, "unit_price": "10.00"}],
            "tax_rate": "0.10",
        },
    },
}
