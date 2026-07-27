#include "decimal.h"
#include <ctype.h>
#include <stdio.h>
#include <string.h>

/* Fixed UEM_DEC_SCALE=10: table covers every legal places/scale argument. */
static int64_t pow10i(int n) {
    static const int64_t T[UEM_DEC_SCALE + 1] = {
        1LL,
        10LL,
        100LL,
        1000LL,
        10000LL,
        100000LL,
        1000000LL,
        10000000LL,
        100000000LL,
        1000000000LL,
        10000000000LL
    };
    if (n < 0) return 1;
    return T[n];
}

/* Call sites only pass scale/unit > 0. a may be signed (quantize q). */
static int mul_ok(int64_t a, int64_t b, int64_t *out) {
    if (a == 0) { *out = 0; return 1; }
    if (a > 0) {
        if (a > INT64_MAX / b) return 0;
    } else {
        if (a < INT64_MIN / b) return 0;
    }
    *out = a * b;
    return 1;
}

static int add_ok(int64_t a, int64_t b, int64_t *out) {
    if (b > 0) {
        if (a > INT64_MAX - b) return 0;
    } else if (b < 0) {
        if (a < INT64_MIN - b) return 0;
    }
    *out = a + b;
    return 1;
}

uem_dec uem_dec_from_i64(int64_t v) {
    uem_dec d;
    int64_t scale = pow10i(UEM_DEC_SCALE);
    d.ok = 0;
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
        while (isdigit((unsigned char)*p)) p++;
    }
    if (*p != 0) return d;
    scale = pow10i(UEM_DEC_SCALE);
    if (!mul_ok(intpart, scale, &scaled_int)) return d;
    {
        /* frac < 10^UEM_DEC_SCALE and fscale = 10^(SCALE-frac_digits) so
         * frac * fscale < 10^SCALE always fits in int64 with room. */
        int64_t fscale = pow10i(UEM_DEC_SCALE - frac_digits);
        scaled_frac = frac * fscale;
    }
    if (!add_ok(scaled_int, scaled_frac, &combined)) return d;
    d.coeff = sign < 0 ? -combined : combined;
    d.ok = 1;
    return d;
}

int uem_dec_cmp(uem_dec a, uem_dec b) {
    if (!a.ok) return 0;
    if (!b.ok) return 0;
    if (a.coeff < b.coeff) return -1;
    if (a.coeff > b.coeff) return 1;
    return 0;
}

uem_dec uem_dec_add(uem_dec a, uem_dec b) {
    uem_dec r;
    r.ok = 0;
    if (!a.ok) return r;
    if (!b.ok) return r;
    if (!add_ok(a.coeff, b.coeff, &r.coeff)) return r;
    r.ok = 1;
    return r;
}

uem_dec uem_dec_mul(uem_dec a, uem_dec b) {
    uem_dec r;
    __int128 prod;
    int64_t scale;
    r.ok = 0;
    if (!a.ok) return r;
    if (!b.ok) return r;
    scale = pow10i(UEM_DEC_SCALE);
    prod = (__int128)a.coeff * (__int128)b.coeff;
    {
        __int128 q = prod / scale;
        if (q > INT64_MAX) return r;
        if (q < INT64_MIN) return r;
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
    q = a.coeff / unit;
    rem = a.coeff % unit;
    if (rem < 0) rem = -rem;
    if (strcmp(mode, "ROUND_DOWN") == 0) {
        /* truncate toward zero */
    } else if (strcmp(mode, "ROUND_UP") == 0) {
        if (rem != 0) {
            if (a.coeff >= 0) q += 1;
            else q -= 1;
        }
    } else if (strcmp(mode, "ROUND_HALF_EVEN") == 0) {
        int bump = 0;
        if (rem * 2 > unit) bump = 1;
        else if (rem * 2 == unit && (q & 1)) bump = 1;
        if (bump) {
            if (a.coeff >= 0) q += 1;
            else q -= 1;
        }
    } else {
        if (rem * 2 >= unit) {
            if (a.coeff >= 0) q += 1;
            else q -= 1;
        }
    }
    /* Checked mul: ROUND_UP near INT64_MAX with unit>1 can overflow. */
    if (!mul_ok(q, unit, &r.coeff)) return r;
    r.ok = 1;
    return r;
}

int uem_dec_format(uem_dec a, int places, char *buf, size_t cap) {
    char tmp[64];
    int n;
    int64_t scaled, base, ipart, fpart, div;
    if (!a.ok) return -1;
    if (!buf) return -1;
    if (cap < 4) return -1;
    if (places < 0 || places > UEM_DEC_SCALE) return -1;
    div = pow10i(UEM_DEC_SCALE - places);
    scaled = a.coeff / div;
    base = pow10i(places);
    ipart = scaled / base;
    fpart = scaled % base;
    if (fpart < 0) fpart = -fpart;
    if (scaled < 0) {
        if (ipart == 0) {
            n = snprintf(tmp, sizeof tmp, "-0.%0*lld", places, (long long)fpart);
        } else {
            n = snprintf(tmp, sizeof tmp, "%lld.%0*lld", (long long)ipart, places, (long long)fpart);
        }
    } else {
        n = snprintf(tmp, sizeof tmp, "%lld.%0*lld", (long long)ipart, places, (long long)fpart);
    }
    /* snprintf of fixed-scale decimal into 64-byte tmp never returns < 0. */
    if ((size_t)n >= cap) return -1;
    memcpy(buf, tmp, (size_t)n + 1);
    return 0;
}
