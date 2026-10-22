/* SPDX-License-Identifier: MIT */
/* SPDX-FileCopyrightText: 2026 japes98 */
/* E-3: timers and interrupts. TIMER5 with PRD 600 (IRQ 63), TIMER0 with
   prescaler index 2 and PRD 1500 (IRQ 4), the core tick timer with PRD
   1234 (IRQ 3), one software interrupt (IRQ 120); each handler counts.
   TIMER4 runs free; the TIMER5 handler keeps the TIMER4 count between two
   of its interrupts. The main loop sleeps with idle. */
#include "exp.h"

__attribute__((interrupt)) void t5_isr(void)
{
    TMR_CON(5) = 1u | 0x4000u;
    u32 now = TMR_CNT(4);
    if (OUT(0))
        OUT(2) = now - OUT(1);
    OUT(1) = now;
    OUT(0)++;
}

__attribute__((interrupt)) void t0_isr(void)
{
    OUT(4) = TMR_CON(0);             /* CON as the handler sees it */
    TMR_CON(0) = 1u | (2u << 4) | 0x4000u;
    OUT(3)++;
}

__attribute__((interrupt)) void tick_isr(void)
{
    TTMR_CON = 1u | 0x40u;
    OUT(5)++;
}

__attribute__((interrupt)) void soft_isr(void)
{
    ILAT_CLR = 1u;
    OUT(6)++;
}

int main(void)
{
    VECTOR(IRQ_TIMER5) = (u32)t5_isr;
    VECTOR(IRQ_TIMER0) = (u32)t0_isr;
    VECTOR(IRQ_TICK_TMR) = (u32)tick_isr;
    VECTOR(IRQ_SOFT0) = (u32)soft_isr;
    ICFG(IRQ_TIMER5) |= ICFG_ON(IRQ_TIMER5, 3u);
    ICFG(IRQ_TIMER0) |= ICFG_ON(IRQ_TIMER0, 2u);
    ICFG(IRQ_TICK_TMR) |= ICFG_ON(IRQ_TICK_TMR, 1u);
    ICFG(IRQ_SOFT0) |= ICFG_ON(IRQ_SOFT0, 1u);
    TMR_CON(4) = 1u;
    TMR_PRD(5) = 600u;
    TMR_CON(5) = 1u;
    TMR_PRD(0) = 1500u;
    TMR_CNT(0) = 0u;
    TMR_CON(0) = 1u | (2u << 4);
    TTMR_PRD = 1234u;
    TTMR_CON = 1u;
    irq_on();
    ILAT_SET = 1u;
    for (;;)
        __asm__ volatile("idle");
}
