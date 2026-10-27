/* SPDX-License-Identifier: MIT */
/* SPDX-FileCopyrightText: 2026 japes98 */
/* The app in the harness's test packages (tests/package.rs): a marker
   word, the address the linker gave a table and the sum of the table read
   through that address, its own entry, then a counter that never stops.
   Linked at 0x02000120 (image-pkg.ld): booted at any other address, the
   table's address points at other bytes and the sum comes out wrong. */
#include "board.h"

static const volatile u32 table[4] = { 0x11111111u, 0x22222222u, 0x33333333u, 0x44444444u };

int main(void)
{
    u32 sum = 0;
    for (int i = 0; i < 4; i++)
        sum += table[i];
    OUT(0) = 0x600df00du;
    OUT(1) = (u32)&table[0];
    OUT(2) = sum;
    OUT(3) = (u32)&main;
    for (;;)
        OUT(4)++;
}
