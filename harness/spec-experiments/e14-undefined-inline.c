/* SPDX-License-Identifier: MIT */
/* SPDX-FileCopyrightText: 2026 japes98 */
/* E-14: an undecodable halfword inline, right after a marker store in the
   same straight-line code (E-11 has it in a function of its own). The run
   should end as fwtest's fault; the marker shows whether the store before
   it ran. */
#include "exp.h"

int main(void)
{
    OUT(0) = 0xbad3u;
    __asm__ volatile(".2byte 0xffff\n\t.2byte 0xffff");
    OUT(1) = 0x600dd00eu;
    return 0;
}
