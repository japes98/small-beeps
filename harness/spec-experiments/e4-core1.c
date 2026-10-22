/* SPDX-License-Identifier: MIT */
/* SPDX-FileCopyrightText: 2026 japes98 */
/* E-4: releasing core 1. Core 0 puts core 1's entry in the word at
   0x01C7FFF8 and sets C1_CON bit 3, then waits for core 1's marker. Core 1
   sets its own stacks, records cnum and its marker, and counts. */
#include "exp.h"

void core1_main(void)
{
    u32 id;
    __asm__ volatile("%0 = cnum" : "=r"(id));
    OUT(8) = id;
    OUT(9) = 0xc0de0001u;
    for (;;)
        OUT(10)++;
}

__asm__(".section .text, \"ax\"\n"
        "core1_start:\n"
        "\tr0 = 0x01c7c000\n"
        "\tssp = r0\n"
        "\tr0 = 0x01c7b000\n"
        "\tsp = r0\n"
        "\tusp = r0\n"
        "\tcall core1_main\n"
        "1:\tgoto 1b\n");
extern void core1_start(void);

int main(void)
{
    u32 id;
    __asm__ volatile("%0 = cnum" : "=r"(id));
    OUT(0) = id;
    CORE1_ENTRY = (u32)core1_start;
    C1_CON |= 8u;
    while (OUT(9) != 0xc0de0001u)
        OUT(1)++;
    OUT(2) = 0x600df00du;
    for (;;)
        OUT(3)++;
}
