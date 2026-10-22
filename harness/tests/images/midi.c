/* SPDX-License-Identifier: MIT */
/* SPDX-FileCopyrightText: 2026 japes98 */
/* UART1 on with receive DMA into a 64-byte ring at OUTBUF: the bytes that
   arrive land there. */
#include "board.h"

int main(void)
{
    UART1_RXSADR = (u32)OUTBUF;
    UART1_RXEADR = (u32)OUTBUF + 64u;
    UART1_CON0 = 0x41u;
    for (;;)
        OUT(0)++;
}
