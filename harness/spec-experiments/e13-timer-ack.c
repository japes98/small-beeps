/* SPDX-License-Identifier: MIT */
/* SPDX-FileCopyrightText: 2026 japes98 */
/* E-13: TIMER0's period and its acknowledge. TIMER0 runs as in E-3
   (prescaler index 2, PRD 1500: 1 ms). For 100 periods the handler
   acknowledges at once; for the next 100 it first busy-waits a fixed loop.
   Each phase keeps the TIMER4 ticks (24 MHz) over its 100 periods, the
   ticks from handler entry to the acknowledge in its last interrupt, and in
   the second phase TIMER0's CNT just before and just after the acknowledge.
   The periphery model (fm1-soc periph.rs) re-arms TIMER0-3 on every CON
   write, so the period should grow by the entry-to-acknowledge time. */
#include "exp.h"

#define PERIODS 100u

static void record(u32 t, u32 acked, u32 at)
{
    if (OUT(2) == 0u)
        OUT(3) = t;
    if (OUT(2) == PERIODS) {
        OUT(at) = t - OUT(3);
        OUT(at + 1u) = acked - t;
        OUT(2) = 0u;
        OUT(1)++;
        return;
    }
    OUT(2)++;
}

__attribute__((interrupt)) void t0_isr(void)
{
    u32 t = TMR_CNT(4);
    if (OUT(1) == 0u) {
        TMR_CON(0) = 1u | (2u << 4) | 0x4000u;
        record(t, TMR_CNT(4), 4u);
        return;
    }
    for (volatile u32 i = 0u; i < 200u; i++) {
    }
    OUT(8) = TMR_CNT(0);
    TMR_CON(0) = 1u | (2u << 4) | 0x4000u;
    OUT(9) = TMR_CNT(0);
    record(t, TMR_CNT(4), 6u);
    if (OUT(1) == 2u) {
        TMR_CON(0) = 0x4000u;
        OUT(0) = 0x600dd00eu;
    }
}

int main(void)
{
    VECTOR(IRQ_TIMER0) = (u32)t0_isr;
    ICFG(IRQ_TIMER0) |= ICFG_ON(IRQ_TIMER0, 2u);
    TMR_CON(4) = 1u;
    TMR_PRD(0) = 1500u;
    TMR_CNT(0) = 0u;
    TMR_CON(0) = 1u | (2u << 4);
    irq_on();
    for (;;)
        __asm__ volatile("idle");
}
