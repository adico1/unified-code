/* Compact SHA-256 — public domain style implementation. */
#include "sha256.h"
#include <string.h>

static uint32_t rotr(uint32_t x, uint32_t n) { return (x >> n) | (x << (32 - n)); }

static void transform(uint32_t state[8], const uint8_t block[64]) {
    static const uint32_t K[64] = {
        0x428a2f98u,0x71374491u,0xb5c0fbcfu,0xe9b5dba5u,0x3956c25bu,0x59f111f1u,0x923f82a4u,0xab1c5ed5u,
        0xd807aa98u,0x12835b01u,0x243185beu,0x550c7dc3u,0x72be5d74u,0x80deb1feu,0x9bdc06a7u,0xc19bf174u,
        0xe49b69c1u,0xefbe4786u,0x0fc19dc6u,0x240ca1ccu,0x2de92c6fu,0x4a7484aau,0x5cb0a9dcu,0x76f988dau,
        0x983e5152u,0xa831c66du,0xb00327c8u,0xbf597fc7u,0xc6e00bf3u,0xd5a79147u,0x06ca6351u,0x14292967u,
        0x27b70a85u,0x2e1b2138u,0x4d2c6dfcu,0x53380d13u,0x650a7354u,0x766a0abbu,0x81c2c92eu,0x92722c85u,
        0xa2bfe8a1u,0xa81a664bu,0xc24b8b70u,0xc76c51a3u,0xd192e819u,0xd6990624u,0xf40e3585u,0x106aa070u,
        0x19a4c116u,0x1e376c08u,0x2748774cu,0x34b0bcb5u,0x391c0cb3u,0x4ed8aa4au,0x5b9cca4fu,0x682e6ff3u,
        0x748f82eeu,0x78a5636fu,0x84c87814u,0x8cc70208u,0x90befffau,0xa4506cebu,0xbef9a3f7u,0xc67178f2u
    };
    uint32_t w[64];
    uint32_t a,b,c,d,e,f,g,h,i,t1,t2,s0,s1,maj,ch;
    for (i = 0; i < 16; i++) {
        w[i] = ((uint32_t)block[i*4] << 24) | ((uint32_t)block[i*4+1] << 16) |
               ((uint32_t)block[i*4+2] << 8) | (uint32_t)block[i*4+3];
    }
    for (i = 16; i < 64; i++) {
        s0 = rotr(w[i-15],7) ^ rotr(w[i-15],18) ^ (w[i-15] >> 3);
        s1 = rotr(w[i-2],17) ^ rotr(w[i-2],19) ^ (w[i-2] >> 10);
        w[i] = w[i-16] + s0 + w[i-7] + s1;
    }
    a=state[0]; b=state[1]; c=state[2]; d=state[3];
    e=state[4]; f=state[5]; g=state[6]; h=state[7];
    for (i = 0; i < 64; i++) {
        s1 = rotr(e,6) ^ rotr(e,11) ^ rotr(e,25);
        ch = (e & f) ^ ((~e) & g);
        t1 = h + s1 + ch + K[i] + w[i];
        s0 = rotr(a,2) ^ rotr(a,13) ^ rotr(a,22);
        maj = (a & b) ^ (a & c) ^ (b & c);
        t2 = s0 + maj;
        h=g; g=f; f=e; e=d+t1; d=c; c=b; b=a; a=t1+t2;
    }
    state[0]+=a; state[1]+=b; state[2]+=c; state[3]+=d;
    state[4]+=e; state[5]+=f; state[6]+=g; state[7]+=h;
}

void uem_sha256(const uint8_t *data, size_t len, uint8_t out[32]) {
    uint32_t state[8] = {
        0x6a09e667u,0xbb67ae85u,0x3c6ef372u,0xa54ff53au,
        0x510e527fu,0x9b05688cu,0x1f83d9abu,0x5be0cd19u
    };
    uint8_t block[64];
    size_t i, rem = len;
    const uint8_t *p = data;
    uint64_t bitlen = (uint64_t)len * 8ull;
    while (rem >= 64) {
        transform(state, p);
        p += 64; rem -= 64;
    }
    memset(block, 0, 64);
    if (rem) memcpy(block, p, rem);
    block[rem] = 0x80;
    if (rem >= 56) {
        transform(state, block);
        memset(block, 0, 64);
    }
    for (i = 0; i < 8; i++)
        block[63 - i] = (uint8_t)((bitlen >> (8 * i)) & 0xff);
    transform(state, block);
    for (i = 0; i < 8; i++) {
        out[i*4]   = (uint8_t)(state[i] >> 24);
        out[i*4+1] = (uint8_t)(state[i] >> 16);
        out[i*4+2] = (uint8_t)(state[i] >> 8);
        out[i*4+3] = (uint8_t)(state[i]);
    }
}

void uem_sha256_hex(const uint8_t *data, size_t len, char out_hex[65]) {
    static const char *hexd = "0123456789abcdef";
    uint8_t dig[32];
    int i;
    uem_sha256(data, len, dig);
    for (i = 0; i < 32; i++) {
        out_hex[i*2]   = hexd[(dig[i] >> 4) & 0xf];
        out_hex[i*2+1] = hexd[dig[i] & 0xf];
    }
    out_hex[64] = 0;
}
