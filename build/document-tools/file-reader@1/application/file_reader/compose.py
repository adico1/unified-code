"""Generated nested seven-stage composition."""

from .runtime import inward, outward
from .stage_01_outer_to_inner import part as stage_01
from .stage_02_inner_to_core import part as stage_02
from .stage_03_core_prepare import part as stage_03
from .stage_04_core_processing import part as stage_04
from .stage_05_core_collect import part as stage_05
from .stage_06_core_to_inner import part as stage_06
from .stage_07_inner_to_outer import part as stage_07


def program(thing):
    return outward(stage_07(stage_06(stage_05(stage_04(stage_03(stage_02(stage_01(inward(thing)))))))))
