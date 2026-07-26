#include "alloc.h"
#include "../third_party/cJSON.h"
#include <stdlib.h>
#include <string.h>

static void *libc_malloc(size_t n) { return malloc(n); }
static void *libc_realloc(void *p, size_t n) { return realloc(p, n); }
static void libc_free(void *p) { free(p); }

static uem_allocator g_alloc = {
    libc_malloc,
    libc_realloc,
    libc_free,
    0,
    0
};

static int g_cjson_hooks_installed = 0;

void uem_allocator_set(const uem_allocator *a) {
    if (!a) {
        g_alloc.malloc_fn = libc_malloc;
        g_alloc.realloc_fn = libc_realloc;
        g_alloc.free_fn = libc_free;
        g_alloc.fail_after = 0;
        g_alloc.allocations = 0;
        return;
    }
    g_alloc.malloc_fn = a->malloc_fn ? a->malloc_fn : libc_malloc;
    g_alloc.realloc_fn = a->realloc_fn ? a->realloc_fn : libc_realloc;
    g_alloc.free_fn = a->free_fn ? a->free_fn : libc_free;
    g_alloc.fail_after = a->fail_after;
    g_alloc.allocations = a->allocations;
}

void uem_allocator_reset(int clear_fail) {
    g_alloc.allocations = 0;
    if (clear_fail) g_alloc.fail_after = 0;
}

void uem_allocator_get(uem_allocator *out) {
    if (!out) return;
    *out = g_alloc;
}

void uem_allocator_fail_after(size_t n) {
    g_alloc.fail_after = n;
    g_alloc.allocations = 0;
}

static int should_fail(void) {
    g_alloc.allocations++;
    if (g_alloc.fail_after > 0 && g_alloc.allocations >= g_alloc.fail_after)
        return 1;
    return 0;
}

void *uem_mem_malloc(size_t n) {
    if (should_fail()) return NULL;
    return g_alloc.malloc_fn(n ? n : 1);
}

void *uem_mem_calloc(size_t count, size_t size) {
    size_t n;
    void *p;
    if (count != 0 && size > (size_t)-1 / count) return NULL;
    n = count * size;
    p = uem_mem_malloc(n ? n : 1);
    if (p) memset(p, 0, n ? n : 1);
    return p;
}

void *uem_mem_realloc(void *p, size_t n) {
    if (should_fail()) return NULL;
    return g_alloc.realloc_fn(p, n ? n : 1);
}

void uem_mem_free(void *p) {
    if (p) g_alloc.free_fn(p);
}

char *uem_mem_strdup(const char *s) {
    size_t n;
    char *p;
    if (!s) return NULL;
    n = strlen(s) + 1;
    p = (char *)uem_mem_malloc(n);
    if (p) memcpy(p, s, n);
    return p;
}

/* cJSON only hooks malloc/free; realloc stays internal to cJSON.
 * We still fail cJSON malloc via the same attempt counter. */
static void *cjson_malloc_hook(size_t sz) {
    return uem_mem_malloc(sz);
}
static void cjson_free_hook(void *ptr) {
    uem_mem_free(ptr);
}

void uem_alloc_install_cjson(void) {
    cJSON_Hooks hooks;
    if (g_cjson_hooks_installed) return;
    hooks.malloc_fn = cjson_malloc_hook;
    hooks.free_fn = cjson_free_hook;
    cJSON_InitHooks(&hooks);
    g_cjson_hooks_installed = 1;
}
