/* SPDX-License-Identifier: MIT */
/* SPDX-FileCopyrightText: 2026 japes98 */
/* E-9: audio out through ALNK0. A buffer of two halves of LEN = 128 words
   (L, R, L, R, ...; a 24-bit sample in each word's low bits) at ADR3,
   refilled on each half-done interrupt (IRQ 11; CON2 bit 7 pending, cleared
   by writing bit 3; the half just finished is CON0 bit 15 inverted). Left
   counts up by 0x123 from 0 as a 24-bit value (its low 8 bits 0x5a), right
   is a fixed pattern: 0x007fffff, 0xff800000, 0x01000000 (above 24 bits),
   0x00000080, repeating. OUT(0) counts halves; OUT(1+i) the half index the
   first eight interrupts refilled. */
#include "exp.h"

#define LEN 128u
#define BUF ((volatile s32 *)0x01c10000u)
#define next (*(volatile s32 *)0x01c000f0u)
#define nr (*(volatile u32 *)0x01c000f4u)

static const s32 right[4] = {0x007fffff, (s32)0xff800000u, 0x01000000, 0x00000080};

static void refill(u32 half)
{
    volatile s32 *p = BUF + half * LEN;
    for (u32 i = 0; i < LEN; i += 2) {
        p[i] = (next << 8) | 0x5a;
        p[i + 1] = right[nr & 3u];
        next = (next + 0x123) & 0x7fff;
        nr++;
    }
}

__attribute__((interrupt)) void alnk_isr(void)
{
    ALNK_CON2 = 8u;
    u32 half = ((ALNK_CON0 >> 15) & 1u) ^ 1u;
    if (OUT(0) < 8u)
        OUT(1 + OUT(0)) = half;
    refill(half);
    OUT(0)++;
}

int main(void)
{
    refill(0);
    refill(1);
    VECTOR(IRQ_ALNK) = (u32)alnk_isr;
    ICFG(IRQ_ALNK) = ICFG_ON(IRQ_ALNK, 1u);
    ALNK_ADR3 = (u32)BUF;
    ALNK_LEN = LEN;
    ALNK_CON0 = 0x800u;
    irq_on();
    for (;;)
        __asm__ volatile("idle");
}
