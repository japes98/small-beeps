/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * M0d's firmware: check that startup gave C its memory, write the marker,
 * then keep a heartbeat timed by TIMER4. No interrupts yet (M1).
 */

#include "sb.h"
#include "WL82.h"

/* HW-25: in fwtest each word written here is appended to the console. The
 * SDK declares DBG_MSG read-only (Q-5), so it is written through our own
 * pointer rather than the SDK's struct. */
#define DBG_MSG (*(volatile u32 *)0x01EEE244u)

/* HW-13: TIMER4 counts 24 MHz once CON bit 0 is set. */
#define TIMER4_RUN   0x1u
#define TICKS_PER_MS 24000u

volatile struct sb_beacon sb_beacon __attribute__((section(".beacon")));

/* One of each kind of C data, for main to check that sb_start copied and
 * cleared them. */
static volatile u32 data_probe = 0x5EED0001u;
static volatile u32 bss_probe;

static void console_write(const char *text, u32 words)
{
    while (words--) {
        const u8 *b = (const u8 *)text;
        DBG_MSG = (u32)b[0] | (u32)b[1] << 8 | (u32)b[2] << 16 | (u32)b[3] << 24;
        text += 4;
    }
}

int main(void)
{
    static const char hello[16] = "small-beeps M0d\n";
    u32 start, done;

    sb_beacon.period = TICKS_PER_MS;
    if (data_probe == 0x5EED0001u && bss_probe == 0) {
        sb_beacon.marker = SB_MARKER;
        console_write(hello, sizeof hello / 4);
    } else {
        sb_beacon.marker = SB_MARKER_BAD;
    }

    /* Only differences of CNT are used: its value when started, and its
     * response to writes, don't matter. Unsigned subtraction is right
     * across a wrap of the 32-bit count. */
    JL_TIMER4->CON = TIMER4_RUN;
    start = JL_TIMER4->CNT;
    /* After starting the time base, so its start tolerance is untouched;
     * before anything that could use the stack. */
    sb_stack_fill();
#if defined(SB_PROBE_BIG)
    sb_probe_big();
#endif
#if defined(SB_PROBE_STACK)
    sb_probe_stack();
#endif
    done = 0;
    for (;;) {
        u32 now = JL_TIMER4->CNT - start;

        /* Count every whole period that has passed, so a pass that comes
         * late still leaves the right number of beats. */
        while (now - done >= TICKS_PER_MS) {
            done += TICKS_PER_MS;
            sb_beacon.beats++;
#if defined(SB_PROBE_SLOW)
            sb_probe_slow();
#endif
        }
        /* Storing on every pass also keeps core 0 busy, so fwtest's
         * captures land on time (docs/HARNESS.md, "Time"). */
        sb_beacon.ticks = now;
    }
}
