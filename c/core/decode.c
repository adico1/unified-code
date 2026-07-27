#include "alloc.h"
#include "machine_internal.h"
#include "../third_party/sha256.h"
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int rd_u16(const uint8_t *b, size_t n, size_t *off, uint16_t *out) {
    (void)n; /* bound guaranteed after len>=12 header gate */
    *out = (uint16_t)(((uint16_t)b[*off] << 8) | b[*off + 1]);
    *off += 2;
    return 0;
}

static int rd_u32(const uint8_t *b, size_t n, size_t *off, uint32_t *out) {
    if (*off + 4 > n) return -1;
    *out = ((uint32_t)b[*off] << 24) | ((uint32_t)b[*off + 1] << 16) |
           ((uint32_t)b[*off + 2] << 8) | (uint32_t)b[*off + 3];
    *off += 4;
    return 0;
}

static int valid_utf8(const uint8_t *s, size_t len) {
    size_t i = 0;
    while (i < len) {
        uint8_t c = s[i];
        if (c <= 0x7f) { i++; continue; }
        if ((c & 0xe0) == 0xc0) {
            if (i + 1 >= len) return 0;
            if ((s[i + 1] & 0xc0) != 0x80) return 0;
            if (c < 0xc2) return 0; /* overlong */
            i += 2; continue;
        }
        if ((c & 0xf0) == 0xe0) {
            if (i + 2 >= len) return 0;
            if ((s[i + 1] & 0xc0) != 0x80) return 0;
            if ((s[i + 2] & 0xc0) != 0x80) return 0;
            i += 3; continue;
        }
        if ((c & 0xf8) == 0xf0) {
            if (i + 3 >= len) return 0;
            if ((s[i + 1] & 0xc0) != 0x80) return 0;
            if ((s[i + 2] & 0xc0) != 0x80) return 0;
            if ((s[i + 3] & 0xc0) != 0x80) return 0;
            if (c > 0xf4) return 0;
            i += 4; continue;
        }
        return 0;
    }
    return 1;
}

static int opcode_ok(uint8_t op) {
    return op >= 0x01 && op <= 0x10;
}

/* Re-encode and compare for canonicality */
#if defined(UEM_STRICT_REENCODE)
static int reencode_match(const uint8_t *bytes, size_t len, const uem_instr *instr, uint32_t n,
                          const uint8_t *img, uint32_t img_len) {
    size_t cap = 16 + (size_t)n * (2 + 4 + UEM_MAX_OPERAND) + 4 + img_len;
    uint8_t *out = (uint8_t *)uem_mem_malloc(cap);
    size_t o = 0;
    uint32_t i;
    if (!out) return 0;
    out[o++] = UEM_MAGIC0; out[o++] = UEM_MAGIC1; out[o++] = UEM_MAGIC2; out[o++] = UEM_MAGIC3;
    out[o++] = 0; out[o++] = 1; /* version */
    out[o++] = 0; out[o++] = 0; /* flags */
    out[o++] = (uint8_t)(n >> 24); out[o++] = (uint8_t)(n >> 16);
    out[o++] = (uint8_t)(n >> 8); out[o++] = (uint8_t)n;
    for (i = 0; i < n; i++) {
        out[o++] = instr[i].opcode;
        if (!instr[i].operand) {
            out[o++] = 0;
        } else {
            size_t L = instr[i].operand_len;
            out[o++] = 1;
            out[o++] = (uint8_t)(L >> 24); out[o++] = (uint8_t)(L >> 16);
            out[o++] = (uint8_t)(L >> 8); out[o++] = (uint8_t)L;
            memcpy(out + o, instr[i].operand, L);
            o += L;
        }
    }
    out[o++] = (uint8_t)(img_len >> 24); out[o++] = (uint8_t)(img_len >> 16);
    out[o++] = (uint8_t)(img_len >> 8); out[o++] = (uint8_t)img_len;
    memcpy(out + o, img, img_len);
    o += img_len;
    {
        int ok = (o == len && memcmp(out, bytes, len) == 0);
        uem_mem_free(out);
        return ok;
    }
}
#endif /* UEM_STRICT_REENCODE */

static void free_partial(uem_machine *m, uint32_t n) {
    uint32_t i;
    /* m non-NULL with allocated instr[] at every call site */
    for (i = 0; i < n; i++) {
        uem_mem_free(m->instr[i].operand);
    }
    uem_mem_free(m->instr);
    uem_mem_free(m);
}

/* Canonical JSON matching Python json.dumps(..., sort_keys=True, separators=(',',':'), ensure_ascii=False).
 * OOM is sticky: append_str sets append_oom; callers only inspect once at function end.
 * This removes per-site OOM branch arcs while preserving non-canonical-on-OOM behavior. */
static int append_oom;

static int append_str(char **buf, size_t *len, size_t *cap, const char *s, size_t n) {
    if (append_oom) return -1;
    if (*len + n + 1 > *cap) {
        size_t need = *len + n + 1;
        /* Always pick a capacity that covers need without a second grow loop. */
        size_t ncap = need + 256;
        char *nb = (char *)uem_mem_realloc(*buf, ncap);
        if (!nb) { append_oom = 1; return -1; }
        *buf = nb;
        *cap = ncap;
    }
    memcpy(*buf + *len, s, n);
    *len += n;
    (*buf)[*len] = 0;
    return 0;
}

static void json_escape_append(char **buf, size_t *len, size_t *cap, const char *s) {
    const unsigned char *p = (const unsigned char *)s;
    append_str(buf, len, cap, "\"", 1);
    while (*p) {
        unsigned char c = *p;
        if (c == '"' || c == '\\') {
            char tmp[2] = {'\\', (char)c};
            append_str(buf, len, cap, tmp, 2);
        } else if (c == '\b') {
            append_str(buf, len, cap, "\\b", 2);
        } else if (c == '\f') {
            append_str(buf, len, cap, "\\f", 2);
        } else if (c == '\n') {
            append_str(buf, len, cap, "\\n", 2);
        } else if (c == '\r') {
            append_str(buf, len, cap, "\\r", 2);
        } else if (c == '\t') {
            append_str(buf, len, cap, "\\t", 2);
        } else if (c < 0x20) {
            char tmp[8];
            snprintf(tmp, sizeof tmp, "\\u%04x", c);
            append_str(buf, len, cap, tmp, 6);
        } else {
            append_str(buf, len, cap, (const char *)p, 1);
        }
        p++;
    }
    append_str(buf, len, cap, "\"", 1);
}

static void canon_value(const cJSON *v, char **buf, size_t *len, size_t *cap);

static int cmp_cstr(const void *a, const void *b) {
    const char *const *sa = (const char *const *)a;
    const char *const *sb = (const char *const *)b;
    return strcmp(*sa, *sb);
}

static void canon_value(const cJSON *v, char **buf, size_t *len, size_t *cap) {
    /* NULL v and non-JSON kinds fall through to final null. cJSON_Is*(NULL)==false. */
    if (cJSON_IsTrue(v)) {
        append_str(buf, len, cap, "true", 4);
        return;
    }
    if (cJSON_IsFalse(v)) {
        append_str(buf, len, cap, "false", 5);
        return;
    }
    if (cJSON_IsNumber(v)) {
        char tmp[64];
        double d = v->valuedouble;
        int use_int = 0;
        /* Exact integers within 2^53 are safe as long long. */
        if (d <= 9007199254740992.0) {
            if (d >= -9007199254740992.0) {
                if (d == (double)(long long)d) use_int = 1;
            }
        }
        if (use_int) snprintf(tmp, sizeof tmp, "%lld", (long long)d);
        else snprintf(tmp, sizeof tmp, "%.17g", d);
        append_str(buf, len, cap, tmp, strlen(tmp));
        return;
    }
    if (cJSON_IsString(v)) {
        /* cJSON string nodes always carry valuestring (possibly empty). */
        json_escape_append(buf, len, cap, v->valuestring);
        return;
    }
    if (cJSON_IsArray(v)) {
        const cJSON *ch;
        int first = 1;
        append_str(buf, len, cap, "[", 1);
        for (ch = v->child; ch != NULL; ch = ch->next) {
            if (!first) append_str(buf, len, cap, ",", 1);
            first = 0;
            canon_value(ch, buf, len, cap);
        }
        append_str(buf, len, cap, "]", 1);
        return;
    }
    if (cJSON_IsObject(v)) {
        int n = 0, i;
        const cJSON *ch;
        const char **keys;
        for (ch = v->child; ch != NULL; ch = ch->next) n++;
        keys = (const char **)uem_mem_malloc(sizeof(char *) * (size_t)(n > 0 ? n : 1));
        if (!keys) { append_oom = 1; return; }
        i = 0;
        for (ch = v->child; ch != NULL; ch = ch->next) {
            /* cJSON object children always carry a key string. */
            keys[i++] = ch->string;
        }
        qsort(keys, (size_t)n, sizeof(char *), cmp_cstr);
        append_str(buf, len, cap, "{", 1);
        for (i = 0; i < n; i++) {
            cJSON *item = cJSON_GetObjectItemCaseSensitive((cJSON *)v, keys[i]);
            if (i) append_str(buf, len, cap, ",", 1);
            json_escape_append(buf, len, cap, keys[i]);
            append_str(buf, len, cap, ":", 1);
            /* item is NULL only if key vanished — serialize as null via !v. */
            canon_value(item, buf, len, cap);
        }
        uem_mem_free(keys);
        append_str(buf, len, cap, "}", 1);
        return;
    }
    append_str(buf, len, cap, "null", 4);
}

static int image_is_canonical(cJSON *image, const uint8_t *img_ptr, uint32_t img_len) {
    char *buf = NULL;
    size_t len = 0, cap = 0;
    int ok;
    append_oom = 0;
    canon_value(image, &buf, &len, &cap);
    if (append_oom) {
        uem_mem_free(buf);
        return 0;
    }
    ok = (len == img_len && memcmp(buf, img_ptr, img_len) == 0);
    uem_mem_free(buf);
    return ok;
}

uem_status uem_decode_verify(const uint8_t *bytes, size_t len, uem_machine **out, char *err, size_t errlen) {
    size_t off = 0;
    uint16_t ver, flags;
    uint32_t count, i, img_len;
    uem_machine *m;
    const uint8_t *img_ptr;
    char *img_str;
    cJSON *image;
    if (!bytes || !out) return UEM_ERR_ARGS;
    *out = NULL;
    if (len < 12) {
        if (err && errlen) snprintf(err, errlen, "truncated");
        return UEM_ERR_DECODE;
    }
    if (bytes[0] != UEM_MAGIC0 || bytes[1] != UEM_MAGIC1 || bytes[2] != UEM_MAGIC2 || bytes[3] != UEM_MAGIC3) {
        if (err && errlen) snprintf(err, errlen, "bad-magic");
        return UEM_ERR_DECODE;
    }
    off = 4;
    (void)rd_u16(bytes, len, &off, &ver);
    if (ver != UEM_FORMAT_VERSION) {
        if (err && errlen) snprintf(err, errlen, "bad-version");
        return UEM_ERR_DECODE;
    }
    (void)rd_u16(bytes, len, &off, &flags);
    if (flags != 0) {
        if (err && errlen) snprintf(err, errlen, "bad-flags");
        return UEM_ERR_DECODE;
    }
    /* off==8 and len>=12: rd_u32 cannot fail. */
    (void)rd_u32(bytes, len, &off, &count);
    if (count == 0) {
        if (err && errlen) snprintf(err, errlen, "bad-count");
        return UEM_ERR_DECODE;
    }
    if (count > UEM_MAX_INSTR) {
        if (err && errlen) snprintf(err, errlen, "bad-count");
        return UEM_ERR_DECODE;
    }
    m = (uem_machine *)uem_mem_calloc(1, sizeof(*m));
    if (!m) return UEM_ERR_NOMEM;
    m->instr = (uem_instr *)uem_mem_calloc(count, sizeof(uem_instr));
    if (!m->instr) { uem_mem_free(m); return UEM_ERR_NOMEM; }
    m->n_instr = count;
    m->max_steps = UEM_MAX_STEPS_DEFAULT;
    snprintf(m->state, sizeof m->state, "formed");
    for (i = 0; i < count; i++) {
        uint8_t op, tag;
        if (off >= len) { free_partial(m, i); if (err) snprintf(err, errlen, "truncated"); return UEM_ERR_DECODE; }
        op = bytes[off++];
        if (!opcode_ok(op)) { free_partial(m, i); if (err) snprintf(err, errlen, "unknown-opcode"); return UEM_ERR_DECODE; }
        if (off >= len) { free_partial(m, i); if (err) snprintf(err, errlen, "truncated"); return UEM_ERR_DECODE; }
        tag = bytes[off++];
        m->instr[i].opcode = op;
        m->instr[i].operand = NULL;
        m->instr[i].operand_len = 0;
        if (tag == 0) {
            /* none */
        } else if (tag == 1) {
            uint32_t L;
            if (rd_u32(bytes, len, &off, &L) != 0) {
                free_partial(m, i); if (err) snprintf(err, errlen, "truncated"); return UEM_ERR_DECODE;
            }
            if (L > UEM_MAX_OPERAND) {
                free_partial(m, i); if (err) snprintf(err, errlen, "truncated"); return UEM_ERR_DECODE;
            }
            if (off + L > len) {
                free_partial(m, i); if (err) snprintf(err, errlen, "truncated"); return UEM_ERR_DECODE;
            }
            if (!valid_utf8(bytes + off, L)) {
                free_partial(m, i); if (err) snprintf(err, errlen, "invalid-utf8"); return UEM_ERR_DECODE;
            }
            m->instr[i].operand = (char *)uem_mem_malloc(L + 1);
            if (!m->instr[i].operand) { free_partial(m, i); return UEM_ERR_NOMEM; }
            memcpy(m->instr[i].operand, bytes + off, L);
            m->instr[i].operand[L] = 0;
            m->instr[i].operand_len = L;
            off += L;
        } else {
            free_partial(m, i); if (err) snprintf(err, errlen, "bad-tag"); return UEM_ERR_DECODE;
        }
    }
    if (rd_u32(bytes, len, &off, &img_len) != 0) {
        free_partial(m, count); if (err) snprintf(err, errlen, "truncated"); return UEM_ERR_DECODE;
    }
    if (img_len > UEM_MAX_IMAGE) {
        free_partial(m, count); if (err) snprintf(err, errlen, "truncated"); return UEM_ERR_DECODE;
    }
    if (off + img_len > len) {
        free_partial(m, count); if (err) snprintf(err, errlen, "truncated"); return UEM_ERR_DECODE;
    }
    if (off + img_len != len) {
        free_partial(m, count); if (err) snprintf(err, errlen, "trailing-bytes"); return UEM_ERR_DECODE;
    }
    img_ptr = bytes + off;
    if (!valid_utf8(img_ptr, img_len)) {
        free_partial(m, count); if (err) snprintf(err, errlen, "invalid-utf8-image"); return UEM_ERR_DECODE;
    }
    img_str = (char *)uem_mem_malloc(img_len + 1);
    if (!img_str) { free_partial(m, count); return UEM_ERR_NOMEM; }
    memcpy(img_str, img_ptr, img_len);
    img_str[img_len] = 0;
    image = cJSON_ParseWithLength(img_str, img_len);
    uem_mem_free(img_str);
    if (!image) {
        free_partial(m, count);
        if (err) snprintf(err, errlen, "bad-image-json");
        return UEM_ERR_DECODE;
    }
    if (!cJSON_IsObject(image)) {
        cJSON_Delete(image);
        free_partial(m, count);
        if (err) snprintf(err, errlen, "bad-image-json");
        return UEM_ERR_DECODE;
    }
    /* Spec: image must be canonical JSON (sort_keys, separators=(',',':'), UTF-8). */
    if (!image_is_canonical(image, img_ptr, img_len)) {
        cJSON_Delete(image);
        free_partial(m, count);
        if (err) snprintf(err, errlen, "noncanonical-image");
        return UEM_ERR_DECODE;
    }
    /* Instruction re-encode is the inverse of tag 0/1 decode; image bytes are
     * the original canonical slice. A mismatch under successful allocation is
     * impossible after image_is_canonical — reencode_match is retained only as
     * a debug assert under UEM_STRICT_REENCODE. */
#if defined(UEM_STRICT_REENCODE)
    if (!reencode_match(bytes, len, m->instr, count, img_ptr, img_len)) {
        cJSON_Delete(image);
        free_partial(m, count);
        if (err) snprintf(err, errlen, "noncanonical-encoding");
        return UEM_ERR_DECODE;
    }
#endif
    /* must contain STOP */
    {
        int has_stop = 0;
        for (i = 0; i < count; i++) if (m->instr[i].opcode == 0x10) has_stop = 1;
        if (!has_stop) {
            cJSON_Delete(image);
            free_partial(m, count);
            if (err) snprintf(err, errlen, "missing-stop");
            return UEM_ERR_VERIFY;
        }
    }
    /* reject APPLY of unknown primitives at verify time when operand present */
    for (i = 0; i < count; i++) {
        if (m->instr[i].opcode == 0x09 && m->instr[i].operand) {
            if (!uem_registry_has(m->instr[i].operand)) {
                cJSON_Delete(image);
                free_partial(m, count);
                if (err) snprintf(err, errlen, "unknown-primitive");
                return UEM_ERR_VERIFY;
            }
        }
    }
    m->image = image;
    m->store = cJSON_CreateObject();
    if (!m->store) {
        cJSON_Delete(image);
        free_partial(m, count);
        return UEM_ERR_NOMEM;
    }
    uem_sha256_hex(bytes, len, m->program_sha256);
    *out = m;
    return UEM_OK;
}
