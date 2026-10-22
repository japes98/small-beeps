/* SPDX-License-Identifier: MIT */
/* SPDX-FileCopyrightText: 2026 japes98 */
/* E-7: the LEDs. For each of the four LED lines (PA9, PA10, PH6, PH9) and
   each of the 11 columns (selected as in E-6), the line is driven high for
   a slot of about 2 ms, timed by busy counting (a timer wait would let
   fwtest's samples come late), with about 0.5 ms dark between slots.
   leds.csv, sampled every 0.5 ms, shows which LED number each slot lights,
   in slot order (line 0 column 0, line 0 column 1, ...). */
#include "exp.h"

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

static const u32 line_pa[4] = {1u << 9, 1u << 10, 0, 0};
static const u32 line_ph[4] = {0, 0, 1u << 6, 1u << 9};

static void spin(u32 n)
{
    for (u32 i = 0; i < n; i++)
        OUT(1) = i;
}

int main(void)
{
    for (u32 line = 0; line < 4; line++) {
        for (u32 c = 0; c < 11; c++) {
            select_column(c);
            PH_OUT = line_ph[line];
            PA_OUT = line_pa[line];
            spin(160000u);
            PA_OUT = 0u;
            PH_OUT = 0u;
            spin(40000u);
        }
    }
    OUT(0) = 1u;
    for (;;)
        __asm__ volatile("idle");
}
