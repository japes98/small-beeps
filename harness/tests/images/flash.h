/* SPDX-License-Identifier: MIT */
/* SPDX-FileCopyrightText: 2026 japes98 */
/*
 * The flash chip on SPI0 (spiflash.rs), from code that runs in RAM: images
 * linked with image-ram.ld call ram_init() first. Everything a function
 * marked RAMCODE calls must be RAMCODE too (or inline), since fwtest ends
 * the run when code in the window runs while the chip is busy.
 */
#ifndef FLASH_H
#define FLASH_H

#include "board.h"

#define RAMCODE __attribute__((section(".ramtext"), noinline))
#define SPI0_CON REG(0x11c00u)

extern unsigned char __ramtext_load[], __ramtext_start[], __ramtext_end[];

static inline void ram_init(void)
{
    for (unsigned char *s = __ramtext_load, *d = __ramtext_start; d < __ramtext_end;)
        *(volatile unsigned char *)d++ = *s++;
}

static inline __attribute__((always_inline)) void fl_sel(void) { PD_OUT = 0; }
static inline __attribute__((always_inline)) void fl_desel(void) { PD_OUT = 1; }

static inline __attribute__((always_inline)) u32 fl_xfer(u32 b)
{
    SPI0_BUF = b;
    while (!(SPI0_CON & 0x8000u)) {
    }
    SPI0_CON |= 0x4000u;
    return SPI0_BUF & 0xffu;
}

static inline __attribute__((always_inline)) void fl_addr(u32 cmd, u32 a)
{
    fl_xfer(cmd);
    fl_xfer(a >> 16);
    fl_xfer(a >> 8);
    fl_xfer(a);
}

static inline __attribute__((always_inline)) u32 fl_status(void)
{
    fl_sel();
    fl_xfer(0x05u);
    SPI0_CON |= 0x1000u;
    u32 s = fl_xfer(0xffu);
    SPI0_CON &= ~0x1000u;
    fl_desel();
    return s;
}

static inline __attribute__((always_inline)) void fl_wren(void)
{
    fl_sel();
    fl_xfer(0x06u);
    fl_desel();
}

static inline __attribute__((always_inline)) void fl_wait(void)
{
    while (fl_status() & 1u) {
    }
}

#endif
