#include "machine_internal.h"
#include "../third_party/sha256.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int rd_u16(const uint8_t *b, size_t n, size_t *off, uint16_t *out) {
    if (*off + 2 > n) return -1;
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
            if (i + 1 >= len || (s[i+1] & 0xc0) != 0x80) return 0;
            if (c < 0xc2) return 0; /* overlong */
            i += 2; continue;
        }
        if ((c & 0xf0) == 0xe0) {
            if (i + 2 >= len || (s[i+1] & 0xc0) != 0x80 || (s[i+2] & 0xc0) != 0x80) return 0;
            i += 3; continue;
        }
        if ((c & 0xf8) == 0xf0) {
            if (i + 3 >= len || (s[i+1] & 0xc0) != 0x80 || (s[i+2] & 0xc0) != 0x80 || (s[i+3] & 0xc0) != 0x80) return 0;
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
static int reencode_match(const uint8_t *bytes, size_t len, const uem_instr *instr, uint32_t n,
                          const uint8_t *img, uint32_t img_len) {
    size_t cap = 16 + (size_t)n * (2 + 4 + UEM_MAX_OPERAND) + 4 + img_len;
    uint8_t *out = (uint8_t *)malloc(cap);
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
            size_t L = strlen(instr[i].operand);
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
        free(out);
        return ok;
    }
}

static void free_partial(uem_machine *m, uint32_t n) {
    uint32_t i;
    if (!m) return;
    if (m->instr) {
        for (i = 0; i < n; i++) free(m->instr[i].operand);
        free(m->instr);
    }
    free(m);
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
    if (rd_u16(bytes, len, &off, &ver) || ver != UEM_FORMAT_VERSION) {
        if (err && errlen) snprintf(err, errlen, "bad-version");
        return UEM_ERR_DECODE;
    }
    if (rd_u16(bytes, len, &off, &flags) || flags != 0) {
        if (err && errlen) snprintf(err, errlen, "bad-flags");
        return UEM_ERR_DECODE;
    }
    if (rd_u32(bytes, len, &off, &count) || count == 0 || count > UEM_MAX_INSTR) {
        if (err && errlen) snprintf(err, errlen, "bad-count");
        return UEM_ERR_DECODE;
    }
    m = (uem_machine *)calloc(1, sizeof(*m));
    if (!m) return UEM_ERR_NOMEM;
    m->instr = (uem_instr *)calloc(count, sizeof(uem_instr));
    if (!m->instr) { free(m); return UEM_ERR_NOMEM; }
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
        if (tag == 0) {
            /* none */
        } else if (tag == 1) {
            uint32_t L;
            if (rd_u32(bytes, len, &off, &L) || L > UEM_MAX_OPERAND || off + L > len) {
                free_partial(m, i); if (err) snprintf(err, errlen, "truncated"); return UEM_ERR_DECODE;
            }
            if (!valid_utf8(bytes + off, L)) {
                free_partial(m, i); if (err) snprintf(err, errlen, "invalid-utf8"); return UEM_ERR_DECODE;
            }
            m->instr[i].operand = (char *)malloc(L + 1);
            if (!m->instr[i].operand) { free_partial(m, i); return UEM_ERR_NOMEM; }
            memcpy(m->instr[i].operand, bytes + off, L);
            m->instr[i].operand[L] = 0;
            off += L;
        } else {
            free_partial(m, i); if (err) snprintf(err, errlen, "bad-tag"); return UEM_ERR_DECODE;
        }
    }
    if (rd_u32(bytes, len, &off, &img_len) || img_len > UEM_MAX_IMAGE || off + img_len > len) {
        free_partial(m, count); if (err) snprintf(err, errlen, "truncated"); return UEM_ERR_DECODE;
    }
    if (off + img_len != len) {
        free_partial(m, count); if (err) snprintf(err, errlen, "trailing-bytes"); return UEM_ERR_DECODE;
    }
    img_ptr = bytes + off;
    if (!valid_utf8(img_ptr, img_len)) {
        free_partial(m, count); if (err) snprintf(err, errlen, "invalid-utf8-image"); return UEM_ERR_DECODE;
    }
    img_str = (char *)malloc(img_len + 1);
    if (!img_str) { free_partial(m, count); return UEM_ERR_NOMEM; }
    memcpy(img_str, img_ptr, img_len);
    img_str[img_len] = 0;
    image = cJSON_ParseWithLength(img_str, img_len);
    free(img_str);
    if (!image || !cJSON_IsObject(image)) {
        if (image) cJSON_Delete(image);
        free_partial(m, count);
        if (err) snprintf(err, errlen, "bad-image-json");
        return UEM_ERR_DECODE;
    }
    /* noncanonical image: cJSON PrintUnformatted uses compact form; require exact match via re-print sort?
       Spec: sort_keys separators. cJSON doesn't sort. Compare re-encode of instructions+original image bytes. */
    if (!reencode_match(bytes, len, m->instr, count, img_ptr, img_len)) {
        cJSON_Delete(image);
        free_partial(m, count);
        if (err) snprintf(err, errlen, "noncanonical-encoding");
        return UEM_ERR_DECODE;
    }
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
