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

/* The beacon: four words at the start of main RAM (firmware/app.ld) that
 * fwtest reads with --ram and --watchdog (HW-26). Tests depend on this
 * layout; change it only together with tests/fw/. */
struct sb_beacon {
    u32 marker;   /* SB_MARKER once main runs and startup checked out */
    u32 beats;    /* heartbeat: whole milliseconds since main started it */
    u32 ticks;    /* time base ticks since then, stored on every pass */
    u32 period;   /* ticks per heartbeat, for the tests to read */
};

#define SB_MARKER     0x44304253u  /* "SB0D" in memory order */
#define SB_MARKER_BAD 0x21444142u  /* "BAD!": startup left data wrong */

extern volatile struct sb_beacon sb_beacon;

int main(void) __attribute__((noreturn));

/* Test builds only (firmware/src/probe.c). */
#if defined(SB_PROBE_SLOW)
void sb_probe_slow(void);
#endif
#if defined(SB_PROBE_BIG)
void sb_probe_big(void);
#endif

#endif
