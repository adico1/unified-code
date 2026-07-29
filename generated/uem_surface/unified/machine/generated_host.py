"""Generated adapter to the independent Python UEM host."""

from unified.machine.host import run_program as audited_python_host_boundary

HOST_IMPLEMENTATION = "python-independent"
HOST_ROLE = "boundary"

def run(thing):
    return audited_python_host_boundary(thing)
