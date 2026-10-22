/* SPDX-License-Identifier: MIT */
/* SPDX-FileCopyrightText: 2026 japes98 */
/* Scans the key matrix's 11 columns (one selected at a time through the
   74HC595 chain) and keeps each column's closed rows in OUT(c) (row 0 = PA0,
   rows 1-4 = PA5..PA8, row 5 = PB7; low = closed, periph.rs closed_rows).
   Also counts the changes of encoder 0's two contacts (column 0 row 0 and
   column 1 row 0) in OUT(16): four per detent. */
#include "board.h"

static void columns(u32 bits)
{
    for (int i = 15; i >= 0; i--) {
        u32 ser = ((bits >> i) & 1u) << 4;
        PA_OUT = ser;
        PA_OUT = ser | 8u;
    }
    PA_OUT = 2u;
    PA_OUT = 0u;
}

static u32 rows(void)
{
    u32 a = ~PA_IN, b = ~PB_IN;
    return (a & 1u) | ((a >> 4) & 0x1eu) | (((b >> 7) & 1u) << 5);
}

int main(void)
{
    u32 last = 0;
    for (;;) {
        for (u32 c = 0; c < 11; c++) {
            columns(0xffffu & ~(1u << c));
            OUT(c) = rows();
        }
        u32 enc = (OUT(0) & 1u) | ((OUT(1) & 1u) << 1);
        if (enc != last) {
            OUT(16)++;
            last = enc;
        }
    }
}
