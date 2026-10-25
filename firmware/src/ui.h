/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * The instrument's interface (M8a; docs/DESIGN-NOTES.md, M8a, and
 * docs/M8-PROPOSAL.md): one screen at a time, HOME back to the patch
 * view, the bottom strip naming what KNOB1 to KNOB4 do on every screen.
 *
 * - The engine owns the interface's state (struct fm_ui): it reads the
 *   panel's events in order in its block callback, so a screen button
 *   and a knob turned just after it are taken in that order, and what a
 *   knob does always matches the screen it was turned on. It adds one to
 *   fm_ui.seq on every change and wakes main.
 * - Main only draws (views.c): it reads the state when seq holds still,
 *   works out what each part of the screen should show, and redraws and
 *   sends only the parts that changed, in frames, within the drawing
 *   budget (panel.c's since M5). It also sets the LEDs (input_led is main
 *   context only): a held button or key fully lit, the screen's own
 *   button lit, the selected operator's key at half brightness.
 */

#ifndef UI_H
#define UI_H

#include "sb.h"

/* The screens, in fm_ui.screen. */
#define UI_PATCH     0u   /* HOME: the patch view */
#define UI_EDIT      1u   /* EDIT: operators and the algorithm */
#define UI_ENV       2u   /* ENV: an envelope */
#define UI_SETTINGS  3u   /* GLO: the settings */
#define UI_SCREENS   4u

/* The interface's state, written by the engine only (fm_play.c). */
struct fm_ui {
    u32 seq;      /* one more on every change */
    u8 screen;    /* UI_* */
    u8 op;        /* the selected operator, 0 to 5 */
    u8 page;      /* the screen's page (SELECT steps through them) */
    u8 row;       /* the settings' row */
    u8 env;       /* ENV: 0 the operator's envelope, 1 the pitch envelope, 2 glide */
    u8 confirm;   /* settings: 1 while the factory reset waits for SAVE */
    u8 knobs;     /* 0: KNOB1 to KNOB4 are the macros; 1: direct (midi_settings.knobs) */
    u8 reserved;
};
extern volatile struct fm_ui fm_ui;

/* What views.c needs of the engine (fm_play.c). */
const u8 *fm_program_bytes(void);   /* the program playing now, as patch bytes */
u32 fm_user_used(void);             /* user slots holding a patch, bit n for slot n */
/* Each operator's loudest gain now, 2^-30, written each block while the
 * operator view shows (since M8a part 3), 0 when nothing sounds. */
extern volatile s32 fm_op_level[6];
/* The envelope view's dot (since M8a part 4), written each block while
 * ENV shows, for the newest note sounding: valid 0 (none), 1 (an
 * operator's envelope: stage ENV_*, att its linear gain 2^-30 in the
 * attack, else its attenuation in 2^-16 octaves) or 2 (the pitch
 * envelope: stage 0 to 2, att its level in 2^-16 of a level). */
struct fm_env_dot {
    u32 valid, stage;
    s32 att;
};
extern volatile struct fm_env_dot fm_env_dot;

/* The live spectrum (since M8a part 5; spectrum.c). Before each
 * transform main sets spec_capture to SPEC_BLOCKS; the engine copies that
 * many blocks' output (out 0: silence, at rest), one each block. */
#define SPEC_N      256u     /* samples a transform */
#define SPEC_BLOCKS 4u       /* blocks a capture: SPEC_N / AUDIO_FRAMES */
#define SPEC_BARS   56u      /* bars, 200 Hz to 20 kHz */
extern volatile u32 spec_capture;
void spectrum_feed(const s32 *out, u32 frames);
/* Main, in three steps (each a part of the drawing): the ring now,
 * windowed (0 if silent); stages first to last - 1 of eight; the bars'
 * heights, 0 to height. */
u32 spectrum_start(void);
void spectrum_stages(u32 first, u32 last);
void spectrum_bars(u8 *bars, u32 height);
/* 1 if the last capture held only silence. */
u32 spectrum_quiet(void);

/* views.c, from main's loop: take the panel's events (LEDs, the event
 * line) and the engine's state, and draw what changed. view_message puts
 * a message on the event line, with a number after it unless it is 0. */
void view_serve(void);
void view_message(const char *text, u32 number);

/* The interface's record, after the store's at 0x01C00870 (firmware/app.ld), for the
 * tests (tools/fw-suite.py reads this layout). Times in time base ticks. */
#define UI_MARKER 0x38495553u   /* "SUI8" in memory order */
struct sb_ui_record {
    u32 marker;
    u32 screen;        /* the screen drawn last */
    u32 seq;           /* fm_ui.seq as drawn last */
    u32 shows;         /* whole screens drawn (the first, and each change of screen) */
    u32 frames;        /* frames begun */
    u32 items;         /* parts of the screen drawn and sent */
    u32 rows_sent;     /* rows sent to the panel */
    u32 item_max;      /* the longest single part, drawn and sent */
    u32 block_max;     /* the most drawing time spent in one audio block */
    u32 over;          /* blocks whose drawing went past the budget (by its last part) */
    u32 leds;          /* LED changes main made */
    u32 messages;      /* messages put on the event line */
    u32 live;          /* live updates drawn (since M8a's later parts) */
    u32 live_max;      /* the longest */
    u32 item_max_part; /* which part that was (views.c's ITEM_* bit) */
    u32 reserved;
    /* Written by the engine (M8a's macros): BRIGHT, COLOR, SHAPE, MOTION
     * now, 0 with "Knobs: direct". */
    s32 macro[4];
    /* The spectrum (M8a part 5): transforms made, skipped (silence), the
     * longest (ticks), and the tallest bar of the last one (its index in
     * the low half, its height in the high). */
    u32 spec_updates;
    u32 spec_silent;
    u32 spec_max;
    u32 spec_peak;
};
extern volatile struct sb_ui_record sb_ui;

#endif
