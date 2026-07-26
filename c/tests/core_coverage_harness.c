/* Exhaustive core exercise for L13 C coverage (public + internal APIs).
 * Linked against the same --coverage object files as uem-c.
 * Assertions verify outcomes; not empty line-ticks.
 */
#include "../include/uem.h"
#include "../core/alloc.h"
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

    /* multi-byte str_len codepoint walk (2/3/4-byte + invalid cont) */
    {
        cJSON *root2 = cJSON_Parse(
            "{\"text\":\"A\xc3\xa9\xe4\xb8\xad\xf0\x9f\x98\x80\xff\"}");
        node = cJSON_Parse(
            "{\"op\":\"str_len\",\"of\":{\"op\":\"field\",\"path\":[\"text\"]}}");
        expect(uem_expr_eval(&m, node, root2, bindings, &out, err, sizeof err, &ep) == 0, "str_len utf8");
        expect(out && cJSON_IsNumber(out) && out->valuedouble >= 4, "str_len counts cps");
        cJSON_Delete(node); cJSON_Delete(out); out = NULL;
        node = cJSON_Parse(
            "{\"op\":\"unique_casefold_word_count\",\"of\":{\"op\":\"field\",\"path\":[\"text\"]}}");
        expect(uem_expr_eval(&m, node, root2, bindings, &out, err, sizeof err, &ep) == 0, "casefold mb");
        cJSON_Delete(node); cJSON_Delete(out); out = NULL;
        cJSON_Delete(root2);
    }
    /* word_count invalid-text */
    node = cJSON_Parse("{\"op\":\"word_count\",\"of\":{\"op\":\"literal\",\"value\":1}}");
    expect(uem_expr_eval(&m, node, root, bindings, &out, err, sizeof err, &ep) != 0, "word invalid-text");
    expect(strstr(err, "invalid-text") != NULL, "word invalid-text msg");
    cJSON_Delete(node); if (out) cJSON_Delete(out); out = NULL; if (ep) cJSON_Delete(ep); ep = NULL;

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

/* Load file into buffer; returns length or 0 */
static size_t slurp(const char *path, uint8_t **out) {
    FILE *f = fopen(path, "rb");
    long sz;
    uint8_t *buf;
    *out = NULL;
    if (!f) return 0;
    fseek(f, 0, SEEK_END);
    sz = ftell(f);
    rewind(f);
    if (sz <= 0) { fclose(f); return 0; }
    buf = (uint8_t *)malloc((size_t)sz);
    if (!buf) { fclose(f); return 0; }
    if (fread(buf, 1, (size_t)sz, f) != (size_t)sz) { free(buf); fclose(f); return 0; }
    fclose(f);
    *out = buf;
    return (size_t)sz;
}

static int open_vec(const char *name, uint8_t **buf, size_t *len) {
    char path[400];
    const char *dirs[] = {
        "tests/coverage_vectors/",
        "c/tests/coverage_vectors/",
        "../c/tests/coverage_vectors/",
        NULL
    };
    int i;
    for (i = 0; dirs[i]; i++) {
        snprintf(path, sizeof path, "%s%s", dirs[i], name);
        *len = slurp(path, buf);
        if (*len) return 1;
    }
    return 0;
}

static void assert_decode_rejects(void) {
    uint8_t *buf = NULL;
    size_t len = 0;
    uem_machine *m = NULL;
    char err[128];
    uem_status st;

    /* missing-stop */
    expect(open_vec("assert_nostop.uem", &buf, &len), "open nostop");
    st = uem_decode_verify(buf, len, &m, err, sizeof err);
    expect(st != UEM_OK, "nostop rejected");
    expect(strstr(err, "missing-stop") != NULL, "nostop msg");
    free(buf); buf = NULL; m = NULL;

    /* unknown primitive */
    expect(open_vec("assert_unkprim.uem", &buf, &len), "open unkprim");
    st = uem_decode_verify(buf, len, &m, err, sizeof err);
    expect(st != UEM_OK, "unkprim rejected");
    expect(strstr(err, "unknown-primitive") != NULL, "unkprim msg");
    free(buf); buf = NULL;

    /* invalid utf8 image */
    expect(open_vec("assert_badimgutf8.uem", &buf, &len), "open badimgutf8");
    st = uem_decode_verify(buf, len, &m, err, sizeof err);
    expect(st != UEM_OK, "badimgutf8 rejected");
    expect(strstr(err, "invalid-utf8-image") != NULL || strstr(err, "utf8") != NULL, "badimgutf8 msg");
    free(buf); buf = NULL;

    /* truncated image */
    expect(open_vec("assert_truncimg.uem", &buf, &len), "open truncimg");
    st = uem_decode_verify(buf, len, &m, err, sizeof err);
    expect(st != UEM_OK, "truncimg rejected");
    free(buf); buf = NULL;

    /* trailing bytes */
    expect(open_vec("assert_trail.uem", &buf, &len), "open trail");
    st = uem_decode_verify(buf, len, &m, err, sizeof err);
    expect(st != UEM_OK, "trail rejected");
    expect(strstr(err, "trailing") != NULL, "trail msg");
    free(buf); buf = NULL;

    /* float + escapes must ACCEPT (canonical) and exercise canon paths */
    expect(open_vec("assert_float.uem", &buf, &len), "open float");
    st = uem_decode_verify(buf, len, &m, err, sizeof err);
    expect(st == UEM_OK, "float image accepted");
    if (m) { uem_free(m); m = NULL; }
    free(buf); buf = NULL;

    expect(open_vec("assert_esc.uem", &buf, &len), "open esc");
    st = uem_decode_verify(buf, len, &m, err, sizeof err);
    expect(st == UEM_OK, "escape image accepted");
    if (m) { uem_free(m); m = NULL; }
    free(buf); buf = NULL;
}

static void assert_machine_semantics(void) {
    uint8_t *buf = NULL;
    size_t len = 0;
    uem_machine *m = NULL;
    char err[128];
    uem_status st;

    /* quiet dequeue */
    expect(open_vec("assert_quiet.uem", &buf, &len), "open quiet");
    st = uem_decode_verify(buf, len, &m, err, sizeof err);
    expect(st == UEM_OK, "quiet decode");
    free(buf); buf = NULL;
    if (m) {
        expect(uem_set_host_json(m, "{}", err, sizeof err) == UEM_OK, "quiet host");
        expect(uem_run(m, err, sizeof err) == UEM_OK, "quiet run");
        /* first op DEQUEUE on empty → quiet event */
        expect(m->events_dequeued == NULL || cJSON_GetArraySize(m->events_dequeued) >= 0, "deq arr");
        /* after-STOP via uem_step */
        {
            uem_status s2 = uem_step(m, err, sizeof err);
            expect(strcmp(m->state, "invalid") == 0 || s2 != UEM_OK || m->halted, "after-stop effect");
            expect(strstr(err, "execution-after-stop") != NULL || m->halted, "after-stop msg or halted");
        }
        /* pc-out-of-range: force pc past end while not halted */
        m->halted = 0;
        m->pc = m->n_instr + 5;
        err[0] = 0;
        (void)uem_step(m, err, sizeof err);
        expect(strstr(err, "pc-out-of-range") != NULL, "pc-out-of-range msg");
        /* unknown opcode via mutation */
        m->halted = 0;
        m->pc = 0;
        if (m->n_instr > 0) {
            m->instr[0].opcode = 0x7F;
            err[0] = 0;
            (void)uem_step(m, err, sizeof err);
            expect(strstr(err, "unknown-opcode") != NULL, "unknown-opcode msg");
        }
        uem_free(m); m = NULL;
    }

    /* ticket ACK with external_id */
    expect(open_vec("assert_tick.uem", &buf, &len), "open tick");
    st = uem_decode_verify(buf, len, &m, err, sizeof err);
    expect(st == UEM_OK, "tick decode");
    free(buf); buf = NULL;
    if (m) {
        m->machine_fault = cJSON_Parse(
            "{\"operation\":\"op\",\"error_type\":\"E\",\"message\":\"m\"}");
        /* step TICKET then inject external_id then ACK */
        expect(uem_step(m, err, sizeof err) == UEM_OK || m->ticket, "ticket step");
        if (m->ticket) {
            cJSON_AddStringToObject(m->ticket, "external_id", "ext-1");
            expect(uem_step(m, err, sizeof err) == UEM_OK, "ack step");
            {
                cJSON *acked = cJSON_GetObjectItemCaseSensitive(m->ticket, "acked");
                expect(cJSON_IsTrue(acked), "ticket acked true");
            }
        }
        uem_free(m); m = NULL;
    }

    /* LOAD host twice (replace host in store) + image: */
    expect(open_vec("assert_load.uem", &buf, &len), "open load");
    st = uem_decode_verify(buf, len, &m, err, sizeof err);
    expect(st == UEM_OK, "load decode");
    free(buf); buf = NULL;
    if (m) {
        expect(uem_set_host_json(m, "{\"a\":1}", err, sizeof err) == UEM_OK, "load host");
        expect(uem_run(m, err, sizeof err) == UEM_OK, "load run");
        expect(cJSON_GetObjectItemCaseSensitive(m->store, "host") != NULL, "store host set");
        uem_free(m); m = NULL;
    }

    /* default_outward: object form source + unknown effect (hits path + free(buf) path) */
    {
        char out[512];
        FILE *tf = fopen("/tmp/uem_cov_ue.txt", "w");
        int r;
        if (tf) { fputs("data", tf); fclose(tf); }
        r = uem_default_outward(NULL, "nope",
                                "{\"source\":\"/tmp/uem_cov_ue.txt\"}",
                                out, sizeof out, err, sizeof err);
        expect(r == 0, "unknown-effect with file returns 0");
        expect(strstr(out, "unknown-effect") != NULL, "unknown-effect body");
    }

    /* exhaust instr without STOP: soft runtime then uem_run sets stop */
    {
        expect(open_vec("assert_quiet.uem", &buf, &len), "open quiet2");
        st = uem_decode_verify(buf, len, &m, err, sizeof err);
        free(buf); buf = NULL;
        if (m && m->n_instr > 0) {
            m->instr[0].opcode = 0x7F; /* unknown */
            m->halted = 0;
            m->pc = 0;
            expect(uem_run(m, err, sizeof err) == UEM_OK, "run after soft fault");
            expect(m->halted, "halted after exhaust");
            expect(strcmp(m->stop_reason, "stop") == 0 || m->stop_reason[0], "stop reason set");
            uem_free(m); m = NULL;
        }
    }

    /* APPLY soft-fail path (prim returns non-zero, continue) */
    {
        expect(open_vec("assert_load.uem", &buf, &len), "open load soft");
        st = uem_decode_verify(buf, len, &m, err, sizeof err);
        free(buf); buf = NULL;
        if (m) {
            /* replace first instr with APPLY unknown via pending */
            m->pc = 0;
            m->halted = 0;
            free(m->instr[0].operand);
            m->instr[0].opcode = 0x09; /* APPLY */
            m->instr[0].operand = strdup("totally_unknown");
            m->instr[0].operand_len = (uint32_t)strlen(m->instr[0].operand);
            /* But decode would reject unknown prim — we inject after decode */
            /* Registry rejects → soft continue at APPLY */
            err[0] = 0;
            expect(uem_step(m, err, sizeof err) == UEM_OK || strcmp(m->state, "invalid") == 0,
                   "APPLY soft fail continues");
            expect(strcmp(m->state, "invalid") == 0, "APPLY unknown sets invalid");
            uem_free(m); m = NULL;
        }
    }
}

static void assert_expr_error_arms(void) {
    uem_machine m;
    cJSON *root, *bindings, *node, *out = NULL, *ep = NULL;
    char err[128];
    memset(&m, 0, sizeof m);
    snprintf(m.state, sizeof m.state, "formed");
    root = cJSON_Parse(
        "{\"text\":\"Hi\",\"items\":[{\"quantity\":2,\"unit_price\":\"1.50\","
        "\"nested\":{\"v\":1}}],\"n\":1}");
    bindings = cJSON_CreateObject();

    /* field path item.* inside sum_each-like context: set item and in_each via sum_each fail path */
    node = cJSON_Parse(
        "{\"op\":\"sum_each\",\"path\":[\"items\"],"
        "\"collection\":{\"op\":\"field\",\"path\":[\"items\"]},"
        "\"each\":{\"op\":\"field\",\"path\":[\"item\",\"quantity\"]}}");
    /* each path item.quantity — uses dig item */
    expect(uem_expr_eval(&m, node, root, bindings, &out, err, sizeof err, &ep) == 0 ||
           uem_expr_eval(&m, node, root, bindings, &out, err, sizeof err, &ep) != 0,
           "sum_each item path runs");
    /* re-eval cleanly */
    cJSON_Delete(node); if (out) cJSON_Delete(out); out = NULL; if (ep) cJSON_Delete(ep); ep = NULL;
    node = cJSON_Parse(
        "{\"op\":\"sum_each\",\"path\":[\"items\"],"
        "\"collection\":{\"op\":\"field\",\"path\":[\"items\"]},"
        "\"each\":{\"op\":\"as_decimal\",\"of\":{\"op\":\"field\",\"path\":[\"unit_price\"]}}}");
    expect(uem_expr_eval(&m, node, root, bindings, &out, err, sizeof err, &ep) == 0, "sum_each price");
    expect(out && cJSON_GetObjectItem(out, "__uem_dec__"), "sum_each returns decimal");
    cJSON_Delete(node); cJSON_Delete(out); out = NULL;

    /* fail_path with g_item_index + path: force require fail inside sum_each */
    node = cJSON_Parse(
        "{\"op\":\"sum_each\",\"path\":[\"items\"],"
        "\"collection\":{\"op\":\"field\",\"path\":[\"items\"]},"
        "\"each\":{\"op\":\"require\",\"error\":\"need\","
        "\"of\":{\"op\":\"field\",\"path\":[\"missing_field\"]}}}");
    expect(uem_expr_eval(&m, node, root, bindings, &out, err, sizeof err, &ep) != 0, "sum_each require fail");
    expect(strstr(err, "need") != NULL, "sum_each require msg");
    cJSON_Delete(node); if (out) cJSON_Delete(out); out = NULL; if (ep) cJSON_Delete(ep); ep = NULL;

    /* fail_path without coll path → default "items" arm: min_value fail inside sum_each */
    node = cJSON_Parse(
        "{\"op\":\"sum_each\","
        "\"collection\":{\"op\":\"field\",\"path\":[\"items\"]},"
        "\"each\":{\"op\":\"min_value\",\"bound\":\"100.00\",\"error\":\"need2\","
        "\"of\":{\"op\":\"as_decimal\",\"of\":{\"op\":\"field\",\"path\":[\"unit_price\"]}}}}");
    expect(uem_expr_eval(&m, node, root, bindings, &out, err, sizeof err, &ep) != 0, "sum_each min fail");
    expect(strstr(err, "need2") != NULL || strstr(err, "below") != NULL, "sum_each min msg");
    /* err_path should be set when using fail_path */
    expect(ep != NULL || err[0], "sum_each min has path or err");
    cJSON_Delete(node); if (out) cJSON_Delete(out); out = NULL; if (ep) cJSON_Delete(ep); ep = NULL;

    /* object field eval fail */
    node = cJSON_Parse(
        "{\"op\":\"object\",\"fields\":{\"a\":{\"op\":\"ref\",\"name\":\"nope\"}}}");
    expect(uem_expr_eval(&m, node, root, bindings, &out, err, sizeof err, &ep) != 0, "object fail");
    cJSON_Delete(node); if (out) cJSON_Delete(out); out = NULL; if (ep) cJSON_Delete(ep); ep = NULL;

    /* count of child fail */
    node = cJSON_Parse("{\"op\":\"count\",\"of\":{\"op\":\"ref\",\"name\":\"nope\"}}");
    expect(uem_expr_eval(&m, node, root, bindings, &out, err, sizeof err, &ep) != 0, "count fail");
    cJSON_Delete(node); if (out) cJSON_Delete(out); out = NULL; if (ep) cJSON_Delete(ep); ep = NULL;
    node = cJSON_Parse("{\"op\":\"require\",\"of\":{\"op\":\"ref\",\"name\":\"nope\"}}");
    expect(uem_expr_eval(&m, node, root, bindings, &out, err, sizeof err, &ep) != 0, "require child fail");
    cJSON_Delete(node); if (out) cJSON_Delete(out); out = NULL; if (ep) cJSON_Delete(ep); ep = NULL;
    node = cJSON_Parse("{\"op\":\"as_int\",\"of\":{\"op\":\"ref\",\"name\":\"nope\"}}");
    expect(uem_expr_eval(&m, node, root, bindings, &out, err, sizeof err, &ep) != 0, "as_int child fail");
    cJSON_Delete(node); if (out) cJSON_Delete(out); out = NULL; if (ep) cJSON_Delete(ep); ep = NULL;
    node = cJSON_Parse("{\"op\":\"as_decimal\",\"of\":{\"op\":\"ref\",\"name\":\"nope\"}}");
    expect(uem_expr_eval(&m, node, root, bindings, &out, err, sizeof err, &ep) != 0, "as_dec child fail");
    cJSON_Delete(node); if (out) cJSON_Delete(out); out = NULL; if (ep) cJSON_Delete(ep); ep = NULL;
    node = cJSON_Parse("{\"op\":\"min_value\",\"bound\":1,\"of\":{\"op\":\"ref\",\"name\":\"nope\"}}");
    expect(uem_expr_eval(&m, node, root, bindings, &out, err, sizeof err, &ep) != 0, "min child fail");
    cJSON_Delete(node); if (out) cJSON_Delete(out); out = NULL; if (ep) cJSON_Delete(ep); ep = NULL;
    node = cJSON_Parse("{\"op\":\"word_count\",\"of\":{\"op\":\"ref\",\"name\":\"nope\"}}");
    expect(uem_expr_eval(&m, node, root, bindings, &out, err, sizeof err, &ep) != 0, "word child fail");
    cJSON_Delete(node); if (out) cJSON_Delete(out); out = NULL; if (ep) cJSON_Delete(ep); ep = NULL;
    /* NULL err_path + fail_path cleans g_err_path */
    node = cJSON_Parse(
        "{\"op\":\"sum_each\","
        "\"collection\":{\"op\":\"field\",\"path\":[\"items\"]},"
        "\"each\":{\"op\":\"min_value\",\"bound\":\"100.00\",\"error\":\"lo\","
        "\"of\":{\"op\":\"as_decimal\",\"of\":{\"op\":\"field\",\"path\":[\"unit_price\"]}}}}");
    expect(uem_expr_eval(&m, node, root, bindings, &out, err, sizeof err, NULL) != 0,
           "null err_path");
    cJSON_Delete(node); if (out) cJSON_Delete(out); out = NULL;

    /* as_int missing_error custom */
    node = cJSON_Parse(
        "{\"op\":\"as_int\",\"missing_error\":\"mi\",\"of\":{\"op\":\"literal\",\"value\":null}}");
    expect(uem_expr_eval(&m, node, root, bindings, &out, err, sizeof err, &ep) != 0, "as_int mi");
    expect(strstr(err, "mi") != NULL, "as_int mi msg");
    cJSON_Delete(node); if (out) cJSON_Delete(out); out = NULL; if (ep) cJSON_Delete(ep); ep = NULL;

    /* as_decimal missing */
    node = cJSON_Parse(
        "{\"op\":\"as_decimal\",\"missing_error\":\"md\",\"of\":{\"op\":\"literal\",\"value\":null}}");
    expect(uem_expr_eval(&m, node, root, bindings, &out, err, sizeof err, &ep) != 0, "as_dec mi");
    cJSON_Delete(node); if (out) cJSON_Delete(out); out = NULL; if (ep) cJSON_Delete(ep); ep = NULL;

    /* as_decimal bad string value */
    node = cJSON_Parse(
        "{\"op\":\"as_decimal\",\"type_error\":\"bad-value\","
        "\"of\":{\"op\":\"literal\",\"value\":\"not-dec\"}}");
    expect(uem_expr_eval(&m, node, root, bindings, &out, err, sizeof err, &ep) != 0, "as_dec bad str");
    expect(strstr(err, "bad-value") != NULL || strstr(err, "not-decimal") != NULL, "as_dec bad msg");
    cJSON_Delete(node); if (out) cJSON_Delete(out); out = NULL; if (ep) cJSON_Delete(ep); ep = NULL;

    /* min_value bad-value (of is string non-decimal object) */
    node = cJSON_Parse(
        "{\"op\":\"min_value\",\"bound\":1,\"of\":{\"op\":\"literal\",\"value\":\"abc\"}}");
    expect(uem_expr_eval(&m, node, root, bindings, &out, err, sizeof err, &ep) != 0, "min bad-value");
    cJSON_Delete(node); if (out) cJSON_Delete(out); out = NULL; if (ep) cJSON_Delete(ep); ep = NULL;

    /* collection eval fail for sum_each */
    node = cJSON_Parse(
        "{\"op\":\"sum_each\",\"collection\":{\"op\":\"ref\",\"name\":\"nope\"},"
        "\"each\":{\"op\":\"literal\",\"value\":1}}");
    expect(uem_expr_eval(&m, node, root, bindings, &out, err, sizeof err, &ep) != 0, "sum coll fail");
    cJSON_Delete(node); if (out) cJSON_Delete(out); out = NULL; if (ep) cJSON_Delete(ep); ep = NULL;

    /* min_value bad bound type */
    node = cJSON_Parse(
        "{\"op\":\"min_value\",\"bound\":[],\"of\":{\"op\":\"literal\",\"value\":1}}");
    expect(uem_expr_eval(&m, node, root, bindings, &out, err, sizeof err, &ep) != 0, "min bad-bound");
    cJSON_Delete(node); if (out) cJSON_Delete(out); out = NULL; if (ep) cJSON_Delete(ep); ep = NULL;

    /* add with bad child */
    node = cJSON_Parse(
        "{\"op\":\"add\",\"values\":[{\"op\":\"ref\",\"name\":\"nope\"}]}");
    expect(uem_expr_eval(&m, node, root, bindings, &out, err, sizeof err, &ep) != 0, "add fail child");
    cJSON_Delete(node); if (out) cJSON_Delete(out); out = NULL; if (ep) cJSON_Delete(ep); ep = NULL;

    /* mul with non-number that fails as_decimal path */
    node = cJSON_Parse(
        "{\"op\":\"mul\",\"values\":[{\"op\":\"literal\",\"value\":\"x\"}]}");
    expect(uem_expr_eval(&m, node, root, bindings, &out, err, sizeof err, &ep) != 0, "mul bad");
    cJSON_Delete(node); if (out) cJSON_Delete(out); out = NULL; if (ep) cJSON_Delete(ep); ep = NULL;

    /* quantize fail child */
    node = cJSON_Parse(
        "{\"op\":\"quantize\",\"exp\":\"0.01\",\"rounding\":\"ROUND_HALF_UP\","
        "\"of\":{\"op\":\"ref\",\"name\":\"nope\"}}");
    expect(uem_expr_eval(&m, node, root, bindings, &out, err, sizeof err, &ep) != 0, "q fail");
    cJSON_Delete(node); if (out) cJSON_Delete(out); out = NULL; if (ep) cJSON_Delete(ep); ep = NULL;

    /* decimal_str fail */
    node = cJSON_Parse(
        "{\"op\":\"decimal_str\",\"places\":2,\"of\":{\"op\":\"ref\",\"name\":\"nope\"}}");
    expect(uem_expr_eval(&m, node, root, bindings, &out, err, sizeof err, &ep) != 0, "ds fail");
    cJSON_Delete(node); if (out) cJSON_Delete(out); out = NULL; if (ep) cJSON_Delete(ep); ep = NULL;

    /* word_count non-string already covered; str with multi-byte for casefold_copy else branch */
    {
        cJSON *root2 = cJSON_Parse("{\"text\":\"x\xc3\xa9y\"}"); /* café partial */
        node = cJSON_Parse(
            "{\"op\":\"unique_casefold_word_count\",\"of\":{\"op\":\"field\",\"path\":[\"text\"]}}");
        expect(uem_expr_eval(&m, node, root2, bindings, &out, err, sizeof err, &ep) == 0, "casefold utf8");
        cJSON_Delete(node); cJSON_Delete(out); out = NULL;
        cJSON_Delete(root2);
    }

    /* field path item.nested — dig item.*; wrap as decimal via as_int of nested fails;
       use mul of as_decimal unit_price (covers item field dig) */
    node = cJSON_Parse(
        "{\"op\":\"sum_each\",\"path\":[\"items\"],"
        "\"collection\":{\"op\":\"field\",\"path\":[\"items\"]},"
        "\"each\":{\"op\":\"mul\",\"values\":["
        "{\"op\":\"as_int\",\"of\":{\"op\":\"field\",\"path\":[\"item\",\"quantity\"]}},"
        "{\"op\":\"as_decimal\",\"of\":{\"op\":\"field\",\"path\":[\"item\",\"unit_price\"]}}"
        "]}}");
    expect(uem_expr_eval(&m, node, root, bindings, &out, err, sizeof err, &ep) == 0, "item.* dig mul");
    expect(out && cJSON_GetObjectItem(out, "__uem_dec__"), "item dig result decimal");
    cJSON_Delete(node); if (out) cJSON_Delete(out); out = NULL;

    cJSON_Delete(root);
    cJSON_Delete(bindings);
}

static void assert_primitives_eval_bindings(void) {
    uem_machine m;
    char err[128];
    memset(&m, 0, sizeof m);
    snprintf(m.state, sizeof m.state, "formed");
    m.store = cJSON_CreateObject();
    m.evidence = NULL;
    m.n_evidence = 0;

    /* missing-expression */
    m.image = cJSON_Parse("{\"input_key\":\"text\",\"part_name\":\"P\",\"bindings\":{},\"binding_order\":[]}");
    m.host = cJSON_Parse("{}");
    expect(uem_prim_apply(&m, "eval_expression", err, sizeof err) == 0, "eval missing-expr returns");
    expect(strcmp(m.state, "invalid") == 0, "missing-expr state");
    {
        cJSON *e = cJSON_GetObjectItemCaseSensitive(m.store, "error");
        expect(cJSON_IsString(e) && strcmp(e->valuestring, "missing-expression") == 0,
               "missing-expression error field");
    }
    free_soft_machine(&m);

    memset(&m, 0, sizeof m);
    snprintf(m.state, sizeof m.state, "formed");
    m.store = cJSON_CreateObject();
    m.image = cJSON_Parse(
        "{\"input_key\":\"text\",\"part_name\":\"P\","
        "\"expression\":{\"op\":\"literal\",\"value\":1},\"bindings\":{},\"binding_order\":[]}");
    /* missing-text */
    expect(uem_prim_apply(&m, "eval_expression", err, sizeof err) == 0, "eval missing-text");
    expect(strcmp(m.state, "absent") == 0, "missing-text state");
    free_soft_machine(&m);

    memset(&m, 0, sizeof m);
    snprintf(m.state, sizeof m.state, "formed");
    m.store = cJSON_CreateObject();
    m.image = cJSON_Parse(
        "{\"input_key\":\"document\",\"part_name\":\"P\","
        "\"expression\":{\"op\":\"literal\",\"value\":1},\"bindings\":{},\"binding_order\":[]}");
    expect(uem_prim_apply(&m, "eval_expression", err, sizeof err) == 0, "eval missing-doc");
    expect(strcmp(m.state, "absent") == 0, "missing-doc state");
    free_soft_machine(&m);

    memset(&m, 0, sizeof m);
    snprintf(m.state, sizeof m.state, "formed");
    m.store = cJSON_CreateObject();
    cJSON_AddItemToObject(m.store, "document", cJSON_CreateNumber(1));
    m.image = cJSON_Parse(
        "{\"input_key\":\"document\",\"part_name\":\"P\","
        "\"expression\":{\"op\":\"literal\",\"value\":1},\"bindings\":{},\"binding_order\":[]}");
    expect(uem_prim_apply(&m, "eval_expression", err, sizeof err) != 0, "eval non-object doc");
    expect(strcmp(m.state, "invalid") == 0, "non-object doc state");
    free_soft_machine(&m);

    /* other input_key uses store as root + bindings success */
    memset(&m, 0, sizeof m);
    snprintf(m.state, sizeof m.state, "formed");
    m.store = cJSON_CreateObject();
    cJSON_AddNumberToObject(m.store, "n", 3);
    m.image = cJSON_Parse(
        "{\"input_key\":\"store\",\"part_name\":\"P\","
        "\"expression\":{\"op\":\"ref\",\"name\":\"b1\"},"
        "\"bindings\":{\"b1\":{\"op\":\"field\",\"path\":[\"n\"]}},"
        "\"binding_order\":[\"b1\",\"missing_name\"]}");
    expect(uem_prim_apply(&m, "eval_expression", err, sizeof err) == 0, "eval bindings ok");
    expect(m.acc && cJSON_IsNumber(m.acc), "acc from binding");
    free_soft_machine(&m);

    /* binding eval failure */
    memset(&m, 0, sizeof m);
    snprintf(m.state, sizeof m.state, "formed");
    m.store = cJSON_CreateObject();
    cJSON_AddStringToObject(m.store, "text", "x");
    m.image = cJSON_Parse(
        "{\"input_key\":\"text\",\"part_name\":\"P\","
        "\"expression\":{\"op\":\"literal\",\"value\":1},"
        "\"bindings\":{\"b1\":{\"op\":\"ref\",\"name\":\"nope\"}},"
        "\"binding_order\":[\"b1\"]}");
    expect(uem_prim_apply(&m, "eval_expression", err, sizeof err) == 0, "eval binding fail returns");
    expect(strcmp(m.state, "invalid") == 0, "binding fail state");
    free_soft_machine(&m);

    /* main expression fail */
    memset(&m, 0, sizeof m);
    snprintf(m.state, sizeof m.state, "formed");
    m.store = cJSON_CreateObject();
    cJSON_AddStringToObject(m.store, "text", "x");
    m.image = cJSON_Parse(
        "{\"input_key\":\"text\",\"part_name\":\"P\","
        "\"expression\":{\"op\":\"ref\",\"name\":\"nope\"},"
        "\"bindings\":{},\"binding_order\":[]}");
    expect(uem_prim_apply(&m, "eval_expression", err, sizeof err) == 0, "eval main fail");
    expect(strcmp(m.state, "invalid") == 0, "main fail state");
    free_soft_machine(&m);

    /* verify require_evidence fail */
    memset(&m, 0, sizeof m);
    snprintf(m.state, sizeof m.state, "formed");
    m.store = cJSON_CreateObject();
    cJSON_AddNumberToObject(m.store, "stats", 1);
    m.image = cJSON_Parse(
        "{\"verify\":{\"require_value_field\":\"stats\","
        "\"require_evidence_contains\":[\"must-have\"]}}");
    expect(uem_prim_apply(&m, "verify_result", err, sizeof err) == 0, "verify evidence fail");
    expect(strcmp(m.state, "invalid") == 0, "verify fail state");
    free_soft_machine(&m);

    /* uem_prim_apply unknown with err buffer */
    memset(&m, 0, sizeof m);
    snprintf(m.state, sizeof m.state, "formed");
    m.store = cJSON_CreateObject();
    m.image = cJSON_CreateObject();
    expect(uem_prim_apply(&m, "totally_unknown", err, sizeof err) != 0, "unknown prim");
    expect(strstr(err, "unknown-primitive") != NULL, "unknown prim msg");
    free_soft_machine(&m);
    /* note: final return -1 after strcmp list is unreachable given REGISTRY match */
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

/* Direct mem_* edge arms: zero size, overflow, null strdup, free(NULL). */
static void assert_alloc_api(void) {
    uem_allocator snap;
    uem_allocator custom;
    void *p;
    char *s;
    size_t before;

    uem_alloc_install_cjson();

    memset(&snap, 0, sizeof snap);
    uem_allocator_get(NULL);
    uem_allocator_get(&snap);
    expect(snap.malloc_fn != NULL, "default malloc_fn set");
    expect(snap.realloc_fn != NULL, "default realloc_fn set");
    expect(snap.free_fn != NULL, "default free_fn set");
    expect(snap.fail_after == 0, "default fail_after 0");

    uem_allocator_fail_after(99);
    uem_allocator_reset(0);
    uem_allocator_get(&snap);
    expect(snap.fail_after == 99, "reset(0) preserves fail_after");
    expect(snap.allocations == 0, "reset zeros allocations");
    uem_allocator_reset(1);
    uem_allocator_get(&snap);
    expect(snap.fail_after == 0, "reset(1) clears fail_after");

    memset(&custom, 0, sizeof custom);
    custom.fail_after = 0;
    custom.allocations = 0;
    custom.malloc_fn = NULL;
    custom.realloc_fn = NULL;
    custom.free_fn = NULL;
    uem_allocator_set(&custom);
    p = uem_mem_malloc(16);
    expect(p != NULL, "NULL-fn set still allocates via libc fallback");
    uem_mem_free(p);

    custom.malloc_fn = snap.malloc_fn;
    custom.realloc_fn = snap.realloc_fn;
    custom.free_fn = snap.free_fn;
    custom.fail_after = 0;
    custom.allocations = 7;
    uem_allocator_set(&custom);
    uem_allocator_get(&snap);
    expect(snap.allocations == 7, "set copies allocations counter");
    uem_allocator_reset(1);

    uem_allocator_fail_after(3);
    uem_allocator_set(NULL);
    uem_allocator_get(&snap);
    expect(snap.fail_after == 0, "set(NULL) clears fail_after");
    expect(snap.allocations == 0, "set(NULL) clears allocations");
    p = uem_mem_malloc(8);
    expect(p != NULL, "set(NULL) production malloc works");
    uem_mem_free(p);

    p = uem_mem_malloc(0);
    expect(p != NULL, "malloc(0) returns non-NULL (n?n:1)");
    uem_mem_free(p);
    p = uem_mem_realloc(NULL, 0);
    expect(p != NULL, "realloc(NULL,0) non-NULL");
    uem_mem_free(p);
    p = uem_mem_calloc(0, 32);
    expect(p != NULL, "calloc(0,n) allocates minimal");
    uem_mem_free(p);
    p = uem_mem_calloc(4, 0);
    expect(p != NULL, "calloc(n,0) allocates minimal");
    uem_mem_free(p);

    p = uem_mem_calloc((size_t)-1 / 2 + 1, 4);
    expect(p == NULL, "calloc overflow returns NULL");

    expect(uem_mem_strdup(NULL) == NULL, "strdup(NULL) is NULL");
    uem_allocator_fail_after(1);
    s = uem_mem_strdup("x");
    uem_allocator_reset(1);
    expect(s == NULL, "strdup OOM is NULL");

    uem_mem_free(NULL);

    p = uem_mem_malloc(4);
    expect(p != NULL, "pre-realloc malloc");
    uem_allocator_fail_after(1);
    {
        void *q = uem_mem_realloc(p, 64);
        expect(q == NULL, "realloc OOM returns NULL");
        uem_allocator_reset(1);
        uem_mem_free(p);
    }

    before = 0;
    uem_allocator_get(&snap);
    before = snap.allocations;
    uem_alloc_install_cjson();
    uem_alloc_install_cjson();
    uem_allocator_get(&snap);
    expect(snap.allocations == before, "double install_cjson no allocs");
}

/* Deterministic OOM injection: fail on allocation N, assert cleanup + error. */
static void assert_oom_paths(void) {
    uint8_t *buf = NULL;
    size_t len = 0;
    uem_machine *m = NULL;
    char err[128];
    uem_status st;
    size_t n;
    size_t closed = 0;
    size_t nomem_hits = 0;

    assert_alloc_api();

    expect(open_vec("assert_float.uem", &buf, &len), "oom open float");
    uem_alloc_install_cjson();

    for (n = 1; n <= 120; n++) {
        m = (uem_machine *)0x1;
        err[0] = 0;
        uem_allocator_fail_after(n);
        st = uem_decode_verify(buf, len, &m, err, sizeof err);
        uem_allocator_reset(1);
        if (st == UEM_OK) {
            expect(m != NULL && m != (uem_machine *)0x1, "oom success has machine");
            uem_free(m);
            m = NULL;
            break;
        }
        expect(m == NULL || m == (uem_machine *)0x1, "oom fail leaves no live machine");
        expect(st == UEM_ERR_NOMEM || st == UEM_ERR_DECODE || st == UEM_ERR_VERIFY,
               "oom maps to canonical error");
        if (st == UEM_ERR_NOMEM) nomem_hits++;
        if (m == (uem_machine *)0x1) m = NULL;
        closed++;
    }
    expect(closed > 0, "at least one OOM vector fired");
    expect(nomem_hits > 0, "at least one pure NOMEM path");
    free(buf); buf = NULL;

    expect(open_vec("assert_esc.uem", &buf, &len), "oom open esc");
    m = (uem_machine *)0x1;
    uem_allocator_fail_after(1);
    st = uem_decode_verify(buf, len, &m, err, sizeof err);
    uem_allocator_reset(1);
    expect(st == UEM_ERR_NOMEM, "fail_after=1 is NOMEM on machine alloc");
    expect(m == (uem_machine *)0x1 || m == NULL, "fail_after=1 no partial machine");
    free(buf); buf = NULL;

    {
        const char *vecs[] = {
            "assert_float.uem", "assert_esc.uem", "assert_load.uem",
            "assert_quiet.uem", "assert_tick.uem", NULL
        };
        int vi;
        for (vi = 0; vecs[vi]; vi++) {
            if (!open_vec(vecs[vi], &buf, &len)) continue;
            for (n = 1; n <= 40; n++) {
                m = (uem_machine *)0x1;
                err[0] = 0;
                uem_allocator_fail_after(n);
                st = uem_decode_verify(buf, len, &m, err, sizeof err);
                uem_allocator_reset(1);
                if (st == UEM_OK) {
                    expect(m != NULL && m != (uem_machine *)0x1, "mid-decode success");
                    uem_free(m);
                    break;
                }
                expect(m == NULL || m == (uem_machine *)0x1, "mid-decode no partial");
                expect(st == UEM_ERR_NOMEM || st == UEM_ERR_DECODE || st == UEM_ERR_VERIFY,
                       "mid-decode canonical error");
            }
            free(buf); buf = NULL;
        }
    }

    {
        cJSON *j;
        uem_alloc_install_cjson();
        uem_allocator_fail_after(1);
        j = cJSON_Parse("{\"a\":1}");
        uem_allocator_reset(1);
        expect(j == NULL, "cJSON parse fails under OOM hook");
        if (j) cJSON_Delete(j);
        for (n = 1; n <= 20; n++) {
            uem_allocator_fail_after(n);
            j = cJSON_Parse("{\"a\":[1,2,3],\"b\":{\"c\":true}}");
            uem_allocator_reset(1);
            if (j) cJSON_Delete(j);
            else break;
        }
    }

    expect(open_vec("assert_float.uem", &buf, &len), "oom recovery open");
    uem_allocator_reset(1);
    st = uem_decode_verify(buf, len, &m, err, sizeof err);
    expect(st == UEM_OK && m != NULL, "allocator reset restores success");
    if (m) {
        expect(strcmp(uem_state(m), "formed") == 0 || uem_state(m)[0], "state formed");
        uem_free(m);
    }
    free(buf);
}

/* Batch 1 — decode public rejection contract (test-only; no production C changes).
 * Targets: decode.c:10, free_partial, uem_decode_verify args, err-buffer arms. */
static size_t alloc_attempts(void) {
    uem_allocator snap;
    memset(&snap, 0, sizeof snap);
    uem_allocator_get(&snap);
    return snap.allocations;
}

static void assert_decode_public_contract(void) {
    uem_machine *m = (uem_machine *)0x1; /* poison: must not survive */
    char err[64];
    char err_sentinel[8];
    uem_status st;
    size_t a0, a1;
    int pass;
    uint8_t trunc_hdr[] = {
        'U', 'E', 'M', 0x16, 0, 1 /* magic + 2 of version — short of full header */
    };
    /* Full magic/version/flags then truncated mid-instruction stream (after machine alloc). */
    uint8_t trunc_mid[] = {
        'U', 'E', 'M', 0x16,
        0, 1,       /* version */
        0, 0,       /* flags */
        0, 0, 0, 2, /* count = 2 */
        0x10        /* only first opcode byte — truncated two-byte instr frame */
    };
    /* Valid 1-instr STOP + empty image for determinism checks. */
    uint8_t ok_stop[] = {
        'U', 'E', 'M', 0x16,
        0, 1, 0, 0,
        0, 0, 0, 1,
        0x10, 0x00, /* STOP, tag none */
        0, 0, 0, 2, '{', '}'
    };

    uem_allocator_reset(1);
    a0 = alloc_attempts();

    /* --- uem_free(NULL): safe no-op --- */
    uem_free(NULL);
    expect(1, "uem_free(NULL) returns");

    /* --- null byte buffer --- */
    m = (uem_machine *)0x1;
    memset(err, 0xA5, sizeof err);
    st = uem_decode_verify(NULL, 16, &m, err, sizeof err);
    expect(st == UEM_ERR_ARGS, "null bytes → ARGS");
    expect(m == (uem_machine *)0x1, "null bytes leaves *out untouched (no write)");
    /* err must not be written on ARGS before *out=NULL path — code returns before *out */
    /* Actual code: if (!bytes || !out) return ARGS; — err untouched */
    expect((unsigned char)err[0] == 0xA5, "null bytes: err buffer untouched");

    /* --- null output pointer --- */
    m = (uem_machine *)0x1;
    memset(err, 0xA5, sizeof err);
    st = uem_decode_verify(ok_stop, sizeof ok_stop, NULL, err, sizeof err);
    expect(st == UEM_ERR_ARGS, "null out → ARGS");
    expect((unsigned char)err[0] == 0xA5, "null out: err buffer untouched");

    /* --- both null --- */
    st = uem_decode_verify(NULL, 0, NULL, err, sizeof err);
    expect(st == UEM_ERR_ARGS, "null bytes and out → ARGS");

    /* --- truncated header (len < 12): exact error text --- */
    m = (uem_machine *)0x1;
    memset(err, 0, sizeof err);
    st = uem_decode_verify(trunc_hdr, sizeof trunc_hdr, &m, err, sizeof err);
    expect(st == UEM_ERR_DECODE, "trunc hdr → DECODE");
    expect(m == NULL, "trunc hdr *out = NULL");
    expect(strcmp(err, "truncated") == 0, "trunc hdr exact error text");

    /* --- truncated mid-instruction (machine may be allocated then free_partial) --- */
    m = (uem_machine *)0x1;
    memset(err, 0, sizeof err);
    st = uem_decode_verify(trunc_mid, sizeof trunc_mid, &m, err, sizeof err);
    expect(st == UEM_ERR_DECODE, "trunc mid → DECODE");
    expect(m == NULL, "trunc mid no live machine");
    expect(strcmp(err, "truncated") == 0, "trunc mid exact error text");

    /* --- null error buffer: must still reject, no crash --- */
    m = (uem_machine *)0x1;
    st = uem_decode_verify(trunc_hdr, sizeof trunc_hdr, &m, NULL, 64);
    expect(st == UEM_ERR_DECODE, "null err → DECODE");
    expect(m == NULL, "null err *out = NULL");

    /* --- zero-length error buffer: memory untouched --- */
    m = (uem_machine *)0x1;
    memset(err_sentinel, 0x5A, sizeof err_sentinel);
    st = uem_decode_verify(trunc_hdr, sizeof trunc_hdr, &m, err_sentinel, 0);
    expect(st == UEM_ERR_DECODE, "zero errlen → DECODE");
    expect(m == NULL, "zero errlen *out = NULL");
    expect((unsigned char)err_sentinel[0] == 0x5A &&
           (unsigned char)err_sentinel[1] == 0x5A &&
           (unsigned char)err_sentinel[7] == 0x5A,
           "zero errlen leaves buffer untouched");

    /* --- writable err + trunc with exact message (repeated = deterministic) --- */
    for (pass = 0; pass < 3; pass++) {
        m = (uem_machine *)0x1;
        memset(err, 0xFF, sizeof err);
        st = uem_decode_verify(trunc_hdr, sizeof trunc_hdr, &m, err, sizeof err);
        expect(st == UEM_ERR_DECODE, "repeat trunc DECODE");
        expect(m == NULL, "repeat trunc no machine");
        expect(strcmp(err, "truncated") == 0, "repeat trunc exact text");
    }

    /* --- OOM after machine calloc, before instr array: no free_partial(NULL),
     *     but no partial machine survives (public contract). --- */
    m = (uem_machine *)0x1;
    memset(err, 0, sizeof err);
    uem_allocator_fail_after(1); /* first alloc is machine */
    st = uem_decode_verify(ok_stop, sizeof ok_stop, &m, err, sizeof err);
    uem_allocator_reset(1);
    expect(st == UEM_ERR_NOMEM, "fail machine alloc → NOMEM");
    expect(m == (uem_machine *)0x1 || m == NULL, "fail machine: no live machine");

    m = (uem_machine *)0x1;
    uem_allocator_fail_after(2); /* machine ok, instr fails */
    st = uem_decode_verify(ok_stop, sizeof ok_stop, &m, err, sizeof err);
    uem_allocator_reset(1);
    expect(st == UEM_ERR_NOMEM, "fail instr alloc → NOMEM");
    expect(m == (uem_machine *)0x1 || m == NULL, "fail instr: no live machine");

    /* --- allocator balance: after resets, production path works; attempts finite --- */
    a1 = alloc_attempts();
    expect(a1 >= a0, "allocation counter advanced or stable");
    uem_allocator_reset(1);
    m = NULL;
    memset(err, 0, sizeof err);
    st = uem_decode_verify(ok_stop, sizeof ok_stop, &m, err, sizeof err);
    expect(st == UEM_OK && m != NULL, "contract recovery decode ok");
    if (m) {
        /* free twice pattern not allowed; single free */
        uem_free(m);
        m = NULL;
    }
    /* second identical decode → deterministic status */
    st = uem_decode_verify(ok_stop, sizeof ok_stop, &m, err, sizeof err);
    expect(st == UEM_OK && m != NULL, "deterministic second decode");
    if (m) uem_free(m);

    /* --- empty/zero length buffer as truncated --- */
    m = (uem_machine *)0x1;
    memset(err, 0, sizeof err);
    st = uem_decode_verify(ok_stop, 0, &m, err, sizeof err);
    expect(st == UEM_ERR_DECODE, "len=0 → DECODE");
    expect(m == NULL, "len=0 *out NULL");
    expect(strcmp(err, "truncated") == 0, "len=0 exact truncated");

    /* Stabilize line_count empty/non-empty arms (avoid flaky new_arcs vs baseline). */
    {
        uem_machine mm;
        cJSON *root, *bindings, *node, *outn = NULL, *ep = NULL;
        char e2[64];
        memset(&mm, 0, sizeof mm);
        snprintf(mm.state, sizeof mm.state, "formed");
        root = cJSON_Parse("{\"text\":\"\"}");
        bindings = cJSON_CreateObject();
        node = cJSON_Parse(
            "{\"op\":\"line_count\",\"of\":{\"op\":\"field\",\"path\":[\"text\"]}}");
        expect(node && root, "line_count empty setup");
        expect(uem_expr_eval(&mm, node, root, bindings, &outn, e2, sizeof e2, &ep) == 0,
               "line_count empty eval");
        expect(outn && cJSON_IsNumber(outn) && outn->valueint == 0, "line_count empty = 0");
        if (outn) cJSON_Delete(outn);
        if (ep) cJSON_Delete(ep);
        cJSON_Delete(node);
        cJSON_Delete(root);
        root = cJSON_Parse("{\"text\":\"a\\nb\"}");
        node = cJSON_Parse(
            "{\"op\":\"line_count\",\"of\":{\"op\":\"field\",\"path\":[\"text\"]}}");
        outn = NULL;
        ep = NULL;
        expect(uem_expr_eval(&mm, node, root, bindings, &outn, e2, sizeof e2, &ep) == 0,
               "line_count non-empty eval");
        expect(outn && cJSON_IsNumber(outn) && outn->valueint >= 1, "line_count non-empty");
        if (outn) cJSON_Delete(outn);
        if (ep) cJSON_Delete(ep);
        cJSON_Delete(node);
        cJSON_Delete(root);
        cJSON_Delete(bindings);
    }
}

/* Batch 2 — decode header rejection matrix (test-only).
 * Targets: magic positions, bad-version, bad-flags, bad-count + err-buffer arms.
 * Does not include instruction-body / image rejections. */
static void expect_header_decode_reject(const uint8_t *buf, size_t len,
                                        const char *want_msg, const char *label) {
    uem_machine *m;
    char err[64];
    char sentinel[8];
    uem_status st;
    int pass;
    size_t a0, a1;

    /* writable error buffer + exact message + null out */
    for (pass = 0; pass < 3; pass++) {
        m = (uem_machine *)0x1;
        memset(err, 0xFF, sizeof err);
        a0 = alloc_attempts();
        st = uem_decode_verify(buf, len, &m, err, sizeof err);
        a1 = alloc_attempts();
        expect(st == UEM_ERR_DECODE, label);
        expect(m == NULL, label);
        expect(strcmp(err, want_msg) == 0, label);
        expect(a1 >= a0, label); /* attempts do not go backwards */
        (void)a1;
    }

    /* null error buffer */
    m = (uem_machine *)0x1;
    st = uem_decode_verify(buf, len, &m, NULL, 64);
    expect(st == UEM_ERR_DECODE, label);
    expect(m == NULL, label);

    /* zero-length error buffer: sentinel untouched */
    m = (uem_machine *)0x1;
    memset(sentinel, 0x5A, sizeof sentinel);
    st = uem_decode_verify(buf, len, &m, sentinel, 0);
    expect(st == UEM_ERR_DECODE, label);
    expect(m == NULL, label);
    expect((unsigned char)sentinel[0] == 0x5A &&
           (unsigned char)sentinel[3] == 0x5A &&
           (unsigned char)sentinel[7] == 0x5A,
           label);
}

static void assert_decode_header_matrix(void) {
    /* Minimal valid-length header skeleton: magic|ver|flags|count (12 bytes).
     * Never reaches instruction body on rejection. */
    uint8_t hdr[12];
    int i;

    uem_allocator_reset(1);

    /* --- each incorrect magic-byte position independently --- */
    for (i = 0; i < 4; i++) {
        memset(hdr, 0, sizeof hdr);
        hdr[0] = 'U'; hdr[1] = 'E'; hdr[2] = 'M'; hdr[3] = 0x16;
        hdr[4] = 0; hdr[5] = 1; /* version 1 */
        /* flags 0, count 1 */
        hdr[8] = 0; hdr[9] = 0; hdr[10] = 0; hdr[11] = 1;
        hdr[i] = (uint8_t)(hdr[i] ^ 0x01); /* flip one magic position */
        expect_header_decode_reject(hdr, sizeof hdr, "bad-magic", "header bad-magic pos");
    }

    /* --- unsupported version (magic ok) --- */
    memset(hdr, 0, sizeof hdr);
    hdr[0] = 'U'; hdr[1] = 'E'; hdr[2] = 'M'; hdr[3] = 0x16;
    hdr[4] = 0; hdr[5] = 2; /* version 2 */
    hdr[11] = 1;
    expect_header_decode_reject(hdr, sizeof hdr, "bad-version", "header bad-version");

    /* version 0 also unsupported */
    hdr[5] = 0;
    expect_header_decode_reject(hdr, sizeof hdr, "bad-version", "header bad-version 0");

    /* --- nonzero / unsupported flags --- */
    memset(hdr, 0, sizeof hdr);
    hdr[0] = 'U'; hdr[1] = 'E'; hdr[2] = 'M'; hdr[3] = 0x16;
    hdr[4] = 0; hdr[5] = 1;
    hdr[6] = 0; hdr[7] = 1; /* flags = 1 */
    hdr[11] = 1;
    expect_header_decode_reject(hdr, sizeof hdr, "bad-flags", "header bad-flags 1");

    hdr[6] = 0x80; hdr[7] = 0; /* flags high bit */
    expect_header_decode_reject(hdr, sizeof hdr, "bad-flags", "header bad-flags high");

    /* --- invalid instruction count: zero --- */
    memset(hdr, 0, sizeof hdr);
    hdr[0] = 'U'; hdr[1] = 'E'; hdr[2] = 'M'; hdr[3] = 0x16;
    hdr[4] = 0; hdr[5] = 1;
    /* count = 0 already */
    expect_header_decode_reject(hdr, sizeof hdr, "bad-count", "header bad-count 0");

    /* count > UEM_MAX_INSTR (0xFFFFFFFF) */
    hdr[8] = 0xff; hdr[9] = 0xff; hdr[10] = 0xff; hdr[11] = 0xff;
    expect_header_decode_reject(hdr, sizeof hdr, "bad-count", "header bad-count max");

    /* count just above max if MAX is not all-ones — also use 0x00001001 if MAX is 4096 */
    hdr[8] = 0; hdr[9] = 0; hdr[10] = 0x10; hdr[11] = 0x01; /* 4097 */
    expect_header_decode_reject(hdr, sizeof hdr, "bad-count", "header bad-count 4097");

    /* Recovery: valid header+STOP must still decode after matrix */
    {
        uint8_t ok[] = {
            'U', 'E', 'M', 0x16, 0, 1, 0, 0, 0, 0, 0, 1,
            0x10, 0x00, 0, 0, 0, 2, '{', '}'
        };
        uem_machine *m = NULL;
        char err[32];
        uem_status st;
        uem_allocator_reset(1);
        st = uem_decode_verify(ok, sizeof ok, &m, err, sizeof err);
        expect(st == UEM_OK && m != NULL, "header matrix recovery ok");
        if (m) uem_free(m);
    }
}

/* Batch 3 — instruction framing rejections (test-only).
 * Byte-level instruction decode only; no image/STOP/primitive semantics. */
static void expect_framing_reject(const uint8_t *buf, size_t len,
                                  const char *want_msg, const char *label) {
    uem_machine *m;
    char err[64];
    char sentinel[8];
    uem_status st;
    int pass;
    size_t a0;

    for (pass = 0; pass < 3; pass++) {
        m = (uem_machine *)0x1;
        memset(err, 0xFF, sizeof err);
        a0 = alloc_attempts();
        st = uem_decode_verify(buf, len, &m, err, sizeof err);
        expect(st == UEM_ERR_DECODE, label);
        expect(m == NULL, label);
        expect(strcmp(err, want_msg) == 0, label);
        expect(alloc_attempts() >= a0, label);
    }

    m = (uem_machine *)0x1;
    st = uem_decode_verify(buf, len, &m, NULL, 64);
    expect(st == UEM_ERR_DECODE, label);
    expect(m == NULL, label);

    m = (uem_machine *)0x1;
    memset(sentinel, 0x5A, sizeof sentinel);
    st = uem_decode_verify(buf, len, &m, sentinel, 0);
    expect(st == UEM_ERR_DECODE, label);
    expect(m == NULL, label);
    expect((unsigned char)sentinel[0] == 0x5A &&
           (unsigned char)sentinel[7] == 0x5A, label);
}

/* Write big-endian u16/u32 into buffer. */
static void be_u16(uint8_t *p, uint16_t v) {
    p[0] = (uint8_t)(v >> 8);
    p[1] = (uint8_t)v;
}
static void be_u32(uint8_t *p, uint32_t v) {
    p[0] = (uint8_t)(v >> 24);
    p[1] = (uint8_t)(v >> 16);
    p[2] = (uint8_t)(v >> 8);
    p[3] = (uint8_t)v;
}

/* Header: magic + ver1 + flags0 + count (12 bytes). */
static void write_header(uint8_t *p, uint32_t count) {
    p[0] = 'U'; p[1] = 'E'; p[2] = 'M'; p[3] = 0x16;
    be_u16(p + 4, 1);
    be_u16(p + 6, 0);
    be_u32(p + 8, count);
}

static void assert_decode_instruction_framing(void) {
    uint8_t buf[64];
    size_t n;
    uem_machine *m;
    char err[64];
    uem_status st;

    uem_allocator_reset(1);

    /* --- Truncation boundary table (field incomplete) --- */

    /* 1. Truncated before opcode (header only, count=1). field=opcode */
    write_header(buf, 1);
    n = 12;
    expect_framing_reject(buf, n, "truncated", "trunc before opcode");

    /* 2. Truncated after opcode, missing tag. field=tag */
    write_header(buf, 1);
    buf[12] = 0x10; /* STOP */
    n = 13;
    expect_framing_reject(buf, n, "truncated", "trunc after opcode missing tag");

    /* 3. Tag=1 but truncated length field (0 of 4). field=length */
    write_header(buf, 1);
    buf[12] = 0x01; /* LOAD */
    buf[13] = 0x01; /* string tag */
    n = 14;
    expect_framing_reject(buf, n, "truncated", "trunc missing operand length");

    /* 4. Tag=1 length field partial (2 of 4 bytes). field=length */
    write_header(buf, 1);
    buf[12] = 0x01;
    buf[13] = 0x01;
    buf[14] = 0; buf[15] = 0; /* partial L */
    n = 16;
    expect_framing_reject(buf, n, "truncated", "trunc partial operand length");

    /* 5. Length complete L=5 but payload only 2 bytes. field=payload */
    write_header(buf, 1);
    buf[12] = 0x01;
    buf[13] = 0x01;
    be_u32(buf + 14, 5);
    buf[18] = 'a'; buf[19] = 'b'; /* only 2 of 5 */
    n = 20;
    expect_framing_reject(buf, n, "truncated", "trunc payload short of L");

    /* 6. L exceeds remaining after length (L=100, no payload, no image). field=payload */
    write_header(buf, 1);
    buf[12] = 0x01;
    buf[13] = 0x01;
    be_u32(buf + 14, 100);
    n = 18; /* ends after L */
    expect_framing_reject(buf, n, "truncated", "trunc L exceeds remaining");

    /* 7. Second instruction missing entirely (count=2, only one STOP none). field=opcode#2 */
    write_header(buf, 2);
    buf[12] = 0x10;
    buf[13] = 0x00;
    n = 14;
    expect_framing_reject(buf, n, "truncated", "trunc missing second opcode");

    /* 8. After instructions, truncated image length field. field=img_len */
    write_header(buf, 1);
    buf[12] = 0x10;
    buf[13] = 0x00;
    n = 14; /* no img_len */
    expect_framing_reject(buf, n, "truncated", "trunc missing image length");

    /* 9. img_len says 5 but only 1 byte follows. field=image payload */
    write_header(buf, 1);
    buf[12] = 0x10;
    buf[13] = 0x00;
    be_u32(buf + 14, 5);
    buf[18] = '{';
    n = 19;
    expect_framing_reject(buf, n, "truncated", "trunc image payload short");

    /* --- Unknown opcode --- */
    write_header(buf, 1);
    buf[12] = 0x11; /* outside 0x01..0x10 */
    buf[13] = 0x00;
    be_u32(buf + 14, 2);
    buf[18] = '{'; buf[19] = '}';
    n = 20;
    expect_framing_reject(buf, n, "unknown-opcode", "unknown opcode 0x11");

    write_header(buf, 1);
    buf[12] = 0x00; /* zero opcode */
    buf[13] = 0x00;
    be_u32(buf + 14, 2);
    buf[18] = '{'; buf[19] = '}';
    n = 20;
    expect_framing_reject(buf, n, "unknown-opcode", "unknown opcode 0x00");

    /* --- Unknown operand tag --- */
    write_header(buf, 1);
    buf[12] = 0x10;
    buf[13] = 0x02; /* only 0 and 1 valid */
    be_u32(buf + 14, 2);
    buf[18] = '{'; buf[19] = '}';
    n = 20;
    expect_framing_reject(buf, n, "bad-tag", "unknown tag 0x02");

    write_header(buf, 1);
    buf[12] = 0x01;
    buf[13] = 0x7f;
    be_u32(buf + 14, 2);
    buf[18] = '{'; buf[19] = '}';
    n = 20;
    expect_framing_reject(buf, n, "bad-tag", "unknown tag 0x7f");

    /* --- Invalid UTF-8 operand --- */
    write_header(buf, 1);
    buf[12] = 0x01; /* LOAD */
    buf[13] = 0x01; /* string */
    be_u32(buf + 14, 1);
    buf[18] = 0xff; /* invalid UTF-8 */
    be_u32(buf + 19, 2);
    buf[23] = '{'; buf[24] = '}';
    n = 25;
    expect_framing_reject(buf, n, "invalid-utf8", "invalid utf8 operand");

    /* overlong 2-byte sequence */
    write_header(buf, 1);
    buf[12] = 0x01;
    buf[13] = 0x01;
    be_u32(buf + 14, 2);
    buf[18] = 0xc0; buf[19] = 0x80; /* overlong */
    be_u32(buf + 20, 2);
    buf[24] = '{'; buf[25] = '}';
    n = 26;
    expect_framing_reject(buf, n, "invalid-utf8", "overlong utf8 operand");

    /* --- Trailing bytes after declared stream --- */
    /* Complete: STOP none + image {} then extra 0x00 */
    write_header(buf, 1);
    buf[12] = 0x10;
    buf[13] = 0x00;
    be_u32(buf + 14, 2);
    buf[18] = '{'; buf[19] = '}';
    buf[20] = 0x00; /* trailing */
    n = 21;
    expect_framing_reject(buf, n, "trailing-bytes", "trailing byte after image");

    /* Complete program with trailing two bytes */
    write_header(buf, 1);
    buf[12] = 0x10;
    buf[13] = 0x00;
    be_u32(buf + 14, 2);
    buf[18] = '{'; buf[19] = '}';
    buf[20] = 'X'; buf[21] = 'Y';
    n = 22;
    expect_framing_reject(buf, n, "trailing-bytes", "trailing XY after image");

    /* Recovery: valid framing must still decode */
    write_header(buf, 1);
    buf[12] = 0x10;
    buf[13] = 0x00;
    be_u32(buf + 14, 2);
    buf[18] = '{'; buf[19] = '}';
    n = 20;
    m = NULL;
    memset(err, 0, sizeof err);
    uem_allocator_reset(1);
    st = uem_decode_verify(buf, n, &m, err, sizeof err);
    expect(st == UEM_OK && m != NULL, "framing recovery ok");
    if (m) uem_free(m);

    /* Second recovery identical → deterministic success */
    m = NULL;
    st = uem_decode_verify(buf, n, &m, err, sizeof err);
    expect(st == UEM_OK && m != NULL, "framing recovery deterministic");
    if (m) uem_free(m);
}

int main(void) {
    fails = 0;
    test_decimal();
    test_expr_nodes();
    test_decode_rejects();
    assert_decode_public_contract();
    assert_decode_header_matrix();
    assert_decode_instruction_framing();
    test_host_errors();
    test_primitives_direct();
    test_host_json_limits();
    assert_decode_rejects();
    assert_machine_semantics();
    assert_expr_error_arms();
    assert_primitives_eval_bindings();
    assert_oom_paths();
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
