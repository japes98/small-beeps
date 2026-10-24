/* SPDX-License-Identifier: MIT */
/* SPDX-FileCopyrightText: 2026 japes98 */
/* E-22: the flash chip on SPI0 (spiflash.rs; JL_SPI0 CON +0, BUF +8 from
   WL82.h; chip select PD0, bit 0 of JL_PORTD OUT). Results in OUT(n):
    0-2  JEDEC ID (9F)
    3-5  status (05) before WREN, after WREN, after a 4 KiB erase
    6    TIMER4 ticks for 64 BUF writes (the bus's pace)
    7    TIMER4 ticks for WREN, a 4 KiB erase and status reads until WIP is 0
    8    status reads that took
    9    bytes 0-3 at 0x80000 after programming F0 0F AA FF, then 3C x4
   10    bytes 0-3 at 0x80010 after a program sent without WREN
   11    bytes 0-3 at 0x80000 through the code window
   12    bytes 0-3 at 0x80100 after programming "ABCD" at 0x800FE
   13    bytes 0-3 at 0x80000 after that (a chip wraps "CD" to here)
   14    bytes 0-3 at 0x81000 after a 4 KiB erase of 0x80000 (programmed
         first)
   15    bytes 0-3 at 0x80000 after that erase
   16    bytes 0-3 at 0x9F000 after a 64 KiB erase of 0x90000 (programmed
         first)
   17    bytes 0-3 at 0xA0000 after that (programmed first; outside it)
   18    end marker */
#include "exp.h"

#define SPI0_CON REG(0x11c00u)
#define SPI0_BUF REG(0x11c08u)
#define PD_OUT REG(0x500c0u)

static void sel(void) { PD_OUT = 0u; }
static void desel(void) { PD_OUT = 1u; }

static u32 xfer(u32 b)
{
    SPI0_BUF = b;
    while (!(SPI0_CON & 0x8000u)) {
    }
    SPI0_CON |= 0x4000u;
    return SPI0_BUF & 0xffu;
}

static void op(u32 cmd)
{
    sel();
    xfer(cmd);
    desel();
}

static u32 status(void)
{
    sel();
    xfer(0x05u);
    SPI0_CON |= 0x1000u;
    u32 s = xfer(0xffu);
    SPI0_CON &= ~0x1000u;
    desel();
    return s;
}

static void addr_cmd(u32 cmd, u32 a)
{
    xfer(cmd);
    xfer(a >> 16);
    xfer(a >> 8);
    xfer(a);
}

static void erase(u32 cmd, u32 a)
{
    op(0x06u);
    sel();
    addr_cmd(cmd, a);
    desel();
    while (status() & 1u) {
    }
}

static void program(u32 a, u32 word, u32 wren)
{
    if (wren)
        op(0x06u);
    sel();
    addr_cmd(0x02u, a);
    for (u32 i = 0; i < 4u; i++)
        xfer((word >> (8u * i)) & 0xffu);
    desel();
    while (status() & 1u) {
    }
}

static u32 read4(u32 a)
{
    u32 w = 0;
    sel();
    addr_cmd(0x03u, a);
    SPI0_CON |= 0x1000u;
    for (u32 i = 0; i < 4u; i++)
        w |= xfer(0xffu) << (8u * i);
    SPI0_CON &= ~0x1000u;
    desel();
    return w;
}

int main(void)
{
    TMR_CON(4) = 1u;
    desel();

    sel();
    xfer(0x9fu);
    SPI0_CON |= 0x1000u;
    for (u32 i = 0; i < 3u; i++)
        OUT(i) = xfer(0xffu);
    SPI0_CON &= ~0x1000u;
    desel();

    OUT(3) = status();
    op(0x06u);
    OUT(4) = status();

    u32 t0 = TMR_CNT(4);
    sel();
    for (u32 i = 0; i < 64u; i++)
        xfer(0xffu);
    desel();
    OUT(6) = TMR_CNT(4) - t0;

    t0 = TMR_CNT(4);
    op(0x06u);
    sel();
    addr_cmd(0x20u, 0x80000u);
    desel();
    u32 polls = 1;
    while (status() & 1u)
        polls++;
    OUT(7) = TMR_CNT(4) - t0;
    OUT(8) = polls;
    OUT(5) = status();

    program(0x80000u, 0xffaa0ff0u, 1);
    program(0x80000u, 0x3c3c3c3cu, 1);
    OUT(9) = read4(0x80000u);
    program(0x80010u, 0x12345678u, 0);
    OUT(10) = read4(0x80010u);
    OUT(11) = REG(0x02000000u + 0x80000u - 0x4000u);

    program(0x800feu, 0x44434241u, 1);
    OUT(12) = read4(0x80100u);
    OUT(13) = read4(0x80000u);

    program(0x81000u, 0x11223344u, 1);
    erase(0x20u, 0x80000u);
    OUT(14) = read4(0x81000u);
    OUT(15) = read4(0x80000u);

    program(0x9f000u, 0x55667788u, 1);
    program(0xa0000u, 0x99aabbccu, 1);
    erase(0xd8u, 0x90000u);
    OUT(16) = read4(0x9f000u);
    OUT(17) = read4(0xa0000u);

    OUT(18) = 0xe22e22e2u;
    return 0;
}
