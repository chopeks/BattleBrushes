#ifndef _XXTEA_H
#define _XXTEA_H

#include <stdint.h>

void decrypt(uint32_t *values, uint32_t count, const uint32_t key[4]);
void encrypt(uint32_t *values, uint32_t count, const uint32_t key[4]);

#endif _XXTEA_H