/* Generated one-Thing adapter; execution remains independent C99. */
#include "uem_generated_host.h"

static uem_generated_thing *audited_c_host_boundary(
    uem_generated_thing *thing
) {
    thing->status = uem_decode_verify(
        thing->bytecode, thing->bytecode_len, &thing->machine,
        thing->error, sizeof thing->error
    );
    if (thing->status != UEM_OK) return thing;
    thing->status = uem_set_host_json(
        thing->machine, thing->host_json, thing->error,
        sizeof thing->error
    );
    if (thing->status != UEM_OK) return thing;
    thing->status = uem_run(thing->machine, thing->error, sizeof thing->error);
    thing->result_json = uem_result_json(thing->machine);
    return thing;
}

uem_generated_thing *uem_generated_host(uem_generated_thing *thing) {
    return audited_c_host_boundary(thing);
}
