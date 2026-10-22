/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * Test builds only. tools/perf.py builds the firmware with each of
 * SB_PROBE_SLOW, SB_PROBE_BIG and SB_PROBE_STACK defined, and checks that
 * the performance gates fail the first two and that the stack's high-water
 * mark sees the third (R-PERF-3, R-PERF-5). tools/fw-suite.py builds it
 * with each of SB_TEST_FAULT, SB_TEST_STRAY and SB_TEST_BADINSN, which go
 * wrong on purpose once interrupts are on (R-IRQ-3, R-IRQ-4). The firmware
 * itself is built with none, and then nothing here is compiled.
 */

#include "sb.h"
#include "WL82.h"

#if defined(SB_PROBE_STACK)
static volatile u32 probe_sink;
#endif

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

#if defined(SB_PROBE_STACK)
/* A known amount of stack: a 1 KiB frame, written with zeros (which RAM
 * already holds in fwtest, so only the fill pattern can show them) and
 * read back. The high-water mark must be at least 1024 bytes. */
static void __attribute__((noinline)) probe_zero_frame(void)
{
    volatile u32 frame[256];
    u32 i, sum = 0;

    for (i = 0; i < 256; i++)
        frame[i] = 0;
    for (i = 0; i < 256; i++)
        sum += frame[i];
    probe_sink = sum;
}

void sb_probe_stack(void)
{
    probe_zero_frame();
}
#endif

#if defined(SB_TEST_FAULT)
/* Overruns main's stack: a frame as big as the whole stack, written, so
 * the stack's guard word is overwritten. The next tick must find it and
 * halt with "HALT stack 001". */
static volatile u32 test_sink;

static void __attribute__((noinline)) test_overrun(void)
{
    volatile u32 frame[512];
    u32 i;

    _Static_assert(sizeof frame >= 0x800, "the frame covers main's whole stack");
    for (i = 0; i < 512; i++)
        frame[i] = i;
    test_sink = frame[0];
}

void sb_test_fault(void)
{
    test_overrun();
}
#endif

#if defined(SB_TEST_STRAY)
/* An interrupt nothing handles: software interrupt 7 (source 127, HW-19),
 * enabled (HW-20) and raised (HW-23). It must halt with "HALT stray 07f". */
void sb_test_stray(void)
{
    (&q32DSP(0)->ICFG00)[127 / 8] = (1u | 1u << 1) << 4 * (127 % 8);
    q32DSP(0)->ILAT_SET = 1u << 7;
}
#endif

#if defined(SB_TEST_BADINSN)
/* An instruction the emulated CPU cannot decode. fwtest stops the run with
 * its own fault outcome before any handler of ours runs: a limit of the
 * harness, not something the firmware reports (SR-1). */
void sb_test_badinsn(void)
{
    __asm__ volatile(".short 0xffff\n\t.short 0xffff");
}
#endif
