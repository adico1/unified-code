"""Generated reusable Standard Ten numeric-library interface."""

from .runtime import _numeric
from .specification import SPECIFICATION

LIBRARY_IDENTITY = 'e962f575d085938a4a9ddf03173f320fc28951c14ae02d4cc284e3501dffe167'

def invoke(request):
    return _numeric(SPECIFICATION["program"], request)
