/* SPDX-License-Identifier: MIT */
/* SPDX-FileCopyrightText: 2026 japes98 */
/* The test app in a package (docs/HARNESS.md, "Packages"): linked where a
   package's app runs, the window's start plus its offset in the app area
   (0x120, after the area's directory), not at the window's start as the
   raw images are. Otherwise as image.ld. */
ENTRY(_start)
SECTIONS
{
    . = 0x02000120;
    .text : { KEEP(*(.text.start)) *(.text*) *(.rodata*) }
    .data : { *(.data*) }
    .bss : { *(.bss*) *(COMMON) }
}
ASSERT(SIZEOF(.data) == 0, "test images have no initialised data")
ASSERT(SIZEOF(.bss) == 0, "test images keep their state at fixed RAM addresses")
