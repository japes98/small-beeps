/* SPDX-License-Identifier: MIT */
/* SPDX-FileCopyrightText: 2026 japes98 */
/* E-17: the SARADC's interrupt (source 24) and CON bit 5. A handler on
   source 24 counts its entries in OUT(12), keeps RES and CON as read on
   entry in OUT(13), OUT(14), acknowledges by writing CON with bit 6 alone,
   and keeps CON as read just after in OUT(15). Each step starts one
   conversion of channel 4 (the pot) and waits a while:
     0: start (bits 4 and 6) without bit 5;
     1: start with bit 5;
     2: start with bit 5 again;
     3: start without bit 5.
   OUT(2k) is the count after step k and OUT(2k + 1) CON read then. */
#include "exp.h"

#define IRQ_SARADC 24u
#define START ((4u << 8) | 0x10u | 0x40u)

__attribute__((interrupt)) void adc_isr(void)
{
    OUT(12)++;
    OUT(13) = ADC_RES;
    OUT(14) = ADC_CON;
    ADC_CON = 0x40u;
    OUT(15) = ADC_CON;
}

static void keep(u32 k)
{
    for (volatile u32 i = 0u; i < 2000u; i++) {
    }
    OUT(2u * k) = OUT(12);
    OUT(2u * k + 1u) = ADC_CON;
}

int main(void)
{
    VECTOR(IRQ_SARADC) = (u32)adc_isr;
    ICFG(IRQ_SARADC) |= ICFG_ON(IRQ_SARADC, 2u);
    irq_on();
    ADC_CON = START;
    keep(0);
    ADC_CON = START | 0x20u;
    keep(1);
    ADC_CON = START | 0x20u;
    keep(2);
    ADC_CON = START;
    keep(3);
    OUT(16) = 0x600dd00eu;
    return 0;
}
