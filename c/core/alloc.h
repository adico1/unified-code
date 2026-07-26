/* Audited allocator boundary for UEM C core.
 * Production default: libc. Tests inject deterministic failures.
 * No test-only production semantics — fail_after is runtime state only.
 * Public typedef lives in include/uem.h; this header adds uem_mem_* entry points.
 */
#ifndef UEM_ALLOC_H
#define UEM_ALLOC_H

#include "../include/uem.h"
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Core allocation entry points — all core heap traffic goes here.
 * Named uem_mem_* to avoid clash with uem_free(uem_machine*). */
void *uem_mem_malloc(size_t n);
void *uem_mem_calloc(size_t count, size_t size);
void *uem_mem_realloc(void *p, size_t n);
void uem_mem_free(void *p);
char *uem_mem_strdup(const char *s);

#ifdef __cplusplus
}
#endif
#endif
