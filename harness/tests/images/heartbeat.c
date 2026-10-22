/* SPDX-License-Identifier: MIT */
/* SPDX-FileCopyrightText: 2026 japes98 */
/* A marker word, then a counter that never stops: `completed`, and the
   watchdog never fires. */
#include "board.h"

int main(void)
{
    OUT(0) = 0x600df00du;
    for (;;)
        OUT(1)++;
}
