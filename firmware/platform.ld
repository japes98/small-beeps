/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * The platform's memory layout (docs/DESIGN-NOTES.md, M0d; since
 * clean-1027, BR-2, the platform's part of what firmware/app.ld was): it
 * links the platform's files with any engine, the base's instrument
 * (firmware/app.ld includes this and adds the instrument's assertions)
 * or a firmware built on the base (tools/build.sh build --platform, which
 * links with this, or with that firmware's own script through --ld,
 * which includes it the same way; docs/BUILDING-ON-SMALL-BEEPS.md). Its
 * assertions cover only the platform's records. An engine's records go
 * in the sections .beacon.engine0 to .beacon.engine4 and .beacon.engine
 * (below, .beacon).
 *
 * IMAGE: the code window. The image's first byte is at its start and is
 *   the first instruction run (HW-1); the window shows the flash chip from
 *   offset 0x4000, so an image may be up to 1 MiB less 16 KiB (HW-5).
 * Since M7 only the boot code runs from the window (.boot.text: _start,
 *   the stack fill and sb_start); sb_start copies every other instruction
 *   and constant to RAM with the initial data, so nothing reads the window
 *   once main runs, and the flash may be busy erasing or programming
 *   without anything waiting on it (docs/DESIGN-NOTES.md, M7; HW-79). The
 *   image ends before chip offset 0xEA000, where the stock firmware's
 *   user patch region begins (HW-80), so it never overwrites the stock
 *   firmware's saved patches; since M8a the store (store.h) takes chip
 *   offsets 0xFC000 to 0xFEFFF, past that region, unless a firmware
 *   built on the base chooses its own region (STORE_BASE, below).
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

/* The store's region (store.h), chip offsets STORE_BASE to STORE_BASE +
 * STORE_SIZE - 1: by default the stock layout's unused region, 0xFC000
 * to 0xFEFFF, 3 sectors (HW-80; M8a). Since clean-store-region a
 * firmware built on the base may choose its own: its linker script sets
 * both before its INCLUDE platform.ld (docs/BUILDING-ON-SMALL-BEEPS.md,
 * "Where the store goes"). The store reads them as sb_store_base and
 * sb_store_size. tools/build.sh checks every link's region
 * (tools/store-region.pl): whole sectors, 3 at least and
 * STORE_SECTORS_MAX at most, either in the app area after the image or
 * in the unused region, never in the stock firmware's user patch region,
 * which begins at chip offset 0xEA000 (HW-80). */
STORE_BASE = DEFINED(STORE_BASE) ? STORE_BASE : 0xFC000;
STORE_SIZE = DEFINED(STORE_SIZE) ? STORE_SIZE : 0x3000;
sb_store_base = STORE_BASE;
sb_store_size = STORE_SIZE;
USER_REGION = 0xEA000;

/* Where the image's first byte runs (Phase A1, HW-91): the raw image at
 * the window's start; the package link (tools/build.sh, with
 * --defsym=IMAGE_ORIGIN=0x02000120) where a package's app.bin runs, past
 * the app area's 0x120-byte directory. The same code either way: only the
 * boot code runs from the window, and it addresses the rest by symbols. */
IMAGE_ORIGIN = DEFINED(IMAGE_ORIGIN) ? IMAGE_ORIGIN : 0x02000000;

MEMORY
{
    IMAGE (rx)  : ORIGIN = IMAGE_ORIGIN, LENGTH = 0xEA000 - 0x4000 - (IMAGE_ORIGIN - 0x02000000)   /* to USER_REGION */
    RAM   (rwx) : ORIGIN = 0x01C00000, LENGTH = 0x0007FC00
}

STACK_SIZE = 0x1000;          /* both stacks */
IRQ_STACK_SIZE = 0x800;       /* the lower half: interrupts, on ssp */

SECTIONS
{
    /* Run from the window: only what runs before the copy to RAM. */
    .text : {
        KEEP(*(.text.entry))
        *(.boot.text)
        . = ALIGN(4);
    } > IMAGE

    /* Fixed at the start of RAM so the tests know where it is: the
     * beacon, then (since M3) the input record and (since M4) the audio
     * record, (since M5) the engine's slot, (since M6a) MIDI's, (since
     * M6b) MIDI out's and (since M7) the store's; then the engine's
     * records (since clean-1027 named for any engine: the base's
     * instrument puts its interface's and its arpeggiator's there, a
     * firmware built on the base its own; docs/BUILDING-ON-SMALL-BEEPS.md).
     * - .beacon.engine0: one record of at most 64 bytes, at 0x01C00590
     *   (the instrument's FM engine's). Its 64 bytes are kept whether
     *   anything fills them or not, so MIDI's record and those after it
     *   stay where they are.
     * - .beacon.engine1 to .beacon.engine4, in that order, then
     *   .beacon.engine: from 0x01C00870 on, after the store's, as large
     *   as they need. */
    .beacon (NOLOAD) : {
        __bss_start = .;
        KEEP(*(.beacon))
        KEEP(*(.beacon.input))
        KEEP(*(.beacon.audio))
        __engine_slot = .;
        KEEP(*(.beacon.engine0))
        . = __engine_slot + 0x40;
        KEEP(*(.beacon.midi))
        KEEP(*(.beacon.midiout))
        KEEP(*(.beacon.store))
        __engine_records = .;
        KEEP(*(.beacon.engine1))
        KEEP(*(.beacon.engine2))
        KEEP(*(.beacon.engine3))
        KEEP(*(.beacon.engine4))
        KEEP(*(.beacon.engine))
    } > RAM

    .bss (NOLOAD) : {
        *(.bss .bss.*)
        . = ALIGN(4);
        __bss_end = .;
    } > RAM

    /* Runs from RAM, loaded from the image just after the boot code:
     * since M7 the code and constants (from __ram_code_start to
     * __ram_code_end), then the initialised data, copied together. */
    .data : {
        __data_start = .;
        __ram_code_start = .;
        *(.text .text.*)
        *(.rodata .rodata.*)
        . = ALIGN(4);
        __ram_code_end = .;
        *(.data .data.*)
        /* C++ static objects' constructors (since clean-1027, BR-4): main()
         * runs them, last first, before an engine's init (main.c). The
         * base has none. */
        . = ALIGN(4);
        __ctors_start = .;
        KEEP(*(.ctors))
        __ctors_end = .;
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
    ASSERT(sb_input == 0x01C00060, "the input record must follow the beacon (M3)")
    ASSERT(sb_audio == 0x01C00550, "the audio record must follow the input record (M4)")
    ASSERT(__engine_slot == 0x01C00590, "the engine's slot must follow the audio record (M5)")
    ASSERT(sb_midi == 0x01C005D0, "the MIDI record must follow the engine's slot (M6a)")
    ASSERT(sb_midi_out == 0x01C00734, "the MIDI out record must follow MIDI in's (M6b)")
    ASSERT(sb_store == 0x01C00780, "the store's record must follow MIDI out's (M7)")
    ASSERT(__engine_records == 0x01C00870, "the engine's records must follow the store's (M8a)")
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
