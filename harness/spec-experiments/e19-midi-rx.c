/* SPDX-License-Identifier: MIT */
/* SPDX-FileCopyrightText: 2026 japes98 */
/* E-19: MIDI input on UART1 (source 20), received by DMA into a ring.
   OUT(0) is CON0 as read at the start, OUT(1) the ring's first word after
   the bytes the script sends while the UART is off (scripts/e19-midi-rx.txt).
   Then the ring (16 bytes at RING, filled with 0xEE first) is set up with
   RXCNT 4 and OTCNT 48 000 (1 ms of the 48 MHz UART clock), and CON0 turned
   on with the receive and timeout interrupts and the receive DMA. The
   handler counts its entries in OUT(12) and logs four words per entry:
   TIMER4's count, CON0 as read on entry, HRXCNT after a latch (CON0 bit 7),
   and CON0 after the acknowledge (bit 12 for a receive pending, bit 10 for
   a timeout). OUT(13) marks the set-up done. */
#include "exp.h"

#define IRQ_UART1 20u
#define UT1_CON0 REG(0x12100u)
#define UT1_OTCNT REG(0x12110u)
#define UT1_RXSADR REG(0x1211cu)
#define UT1_RXEADR REG(0x12120u)
#define UT1_RXCNT REG(0x12124u)
#define UT1_HRXCNT REG(0x12128u)
#define RING 0x01c00200u
#define ON (0x01u | 0x08u | 0x20u | 0x40u)

__attribute__((interrupt)) void uart1_isr(void)
{
    u32 n = OUT(12)++;
    u32 con = UT1_CON0;
    volatile u32 *e = LOG + 4u * (n & 31u);
    e[0] = TMR_CNT(4);
    e[1] = con;
    UT1_CON0 = ON | 0x80u;
    e[2] = UT1_HRXCNT;
    UT1_CON0 = ON | ((con & 0x4000u) ? 0x1000u : 0u) | ((con & 0x800u) ? 0x400u : 0u);
    e[3] = UT1_CON0;
}

int main(void)
{
    TMR_CON(4) = 1u;
    OUT(0) = UT1_CON0;
    for (u32 i = 0u; i < 4u; i++) {
        REG(RING + 4u * i) = 0xeeeeeeeeu;
    }
    wait_us(2000);
    OUT(1) = REG(RING);
    VECTOR(IRQ_UART1) = (u32)uart1_isr;
    ICFG(IRQ_UART1) |= ICFG_ON(IRQ_UART1, 2u);
    irq_on();
    UT1_RXSADR = RING;
    UT1_RXEADR = RING + 16u;
    UT1_RXCNT = 4u;
    UT1_OTCNT = 48000u;
    UT1_CON0 = ON;
    OUT(13) = 0x600dd00eu;
    for (;;) {
        wait_us(1000);
    }
}
