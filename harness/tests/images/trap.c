/* SPDX-License-Identifier: MIT */
/* SPDX-FileCopyrightText: 2026 japes98 */
/* A breakpoint: the compiler's __builtin_trap(), built with the firmware's
   CPU flags (build.sh), is `bkpt`. OUT(0) is written first; the run must
   end as a trap at the bkpt, not as a fault (tests/fwtest.rs,
   bkpt_ends_the_run_as_a_trap). */
#include "board.h"

int main(void)
{
    OUT(0) = 0x7a7a7a7au;
    __builtin_trap();
}
