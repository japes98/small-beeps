/* SPDX-License-Identifier: MIT */
/* SPDX-FileCopyrightText: 2026 japes98 */
/* Twelve bytes to the debug console, then halt. */
#include "board.h"

int main(void)
{
    DBG_MSG = 0x6c6c6568u; /* "hell" */
    DBG_MSG = 0x6f77206fu; /* "o wo" */
    DBG_MSG = 0x0a646c72u; /* "rld\n" */
    return 0;
}
