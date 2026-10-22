/* SPDX-License-Identifier: MIT */
/* SPDX-FileCopyrightText: 2026 japes98 */
/* Four coloured quadrants and a diagonal, one byte at a time through SPI1
   (column/row address set, memory write), then halt. */
#include "board.h"

static void cmd(u32 c) { PC_OUT = 0; SPI1_BUF = c; }
static void dat(u32 d) { PC_OUT = 0x100; SPI1_BUF = d; }

static void window(u32 x0, u32 y0, u32 x1, u32 y1)
{
    cmd(0x2a); dat(x0 >> 8); dat(x0); dat(x1 >> 8); dat(x1);
    cmd(0x2b); dat(y0 >> 8); dat(y0); dat(y1 >> 8); dat(y1);
    cmd(0x2c);
}

static void fill(u32 x0, u32 y0, u32 x1, u32 y1, u32 rgb565)
{
    window(x0, y0, x1, y1);
    for (u32 n = (x1 - x0 + 1) * (y1 - y0 + 1); n; n--) {
        dat(rgb565 >> 8);
        dat(rgb565);
    }
}

int main(void)
{
    cmd(0x11);
    cmd(0x29);
    fill(0, 0, 119, 119, 0xf800);
    fill(120, 0, 239, 119, 0x07e0);
    fill(0, 120, 119, 239, 0x001f);
    fill(120, 120, 239, 239, 0xffff);
    for (u32 i = 0; i < 240; i++)
        fill(i, i, i, i, 0x0000);
    return 0;
}
