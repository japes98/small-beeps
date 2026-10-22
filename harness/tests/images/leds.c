/* SPDX-License-Identifier: MIT */
/* SPDX-FileCopyrightText: 2026 japes98 */
/* Selects matrix column 0 through the 74HC595 chain (SER PA4, SRCLK PA3,
   RCLK PA1; a low bit selects a column), lights the LED on line PA9 for the
   first 10 ms, then the one on line PA10 (periph.rs led_credit); the
   OS-free timing is a spin on TIMER4, which fwtest skips through. */
#include "board.h"

#define T4_CON REG(0x10800u)
#define T4_CNT REG(0x10804u)

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

static void wait_ms(u32 ms)
{
    T4_CNT = 0;
    while (T4_CNT < ms * 24000u)
        ;
}

int main(void)
{
    T4_CON = 1;
    columns(0xfffeu);
    PA_OUT = 1u << 9;
    wait_ms(10);
    PA_OUT = 1u << 10;
    for (;;)
        OUT(0)++;
}
