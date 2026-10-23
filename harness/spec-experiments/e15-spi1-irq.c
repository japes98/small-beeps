/* SPDX-License-Identifier: MIT */
/* SPDX-FileCopyrightText: 2026 japes98 */
/* E-15: SPI1's transfer-done interrupt (source 16) and CON bit 13. A
   handler on source 16 counts its entries and acknowledges by setting CON
   bit 14, keeping the other bits (as the SDK's examples do). Each step
   starts one transfer, a DMA of 2 bytes or a single byte in BUF, then
   waits a while for the interrupt, and keeps the count and CON as read:
     0: CON never written (its reset value), DMA;
     1: CON written 0 (bit 13 clear), DMA;
     2: the same, one byte in BUF;
     3: CON written with bit 13, DMA;
     4: the same, one byte in BUF;
     5: CON written 0 again, DMA;
     6: the same, one byte in BUF;
     7: CON written with bit 13 and the source's enable off in ICFG, DMA,
        then CON written 0 and the source enabled again: whether a
        transfer done while the source was off is still taken.
   OUT(18) is the count, OUT(1) CON's first read, OUT(2 + 2k) the count
   after step k and OUT(3 + 2k) CON read then. The bytes go to the panel
   as data (PC8 high) and are ignored there. Before the fix to fwtest
   (SR-3), a CON write could not clear bit 13: steps 5 and 6 counted. */
#include "exp.h"

#define IRQ_SPI1 16u
#define SRC ((volatile u8 *)0x01c02000u)
#define HITS OUT(18)

__attribute__((interrupt)) void spi1_isr(void)
{
    HITS++;
    SPI1_CON |= 0x4000u;
}

static void settle(void)
{
    for (volatile u32 i = 0u; i < 2000u; i++) {
    }
}

static void dma(void)
{
    SPI1_ADR = (u32)SRC;
    SPI1_CNT = 2u;
    settle();
}

static void byte(void)
{
    SPI1_BUF = 0u;
    settle();
}

static void keep(u32 k)
{
    OUT(2u + 2u * k) = HITS;
    OUT(3u + 2u * k) = SPI1_CON;
}

int main(void)
{
    SRC[0] = 0u;
    SRC[1] = 0u;
    PC_OUT = 0x100u;
    OUT(1) = SPI1_CON;
    VECTOR(IRQ_SPI1) = (u32)spi1_isr;
    ICFG(IRQ_SPI1) |= ICFG_ON(IRQ_SPI1, 2u);
    irq_on();

    dma();
    keep(0);
    SPI1_CON = 0u;
    dma();
    keep(1);
    byte();
    keep(2);
    SPI1_CON = 0x2000u;
    dma();
    keep(3);
    byte();
    keep(4);
    SPI1_CON = 0u;
    dma();
    keep(5);
    byte();
    keep(6);

    ICFG(IRQ_SPI1) &= ~ICFG_ON(IRQ_SPI1, 7u);
    SPI1_CON = 0x2000u;
    dma();
    SPI1_CON = 0u;
    ICFG(IRQ_SPI1) |= ICFG_ON(IRQ_SPI1, 2u);
    settle();
    keep(7);

    OUT(0) = 0x600dd00eu;
    return 0;
}
