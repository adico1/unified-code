/* MCU host demo — UEM-MCU-1 profile surface.
 * Uses portable core. No filesystem in the OUTWARD path for inject hosts.
 * L12: do not claim an MCU family until tested on a physical board.
 */
#include "uem_mcu.h"
#include "uem.h"
#include "../../third_party/cJSON.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct { cJSON *host; } inj_ctx;

static int demo_inject(void *ctx, const char *effect, const char *source_json,
                       char *result_json, size_t result_cap, char *err, size_t errlen) {
    inj_ctx *h = (inj_ctx *)ctx;
    (void)source_json;
    if (h && h->host) {
        if (strcmp(effect, "read_utf8") == 0) {
            cJSON *t = cJSON_GetObjectItemCaseSensitive(h->host, "text");
            if (cJSON_IsString(t)) {
                cJSON *w = cJSON_CreateObject();
                char *p;
                cJSON_AddStringToObject(w, "data", t->valuestring);
                p = cJSON_PrintUnformatted(w);
                snprintf(result_json, result_cap, "%s", p);
                free(p);
                cJSON_Delete(w);
                return 0;
            }
        }
        if (strcmp(effect, "read_json") == 0) {
            cJSON *d = cJSON_GetObjectItemCaseSensitive(h->host, "document");
            if (cJSON_IsObject(d)) {
                cJSON *w = cJSON_CreateObject();
                char *p;
                cJSON_AddItemToObject(w, "data", cJSON_Duplicate(d, 1));
                p = cJSON_PrintUnformatted(w);
                snprintf(result_json, result_cap, "%s", p);
                free(p);
                cJSON_Delete(w);
                return 0;
            }
        }
    }
    snprintf(err, errlen, "mcu-outward-pending");
    snprintf(result_json, result_cap,
             "{\"error\":\"mcu-outward-pending\",\"effect\":\"%s\"}",
             effect ? effect : "");
    return 0;
}

static uint8_t *read_all(const char *path, size_t *n) {
    FILE *f = fopen(path, "rb");
    long sz;
    uint8_t *b;
    if (!f) return NULL;
    if (fseek(f, 0, SEEK_END) != 0) { fclose(f); return NULL; }
    sz = ftell(f);
    if (sz < 0) { fclose(f); return NULL; }
    rewind(f);
    b = (uint8_t *)malloc((size_t)sz);
    if (!b) { fclose(f); return NULL; }
    if (fread(b, 1, (size_t)sz, f) != (size_t)sz) { free(b); fclose(f); return NULL; }
    fclose(f);
    *n = (size_t)sz;
    return b;
}

int main(int argc, char **argv) {
    size_t n = 0;
    uint8_t *bc;
    const char *host = "{}";
    int i;
    uem_machine *m = NULL;
    char err[256];
    inj_ctx hc;
    char *out;
    if (argc < 3 || strcmp(argv[1], "run") != 0) {
        fprintf(stderr, "uem-mcu-demo run <program.uem> --host '<json>'\n");
        fprintf(stderr, "profile=%s — not a board support claim (L12)\n", UEM_MCU_PROFILE);
        return 2;
    }
    for (i = 3; i < argc; i++)
        if (strcmp(argv[i], "--host") == 0 && i + 1 < argc) host = argv[++i];
    bc = read_all(argv[2], &n);
    if (!bc) { fprintf(stderr, "read fail\n"); return 1; }
    if (uem_decode_verify(bc, n, &m, err, sizeof err) != UEM_OK) {
        fprintf(stderr, "decode: %s\n", err);
        free(bc);
        return 1;
    }
    free(bc);
    if (uem_set_host_json(m, host, err, sizeof err) != UEM_OK) {
        fprintf(stderr, "host: %s\n", err);
        uem_free(m);
        return 1;
    }
    hc.host = cJSON_Parse(host);
    uem_set_outward_handler(m, demo_inject, &hc);
    uem_run(m, err, sizeof err);
    out = uem_result_json(m);
    if (out) { fputs(out, stdout); fputc('\n', stdout); free(out); }
    if (hc.host) cJSON_Delete(hc.host);
    uem_free(m);
    return 0;
}
