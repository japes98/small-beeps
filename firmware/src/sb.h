/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * Our own minimal runtime definitions. The firmware is built with
 * -nostdinc, so nothing here comes from a C library.
 */

#ifndef SB_H
#define SB_H

typedef unsigned char u8;
typedef unsigned int u32;

_Static_assert(sizeof(u32) == 4, "u32 is 32 bits");

/* The beacon: words at the start of main RAM (firmware/app.ld) that
 * fwtest reads with --ram and --watchdog (HW-26). Tests depend on this
 * layout; change it only together with tests/fw/ and tools/fw-suite.py.
 * The first four words keep M0d's meaning, which tools/perf.py also reads
 * from older records' images. fwtest can take a capture in the middle of
 * the tick handler (docs/HARNESS.md, "Time"), so the handler writes the
 * heartbeat twice, first (beats, ticks) then (beats_b, ticks_b), between
 * two increments of seq: a capture can split at most one copy, so at
 * least one is always consistent, and both are when seq is even. */
struct sb_beacon {
    u32 marker;   /* SB_MARKER once main runs and startup checked out */
    u32 beats;    /* heartbeat: whole milliseconds of the time base */
    u32 ticks;    /* time base ticks since main started it, at the last tick */
    u32 period;   /* ticks per heartbeat, for the tests to read */
    u32 seq;      /* odd while the tick handler is updating the heartbeat */
    u32 beats_b;  /* the second copy of beats and ticks, written after them */
    u32 ticks_b;
    u32 tick_count;     /* tick interrupts taken */
    u32 interval_min;   /* shortest time base interval between two ticks */
    u32 interval_max;   /* longest */
    u32 wakes;          /* times main's idle wait returned */
    u32 clock;          /* sb_clock_measure: time base ticks per SB_CLOCK_CYCLES */
    u32 halt_reason;    /* SB_HALT_*, 0 while running */
    u32 halt_source;    /* the interrupt source, or which stack's guard */
    u32 halt_reti;      /* where the interrupt came in (reti), if any */
};

#define SB_MARKER     0x44304253u  /* "SB0D" in memory order */
#define SB_MARKER_BAD 0x21444142u  /* "BAD!": startup left data wrong */

/* The stack fill pattern, which is also each stack's guard (crt0.S). */
#define SB_STACK_FILL 0x4B415453u  /* "STAK" */

/* Why the firmware halted (the beacon, and the console line). */
#define SB_HALT_STRAY 1u  /* an interrupt with no handler */
#define SB_HALT_FAULT 2u  /* a CPU exception source (0 to 2) */
#define SB_HALT_STACK 3u  /* a stack's guard word was overwritten */

extern volatile struct sb_beacon sb_beacon;

int main(void) __attribute__((noreturn));

/* main.c */
void sb_console_write(const char *text, u32 words);
void sb_tick(void) __attribute__((interrupt("")));

/* irq.c */
void sb_irq_init(void (*tick)(void));
void sb_irq_on(void);
void sb_halt(u32 reason, u32 source, u32 reti) __attribute__((noreturn));

/* crt0.S */
u32 sb_clock_measure(void);
#define SB_CLOCK_CYCLES 2402u  /* instructions between its two reads */

/* Test builds only (firmware/src/probe.c). */
#if defined(SB_PROBE_SLOW)
void sb_probe_slow(void);
#endif
#if defined(SB_PROBE_BIG)
void sb_probe_big(void);
#endif
#if defined(SB_PROBE_STACK)
void sb_probe_stack(void);
#endif
#if defined(SB_TEST_FAULT)
void sb_test_fault(void);
#endif
#if defined(SB_TEST_STRAY)
void sb_test_stray(void);
#endif
#if defined(SB_TEST_BADINSN)
void sb_test_badinsn(void);
#endif

#endif
