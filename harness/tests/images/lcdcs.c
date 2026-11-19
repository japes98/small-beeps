/* SPDX-License-Identifier: MIT */
/* SPDX-FileCopyrightText: 2026 japes98 */
/* The panel's chip select (PC7, HW-115): with PC7 an output driven high,
   as the first hardware build left it, the left half is filled red, one
   byte at a time and then by DMA; with PC7 low the right half is filled
   green the same way. Then halt: only the right half may show. */
#include "board.h"

#define PC_DIR REG(0x50088u)
#define CS 0x80u
#define DC 0x100u

/* one row of pixels for the DMA, at a fixed RAM address */
#define row ((volatile unsigned char *)0x01c10000u)

static void cmd(u32 c) { PC_OUT &= ~DC; SPI1_BUF = c; }
static void dat(u32 d) { PC_OUT |= DC; SPI1_BUF = d; }

static void fill(u32 x0, u32 x1, u32 rgb565)
{
    u32 n = x1 - x0 + 1, y, i;

    for (i = 0; i < n; i++) {
        row[2 * i] = rgb565 >> 8;
        row[2 * i + 1] = rgb565;
    }
    cmd(0x2a); dat(x0 >> 8); dat(x0); dat(x1 >> 8); dat(x1);
    cmd(0x2b); dat(0); dat(0); dat(0); dat(239);
    cmd(0x2c);
    /* the first row a byte at a time, the rest by DMA */
    for (i = 0; i < n; i++) {
        dat(rgb565 >> 8);
        dat(rgb565);
    }
    for (y = 1; y < 240; y++) {
        SPI1_ADR = (u32)row;
        SPI1_CNT = 2 * n;
    }
}

int main(void)
{
    PC_OUT |= CS;
    PC_DIR &= ~CS;
    cmd(0x11);
    cmd(0x29);
    fill(0, 119, 0xf800);
    PC_OUT &= ~CS;
    cmd(0x11);
    cmd(0x29);
    fill(120, 239, 0x07e0);
    PC_OUT |= CS;
    return 0;
}
