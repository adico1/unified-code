#include "alloc.h"
#include "machine_internal.h"
#include "decimal.h"
#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static cJSON *dig(cJSON *obj, cJSON *path_arr) {
    cJSON *cur = obj;
    cJSON *el;
    if (!path_arr || !cJSON_IsArray(path_arr)) return NULL;
    cJSON_ArrayForEach(el, path_arr) {
        if (!cur) return NULL;
        if (cJSON_IsNumber(el)) {
            int idx = el->valueint;
            if (!cJSON_IsArray(cur) || idx < 0 || idx >= cJSON_GetArraySize(cur)) return NULL;
            cur = cJSON_GetArrayItem(cur, idx);
        } else if (cJSON_IsString(el)) {
            if (!cJSON_IsObject(cur)) return NULL;
            cur = cJSON_GetObjectItemCaseSensitive(cur, el->valuestring);
        } else return NULL;
    }
    return cur;
}

static cJSON *g_err_path = NULL;
static int g_item_index = -1;
static cJSON *g_coll_path = NULL;

static int fail(char *err, size_t errlen, const char *msg) {
    if (err && errlen) snprintf(err, errlen, "%s", msg);
    return -1;
}

static int fail_path(char *err, size_t errlen, const char *msg, cJSON *path) {
    if (g_err_path) cJSON_Delete(g_err_path);
    if (g_item_index >= 0) {
        cJSON *full = cJSON_CreateArray();
        cJSON *el;
        if (g_coll_path && cJSON_IsArray(g_coll_path)) {
            cJSON_ArrayForEach(el, g_coll_path) cJSON_AddItemToArray(full, cJSON_Duplicate(el, 1));
        } else {
            cJSON_AddItemToArray(full, cJSON_CreateString("items"));
        }
        cJSON_AddItemToArray(full, cJSON_CreateNumber(g_item_index));
        if (path && cJSON_IsArray(path)) {
            cJSON_ArrayForEach(el, path) cJSON_AddItemToArray(full, cJSON_Duplicate(el, 1));
        }
        g_err_path = full;
    } else {
        g_err_path = path ? cJSON_Duplicate(path, 1) : NULL;
    }
    return fail(err, errlen, msg);
}

/* casefold ASCII only; non-ASCII copied */
static void casefold_copy(const char *in, char *out, size_t cap) {
    size_t i = 0, o = 0;
    while (in[i] && o + 1 < cap) {
        unsigned char c = (unsigned char)in[i];
        if (c < 0x80) {
            out[o++] = (char)tolower(c);
            i++;
        } else {
            /* copy UTF-8 sequence as-is */
            out[o++] = in[i++];
        }
    }
    out[o] = 0;
}

static int eval_node(cJSON *node, cJSON *root, cJSON *item, int in_each,
                     cJSON *bindings, cJSON **out, char *err, size_t errlen);

static int eval_node(cJSON *node, cJSON *root, cJSON *item, int in_each,
                     cJSON *bindings, cJSON **out, char *err, size_t errlen) {
    const char *op;
    cJSON *opj;
    if (!node || !cJSON_IsObject(node)) return fail(err, errlen, "bad-node");
    opj = cJSON_GetObjectItemCaseSensitive(node, "op");
    if (!cJSON_IsString(opj)) return fail(err, errlen, "bad-node");
    op = opj->valuestring;
    *out = NULL;

    if (strcmp(op, "literal") == 0) {
        cJSON *v = cJSON_GetObjectItemCaseSensitive(node, "value");
        *out = v ? cJSON_Duplicate(v, 1) : cJSON_CreateNull();
        return *out ? 0 : -1;
    }
    if (strcmp(op, "ref") == 0) {
        cJSON *nj = cJSON_GetObjectItemCaseSensitive(node, "name");
        cJSON *v;
        if (!cJSON_IsString(nj) || !bindings) return fail(err, errlen, "missing-binding");
        /* Missing key → missing-binding. Key present with JSON null → duplicate null.
         * cJSON_GetObjectItem returns non-NULL for null-typed items. */
        v = cJSON_GetObjectItemCaseSensitive(bindings, nj->valuestring);
        if (!v) return fail(err, errlen, "missing-binding");
        *out = cJSON_Duplicate(v, 1);
        return *out ? 0 : -1;
    }
    if (strcmp(op, "field") == 0) {
        cJSON *path = cJSON_GetObjectItemCaseSensitive(node, "path");
        cJSON *got = NULL;
        if (path && cJSON_IsArray(path) && cJSON_GetArraySize(path) > 0) {
            cJSON *first = cJSON_GetArrayItem(path, 0);
            if (cJSON_IsString(first) && strcmp(first->valuestring, "item") == 0) {
                /* path item.* */
                cJSON *rest = cJSON_CreateArray();
                int i, n = cJSON_GetArraySize(path);
                for (i = 1; i < n; i++) cJSON_AddItemToArray(rest, cJSON_Duplicate(cJSON_GetArrayItem(path, i), 1));
                got = dig(item, rest);
                cJSON_Delete(rest);
            } else if (in_each && item) {
                got = dig(item, path);
                if (!got) got = dig(root, path);
            } else {
                got = dig(root, path);
            }
        }
        *out = got ? cJSON_Duplicate(got, 1) : cJSON_CreateNull();
        return 0;
    }
    if (strcmp(op, "object") == 0) {
        cJSON *fields = cJSON_GetObjectItemCaseSensitive(node, "fields");
        cJSON *obj = cJSON_CreateObject();
        cJSON *child;
        if (!cJSON_IsObject(fields) || !obj) return fail(err, errlen, "bad-object");
        cJSON_ArrayForEach(child, fields) {
            cJSON *val = NULL;
            if (eval_node(child, root, item, in_each, bindings, &val, err, errlen) != 0) {
                cJSON_Delete(obj);
                return -1;
            }
            cJSON_AddItemToObject(obj, child->string, val);
        }
        *out = obj;
        return 0;
    }
    if (strcmp(op, "count") == 0) {
        cJSON *ofn = NULL;
        if (eval_node(cJSON_GetObjectItemCaseSensitive(node, "of"), root, item, in_each, bindings, &ofn, err, errlen) != 0)
            return -1;
        if (!ofn || cJSON_IsNull(ofn)) { *out = cJSON_CreateNumber(0); cJSON_Delete(ofn); return 0; }
        if (cJSON_IsArray(ofn)) *out = cJSON_CreateNumber(cJSON_GetArraySize(ofn));
        else if (cJSON_IsString(ofn)) *out = cJSON_CreateNumber((double)strlen(ofn->valuestring));
        else *out = cJSON_CreateNumber(0);
        cJSON_Delete(ofn);
        return 0;
    }
    if (strcmp(op, "require") == 0) {
        cJSON *ofn = NULL;
        cJSON *ej = cJSON_GetObjectItemCaseSensitive(node, "error");
        cJSON *pj = cJSON_GetObjectItemCaseSensitive(node, "path");
        if (eval_node(cJSON_GetObjectItemCaseSensitive(node, "of"), root, item, in_each, bindings, &ofn, err, errlen) != 0)
            return -1;
        if (!ofn || cJSON_IsNull(ofn)) {
            cJSON_Delete(ofn);
            return fail_path(err, errlen, cJSON_IsString(ej) ? ej->valuestring : "missing", pj);
        }
        *out = ofn;
        return 0;
    }
    if (strcmp(op, "as_int") == 0) {
        cJSON *ofn = NULL;
        cJSON *te = cJSON_GetObjectItemCaseSensitive(node, "type_error");
        cJSON *me = cJSON_GetObjectItemCaseSensitive(node, "missing_error");
        cJSON *pj = cJSON_GetObjectItemCaseSensitive(node, "path");
        if (eval_node(cJSON_GetObjectItemCaseSensitive(node, "of"), root, item, in_each, bindings, &ofn, err, errlen) != 0)
            return -1;
        if (!ofn || cJSON_IsNull(ofn)) {
            cJSON_Delete(ofn);
            return fail_path(err, errlen, cJSON_IsString(me) ? me->valuestring : "missing", pj);
        }
        if (!cJSON_IsNumber(ofn) || ofn->valuedouble != (double)ofn->valueint) {
            cJSON_Delete(ofn);
            return fail_path(err, errlen, cJSON_IsString(te) ? te->valuestring : "invalid-integer", pj);
        }
        *out = ofn;
        return 0;
    }
    if (strcmp(op, "as_decimal") == 0) {
        cJSON *ofn = NULL;
        cJSON *te = cJSON_GetObjectItemCaseSensitive(node, "type_error");
        cJSON *me = cJSON_GetObjectItemCaseSensitive(node, "missing_error");
        cJSON *pj = cJSON_GetObjectItemCaseSensitive(node, "path");
        uem_dec d;
        if (eval_node(cJSON_GetObjectItemCaseSensitive(node, "of"), root, item, in_each, bindings, &ofn, err, errlen) != 0)
            return -1;
        if (!ofn || cJSON_IsNull(ofn)) {
            cJSON_Delete(ofn);
            return fail_path(err, errlen, cJSON_IsString(me) ? me->valuestring : "missing", pj);
        }
        if (!cJSON_IsString(ofn)) {
            cJSON_Delete(ofn);
            return fail_path(err, errlen, cJSON_IsString(te) ? te->valuestring : "not-decimal-string", pj);
        }
        d = uem_dec_from_str(ofn->valuestring);
        cJSON_Delete(ofn);
        if (!d.ok) return fail_path(err, errlen, cJSON_IsString(te) ? te->valuestring : "not-decimal-string", pj);
        /* store as object {"__dec__": coeff} */
        *out = cJSON_CreateObject();
        cJSON_AddStringToObject(*out, "__uem_dec__", "1");
        cJSON_AddNumberToObject(*out, "coeff", (double)d.coeff);
        return 0;
    }
    if (strcmp(op, "min_value") == 0 || strcmp(op, "max_value") == 0) {
        cJSON *ofn = NULL, *boundj;
        uem_dec v, b;
        cJSON *ej = cJSON_GetObjectItemCaseSensitive(node, "error");
        if (eval_node(cJSON_GetObjectItemCaseSensitive(node, "of"), root, item, in_each, bindings, &ofn, err, errlen) != 0)
            return -1;
        boundj = cJSON_GetObjectItemCaseSensitive(node, "bound");
        if (cJSON_IsObject(ofn) && cJSON_GetObjectItem(ofn, "__uem_dec__")) {
            v.coeff = (int64_t)cJSON_GetObjectItem(ofn, "coeff")->valuedouble;
            v.ok = 1;
        } else if (cJSON_IsNumber(ofn)) {
            v = uem_dec_from_i64(ofn->valueint);
        } else {
            cJSON_Delete(ofn);
            return fail(err, errlen, "bad-value");
        }
        if (cJSON_IsString(boundj)) b = uem_dec_from_str(boundj->valuestring);
        else if (cJSON_IsNumber(boundj)) b = uem_dec_from_i64(boundj->valueint);
        else { cJSON_Delete(ofn); return fail(err, errlen, "bad-bound"); }
        if (strcmp(op, "min_value") == 0 && uem_dec_cmp(v, b) < 0) {
            cJSON *pj = cJSON_GetObjectItemCaseSensitive(node, "path");
            cJSON_Delete(ofn);
            return fail_path(err, errlen, cJSON_IsString(ej) ? ej->valuestring : "below-minimum", pj);
        }
        if (strcmp(op, "max_value") == 0 && uem_dec_cmp(v, b) > 0) {
            cJSON *pj = cJSON_GetObjectItemCaseSensitive(node, "path");
            cJSON_Delete(ofn);
            return fail_path(err, errlen, cJSON_IsString(ej) ? ej->valuestring : "above-maximum", pj);
        }
        *out = ofn;
        return 0;
    }
    if (strcmp(op, "mul") == 0 || strcmp(op, "add") == 0) {
        cJSON *values = cJSON_GetObjectItemCaseSensitive(node, "values");
        cJSON *child;
        uem_dec acc;
        int first = 1;
        if (!cJSON_IsArray(values)) return fail(err, errlen, "bad-values");
        acc.ok = 0;
        cJSON_ArrayForEach(child, values) {
            cJSON *v = NULL;
            uem_dec d;
            if (eval_node(child, root, item, in_each, bindings, &v, err, errlen) != 0) return -1;
            if (cJSON_IsObject(v) && cJSON_GetObjectItem(v, "__uem_dec__")) {
                d.coeff = (int64_t)cJSON_GetObjectItem(v, "coeff")->valuedouble;
                d.ok = 1;
            } else if (cJSON_IsNumber(v)) d = uem_dec_from_i64(v->valueint);
            else { cJSON_Delete(v); return fail(err, errlen, "bad-num"); }
            cJSON_Delete(v);
            if (first) { acc = d; first = 0; }
            else if (strcmp(op, "mul") == 0) acc = uem_dec_mul(acc, d);
            else acc = uem_dec_add(acc, d);
            if (!acc.ok) return fail(err, errlen, "num-overflow");
        }
        *out = cJSON_CreateObject();
        cJSON_AddStringToObject(*out, "__uem_dec__", "1");
        cJSON_AddNumberToObject(*out, "coeff", (double)acc.coeff);
        return 0;
    }
    if (strcmp(op, "sum_each") == 0) {
        cJSON *coll = NULL, *each = cJSON_GetObjectItemCaseSensitive(node, "each");
        cJSON *el;
        uem_dec total = uem_dec_from_i64(0);
        if (eval_node(cJSON_GetObjectItemCaseSensitive(node, "collection"), root, item, in_each, bindings, &coll, err, errlen) != 0)
            return -1;
        if (!cJSON_IsArray(coll)) { cJSON_Delete(coll); return fail(err, errlen, "items-not-a-list"); }
        {
        int sidx = 0;
        cJSON *cpath = cJSON_GetObjectItemCaseSensitive(node, "path");
        g_coll_path = cpath;
        cJSON_ArrayForEach(el, coll) {
            cJSON *part = NULL;
            uem_dec d;
            g_item_index = sidx;
            if (!cJSON_IsObject(el)) { g_item_index = -1; g_coll_path = NULL; cJSON_Delete(coll); return fail(err, errlen, "item-not-an-object"); }
            if (eval_node(each, root, el, 1, bindings, &part, err, errlen) != 0) {
                g_item_index = -1; g_coll_path = NULL;
                cJSON_Delete(coll);
                return -1;
            }
            if (cJSON_IsObject(part) && cJSON_GetObjectItem(part, "__uem_dec__")) {
                d.coeff = (int64_t)cJSON_GetObjectItem(part, "coeff")->valuedouble;
                d.ok = 1;
            } else { cJSON_Delete(part); cJSON_Delete(coll); return fail(err, errlen, "bad-num"); }
            cJSON_Delete(part);
            total = uem_dec_add(total, d);
            if (!total.ok) { g_item_index = -1; g_coll_path = NULL; cJSON_Delete(coll); return fail(err, errlen, "num-overflow"); }
            sidx++;
        }
        g_item_index = -1;
        g_coll_path = NULL;
        }
        cJSON_Delete(coll);
        *out = cJSON_CreateObject();
        cJSON_AddStringToObject(*out, "__uem_dec__", "1");
        cJSON_AddNumberToObject(*out, "coeff", (double)total.coeff);
        return 0;
    }
    if (strcmp(op, "quantize") == 0) {
        cJSON *ofn = NULL;
        cJSON *exp = cJSON_GetObjectItemCaseSensitive(node, "exp");
        cJSON *rnd = cJSON_GetObjectItemCaseSensitive(node, "rounding");
        uem_dec d, q;
        if (eval_node(cJSON_GetObjectItemCaseSensitive(node, "of"), root, item, in_each, bindings, &ofn, err, errlen) != 0)
            return -1;
        if (cJSON_IsObject(ofn) && cJSON_GetObjectItem(ofn, "__uem_dec__")) {
            d.coeff = (int64_t)cJSON_GetObjectItem(ofn, "coeff")->valuedouble;
            d.ok = 1;
        } else { cJSON_Delete(ofn); return fail(err, errlen, "bad-num"); }
        cJSON_Delete(ofn);
        q = uem_dec_quantize(d, cJSON_IsString(exp) ? exp->valuestring : "0.01",
                             cJSON_IsString(rnd) ? rnd->valuestring : "ROUND_HALF_UP");
        if (!q.ok) return fail(err, errlen, "quantize-fail");
        *out = cJSON_CreateObject();
        cJSON_AddStringToObject(*out, "__uem_dec__", "1");
        cJSON_AddNumberToObject(*out, "coeff", (double)q.coeff);
        return 0;
    }
    if (strcmp(op, "decimal_str") == 0) {
        cJSON *ofn = NULL;
        cJSON *pl = cJSON_GetObjectItemCaseSensitive(node, "places");
        int places = cJSON_IsNumber(pl) ? pl->valueint : 2;
        char buf[64];
        uem_dec d;
        if (eval_node(cJSON_GetObjectItemCaseSensitive(node, "of"), root, item, in_each, bindings, &ofn, err, errlen) != 0)
            return -1;
        if (cJSON_IsObject(ofn) && cJSON_GetObjectItem(ofn, "__uem_dec__")) {
            d.coeff = (int64_t)cJSON_GetObjectItem(ofn, "coeff")->valuedouble;
            d.ok = 1;
        } else { cJSON_Delete(ofn); return fail(err, errlen, "bad-num"); }
        cJSON_Delete(ofn);
        if (uem_dec_format(d, places, buf, sizeof buf) != 0) return fail(err, errlen, "format-fail");
        *out = cJSON_CreateString(buf);
        return 0;
    }
    if (strcmp(op, "str_len") == 0 || strcmp(op, "line_count") == 0 ||
        strcmp(op, "word_count") == 0 || strcmp(op, "unique_casefold_word_count") == 0) {
        cJSON *ofn = NULL;
        const char *s;
        if (eval_node(cJSON_GetObjectItemCaseSensitive(node, "of"), root, item, in_each, bindings, &ofn, err, errlen) != 0)
            return -1;
        if (!cJSON_IsString(ofn)) { cJSON_Delete(ofn); return fail(err, errlen, "invalid-text"); }
        s = ofn->valuestring;
        if (strcmp(op, "str_len") == 0) {
            /* UTF-8 code units (Python len on str is codepoints for BMP mostly - actually Python 3 len is codepoints)
               For proof vectors ASCII + Hebrew: counting UTF-8 codepoints */
            size_t i = 0, cps = 0;
            while (s[i]) {
                unsigned char c = (unsigned char)s[i];
                if (c < 0x80) i++;
                else if ((c & 0xe0) == 0xc0) i += 2;
                else if ((c & 0xf0) == 0xe0) i += 3;
                else if ((c & 0xf8) == 0xf0) i += 4;
                else i++;
                cps++;
            }
            *out = cJSON_CreateNumber((double)cps);
        } else if (strcmp(op, "line_count") == 0) {
            size_t lines = 0, i = 0;
            if (s[0] == 0) { *out = cJSON_CreateNumber(0); }
            else {
                lines = 1;
                while (s[i]) { if (s[i] == '\n') lines++; i++; }
                /* Python splitlines: trailing empty not counted same as splitlines()
                   "a\n".splitlines() -> ['a'] len 1; "a\nb".splitlines() -> 2
                   empty string -> [] */
                if (s[0] == 0) lines = 0;
                *out = cJSON_CreateNumber((double)lines);
            }
            /* match Python: "".splitlines()=0; "a".splitlines()=1; "a\n".splitlines()=1; "a\nb"=2 */
            {
                size_t n = 0;
                const char *p = s;
                if (*p) {
                    while (*p) {
                        const char *start = p;
                        while (*p && *p != '\n' && *p != '\r') p++;
                        n++;
                        if (*p == '\r' && p[1] == '\n') p += 2;
                        else if (*p == '\n' || *p == '\r') p++;
                        (void)start;
                    }
                }
                cJSON_Delete(*out);
                *out = cJSON_CreateNumber((double)n);
            }
        } else if (strcmp(op, "word_count") == 0) {
            size_t n = 0, i = 0, in = 0;
            while (s[i]) {
                if (!isspace((unsigned char)s[i])) {
                    if (!in) { n++; in = 1; }
                } else in = 0;
                i++;
            }
            *out = cJSON_CreateNumber((double)n);
        } else {
            /* unique casefold words */
            char **seen = NULL;
            size_t nseen = 0, cap = 0, i = 0;
            while (s[i]) {
                while (s[i] && isspace((unsigned char)s[i])) i++;
                if (!s[i]) break;
                {
                    size_t start = i, len, k, found = 0;
                    char word[512], cf[512];
                    while (s[i] && !isspace((unsigned char)s[i])) i++;
                    len = i - start;
                    if (len >= sizeof word) len = sizeof word - 1;
                    memcpy(word, s + start, len);
                    word[len] = 0;
                    casefold_copy(word, cf, sizeof cf);
                    for (k = 0; k < nseen; k++) if (strcmp(seen[k], cf) == 0) { found = 1; break; }
                    if (!found) {
                        if (nseen + 1 > cap) {
                            size_t ncap = cap ? cap * 2 : 8;
                            char **ns = (char **)uem_mem_realloc(seen, ncap * sizeof(char *));
                            if (!ns) { /* leak on OOM path simplified */ break; }
                            seen = ns; cap = ncap;
                        }
                        seen[nseen] = uem_mem_strdup(cf);
                        nseen++;
                    }
                }
            }
            *out = cJSON_CreateNumber((double)nseen);
            for (i = 0; i < nseen; i++) uem_mem_free(seen[i]);
            uem_mem_free(seen);
        }
        cJSON_Delete(ofn);
        return 0;
    }
    return fail(err, errlen, "unknown-op");
}

int uem_expr_eval(uem_machine *m, cJSON *node, cJSON *root, cJSON *bindings, cJSON **out,
                  char *err, size_t errlen, cJSON **err_path) {
    int rc;
    (void)m;
    if (g_err_path) { cJSON_Delete(g_err_path); g_err_path = NULL; }
    rc = eval_node(node, root, NULL, 0, bindings, out, err, errlen);
    if (err_path) {
        *err_path = g_err_path;
        g_err_path = NULL;
    } else if (g_err_path) {
        cJSON_Delete(g_err_path);
        g_err_path = NULL;
    }
    return rc;
}
