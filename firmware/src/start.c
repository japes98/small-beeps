/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * C runtime start: give C its initial memory, then run main. Called from
 * crt0.S on the stack it set up. The symbols come from firmware/app.ld.
 * Since M7 the initial data begins with every instruction and constant
 * but the boot code's, so this runs from the window and copies them to
 * RAM, where main and everything after it run (docs/DESIGN-NOTES.md, M7).
 */

#include "sb.h"
#include "hw_fm1.h"

extern u32 __data_load[], __data_start[], __data_end[];
extern u32 __bss_start[], __bss_end[];

#if defined(SB_HW_FM1)
void sb_start(u32 boot_block) __attribute__((noreturn, section(".boot.text")));

void sb_start(u32 boot_block)
#else
void sb_start(void) __attribute__((noreturn, section(".boot.text")));

void sb_start(void)
#endif
{
    const u32 *src = __data_load;
    u32 *dst;
#if defined(SB_HW_FM1)
    /* The chip key, 16 bits at +12 of the block r0 pointed at (HW-112),
     * read before anything can write the vector table over it (HW-126). */
    u32 key = *(volatile unsigned short *)(boot_block + 12);
#endif

#if defined(SB_HW_FM1)
    /* On a unit: the panel up and band 1 drawn, from the window, before
     * anything else can go wrong (hw_fm1.c). */
    hw_early();
#endif
    /* Code, constants and initialised data: their bytes sit in the
     * image, after the boot code. */
    for (dst = __data_start; dst < __data_end; dst++)
        *dst = *src++;

    /* Zero-initialised data. fwtest starts with RAM cleared, but a loader
     * on the chip makes no such promise. */
    for (dst = __bss_start; dst < __bss_end; dst++)
        *dst = 0;
#if defined(SB_HW_FM1)
    hw_boot_block = boot_block;
    hw_boot_key = key;
    /* Code just copied to RAM runs after a csync (HW-127). */
    __asm__ volatile("csync" ::: "memory");
#endif

    main();
}
