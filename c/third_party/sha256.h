/* Public-domain SHA-256 (compact). */
#ifndef UEM_SHA256_H
#define UEM_SHA256_H
#include <stddef.h>
#include <stdint.h>

void uem_sha256(const uint8_t *data, size_t len, uint8_t out[32]);
void uem_sha256_hex(const uint8_t *data, size_t len, char out_hex[65]);

#endif
