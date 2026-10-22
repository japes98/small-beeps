/* SPDX-License-Identifier: MIT */
/* SPDX-FileCopyrightText: 2026 japes98 */
/* E-8: the SARADC. Converts channels 0..15 over and over (CON = channel
   << 8 | enable bit 4 | start bit 6, then waits for done bit 7) and keeps
   each result in OUT(channel). The script moves the pot. */
#include "exp.h"

int main(void)
{
    for (;;) {
        for (u32 ch = 0; ch < 16; ch++) {
            ADC_CON = (ch << 8) | 0x10u | 0x40u;
            while (!(ADC_CON & 0x80u)) {
            }
            OUT(ch) = ADC_RES;
            ADC_CON = 0x40u;
        }
    }
}
