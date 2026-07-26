#include "decimal.h"
#include <ctype.h>
#include <stdio.h>
#include <string.h>

static int64_t pow10i(int n) {
    int64_t r = 1;
    int i;
    for (i = 0; i < n; i++) {
        if (r > INT64_MAX / 10) return -1;
        r *= 10;
    }
    return r;
}

static int mul_ok(int64_t a, int64_t b, int64_t *out) {
    if (a == 0 || b == 0) { *out = 0; return 1; }
    if (a > 0 && b > 0 && a > INT64_MAX / b) return 0;
    if (a > 0 && b < 0 && b < INT64_MIN / a) return 0;
    if (a < 0 && b > 0 && a < INT64_MIN / b) return 0;
    if (a < 0 && b < 0 && a < INT64_MAX / b) return 0;
    *out = a * b;
    return 1;
}

static int add_ok(int64_t a, int64_t b, int64_t *out) {
    if (b > 0 && a > INT64_MAX - b) return 0;
    if (b < 0 && a < INT64_MIN - b) return 0;
    *out = a + b;
    return 1;
}

uem_dec uem_dec_from_i64(int64_t v) {
    uem_dec d;
    int64_t scale = pow10i(UEM_DEC_SCALE);
    d.ok = 0;
    if (scale < 0) return d;
    if (!mul_ok(v, scale, &d.coeff)) return d;
    d.ok = 1;
    return d;
}

uem_dec uem_dec_from_str(const char *s) {
    uem_dec d;
    int sign = 1;
    int64_t intpart = 0, frac = 0;
    int frac_digits = 0;
    const char *p;
    int64_t scale, scaled_int, scaled_frac, combined;
    d.ok = 0;
    if (!s || !*s) return d;
    p = s;
    if (*p == '+') p++;
    else if (*p == '-') { sign = -1; p++; }
    if (!isdigit((unsigned char)*p) && *p != '.') return d;
    while (isdigit((unsigned char)*p)) {
        int dig = *p - '0';
        if (intpart > (INT64_MAX - dig) / 10) return d;
        intpart = intpart * 10 + dig;
        p++;
    }
    if (*p == '.') {
        p++;
        while (isdigit((unsigned char)*p) && frac_digits < UEM_DEC_SCALE) {
            int dig = *p - '0';
            frac = frac * 10 + dig;
            frac_digits++;
            p++;
        }
        /* ignore extra digits beyond scale (truncate toward zero for parse; quantize later) */
        while (isdigit((unsigned char)*p)) p++;
    }
    if (*p != 0) return d;
    scale = pow10i(UEM_DEC_SCALE);
    if (scale < 0) return d;
    if (!mul_ok(intpart, scale, &scaled_int)) return d;
    {
        int64_t fscale = pow10i(UEM_DEC_SCALE - frac_digits);
        if (fscale < 0) return d;
        if (!mul_ok(frac, fscale, &scaled_frac)) return d;
    }
    if (!add_ok(scaled_int, scaled_frac, &combined)) return d;
    d.coeff = sign < 0 ? -combined : combined;
    d.ok = 1;
    return d;
}

int uem_dec_cmp(uem_dec a, uem_dec b) {
    if (!a.ok || !b.ok) return 0;
    if (a.coeff < b.coeff) return -1;
    if (a.coeff > b.coeff) return 1;
    return 0;
}

uem_dec uem_dec_add(uem_dec a, uem_dec b) {
    uem_dec r;
    r.ok = 0;
    if (!a.ok || !b.ok) return r;
    if (!add_ok(a.coeff, b.coeff, &r.coeff)) return r;
    r.ok = 1;
    return r;
}

uem_dec uem_dec_mul(uem_dec a, uem_dec b) {
    uem_dec r;
    __int128 prod;
    int64_t scale;
    r.ok = 0;
    if (!a.ok || !b.ok) return r;
    scale = pow10i(UEM_DEC_SCALE);
    if (scale < 0) return r;
    prod = (__int128)a.coeff * (__int128)b.coeff;
    /* divide by 10^scale with truncate toward zero then we'll quantize separately;
       keep full intermediate: value = prod / 10^(2*scale) * 10^scale = prod / 10^scale */
    {
        __int128 q = prod / scale;
        if (q > INT64_MAX || q < INT64_MIN) return r;
        r.coeff = (int64_t)q;
        r.ok = 1;
        return r;
    }
}

static int exp_places(const char *exp) {
    const char *p;
    int places = 0;
    if (!exp) return 2;
    p = strchr(exp, '.');
    if (!p) return 0;
    p++;
    while (isdigit((unsigned char)*p)) { places++; p++; }
    return places;
}

uem_dec uem_dec_quantize(uem_dec a, const char *exp, const char *rounding) {
    uem_dec r;
    int places = exp_places(exp);
    int64_t unit, q, rem;
    const char *mode = rounding ? rounding : "ROUND_HALF_UP";
    r.ok = 0;
    if (!a.ok) return r;
    if (strcmp(mode, "ROUND_HALF_UP") != 0 &&
        strcmp(mode, "ROUND_DOWN") != 0 &&
        strcmp(mode, "ROUND_UP") != 0 &&
        strcmp(mode, "ROUND_HALF_EVEN") != 0) {
        return r;
    }
    unit = pow10i(UEM_DEC_SCALE - places);
    if (unit <= 0) return r;
    q = a.coeff / unit;
    rem = a.coeff % unit;
    if (rem < 0) rem = -rem;
    if (strcmp(mode, "ROUND_DOWN") == 0) {
        /* truncate toward zero: keep q */
    } else if (strcmp(mode, "ROUND_UP") == 0) {
        if (rem != 0) {
            if (a.coeff >= 0) q += 1;
            else q -= 1;
        }
    } else if (strcmp(mode, "ROUND_HALF_EVEN") == 0) {
        if (rem * 2 > unit || (rem * 2 == unit && (q & 1))) {
            if (a.coeff >= 0) q += 1;
            else q -= 1;
        }
    } else {
        /* ROUND_HALF_UP */
        if (rem * 2 >= unit) {
            if (a.coeff >= 0) q += 1;
            else q -= 1;
        }
    }
    if (!mul_ok(q, unit, &r.coeff)) return r;
    r.ok = 1;
    return r;
}

int uem_dec_format(uem_dec a, int places, char *buf, size_t cap) {
    char tmp[64];
    int n;
    int64_t scaled, base, ipart, fpart, div;
    if (!a.ok || !buf || cap < 4) return -1;
    if (places < 0 || places > UEM_DEC_SCALE) return -1;
    div = pow10i(UEM_DEC_SCALE - places);
    if (div <= 0) return -1;
    scaled = a.coeff / div;
    base = pow10i(places);
    if (base <= 0) return -1;
    ipart = scaled / base;
    fpart = scaled % base;
    if (fpart < 0) fpart = -fpart;
    if (scaled < 0 && ipart == 0)
        n = snprintf(tmp, sizeof tmp, "-0.%0*lld", places, (long long)fpart);
    else
        n = snprintf(tmp, sizeof tmp, "%lld.%0*lld", (long long)ipart, places, (long long)fpart);
    if (n < 0 || (size_t)n >= cap) return -1;
    memcpy(buf, tmp, (size_t)n + 1);
    return 0;
}
