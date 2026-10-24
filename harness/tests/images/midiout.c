/* SPDX-License-Identifier: MIT */
/* SPDX-FileCopyrightText: 2026 japes98 */
/* UART1's transmit side, the MIDI output. A BUF write with the UART off
   (not sent); then the UART on with its transmit interrupt, whose handler
   counts in OUT(1) and keeps TIMER4's count and CON0 as read on entry in
   OUT(2 + 2k), OUT(3 + 2k). At the start a DMA of five bytes (a note-on,
   then a second by running status); at 3 ms a clock byte through BUF; at
   4 ms a DMA of a note-off with an active-sensing byte through BUF behind
   it. OUT(0) marks the end. */
#include "board.h"

/* the bytes to send, in RAM (test images have no initialised data) */
#define MSG 0x01c00300u
#define OFF 0x01c00310u

__attribute__((interrupt)) void uart1_isr(void)
{
    u32 n = OUT(1)++;
    OUT(2u + 2u * n) = T4_CNT;
    OUT(3u + 2u * n) = UART1_CON0;
    UART1_CON0 = 0x05u | 0x2000u;
}

static void until_us(u32 us)
{
    while (T4_CNT < 24u * us) {
    }
}

int main(void)
{
    T4_CON = 1u;
    REG(MSG) = 0x3e643c90u;
    REG(MSG + 4u) = 0x00000050u;
    REG(OFF) = 0x00003c80u;
    UART1_BUF = 0x99u;
    VECTOR(IRQ_UART1) = (u32)uart1_isr;
    ICFG(IRQ_UART1) |= ICFG_ON(IRQ_UART1, 2u);
    irq_on();
    UART1_CON0 = 0x05u;
    UART1_TXADR = MSG;
    UART1_TXCNT = 5u;
    until_us(3000);
    UART1_BUF = 0xf8u;
    until_us(4000);
    UART1_TXADR = OFF;
    UART1_TXCNT = 3u;
    UART1_BUF = 0xfeu;
    until_us(6000);
    OUT(0) = 0x600dd00eu;
    for (;;) {
    }
}
