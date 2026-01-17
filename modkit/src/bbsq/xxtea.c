#include "xxtea.h"

#define DELTA 0x9e3779b9
#define MX(p) (((z>>5^y<<2) + (y>>3^z<<4)) ^ ((sum^y) + (key[((p)&3)^e] ^ z)))

void decrypt(uint32_t *values, uint32_t count, const uint32_t key[4])
{
    uint32_t rounds = 6 + 52/count, sum = rounds*DELTA, y = values[0], z;
    do
    {
        uint32_t e = (sum >> 2) & 3;
        for (uint32_t p = count-1; p; p--)
        {
            z = values[p-1];
            y = values[p] -= MX(p);
        }
        z = values[count-1];
        y = values[0] -= MX(0);
        sum -= DELTA;
    } while (--rounds);
}

void encrypt(uint32_t *values, uint32_t count, const uint32_t key[4])
{
    uint32_t rounds = 6 + 52/count, sum = 0, y, z = values[count-1];
    do
    {
        sum += DELTA;
        uint32_t e = (sum >> 2) & 3, p;
        for (p = 0; p < count-1; p++)
        {
            y = values[p+1];
            z = values[p] += MX(p);
        }
        y = values[0];
        z = values[count-1] += MX(p);
    } while (--rounds);
}
