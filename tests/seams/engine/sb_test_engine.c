/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * A test engine on the engine seam (firmware/src/engine.h, BR-1), built
 * from outside firmware/ (tools/build.sh --src tests/seams/engine
 * --define SB_ENGINE_EXTERNAL) by tools/seams_suite.py, case engine. It
 * counts what main asks of it in a record the suite reads by its ELF
 * symbol (since BR-2 among the engine's records, firmware/platform.ld), plays a quiet square wave, and counts the panel's key presses.
 */

#include "audio.h"
#include "engine.h"
#include "input.h"

#define TEST_ENGINE_MARKER 0x31474E45u   /* "ENG1" in memory order */
#define HALF_PERIOD        50u           /* frames: about 441 Hz */
#define LEVEL              (AUDIO_FULL / 16)

struct sb_test_engine_record {
    u32 marker;
    u32 inits;          /* sb_engine_init calls */
    u32 init_ticks;     /* the tick's interrupts taken before it: 0, as interrupts are off */
    u32 init_blocks;    /* audio blocks before it: 0, as the audio starts after */
    u32 blocks;         /* sb_engine_block calls */
    u32 frames;         /* frames they were asked for */
    u32 serves;         /* sb_engine_serve calls */
    u32 serve_seconds;  /* sb_seconds at the last */
    u32 presses;        /* key presses the block callback took */
    u32 serve_presses;  /* presses seen by the last serve */
};

/* Among the engine's records (firmware/platform.ld): linked with the
 * platform alone, the first after the store's, where engine.ld asserts
 * it; with the base's instrument, after its records. */
volatile struct sb_test_engine_record sb_test_engine __attribute__((section(".beacon.engine")));

static u32 phase;

void sb_engine_init(void)
{
    sb_test_engine.marker = TEST_ENGINE_MARKER;
    sb_test_engine.inits++;
    sb_test_engine.init_ticks = sb_beacon.tick_count;
    sb_test_engine.init_blocks = sb_audio.blocks;
}

void sb_engine_block(s32 *out, u32 frames)
{
    struct input_event e;
    u32 n;

    while (input_read_audio(&e))
        if (e.kind == INPUT_PRESS)
            sb_test_engine.presses++;
    for (n = 0; n < frames; n++) {
        s32 s = phase < HALF_PERIOD ? LEVEL : -LEVEL;

        out[2 * n] = s;
        out[2 * n + 1] = s;
        phase = (phase + 1) % (2 * HALF_PERIOD);
    }
    sb_test_engine.blocks++;
    sb_test_engine.frames += frames;
}

void sb_engine_serve(void)
{
    sb_test_engine.serves++;
    sb_test_engine.serve_seconds = sb_seconds;
    sb_test_engine.serve_presses = sb_test_engine.presses;
}
