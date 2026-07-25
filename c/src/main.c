#include "uem.h"
#include "../third_party/cJSON.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static uint8_t *read_file(const char *path, size_t *out_len) {
    FILE *f = fopen(path, "rb");
    long sz;
    uint8_t *buf;
    if (!f) return NULL;
    if (fseek(f, 0, SEEK_END) != 0) { fclose(f); return NULL; }
    sz = ftell(f);
    if (sz < 0) { fclose(f); return NULL; }
    rewind(f);
    buf = (uint8_t *)malloc((size_t)sz);
    if (!buf) { fclose(f); return NULL; }
    if (fread(buf, 1, (size_t)sz, f) != (size_t)sz) { free(buf); fclose(f); return NULL; }
    fclose(f);
    *out_len = (size_t)sz;
    return buf;
}

/* Outward that prefers host inject text/document */
typedef struct {
    cJSON *host;
} host_ctx;

static int host_outward(void *ctx, const char *effect, const char *source_json,
                        char *result_json, size_t result_cap, char *err, size_t errlen) {
    host_ctx *h = (host_ctx *)ctx;
    if (h && h->host) {
        if (strcmp(effect, "read_utf8") == 0) {
            cJSON *t = cJSON_GetObjectItemCaseSensitive(h->host, "text");
            if (cJSON_IsString(t)) {
                cJSON *wrap = cJSON_CreateObject();
                char *p;
                cJSON_AddStringToObject(wrap, "data", t->valuestring);
                p = cJSON_PrintUnformatted(wrap);
                snprintf(result_json, result_cap, "%s", p);
                free(p);
                cJSON_Delete(wrap);
                return 0;
            }
        }
        if (strcmp(effect, "read_json") == 0) {
            cJSON *d = cJSON_GetObjectItemCaseSensitive(h->host, "document");
            if (cJSON_IsObject(d)) {
                cJSON *wrap = cJSON_CreateObject();
                char *p;
                cJSON_AddItemToObject(wrap, "data", cJSON_Duplicate(d, 1));
                p = cJSON_PrintUnformatted(wrap);
                snprintf(result_json, result_cap, "%s", p);
                free(p);
                cJSON_Delete(wrap);
                return 0;
            }
        }
    }
    return uem_default_outward(NULL, effect, source_json, result_json, result_cap, err, errlen);
}

static void usage(const char *argv0) {
    fprintf(stderr,
            "UEM-16 C99 interpreter (registry v%d)\n"
            "Usage:\n"
            "  %s version\n"
            "  %s verify <program.uem>\n"
            "  %s run <program.uem> --host '<json>'\n"
            "  %s sha <program.uem>\n",
            UEM_REGISTRY_VERSION, argv0, argv0, argv0, argv0);
}

int main(int argc, char **argv) {
    char err[256];
    if (argc < 2) { usage(argv[0]); return 2; }
    if (strcmp(argv[1], "version") == 0) {
        printf("uem-c UEM-16 format=%d registry=%d\n", UEM_FORMAT_VERSION, UEM_REGISTRY_VERSION);
        return 0;
    }
    if (argc < 3) { usage(argv[0]); return 2; }
    {
        size_t len = 0;
        uint8_t *bytes = read_file(argv[2], &len);
        uem_machine *m = NULL;
        uem_status st;
        if (!bytes) {
            fprintf(stderr, "io: cannot read %s\n", argv[2]);
            return 1;
        }
        st = uem_decode_verify(bytes, len, &m, err, sizeof err);
        if (strcmp(argv[1], "verify") == 0 || strcmp(argv[1], "sha") == 0) {
            free(bytes);
            if (st != UEM_OK) {
                printf("{\"ok\":false,\"error\":%s}\n", err[0] ? err : "decode");
                /* print JSON-safe */
                fprintf(stderr, "verify-fail: %s\n", err);
                return 1;
            }
            printf("{\"ok\":true,\"program_sha256\":\"%s\",\"instructions\":%u}\n",
                   uem_program_sha256(m), uem_instruction_count(m));
            uem_free(m);
            return 0;
        }
        if (strcmp(argv[1], "run") == 0) {
            const char *host = "{}";
            int i;
            host_ctx hc;
            char *out;
            for (i = 3; i < argc; i++) {
                if (strcmp(argv[i], "--host") == 0 && i + 1 < argc) host = argv[++i];
            }
            free(bytes);
            if (st != UEM_OK) {
                fprintf(stderr, "decode: %s\n", err);
                return 1;
            }
            if (uem_set_host_json(m, host, err, sizeof err) != UEM_OK) {
                fprintf(stderr, "host: %s\n", err);
                uem_free(m);
                return 1;
            }
            hc.host = cJSON_Parse(host);
            uem_set_outward_handler(m, host_outward, &hc);
            if (uem_run(m, err, sizeof err) != UEM_OK) {
                fprintf(stderr, "run: %s\n", err);
            }
            out = uem_result_json(m);
            if (out) {
                fputs(out, stdout);
                fputc('\n', stdout);
                free(out);
            }
            if (hc.host) cJSON_Delete(hc.host);
            uem_free(m);
            return 0;
        }
        free(bytes);
        usage(argv[0]);
        return 2;
    }
}
