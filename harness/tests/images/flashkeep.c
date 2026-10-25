/* SPDX-License-Identifier: MIT */
/* SPDX-FileCopyrightText: 2026 japes98 */
/* A count kept in the flash across runs. From RAM: reads the word at chip
   offset 0x80000 into OUT(0) (0xFFFFFFFF on an erased chip). On an erased
   word it fills the sector at 0x80000 with zeros but for that word, which
   gets 1 (16 page programs); otherwise it erases the sector and does the
   same with the count plus one. OUT(1) marks the end. Run again with the
   last run's flash.bin as --flash; cut the power during the erase. */
#include "flash.h"

#define BUF ((volatile unsigned char *)0x01c01000u)

static RAMCODE u32 read_word(u32 a)
{
    u32 w = 0;
    fl_sel();
    fl_addr(0x03u, a);
    SPI0_CON |= 0x1000u;
    for (u32 i = 0; i < 4u; i++)
        w |= fl_xfer(0xffu) << (8u * i);
    SPI0_CON &= ~0x1000u;
    fl_desel();
    return w;
}

static RAMCODE void keep(u32 old)
{
    if (old != 0xffffffffu) {
        fl_wren();
        fl_sel();
        fl_addr(0x20u, 0x80000u);
        fl_desel();
        fl_wait();
    }
    for (u32 page = 0; page < 16u; page++) {
        fl_wren();
        fl_sel();
        fl_addr(0x02u, 0x80000u + 256u * page);
        for (u32 i = 0; i < 256u; i++)
            fl_xfer(BUF[256u * page + i]);
        fl_desel();
        fl_wait();
    }
}

int main(void)
{
    ram_init();
    fl_desel();
    u32 old = read_word(0x80000u);
    OUT(0) = old;
    u32 n = old == 0xffffffffu ? 1u : old + 1u;
    for (u32 i = 0; i < 4096u; i++)
        BUF[i] = 0;
    *(volatile u32 *)BUF = n;
    keep(old);
    OUT(1) = 0x600du;
    return 0;
}
