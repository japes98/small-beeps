/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * The test instrument (M4): an engine that proves the audio path end to
 * end, not a synth design (docs/DESIGN-NOTES.md, M4, "The test
 * instrument"). Four sine voices played by the 27 keys, each with a
 * linear attack and release so a note starts and stops without a click,
 * pitch from the key (KEY1 is F3; OCT- and OCT+ shift by octaves), level
 * from MASTER; and a fixed test tone, 1 kHz at -6 dBFS whatever MASTER
 * says, started and stopped by PLAY. Fixed point throughout: there is no
 * floating point and no maths library (R-BUILD-1).
 */

#include "audio.h"
#include "input.h"

#define VOICES       4u
#define TONE         VOICES            /* the test tone's oscillator */
/* A sine table of 1024 steps a cycle (and one more, for interpolating
 * past the last), 24-bit full scale: filled once by synth_init. */
#define SINE_BITS    10u
#define SINE_STEPS   (1u << SINE_BITS)
/* Envelopes are gains from 0 to ENV_FULL. Attack 5 ms, release 20 ms at
 * the output's rate: 221 and 882 samples. */
#define ENV_FULL     (1 << 24)
#define ATTACK       (ENV_FULL / 221)
#define RELEASE      (ENV_FULL / 882)
/* KEY1 is MIDI note 53 (F3); KEY8 is middle C. */
#define KEY1_NOTE    53
#define OCTAVES      2

enum { OFF, ATTACKING, HOLDING, RELEASING };

struct voice {
    u32 phase;   /* the cycle, in 1 / 2^32 */
    u32 inc;     /* added each sample: frequency / rate * 2^32 */
    s32 env;     /* gain, 0 to ENV_FULL */
    u32 state;
    u32 control; /* the key holding it */
    u32 age;     /* sb_audio.blocks when its note began */
};

static s32 sine[SINE_STEPS + 1];
static struct voice voice[VOICES + 1];
static s32 mix[AUDIO_FRAMES];
static s32 master;
static int octave;

/* Phase increments of MIDI notes 108 to 119 (C8 to B8) at the output's
 * rate: round(440 * 2^((n - 69) / 12) / (24 MHz / 544) * 2^32), computed
 * offline in double precision. Lower notes are these halved, rounded. */
static const u32 top_octave[12] = {
    407518831, 431751162, 457424422, 484624293, 513441553, 543972377,
    576318657, 610588348, 646895821, 685362248, 726116008, 769293113,
};
/* 1 kHz: round(1000 / (24 MHz / 544) * 2^32). */
#define TONE_INC     97352592u

static u32 note_inc(int note)
{
    u32 down;

    note = note < 0 ? 0 : note > 119 ? 119 : note;
    if (note >= 108)
        return top_octave[note - 108];
    down = (u32)(119 - note) / 12;   /* octaves below the top one */
    return (top_octave[note + 12 * (int)down - 108] + (1u << (down - 1))) >> down;
}

/* a * b / 2^29, for the sine's series: in 2^-29, x^2 up to (pi / 2)^2
 * still fits 32 bits. */
static s32 q29(s32 a, s32 b)
{
    return (s32)((s64)a * b >> 29);
}

/* sin(x) for x from 0 to pi/2 in 2^-29 (the result too), by its series to
 * x^11: within 1e-7 at pi/2, far below the 24-bit samples' steps. */
static s32 sin_q29(s32 x)
{
    s32 s = q29(x, x), t = (1 << 29);

    t = (1 << 29) - q29(t, s) / 110;
    t = (1 << 29) - q29(t, s) / 72;
    t = (1 << 29) - q29(t, s) / 42;
    t = (1 << 29) - q29(t, s) / 20;
    t = (1 << 29) - q29(t, s) / 6;
    return q29(x, t);
}

void synth_init(void)
{
    u32 i;

    /* A quarter cycle from the series, the rest by symmetry. pi / 2 in
     * 2^-29 is 843314857. */
    for (i = 0; i <= SINE_STEPS / 4; i++) {
        s32 x = (s32)((s64)i * 843314857 >> (SINE_BITS - 2));
        s32 v = (s32)(((s64)sin_q29(x) * AUDIO_FULL + (1 << 28)) >> 29);
        sine[i] = v;
        sine[SINE_STEPS / 2 - i] = v;
        sine[SINE_STEPS / 2 + i] = -v;
        if (i)
            sine[SINE_STEPS - i] = -v;
    }
    sine[SINE_STEPS] = sine[0];
    voice[TONE].inc = TONE_INC;
}

/* One sample of an oscillator: the table, interpolated (15 bits of the
 * phase between two steps). */
static inline __attribute__((always_inline)) s32 osc(u32 phase)
{
    u32 i = phase >> (32 - SINE_BITS), f = phase >> (17 - SINE_BITS) & 0x7FFFu;
    s32 a = sine[i];

    return a + ((sine[i + 1] - a) * (s32)f >> 15);
}

static void note_on(u32 control)
{
    u32 v, pick = VOICES, oldest = 0;

    /* A free voice; else the quietest releasing one; else the oldest. */
    for (v = 0; v < VOICES; v++)
        if (voice[v].state == OFF) {
            pick = v;
            break;
        }
    if (pick == VOICES) {
        for (v = 0; v < VOICES; v++)
            if (voice[v].state == RELEASING && (pick == VOICES || voice[v].env < voice[pick].env))
                pick = v;
        if (pick == VOICES)
            for (v = 1; v < VOICES; v++)
                if (voice[v].age < voice[oldest].age)
                    oldest = v;
        pick = pick == VOICES ? oldest : pick;
        sb_audio.engine[SYNTH_STOLEN]++;
    }
    /* A voice taken over keeps its phase and level, so the change is a
     * change of pitch, not a step. */
    if (voice[pick].state == OFF)
        voice[pick].phase = 0;
    voice[pick].inc = note_inc(KEY1_NOTE + (int)(control - INPUT_KEY1) + 12 * octave);
    voice[pick].state = ATTACKING;
    voice[pick].control = control;
    voice[pick].age = sb_audio.blocks;
    if (!sb_audio.engine[SYNTH_NOTES])
        sb_audio.engine[SYNTH_FIRST_ON] = sb_audio.blocks;
    sb_audio.engine[SYNTH_NOTES]++;
}

static void note_off(u32 control)
{
    u32 v;

    for (v = 0; v < VOICES; v++)
        if (voice[v].control == control && (voice[v].state == ATTACKING || voice[v].state == HOLDING))
            voice[v].state = RELEASING;
}

/* The events since the last block. */
static void events(void)
{
    struct input_event e;

    while (input_read_audio(&e)) {
        sb_audio.engine[SYNTH_EVENTS]++;
        if (e.control >= INPUT_KEY1 && e.control <= INPUT_KEY27) {
            if (e.kind == INPUT_PRESS)
                note_on(e.control);
            else if (e.kind == INPUT_RELEASE)
                note_off(e.control);
        } else if (e.kind == INPUT_PRESS && e.control == INPUT_OCT_DOWN) {
            octave -= octave > -OCTAVES;
        } else if (e.kind == INPUT_PRESS && e.control == INPUT_OCT_UP) {
            octave += octave < OCTAVES;
        } else if (e.kind == INPUT_PRESS && e.control == INPUT_PLAY) {
            voice[TONE].state = voice[TONE].state == OFF || voice[TONE].state == RELEASING
                                ? ATTACKING : RELEASING;
        }
    }
    sb_audio.engine[SYNTH_OCTAVE] = (u32)octave;
    sb_audio.engine[SYNTH_TONE] = voice[TONE].state != OFF && voice[TONE].state != RELEASING;
}

/* One voice's frames into mix[] at shift (26: a quarter of full scale;
 * 25: a half). Returns 0 once the voice has gone silent. */
static u32 render(struct voice *p, u32 frames, u32 shift)
{
    u32 n, phase = p->phase, inc = p->inc;
    s32 env = p->env, step = p->state == ATTACKING ? ATTACK : p->state == RELEASING ? -RELEASE : 0;

    for (n = 0; n < frames; n++) {
        mix[n] += (s32)((s64)osc(phase) * env >> shift);
        phase += inc;
        if (step) {
            env += step;
            if (env >= ENV_FULL) {
                env = ENV_FULL;
                step = 0;
                p->state = HOLDING;
            } else if (env <= 0) {
                p->state = OFF;
                p->env = 0;
                sb_audio.engine[SYNTH_LAST_OFF] = sb_audio.blocks;
                return 0;
            }
        }
    }
    p->phase = phase;
    p->env = env;
    return 1;
}

void synth_block(s32 *out, u32 frames)
{
    u32 n, v, on = 0, tone;
    s32 target, m, step, *w;
    int pot;

    events();
    /* MASTER's gain: the square of its position, so that it sounds about
     * even, reached by a ramp over the block so a move doesn't click. */
    pot = input_value(INPUT_MASTER);
    target = pot >= 1023 ? ENV_FULL : pot * pot * 16;
    step = (target - master) / (s32)AUDIO_FRAMES;
    sb_audio.engine[SYNTH_MASTER] = (u32)target;

    for (v = 0; v < VOICES + 1 && voice[v].state == OFF; v++)
        ;
    if (v == VOICES + 1) {
        /* At rest: silence, exactly. */
        for (n = 0; n < 2 * frames; n++)
            out[n] = 0;
        master = target;
        sb_audio.engine[SYNTH_VOICES_ON] = 0;
        return;
    }
    for (n = 0; n < frames; n++)
        mix[n] = 0;
    for (v = 0; v < VOICES; v++)
        if (voice[v].state != OFF)
            on += render(&voice[v], frames, 26);
    m = master;
    for (n = 0, w = out; n < frames; n++, w += 2) {
        s32 s = (s32)((s64)mix[n] * m >> 24);
        m += step;
        w[0] = s;
        w[1] = s;
    }
    master = target;
    /* The test tone after MASTER: its level is fixed. */
    tone = voice[TONE].state != OFF;
    if (tone) {
        for (n = 0; n < frames; n++)
            mix[n] = 0;
        render(&voice[TONE], frames, 25);
        for (n = 0, w = out; n < frames; n++, w += 2) {
            s32 s = w[0] + mix[n];
            s = s > AUDIO_FULL ? AUDIO_FULL : s < -AUDIO_FULL ? -AUDIO_FULL : s;
            w[0] = s;
            w[1] = s;
        }
    }
    sb_audio.engine[SYNTH_VOICES_ON] = on;
}
