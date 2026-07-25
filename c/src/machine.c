#include "machine_internal.h"
#include "../third_party/sha256.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdlib.h>

int uem_ev_append(uem_machine *m, const char *mark) {
    if (!m || !mark) return -1;
    if (m->n_evidence + 1 > m->evidence_cap) {
        size_t ncap = m->evidence_cap ? m->evidence_cap * 2 : 64;
        char **ne = (char **)realloc(m->evidence, ncap * sizeof(char *));
        if (!ne) return -1;
        m->evidence = ne;
        m->evidence_cap = ncap;
    }
    m->evidence[m->n_evidence] = strdup(mark);
    if (!m->evidence[m->n_evidence]) return -1;
    m->n_evidence++;
    return 0;
}

int uem_set_state(uem_machine *m, const char *st) {
    if (!m || !st) return -1;
    snprintf(m->state, sizeof m->state, "%s", st);
    return 0;
}

void uem_free(uem_machine *m) {
    uint32_t i;
    size_t j;
    if (!m) return;
    if (m->instr) {
        for (i = 0; i < m->n_instr; i++) free(m->instr[i].operand);
        free(m->instr);
    }
    cJSON_Delete(m->image);
    cJSON_Delete(m->store);
    cJSON_Delete(m->host);
    cJSON_Delete(m->acc);
    cJSON_Delete(m->outward_request);
    cJSON_Delete(m->outward_result);
    cJSON_Delete(m->ticket);
    cJSON_Delete(m->presentation);
    cJSON_Delete(m->machine_fault);
    cJSON_Delete(m->outward_log);
    cJSON_Delete(m->events_emitted);
    cJSON_Delete(m->events_dequeued);
    for (j = 0; j < m->n_evidence; j++) free(m->evidence[j]);
    free(m->evidence);
    free(m->pending_primitive);
    free(m->event_name);
    free(m->event_id);
    for (j = 0; j < m->q_len; j++) { free(m->q_name[j]); free(m->q_id[j]); }
    free(m->q_name);
    free(m->q_id);
    for (j = 0; j < m->n_processed; j++) free(m->processed_ids[j]);
    free(m->processed_ids);
    free(m);
}

uem_status uem_set_host_json(uem_machine *m, const char *json, char *err, size_t errlen) {
    cJSON *h;
    if (!m || !json) return UEM_ERR_ARGS;
    if (strlen(json) > UEM_MAX_HOST_JSON) {
        if (err) snprintf(err, errlen, "host-too-large");
        return UEM_ERR_LIMIT;
    }
    h = cJSON_Parse(json);
    if (!h || !cJSON_IsObject(h)) {
        if (h) cJSON_Delete(h);
        if (err) snprintf(err, errlen, "host-json");
        return UEM_ERR_ARGS;
    }
    if (m->host) cJSON_Delete(m->host);
    m->host = h;
    return UEM_OK;
}

void uem_set_outward_handler(uem_machine *m, uem_outward_fn fn, void *ctx) {
    if (!m) return;
    m->outward = fn;
    m->outward_ctx = ctx;
}

static void event_id_make(uem_machine *m, const char *name, char out[17]) {
    char raw[128];
    char hex[65];
    snprintf(raw, sizeof raw, "%s|%u", name, m->event_seq);
    uem_sha256_hex((const uint8_t *)raw, strlen(raw), hex);
    memcpy(out, hex, 16);
    out[16] = 0;
}

static int step_one(uem_machine *m, char *err, size_t errlen) {
    uem_instr *in;
    uint8_t op;
    char *operand;
    char emark[192];
    /* env override for resource-limit vectors */
    {
        const char *ms = getenv("UEM_MAX_STEPS");
        if (ms && *ms) {
            unsigned long v = strtoul(ms, NULL, 10);
            if (v > 0 && v < m->max_steps) m->max_steps = (uint32_t)v;
        }
    }
    if (m->halted) {
        uem_ev_append(m, "execution-after-stop");
        uem_set_state(m, "invalid");
        if (err) snprintf(err, errlen, "execution-after-stop");
        return -1;
    }
    if (m->steps >= m->max_steps) {
        m->halted = 1;
        snprintf(m->stop_reason, sizeof m->stop_reason, "limit:steps");
        uem_set_state(m, "invalid");
        uem_ev_append(m, "limit:steps");
        return -1;
    }
    if (m->pc >= m->n_instr) {
        if (err) snprintf(err, errlen, "pc-out-of-range");
        return -1;
    }
    in = &m->instr[m->pc];
    m->pc++;
    m->steps++;
    op = in->opcode;
    operand = in->operand;
    {
        static const char *OPN[] = {
            "?", "LOAD", "READ", "WRITE", "DELETE", "EMIT", "ENQUEUE", "DEQUEUE",
            "ROUTE", "APPLY", "MAP", "FOLD", "VERIFY", "TICKET", "OUTWARD", "ACK", "STOP"
        };
        const char *on = (op >= 1 && op <= 16) ? OPN[op] : "?";
        if (operand) snprintf(emark, sizeof emark, "op:%s:%s", on, operand);
        else snprintf(emark, sizeof emark, "op:%s", on);
    }

    switch (op) {
    case 0x01: /* LOAD */
        if (operand && strcmp(operand, "host_input") == 0) {
            if (m->acc) cJSON_Delete(m->acc);
            m->acc = m->host ? cJSON_Duplicate(m->host, 1) : cJSON_CreateNull();
            if (m->host) {
                if (cJSON_GetObjectItem(m->store, "host"))
                    cJSON_ReplaceItemInObject(m->store, "host", cJSON_Duplicate(m->host, 1));
                else
                    cJSON_AddItemToObject(m->store, "host", cJSON_Duplicate(m->host, 1));
            }
        } else if (operand && strncmp(operand, "image:", 6) == 0) {
            cJSON *v = cJSON_GetObjectItemCaseSensitive(m->image, operand + 6);
            if (m->acc) cJSON_Delete(m->acc);
            m->acc = v ? cJSON_Duplicate(v, 1) : cJSON_CreateNull();
        }
        break;
    case 0x02: /* READ path into _acc */
        if (operand) {
            cJSON *v = cJSON_GetObjectItemCaseSensitive(m->store, operand);
            if (m->acc) cJSON_Delete(m->acc);
            m->acc = v ? cJSON_Duplicate(v, 1) : cJSON_CreateNull();
        }
        break;
    case 0x03: /* WRITE _acc into path */
        if (operand) {
            cJSON *v = m->acc ? cJSON_Duplicate(m->acc, 1) : cJSON_CreateNull();
            if (cJSON_GetObjectItemCaseSensitive(m->store, operand))
                cJSON_ReplaceItemInObjectCaseSensitive(m->store, operand, v);
            else
                cJSON_AddItemToObject(m->store, operand, v);
        }
        break;
    case 0x04: /* DELETE */
        if (operand) cJSON_DeleteItemFromObjectCaseSensitive(m->store, operand);
        break;
    case 0x05: { /* EMIT */
        char id[17];
        const char *name = operand ? operand : "event";
        free(m->event_name);
        m->event_name = strdup(name);
        event_id_make(m, name, id);
        free(m->event_id);
        m->event_id = strdup(id);
        m->event_seq++;
        m->event_count++;
        if (!m->events_emitted) m->events_emitted = cJSON_CreateArray();
        cJSON_AddItemToArray(m->events_emitted, cJSON_CreateString(name));
        {
            char mk[128];
            snprintf(mk, sizeof mk, "event:%s", name);
            uem_ev_append(m, mk);
        }
        break;
    }
    case 0x06: { /* ENQUEUE */
        const char *name = operand ? operand : (m->event_name ? m->event_name : "event");
        char id[17];
        if (m->q_len + 1 > m->q_cap) {
            size_t ncap = m->q_cap ? m->q_cap * 2 : 16;
            char **nn = (char **)realloc(m->q_name, ncap * sizeof(char *));
            char **ni = (char **)realloc(m->q_id, ncap * sizeof(char *));
            if (!nn || !ni) return -1;
            m->q_name = nn; m->q_id = ni; m->q_cap = ncap;
        }
        if (m->event_id) snprintf(id, sizeof id, "%s", m->event_id);
        else event_id_make(m, name, id);
        m->q_name[m->q_len] = strdup(name);
        m->q_id[m->q_len] = strdup(id);
        m->q_len++;
        m->event_seq++;
        {
            char mk[128];
            snprintf(mk, sizeof mk, "event:enqueue:%s", name);
            uem_ev_append(m, mk);
        }
        break;
    }
    case 0x07: /* DEQUEUE */
        if (m->q_len == 0) {
            free(m->event_name); m->event_name = strdup("quiet");
            free(m->event_id); m->event_id = strdup("quiet");
            uem_ev_append(m, "event:quiet");
        } else {
            free(m->event_name); m->event_name = m->q_name[0];
            free(m->event_id); m->event_id = m->q_id[0];
            memmove(m->q_name, m->q_name + 1, (m->q_len - 1) * sizeof(char *));
            memmove(m->q_id, m->q_id + 1, (m->q_len - 1) * sizeof(char *));
            m->q_len--;
            if (!m->events_dequeued) m->events_dequeued = cJSON_CreateArray();
            cJSON_AddItemToArray(m->events_dequeued, cJSON_CreateString(m->event_name));
            {
                char mk[128];
                snprintf(mk, sizeof mk, "event:dequeue:%s", m->event_name);
                uem_ev_append(m, mk);
            }
        }
        break;
    case 0x08: /* ROUTE */
        /* routes from image */
        {
            cJSON *routes = cJSON_GetObjectItemCaseSensitive(m->image, "routes");
            cJSON *p = NULL;
            if (m->event_name && cJSON_IsObject(routes))
                p = cJSON_GetObjectItemCaseSensitive(routes, m->event_name);
            free(m->pending_primitive);
            m->pending_primitive = NULL;
            if (!cJSON_IsString(p)) {
                uem_set_state(m, "invalid");
                uem_ev_append(m, "event:unknown");
            } else {
                m->pending_primitive = strdup(p->valuestring);
            }
        }
        break;
    case 0x09: { /* APPLY */
        const char *name = operand ? operand : m->pending_primitive;
        char e2[64];
        if (!name) {
            uem_set_state(m, "invalid");
            uem_ev_append(m, "apply:missing-primitive");
            break;
        }
        if (uem_prim_apply(m, name, e2, sizeof e2) != 0) {
            /* soft invalid continues unless fatal */
        }
        free(m->pending_primitive);
        m->pending_primitive = NULL;
        break;
    }
    case 0x0A: /* MAP */
    case 0x0B: /* FOLD — stub audited sites for v0.1 linear programs */
        uem_ev_append(m, op == 0x0A ? "map:complete" : "fold:complete");
        break;
    case 0x0C: /* VERIFY */
        uem_prim_apply(m, "verify_result", err, errlen);
        break;
    case 0x0D: /* TICKET */
        uem_ticket_construct(m);
        break;
    case 0x0E: { /* OUTWARD — request only; host fulfills between steps */
        const char *effect = operand ? operand : "effect";
        cJSON *b = cJSON_GetObjectItemCaseSensitive(m->image, "boundary");
        cJSON *req = cJSON_CreateObject();
        const char *sf = "source";
        cJSON *src;
        char mk[128];
        if (b) {
            cJSON *s = cJSON_GetObjectItemCaseSensitive(b, "source_field");
            if (cJSON_IsString(s)) sf = s->valuestring;
        }
        src = cJSON_GetObjectItemCaseSensitive(m->store, sf);
        cJSON_AddStringToObject(req, "effect", effect);
        if (src) cJSON_AddItemToObject(req, "source", cJSON_Duplicate(src, 1));
        if (m->outward_request) cJSON_Delete(m->outward_request);
        m->outward_request = req;
        /* clear prior result so host must supply */
        if (m->outward_result) { cJSON_Delete(m->outward_result); m->outward_result = NULL; }
        snprintf(mk, sizeof mk, "outward:request:%s", effect);
        uem_ev_append(m, mk);
        break;
    }
    case 0x0F: /* ACK */
        if (m->ticket) {
            cJSON *ext = cJSON_GetObjectItemCaseSensitive(m->ticket, "external_id");
            if (cJSON_IsString(ext) && ext->valuestring[0]) {
                cJSON_ReplaceItemInObject(m->ticket, "acked", cJSON_CreateTrue());
                uem_ev_append(m, "event:ticket.acked");
            } else {
                uem_ev_append(m, "event:ticket.ack_pending");
            }
        }
        break;
    case 0x10: /* STOP */
        m->halted = 1;
        snprintf(m->stop_reason, sizeof m->stop_reason, "%s", operand ? operand : "stop");
        uem_ev_append(m, "op:STOP");
        break;
    default:
        uem_set_state(m, "invalid");
        if (err) snprintf(err, errlen, "unknown-opcode");
        return -1;
    }
    uem_ev_append(m, emark);
    return 0;
}

static void fulfill_outward(uem_machine *m) {
    cJSON *req, *src;
    const char *effect;
    char resbuf[UEM_MAX_OUT];
    char ebuf[256];
    char *srcjson;
    int rc;
    if (!m || !m->outward_request || m->outward_result || !m->outward) return;
    req = m->outward_request;
    effect = cJSON_GetObjectItemCaseSensitive(req, "effect")
                 ? cJSON_GetObjectItemCaseSensitive(req, "effect")->valuestring
                 : "effect";
    src = cJSON_GetObjectItemCaseSensitive(req, "source");
    srcjson = src ? cJSON_PrintUnformatted(src) : strdup("null");
    ebuf[0] = 0;
    rc = m->outward(m->outward_ctx, effect, srcjson, resbuf, sizeof resbuf, ebuf, sizeof ebuf);
    free(srcjson);
    {
        cJSON *ent = cJSON_CreateObject();
        cJSON_AddStringToObject(ent, "effect", effect);
        if (src) cJSON_AddItemToObject(ent, "source", cJSON_Duplicate(src, 1));
        if (!m->outward_log) m->outward_log = cJSON_CreateArray();
        cJSON_AddItemToArray(m->outward_log, ent);
    }
    if (rc == 0) {
        if (m->outward_result) cJSON_Delete(m->outward_result);
        m->outward_result = cJSON_Parse(resbuf);
        uem_ev_append(m, "host:fulfill");
    } else {
        cJSON *rj = cJSON_CreateObject();
        cJSON_AddStringToObject(rj, "error", ebuf[0] ? ebuf : "outward-fail");
        if (m->outward_result) cJSON_Delete(m->outward_result);
        m->outward_result = rj;
        uem_ev_append(m, "host:fulfill");
    }
}

uem_status uem_run(uem_machine *m, char *err, size_t errlen) {
    if (!m) return UEM_ERR_ARGS;
    while (!m->halted && m->pc < m->n_instr) {
        if (step_one(m, err, errlen) != 0) {
            if (m->halted) return UEM_OK;
        }
        /* After OUTWARD, fulfill before next instruction (Python host order). */
        if (m->outward_request && !m->outward_result)
            fulfill_outward(m);
    }
    if (!m->halted) {
        m->halted = 1;
        snprintf(m->stop_reason, sizeof m->stop_reason, "stop");
    }
    return UEM_OK;
}

char *uem_result_json(const uem_machine *m) {
    cJSON *root;
    cJSON *ev;
    size_t i;
    char *s;
    const char *limit_hit = NULL;
    if (!m) return NULL;
    root = cJSON_CreateObject();
    /* L11 canonical fields (Python host normalizes identically) */
    cJSON_AddNumberToObject(root, "canonical_version", 1);
    cJSON_AddNumberToObject(root, "registry_version", UEM_REGISTRY_VERSION);
    cJSON_AddStringToObject(root, "unicode_profile", "UEM-ASCII-1");
    cJSON_AddStringToObject(root, "state", m->state);
    cJSON_AddStringToObject(root, "stop_reason", m->stop_reason[0] ? m->stop_reason : "stop");
    cJSON_AddStringToObject(root, "program_sha256", m->program_sha256);
    cJSON_AddNumberToObject(root, "steps", m->steps);
    cJSON_AddNumberToObject(root, "instruction_count", m->n_instr);
    if (strncmp(m->stop_reason, "limit:", 6) == 0) limit_hit = m->stop_reason + 6;
    if (limit_hit) cJSON_AddStringToObject(root, "limit_hit", limit_hit);
    else cJSON_AddNullToObject(root, "limit_hit");
    if (m->presentation)
        cJSON_AddItemToObject(root, "presentation", cJSON_Duplicate(m->presentation, 1));
    else cJSON_AddNullToObject(root, "presentation");
    {
        cJSON *st = cJSON_GetObjectItemCaseSensitive(m->store, "stats");
        if (st) cJSON_AddItemToObject(root, "stats", cJSON_Duplicate(st, 1));
        else cJSON_AddNullToObject(root, "stats");
    }
    {
        cJSON *er = cJSON_GetObjectItemCaseSensitive(m->store, "error");
        if (er) cJSON_AddItemToObject(root, "error", cJSON_Duplicate(er, 1));
        else cJSON_AddNullToObject(root, "error");
    }
    {
        cJSON *path = cJSON_GetObjectItemCaseSensitive(m->store, "path");
        if (path) cJSON_AddItemToObject(root, "path", cJSON_Duplicate(path, 1));
        else cJSON_AddNullToObject(root, "path");
    }
    if (m->ticket) cJSON_AddItemToObject(root, "ticket", cJSON_Duplicate(m->ticket, 1));
    else cJSON_AddNullToObject(root, "ticket");
    cJSON_AddItemToObject(root, "outward_log",
        m->outward_log ? cJSON_Duplicate(m->outward_log, 1) : cJSON_CreateArray());
    cJSON_AddItemToObject(root, "events_emitted",
        m->events_emitted ? cJSON_Duplicate(m->events_emitted, 1) : cJSON_CreateArray());
    cJSON_AddItemToObject(root, "events_dequeued",
        m->events_dequeued ? cJSON_Duplicate(m->events_dequeued, 1) : cJSON_CreateArray());
    cJSON_AddNullToObject(root, "reject");
    ev = cJSON_CreateArray();
    for (i = 0; i < m->n_evidence; i++) cJSON_AddItemToArray(ev, cJSON_CreateString(m->evidence[i]));
    cJSON_AddItemToObject(root, "evidence", ev);
    s = cJSON_PrintUnformatted(root);
    cJSON_Delete(root);
    return s;
}

const char *uem_state(const uem_machine *m) { return m ? m->state : NULL; }
const char *uem_stop_reason(const uem_machine *m) { return m ? m->stop_reason : NULL; }
const char *uem_program_sha256(const uem_machine *m) { return m ? m->program_sha256 : NULL; }
uint32_t uem_instruction_count(const uem_machine *m) { return m ? m->n_instr : 0; }
uint32_t uem_step_count(const uem_machine *m) { return m ? m->steps : 0; }

/* file host */
int uem_default_outward(void *ctx, const char *effect, const char *source_json,
                        char *result_json, size_t result_cap, char *err, size_t errlen) {
    cJSON *src = cJSON_Parse(source_json);
    const char *path = NULL;
    FILE *f;
    char *buf = NULL;
    long sz;
    (void)ctx;
    if (cJSON_IsString(src)) path = src->valuestring;
    else if (src && cJSON_IsString(cJSON_GetObjectItem(src, "source")))
        path = cJSON_GetObjectItem(src, "source")->valuestring;
    /* host inject handled by require_source+host fields before outward; if text/document in machine host, fulfill from there via effect handlers in CLI */
    if (!path) {
        cJSON_Delete(src);
        snprintf(err, errlen, "missing-source");
        snprintf(result_json, result_cap, "{\"error\":\"missing-source\"}");
        return -1;
    }
    if (strcmp(path, "-") == 0) {
        cJSON_Delete(src);
        snprintf(err, errlen, "stdin-not-provided");
        snprintf(result_json, result_cap, "{\"error\":\"stdin-not-provided\"}");
        return -1;
    }
    f = fopen(path, "rb");
    if (!f) {
        cJSON_Delete(src);
        snprintf(result_json, result_cap, "{\"error\":\"missing-file\"}");
        return 0;
    }
    if (fseek(f, 0, SEEK_END) != 0) { fclose(f); cJSON_Delete(src); return -1; }
    sz = ftell(f);
    if (sz < 0 || sz > (long)UEM_MAX_OUT) { fclose(f); cJSON_Delete(src); snprintf(err, errlen, "too-large"); return -1; }
    rewind(f);
    buf = (char *)malloc((size_t)sz + 1);
    if (!buf) { fclose(f); cJSON_Delete(src); return -1; }
    if (fread(buf, 1, (size_t)sz, f) != (size_t)sz) { free(buf); fclose(f); cJSON_Delete(src); return -1; }
    buf[sz] = 0;
    fclose(f);
    cJSON_Delete(src);
    if (strcmp(effect, "read_utf8") == 0) {
        /* validate utf-8 lightly: cJSON string escape */
        cJSON *wrap = cJSON_CreateObject();
        cJSON_AddStringToObject(wrap, "data", buf);
        {
            char *p = cJSON_PrintUnformatted(wrap);
            snprintf(result_json, result_cap, "%s", p);
            free(p);
        }
        cJSON_Delete(wrap);
        free(buf);
        return 0;
    }
    if (strcmp(effect, "read_json") == 0) {
        cJSON *doc = cJSON_Parse(buf);
        free(buf);
        if (!doc || !cJSON_IsObject(doc)) {
            if (doc) cJSON_Delete(doc);
            snprintf(result_json, result_cap, "{\"error\":\"invalid-json\"}");
            return 0;
        }
        {
            cJSON *wrap = cJSON_CreateObject();
            cJSON_AddItemToObject(wrap, "data", doc);
            {
                char *p = cJSON_PrintUnformatted(wrap);
                snprintf(result_json, result_cap, "%s", p);
                free(p);
            }
            cJSON_Delete(wrap);
        }
        return 0;
    }
    free(buf);
    snprintf(result_json, result_cap, "{\"error\":\"unknown-effect\"}");
    return 0;
}
