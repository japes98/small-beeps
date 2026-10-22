/* SPDX-License-Identifier: MIT */
/* SPDX-FileCopyrightText: 2026 japes98 */
/* E-6: the key matrix. Scans the 11 columns (a 0 bit in the 16-bit word
   shifted into the 74HC595 chain on PA4/PA3, latched with PA1, selects a
   column) and reads the rows (row 0 PA0, rows 1-4 PA5..PA8, row 5 PB7,
   low = closed). Every change of a column's closed rows goes in the log as
   (column << 8 | rows); OUT(15) is the log's length. The script presses
   each key in turn, then turns each encoder one detent each way. */
#include "exp.h"

#define STATE ((volatile u32 *)0x01c00180u)

static void select_column(u32 c)
{
    u32 bits = 0xffffu & ~(1u << c);
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
    for (;;) {
        for (u32 c = 0; c < 11; c++) {
            select_column(c);
            u32 r = rows();
            if (r != STATE[c]) {
                STATE[c] = r;
                if (OUT(15) < 256u)
                    LOG[OUT(15)++] = (c << 8) | r;
            }
        }
    }
}
