/* Wasm host skeleton — portable core, no POSIX assumptions in API.
 * L12: Wasm-host support requires golden pass in ≥2 independent runtimes.
 * This is not direct chip support.
 */
#include "uem.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifdef __wasi__
/* Minimal WASI entry for compile checks. Full harness is scripts/run_l12_report.py */
int main(void) {
    printf("uem-wasm host=wasm format=%d registry=%d\n",
           UEM_FORMAT_VERSION, UEM_REGISTRY_VERSION);
    return 0;
}
#else
/* Native stub so the file always compiles when selected without WASI. */
int main(void) {
    fprintf(stderr, "build with -target wasm32-wasi for Wasm artifact\n");
    return 2;
}
#endif
