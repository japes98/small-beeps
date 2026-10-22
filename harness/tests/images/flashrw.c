/* SPDX-License-Identifier: MIT */
/* SPDX-FileCopyrightText: 2026 japes98 */
/* Copies 16 bytes from flash offset 0x5000 (read through the image window,
   which shows the chip from offset 0x4000, lib.rs XIP_FLASH_OFFSET) to
   OUTBUF, then erases the sector at 0x80000 and programs "flash written!!!"
   there over SPI0 (spiflash.rs), then halts. */
#include "board.h"

static void select(void) { PD_OUT = 0; }
static void deselect(void) { PD_OUT = 1; }
static void byte(u32 b) { SPI0_BUF = b; }

static void command(u32 op, u32 addr, const char *data, u32 n)
{
    select(); byte(0x06); deselect();
    select();
    byte(op); byte(addr >> 16); byte(addr >> 8); byte(addr);
    for (u32 i = 0; i < n; i++)
        byte((unsigned char)data[i]);
    deselect();
}

int main(void)
{
    deselect();
    volatile unsigned char *xip = (volatile unsigned char *)(0x02000000u + 0x5000u - 0x4000u);
    for (u32 i = 0; i < 16; i++)
        OUTBUF[i] = xip[i];
    command(0x20, 0x80000, 0, 0);
    command(0x02, 0x80000, "flash written!!!", 16);
    return 0;
}
