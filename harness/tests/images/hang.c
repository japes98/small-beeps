/* SPDX-License-Identifier: MIT */
/* SPDX-FileCopyrightText: 2026 japes98 */
/* One heartbeat, then a spin with interrupts on: not a halt, but the
   watchdog's word never changes again (`hang`). */
#include "board.h"

int main(void)
{
    OUT(1) = 1;
    irq_on();
    for (;;)
        ;
}
