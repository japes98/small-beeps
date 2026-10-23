/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * The firmware's main: check that startup gave C its memory, write the
 * marker, measure the core clock, start the 1 ms tick interrupt that
 * keeps the heartbeat (M1), bring up the screen and show the address
 * pattern, then the test screen (M2), start scanning the panel (M3), and
 * idle between interrupts, putting the heartbeat on the screen once a
 * second and showing the panel's controls on the panel screen from the
 * first touch on.
 */

#include "sb.h"
#include "input.h"
#include "WL82.h"

/* HW-25: in fwtest each word written here is appended to the console. The
 * SDK declares DBG_MSG read-only (Q-5), so it is written through our own
 * pointer rather than the SDK's struct. */
#define DBG_MSG (*(volatile u32 *)0x01EEE244u)

/* HW-13: TIMER4 counts 24 MHz once CON bit 0 is set: the time base. */
#define TIMER4_RUN   0x1u
#define TICKS_PER_MS 24000u

/* HW-16: TIMER0 runs with CON bits 0-1 non-zero, bits 4-7 = 2 divide the
 * 24 MHz clock by 16, and it interrupts on reaching PRD: 1500 counts of
 * 1.5 MHz is 1 ms. Writing CON with bit 14 acknowledges it. */
#define TICK_CON     0x21u
#define TICK_ACK     (1u << 14)
#define TICK_PRD     1500u

/* HW-19, HW-20: the sources main enables, and their priorities. The tick
 * is above SPI1's, so a tick waits at most for one short SPI1 handler
 * (DESIGN-NOTES.md, M2). */
#define SRC_TIMER0   4u
#define SRC_SPI1     16u
#define PRIO_TICK    1u
#define PRIO_SPI1    0u

/* When the test screen replaces the address pattern, in beats. */
#define TEST_SCREEN_MS 500u
#define BEATS_PER_SECOND 1000u

extern u32 __stack_limit[], __irq_stack_top[];

volatile struct sb_beacon sb_beacon __attribute__((section(".beacon")));

/* One of each kind of C data, for main to check that sb_start copied and
 * cleared them. */
static volatile u32 data_probe = 0x5EED0001u;
static volatile u32 bss_probe;

/* The heartbeat's state, kept by sb_tick: the time base when main started
 * it, the ticks counted into beats so far, the time base at the last
 * tick; and the next whole second. */
static u32 tb_start, tb_done, tb_last, next_second = 1000;

volatile u32 sb_work, sb_seconds;

u32 sb_now(void)
{
    return JL_TIMER4->CNT;
}

u32 sb_ticks(void)
{
    return JL_TIMER4->CNT - tb_start;
}

/* Waits at least ms milliseconds on the heartbeat, idling between ticks:
 * one beat more, since the first may be nearly over. */
void sb_wait_ms(u32 ms)
{
    u32 until = sb_beacon.beats + ms + 1;

    while ((int)(sb_beacon.beats - until) < 0)
        __asm__ volatile("idle");
}

void sb_console_write(const char *text, u32 words)
{
    while (words--) {
        const u8 *b = (const u8 *)text;
        DBG_MSG = (u32)b[0] | (u32)b[1] << 8 | (u32)b[2] << 16 | (u32)b[3] << 24;
        text += 4;
    }
}

/* The tick. The heartbeat counts whole milliseconds of the time base, not
 * ticks, so it stays exact whatever the tick's own period does (our fwtest
 * runs measure TIMER0's 1 ms as 24 000.7 time base ticks: DESIGN-NOTES.md,
 * M1); the ticks and their intervals are counted on the side. */
void sb_tick(void)
{
    u32 now = JL_TIMER4->CNT - tb_start;
    u32 n = sb_beacon.tick_count, beats;

    JL_TIMER0->CON = TICK_CON | TICK_ACK;
    sb_beacon.seq++;
    if (n) {
        u32 d = now - tb_last;
        if (n == 1 || d < sb_beacon.interval_min)
            sb_beacon.interval_min = d;
        if (d > sb_beacon.interval_max)
            sb_beacon.interval_max = d;
    }
    tb_last = now;
    sb_beacon.tick_count = n + 1;
    /* Every whole millisecond that has passed, so a late tick still leaves
     * the right count. Unsigned differences stay right across a wrap. */
    beats = sb_beacon.beats;
    while (now - tb_done >= TICKS_PER_MS) {
        tb_done += TICKS_PER_MS;
        beats++;
#if defined(SB_PROBE_SLOW)
        sb_probe_slow();
#endif
    }
    sb_beacon.beats = beats;
    sb_beacon.ticks = now;
    sb_beacon.beats_b = beats;
    sb_beacon.ticks_b = now;
    sb_beacon.seq++;
    /* A whole second: main puts it on the screen (since M3 the tick tells
     * it, as the input scan's interrupts wake main too). */
    if (beats >= next_second) {
        next_second += BEATS_PER_SECOND;
        sb_seconds++;
        sb_work++;
    }

    /* Each stack's lowest word still holds the fill: nothing ran past it. */
    if (__irq_stack_top[0] != SB_STACK_FILL)
        sb_halt(SB_HALT_STACK, 1, 0);
    if (__stack_limit[0] != SB_STACK_FILL)
        sb_halt(SB_HALT_STACK, 2, 0);
}

int main(void)
{
    static const char hello[16] = "small-beeps M3 \n";

    sb_beacon.period = TICKS_PER_MS;
    if (data_probe == 0x5EED0001u && bss_probe == 0) {
        sb_beacon.marker = SB_MARKER;
        sb_console_write(hello, sizeof hello / 4);
    } else {
        sb_beacon.marker = SB_MARKER_BAD;
    }

    /* Only differences of CNT are used: its value when started, and its
     * response to writes, don't matter. */
    JL_TIMER4->CON = TIMER4_RUN;
    tb_start = JL_TIMER4->CNT;
    /* No clock register is written (HW-11, SR-2): the clock is measured. */
    sb_beacon.clock = sb_clock_measure((volatile u32 *)&JL_TIMER4->CNT);
#if defined(SB_PROBE_BIG)
    sb_probe_big();
#endif
#if defined(SB_PROBE_STACK)
    sb_probe_stack();
#endif

    sb_irq_init();
    sb_irq_enable(SRC_TIMER0, sb_tick, PRIO_TICK);
    sb_irq_enable(SRC_SPI1, lcd_spi_done, PRIO_SPI1);
    JL_TIMER0->CNT = 0;
    JL_TIMER0->PRD = TICK_PRD;
    JL_TIMER0->CON = TICK_CON;
    input_start();
#if defined(SB_TEST_LEDS)
    sb_test_leds();
#endif
    sb_irq_on();

#if defined(SB_TEST_FAULT)
    sb_test_fault();
#endif
#if defined(SB_TEST_STRAY)
    sb_test_stray();
#endif
#if defined(SB_TEST_BADINSN)
    sb_test_badinsn();
#endif

    /* The screen: the controller's start, the address pattern sent while
     * the display is still off, then display on (DESIGN-NOTES.md, M2). */
    lcd_init();
    screen_pattern();
    lcd_send_rows(0, SCREEN_H);
    lcd_command(LCD_DISPON, 0, 0);
    sb_beacon.screen = SB_SCREEN_PATTERN;

    if (sb_beacon.beats + 1 < TEST_SCREEN_MS)
        sb_wait_ms(TEST_SCREEN_MS - 1 - sb_beacon.beats);
    {
        u32 t = sb_now();
        screen_test();
        sb_beacon.render_ticks = sb_now() - t;
    }
    lcd_send_rows(0, SCREEN_H);
    sb_beacon.screen = SB_SCREEN_TEST;
#if defined(SB_TEST_FLOOD)
    sb_test_flood();
#endif

    /* Between interrupts the core waits. Since M3 the input scan wakes it
     * twelve times a tick as well, so each wake only looks whether the
     * tick (at a whole second) or the scan (with an event) added work,
     * and the rest is done then (DESIGN-NOTES.md, M3). The wakes are
     * counted in a register and reach the beacon, with the ticks taken,
     * whenever there is work, for the test of R-IRQ-1. An interrupt that
     * adds work between the test and the idle leaves it until the next
     * wake, at most one scan slot (83 us) later. */
    {
        u32 wakes, seen, second;

        lcd_wait();
        wakes = sb_beacon.wakes;
        sb_beacon.loop_ticks = sb_beacon.tick_count;
        seen = sb_work;
        second = sb_seconds;
        for (;;) {
            __asm__ volatile("idle");
            wakes++;
            if (sb_work != seen) {
                seen = sb_work;
                sb_beacon.wakes = wakes;
                sb_beacon.wakes_ticks = sb_beacon.tick_count;
                panel_serve();
                while (second != sb_seconds) {
                    second++;
                    screen_beat();
                }
            }
        }
    }
}
