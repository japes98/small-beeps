/* SPDX-License-Identifier: MIT */
/* SPDX-FileCopyrightText: 2026 japes98 */
/* Interrupts while the flash is busy. TIMER0 (prescaler setting 2, PRD
   1500: every 1 ms) raises source 4; its handler, in RAM, counts in OUT(1).
   From RAM with interrupts on: a 4 KiB erase at 0x80000, then a page
   program there, each waited for. OUT(2), OUT(3): TIMER4 ticks each took;
   OUT(4), OUT(5): the handler's count after each. Then the handler is
   moved to a copy in the window and another erase started: the next tick
   ends the run as a fault. OUT(0) marks the end of the first part. */
#include "flash.h"

#define TMR0_CON REG(0x10400u)
#define TMR0_CNT REG(0x10404u)
#define TMR0_PRD REG(0x10408u)

__attribute__((interrupt)) RAMCODE void tick_ram(void)
{
    OUT(1)++;
    TMR0_CON = 0x4021u;
}

__attribute__((interrupt)) void tick_window(void)
{
    OUT(6)++;
    TMR0_CON = 0x4021u;
}

static RAMCODE u32 timed(u32 op, u32 addr, u32 n)
{
    u32 t0 = T4_CNT;
    fl_wren();
    fl_sel();
    fl_addr(op, addr);
    for (u32 i = 0; i < n; i++)
        fl_xfer(0x5au);
    fl_desel();
    fl_wait();
    return T4_CNT - t0;
}

static RAMCODE void start_erase(void)
{
    fl_wren();
    fl_sel();
    fl_addr(0x20u, 0x81000u);
    fl_desel();
    fl_wait();
}

int main(void)
{
    ram_init();
    fl_desel();
    T4_CON = 1u;
    VECTOR(4) = (u32)tick_ram;
    TMR0_CNT = 0;
    TMR0_PRD = 1500u;
    TMR0_CON = 0x21u;
    ICFG(4) |= ICFG_ON(4, 1);
    __asm__ volatile("r0 = 0x100\n\ticfg = r0\n\tsti" ::: "r0");
    OUT(2) = timed(0x20u, 0x80000u, 0);
    OUT(4) = OUT(1);
    OUT(3) = timed(0x02u, 0x80000u, 16);
    OUT(5) = OUT(1);
    OUT(0) = 0x600du;
    VECTOR(4) = (u32)tick_window;
    start_erase();
    OUT(7) = 0xbadu;
    return 0;
}
