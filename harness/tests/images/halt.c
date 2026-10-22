/* SPDX-License-Identifier: MIT */
/* SPDX-FileCopyrightText: 2026 japes98 */
/* A marker word, then return: start.S halts (`halt`). */
#include "board.h"

int main(void)
{
    OUT(0) = 0x0ddba11u;
    return 0;
}
