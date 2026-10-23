/* SPDX-License-Identifier: MIT */
/* SPDX-FileCopyrightText: 2026 japes98 */
/* E-16: a whole frame in one DMA transfer. The window is the whole screen
   (CASET 0-239, RASET 0-239, RAMWR, byte by byte); then one write of 115 200
   to SPI1's CNT sends a frame from RAM: rows 0-119 red, rows 120-239 blue,
   with pixel (0, 0) green and pixel (239, 239) white to show the order.
   Captured at the end. */
#include "exp.h"

#define FRAME ((volatile u8 *)0x01c10000u)
#define BYTES (240u * 240u * 2u)

static void cmd(u32 c) { PC_OUT = 0; SPI1_BUF = c; }
static void dat(u32 d) { PC_OUT = 0x100; SPI1_BUF = d; }

static void pixel(u32 i, u32 rgb565)
{
    FRAME[2u * i] = rgb565 >> 8;
    FRAME[2u * i + 1u] = rgb565;
}

int main(void)
{
    for (u32 i = 0; i < 240u * 240u; i++)
        pixel(i, i < 240u * 120u ? 0xf800u : 0x001fu);
    pixel(0, 0x07e0u);
    pixel(240u * 240u - 1u, 0xffffu);
    cmd(0x11);
    cmd(0x3a); dat(0x55);
    cmd(0x29);
    cmd(0x2a); dat(0); dat(0); dat(0); dat(239);
    cmd(0x2b); dat(0); dat(0); dat(0); dat(239);
    cmd(0x2c);
    PC_OUT = 0x100;
    SPI1_ADR = (u32)FRAME;
    SPI1_CNT = BYTES;
    OUT(0) = 1u;
    return 0;
}
