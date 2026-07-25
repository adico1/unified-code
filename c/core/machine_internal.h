#ifndef UEM_MACHINE_INTERNAL_H
#define UEM_MACHINE_INTERNAL_H

#include "../include/uem.h"
#include "../third_party/cJSON.h"
#include <stdint.h>

typedef struct {
    uint8_t opcode;
    char *operand; /* NULL if none; heap; may contain embedded NULs */
    uint32_t operand_len; /* byte length of operand (not strlen) */
} uem_instr;

struct uem_machine {
    uem_instr *instr;
    uint32_t n_instr;
    uint32_t pc;
    cJSON *image;
    cJSON *store;
    cJSON *host;
    cJSON *acc;
    cJSON *outward_request;
    cJSON *outward_result;
    cJSON *ticket;
    cJSON *presentation;
    char **evidence;
    size_t n_evidence;
    size_t evidence_cap;
    char state[16];
    char stop_reason[64];
    int halted;
    uint32_t steps;
    uint32_t max_steps;
    uint32_t event_count;
    char program_sha256[65];
    uem_outward_fn outward;
    void *outward_ctx;
    char *pending_primitive;
    char *event_name;
    char *event_id;
    /* event queue as parallel arrays */
    char **q_name;
    char **q_id;
    size_t q_len;
    size_t q_cap;
    char **processed_ids;
    size_t n_processed;
    size_t processed_cap;
    uint32_t event_seq;
    cJSON *machine_fault;
    int invalid_soft; /* validation invalid but continue to STOP */
    cJSON *outward_log; /* array of {effect, source} */
    cJSON *events_emitted;
    cJSON *events_dequeued;
};

int uem_ev_append(uem_machine *m, const char *mark);
int uem_set_state(uem_machine *m, const char *st);
int uem_prim_apply(uem_machine *m, const char *name, char *err, size_t errlen);
int uem_expr_eval(uem_machine *m, cJSON *node, cJSON *root, cJSON *bindings, cJSON **out,
                  char *err, size_t errlen, cJSON **err_path);
void uem_ticket_construct(uem_machine *m);

/* registry */
int uem_registry_has(const char *name);

#endif
