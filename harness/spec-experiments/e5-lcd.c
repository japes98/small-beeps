/* SPDX-License-Identifier: MIT */
/* SPDX-FileCopyrightText: 2026 japes98 */
/* E-5: the LCD through SPI1. Bytes with PC8 low are commands, high are
   data. The whole screen blue by DMA (ADR/CNT, one row of 480 bytes at a
   time); a red 10 x 10 square at (0,0) and a green one at (230,230), byte
   by byte; then INVON and DISPOFF. After about 4 ms of busy counting (a
   timer wait would let fwtest's captures come late), a software reset
   (0x01). Captured at 1 ms and at the end. */
#include "exp.h"

#define ROW ((volatile u8 *)0x01c02000u)

static void cmd(u32 c) { PC_OUT = 0; SPI1_BUF = c; }
static void dat(u32 d) { PC_OUT = 0x100; SPI1_BUF = d; }

static void window(u32 x0, u32 y0, u32 x1, u32 y1)
{
    cmd(0x2a); dat(x0 >> 8); dat(x0); dat(x1 >> 8); dat(x1);
    cmd(0x2b); dat(y0 >> 8); dat(y0); dat(y1 >> 8); dat(y1);
    cmd(0x2c);
}

static void square(u32 x, u32 y, u32 rgb565)
{
    window(x, y, x + 9, y + 9);
    for (u32 n = 100; n; n--) {
        dat(rgb565 >> 8);
        dat(rgb565);
    }
}

int main(void)
{
    for (u32 i = 0; i < 480; i += 2) {
        ROW[i] = 0x00;
        ROW[i + 1] = 0x1f;
    }
    cmd(0x11);
    cmd(0x3a); dat(0x55);
    cmd(0x29);
    window(0, 0, 239, 239);
    PC_OUT = 0x100;
    for (u32 y = 0; y < 240; y++) {
        SPI1_ADR = (u32)ROW;
        SPI1_CNT = 480u;
    }
    square(0, 0, 0xf800);
    square(230, 230, 0x07e0);
    cmd(0x21);
    cmd(0x28);
    for (u32 i = 0; i < 200000u; i++)
        OUT(1) = i;
    cmd(0x01);
    OUT(0) = 1u;
    return 0;
}
