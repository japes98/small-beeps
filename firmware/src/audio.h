/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * The audio layer (M4): the output, double-buffered and driven by its
 * interrupt, and the one callback a sound engine implements. This is the
 * API engines are written against, beside input.h; keep it small and
 * stable (docs/DESIGN-NOTES.md, M4, "The audio API").
 *
 * - The engine is one function, audio_engine_fn. The audio layer calls it
 *   once a block, from the output's interrupt, to fill the half of the
 *   buffer that has just finished playing while the other half plays.
 * - A block is AUDIO_FRAMES stereo frames: 2 * AUDIO_FRAMES words, left
 *   then right, each a 24-bit signed sample, sign-extended to 32 bits,
 *   within -AUDIO_FULL .. AUDIO_FULL (HW-44). The engine writes them
 *   straight into the buffer the output plays from: nothing is copied or
 *   converted after it, so it must write every word and stay in range.
 * - The rate is AUDIO_RATE_NUM / AUDIO_RATE_DEN frames a second (HW-45):
 *   44 117.647 Hz, not 44 100.
 * - Between blocks the engine reads the panel's input events with
 *   input_read_audio() (input.h), from inside its callback: the same
 *   events, in the same order, as main's input_read(), from a queue of
 *   their own. input_value() gives any control's present state.
 * - The callback runs in an interrupt at the lowest priority: the tick
 *   and the input scan may interrupt it, main never does. It must finish
 *   within one block (AUDIO_FRAMES / rate, 1.451 ms); a block it is late
 *   for is an underrun, counted and reported on the debug channel
 *   (sb_audio.underruns).
 */

#ifndef AUDIO_H
#define AUDIO_H

#include "sb.h"

#define AUDIO_FRAMES     64u           /* stereo frames a block */
#define AUDIO_RATE_NUM   24000000u     /* frames a second: 24 MHz / 544 (HW-45) */
#define AUDIO_RATE_DEN   544u
#define AUDIO_FULL       0x7FFFFF      /* 24-bit full scale */

/* Fills frames stereo frames at out: out[2n] left, out[2n + 1] right. */
typedef void (*audio_engine_fn)(s32 *out, u32 frames);

/* Starts the output with silence and engine as its engine; main calls it
 * once, before interrupts are on. */
void audio_start(audio_engine_fn engine);
void audio_block(void) __attribute__((interrupt("")));

/* The audio record: counters, at a fixed place in RAM right after the
 * input record (firmware/app.ld), for the tests to capture with fwtest's
 * --ram (tools/fw-suite.py reads this layout). Times are in time base
 * ticks (24 a microsecond). */
#define AUDIO_MARKER     0x34445541u   /* "AUD4" in memory order */
struct sb_audio_record {
    u32 marker;       /* AUDIO_MARKER once the output runs */
    u32 start;        /* sb_ticks() when the output started */
    u32 blocks;       /* blocks the engine filled */
    u32 underruns;    /* blocks it was late for, or a half that went by */
    u32 fill_last;    /* the last block's fill: interrupt to engine done */
    u32 fill_max;     /* the longest */
    u32 dropped;      /* input events the engine's queue dropped (full) */
    u32 engine[9];    /* the engine's own (synth.c: SYNTH_* below) */
};
extern volatile struct sb_audio_record sb_audio;

/* What the test instrument (synth.c) keeps in sb_audio.engine. */
#define SYNTH_VOICES_ON  0   /* voices sounding */
#define SYNTH_NOTES      1   /* notes started */
#define SYNTH_TONE       2   /* 1 while the test tone plays */
#define SYNTH_MASTER     3   /* the MASTER gain, 0 to 1 << 24 */
#define SYNTH_EVENTS     4   /* input events taken */
#define SYNTH_STOLEN     5   /* notes that took a voice still sounding */
#define SYNTH_OCTAVE     6   /* octave shift, -2 to 2, as stored (s32) */
#define SYNTH_FIRST_ON   7   /* sb_audio.blocks when the first note began */
#define SYNTH_LAST_OFF   8   /* sb_audio.blocks when a voice last went silent */

/* synth.c: the test instrument, the engine main starts. */
void synth_block(s32 *out, u32 frames);
void synth_init(void);

#endif
