/* SPDX-License-Identifier: MIT */
/* SPDX-FileCopyrightText: 2026 japes98 */
/* Converts ADC channel 4 (the pot) again and again; the last reading in
   OUT(0), the number of conversions in OUT(1). */
#include "board.h"

int main(void)
{
    for (;;) {
        ADC_CON = (4u << 8) | 0x10u | 0x40u;
        while (!(ADC_CON & 0x80u))
            ;
        OUT(0) = ADC_RES;
        OUT(1)++;
    }
}
