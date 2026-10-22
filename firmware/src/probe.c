/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * Test builds only. tools/perf.py builds the firmware once with
 * SB_PROBE_SLOW and once with SB_PROBE_BIG defined, and checks that the
 * performance gates fail each one (R-PERF-5). The firmware itself is built
 * with neither, and then nothing here is compiled.
 */

#include "sb.h"

#if defined(SB_PROBE_SLOW)
/* Extra work on every heartbeat beat: the speed gate must catch it. */
void sb_probe_slow(void)
{
    volatile u32 i;

    for (i = 0; i < 20; i++)
        ;
}
#endif

#if defined(SB_PROBE_BIG)
/* More code (a 1 KiB table among the constants), more static RAM (256
 * bytes of zeroed data) and a deeper stack (512 bytes, every word written
 * with a non-zero value): each budget must catch its own. */
static const u32 probe_table[256] = { 1 };
static volatile u32 probe_ram[64];

static void __attribute__((noinline)) probe_stack(void)
{
    volatile u32 frame[128];
    u32 i;

    for (i = 0; i < 128; i++)
        frame[i] = i + 1;
    probe_ram[0] = frame[127];
}

void sb_probe_big(void)
{
    probe_stack();
    probe_ram[1] = probe_table[sb_beacon.beats & 255];
}
#endif
