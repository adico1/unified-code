#include "alloc.h"
#include "machine_internal.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static const char *REGISTRY[] = {
    "identity", "letter", "mark_inward", "require_source", "accept_outward",
    "eval_expression", "merge_result", "verify_result", "present_json", "mark_part",
    "state_transition",
    NULL
};

int uem_registry_has(const char *name) {
    int i;
    if (!name) return 0;
    for (i = 0; REGISTRY[i]; i++) if (strcmp(REGISTRY[i], name) == 0) return 1;
    return 0;
}

static int store_set(uem_machine *m, const char *k, cJSON *v) {
    if (cJSON_GetObjectItemCaseSensitive(m->store, k))
        cJSON_ReplaceItemInObjectCaseSensitive(m->store, k, v);
    else
        cJSON_AddItemToObject(m->store, k, v);
    return 0;
}

static cJSON *store_get(uem_machine *m, const char *k) {
    return cJSON_GetObjectItemCaseSensitive(m->store, k);
}

static int prim_identity(uem_machine *m) {
    return uem_ev_append(m, "primitive:identity");
}

static int prim_mark_inward(uem_machine *m) {
    return uem_ev_append(m, "boundary:inward");
}

static int prim_letter(uem_machine *m) {
    if (strcmp(m->state, "invalid") == 0 || strcmp(m->state, "absent") == 0 ||
        strcmp(m->state, "false") == 0)
        return uem_ev_append(m, "letter:skipped");
    return uem_ev_append(m, "letter:distinguished");
}

static int prim_require_source(uem_machine *m) {
    cJSON *src_cfg = cJSON_GetObjectItemCaseSensitive(m->image, "source");
    const char *field = "source";
    const char *err_missing = "missing-source";
    const char *err_extra = "extra-source";
    cJSON *f, *e;
    if (src_cfg) {
        f = cJSON_GetObjectItemCaseSensitive(src_cfg, "field");
        if (cJSON_IsString(f)) field = f->valuestring;
        e = cJSON_GetObjectItemCaseSensitive(src_cfg, "missing");
        if (cJSON_IsString(e)) err_missing = e->valuestring;
        e = cJSON_GetObjectItemCaseSensitive(src_cfg, "extra");
        if (cJSON_IsString(e)) err_extra = e->valuestring;
    }
    if (!m->host) {
        store_set(m, "error", cJSON_CreateString(err_missing));
        uem_set_state(m, "invalid");
        return uem_ev_append(m, "source:missing");
    }
    {
        cJSON *tx = cJSON_GetObjectItemCaseSensitive(m->host, "text");
        if (tx && cJSON_IsString(tx)) {
            cJSON *sf = cJSON_GetObjectItemCaseSensitive(m->host, field);
            const char *sv = "-";
            if (sf) {
                if (cJSON_IsString(sf)) sv = sf->valuestring;
            }
            store_set(m, field, cJSON_CreateString(sv));
            return uem_ev_append(m, "source:ok");
        }
    }
    {
        cJSON *doc = cJSON_GetObjectItemCaseSensitive(m->host, "document");
        if (doc && cJSON_IsObject(doc)) {
            cJSON *sf = cJSON_GetObjectItemCaseSensitive(m->host, field);
            const char *sv = "-";
            if (sf) {
                if (cJSON_IsString(sf)) sv = sf->valuestring;
            }
            store_set(m, field, cJSON_CreateString(sv));
            return uem_ev_append(m, "source:ok");
        }
    }
    {
        cJSON *sf = cJSON_GetObjectItemCaseSensitive(m->host, field);
        if (sf) {
            if (!cJSON_IsNull(sf)) {
                store_set(m, field, cJSON_Duplicate(sf, 1));
                return uem_ev_append(m, "source:ok");
            }
        }
    }
    {
        cJSON *argv = cJSON_GetObjectItemCaseSensitive(m->host, "argv");
        if (cJSON_IsArray(argv)) {
            int n = cJSON_GetArraySize(argv);
            if (n == 0) {
                store_set(m, "error", cJSON_CreateString(err_missing));
                uem_set_state(m, "invalid");
                return uem_ev_append(m, "source:missing");
            }
            if (n > 1) {
                store_set(m, "error", cJSON_CreateString(err_extra));
                uem_set_state(m, "invalid");
                return uem_ev_append(m, "source:extra");
            }
            store_set(m, field, cJSON_Duplicate(cJSON_GetArrayItem(argv, 0), 1));
            return uem_ev_append(m, "source:ok");
        }
    }
    store_set(m, "error", cJSON_CreateString(err_missing));
    uem_set_state(m, "invalid");
    return uem_ev_append(m, "source:missing");
}

static int prim_accept_outward(uem_machine *m) {
    cJSON *b = cJSON_GetObjectItemCaseSensitive(m->image, "boundary");
    const char *bname = "boundary";
    const char *target = "payload";
    cJSON *res = m->outward_result;
    char mark[128];
    if (b) {
        cJSON *n = cJSON_GetObjectItemCaseSensitive(b, "name");
        cJSON *t = cJSON_GetObjectItemCaseSensitive(b, "target_field");
        if (cJSON_IsString(n)) bname = n->valuestring;
        if (cJSON_IsString(t)) target = t->valuestring;
    }
    if (!res) {
        store_set(m, "error", cJSON_CreateString("outward-missing-result"));
        uem_set_state(m, "invalid");
        return uem_ev_append(m, "outward:missing");
    }
    if (cJSON_GetObjectItemCaseSensitive(res, "error")) {
        cJSON *er = cJSON_GetObjectItemCaseSensitive(res, "error");
        char errtxt[128];
        /* cJSON string nodes always have non-NULL valuestring (possibly empty). */
        if (cJSON_IsString(er))
            snprintf(errtxt, sizeof errtxt, "%s", er->valuestring);
        else
            snprintf(errtxt, sizeof errtxt, "%s", "error");
        store_set(m, "error", cJSON_Duplicate(er, 1));
        if (cJSON_GetObjectItemCaseSensitive(res, "path"))
            store_set(m, "path", cJSON_Duplicate(cJSON_GetObjectItemCaseSensitive(res, "path"), 1));
        cJSON_Delete(m->outward_result);
        m->outward_result = NULL;
        res = NULL;
        uem_set_state(m, "invalid");
        snprintf(mark, sizeof mark, "boundary:%s", bname);
        uem_ev_append(m, mark);
        snprintf(mark, sizeof mark, "read:error:%s", errtxt);
        return uem_ev_append(m, mark);
    }
    {
        cJSON *data = cJSON_GetObjectItemCaseSensitive(res, "data");
        store_set(m, target, data ? cJSON_Duplicate(data, 1) : cJSON_Duplicate(res, 1));
    }
    cJSON_Delete(m->outward_result);
    m->outward_result = NULL;
    cJSON_Delete(m->outward_request);
    m->outward_request = NULL;
    snprintf(mark, sizeof mark, "boundary:%s", bname);
    uem_ev_append(m, mark);
    return uem_ev_append(m, "read:ok");
}

static int prim_eval_expression(uem_machine *m) {
    cJSON *expr, *bindings_ast, *order, *root = NULL;
    cJSON *bound = cJSON_CreateObject();
    cJSON *result = NULL;
    char err[128];
    const char *part = "part";
    const char *input_key = "document";
    cJSON *ik, *pn;
    char mark[128];
    if (strcmp(m->state, "invalid") == 0 || strcmp(m->state, "absent") == 0 ||
        strcmp(m->state, "false") == 0 || strcmp(m->state, "unknown") == 0) {
        cJSON_Delete(bound);
        return uem_ev_append(m, "eval:skipped");
    }
    if (store_get(m, "error")) {
        cJSON_Delete(bound);
        return uem_ev_append(m, "eval:prior-error");
    }
    ik = cJSON_GetObjectItemCaseSensitive(m->image, "input_key");
    if (cJSON_IsString(ik)) input_key = ik->valuestring;
    pn = cJSON_GetObjectItemCaseSensitive(m->image, "part_name");
    if (cJSON_IsString(pn)) part = pn->valuestring;
    expr = cJSON_GetObjectItemCaseSensitive(m->image, "expression");
    bindings_ast = cJSON_GetObjectItemCaseSensitive(m->image, "bindings");
    order = cJSON_GetObjectItemCaseSensitive(m->image, "binding_order");
    if (!expr) {
        store_set(m, "error", cJSON_CreateString("missing-expression"));
        uem_set_state(m, "invalid");
        cJSON_Delete(bound);
        return uem_ev_append(m, "eval:missing-expression");
    }
    if (strcmp(input_key, "text") == 0) {
        cJSON *t = store_get(m, "text");
        if (!cJSON_IsString(t)) {
            store_set(m, "error", cJSON_CreateString("missing-text"));
            uem_set_state(m, "absent");
            cJSON_Delete(bound);
            snprintf(mark, sizeof mark, "part:%s", part);
            uem_ev_append(m, mark);
            snprintf(mark, sizeof mark, "%s:missing-input", part);
            return uem_ev_append(m, mark);
        }
        root = cJSON_CreateObject();
        cJSON_AddItemToObject(root, "text", cJSON_Duplicate(t, 1));
    } else if (strcmp(input_key, "document") == 0) {
        cJSON *d = store_get(m, "document");
        if (!d) {
            store_set(m, "error", cJSON_CreateString("missing-document"));
            uem_set_state(m, "absent");
            cJSON_Delete(bound);
            snprintf(mark, sizeof mark, "part:%s", part);
            uem_ev_append(m, mark);
            snprintf(mark, sizeof mark, "%s:missing-input", part);
            return uem_ev_append(m, mark);
        }
        if (!cJSON_IsObject(d)) {
            store_set(m, "error", cJSON_CreateString("input-not-an-object"));
            uem_set_state(m, "invalid");
            cJSON_Delete(bound);
            return -1;
        }
        root = cJSON_Duplicate(d, 1);
    } else {
        root = cJSON_Duplicate(m->store, 1);
    }
    /* bindings in binding_order only (canonical CSE sequence from compile).
     * Never iterate bindings object key order — image JSON uses sort_keys. */
    if (cJSON_IsArray(order)) {
        if (cJSON_IsObject(bindings_ast)) {
            cJSON *nm;
            for (nm = order->child; nm != NULL; nm = nm->next) {
                cJSON *node, *val = NULL;
                cJSON *bpath = NULL;
                if (!cJSON_IsString(nm)) continue;
                node = cJSON_GetObjectItemCaseSensitive(bindings_ast, nm->valuestring);
                if (!node) continue;
                if (uem_expr_eval(m, node, root, bound, &val, err, sizeof err, &bpath) != 0) {
                    store_set(m, "error", cJSON_CreateString(err));
                    if (bpath) store_set(m, "path", bpath);
                    uem_set_state(m, "invalid");
                    cJSON_Delete(root);
                    cJSON_Delete(bound);
                    snprintf(mark, sizeof mark, "part:%s", part);
                    uem_ev_append(m, mark);
                    snprintf(mark, sizeof mark, "%s:error:%s", part, err);
                    return uem_ev_append(m, mark);
                }
                /* eval success always yields a value pointer (possibly JSON null). */
                cJSON_AddItemToObject(bound, nm->valuestring, val);
            }
        }
    }
    cJSON *err_path = NULL;
    if (uem_expr_eval(m, expr, root, bound, &result, err, sizeof err, &err_path) != 0) {
        store_set(m, "error", cJSON_CreateString(err));
        if (err_path) {
            store_set(m, "path", err_path);
            err_path = NULL;
        }
        uem_set_state(m, "invalid");
        cJSON_Delete(root);
        cJSON_Delete(bound);
        snprintf(mark, sizeof mark, "part:%s", part);
        uem_ev_append(m, mark);
        snprintf(mark, sizeof mark, "%s:error:%s", part, err);
        return uem_ev_append(m, mark);
    }
    cJSON_Delete(root);
    cJSON_Delete(bound);
    if (m->acc) cJSON_Delete(m->acc);
    m->acc = result;
    snprintf(mark, sizeof mark, "part:%s", part);
    uem_ev_append(m, mark);
    snprintf(mark, sizeof mark, "%s:ok", part);
    return uem_ev_append(m, mark);
}

static int prim_merge_result(uem_machine *m) {
    cJSON *mk = cJSON_GetObjectItemCaseSensitive(m->image, "merge_key");
    const char *key = cJSON_IsString(mk) ? mk->valuestring : "result";
    if (strcmp(m->state, "invalid") == 0 || strcmp(m->state, "absent") == 0 ||
        strcmp(m->state, "false") == 0)
        return uem_ev_append(m, "merge:skipped");
    if (m->acc) store_set(m, key, cJSON_Duplicate(m->acc, 1));
    return uem_ev_append(m, "merge:ok");
}

static int prim_verify_result(uem_machine *m) {
    cJSON *vcfg = cJSON_GetObjectItemCaseSensitive(m->image, "verify");
    cJSON *field = vcfg ? cJSON_GetObjectItemCaseSensitive(vcfg, "require_value_field") : NULL;
    cJSON *req = vcfg ? cJSON_GetObjectItemCaseSensitive(vcfg, "require_evidence_contains") : NULL;
    int ok = 1;
    if (strcmp(m->state, "invalid") == 0 || strcmp(m->state, "absent") == 0 ||
        strcmp(m->state, "false") == 0) {
        uem_set_state(m, "invalid");
        return uem_ev_append(m, "script-law:fail");
    }
    if (store_get(m, "error")) {
        uem_set_state(m, "invalid");
        return uem_ev_append(m, "script-law:fail");
    }
    if (cJSON_IsString(field) && !store_get(m, field->valuestring)) {
        uem_set_state(m, "invalid");
        return uem_ev_append(m, "script-law:fail");
    }
    if (cJSON_IsArray(req)) {
        cJSON *el;
        for (el = req->child; el != NULL; el = el->next) {
            size_t i;
            int found = 0;
            if (!cJSON_IsString(el)) continue;
            for (i = 0; i < m->n_evidence; i++) {
                if (strcmp(m->evidence[i], el->valuestring) == 0) { found = 1; break; }
            }
            if (!found) ok = 0;
        }
    }
    if (!ok) {
        uem_set_state(m, "invalid");
        return uem_ev_append(m, "script-law:fail");
    }
    uem_set_state(m, "valid");
    return uem_ev_append(m, "script-law:pass");
}

static int prim_present_json(uem_machine *m) {
    cJSON *pcfg = cJSON_GetObjectItemCaseSensitive(m->image, "presentation");
    cJSON *keys = pcfg ? cJSON_GetObjectItemCaseSensitive(pcfg, "success_keys") : NULL;
    cJSON *sf = pcfg ? cJSON_GetObjectItemCaseSensitive(pcfg, "success_from") : NULL;
    cJSON *inc = pcfg ? cJSON_GetObjectItemCaseSensitive(pcfg, "include_error_path") : NULL;
    const char *success_from = cJSON_IsString(sf) ? sf->valuestring : "result";
    cJSON *pres = cJSON_CreateObject();
    char *text = NULL;
    int exit_code = 1;
    if (strcmp(m->state, "valid") == 0) {
        if (cJSON_IsArray(keys)) {
            cJSON *src = store_get(m, success_from);
            cJSON *obj = cJSON_CreateObject();
            cJSON *k;
            if (cJSON_IsObject(src)) {
                for (k = keys->child; k != NULL; k = k->next) {
                    cJSON *v;
                    if (!cJSON_IsString(k)) continue;
                    v = cJSON_GetObjectItemCaseSensitive(src, k->valuestring);
                    if (v) cJSON_AddItemToObject(obj, k->valuestring, cJSON_Duplicate(v, 1));
                }
                text = cJSON_PrintUnformatted(obj);
                exit_code = 0;
            }
            cJSON_Delete(obj);
        }
    }
    if (!text) {
        cJSON *body = cJSON_CreateObject();
        cJSON *er = store_get(m, "error");
        int include_path = 0;
        if (cJSON_IsString(er))
            cJSON_AddStringToObject(body, "error", er->valuestring);
        else
            cJSON_AddStringToObject(body, "error", "invalid");
        if (cJSON_IsTrue(inc)) include_path = 1;
        if (cJSON_IsNumber(inc) && inc->valueint) include_path = 1;
        if (inc && (inc->type & cJSON_True)) include_path = 1;
        if (include_path) {
            cJSON *path = store_get(m, "path");
            if (path) cJSON_AddItemToObject(body, "path", cJSON_Duplicate(path, 1));
        }
        text = cJSON_PrintUnformatted(body);
        cJSON_Delete(body);
        exit_code = 1;
    }
    /* text is set by success Print or error-body Print under normal memory. */
    cJSON_AddStringToObject(pres, "text", text ? text : "{}");
    cJSON_AddNumberToObject(pres, "exit_code", exit_code);
    uem_mem_free(text);
    store_set(m, "presentation", cJSON_Duplicate(pres, 1));
    if (m->presentation) cJSON_Delete(m->presentation);
    m->presentation = pres;
    return uem_ev_append(m, "present_result:ok");
}

static int prim_mark_part(uem_machine *m) {
    cJSON *pn = cJSON_GetObjectItemCaseSensitive(m->image, "part_name");
    char mark[128];
    snprintf(mark, sizeof mark, "part:%s", cJSON_IsString(pn) ? pn->valuestring : "part");
    return uem_ev_append(m, mark);
}

int uem_prim_apply(uem_machine *m, const char *name, char *err, size_t errlen) {
    if (!uem_registry_has(name)) {
        if (err) snprintf(err, errlen, "unknown-primitive");
        store_set(m, "error", cJSON_CreateString("unknown-primitive"));
        uem_set_state(m, "invalid");
        uem_ev_append(m, "primitive:unknown");
        return -1;
    }
    if (strcmp(name, "identity") == 0) return prim_identity(m);
    if (strcmp(name, "letter") == 0) return prim_letter(m);
    if (strcmp(name, "mark_inward") == 0) return prim_mark_inward(m);
    if (strcmp(name, "require_source") == 0) return prim_require_source(m);
    if (strcmp(name, "accept_outward") == 0) return prim_accept_outward(m);
    if (strcmp(name, "eval_expression") == 0) return prim_eval_expression(m);
    if (strcmp(name, "merge_result") == 0) return prim_merge_result(m);
    if (strcmp(name, "verify_result") == 0) return prim_verify_result(m);
    if (strcmp(name, "present_json") == 0) return prim_present_json(m);
    if (strcmp(name, "state_transition") == 0) return uem_stateful_transition(m);
    /* mark_part is last registry entry — always matches if uem_registry_has passed. */
    return prim_mark_part(m);
}

void uem_ticket_construct(uem_machine *m) {
    /* pure ticket from machine_fault; redaction */
    cJSON *fault = m->machine_fault;
    cJSON *t = cJSON_CreateObject();
    const char *op = "machine";
    const char *et = "Fault";
    const char *msg = "unhandled";
    char red[512];
    char raw[1024];
    char cid[65];
    size_t i;
    if (fault) {
        cJSON *o = cJSON_GetObjectItemCaseSensitive(fault, "operation");
        cJSON *e = cJSON_GetObjectItemCaseSensitive(fault, "error_type");
        cJSON *ms = cJSON_GetObjectItemCaseSensitive(fault, "message");
        if (cJSON_IsString(o)) op = o->valuestring;
        if (cJSON_IsString(e)) et = e->valuestring;
        if (cJSON_IsString(ms)) msg = ms->valuestring;
    }
    {
        /* redact */
        char lower[512];
        size_t n = strlen(msg);
        if (n >= sizeof lower) n = sizeof lower - 1;
        memcpy(lower, msg, n);
        lower[n] = 0;
        for (i = 0; i < n; i++) if (lower[i] >= 'A' && lower[i] <= 'Z') lower[i] = (char)(lower[i] - 'A' + 'a');
        if (strstr(lower, "password") || strstr(lower, "token") || strstr(lower, "secret") ||
            strstr(lower, "authorization") || strstr(lower, "api_key") || strstr(lower, "apikey"))
            snprintf(red, sizeof red, "[redacted-message]");
        else {
            if (n > 500) n = 500;
            memcpy(red, msg, n);
            red[n] = 0;
        }
    }
    /* Ticket identity: failure material only (cross-host stable). */
    snprintf(raw, sizeof raw, "%s|%s|%s", op, et, red);
    {
        extern void uem_sha256_hex(const uint8_t *, size_t, char *);
        uem_sha256_hex((const uint8_t *)raw, strlen(raw), cid);
        cid[16] = 0;
    }
    cJSON_AddStringToObject(t, "kind", "unhandled-exception");
    cJSON_AddStringToObject(t, "operation", op);
    cJSON_AddStringToObject(t, "error_type", et);
    cJSON_AddStringToObject(t, "message", red);
    cJSON_AddStringToObject(t, "correlation_id", cid);
    cJSON_AddStringToObject(t, "ticket_id", cid);
    cJSON_AddStringToObject(t, "occurred_at", "static");
    cJSON_AddBoolToObject(t, "acked", 0);
    if (m->ticket) cJSON_Delete(m->ticket);
    m->ticket = t;
    uem_set_state(m, "invalid");
    uem_ev_append(m, "event:ticket.open");
    uem_ev_append(m, "event:ticket.construct");
}
