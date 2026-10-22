/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * Memory layout for the raw image (docs/DESIGN-NOTES.md, M0d).
 *
 * IMAGE: the code window. The image's first byte is at its start and is
 *   the first instruction run (HW-1); the window shows the flash chip from
 *   offset 0x4000, so an image may be up to 1 MiB less 16 KiB (HW-5).
 * RAM: main RAM is 512 KiB from 0x01C00000 on the chip (HW-6). Its top,
 *   from 0x01C7FC00, is not part of RAM here: the block r0 points to at
 *   entry (HW-4) and the SDK's boot and update area are left alone, and
 *   the vector table at 0x01C7FE00 (HW-18) is written only by
 *   firmware/src/irq.c, through __vectors. fwtest has more RAM (HW-7);
 *   this layout uses only what the chip has.
 * The stack area is two stacks (HW-3): main's, on sp, at the top, and the
 *   interrupt stack, on ssp, below it. Each one's lowest word is its guard
 *   (docs/DESIGN-NOTES.md, M1).
 */

OUTPUT_ARCH(pi32v2)
ENTRY(_start)

MEMORY
{
    IMAGE (rx)  : ORIGIN = 0x02000000, LENGTH = 0x000FC000
    RAM   (rwx) : ORIGIN = 0x01C00000, LENGTH = 0x0007FC00
}

STACK_SIZE = 0x1000;          /* both stacks */
IRQ_STACK_SIZE = 0x800;       /* the lower half: interrupts, on ssp */

SECTIONS
{
    .text : {
        KEEP(*(.text.entry))
        *(.text .text.*)
        *(.rodata .rodata.*)
        . = ALIGN(4);
    } > IMAGE

    /* Fixed at the start of RAM so the tests know where it is. */
    .beacon (NOLOAD) : {
        __bss_start = .;
        KEEP(*(.beacon))
    } > RAM

    .bss (NOLOAD) : {
        *(.bss .bss.*)
        . = ALIGN(4);
        __bss_end = .;
    } > RAM

    /* Runs from RAM, loaded from the image just after the code. */
    .data : {
        __data_start = .;
        *(.data .data.*)
        . = ALIGN(4);
        __data_end = .;
    } > RAM AT > IMAGE
    __data_load = LOADADDR(.data);

    /* The stack takes the top of RAM and grows down from __stack_top. */
    __stack_top = ORIGIN(RAM) + LENGTH(RAM);
    __stack_limit = __stack_top - STACK_SIZE;
    __irq_stack_top = __stack_limit + IRQ_STACK_SIZE;
    __vectors = 0x01C7FE00;

    ASSERT(ADDR(.beacon) == 0x01C00000, "the beacon must start main RAM")
    ASSERT(__data_end <= __stack_limit, "data and bss run into the stack")
    ASSERT(__stack_top == 0x01C7FC00, "the stack must end below the reserved top of RAM")
    ASSERT(__stack_top % 8 == 0, "the stack must be 8-byte aligned")
    ASSERT(__irq_stack_top % 8 == 0, "the interrupt stack must be 8-byte aligned")
    ASSERT(__vectors == __stack_top + 0x200, "the vector table is HW-18's, above the reserved area")
    ASSERT(sb_irq_stubs_end - sb_irq_stubs == 128 * 2, "crt0.S's stubs must be 2 bytes each")

    /* Debug information: kept in the ELF, never loaded. Every section is
     * placed by name (the build links with --orphan-handling=error). */
    .debug_info     0 : { *(.debug_info) }
    .debug_abbrev   0 : { *(.debug_abbrev) }
    .debug_line     0 : { *(.debug_line) }
    .debug_str      0 : { *(.debug_str) }
    .debug_loc      0 : { *(.debug_loc) }
    .debug_ranges   0 : { *(.debug_ranges) }
    .debug_frame    0 : { *(.debug_frame) }
    .debug_macinfo  0 : { *(.debug_macinfo) }
    .debug_pubnames 0 : { *(.debug_pubnames) }
    .debug_pubtypes 0 : { *(.debug_pubtypes) }

    /DISCARD/ : { *(.comment) }
}
