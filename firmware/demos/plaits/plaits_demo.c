/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * The Plaits demo's engine (M4b's platform load test, docs/DESIGN-NOTES.md):
 * Plaits' voice played through our audio and input APIs only (audio.h,
 * input.h), in place of the test instrument. Built as its own image by
 * tools/build.sh build --demo plaits; never part of the firmware.
 *
 * - A key plays a note: the last key pressed sets the pitch (KEY1 is F3, as
 *   in the test instrument; OCT- and OCT+ shift by octaves) and holds
 *   Plaits' trigger high until it is released.
 * - ALGORITHM selects the engine, one detent each, round all 24, from
 *   the chiptune engine (7): the only one soft-float can render within a
 *   block. Any other overloads core 0 with soft-float (underruns, and
 *   main, starved, stops taking input); built with PLAITS_HWFLOAT every
 *   engine fits (docs/DESIGN-NOTES.md, M4b).
 * - KNOB1 to KNOB4 are Plaits' HARMONICS, TIMBRE, MORPH and its envelope's
 *   decay: each starts in the middle, 64 detents from end to end.
 * - MASTER is the volume, its square as in the test instrument.
 *
 * Plaits computes at its own rate (47 872.34 Hz, its tables and filters
 * are made for it); ours is 44 117.647 Hz, so every pitch is raised by
 * 12 log2(47 872.34 / 44 117.647) = 1.414 semitones to sound right. Its
 * time constants (envelopes, filters' corners in Hz) run 7.8% slow.
 */

#include "audio.h"
#include "input.h"
#include "plaits_voice.h"

#define KEY1_NOTE     53
#define OCTAVES       2
#define RATE_OFFSET   1.4140377f   /* semitones, as above */
#define KNOB_SPAN     64           /* detents from 0 to 1 */
#define GAIN_FULL     (1 << 24)
#define FIRST_ENGINE  7            /* chiptune, as above */

static struct plaits_params params;
static int octave;
static u32 held;                    /* the key holding the trigger, or 0 */
static s32 gain;

/* An encoder's position as a parameter from 0 to 1, starting at 0.5. */
static float knob(u32 control)
{
    int d = input_value(control) + KNOB_SPAN / 2;

    if (d < 0)
        d = 0;
    if (d > KNOB_SPAN)
        d = KNOB_SPAN;
    return (float)d / (float)KNOB_SPAN;
}

void plaits_demo_init(void)
{
    plaits_voice_init(0);
    params.note = 48.0f;
    params.lpg_colour = 0.5f;
}

static void events(void)
{
    struct input_event e;

    while (input_read_audio(&e)) {
        if (e.control >= INPUT_KEY1 && e.control <= INPUT_KEY27) {
            if (e.kind == INPUT_PRESS) {
                held = e.control;
                params.note = (float)(KEY1_NOTE + (int)(e.control - INPUT_KEY1) + 12 * octave) + RATE_OFFSET;
                params.trigger = 1;
            } else if (e.kind == INPUT_RELEASE && e.control == held) {
                held = 0;
                params.trigger = 0;
            }
        } else if (e.kind == INPUT_PRESS && e.control == INPUT_OCT_DOWN) {
            octave -= octave > -OCTAVES;
        } else if (e.kind == INPUT_PRESS && e.control == INPUT_OCT_UP) {
            octave += octave < OCTAVES;
        }
    }
}

void plaits_demo_block(s32 *out, u32 frames)
{
    short buf[2 * PLAITS_RENDER];
    int engine, pot;
    u32 n, i;

    events();
    engine = (FIRST_ENGINE + input_value(INPUT_ALGORITHM)) % PLAITS_ENGINES;
    params.engine = engine < 0 ? engine + PLAITS_ENGINES : engine;
    params.harmonics = knob(INPUT_KNOB1);
    params.timbre = knob(INPUT_KNOB2);
    params.morph = knob(INPUT_KNOB3);
    params.decay = knob(INPUT_KNOB4);
    pot = input_value(INPUT_MASTER);
    gain = pot >= 1023 ? GAIN_FULL : pot * pot * 16;

    for (n = 0; n < frames; n += PLAITS_RENDER) {
        u32 k = frames - n < PLAITS_RENDER ? frames - n : PLAITS_RENDER;

        plaits_voice_render(0, &params, buf, k);
        for (i = 0; i < k; i++) {
            /* 16-bit to the output's 24 bits, then the volume. */
            s32 s = (s32)((s64)((s32)buf[2 * i] << 8) * gain >> 24);

            out[2 * (n + i)] = s;
            out[2 * (n + i) + 1] = s;
        }
    }
    sb_audio.engine[0] = (u32)params.engine;
    sb_audio.engine[1] = held;
}
