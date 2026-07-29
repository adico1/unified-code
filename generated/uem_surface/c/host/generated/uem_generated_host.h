/* Generated adapter to the independent C99 UEM host. */
#ifndef UEM_GENERATED_HOST_H
#define UEM_GENERATED_HOST_H

#include "uem.h"

typedef struct {
    const uint8_t *bytecode;
    size_t bytecode_len;
    const char *host_json;
    uem_machine *machine;
    uem_status status;
    char *result_json;
    char error[256];
} uem_generated_thing;

uem_generated_thing *uem_generated_host(uem_generated_thing *thing);

#endif
