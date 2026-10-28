/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * Core 1's start (core1.h; since clean-1027, BR-3, the platform's): core
 * 0 leaves the entry and the stack where core1_entry.S finds them,
 * points source 126's vector word at that entry and sets C1_CON bit 3
 * (HW-9); core 1 says it runs under the lock, then runs the entry.
 */

#include "core1.h"

/* HW-9: core 1 starts at the address in this word (also source 126's
 * vector) once bit 3 of C1_CON is set. */
#define CORE1_START (*(volatile u32 *)0x01C7FFF8u)
#define C1_CON      (*(volatile u32 *)0x01EEE004u)

void sb_core1_entry(void);
void sb_core1_main(void);

/* Read by core1_entry.S on core 1, before it has a stack. */
u32 *volatile sb_core1_sp;
static void (*volatile core1_fn)(void);
static volatile u32 core1_running;
static volatile u8 core1_lock;

/* Core 1, on its own stack. */
void sb_core1_main(void)
{
    sb_publish(&core1_lock, &core1_running, 1);
    core1_fn();
}

int sb_core1_start(void (*entry)(void), u32 *stack_top)
{
    u32 n, saved;

    core1_fn = entry;
    sb_core1_sp = stack_top;
    /* Its start address in source 126's vector word, then C1_CON bit 3;
     * once it runs, the word gets its stub back. */
    saved = CORE1_START;
    sb_publish(&core1_lock, (volatile u32 *)&CORE1_START, (u32)sb_core1_entry);
    C1_CON |= 1u << 3;
    for (n = 0; n < SB_CORE1_WAIT && !sb_shared(&core1_running); n++)
        ;
    CORE1_START = saved;
    return sb_shared(&core1_running) != 0;
}
