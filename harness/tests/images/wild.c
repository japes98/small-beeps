/* SPDX-License-Identifier: MIT */
/* SPDX-FileCopyrightText: 2026 japes98 */
/* A jump to an address no memory holds code at: `fault`. */
#include "board.h"

int main(void)
{
    OUT(0) = 1;
    ((void (*)(void))0x10000000u)();
    return 0;
}
