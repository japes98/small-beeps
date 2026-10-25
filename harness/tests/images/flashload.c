/* SPDX-License-Identifier: MIT */
/* SPDX-FileCopyrightText: 2026 japes98 */
/* From RAM, starts a 4 KiB erase at 0x80000, then, still in RAM and while
   the chip is busy, reads a word of the image through the window: fwtest
   ends the run as a fault at that read. OUT(0) marks a run past it. */
#include "flash.h"

static RAMCODE void erase_and_read(void)
{
    fl_wren();
    fl_sel();
    fl_addr(0x20u, 0x80000u);
    fl_desel();
    OUT(1) = *(volatile u32 *)0x02000000u;
    fl_wait();
    OUT(0) = 0xbadu;
}

int main(void)
{
    ram_init();
    fl_desel();
    erase_and_read();
    return 0;
}
