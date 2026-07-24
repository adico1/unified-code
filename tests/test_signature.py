from inspect import Parameter, signature

import unified


def test_every_public_operation_has_one_input():
    operations = (
        unified.letter,
        unified.world,
        unified.beginning,
        unified.end,
        unified.good,
        unified.bad,
        unified.below,
        unified.above,
        unified.west,
        unified.east,
        unified.south,
        unified.north,
        unified.line,
        unified.plane,
        unified.space,
        unified.time,
        unified.value,
        unified.verify,
    )

    for operation in operations:
        parameters = tuple(signature(operation).parameters.values())
        assert len(parameters) == 1
        assert parameters[0].kind is Parameter.POSITIONAL_OR_KEYWORD
