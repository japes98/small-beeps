/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * The input layer: every control on the panel, and its LEDs (M3). This is
 * the API the rest of the firmware, and engines built on it, use; keep it
 * small and stable (docs/DESIGN-NOTES.md, M3, "The input API").
 *
 * - One event queue, read with input_read(). Each event names a control,
 *   what happened to it, a value and the time it was decided.
 * - Control IDs are named after the panel's printed labels (HW-36). Their
 *   numbers never change; a board wired differently from fwtest (Q-7)
 *   changes only input.c's tables.
 * - input_value() gives a control's present state at any time.
 * - input_led() sets the LED of a button or key, with a brightness.
 */

#ifndef INPUT_H
#define INPUT_H

#include "sb.h"

/* Control IDs. Buttons, then the 27 keys from left to right, then the
 * knobs. The 14 buttons and 27 keys each have an LED. */
#define INPUT_OCT_DOWN   0u   /* OCT- */
#define INPUT_OCT_UP     1u   /* OCT+ */
#define INPUT_FX         2u
#define INPUT_SEL        3u
#define INPUT_ENV        4u
#define INPUT_LFO        5u
#define INPUT_EDIT       6u
#define INPUT_GLO        7u   /* the button; the raised key is INPUT_KEY_GLO */
#define INPUT_HOME       8u
#define INPUT_SAVE       9u
#define INPUT_ARP        10u
#define INPUT_SEQ        11u
#define INPUT_PLAY       12u  /* PLAY/STOP, one button */
#define INPUT_REC        13u
/* Keys: KEY1 is the leftmost, KEY27 the rightmost. The 16 lower keys have
 * no printed label; the raised keys are KEY2, 4, 6, 9, 11, 14, 16, 18, 21,
 * 23 and 26, and the first ten carry second labels (below). */
#define INPUT_KEY1       14u
#define INPUT_KEY(n)     (INPUT_KEY1 + (n) - 1u)   /* n = 1 to 27 */
#define INPUT_KEY27      40u
#define INPUT_KEY_OP1    INPUT_KEY(2)
#define INPUT_KEY_OP2    INPUT_KEY(4)
#define INPUT_KEY_OP3    INPUT_KEY(6)
#define INPUT_KEY_OP4    INPUT_KEY(9)
#define INPUT_KEY_OP5    INPUT_KEY(11)
#define INPUT_KEY_OP6    INPUT_KEY(14)
#define INPUT_KEY_PIT    INPUT_KEY(16)
#define INPUT_KEY_GLO    INPUT_KEY(18)
#define INPUT_KEY_MONO   INPUT_KEY(21)
#define INPUT_KEY_POLY   INPUT_KEY(23)
/* Knobs: MASTER is a pot, the other seven are encoders with detents. */
#define INPUT_MASTER     41u
#define INPUT_SELECT     42u
#define INPUT_PRESETS    43u
#define INPUT_ALGORITHM  44u
#define INPUT_KNOB1      45u
#define INPUT_KNOB2      46u
#define INPUT_KNOB3      47u
#define INPUT_KNOB4      48u
#define INPUT_CONTROLS   49u
#define INPUT_LEDS       41u  /* controls 0 to 40 have an LED */

/* What happened (input_event.kind), and its value. */
#define INPUT_PRESS      1u   /* a button or key went down; value 1 */
#define INPUT_RELEASE    2u   /* it came up; value 0 */
#define INPUT_TURN       3u   /* an encoder moved one detent: +1 clockwise, -1 not */
#define INPUT_MOVE       4u   /* the pot moved: value is its new position, 0 to 1023 */

/* An event: 8 bytes. time is in time base ticks (24 per microsecond,
 * sb_ticks()) since the firmware started its time base, when the input
 * layer decided the event: after debouncing for a key, at the detent's
 * last contact change seen for an encoder. It wraps every 178.9 s, so
 * compare times by unsigned difference. */
struct input_event {
    u8 control;
    u8 kind;
    s16 value;
    u32 time;
};
_Static_assert(sizeof(struct input_event) == 8, "an event is 8 bytes");

/* The queue holds INPUT_QUEUE events. When it is full, new events are
 * dropped (the oldest are kept) and counted (sb_input.dropped). */
#define INPUT_QUEUE      64u

/* Takes the oldest event into *e: 1, or 0 if there is none. Main context
 * only (one reader). */
int input_read(struct input_event *e);

/* A control's present state: 1 while a button or key is held, else 0; an
 * encoder's position (detents since start, clockwise positive); the pot's
 * position, 0 to 1023, as last reported. */
int input_value(u32 control);

/* Sets the LED of control (0 to 40) to level, 0 (off) to 255 (fully on).
 * The scan shows it from the next time it selects that LED's column, at
 * most one scan (1 ms) later. Brightness has 9 steps: level 255 * n / 8
 * for n = 0 to 8, rounded to the nearest. Main context only. */
#define INPUT_LED_FULL   255u
void input_led(u32 control, u32 level);

/* The input record: counters and the last INPUT_LOG events, at a fixed
 * place in RAM right after the beacon (firmware/app.ld), for the tests to
 * capture with fwtest's --ram (tools/fw-suite.py reads this layout). */
#define INPUT_LOG        128u
struct sb_input_record {
    u32 cycles;       /* whole scans of the panel (one a millisecond) */
    u32 events;       /* events made; the last is log[(events - 1) % INPUT_LOG] */
    u32 dropped;      /* events dropped because the queue was full */
    u32 taken;        /* events input_read() handed out */
    u32 led_calls;    /* input_led() calls */
    u32 led_time;     /* sb_ticks() at the last input_led() call */
    u32 led_control;  /* and its control and level, control << 8 | level */
    u32 led_lag_max;  /* the longest from an event's time to an input_led()
                       * call after input_read() handed it out, in ticks */
    u32 pot_raw;      /* the pot's last raw reading */
    u32 led_show_max; /* test build SB_TEST_LED_SHOW only (else 0): the
                       * longest from an input_led() call to the scan first
                       * driving that LED's column, in ticks */
    int values[INPUT_CONTROLS + 1];   /* input_value(), padded to 8 bytes */
    struct input_event log[INPUT_LOG];
};
extern volatile struct sb_input_record sb_input;

/* Starts scanning; main calls it once, before interrupts are on. */
void input_start(void);
void input_scan(void) __attribute__((interrupt("")));

#endif
