/* SPDX-License-Identifier: MIT */
/* SPDX-FileCopyrightText: 2026 japes98 */
/* E-1: the state fwtest starts an image in (boot.S saved the registers),
   the block r0 points at, what the code window shows past the image, and
   which RAM banks hold a written word. Then halt. */
#include "exp.h"

extern const u32 image_end[];

static u32 holds(u32 addr)
{
    volatile u32 *p = (volatile u32 *)addr;
    *p = 0x5a5aa5a5u;
    return *p == 0x5a5aa5a5u;
}

int main(void)
{
    const volatile u32 *blk = (const volatile u32 *)OUT(0);
    for (u32 i = 0; i < 16; i++)
        REG(0x01c00200u + 4u * i) = blk[i];
    OUT(24) = image_end[0];        /* first word past the image */
    OUT(25) = image_end[1024];     /* 4 KiB further on */
    OUT(26) = holds(0x01c7fdfcu);  /* main RAM, below the vector table */
    OUT(27) = holds(0x01cffffcu);  /* the last word of fwtest's 1 MiB */
    OUT(28) = holds(0x01f3fffcu);  /* the SRAM banks' last word */
    OUT(29) = holds(0x0407fffcu);  /* the second RAM bank's last word */
    return 0;
}
