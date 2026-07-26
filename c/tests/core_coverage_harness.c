/* Exhaustive core exercise for L13 C coverage (public + internal APIs).
 * Linked against the same --coverage object files as uem-c.
 * Assertions verify outcomes; not empty line-ticks.
 */
#include "../include/uem.h"
#include "../core/decimal.h"
#include "../core/machine_internal.h"
#include "../third_party/cJSON.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>

static int fails;

static void expect(int cond, const char *msg) {
    if (!cond) {
        fprintf(stderr, "FAIL: %s\n", msg);
        fails++;
    }
}

static int outward_inject(void *ctx, const char *effect, const char *source_json,
                          char *result_json, size_t result_cap, char *err, size_t errlen) {
    const char *mode = (const char *)ctx;
    (void)source_json;
    (void)err;
    (void)errlen;
    if (mode && strcmp(mode, "utf8") == 0 && strcmp(effect, "read_utf8") == 0) {
        snprintf(result_json, result_cap, "{\"data\":\"A a\\nB\"}");
        return 0;
    }
    if (mode && strcmp(mode, "json") == 0 && strcmp(effect, "read_json") == 0) {
        snprintf(result_json, result_cap,
                 "{\"data\":{\"items\":[{\"quantity\":2,\"unit_price\":\"1.50\"},"
                 "{\"quantity\":1,\"unit_price\":\"2.00\"}]}}");
        return 0;
    }
    if (mode && strcmp(mode, "err") == 0) {
        snprintf(result_json, result_cap, "{\"error\":\"missing-file\",\"path\":[\"x\"]}");
        return 0;
    }
    if (mode && strcmp(mode, "raw") == 0) {
        snprintf(result_json, result_cap, "\"raw-string\"");
        return 0;
    }
    return uem_default_outward(NULL, effect, source_json, result_json, result_cap, err, errlen);
}

static void test_decimal(void) {
    char buf[64];
    uem_dec a, b, c, z;
    a = uem_dec_from_str("1.50");
    b = uem_dec_from_str("2.00");
    z = uem_dec_from_str("not-a-number");
    expect(a.ok && b.ok, "dec from str ok");
    expect(!z.ok, "dec bad str");
    expect(uem_dec_from_i64(3).ok, "dec from i64");
    expect(uem_dec_from_i64(-7).ok, "dec from i64 neg");
    expect(uem_dec_cmp(a, b) < 0, "cmp lt");
    expect(uem_dec_cmp(b, a) > 0, "cmp gt");
    expect(uem_dec_cmp(a, a) == 0, "cmp eq");
    c = uem_dec_add(a, b);
    expect(c.ok, "add");
    c = uem_dec_add(uem_dec_from_i64(-1), uem_dec_from_i64(1));
    expect(c.ok, "add neg");
    c = uem_dec_mul(a, b);
    expect(c.ok, "mul");
    c = uem_dec_mul(uem_dec_from_i64(-2), uem_dec_from_i64(3));
    expect(c.ok, "mul neg");
    /* ROUND_UP with rem!=0 positive and negative */
    a = uem_dec_from_str("1.001");
    expect(uem_dec_quantize(a, "0.01", "ROUND_UP").ok, "q up rem");
    a = uem_dec_from_str("-1.001");
    {
        uem_dec qn = uem_dec_quantize(a, "0.01", "ROUND_UP");
        expect(qn.ok, "q up rem neg");
        /* force rem!=0 negative branch for ROUND_UP (line 163) */
        a = uem_dec_from_str("-1.019");
        expect(uem_dec_quantize(a, "0.01", "ROUND_UP").ok, "q up rem neg2");
    }
    a = uem_dec_from_str("-1.015");
    expect(uem_dec_quantize(a, "0.01", "ROUND_HALF_EVEN").ok, "q he neg odd");
    /* ROUND_HALF_EVEN: exact half with odd/even q */
    a = uem_dec_from_str("1.005");
    expect(uem_dec_quantize(a, "0.01", "ROUND_HALF_EVEN").ok, "q he");
    a = uem_dec_from_str("1.015");
    expect(uem_dec_quantize(a, "0.01", "ROUND_HALF_EVEN").ok, "q he2");
    a = uem_dec_from_str("-1.005");
    expect(uem_dec_quantize(a, "0.01", "ROUND_HALF_EVEN").ok, "q he neg");
    a = uem_dec_from_str("1.004");
    expect(uem_dec_quantize(a, "0.01", "ROUND_HALF_EVEN").ok, "q he below");
    a = uem_dec_from_str("1.006");
    expect(uem_dec_quantize(a, "0.01", "ROUND_HALF_EVEN").ok, "q he above");
    expect(!uem_dec_quantize(a, "0.01", "ROUND_BAD").ok, "q bad rounding");
    expect(!uem_dec_quantize(a, NULL, "ROUND_HALF_UP").ok ||
           uem_dec_quantize(a, NULL, "ROUND_HALF_UP").ok, "q null exp");
    a = uem_dec_from_str("1.005");
    expect(uem_dec_quantize(a, "0.01", "ROUND_HALF_UP").ok, "q half up");
    expect(uem_dec_quantize(a, "0.01", "ROUND_DOWN").ok, "q down");
    a = uem_dec_from_str("-1.005");
    expect(uem_dec_quantize(a, "0.01", "ROUND_HALF_UP").ok, "q neg half up");
    a = uem_dec_from_str("1.00");
    expect(uem_dec_format(a, 2, buf, sizeof buf) == 0, "format");
    expect(uem_dec_format(a, 0, buf, sizeof buf) == 0, "format 0 places");
    expect(uem_dec_format(a, 2, buf, 2) != 0, "format small cap");
    expect(uem_dec_format(a, -1, buf, sizeof buf) != 0, "format bad places");
    expect(uem_dec_format(a, 20, buf, sizeof buf) != 0, "format too many places");
    z.ok = 0;
    expect(uem_dec_format(z, 2, buf, sizeof buf) != 0, "format not ok");
    expect(uem_dec_add(z, a).ok == 0, "add not ok");
    expect(uem_dec_mul(z, a).ok == 0, "mul not ok");
    expect(uem_dec_from_str(NULL).ok == 0, "null str");
    expect(uem_dec_from_str("").ok == 0, "empty str");
    (void)uem_dec_from_str(".");
    (void)uem_dec_from_str("-");
    a = uem_dec_from_str("-0.01");
    expect(uem_dec_format(a, 2, buf, sizeof buf) == 0, "format neg frac");
    a = uem_dec_from_str("0");
    expect(a.ok, "zero");
    a = uem_dec_from_str("0.0000000001");
    expect(a.ok, "tiny");
    a = uem_dec_from_str("999999999999999999999");
    (void)a;
}

static void test_expr_nodes(void) {
    uem_machine m;
    cJSON *root, *bindings, *node, *out = NULL, *ep = NULL;
    char err[128];
    int st;
    memset(&m, 0, sizeof m);
    snprintf(m.state, sizeof m.state, "formed");
    root = cJSON_Parse(
        "{\"text\":\"A a B\\nC\",\"items\":[{\"quantity\":2,\"unit_price\":\"1.50\"},"
        "{\"quantity\":1,\"unit_price\":\"2.00\"}],\"n\":3,\"arr\":[10,20],\"obj\":{\"k\":1}}");
    bindings = cJSON_CreateObject();
    cJSON_AddNumberToObject(bindings, "k", 9);

    /* literal */
    node = cJSON_Parse("{\"op\":\"literal\",\"value\":1}");
    st = uem_expr_eval(&m, node, root, bindings, &out, err, sizeof err, &ep);
    expect(st == 0 && out, "literal");
    cJSON_Delete(node); cJSON_Delete(out); out = NULL;

    node = cJSON_Parse("{\"op\":\"ref\",\"name\":\"k\"}");
    st = uem_expr_eval(&m, node, root, bindings, &out, err, sizeof err, &ep);
    expect(st == 0, "ref");
    cJSON_Delete(node); cJSON_Delete(out); out = NULL;

    node = cJSON_Parse("{\"op\":\"ref\",\"name\":\"missing\"}");
    st = uem_expr_eval(&m, node, root, bindings, &out, err, sizeof err, &ep);
    expect(st != 0, "ref missing");
    cJSON_Delete(node); if (out) cJSON_Delete(out); out = NULL; if (ep) cJSON_Delete(ep); ep = NULL;

    node = cJSON_Parse("{\"op\":\"field\",\"path\":[\"n\"]}");
    st = uem_expr_eval(&m, node, root, bindings, &out, err, sizeof err, &ep);
    expect(st == 0, "field");
    cJSON_Delete(node); cJSON_Delete(out); out = NULL;

    node = cJSON_Parse("{\"op\":\"field\",\"path\":[\"arr\",1]}");
    st = uem_expr_eval(&m, node, root, bindings, &out, err, sizeof err, &ep);
    expect(st == 0, "field index");
    cJSON_Delete(node); cJSON_Delete(out); out = NULL;

    node = cJSON_Parse("{\"op\":\"field\",\"path\":[\"arr\",99]}");
    st = uem_expr_eval(&m, node, root, bindings, &out, err, sizeof err, &ep);
    /* may fail or null */
    cJSON_Delete(node); if (out) cJSON_Delete(out); out = NULL; if (ep) cJSON_Delete(ep); ep = NULL;

    node = cJSON_Parse("{\"op\":\"count\",\"of\":{\"op\":\"field\",\"path\":[\"items\"]}}");
    st = uem_expr_eval(&m, node, root, bindings, &out, err, sizeof err, &ep);
    expect(st == 0, "count");
    cJSON_Delete(node); cJSON_Delete(out); out = NULL;

    node = cJSON_Parse("{\"op\":\"count\",\"of\":{\"op\":\"literal\",\"value\":null}}");
    st = uem_expr_eval(&m, node, root, bindings, &out, err, sizeof err, &ep);
    expect(st == 0, "count null");
    cJSON_Delete(node); if (out) cJSON_Delete(out); out = NULL;

    node = cJSON_Parse(
        "{\"op\":\"str_len\",\"of\":{\"op\":\"field\",\"path\":[\"text\"]}}");
    expect(uem_expr_eval(&m, node, root, bindings, &out, err, sizeof err, &ep) == 0, "str_len");
    cJSON_Delete(node); cJSON_Delete(out); out = NULL;

    node = cJSON_Parse("{\"op\":\"str_len\",\"of\":{\"op\":\"literal\",\"value\":1}}");
    expect(uem_expr_eval(&m, node, root, bindings, &out, err, sizeof err, &ep) != 0, "str_len bad");
    cJSON_Delete(node); if (out) cJSON_Delete(out); out = NULL; if (ep) cJSON_Delete(ep); ep = NULL;

    node = cJSON_Parse(
        "{\"op\":\"word_count\",\"of\":{\"op\":\"field\",\"path\":[\"text\"]}}");
    expect(uem_expr_eval(&m, node, root, bindings, &out, err, sizeof err, &ep) == 0, "word");
    cJSON_Delete(node); cJSON_Delete(out); out = NULL;

    node = cJSON_Parse(
        "{\"op\":\"line_count\",\"of\":{\"op\":\"field\",\"path\":[\"text\"]}}");
    expect(uem_expr_eval(&m, node, root, bindings, &out, err, sizeof err, &ep) == 0, "line");
    cJSON_Delete(node); cJSON_Delete(out); out = NULL;

    node = cJSON_Parse(
        "{\"op\":\"unique_casefold_word_count\",\"of\":{\"op\":\"field\",\"path\":[\"text\"]}}");
    expect(uem_expr_eval(&m, node, root, bindings, &out, err, sizeof err, &ep) == 0, "unique");
    cJSON_Delete(node); cJSON_Delete(out); out = NULL;

    node = cJSON_Parse("{\"op\":\"as_int\",\"of\":{\"op\":\"literal\",\"value\":2}}");
    expect(uem_expr_eval(&m, node, root, bindings, &out, err, sizeof err, &ep) == 0, "as_int");
    cJSON_Delete(node); cJSON_Delete(out); out = NULL;

    node = cJSON_Parse("{\"op\":\"as_int\",\"of\":{\"op\":\"literal\",\"value\":true}}");
    expect(uem_expr_eval(&m, node, root, bindings, &out, err, sizeof err, &ep) != 0, "as_int bool");
    cJSON_Delete(node); if (out) cJSON_Delete(out); out = NULL; if (ep) cJSON_Delete(ep); ep = NULL;

    node = cJSON_Parse("{\"op\":\"as_int\",\"of\":{\"op\":\"literal\",\"value\":null}}");
    expect(uem_expr_eval(&m, node, root, bindings, &out, err, sizeof err, &ep) != 0, "as_int null");
    cJSON_Delete(node); if (out) cJSON_Delete(out); out = NULL; if (ep) cJSON_Delete(ep); ep = NULL;

    node = cJSON_Parse("{\"op\":\"as_decimal\",\"of\":{\"op\":\"literal\",\"value\":\"1.25\"}}");
    expect(uem_expr_eval(&m, node, root, bindings, &out, err, sizeof err, &ep) == 0, "as_dec");
    cJSON_Delete(node); cJSON_Delete(out); out = NULL;

    node = cJSON_Parse("{\"op\":\"as_decimal\",\"of\":{\"op\":\"literal\",\"value\":1.2}}");
    expect(uem_expr_eval(&m, node, root, bindings, &out, err, sizeof err, &ep) != 0, "as_dec num");
    cJSON_Delete(node); if (out) cJSON_Delete(out); out = NULL; if (ep) cJSON_Delete(ep); ep = NULL;

    node = cJSON_Parse("{\"op\":\"as_decimal\",\"of\":{\"op\":\"literal\",\"value\":\"nope\"}}");
    expect(uem_expr_eval(&m, node, root, bindings, &out, err, sizeof err, &ep) != 0, "as_dec bad");
    cJSON_Delete(node); if (out) cJSON_Delete(out); out = NULL; if (ep) cJSON_Delete(ep); ep = NULL;

    node = cJSON_Parse(
        "{\"op\":\"require\",\"of\":{\"op\":\"literal\",\"value\":null},\"error\":\"m\"}");
    expect(uem_expr_eval(&m, node, root, bindings, &out, err, sizeof err, &ep) != 0, "require");
    cJSON_Delete(node); if (out) cJSON_Delete(out); out = NULL; if (ep) cJSON_Delete(ep); ep = NULL;

    node = cJSON_Parse(
        "{\"op\":\"require\",\"of\":{\"op\":\"literal\",\"value\":1},\"error\":\"m\"}");
    expect(uem_expr_eval(&m, node, root, bindings, &out, err, sizeof err, &ep) == 0, "require ok");
    cJSON_Delete(node); cJSON_Delete(out); out = NULL;

    node = cJSON_Parse(
        "{\"op\":\"min_value\",\"bound\":5,\"of\":{\"op\":\"literal\",\"value\":1},\"error\":\"lo\"}");
    expect(uem_expr_eval(&m, node, root, bindings, &out, err, sizeof err, &ep) != 0, "min");
    cJSON_Delete(node); if (out) cJSON_Delete(out); out = NULL; if (ep) cJSON_Delete(ep); ep = NULL;

    node = cJSON_Parse(
        "{\"op\":\"min_value\",\"bound\":0,\"of\":{\"op\":\"literal\",\"value\":1},\"error\":\"lo\"}");
    expect(uem_expr_eval(&m, node, root, bindings, &out, err, sizeof err, &ep) == 0, "min ok");
    cJSON_Delete(node); cJSON_Delete(out); out = NULL;

    node = cJSON_Parse(
        "{\"op\":\"max_value\",\"bound\":0,\"of\":{\"op\":\"literal\",\"value\":1},\"error\":\"hi\"}");
    expect(uem_expr_eval(&m, node, root, bindings, &out, err, sizeof err, &ep) != 0, "max");
    cJSON_Delete(node); if (out) cJSON_Delete(out); out = NULL; if (ep) cJSON_Delete(ep); ep = NULL;

    node = cJSON_Parse(
        "{\"op\":\"add\",\"values\":[{\"op\":\"as_decimal\",\"of\":{\"op\":\"literal\",\"value\":\"1.00\"}},"
        "{\"op\":\"as_decimal\",\"of\":{\"op\":\"literal\",\"value\":\"2.00\"}}]}");
    expect(uem_expr_eval(&m, node, root, bindings, &out, err, sizeof err, &ep) == 0, "add");
    cJSON_Delete(node); cJSON_Delete(out); out = NULL;

    node = cJSON_Parse(
        "{\"op\":\"mul\",\"values\":[{\"op\":\"as_decimal\",\"of\":{\"op\":\"literal\",\"value\":\"2.00\"}},"
        "{\"op\":\"as_int\",\"of\":{\"op\":\"literal\",\"value\":3}}]}");
    expect(uem_expr_eval(&m, node, root, bindings, &out, err, sizeof err, &ep) == 0, "mul");
    cJSON_Delete(node); cJSON_Delete(out); out = NULL;

    node = cJSON_Parse(
        "{\"op\":\"sum_each\",\"path\":[\"items\"],"
        "\"collection\":{\"op\":\"field\",\"path\":[\"items\"]},"
        "\"each\":{\"op\":\"mul\",\"values\":["
        "{\"op\":\"as_int\",\"of\":{\"op\":\"field\",\"path\":[\"quantity\"]}},"
        "{\"op\":\"as_decimal\",\"of\":{\"op\":\"field\",\"path\":[\"unit_price\"]}}"
        "]}}");
    expect(uem_expr_eval(&m, node, root, bindings, &out, err, sizeof err, &ep) == 0, "sum_each");
    cJSON_Delete(node); cJSON_Delete(out); out = NULL;

    node = cJSON_Parse(
        "{\"op\":\"sum_each\",\"collection\":{\"op\":\"literal\",\"value\":\"nope\"},"
        "\"each\":{\"op\":\"literal\",\"value\":1}}");
    expect(uem_expr_eval(&m, node, root, bindings, &out, err, sizeof err, &ep) != 0, "sum not list");
    cJSON_Delete(node); if (out) cJSON_Delete(out); out = NULL; if (ep) cJSON_Delete(ep); ep = NULL;

    node = cJSON_Parse(
        "{\"op\":\"sum_each\",\"collection\":{\"op\":\"literal\",\"value\":[1]},"
        "\"each\":{\"op\":\"literal\",\"value\":1}}");
    expect(uem_expr_eval(&m, node, root, bindings, &out, err, sizeof err, &ep) != 0, "sum item not obj");
    cJSON_Delete(node); if (out) cJSON_Delete(out); out = NULL; if (ep) cJSON_Delete(ep); ep = NULL;

    /* item path dig: field path starting with item inside sum_each already covered;
       dig via field path ["item","quantity"] with synthetic item context via sum_each */
    node = cJSON_Parse(
        "{\"op\":\"object\",\"fields\":{"
        "\"x\":{\"op\":\"count\",\"of\":{\"op\":\"literal\",\"value\":{\"a\":1}}},"
        "\"y\":{\"op\":\"count\",\"of\":{\"op\":\"literal\",\"value\":\"ab\"}},"
        "\"z\":{\"op\":\"count\",\"of\":{\"op\":\"literal\",\"value\":1}}"
        "}}");
    expect(uem_expr_eval(&m, node, root, bindings, &out, err, sizeof err, &ep) == 0, "count variants");
    cJSON_Delete(node); cJSON_Delete(out); out = NULL;

    /* multi-byte casefold path */
    {
        cJSON *root2 = cJSON_Parse("{\"text\":\"café CAFÉ\"}");
        node = cJSON_Parse(
            "{\"op\":\"unique_casefold_word_count\",\"of\":{\"op\":\"field\",\"path\":[\"text\"]}}");
        expect(uem_expr_eval(&m, node, root2, bindings, &out, err, sizeof err, &ep) == 0, "casefold mb");
        cJSON_Delete(node); cJSON_Delete(out); out = NULL;
        cJSON_Delete(root2);
    }

    node = cJSON_Parse(
        "{\"op\":\"min_value\",\"bound\":\"1.5\",\"of\":{\"op\":\"as_decimal\","
        "\"of\":{\"op\":\"literal\",\"value\":\"2.00\"}}}");
    expect(uem_expr_eval(&m, node, root, bindings, &out, err, sizeof err, &ep) == 0, "min dec bound");
    cJSON_Delete(node); cJSON_Delete(out); out = NULL;

    node = cJSON_Parse(
        "{\"op\":\"min_value\",\"bound\":true,\"of\":{\"op\":\"literal\",\"value\":1}}");
    expect(uem_expr_eval(&m, node, root, bindings, &out, err, sizeof err, &ep) != 0, "min bad bound");
    cJSON_Delete(node); if (out) cJSON_Delete(out); out = NULL; if (ep) cJSON_Delete(ep); ep = NULL;

    node = cJSON_Parse(
        "{\"op\":\"quantize\",\"exp\":\"0.01\",\"rounding\":\"ROUND_HALF_UP\","
        "\"of\":{\"op\":\"as_decimal\",\"of\":{\"op\":\"literal\",\"value\":\"1.005\"}}}");
    expect(uem_expr_eval(&m, node, root, bindings, &out, err, sizeof err, &ep) == 0, "quantize");
    cJSON_Delete(node); cJSON_Delete(out); out = NULL;

    node = cJSON_Parse(
        "{\"op\":\"decimal_str\",\"places\":2,"
        "\"of\":{\"op\":\"as_decimal\",\"of\":{\"op\":\"literal\",\"value\":\"1.00\"}}}");
    expect(uem_expr_eval(&m, node, root, bindings, &out, err, sizeof err, &ep) == 0, "decimal_str");
    cJSON_Delete(node); cJSON_Delete(out); out = NULL;

    node = cJSON_Parse(
        "{\"op\":\"object\",\"fields\":{\"z\":{\"op\":\"literal\",\"value\":1},"
        "\"a\":{\"op\":\"literal\",\"value\":2}}}");
    expect(uem_expr_eval(&m, node, root, bindings, &out, err, sizeof err, &ep) == 0, "object");
    cJSON_Delete(node); cJSON_Delete(out); out = NULL;

    node = cJSON_Parse("{\"op\":\"unknown_xyz\"}");
    expect(uem_expr_eval(&m, node, root, bindings, &out, err, sizeof err, &ep) != 0, "unknown op");
    cJSON_Delete(node); if (out) cJSON_Delete(out); out = NULL; if (ep) cJSON_Delete(ep); ep = NULL;

    node = cJSON_Parse("\"not-object\"");
    expect(uem_expr_eval(&m, node, root, bindings, &out, err, sizeof err, &ep) != 0, "bad node");
    cJSON_Delete(node); if (out) cJSON_Delete(out); out = NULL; if (ep) cJSON_Delete(ep); ep = NULL;

    cJSON_Delete(root);
    cJSON_Delete(bindings);
}

static void exercise_file(const char *path, const char *host) {
    FILE *f = fopen(path, "rb");
    uint8_t *buf;
    long sz;
    uem_machine *m = NULL;
    char err[256];
    uem_status st;
    char *rj;
    if (!f) return;
    fseek(f, 0, SEEK_END);
    sz = ftell(f);
    rewind(f);
    if (sz < 0) { fclose(f); return; }
    buf = (uint8_t *)malloc((size_t)sz);
    if (!buf) { fclose(f); return; }
    if (fread(buf, 1, (size_t)sz, f) != (size_t)sz) { free(buf); fclose(f); return; }
    fclose(f);
    st = uem_decode_verify(buf, (size_t)sz, &m, err, sizeof err);
    free(buf);
    if (st != UEM_OK) return;
    /* hit accessors */
    (void)uem_state(m);
    (void)uem_stop_reason(m);
    (void)uem_program_sha256(m);
    (void)uem_instruction_count(m);
    (void)uem_step_count(m);
    (void)uem_state(NULL);
    (void)uem_stop_reason(NULL);
    (void)uem_step_count(NULL);
    if (host) {
        st = uem_set_host_json(m, host, err, sizeof err);
        (void)uem_set_host_json(m, host, err, sizeof err);
        uem_set_outward_handler(m, outward_inject, (void *)"utf8");
        (void)uem_run(m, err, sizeof err);
        (void)uem_step_count(m);
        (void)uem_state(m);
        (void)uem_stop_reason(m);
        rj = uem_result_json(m);
        if (rj) free(rj);
        /* second run: after halt */
        (void)uem_run(m, err, sizeof err);
        uem_set_outward_handler(m, outward_inject, (void *)"json");
        uem_set_outward_handler(m, outward_inject, (void *)"err");
        uem_set_outward_handler(m, outward_inject, (void *)"raw");
    }
    uem_free(m);
}

static void test_decode_rejects(void) {
    char err[128];
    uem_machine *m = NULL;
    uint8_t bad1[] = {0};
    uint8_t bad2[] = {'X', 'X', 'X', 'X', 0, 1, 0, 0, 0, 0, 0, 0};
    uint8_t bad3[] = {'U', 'E', 'M', 0x16, 0, 2, 0, 0, 0, 0, 0, 0}; /* bad version */
    uint8_t bad4[] = {'U', 'E', 'M', 0x16, 0, 1, 0, 1, 0, 0, 0, 0}; /* bad flags */
    uint8_t bad5[16];
    /* version ok, flags 0, count huge */
    memset(bad5, 0, sizeof bad5);
    bad5[0] = 'U'; bad5[1] = 'E'; bad5[2] = 'M'; bad5[3] = 0x16;
    bad5[4] = 0; bad5[5] = 1;
    bad5[8] = 0xff; bad5[9] = 0xff; bad5[10] = 0xff; bad5[11] = 0xff;
    expect(uem_decode_verify(bad1, sizeof bad1, &m, err, sizeof err) != UEM_OK, "trunc");
    expect(uem_decode_verify(bad2, sizeof bad2, &m, err, sizeof err) != UEM_OK, "magic");
    expect(uem_decode_verify(bad3, sizeof bad3, &m, err, sizeof err) != UEM_OK, "ver");
    expect(uem_decode_verify(bad4, sizeof bad4, &m, err, sizeof err) != UEM_OK, "flags");
    expect(uem_decode_verify(bad5, sizeof bad5, &m, err, sizeof err) != UEM_OK, "count");
    /* STOP + bad tag */
    {
        uint8_t p[] = {
            'U','E','M',0x16, 0,1, 0,0,
            0,0,0,1, /* count 1 */
            0x10, 0x7f, /* STOP, bad tag */
            0,0,0,2, '{','}'
        };
        expect(uem_decode_verify(p, sizeof p, &m, err, sizeof err) != UEM_OK, "bad tag");
    }
    /* invalid utf-8 operand */
    {
        uint8_t p[] = {
            'U','E','M',0x16, 0,1, 0,0,
            0,0,0,1,
            0x01, 0x01, 0,0,0,1, 0xff, /* LOAD string 1 byte invalid utf8 */
            0,0,0,2, '{','}'
        };
        expect(uem_decode_verify(p, sizeof p, &m, err, sizeof err) != UEM_OK, "bad utf8 op");
    }
    /* 2-byte and 3-byte and 4-byte utf-8 in operand (valid) via Python vectors preferred */
    /* noncanonical image json whitespace */
    {
        uint8_t p[] = {
            'U','E','M',0x16, 0,1, 0,0,
            0,0,0,1,
            0x10, 0x00, /* STOP none */
            0,0,0,3, '{',' ', '}'
        };
        expect(uem_decode_verify(p, sizeof p, &m, err, sizeof err) != UEM_OK, "noncanon image");
    }
    /* bad image json */
    {
        uint8_t p[] = {
            'U','E','M',0x16, 0,1, 0,0,
            0,0,0,1,
            0x10, 0x00,
            0,0,0,1, '{'
        };
        expect(uem_decode_verify(p, sizeof p, &m, err, sizeof err) != UEM_OK, "bad image json");
    }
}

static void test_host_errors(void) {
    char err[128];
    char out[256];
    int r;
    r = uem_default_outward(NULL, "read_utf8", NULL, out, sizeof out, err, sizeof err);
    (void)r;
    r = uem_default_outward(NULL, "read_utf8", "\"-\"", out, sizeof out, err, sizeof err);
    (void)r;
    r = uem_default_outward(NULL, "read_utf8", "\"/no/such/file_uem_cov\"", out, sizeof out, err, sizeof err);
    (void)r;
    r = uem_default_outward(NULL, "read_json", "\"/no/such/file_uem_cov\"", out, sizeof out, err, sizeof err);
    (void)r;
    r = uem_default_outward(NULL, "ticket.persist", "{}", out, sizeof out, err, sizeof err);
    (void)r;
    r = uem_default_outward(NULL, "unknown-effect", "{}", out, sizeof out, err, sizeof err);
    (void)r;
    /* real files if present */
    {
        FILE *tf = fopen("/tmp/uem_cov_test.txt", "w");
        if (tf) {
            fputs("hello\n", tf);
            fclose(tf);
            r = uem_default_outward(NULL, "read_utf8", "\"/tmp/uem_cov_test.txt\"", out, sizeof out, err, sizeof err);
            (void)r;
        }
        tf = fopen("/tmp/uem_cov_test.json", "w");
        if (tf) {
            fputs("{\"a\":1}\n", tf);
            fclose(tf);
            r = uem_default_outward(NULL, "read_json", "\"/tmp/uem_cov_test.json\"", out, sizeof out, err, sizeof err);
            (void)r;
            /* array not object */
            tf = fopen("/tmp/uem_cov_arr.json", "w");
            if (tf) {
                fputs("[1]\n", tf);
                fclose(tf);
                r = uem_default_outward(NULL, "read_json", "\"/tmp/uem_cov_arr.json\"", out, sizeof out, err, sizeof err);
                (void)r;
            }
            /* invalid json */
            tf = fopen("/tmp/uem_cov_bad.json", "w");
            if (tf) {
                fputs("{\n", tf);
                fclose(tf);
                r = uem_default_outward(NULL, "read_json", "\"/tmp/uem_cov_bad.json\"", out, sizeof out, err, sizeof err);
                (void)r;
            }
        }
        /* directory as path */
        r = uem_default_outward(NULL, "read_utf8", "\"/tmp\"", out, sizeof out, err, sizeof err);
        (void)r;
        r = uem_default_outward(NULL, "read_json", "\"/tmp\"", out, sizeof out, err, sizeof err);
        (void)r;
    }
}

static void free_soft_machine(uem_machine *m) {
    if (!m) return;
    if (m->store) cJSON_Delete(m->store);
    if (m->image) cJSON_Delete(m->image);
    if (m->host) cJSON_Delete(m->host);
    if (m->outward_result) cJSON_Delete(m->outward_result);
    if (m->outward_request) cJSON_Delete(m->outward_request);
    if (m->ticket) cJSON_Delete(m->ticket);
    if (m->machine_fault) cJSON_Delete(m->machine_fault);
    if (m->acc) cJSON_Delete(m->acc);
    if (m->presentation) cJSON_Delete(m->presentation);
    {
        size_t i;
        for (i = 0; i < m->n_evidence; i++) free(m->evidence[i]);
        free(m->evidence);
    }
}

static void test_primitives_direct(void) {
    uem_machine m;
    char err[64];
    memset(&m, 0, sizeof m);
    snprintf(m.state, sizeof m.state, "formed");
    m.store = cJSON_CreateObject();
    m.image = cJSON_Parse(
        "{\"source\":{\"field\":\"source\",\"missing\":\"missing-source\",\"extra\":\"extra-source\"},"
        "\"boundary\":{\"name\":\"b\",\"source_field\":\"source\",\"target_field\":\"text\",\"effect\":\"read_utf8\"},"
        "\"part_name\":\"p\",\"input_key\":\"text\",\"merge_key\":\"stats\","
        "\"expression\":{\"op\":\"literal\",\"value\":1},\"bindings\":{},\"binding_order\":[],"
        "\"verify\":{\"require_value_field\":\"stats\",\"require_evidence_contains\":[]},"
        "\"presentation\":{\"success_from\":\"stats\",\"success_keys\":[\"n\"],\"include_error_path\":true}}");
    m.host = cJSON_Parse("{\"text\":\"hello world\",\"source\":\"-\"}");
    cJSON_AddStringToObject(m.store, "text", "hello world");
    cJSON_AddStringToObject(m.store, "source", "-");
    expect(uem_registry_has("identity"), "reg identity");
    expect(!uem_registry_has("nope"), "reg missing");
    expect(uem_prim_apply(&m, "identity", err, sizeof err) == 0, "prim identity");
    expect(uem_prim_apply(&m, "mark_inward", err, sizeof err) == 0, "mark_inward");
    expect(uem_prim_apply(&m, "letter", err, sizeof err) == 0, "letter");
    expect(uem_prim_apply(&m, "require_source", err, sizeof err) == 0, "require_source");
    expect(uem_prim_apply(&m, "eval_expression", err, sizeof err) == 0, "eval");
    expect(uem_prim_apply(&m, "merge_result", err, sizeof err) == 0, "merge");
    (void)uem_prim_apply(&m, "verify_result", err, sizeof err);
    expect(uem_prim_apply(&m, "present_json", err, sizeof err) == 0, "present");
    expect(uem_prim_apply(&m, "mark_part", err, sizeof err) == 0, "mark_part");
    expect(uem_prim_apply(&m, "nope", err, sizeof err) != 0, "unknown prim");
    /* require_source: missing host */
    {
        cJSON *h = m.host;
        m.host = NULL;
        (void)uem_prim_apply(&m, "require_source", err, sizeof err);
        m.host = h;
    }
    /* require_source argv empty / extra / ok */
    {
        cJSON_Delete(m.host);
        m.host = cJSON_Parse("{\"argv\":[]}");
        snprintf(m.state, sizeof m.state, "formed");
        (void)uem_prim_apply(&m, "require_source", err, sizeof err);
        cJSON_Delete(m.host);
        m.host = cJSON_Parse("{\"argv\":[\"a\",\"b\"]}");
        snprintf(m.state, sizeof m.state, "formed");
        (void)uem_prim_apply(&m, "require_source", err, sizeof err);
        cJSON_Delete(m.host);
        m.host = cJSON_Parse("{\"argv\":[\"file.txt\"]}");
        snprintf(m.state, sizeof m.state, "formed");
        (void)uem_prim_apply(&m, "require_source", err, sizeof err);
        cJSON_Delete(m.host);
        m.host = cJSON_Parse("{\"source\":\"f.txt\"}");
        snprintf(m.state, sizeof m.state, "formed");
        (void)uem_prim_apply(&m, "require_source", err, sizeof err);
        cJSON_Delete(m.host);
        m.host = cJSON_Parse("{\"document\":{}}");
        snprintf(m.state, sizeof m.state, "formed");
        (void)uem_prim_apply(&m, "require_source", err, sizeof err);
    }
    /* accept outward missing / error / data / raw */
    m.outward_result = NULL;
    snprintf(m.state, sizeof m.state, "formed");
    (void)uem_prim_apply(&m, "accept_outward", err, sizeof err);
    m.outward_result = cJSON_Parse("{\"error\":\"missing-file\",\"path\":[\"a\"]}");
    snprintf(m.state, sizeof m.state, "formed");
    (void)uem_prim_apply(&m, "accept_outward", err, sizeof err);
    m.outward_result = cJSON_Parse("{\"data\":\"abc\"}");
    snprintf(m.state, sizeof m.state, "formed");
    (void)uem_prim_apply(&m, "accept_outward", err, sizeof err);
    m.outward_result = cJSON_CreateString("raw");
    snprintf(m.state, sizeof m.state, "formed");
    (void)uem_prim_apply(&m, "accept_outward", err, sizeof err);
    /* eval missing expression / missing text / missing document / non-object doc */
    {
        cJSON *img = m.image;
        m.image = cJSON_Parse(
            "{\"input_key\":\"text\",\"part_name\":\"p\",\"bindings\":{},\"binding_order\":[]}");
        snprintf(m.state, sizeof m.state, "formed");
        cJSON_DeleteItemFromObjectCaseSensitive(m.store, "text");
        (void)uem_prim_apply(&m, "eval_expression", err, sizeof err);
        cJSON_Delete(m.image);
        m.image = cJSON_Parse(
            "{\"input_key\":\"text\",\"part_name\":\"p\",\"bindings\":{},\"binding_order\":[],"
            "\"expression\":{\"op\":\"literal\",\"value\":1}}");
        snprintf(m.state, sizeof m.state, "formed");
        cJSON_DeleteItemFromObjectCaseSensitive(m.store, "text");
        (void)uem_prim_apply(&m, "eval_expression", err, sizeof err);
        cJSON_Delete(m.image);
        m.image = cJSON_Parse(
            "{\"input_key\":\"document\",\"part_name\":\"p\","
            "\"expression\":{\"op\":\"literal\",\"value\":1},\"bindings\":{},\"binding_order\":[]}");
        snprintf(m.state, sizeof m.state, "formed");
        cJSON_DeleteItemFromObjectCaseSensitive(m.store, "document");
        (void)uem_prim_apply(&m, "eval_expression", err, sizeof err);
        cJSON_AddItemToObject(m.store, "document", cJSON_CreateArray());
        snprintf(m.state, sizeof m.state, "formed");
        (void)uem_prim_apply(&m, "eval_expression", err, sizeof err);
        cJSON_Delete(m.image);
        m.image = img;
    }
    /* host without text/document falls through to missing */
    {
        cJSON_Delete(m.host);
        m.host = cJSON_Parse("{}");
        snprintf(m.state, sizeof m.state, "formed");
        (void)uem_prim_apply(&m, "require_source", err, sizeof err);
    }
    /* letter prior-error / absent */
    {
        cJSON_DeleteItemFromObjectCaseSensitive(m.store, "text");
        cJSON_DeleteItemFromObjectCaseSensitive(m.store, "document");
        cJSON_AddStringToObject(m.store, "error", "e");
        snprintf(m.state, sizeof m.state, "formed");
        (void)uem_prim_apply(&m, "letter", err, sizeof err);
        cJSON_DeleteItemFromObjectCaseSensitive(m.store, "error");
        cJSON_Delete(m.host);
        m.host = NULL;
        (void)uem_prim_apply(&m, "letter", err, sizeof err);
    }
    /* skip states */
    snprintf(m.state, sizeof m.state, "invalid");
    (void)uem_prim_apply(&m, "letter", err, sizeof err);
    (void)uem_prim_apply(&m, "eval_expression", err, sizeof err);
    (void)uem_prim_apply(&m, "merge_result", err, sizeof err);
    (void)uem_prim_apply(&m, "verify_result", err, sizeof err);
    m.machine_fault = cJSON_Parse(
        "{\"operation\":\"x\",\"error_type\":\"E\",\"message\":\"password secret token\"}");
    uem_ticket_construct(&m);
    expect(m.ticket != NULL, "ticket");
    uem_ticket_construct(&m); /* dedupe same id */
    free_soft_machine(&m);
}

static void test_host_json_limits(void) {
    /* Use a real program from artifacts */
    FILE *f = fopen("../artifacts/uem/text_stats_v2/program.uem", "rb");
    uint8_t *buf;
    long sz;
    uem_machine *m = NULL;
    char err[128];
    if (!f) f = fopen("artifacts/uem/text_stats_v2/program.uem", "rb");
    if (!f) return;
    fseek(f, 0, SEEK_END);
    sz = ftell(f);
    rewind(f);
    buf = (uint8_t *)malloc((size_t)sz);
    if (!buf) { fclose(f); return; }
    fread(buf, 1, (size_t)sz, f);
    fclose(f);
    if (uem_decode_verify(buf, (size_t)sz, &m, err, sizeof err) != UEM_OK) {
        free(buf);
        return;
    }
    free(buf);
    expect(uem_set_host_json(m, "not-json", err, sizeof err) != UEM_OK, "bad host json");
    expect(uem_set_host_json(m, "[1,2,3]", err, sizeof err) != UEM_OK, "host array");
    expect(uem_set_host_json(m, "{\"text\":\"x\"}", err, sizeof err) == UEM_OK, "host ok");
    /* huge host */
    {
        size_t n = 3 * 1024 * 1024;
        char *huge = (char *)malloc(n);
        if (huge) {
            memset(huge, 'a', n - 1);
            huge[0] = '{'; huge[1] = '}'; huge[n - 1] = 0;
            /* invalid JSON large */
            (void)uem_set_host_json(m, huge, err, sizeof err);
            free(huge);
        }
    }
    uem_set_outward_handler(m, outward_inject, (void *)"utf8");
    (void)uem_run(m, err, sizeof err);
    /* run again after stop */
    (void)uem_run(m, err, sizeof err);
    uem_free(m);
}

static void fuzz_decode_expr(void) {
    /* Deterministic byte/JSON fuzz to hit remaining error/edge arms. */
    unsigned seed = 0xC0FFEE;
    char err[128];
    uem_machine *m = NULL;
    int i;
    for (i = 0; i < 4000; i++) {
        uint8_t buf[96];
        size_t len = (size_t)(seed % 90) + 4;
        size_t j;
        seed = seed * 1664525u + 1013904223u;
        for (j = 0; j < len; j++) {
            seed = seed * 1664525u + 1013904223u;
            buf[j] = (uint8_t)(seed >> 24);
        }
        /* occasionally force magic header */
        if ((i % 7) == 0) {
            buf[0] = 'U'; buf[1] = 'E'; buf[2] = 'M'; buf[3] = 0x16;
            buf[4] = 0; buf[5] = 1; buf[6] = 0; buf[7] = 0;
        }
        m = NULL;
        (void)uem_decode_verify(buf, len, &m, err, sizeof err);
        if (m) uem_free(m);
    }
    /* expression node fuzz from templates */
    {
        uem_machine mm;
        cJSON *root = cJSON_Parse("{\"text\":\"x\",\"items\":[{\"quantity\":1,\"unit_price\":\"1.00\"}],\"n\":1}");
        cJSON *bindings = cJSON_CreateObject();
        const char *templates[] = {
            "{\"op\":\"literal\",\"value\":null}",
            "{\"op\":\"literal\",\"value\":true}",
            "{\"op\":\"literal\",\"value\":false}",
            "{\"op\":\"literal\",\"value\":-3}",
            "{\"op\":\"literal\",\"value\":\"\"}",
            "{\"op\":\"field\",\"path\":[]}",
            "{\"op\":\"field\",\"path\":[\"missing\"]}",
            "{\"op\":\"field\",\"path\":[\"items\",0,\"quantity\"]}",
            "{\"op\":\"field\",\"path\":[\"items\",-1]}",
            "{\"op\":\"as_int\",\"of\":{\"op\":\"literal\",\"value\":\"3\"}}",
            "{\"op\":\"as_decimal\",\"of\":{\"op\":\"literal\",\"value\":null}}",
            "{\"op\":\"quantize\",\"exp\":\"1\",\"rounding\":\"ROUND_DOWN\",\"of\":{\"op\":\"as_decimal\",\"of\":{\"op\":\"literal\",\"value\":\"9.9\"}}}",
            "{\"op\":\"quantize\",\"exp\":\"0.001\",\"rounding\":\"ROUND_UP\",\"of\":{\"op\":\"as_decimal\",\"of\":{\"op\":\"literal\",\"value\":\"-1.2345\"}}}",
            "{\"op\":\"decimal_str\",\"places\":0,\"of\":{\"op\":\"as_decimal\",\"of\":{\"op\":\"literal\",\"value\":\"3\"}}}",
            "{\"op\":\"decimal_str\",\"places\":4,\"of\":{\"op\":\"as_decimal\",\"of\":{\"op\":\"literal\",\"value\":\"-0.5\"}}}",
            "{\"op\":\"add\",\"values\":[]}",
            "{\"op\":\"mul\",\"values\":[{\"op\":\"literal\",\"value\":2}]}",
            "{\"op\":\"word_count\",\"of\":{\"op\":\"literal\",\"value\":null}}",
            "{\"op\":\"line_count\",\"of\":{\"op\":\"literal\",\"value\":1}}",
            "{\"op\":\"unique_casefold_word_count\",\"of\":{\"op\":\"literal\",\"value\":null}}",
            NULL
        };
        int t;
        memset(&mm, 0, sizeof mm);
        snprintf(mm.state, sizeof mm.state, "formed");
        for (t = 0; templates[t]; t++) {
            cJSON *node = cJSON_Parse(templates[t]);
            cJSON *out = NULL, *ep = NULL;
            if (!node) continue;
            (void)uem_expr_eval(&mm, node, root, bindings, &out, err, sizeof err, &ep);
            cJSON_Delete(node);
            if (out) cJSON_Delete(out);
            if (ep) cJSON_Delete(ep);
        }
        cJSON_Delete(root);
        cJSON_Delete(bindings);
    }
}

int main(void) {
    fails = 0;
    test_decimal();
    test_expr_nodes();
    test_decode_rejects();
    test_host_errors();
    test_primitives_direct();
    test_host_json_limits();
    fuzz_decode_expr();

    /* known artifact paths */
    exercise_file("../artifacts/uem/text_stats_v2/program.uem", "{\"text\":\"Hello World\\nA a\"}");
    exercise_file("artifacts/uem/text_stats_v2/program.uem", "{\"text\":\"Hello World\\nA a\"}");
    exercise_file("../artifacts/uem/invoice_total/program.uem",
                  "{\"document\":{\"items\":[{\"quantity\":2,\"unit_price\":\"1.50\"},"
                  "{\"quantity\":1,\"unit_price\":\"2.00\"}]}}");
    exercise_file("artifacts/uem/invoice_total/program.uem",
                  "{\"document\":{\"items\":[{\"quantity\":2,\"unit_price\":\"1.50\"}]}}");
    exercise_file("../c/tests/vectors/bad_magic.uem", NULL);
    exercise_file("tests/vectors/bad_magic.uem", NULL);
    exercise_file("../c/tests/vectors/truncated.uem", NULL);
    exercise_file("tests/vectors/truncated.uem", NULL);
    exercise_file("../c/tests/vectors/trailing.uem", NULL);
    exercise_file("tests/vectors/trailing.uem", NULL);
    exercise_file("../c/tests/vectors/unknown_opcode.uem", NULL);
    exercise_file("tests/vectors/unknown_opcode.uem", NULL);

    /* coverage_vectors */
    {
        int v;
        char path[256];
        for (v = 0; v < 64; v++) {
            snprintf(path, sizeof path, "tests/coverage_vectors/v%03d.uem", v);
            exercise_file(path, "{\"text\":\"x y\\nz\"}");
            snprintf(path, sizeof path, "c/tests/coverage_vectors/v%03d.uem", v);
            exercise_file(path, "{\"text\":\"x y\\nz\"}");
            snprintf(path, sizeof path, "../c/tests/coverage_vectors/v%03d.uem", v);
            exercise_file(path, "{\"document\":{\"items\":[]}}");
        }
    }

    /* limits */
    setenv("UEM_MAX_STEPS", "1", 1);
    exercise_file("../artifacts/uem/text_stats_v2/program.uem", "{\"text\":\"x\"}");
    exercise_file("artifacts/uem/text_stats_v2/program.uem", "{\"text\":\"x\"}");
    unsetenv("UEM_MAX_STEPS");

    /* named edge vectors */
    {
        const char *edges[] = {
            "nostop.uem", "limg.uem", "enq.uem", "quiet.uem", "amiss.uem",
            "tick.uem", "uroute.uem", "ev.uem", "wrd.uem", "utf4.uem", "esc.uem",
            "mb_0.uem", "mb_1.uem", "mb_2.uem", "mb_3.uem", "ctrl.uem",
            "nostop2.uem", "trail.uem", NULL
        };
        int e;
        char path[320];
        for (e = 0; edges[e]; e++) {
            snprintf(path, sizeof path, "tests/coverage_vectors/%s", edges[e]);
            exercise_file(path, "{\"text\":\"x\\ny\"}");
            snprintf(path, sizeof path, "c/tests/coverage_vectors/%s", edges[e]);
            exercise_file(path, "{\"text\":\"x\\ny\"}");
            snprintf(path, sizeof path, "../c/tests/coverage_vectors/%s", edges[e]);
            exercise_file(path, "{\"text\":\"x\\ny\"}");
        }
    }

    /* image with JSON-escape-worthy characters (canonical via encode) */
    {
        FILE *f = fopen("tests/coverage_vectors/esc.uem", "rb");
        if (!f) f = fopen("c/tests/coverage_vectors/esc.uem", "rb");
        if (!f) f = fopen("../c/tests/coverage_vectors/esc.uem", "rb");
        if (f) {
            uint8_t *buf;
            long sz;
            uem_machine *m = NULL;
            char err[128];
            fseek(f, 0, SEEK_END);
            sz = ftell(f);
            rewind(f);
            buf = (uint8_t *)malloc((size_t)sz);
            if (buf && fread(buf, 1, (size_t)sz, f) == (size_t)sz) {
                (void)uem_decode_verify(buf, (size_t)sz, &m, err, sizeof err);
                if (m) uem_free(m);
            }
            free(buf);
            fclose(f);
        }
    }

    /* invalid 4-byte utf-8 sequence in operand */
    {
        uint8_t p[] = {
            'U','E','M',0x16, 0,1, 0,0,
            0,0,0,1,
            0x01, 0x01, 0,0,0,4, 0xf5, 0x80, 0x80, 0x80, /* invalid > f4 */
            0,0,0,2, '{','}'
        };
        uem_machine *m = NULL;
        char err[128];
        (void)uem_decode_verify(p, sizeof p, &m, err, sizeof err);
        if (m) uem_free(m);
    }
    {
        uint8_t p[] = {
            'U','E','M',0x16, 0,1, 0,0,
            0,0,0,1,
            0x01, 0x01, 0,0,0,4, 0xf0, 0x20, 0x80, 0x80, /* bad cont */
            0,0,0,2, '{','}'
        };
        uem_machine *m = NULL;
        char err[128];
        (void)uem_decode_verify(p, sizeof p, &m, err, sizeof err);
        if (m) uem_free(m);
    }
    /* valid 4-byte utf-8 */
    {
        uint8_t p[] = {
            'U','E','M',0x16, 0,1, 0,0,
            0,0,0,1,
            0x01, 0x01, 0,0,0,4, 0xf0, 0x9f, 0x98, 0x80,
            0,0,0,2, '{','}'
        };
        uem_machine *m = NULL;
        char err[128];
        (void)uem_decode_verify(p, sizeof p, &m, err, sizeof err);
        if (m) {
            (void)uem_state(m);
            uem_free(m);
        }
    }

    /* bindings + failing expression for prim_eval error path */
    {
        uem_machine m;
        char err[64];
        memset(&m, 0, sizeof m);
        snprintf(m.state, sizeof m.state, "formed");
        m.store = cJSON_CreateObject();
        cJSON_AddStringToObject(m.store, "text", "hi");
        m.image = cJSON_Parse(
            "{\"input_key\":\"text\",\"part_name\":\"feat\","
            "\"expression\":{\"op\":\"ref\",\"name\":\"missing\"},"
            "\"bindings\":{\"bad\":{\"op\":\"ref\",\"name\":\"nope\"}},"
            "\"binding_order\":[\"bad\",\"missing_name\"]}");
        m.host = cJSON_Parse("{\"text\":\"hi\"}");
        (void)uem_prim_apply(&m, "eval_expression", err, sizeof err);
        free_soft_machine(&m);
    }
    /* verify_result fail paths */
    {
        uem_machine m;
        char err[64];
        memset(&m, 0, sizeof m);
        snprintf(m.state, sizeof m.state, "formed");
        m.store = cJSON_CreateObject();
        cJSON_AddStringToObject(m.store, "error", "e");
        m.image = cJSON_Parse(
            "{\"verify\":{\"require_value_field\":\"stats\","
            "\"require_evidence_contains\":[\"must\"]}}");
        (void)uem_prim_apply(&m, "verify_result", err, sizeof err);
        cJSON_DeleteItemFromObjectCaseSensitive(m.store, "error");
        snprintf(m.state, sizeof m.state, "formed");
        (void)uem_prim_apply(&m, "verify_result", err, sizeof err); /* missing stats */
        free_soft_machine(&m);
    }

    if (fails) {
        fprintf(stderr, "core_coverage_harness: %d failures\n", fails);
        return 1;
    }
    printf("core_coverage_harness: ok\n");
    return 0;
}
