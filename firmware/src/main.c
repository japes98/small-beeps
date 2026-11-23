/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * The firmware's main: check that startup gave C its memory, write the
 * marker, measure the core clock, start the 1 ms tick interrupt that
 * keeps the heartbeat (M1), bring up the screen and show the address
 * pattern, then the test screen (M2), start scanning the panel (M3) and
 * the audio output with the test instrument (M4), and idle between
 * interrupts, putting the heartbeat on the test screen once a
 * second and, from the first touch on, the instrument's screens (M8a,
 * views.c). Built with SB_ENGINE_EXTERNAL (since clean-1027, BR-1) it
 * runs an engine defined outside the base's instrument instead
 * (engine.h), and with SB_NO_START_SCREENS as well (since BR-16) shows
 * black in place of the pattern and the test screen.
 */

#include "sb.h"
#include "input.h"
#include "audio.h"
#include "engine.h"
#include "fm.h"
#include "store.h"
#include "ui.h"
#include "WL82.h"
#include "hw_fm1.h"
#if defined(SB_USB_MIDI)
#include "usb_midi.h"
#endif

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
 * (DESIGN-NOTES.md, M2); since M4 both are above the audio engine's (0),
 * which they may interrupt (DESIGN-NOTES.md, M4). */
#define SRC_TIMER0   4u
#define SRC_SPI1     16u
#define PRIO_TICK    2u
#define PRIO_SPI1    1u

/* When the test screen replaces the address pattern, in beats. */
#define TEST_SCREEN_MS 500u
#define BEATS_PER_SECOND 1000u

#if defined(SB_NO_START_SCREENS) && !defined(SB_ENGINE_EXTERNAL)
#error "SB_NO_START_SCREENS is for an engine built on the base (SB_ENGINE_EXTERNAL)"
#endif

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

volatile u32 sb_work, sb_seconds, sb_wake_at;

#if defined(SB_COST_SILENT_ENGINE)
/* The output path's own cost (docs/DESIGN-NOTES.md, M4): an engine that
 * only writes silence. */
static void sb_silent_block(s32 *out, u32 frames)
{
    u32 n;

    for (n = 0; n < 2 * frames; n++)
        out[n] = 0;
}
#endif

#if defined(SB_HW_FM1)
/* The FM-1 hardware build's time base (R-HW-1): TIMER4's clock on the
 * chip isn't in HARDWARE-SPEC (SR-16), so time is TIMER0's slots
 * (hw_fm1.h) and its count, in the same 24 MHz units: 2000 a slot, 2 / 5
 * a count. A slot whose interrupt is pending but not yet taken (the count
 * has wrapped) is added. */
volatile u32 hw_slots;

/* The slots counted, the count and its wrap flag (CON bit 15) taken
 * together: a slot's interrupt between them changes hw_slots, and the
 * three are read again. Until the build after audio5 the flag was read
 * after the loop, so an interrupt there (counting the slot and clearing
 * the flag) could pair a count read after the wrap with the slots before
 * it: one slot back in time, which the flash's busy wait (store.c) read
 * as a 3 s timeout, leaving a log record's last pages unprogrammed. */
#if defined(SB_TEST_NOW_RACE)
/* The test build (case nowrace): the slot interrupt's time-keeping (its
 * acknowledge and its count) made to happen at one chosen point between
 * sb_now()'s reads, the race fwtest's prompt interrupts never hit. */
static volatile u32 race_at;
#define RACE(k) do { if (race_at == (k)) { race_at = 0; JL_TIMER0->CON = HW_SLOT_CON | TICK_ACK; hw_slots++; } } while (0)
#else
#define RACE(k) do { } while (0)
#endif

u32 sb_now(void)
{
    u32 s, c, f;

    do {
        s = hw_slots;
        RACE(1u);
        c = JL_TIMER0->CNT;
        RACE(2u);
        f = JL_TIMER0->CON & 0x8000u;
        RACE(3u);
    } while (s != hw_slots);
    RACE(4u);
    if (f && c < HW_SLOT_PRD / 2)
        s++;
    return s * HW_SLOT_UNITS + c * 2 / 5;
}

#if defined(SB_TEST_NOW_RACE)
/* At each of the four points, NOW_RACE_RUNS times: with interrupts off,
 * wait for TIMER0 to wrap (its flag set, its count small), read sb_now(),
 * then read it again with the slot's time-keeping made to happen at that
 * point; the second must not be earlier. hw_now_test counts the runs and,
 * by point, the readings that went back. */
#define NOW_RACE_RUNS 50u
struct hw_now_test hw_now_test;

static void now_race_test(void)
{
    u32 k, n, before, after;

    for (k = 1; k <= 4u; k++) {
        for (n = 0; n < NOW_RACE_RUNS; n++) {
            __asm__ volatile("cli" ::: "memory");
            while (!(JL_TIMER0->CON & 0x8000u))
                ;
            before = sb_now();
            race_at = k;
            after = sb_now();
            race_at = 0;
            __asm__ volatile("sti" ::: "memory");
            hw_now_test.runs++;
            if ((int)(after - before) < 0)
                hw_now_test.backs[k]++;
            sb_wait_ms(1);
        }
    }
    hw_now_test.done = 1;
}
#endif

u32 sb_ticks(void)
{
    return sb_now() - tb_start;
}
#else
u32 sb_now(void)
{
    return JL_TIMER4->CNT;
}

u32 sb_ticks(void)
{
    return JL_TIMER4->CNT - tb_start;
}
#endif

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
#if defined(SB_HW_FM1)
    u32 now = sb_now() - tb_start;
#else
    u32 now = JL_TIMER4->CNT - tb_start;
#endif
    u32 n = sb_beacon.tick_count, beats;

#if !defined(SB_HW_FM1)
    JL_TIMER0->CON = TICK_CON | TICK_ACK;
#endif
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
    /* The panel's next frame is due (since M5). */
    if (sb_wake_at && (int)(beats - sb_wake_at) >= 0) {
        sb_wake_at = 0;
        sb_work++;
    }

    /* Each stack's lowest word still holds the fill: nothing ran past it. */
    if (__irq_stack_top[0] != SB_STACK_FILL)
        sb_halt(SB_HALT_STACK, 1, 0);
    if (__stack_limit[0] != SB_STACK_FILL)
        sb_halt(SB_HALT_STACK, 2, 0);
}

#if defined(SB_HW_FM1)
/* TIMER0's interrupt in the hardware build: one scan slot, and every
 * twelfth the tick. Acknowledged first, as the tick and the scan are in
 * the other builds. */
void hw_slot(void)
{
    static u32 n;

    JL_TIMER0->CON = HW_SLOT_CON | TICK_ACK;
    hw_slots++;
    /* Not while main sweeps the matrix (hw_start3.c). */
    if (!hw_scan_paused)
        input_scan();
#if defined(SB_HW_AUDIO9)
    hw_a9_pb5_poll();
#endif
#if defined(SB_HW_AUDIO11)
    hw_a11_adc_poll();
#endif
#if defined(SB_HW_AUDIO10)
    hw_a10_pot_poll();
#endif
    if (++n == HW_SLOTS_TICK) {
        n = 0;
        sb_tick();
    }
}

/* The hardware build's panel work in place of the instrument's screens:
 * each button or key pressed or released is named on the test screen
 * (inside its box, rows HW_EVENT_Y to + 15), and its LED follows it, so a
 * unit shows which control each contact is (Q-7). */
#define HW_EVENT_X 26u
#define HW_EVENT_Y 104u
#define HW_EVENT_W 188u
#if defined(SB_HW_AUDIO11)
/* audio11's E: the large area (hw_audio.c) covers the event box's rows. */
#define HW_NO_EVENT_BOX 1
#else
#define HW_NO_EVENT_BOX 0
#endif
static void hw_show(const struct input_event *e)
{
    static const char names[14][5] = {
        "OCT-", "OCT+", "FX", "SEL", "ENV", "LFO", "EDIT",
        "GLO", "HOME", "SAVE", "ARP", "SEQ", "PLAY", "REC",
    };
    char text[24];
    u32 i = 0, c = e->control, k;
    const char *name, *what = e->kind == INPUT_PRESS ? " down" : " up";

    if (hw_hold_screen || HW_NO_EVENT_BOX)
        return;
    text[i++] = (char)('0' + c / 10);
    text[i++] = (char)('0' + c % 10);
    text[i++] = ' ';
    if (c < 14) {
        for (name = names[c], k = 0; k < 5 && name[k]; k++)
            text[i++] = name[k];
    } else {
        k = c - INPUT_KEY1 + 1;
        for (name = "key "; *name; name++)
            text[i++] = *name;
        if (k >= 10)
            text[i++] = (char)('0' + k / 10);
        text[i++] = (char)('0' + k % 10);
    }
    for (; *what; what++)
        text[i++] = *what;
    text[i] = 0;
    gfx_fill(HW_EVENT_X, HW_EVENT_Y, HW_EVENT_W, 16, RGB565(0, 0, 0));
    gfx_text(HW_EVENT_X, HW_EVENT_Y, text, RGB565(31, 63, 31), RGB565(0, 0, 0), 2);
    lcd_send_rect(HW_EVENT_X, HW_EVENT_Y, HW_EVENT_W, 16);
}

/* MASTER, the pot (HW-133 item 5), on the event line as it moves. */
static void hw_show_master(int v)
{
    char text[16] = "MASTER ";
    u32 i = 7, d;

    if (HW_NO_EVENT_BOX)
        return;
    for (d = 1000; d; d /= 10)
        if ((u32)v >= d || d == 1)
            text[i++] = (char)('0' + (u32)v / d % 10);
    text[i] = 0;
    gfx_fill(HW_EVENT_X, HW_EVENT_Y, HW_EVENT_W, 16, RGB565(0, 0, 0));
    gfx_text(HW_EVENT_X, HW_EVENT_Y, text, RGB565(31, 63, 31), RGB565(0, 0, 0), 2);
    lcd_send_rect(HW_EVENT_X, HW_EVENT_Y, HW_EVENT_W, 16);
}

/* An encoder's detent (clean-br17-encoders), on the event line: its name,
 * +1 or -1 as the scan decodes it (HW-38's order: +1 when the B contact,
 * the higher column, closes first), and the column that closed first. */
static void hw_show_turn(u32 control, int d)
{
    static const char names[7][10] = {
        "SELECT", "PRESETS", "ALGORITHM", "KNOB1", "KNOB2", "KNOB3", "KNOB4",
    };
    char text[24];
    const char *n = names[control - INPUT_SELECT];
    u32 i = 0, lead = input_lead(control);

    if (hw_hold_screen || HW_NO_EVENT_BOX)
        return;
    while (*n)
        text[i++] = *n++;
    text[i++] = ' ';
    text[i++] = d > 0 ? '+' : '-';
    text[i++] = '1';
    text[i++] = ' ';
    text[i++] = 'c';
    if (lead > 15) {
        text[i++] = '?';
    } else {
        if (lead >= 10)
            text[i++] = '1';
        text[i++] = (char)('0' + lead % 10);
    }
    text[i] = 0;
    gfx_fill(HW_EVENT_X, HW_EVENT_Y, HW_EVENT_W, 16, RGB565(0, 0, 0));
    gfx_text(HW_EVENT_X, HW_EVENT_Y, text, RGB565(31, 63, 0), RGB565(0, 0, 0), 2);
    lcd_send_rect(HW_EVENT_X, HW_EVENT_Y, HW_EVENT_W, 16);
}

#if defined(SB_HW_AUDIO1)
/* The test screen and start3's rows, drawn again after the audio page. */
static void hw_test_screen(void)
{
    if (hw_hold_screen)
        return;
    lcd_wait();
    screen_test();
    lcd_send_rows(0, SCREEN_H);
    lcd_wait();
    hw_rows_all();
#if defined(SB_HW_AUDIO11)
    hw_a11_big(1);
#endif
}
#endif

/* A key's LED level (leds1): lit while it is held; with the audio probe,
 * a step key's also while its step is taken (hw_audio_key_lit). */
static u32 hw_led_level(const struct input_event *e)
{
    if (e->kind == INPUT_PRESS)
        return INPUT_LED_FULL;
#if defined(SB_HW_AUDIO1)
    return hw_audio_key_lit(e->control) ? INPUT_LED_FULL : 0;
#else
    return 0;
#endif
}

static void hw_serve(void)
{
    struct input_event e;

    while (input_read(&e)) {
        if (e.control == INPUT_MASTER && e.kind == INPUT_MOVE) {
#if defined(SB_HW_AUDIO10)
            hw_a10_master((u32)e.value);
#endif
            if (sb_beacon.screen == SB_SCREEN_TEST && !hw_hold_screen)
                hw_show_master(e.value);
            continue;
        }
        if (e.kind == INPUT_TURN && e.control >= INPUT_SELECT && e.control <= INPUT_KNOB4) {
            if (sb_beacon.screen == SB_SCREEN_TEST)
                hw_show_turn(e.control, e.value);
            continue;
        }
        /* leds1 (the owner's request): every key's LED follows it, before
         * any key's own work, so the keys that are handled below light
         * too. */
        if (e.control < INPUT_LEDS && (e.kind == INPUT_PRESS || e.kind == INPUT_RELEASE))
            input_led(e.control, hw_led_level(&e));
#if defined(SB_HW_AUDIO1)
        /* The next key: a press of it on the test screen moves the guide on. */
        if (e.kind == INPUT_PRESS && sb_beacon.screen == SB_SCREEN_TEST)
            hw_guide_key(e.control);
#endif
#if defined(SB_HW_FINDER)
        /* HOME opens the knob finder, for good (hw_start3.c). */
        if (e.control == INPUT_HOME && e.kind == INPUT_PRESS)
            hw_finder();
#endif
#if defined(SB_HW_REPORT)
        /* report1: EDIT saves a report (hw_report.c); "saved #n" on the
         * step row. */
        if (e.control == INPUT_EDIT && e.kind == INPUT_PRESS && sb_beacon.screen == SB_SCREEN_TEST) {
            hw_report_save("save key");
#if defined(SB_HW_AUDIO1)
            hw_guide_show();
#endif
            continue;
        }
#endif
#if defined(SB_HW_AUDIO12)
        /* audio12b (D5, the owner's ruling): SEL runs the instrument's
         * start; the panel takes over from the test screen. */
        if (e.control == INPUT_SEL && e.kind == INPUT_PRESS && sb_beacon.screen == SB_SCREEN_TEST) {
            hw_audio_leds(e.control);
#if defined(SB_HW_AUDIO13)
            hw_a12_instrument(0);
#else
            hw_a12_instrument();
#endif
            return;
        }
#endif
#if defined(SB_HW_AUDIO13)
        /* audio13 (U2, the owner's rulings): OCT- reads the USB block's
         * words again, SAVE marks the next cable state, OCT+ turns U2-C on
         * or off (hw_audio.c). The engine takes OCT- and OCT+ as well (its
         * octave), and nothing from SAVE alone. */
        if ((e.control == INPUT_OCT_DOWN || e.control == INPUT_OCT_UP || e.control == INPUT_SAVE)
                && e.kind == INPUT_PRESS && sb_beacon.screen == SB_SCREEN_TEST) {
            hw_a13_u2_key(e.control);
            hw_audio_leds(e.control);
            hw_guide_show();
            continue;
        }
#endif
#if defined(SB_HW_U3U)
        /* U3-U's tries (the owner's ruling of 2026-11-23): KEY7 on the
         * test screen takes the port's next spacing, from then on, so one
         * flash tries them all; each record and each host attempt logs the
         * one in use (usb_midi.c). */
        if (e.control == INPUT_KEY(7) && e.kind == INPUT_PRESS && sb_beacon.screen == SB_SCREEN_TEST) {
            usb_midi_gap_key();
            continue;
        }
#endif
#if defined(SB_HW_AUDIO10)
        /* audio10 (the spec side's clean-br17-audio10): LFO cycles F's
         * format; PLAY zeros, HOME the LED blink, ENV the screen, GLO the
         * log, each held and back by the same key; REC holds the scan for
         * 5 s, ending by itself. */
#if defined(SB_HW_AUDIO11)
        /* audio11 (the spec side's clean-br17-audio11): N is the only
         * format, so LFO is the engine's again (main gives it nothing);
         * SEL cycles the SARADC's set-up, the SDK's and the old. */
#define HW_A10_KEY1 INPUT_SEL
#else
#define HW_A10_KEY1 INPUT_LFO
#endif
        if ((e.control == HW_A10_KEY1 || e.control == INPUT_PLAY || e.control == INPUT_HOME || e.control == INPUT_ENV
                || e.control == INPUT_GLO || e.control == INPUT_REC) && e.kind == INPUT_PRESS
                && sb_beacon.screen == SB_SCREEN_TEST) {
            u32 held_screen = hw_hold_screen;

#if defined(SB_HW_AUDIO11)
            if (e.control == INPUT_SEL)
                hw_a11_setup_key();
#else
            if (e.control == INPUT_LFO)
                hw_a10_fmt_key();
#endif
            else
                hw_a10_hold_key(e.control == INPUT_PLAY ? HW_A10_ZERO : e.control == INPUT_HOME ? HW_A10_LED :
                                e.control == INPUT_ENV ? HW_A10_SCREEN : e.control == INPUT_GLO ? HW_A10_LOG :
                                HW_A10_SCAN);
            if (e.control != INPUT_HOME)
                hw_audio_leds(e.control);
            if (held_screen && !hw_hold_screen)
                hw_test_screen();
            if (!(hw_aud.holds >> HW_A10_SCAN & 1u))
                hw_guide_show();
            continue;
        }
#endif
#if defined(SB_HW_AUDIO1)
        /* audio1 (hw_audio.c): PLAY stops and starts the tone; HOME shows
         * the audio page again, then the test screen. */
        if (e.control == INPUT_PLAY && e.kind == INPUT_PRESS)
            hw_audio_toggle();
        /* audio2: REC takes CLK_CON2 bit 9's step, or puts it back; then
         * the page, then the test screen. */
        if (e.control == INPUT_REC && e.kind == INPUT_PRESS && sb_beacon.screen == SB_SCREEN_TEST) {
            hw_audio_step();
            hw_audio_leds(e.control);
            hw_audio_keypage();
            hw_test_screen();
            hw_guide_show();
            continue;
        }
#if defined(SB_HW_AUDIO9)
        /* audio9 (the spec side's clean-br17-audio9): SEQ takes the route
         * down or up, FX switches the tone and the synth, LFO steps S2;
         * HOME shows audio8's and audio9's view. The old steps' keys
         * (ARP, SAVE, ENV, FX, LFO, SEL, GLO, OCT+, OCT-, KEY1 to KEY6) are
         * the engine's alone: main gives them no step. */
#if defined(SB_HW_AUDIO12)
        /* audio12 (S): LFO starts the sweep, or stops it after the chord
         * in progress (the engine does nothing with LFO). */
        if (e.control == INPUT_LFO && e.kind == INPUT_PRESS && sb_beacon.screen == SB_SCREEN_TEST) {
            hw_a12_sweep_key();
            hw_audio_leds(e.control);
            hw_guide_show();
            continue;
        }
#endif
#if defined(SB_HW_AUDIO11)
#define HW_A9_LFO 0xFFu      /* LFO is the engine's (audio11) */
#else
#define HW_A9_LFO INPUT_LFO
#endif
        if ((e.control == INPUT_SEQ || e.control == INPUT_FX || e.control == HW_A9_LFO || e.control == INPUT_HOME)
                && e.kind == INPUT_PRESS && sb_beacon.screen == SB_SCREEN_TEST) {
            if (e.control == INPUT_SEQ)
                hw_a9_route_key();
            else if (e.control == INPUT_FX)
                hw_a9_synth_key();
            else if (e.control == INPUT_LFO)
                hw_a9_s2_key();
            hw_audio_leds(e.control);
            if (e.control == INPUT_SEQ || e.control == INPUT_HOME) {
                hw_audio_keypage_a8();
                hw_test_screen();
            }
            hw_guide_show();
            continue;
        }
#else
        /* audio3 (the spec side's clean-br17-audio3): ARP takes step A
         * (CON0 bit 11 cleared and set again, with bit 9 set), SAVE step B
         * (CLK_CON2 bit 8, with bit 9 set); a second press undoes each. */
        if ((e.control == INPUT_ARP || e.control == INPUT_SAVE) && e.kind == INPUT_PRESS
                && sb_beacon.screen == SB_SCREEN_TEST) {
            if (e.control == INPUT_ARP)
                hw_audio_a();
            else
                hw_audio_b();
            hw_audio_leds(e.control);
            hw_audio_keypage();
            hw_test_screen();
            hw_guide_show();
            continue;
        }
        /* audio4 (the spec side's clean-br17-audio4): ENV takes step H
         * (the audio clock measured), FX measures again; LFO takes step I
         * (ALNK1 with CLK_CON2 bit 11), SEL adds bit 10; a second ENV or
         * LFO undoes. */
        if ((e.control == INPUT_ENV || e.control == INPUT_FX || e.control == INPUT_LFO || e.control == INPUT_SEL)
                && e.kind == INPUT_PRESS && sb_beacon.screen == SB_SCREEN_TEST) {
            if (e.control == INPUT_ENV)
                hw_audio_h();
            else if (e.control == INPUT_FX)
                hw_audio_h_again();
            else if (e.control == INPUT_LFO)
                hw_audio_i();
            else
                hw_audio_i10();
            hw_audio_leds(e.control);
            hw_audio_keypage_hi();
            hw_test_screen();
            hw_guide_show();
            continue;
        }
        /* audio5 (the spec side's clean-br17-audio5): GLO takes step K
         * (every measurement of input 5 from one press), OCT+ runs J's
         * sweep of ALNK0's CON1 and CON3 (a press while it runs aborts
         * it; a press with a bit left set puts it back); a second GLO
         * undoes K. */
        if ((e.control == INPUT_GLO || e.control == INPUT_OCT_UP) && e.kind == INPUT_PRESS
                && sb_beacon.screen == SB_SCREEN_TEST) {
            if (e.control == INPUT_GLO)
                hw_audio_k();
            else
                hw_audio_j();
            hw_audio_leds(e.control);
            hw_audio_keypage_kj();
            hw_test_screen();
            hw_guide_show();
            continue;
        }
        /* audio6 (the spec side's clean-br17-audio6): OCT- runs step D's
         * sweep of JL_IOMAP->CON5 (a press while it runs stops it; a press
         * with a bit kept puts CON5 back). */
        if (e.control == INPUT_OCT_DOWN && e.kind == INPUT_PRESS && sb_beacon.screen == SB_SCREEN_TEST) {
            hw_audio_d();
            hw_audio_leds(e.control);
            hw_audio_keypage_d();
            hw_test_screen();
            hw_guide_show();
            continue;
        }
        /* audio7 (the spec side's clean-br17-audio7): KEY1 takes set-up L1,
         * KEY2 set-up L2; a kept set-up is put back by either. */
        if ((e.control == INPUT_KEY(1) || e.control == INPUT_KEY(2)) && e.kind == INPUT_PRESS
                && sb_beacon.screen == SB_SCREEN_TEST) {
            hw_audio_l(e.control == INPUT_KEY(1) ? 1u : 2u);
            hw_audio_leds(e.control);
            hw_audio_keypage_l();
            hw_test_screen();
            hw_guide_show();
            continue;
        }
#if defined(SB_HW_AUDIO8)
        /* audio8 (the spec side's clean-br17-audio8): KEY3 R2 (port C's
         * four pins), KEY4 step 1, KEY5 the CON5 sweep, KEY6 the sense
         * scan; a second KEY3, KEY4 or KEY5 undoes its own. */
        if (e.control >= INPUT_KEY(3) && e.control <= INPUT_KEY(6) && e.kind == INPUT_PRESS
                && sb_beacon.screen == SB_SCREEN_TEST) {
            if (e.control == INPUT_KEY(3))
                hw_a8_r2();
            else if (e.control == INPUT_KEY(4))
                hw_a8_step1();
            else if (e.control == INPUT_KEY(5))
                hw_a8_sweep();
            else
                hw_a8_sense();
            hw_audio_leds(e.control);
            hw_audio_keypage_a8();
            hw_test_screen();
            hw_guide_show();
            continue;
        }
#endif
#endif
        /* audio3: SEQ stops ALNK0 (CON0 bit 11 cleared alone), or puts
         * back the CON0 read before; then the page, then the test screen. */
        if (e.control == INPUT_SEQ && e.kind == INPUT_PRESS && sb_beacon.screen == SB_SCREEN_TEST) {
            hw_audio_alnk();
            hw_audio_leds(e.control);
            hw_audio_keypage();
            hw_test_screen();
            hw_guide_show();
            continue;
        }
        if (e.control == INPUT_HOME && e.kind == INPUT_PRESS && sb_beacon.screen == SB_SCREEN_TEST) {
            hw_audio_page();
            hw_test_screen();
            hw_guide_show();
            continue;
        }
#endif
        if (e.control >= INPUT_LEDS || (e.kind != INPUT_PRESS && e.kind != INPUT_RELEASE))
            continue;
        input_led(e.control, hw_led_level(&e));
        if (sb_beacon.screen == SB_SCREEN_TEST)
            hw_show(&e);
    }
    /* start3's rows (hw_start3.c): about ten times a second, and core 1's
     * counter once a second; main is woken for them through sb_wake_at. */
    if (sb_beacon.screen == SB_SCREEN_TEST) {
        static u32 next = 0, seconds = 0;
        u32 now = sb_beacon.beats;

        if ((int)(now - next) >= 0) {
#if defined(SB_HW_AUDIO1)
            hw_guide_tick();
#endif
#if defined(SB_HW_AUDIO9)
            hw_a9_tick();
#endif
#if defined(SB_HW_AUDIO13)
            /* U2-B: the USB block's words every 100 ms (hw_audio.c). */
            hw_a13_u2_poll();
#endif
            hw_refresh(sb_seconds != seconds);
            seconds = sb_seconds;
            next = now + 100;
        }
        sb_wake_at = next;
    }
}
#endif

#if defined(SB_HW_AUDIO12)
/* The panel's work once the instrument's start has put it up; audio13's
 * ARP line after it (hw_audio.c). */
static void hw_panel_serve(void)
{
    view_serve();
#if defined(SB_HW_AUDIO13)
    hw_a13_panel_tick();
#endif
}
#endif

/* The store's work (M7), from main's loop: what the panel saved or
 * reset, and the selection and settings once they settle. */
#if defined(SB_ENGINE_EXTERNAL)
/* C++ static objects' constructors (since clean-1027, BR-4: the
 * platform's runtime), from firmware/platform.ld's table, last first. */
static void run_constructors(void)
{
    extern void (*__ctors_start[])(void), (*__ctors_end[])(void);
    void (**f)(void) = __ctors_end;

    while (f != __ctors_start)
        (*--f)();
}
#endif

#if !defined(SB_ENGINE_EXTERNAL) && !defined(SB_HW_FM1)
static void serve_store(void)
{
    const char *said = store_serve();

    if (said)
        view_message(said, store_message_slot);
}
#endif

int main(void)
{
    static const char hello[16] = "small-beeps M5 \n";

    sb_beacon.period = TICKS_PER_MS;
#if defined(SB_HW_AUDIO1)
    /* audio1: the audio registers as m-bootloader's call left them, before
     * anything of main's (hw_audio.c). */
    hw_audio_boot();
#endif
#if defined(SB_HW_FM1)
    /* Running from RAM, after the copy (R-HW-1). */
    hw_band(2);
#endif
    if (data_probe == 0x5EED0001u && bss_probe == 0) {
        sb_beacon.marker = SB_MARKER;
#if defined(SB_HW_FM1)
        (void)hello;
#else
        sb_console_write(hello, sizeof hello / 4);
#endif
    } else {
        sb_beacon.marker = SB_MARKER_BAD;
    }

    /* Only differences of CNT are used: its value when started, and its
     * response to writes, don't matter. */
#if defined(SB_HW_FM1)
    /* No TIMER4 (its clock on the chip is SR-16's), and no measure of the
     * core clock against it: HW-119 gives 360 MHz. */
    tb_start = 0;
#else
    JL_TIMER4->CON = TIMER4_RUN;
    tb_start = JL_TIMER4->CNT;
    /* No clock register is written (HW-11, SR-2): the clock is measured. */
    sb_beacon.clock = sb_clock_measure((volatile u32 *)&JL_TIMER4->CNT);
#endif
#if defined(SB_PROBE_BIG)
    sb_probe_big();
#endif
#if defined(SB_PROBE_STACK)
    sb_probe_stack();
#endif
#if defined(SB_TEST_LATE_START)
    /* The timing goldens' policy (tools/goldtime.py): a start about
     * 0.1 ms late, inside the 0.2 ms its run ends keep, as a bigger
     * image's would be, so every block and event of ours moves later
     * against the script; tools/regolden.py must prove each golden this
     * moves a pure time shift. */
    {
        volatile u32 n;
        for (n = 0; n < 5000u; n++)
            ;
    }
#endif

#if defined(SB_HW_FM1)
    /* start3 (c) step 1: the flash's read-only round trip, from RAM with
     * interrupts off, before the vector table is written (hw_start3.c). */
    hw_round_trip();
    /* start3b: the rows and the round trip's LED marks held on the unit
     * (SB_HW_HOLD), before the scan takes the LEDs. */
    hw_hold();
    hw_step("interrupts: setting up");
#endif
    sb_irq_init();
#if defined(SB_HW_FM1)
    sb_irq_enable(SRC_TIMER0, hw_slot, PRIO_TICK);
#if !defined(SB_TEST_SPI_NO_IRQ)
    /* The test build leaves SPI1's interrupt off, so lcd_wait's timeout
     * is seen to report it (seams case hw). */
    sb_irq_enable(SRC_SPI1, lcd_spi_done, PRIO_SPI1);
#endif
    /* PB1 and PB6 analogue first: input_start takes the pot's first
     * reading (MASTER, channel 4, HW-133). */
    hw_adc_start();
    input_start();
    JL_TIMER0->CNT = 0;
    JL_TIMER0->PRD = HW_SLOT_PRD;
    JL_TIMER0->CON = HW_SLOT_CON;
    hw_step("interrupts: on, waiting 2 beats");
    sb_irq_on();
    /* Interrupts and TIMER0 work: the tick has counted two beats. A spin,
     * not idle, so idle is tested apart (below). */
    while (sb_beacon.beats < 2)
        ;
#if defined(SB_TEST_NOW_RACE)
    now_race_test();
#endif
    hw_band(3);
    /* start3 (c) step 2: the store's start-up counter, if step 1 came
     * back (hw_start3.c). */
    hw_store_counter();
#if defined(SB_HW_HOLD)
    /* start3b: is the tick still running after the store's step? */
    hw_step("tick after the store");
    hw_watch(HW_WATCH_MS);
#endif
    /* start3 (d): core 1 counting, after the vector table (HW-9). No
     * engine, audio or MIDI on a unit yet (HW-130). Since start3b after
     * the store's step, so a hang tells them apart. */
    hw_core1_start();
#if defined(SB_HW_AUDIO1)
    /* audio3: core 1's count just after its release (hw_audio.c). */
    hw_c1_mark(HW_C1_REL);
#endif
#if defined(SB_HW_HOLD)
    hw_step("tick after core 1");
    hw_watch(HW_WATCH_MS);
#endif
#else
    sb_irq_enable(SRC_TIMER0, sb_tick, PRIO_TICK);
    sb_irq_enable(SRC_SPI1, lcd_spi_done, PRIO_SPI1);
    JL_TIMER0->CNT = 0;
    JL_TIMER0->PRD = TICK_PRD;
    JL_TIMER0->CON = TICK_CON;
    input_start();
#endif
#if defined(SB_HW_FM1)
#elif defined(SB_ENGINE_EXTERNAL)
    /* An engine of a firmware built on the base (engine.h; the Plaits
     * demo is one): its static objects' constructors, then its own
     * start-up, in place of the instrument's. */
    run_constructors();
    sb_engine_init();
#else
    /* The FM engine (M5); it starts core 1. */
    fm_init();
    /* The store (M7): user slots, settings and selection, before the
     * audio starts. */
    store_boot();
#endif
#if defined(SB_HW_FM1)
#elif defined(SB_ENGINE_EXTERNAL)
    audio_start(sb_engine_block);
#elif defined(SB_COST_NO_AUDIO)
    (void)fm_block;
#elif defined(SB_COST_SILENT_ENGINE)
    audio_start(sb_silent_block);
#elif defined(SB_TEST_UNDERRUN)
    audio_start(sb_test_late_block);
#else
    audio_start(fm_block);
#endif
#if defined(SB_TEST_LEDS)
    sb_test_leds();
#endif
#if !defined(SB_HW_FM1)
    sb_irq_on();
#endif

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
     * the display is still off, then display on (DESIGN-NOTES.md, M2). The
     * hardware build brought the panel up already (hw_early). */
#if !defined(SB_HW_FM1)
    lcd_init();
#endif
#if defined(SB_NO_START_SCREENS)
    /* Since BR-16 an engine may start without the bring-up screens: a
     * black frame in place of the pattern (the engine's init may have
     * drawn into the frame buffer), no wait and no test screen, so its
     * first serve comes as soon as the display is on. */
    gfx_fill(0, 0, SCREEN_W, SCREEN_H, 0);
    lcd_send_rows(0, SCREEN_H);
    lcd_command(LCD_DISPON, 0, 0);
    sb_beacon.screen = SB_SCREEN_BLANK;
#else
#if defined(SB_HW_FM1)
    hw_step("pattern: sending");
#endif
    screen_pattern();
    lcd_send_rows(0, SCREEN_H);
#if defined(SB_HW_FM1)
    /* Band 4 (yellow), over the pattern: its DMA chain ended by SPI1's
     * interrupts (R-HW-1); then start3b's rows again over it. */
    lcd_wait();
    hw_band(4);
    hw_rows_start();
    hw_step("pattern: sent, display on");
#endif
    lcd_command(LCD_DISPON, 0, 0);
    sb_beacon.screen = SB_SCREEN_PATTERN;

#if defined(SB_HW_FM1)
    /* start3b: a watched spin in place of idle, the tick's row drawn as it
     * goes; then idle alone, briefly. */
    hw_step("waiting for the test screen (spin)");
    if (sb_beacon.beats + 1 < TEST_SCREEN_MS)
        hw_watch(TEST_SCREEN_MS - 1 - sb_beacon.beats);
    hw_step("idle: 20 beats");
    sb_wait_ms(20);
    /* start3c: core 1's screen, held (SB_HW_HOLD). */
    hw_core1_screen();
#if defined(SB_HW_AUDIO13)
    /* audio13 (D5, the owner's ruling): the instrument's start from cold,
     * then the panel, unless HOME is held now: then the test screen, as
     * audio12b's (U2-A's second reading first, hw_audio.c). */
    if (hw_a13_power_on())
        goto serve;
#elif defined(SB_HW_AUDIO12)
    /* audio12b (the owner's ruling): the test screen, as audio11's; SEL
     * there runs the instrument's start (hw_audio.c). */
    hw_aud.start_mode = HW_A12_TEST;
#endif
    hw_step("test screen: drawing");
#else
    if (sb_beacon.beats + 1 < TEST_SCREEN_MS)
        sb_wait_ms(TEST_SCREEN_MS - 1 - sb_beacon.beats);
#endif
    {
        u32 t = sb_now();
        screen_test();
        sb_beacon.render_ticks = sb_now() - t;
    }
    lcd_send_rows(0, SCREEN_H);
    sb_beacon.screen = SB_SCREEN_TEST;
#if defined(SB_HW_FM1)
    /* start3's rows on the test screen (hw_start3.c). */
    lcd_wait();
    hw_rows_all();
#if defined(SB_HW_REPORT)
    /* report1: the end of boot, the test screen up (hw_report.c). */
    hw_report_save("boot");
#endif
#if defined(SB_HW_AUDIO1)
    /* audio1: the tone, once the test screen is up; its page, then the
     * test screen again (hw_audio.c). */
#if defined(SB_HW_AUDIO9)
    /* audio9 (S1): the FM engine, core 0 alone and MIDI off on a unit
     * (fm_play.c, midi.c); it fills nothing until FX turns the synth on. */
    hw_step("audio9: the engine's start");
    fm_init();
#endif
    hw_step("audio: starting ALNK0");
    hw_audio_start();
#if defined(SB_HW_AUDIO9)
    /* audio9 (S0): L2, R2 and the route, once the test screen is up. */
    hw_audio9_boot();
#elif defined(SB_HW_AUDIO8)
    /* audio8 (R0): L2, the running state, once the test screen is up. */
    hw_audio_boot_l2();
#endif
    hw_step("audio: page");
    hw_audio_page();
    hw_test_screen();
    hw_guide_show();
#endif
#endif
#endif
#if defined(SB_HW_AUDIO13)
serve:
#endif
#if defined(SB_TEST_STORE_WIPE)
    sb_test_store_wipe();
#endif
#if defined(SB_TEST_FLOOD)
    sb_test_flood();
#endif

    /* Between interrupts the core waits. Since M3 the input scan wakes it
     * twelve times a tick as well (and since M4 the audio output once a
     * block), so each wake only looks whether the
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
#if defined(SB_USB_MIDI)
        /* U3-U (usb_midi.h): the cable reading at the app's start, then
         * from each wake with work (about once a second at least). */
        usb_midi_poll();
#endif
        /* What the engine asked of the store before the loop began, and
         * (since M8a) the panel's events from before it: the screens. */
#if defined(SB_HW_AUDIO12)
        if (hw_aud.start_mode == HW_A12_INSTRUMENT)
            hw_panel_serve();
        else
#endif
#if defined(SB_HW_FM1)
        hw_serve();
#elif defined(SB_ENGINE_EXTERNAL)
        sb_engine_serve();
#else
        serve_store();
        view_serve();
#endif
        for (;;) {
            __asm__ volatile("idle");
            wakes++;
            if (sb_work != seen) {
                seen = sb_work;
                sb_beacon.wakes = wakes;
                sb_beacon.wakes_ticks = sb_beacon.tick_count;
#if defined(SB_USB_MIDI)
                usb_midi_poll();
#endif
#if defined(SB_HW_AUDIO12)
                /* Once SEL's start has put the panel up, the panel
                 * serves the events (the test screen's keys do nothing);
                 * no store (its flash writes aren't part of audio12). */
                if (hw_aud.start_mode == HW_A12_INSTRUMENT)
                    hw_panel_serve();
                else
#endif
#if defined(SB_HW_FM1)
                hw_serve();
#elif defined(SB_ENGINE_EXTERNAL)
                sb_engine_serve();
#else
                view_serve();
                serve_store();
#endif
                /* The heartbeat is the test screen's own (since M8a the
                 * instrument's screens have no place for it). */
                while (second != sb_seconds) {
                    second++;
                    if (sb_beacon.screen == SB_SCREEN_TEST)
                        screen_beat();
                }
            }
        }
    }
}
