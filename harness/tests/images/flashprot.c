/* SPDX-License-Identifier: MIT */
/* SPDX-FileCopyrightText: 2026 japes98 */
/* A store's write and read-back against block protection (HARDWARE-SPEC
   HW-121, HW-124 item 4, HW-131). From RAM: reads status registers 1 and 2
   into OUT(0) and OUT(1), erases the sector at chip offset 0x80000 and
   waits, reads the sector back and counts the bytes that aren't 0xFF into
   OUT(2), programs 16 bytes at 0x80000 and waits, reads them back and
   counts the bytes that differ into OUT(3). OUT(4) marks the end. A
   protected erase or program is ignored, so the read-backs catch it. */
#include "flash.h"

static RAMCODE u32 status2(void)
{
    fl_sel();
    fl_xfer(0x35u);
    SPI0_CON |= 0x1000u;
    u32 s = fl_xfer(0xffu);
    SPI0_CON &= ~0x1000u;
    fl_desel();
    return s;
}

/* How many of the n bytes at a differ from want (or from data, if given). */
static RAMCODE u32 differ(u32 a, u32 n, u32 want, const volatile unsigned char *data)
{
    u32 bad = 0;
    fl_sel();
    fl_addr(0x03u, a);
    SPI0_CON |= 0x1000u;
    for (u32 i = 0; i < n; i++)
        bad += fl_xfer(0xffu) != (data ? data[i] : want);
    SPI0_CON &= ~0x1000u;
    fl_desel();
    return bad;
}

static RAMCODE void run(void)
{
    OUT(0) = fl_status();
    OUT(1) = status2();
    fl_wren();
    fl_sel();
    fl_addr(0x20u, 0x80000u);
    fl_desel();
    fl_wait();
    OUT(2) = differ(0x80000u, 4096u, 0xffu, 0);
    fl_wren();
    fl_sel();
    fl_addr(0x02u, 0x80000u);
    for (u32 i = 0; i < 16u; i++)
        fl_xfer(OUTBUF[i]);
    fl_desel();
    fl_wait();
    OUT(3) = differ(0x80000u, 16u, 0, OUTBUF);
}

int main(void)
{
    ram_init();
    fl_desel();
    const char *text = "written, or not.";
    for (u32 i = 0; i < 16; i++)
        OUTBUF[i] = text[i];
    run();
    OUT(4) = 0x600du;
    return 0;
}
