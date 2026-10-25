/* SPDX-License-Identifier: MIT */
/* SPDX-FileCopyrightText: 2026 japes98 */
/* From RAM, starts a 4 KiB erase at 0x80000 and returns to main in the
   window at once, without waiting: fwtest ends the run as a fault there.
   OUT(0) marks the return; it must never be written. */
#include "flash.h"

static RAMCODE void erase_and_go(void)
{
    fl_wren();
    fl_sel();
    fl_addr(0x20u, 0x80000u);
    fl_desel();
}

int main(void)
{
    ram_init();
    fl_desel();
    erase_and_go();
    OUT(0) = 0xbadu;
    return 0;
}
