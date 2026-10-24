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
typedef unsigned short u16;
typedef unsigned int u32;
typedef signed char s8;
typedef short s16;
typedef int s32;
typedef long long s64;
typedef unsigned long long u64;

_Static_assert(sizeof(u16) == 2, "u16 is 16 bits");
_Static_assert(sizeof(u32) == 4, "u32 is 32 bits");
_Static_assert(sizeof(s16) == 2, "s16 is 16 bits");
_Static_assert(sizeof(s32) == 4, "s32 is 32 bits");
_Static_assert(sizeof(s64) == 8, "s64 is 64 bits");
_Static_assert(sizeof(u64) == 8, "u64 is 64 bits");

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
    u32 wakes;          /* times main's idle wait returned (since M2 stored
                         * once a second, with wakes_ticks) */
    u32 clock;          /* sb_clock_measure: time base ticks per SB_CLOCK_CYCLES */
    u32 halt_reason;    /* SB_HALT_*, 0 while running */
    u32 halt_source;    /* the interrupt source, or which stack's guard */
    u32 halt_reti;      /* where the interrupt came in (reti), if any */
    /* Since M2: the screen (docs/DESIGN-NOTES.md, M2). Times are in time
     * base ticks (24 per microsecond). */
    u32 screen;         /* SB_SCREEN_*: what the panel shows */
    u32 loop_ticks;     /* tick_count when main's idle loop began */
    u32 frames;         /* whole frames sent to the panel */
    u32 frame_ticks;    /* the last whole frame: window set to last byte sent */
    u32 render_ticks;   /* drawing the test screen into the frame buffer */
    u32 beat_ticks;     /* the last heartbeat update: drawn and its rows sent */
    u32 shown;          /* the heartbeat's seconds on the screen */
    u32 chunks;         /* DMA transfers to the panel */
    u32 wakes_ticks;    /* tick_count when main last stored wakes */
};

/* What the screen shows (sb_beacon.screen), in order. */
#define SB_SCREEN_NONE    0u
#define SB_SCREEN_PATTERN 1u  /* the address pattern (screen.c) */
#define SB_SCREEN_TEST    2u  /* the test screen with the heartbeat */
#define SB_SCREEN_PANEL   3u  /* the live panel screen (panel.c, M3) */

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

void sb_wait_ms(u32 ms);

/* irq.c */
void sb_irq_init(void);
void sb_irq_enable(u32 source, void (*handler)(void), u32 priority);
void sb_irq_on(void);
void sb_halt(u32 reason, u32 source, u32 reti) __attribute__((noreturn));

/* The time base's count (HW-13), for timing. */
u32 sb_now(void);
/* Time base ticks since main started the time base (the beacon's ticks;
 * input events' times). */
u32 sb_ticks(void);

/* Work for main's idle loop (since M3): any change of sb_work means look
 * again. The tick adds one at each whole second of the heartbeat (and
 * adds one to sb_seconds), the input scan one with each event it queues
 * (docs/DESIGN-NOTES.md, M3). */
extern volatile u32 sb_work, sb_seconds;
/* Since M5: a heartbeat (beats) at which the tick adds one to sb_work and
 * clears this, for the panel's next frame (panel.c); 0 for none. */
extern volatile u32 sb_wake_at;

/* lcd.c: the panel (HW-27 to HW-32). Rows are whole rows of the frame
 * buffer, sent from it as they are. */
void lcd_init(void);
void lcd_command(u8 command, const u8 *params, u32 count);
void lcd_send_rows(u32 first, u32 rows);
void lcd_wait(void);
void lcd_spi_done(void) __attribute__((interrupt("")));
#define LCD_DISPON 0x29u

/* gfx.c: drawing into the frame buffer. Colours are RGB565 (HW-27). */
#define SCREEN_W 240u
#define SCREEN_H 240u
#define RGB565(r5, g6, b5) ((u32)(r5) << 11 | (u32)(g6) << 5 | (u32)(b5))
extern u16 sb_fb[SCREEN_W * SCREEN_H];
void gfx_fill(u32 x, u32 y, u32 w, u32 h, u32 colour);
void gfx_frame(u32 x, u32 y, u32 w, u32 h, u32 colour);
void gfx_line(int x0, int y0, int x1, int y1, u32 colour);
void gfx_pixel(u32 x, u32 y, u32 colour);
u32 gfx_text(u32 x, u32 y, const char *text, u32 fg, u32 bg, u32 scale);
void gfx_glyph(u32 x, u32 y, u32 c, u32 fg, u32 bg, u32 scale);

/* font.c: our own font, 5 x 8 in a 6 x 8 cell, printable ASCII. */
#define FONT_W 5u
#define FONT_H 8u
#define FONT_CELL 6u
#define FONT_FIRST 32u
#define FONT_LAST 126u
extern const u8 font_glyphs[FONT_LAST - FONT_FIRST + 1][FONT_H];

/* screen.c */
void screen_pattern(void);
void screen_test(void);
void screen_beat(void);
void screen_beat_all(void);

/* panel.c: the live panel screen (M3): takes every queued input event,
 * lights the LEDs to match and, from the first one on, shows the panel. */
void panel_serve(void);

/* crt0.S */
u32 sb_clock_measure(volatile u32 *count);
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
#if defined(SB_PROBE_LOADED)
void sb_probe_loaded(void);
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
#if defined(SB_TEST_FLOOD)
void sb_test_flood(void) __attribute__((noreturn));
#endif
#if defined(SB_TEST_LEDS)
void sb_test_leds(void);
#endif
#if defined(SB_TEST_UNDERRUN)
void sb_test_late_block(s32 *out, u32 frames);
#endif

#endif
