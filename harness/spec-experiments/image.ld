/* SPDX-License-Identifier: MIT */
/* SPDX-FileCopyrightText: 2026 japes98 */
/* The experiments run from the start of the image window (docs/HARNESS.md):
   one section, code and constants, no initialised data. */
ENTRY(_start)
SECTIONS
{
    . = 0x02000000;
    .text : { KEEP(*(.text.start)) *(.text*) *(.rodata*) . = ALIGN(4); image_end = .; }
    .data : { *(.data*) }
    .bss : { *(.bss*) *(COMMON) }
}
ASSERT(SIZEOF(.data) == 0, "experiments have no initialised data")
ASSERT(SIZEOF(.bss) == 0, "experiments keep their state at fixed RAM addresses")
