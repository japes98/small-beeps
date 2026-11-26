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
#if defined(SB_HW_FM1)
#include "WL82.h"
#endif

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
#if defined(SB_HW_FM1) && defined(SB_HW_TEST)
    /* audio13's U2-A (the owner's rulings): the USB block's five words as
     * the app finds them, read only, before anything of ours but the
     * panel's first band (a read that hangs leaves band 1 alone on the
     * screen); kept in registers until the copy and the zeroing are done. */
    u32 u2_0 = JL_USB->CON0, u2_1 = JL_USB->CON1, u2_2 = JL_USB_IO->CON0, u2_3 = JL_USB_IO->CON1,
        u2_4 = JL_USB_IO->CON2;
#endif
#if defined(SB_HW_FM1) && defined(SB_HW_TEST)
    /* audio14's P (the owner's ruling): the block at 0x16A00, four words,
     * read only, just after U2-A's; nothing is written to it. */
    u32 p_0 = *(volatile u32 *)(HW_A14_P_BASE + 0u), p_1 = *(volatile u32 *)(HW_A14_P_BASE + 4u),
        p_2 = *(volatile u32 *)(HW_A14_P_BASE + 8u), p_3 = *(volatile u32 *)(HW_A14_P_BASE + 12u);
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
#if defined(SB_HW_TEST)
    hw_u2_boot[0] = u2_0;
    hw_u2_boot[1] = u2_1;
    hw_u2_boot[2] = u2_2;
    hw_u2_boot[3] = u2_3;
    hw_u2_boot[4] = u2_4;
    hw_p_boot[0] = p_0;
    hw_p_boot[1] = p_1;
    hw_p_boot[2] = p_2;
    hw_p_boot[3] = p_3;
#endif
    /* Code just copied to RAM runs after a csync (HW-127). */
    __asm__ volatile("csync" ::: "memory");
#endif

    main();
}
