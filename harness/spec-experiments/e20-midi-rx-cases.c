/* SPDX-License-Identifier: MIT */
/* SPDX-FileCopyrightText: 2026 japes98 */
/* E-20: MIDI input on UART1 (source 20), the cases E-19 leaves out. The
   handler counts its entries in OUT(10) and acknowledges a receive pending
   (CON0 bit 12) or a timeout (bit 10) without ever latching (bit 7), with
   CON0's set-up bits from OUT(11). The script (scripts/e20-midi-rx-cases.txt)
   sends bytes in each phase; times are TIMER4's, from the start.
     A (0.5 ms): CON0 0x09, the receive interrupt on but not the DMA, a
       16-byte ring, RXCNT 1. At 2 ms: OUT(0) BUF, OUT(1) CON0, OUT(2) the
       entries.
     B (2 ms): the DMA on (CON0 0x69) with RXEADR = RXSADR. At 4 ms: OUT(3)
       CON0, OUT(4) the entries, OUT(5) the ring's first word.
     C (4 ms): a 16-byte ring at RING, RXCNT 2, OTCNT 480 000 (10 ms). At
       7.5 ms: OUT(6) the entries since C began, OUT(7) CON0.
     D (7.5 ms): the ring moved to RING2; at 8.8 ms, two bytes in, RXSADR
       written again with RING2. At 11 ms: OUT(8) the entries since D began.
   OUT(9) marks the end. */
#include "exp.h"

#define IRQ_UART1 20u
#define UT1_CON0 REG(0x12100u)
#define UT1_BUF REG(0x1210cu)
#define UT1_OTCNT REG(0x12110u)
#define UT1_RXSADR REG(0x1211cu)
#define UT1_RXEADR REG(0x12120u)
#define UT1_RXCNT REG(0x12124u)
#define RING 0x01c00200u
#define RING2 0x01c00300u
#define ON (0x01u | 0x08u | 0x20u | 0x40u)

__attribute__((interrupt)) void uart1_isr(void)
{
    u32 con = UT1_CON0;
    OUT(10)++;
    UT1_CON0 = OUT(11) | ((con & 0x4000u) ? 0x1000u : 0u) | ((con & 0x800u) ? 0x400u : 0u);
}

static void until_us(u32 us)
{
    while (TMR_CNT(4) < 24u * us) {
    }
}

static void fill(u32 at)
{
    for (u32 i = 0u; i < 4u; i++) {
        REG(at + 4u * i) = 0xeeeeeeeeu;
    }
}

int main(void)
{
    TMR_CON(4) = 1u;
    fill(RING);
    fill(RING2);
    VECTOR(IRQ_UART1) = (u32)uart1_isr;
    ICFG(IRQ_UART1) |= ICFG_ON(IRQ_UART1, 2u);
    irq_on();

    until_us(500);
    UT1_RXSADR = RING;
    UT1_RXEADR = RING + 16u;
    UT1_RXCNT = 1u;
    OUT(11) = 0x09u;
    UT1_CON0 = 0x09u;
    until_us(2000);
    OUT(0) = UT1_BUF;
    OUT(1) = UT1_CON0;
    OUT(2) = OUT(10);

    UT1_CON0 = 0u;
    UT1_RXEADR = RING;
    OUT(11) = ON;
    UT1_CON0 = ON;
    until_us(4000);
    OUT(3) = UT1_CON0;
    OUT(4) = OUT(10);
    OUT(5) = REG(RING);

    UT1_CON0 = 0u;
    UT1_RXSADR = RING;
    UT1_RXEADR = RING + 16u;
    UT1_RXCNT = 2u;
    UT1_OTCNT = 480000u;
    u32 c0 = OUT(10);
    UT1_CON0 = ON;
    until_us(7500);
    OUT(6) = OUT(10) - c0;
    OUT(7) = UT1_CON0;

    u32 d0 = OUT(10);
    UT1_RXSADR = RING2;
    UT1_RXEADR = RING2 + 16u;
    until_us(8800);
    UT1_RXSADR = RING2;
    until_us(11000);
    OUT(8) = OUT(10) - d0;
    OUT(9) = 0x600dd00eu;
    for (;;) {
    }
}
