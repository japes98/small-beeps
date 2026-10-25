/* SPDX-License-Identifier: MIT */
/* SPDX-FileCopyrightText: 2026 japes98 */
/* The experiments' image.ld plus code that runs from RAM: functions in section .ramtext are
   linked at 0x01C40000 and stored right after .text in the image, and
   ram_init() (e22-flash.c) copies them there before anything calls them. */
ENTRY(_start)
SECTIONS
{
    . = 0x02000000;
    .text : { KEEP(*(.text.start)) *(.text*) *(.rodata*) . = ALIGN(4); }
    .ramtext 0x01c40000 : AT(LOADADDR(.text) + SIZEOF(.text)) { *(.ramtext*) . = ALIGN(4); }
    __ramtext_load = LOADADDR(.ramtext);
    __ramtext_start = ADDR(.ramtext);
    __ramtext_end = ADDR(.ramtext) + SIZEOF(.ramtext);
    .data : { *(.data*) }
    .bss : { *(.bss*) *(COMMON) }
}
ASSERT(SIZEOF(.data) == 0, "experiments have no initialised data")
ASSERT(SIZEOF(.bss) == 0, "experiments keep their state at fixed RAM addresses")
