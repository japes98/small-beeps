/* SPDX-License-Identifier: MIT */
/* SPDX-FileCopyrightText: 2026 japes98 */
/* SPI1's transfer-done interrupt follows CON bit 13 as last written. A
   handler on source 16 counts in OUT(8) and acknowledges with bit 14,
   keeping CON's other bits. Steps, each keeping the count and CON in
   OUT(2k), OUT(2k + 1): 0 bit 13 set, a DMA; 1 CON written 0, a DMA;
   2 a byte in BUF; 3 bit 13 set again, a byte in BUF. Then halt. */
#include "board.h"

#define SRC ((volatile unsigned char *)0x01c02000u)

__attribute__((interrupt)) void spi1_isr(void)
{
    OUT(8)++;
    SPI1_CON |= 0x4000u;
}

static void keep(u32 k)
{
    for (volatile u32 i = 0u; i < 1000u; i++) {
    }
    OUT(2u * k) = OUT(8);
    OUT(2u * k + 1u) = SPI1_CON;
}

int main(void)
{
    PC_OUT = 0x100u;
    VECTOR(IRQ_SPI1) = (u32)spi1_isr;
    ICFG(IRQ_SPI1) |= ICFG_ON(IRQ_SPI1, 2u);
    irq_on();
    SPI1_ADR = (u32)SRC;
    SPI1_CON = 0x2000u;
    SPI1_CNT = 2u;
    keep(0);
    SPI1_CON = 0u;
    SPI1_CNT = 2u;
    keep(1);
    SPI1_BUF = 0u;
    keep(2);
    SPI1_CON = 0x2000u;
    SPI1_BUF = 0u;
    keep(3);
    return 0;
}
