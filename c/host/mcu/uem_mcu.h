/* UEM-MCU-1 — bounded-memory embedding profile.
 * No filesystem. OUTWARD returns effect records to firmware.
 * A MCU family is supported only after physical board golden pass (L12).
 */
#ifndef UEM_MCU_H
#define UEM_MCU_H

#include <stddef.h>
#include <stdint.h>

#define UEM_MCU_PROFILE "UEM-MCU-1"
#define UEM_MCU_MAX_STEPS 10000u
#define UEM_MCU_MAX_EVIDENCE 256u
#define UEM_MCU_MAX_OUTWARD 16u
#define UEM_MCU_ARENA_DEFAULT (64u * 1024u)

typedef struct {
    uint8_t *arena;
    size_t arena_size;
    size_t arena_used;
} uem_mcu_mem;

typedef struct {
    const char *effect;
    const char *source_json; /* may be NULL */
} uem_mcu_outward;

typedef struct {
    int ok;
    const char *state;
    const char *stop_reason;
    const char *result_json; /* presentation or error payload */
    uint32_t outward_count;
    uem_mcu_outward outward[UEM_MCU_MAX_OUTWARD];
    const char *error;
} uem_mcu_result;

/* Run bytecode with caller-supplied arena and host JSON (no file I/O). */
int uem_mcu_run(
    const uint8_t *bytecode,
    size_t bytecode_len,
    const char *host_json,
    uem_mcu_mem *mem,
    uem_mcu_result *out
);

#endif
