#ifndef UEM_DECIMAL_H
#define UEM_DECIMAL_H
#include <stddef.h>
#include <stdint.h>

/* Fixed-scale decimal: value = coeff / 10^DEC_SCALE (DEC_SCALE=10). */
#define UEM_DEC_SCALE 10

typedef struct {
    int64_t coeff; /* checked arithmetic */
    int ok;
} uem_dec;

uem_dec uem_dec_from_str(const char *s);
uem_dec uem_dec_from_i64(int64_t v);
int uem_dec_cmp(uem_dec a, uem_dec b);
uem_dec uem_dec_add(uem_dec a, uem_dec b);
uem_dec uem_dec_mul(uem_dec a, uem_dec b);
/* quantize to exp like "0.01" with ROUND_HALF_UP */
uem_dec uem_dec_quantize(uem_dec a, const char *exp, const char *rounding);
/* format with fixed places (e.g. 2 -> "1.00") into buf */
int uem_dec_format(uem_dec a, int places, char *buf, size_t cap);

#endif
