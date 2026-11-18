/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * The FM-1 hardware build (SB_HW_FM1, hw_fm1.c; R-HW-1): the panel's
 * bring-up before the copy to RAM, the start-up's bands, and the halt
 * screen, all polled and in the window; and TIMER0 as the build's one
 * timer (main.c).
 */

#ifndef HW_FM1_H
#define HW_FM1_H

#include "sb.h"

#if defined(SB_HW_FM1)
#if defined(SB_ENGINE_EXTERNAL) || defined(SB_NO_START_SCREENS)
#error "SB_HW_FM1 is the base's own start-up on a unit: not with SB_ENGINE_EXTERNAL or SB_NO_START_SCREENS"
#endif
#if defined(SB_PROBE_RETURN) || defined(SB_PROBE_LIGHT) || defined(SB_PROBE_PANEL)
#error "SB_HW_FM1 is not a probe: build it without SB_PROBE_*"
#endif

void hw_early(void);
void hw_fill(u32 x, u32 y, u32 w, u32 h, u32 colour);
void hw_band(u32 n);
void hw_halt_screen(void);

/* TIMER0, the build's one timer (HW-119: it runs from the 60 MHz
 * low-speed bus; HW-48: prescaler setting 0 divides by 1): an interrupt
 * every HW_SLOT_PRD counts, 83.3 us, one scan slot; twelve make the 1 ms
 * tick. CON bits 0-1 set to 1 to run it is fwtest's reading (HW-48),
 * taken for the chip too: SR-16. */
#define HW_SLOT_CON   0x1u
#define HW_SLOT_PRD   5000u
#define HW_SLOTS_TICK 12u
/* sb_now()'s 24 MHz units in one slot, and per count: 2000 and 2 / 5. */
#define HW_SLOT_UNITS 2000u
void hw_slot(void) __attribute__((interrupt("")));
#endif

#endif
