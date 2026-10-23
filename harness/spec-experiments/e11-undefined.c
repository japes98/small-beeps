/* SPDX-License-Identifier: MIT */
/* SPDX-FileCopyrightText: 2026 japes98 */
/* E-11: an instruction fwtest cannot decode. Handlers on sources 0, 1 and
   2 count at OUT(1..3); OUT(0) marks that the next step is a call to
   bad(), whose first halfword fwtest can't decode (kept in a function of
   its own: fwtest reports such a fault before any instruction of the
   straight-line code holding it runs). The run should end as fwtest's
   fault, no handler having run. */
#include "exp.h"

__attribute__((interrupt)) void src0_isr(void) { OUT(1)++; }
__attribute__((interrupt)) void src1_isr(void) { OUT(2)++; }
__attribute__((interrupt)) void src2_isr(void) { OUT(3)++; }

__attribute__((noinline)) void bad(void)
{
    __asm__ volatile(".2byte 0xffff\n\t.2byte 0xffff");
}

int main(void)
{
    VECTOR(0) = (u32)src0_isr;
    VECTOR(1) = (u32)src1_isr;
    VECTOR(2) = (u32)src2_isr;
    ICFG(0) |= ICFG_ON(0, 7u) | ICFG_ON(1, 7u) | ICFG_ON(2, 7u);
    irq_on();
    OUT(0) = 0xbad1u;
    bad();
    OUT(0) = 0x600dd00eu;
    return 0;
}
