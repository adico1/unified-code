/* UEM-16 C99 public API — Thing is opaque machine state. Spec: UEM_SPEC.md */
#ifndef UEM_H
#define UEM_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define UEM_MAGIC0 'U'
#define UEM_MAGIC1 'E'
#define UEM_MAGIC2 'M'
#define UEM_MAGIC3 0x16
#define UEM_FORMAT_VERSION 1
#define UEM_REGISTRY_VERSION 1
#define UEM_MAX_STEPS_DEFAULT 100000u
#define UEM_MAX_QUEUE_DEFAULT 10000u
#define UEM_MAX_EVIDENCE 512
#define UEM_MAX_INSTR 4096
#define UEM_MAX_OPERAND 4096
#define UEM_MAX_IMAGE (8u * 1024u * 1024u)
#define UEM_MAX_HOST_JSON (2u * 1024u * 1024u)
#define UEM_MAX_OUT (2u * 1024u * 1024u)

typedef enum {
    UEM_OK = 0,
    UEM_ERR_IO = 1,
    UEM_ERR_NOMEM = 2,
    UEM_ERR_DECODE = 3,
    UEM_ERR_VERIFY = 4,
    UEM_ERR_LIMIT = 5,
    UEM_ERR_RUNTIME = 6,
    UEM_ERR_ARGS = 7
} uem_status;

typedef struct uem_machine uem_machine;

/* Decode + verify canonical bytecode. On success machine is ready to load host. */
uem_status uem_decode_verify(const uint8_t *bytes, size_t len, uem_machine **out, char *err, size_t errlen);

/* Free machine. */
void uem_free(uem_machine *m);

/* Set host input JSON object string (owned copy inside machine). */
uem_status uem_set_host_json(uem_machine *m, const char *json, char *err, size_t errlen);

/* Run until STOP, limit, or fatal. Fulfills OUTWARD via host callbacks set below. */
typedef int (*uem_outward_fn)(void *ctx, const char *effect, const char *source_json,
                              char *result_json, size_t result_cap, char *err, size_t errlen);

void uem_set_outward_handler(uem_machine *m, uem_outward_fn fn, void *ctx);

uem_status uem_run(uem_machine *m, char *err, size_t errlen);

/* Canonical result JSON for differential comparison (caller frees with free()). */
char *uem_result_json(const uem_machine *m);

/* Accessors */
const char *uem_state(const uem_machine *m);
const char *uem_stop_reason(const uem_machine *m);
const char *uem_program_sha256(const uem_machine *m);
uint32_t uem_instruction_count(const uem_machine *m);
uint32_t uem_step_count(const uem_machine *m);

/* Default file-based outward for read_utf8 / read_json. */
int uem_default_outward(void *ctx, const char *effect, const char *source_json,
                        char *result_json, size_t result_cap, char *err, size_t errlen);

#ifdef __cplusplus
}
#endif
#endif
