/* SPDX-License-Identifier: MIT */
/* SPDX-FileCopyrightText: 2026 japes98 */
/* E-2: the debug message register as fwtest's console sees it: two word
   writes, then a byte write and a halfword write, then a word. */
#include "exp.h"

int main(void)
{
    DBG_MSG = 0x64636261u;                        /* "abcd" */
    DBG_MSG = 0x0a3a3231u;                        /* "12:\n" */
    *(volatile u8 *)0x1eee244u = 'X';             /* a byte write */
    *(volatile u16 *)0x1eee244u = 0x5a59u;        /* a halfword write: "YZ" */
    DBG_MSG = 0x0a646e65u;                        /* "end\n" */
    return 0;
}
