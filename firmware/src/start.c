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

extern u32 __data_load[], __data_start[], __data_end[];
extern u32 __bss_start[], __bss_end[];

void sb_start(void) __attribute__((noreturn, section(".boot.text")));

void sb_start(void)
{
    const u32 *src = __data_load;
    u32 *dst;

    /* Code, constants and initialised data: their bytes sit in the
     * image, after the boot code. */
    for (dst = __data_start; dst < __data_end; dst++)
        *dst = *src++;

    /* Zero-initialised data. fwtest starts with RAM cleared, but a loader
     * on the chip makes no such promise. */
    for (dst = __bss_start; dst < __bss_end; dst++)
        *dst = 0;

    main();
}
