/* SPDX-License-Identifier: MIT */
/* SPDX-FileCopyrightText: 2026 japes98 */
/* Audio out: a buffer of two halves of LEN words (L/R int32, the 16-bit
   sample << 8), refilled with a rising ramp on each half-done interrupt
   (IRQ 11); the main loop sleeps with `idle`. Blocks done in OUT(0). */
#include "board.h"

#define LEN 64u
#define BUF ((volatile s32 *)0x01c10000u)

/* the ramp's next value (no .bss in test images) */
#define next (*(volatile s32 *)0x01c000f0u)

static void refill(u32 half)
{
    volatile s32 *p = BUF + half * LEN;
    for (u32 i = 0; i < LEN; i += 2) {
        p[i] = next << 8;
        p[i + 1] = -next << 8;
        next = (next + 97) & 0x7fff;
    }
}

__attribute__((interrupt)) void alnk_isr(void)
{
    ALNK_PEND = 8u;
    refill(((ALNK_CON0 >> 15) & 1u) ^ 1u);
    OUT(0)++;
}

int main(void)
{
    refill(0);
    refill(1);
    VECTOR(IRQ_ALNK) = (u32)alnk_isr;
    ICFG(IRQ_ALNK) = ICFG_ON(IRQ_ALNK, 1u);
    ALNK_ADR = (u32)BUF;
    ALNK_LEN = LEN;
    ALNK_CON0 = 0x800u;
    irq_on();
    for (;;)
        __asm__ volatile("idle");
}
