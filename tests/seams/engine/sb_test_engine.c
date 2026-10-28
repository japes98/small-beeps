/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * A test engine on the engine seam (firmware/src/engine.h, BR-1), built
 * from outside firmware/ (tools/build.sh --src tests/seams/engine
 * --define SB_ENGINE_EXTERNAL) by tools/seams_suite.py, case engine. It
 * counts what main asks of it in a record the suite reads by its ELF
 * symbol (since BR-2 among the engine's records, firmware/platform.ld),
 * plays a quiet square wave, and counts the panel's key presses. Since
 * BR-3 it starts core 1 (core1.h) and hands it a job every block: a
 * sequence number to triple, published under a lock as the FM engine
 * hands over its voices.
 */

#include "audio.h"
#include "core1.h"
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
    /* Since BR-3: */
    u32 core1;          /* sb_core1_start's result */
    u32 core1_jobs;     /* jobs core 1 did */
    u32 core1_wrong;    /* blocks whose job came back wrong or late */
};

/* Among the engine's records (firmware/platform.ld): linked with the
 * platform alone, the first after the store's, where engine.ld asserts
 * it; with the base's instrument, after its records. */
volatile struct sb_test_engine_record sb_test_engine __attribute__((section(".beacon.engine")));

static u32 phase;

/* Core 1's job: core 0 publishes job_seq, core 1 answers job_out (three
 * times it) and job_done (job_seq). */
static volatile u32 job_seq, job_done, job_out;
static volatile u8 job_lock;
static u32 core1_stack[128] __attribute__((aligned(8)));

static void core1_loop(void)
{
    u32 seen = 0;

    for (;;) {
        u32 s = sb_shared(&job_seq);

        if (s == seen)
            continue;
        seen = s;
        job_out = 3 * s;
        sb_test_engine.core1_jobs++;
        sb_publish(&job_lock, &job_done, s);
    }
}

void sb_engine_init(void)
{
    sb_test_engine.marker = TEST_ENGINE_MARKER;
    sb_test_engine.inits++;
    sb_test_engine.init_ticks = sb_beacon.tick_count;
    sb_test_engine.init_blocks = sb_audio.blocks;
    sb_test_engine.core1 = (u32)sb_core1_start(core1_loop, core1_stack + sizeof core1_stack / sizeof core1_stack[0]);
}

void sb_engine_block(s32 *out, u32 frames)
{
    struct input_event e;
    u32 n, seq = job_seq + 1, wait;

    /* Core 1's job for this block, waited for after the samples. */
    if (sb_test_engine.core1)
        sb_publish(&job_lock, &job_seq, seq);
    while (input_read_audio(&e))
        if (e.kind == INPUT_PRESS)
            sb_test_engine.presses++;
    for (n = 0; n < frames; n++) {
        s32 s = phase < HALF_PERIOD ? LEVEL : -LEVEL;

        out[2 * n] = s;
        out[2 * n + 1] = s;
        phase = (phase + 1) % (2 * HALF_PERIOD);
    }
    if (sb_test_engine.core1) {
        for (wait = 0; wait < 100000u && sb_shared(&job_done) != seq; wait++)
            ;
        if (sb_shared(&job_done) != seq || job_out != 3 * seq)
            sb_test_engine.core1_wrong++;
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
