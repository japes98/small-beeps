/* SPDX-License-Identifier: MIT */
/* SPDX-FileCopyrightText: 2026 japes98 */
/* Copies 16 bytes from flash offset 0x5000 (read through the image window,
   which shows the chip from offset 0x4000, lib.rs XIP_FLASH_OFFSET) to
   OUTBUF, then, from RAM, erases the sector at 0x80000 and programs
   "flash written!!!" there over SPI0 (spiflash.rs), waiting for each to
   finish, then halts. */
#include "flash.h"

static RAMCODE void command(u32 op, u32 addr, const char *data, u32 n)
{
    fl_wren();
    fl_sel();
    fl_addr(op, addr);
    for (u32 i = 0; i < n; i++)
        fl_xfer((unsigned char)data[i]);
    fl_desel();
    fl_wait();
}

int main(void)
{
    ram_init();
    fl_desel();
    volatile unsigned char *xip = (volatile unsigned char *)(0x02000000u + 0x5000u - 0x4000u);
    for (u32 i = 0; i < 16; i++)
        OUTBUF[i] = xip[i];
    /* the bytes to program, in RAM: the window can't be read while busy */
    const char *text = "flash written!!!";
    for (u32 i = 0; i < 16; i++)
        OUTBUF[16 + i] = text[i];
    command(0x20, 0x80000, 0, 0);
    command(0x02, 0x80000, (const char *)&OUTBUF[16], 16);
    return 0;
}
