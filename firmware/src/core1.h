/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * Core 1 (since clean-1027, BR-3; until then the FM engine's own,
 * docs/DESIGN-NOTES.md, M5, "Two cores"): its start, and the lock and
 * the shared loads two cores hand work over with. Any engine uses them;
 * the base's FM engine (fm_play.c) and the Plaits bench do.
 *
 * - sb_core1_start(entry, stack_top) releases core 1 into entry, on the
 *   stack that ends at stack_top (8-byte aligned; the stack grows down
 *   from it), and returns 1 once core 1 runs, or 0 if it never says so
 *   within SB_CORE1_WAIT polls (then core 0 must do core 1's work
 *   itself). Core 1 runs in supervisor mode and takes no interrupt (no
 *   source is enabled on it, HW-64); if entry ever returns, core 1 stops
 *   there with interrupts off. Call it once, from the engine's init
 *   (engine.h), before interrupts are on: it borrows source 126's vector
 *   word for core 1's start address and puts it back (HW-9).
 * - sb_lock and sb_unlock: a lock byte taken by test-and-set, csync
 *   around (HW-65); sb_shared: a shared word read after csync, so a
 *   change the other core made under the lock is seen; sb_publish: a
 *   shared word written under a lock. A hand-over is two sequence
 *   numbers: core 0 publishes a job's, core 1 polls it with sb_shared,
 *   does the job and publishes the same number back.
 */

#ifndef CORE1_H
#define CORE1_H

#include "sb.h"

#define SB_CORE1_WAIT 100000u   /* polls of its flag, about 1 ms in fwtest */

int sb_core1_start(void (*entry)(void), u32 *stack_top);

/* HW-65: test-and-set the byte until it was clear, csync around. */
static inline void sb_lock(volatile u8 *b)
{
    __asm__ volatile("csync\n"
                     "1:\n\t"
                     "testset b[%0]\n\t"
                     "ifeq goto 1b\n\t"
                     "csync" : : "r"(b) : "memory");
}

static inline void sb_unlock(volatile u8 *b)
{
    __asm__ volatile("csync" : : : "memory");
    *b = 0;
}

static inline u32 sb_shared(volatile u32 *p)
{
    __asm__ volatile("csync" : : : "memory");
    return *p;
}

static inline void sb_publish(volatile u8 *lock, volatile u32 *p, u32 v)
{
    sb_lock(lock);
    *p = v;
    sb_unlock(lock);
}

#endif
