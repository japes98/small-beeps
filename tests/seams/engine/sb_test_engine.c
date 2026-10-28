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
 * hands over its voices. Since BR-4 its init runs C++ that needs the
 * platform's runtime (sb_test_runtime.cc). Since BR-7 it takes MIDI in
 * and keeps each System Exclusive message's bytes through the SysEx tap
 * (midi.h), up to SYSEX_MAX of them, and its serve sums them. Since
 * BR-8 its serve sends RAW_LEN raw bytes to MIDI out at the first whole
 * second (a System Exclusive message), while for RAW_BLOCKS blocks from
 * then its block callback queues a clock every block and a note on or
 * off every 16th.
 */

#include "audio.h"
#include "core1.h"
#include "engine.h"
#include "input.h"
#include "midi.h"
#include "midi_out.h"

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
    /* Since BR-4: */
    u32 runtime;        /* sb_test_runtime's result */
    /* Since BR-7: */
    u32 sysex_begun;    /* MIDI_SYSEX_BEGIN taps */
    u32 sysex_ended;    /* MIDI_SYSEX_END taps */
    u32 sysex_cut;      /* MIDI_SYSEX_CUT taps */
    u32 sysex_cut_by;   /* the status byte that cut the last */
    u32 sysex_served;   /* whole messages the serve summed */
    u32 sysex_len;      /* the last one's data bytes */
    u32 sysex_sum;      /* their sum, each byte times its place plus one */
    u32 sysex_first;    /* its first data byte and its last */
    u32 sysex_last;
    u32 realtime;       /* realtime messages midi_read handed on */
    u32 notes;          /* note ons it handed on */
    /* Since BR-8: */
    u32 raw_started;    /* the block in which the serve handed MIDI out its bytes, or 0 */
    u32 raw_done;       /* the block in which a serve found them gone, or 0 */
    u32 out_notes;      /* note ons and offs the block callback queued */
    u32 out_clocks;     /* clocks it queued */
    u32 out_refused;    /* of those, the queue dropped */
};

u32 sb_test_runtime(void);

/* Among the engine's records (firmware/platform.ld): linked with the
 * platform alone, the first after the store's, where engine.ld asserts
 * it; with the base's instrument, after its records. */
volatile struct sb_test_engine_record sb_test_engine __attribute__((section(".beacon.engine")));

static u32 phase;

/* The SysEx tap's buffer: written in the block callback, read by the
 * serve once a message has ended (ready holds its length, 0 meanwhile). */
#define SYSEX_MAX 4200u
static u8 sysex_buf[SYSEX_MAX];
static u32 sysex_at;
static volatile u32 sysex_ready;

/* MIDI out's raw bytes: F0, RAW_LEN - 2 data bytes, F7. */
#define RAW_LEN    600u
#define RAW_BLOCKS 300u
static u8 raw[RAW_LEN];

static void queue_out(u8 status, u8 d1, u8 d2, u8 length)
{
    struct midi_msg m;

    m.status = status;
    m.data[0] = d1;
    m.data[1] = d2;
    m.length = length;
    if (!midi_out_send(&m))
        sb_test_engine.out_refused++;
}

static void sysex_tap(u32 event, u8 byte)
{
    switch (event) {
    case MIDI_SYSEX_BEGIN:
        sb_test_engine.sysex_begun++;
        sysex_at = 0;
        break;
    case MIDI_SYSEX_DATA:
        if (sysex_at < SYSEX_MAX)
            sysex_buf[sysex_at] = byte;
        sysex_at++;
        break;
    case MIDI_SYSEX_END:
        sb_test_engine.sysex_ended++;
        if (!sysex_ready && sysex_at <= SYSEX_MAX) {
            sysex_ready = sysex_at;
            sb_work++;
        }
        break;
    default:
        sb_test_engine.sysex_cut++;
        sb_test_engine.sysex_cut_by = byte;
        break;
    }
}

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
    sb_test_engine.runtime = sb_test_runtime();
    midi_start();
    midi_sysex_tap(sysex_tap);
    sb_test_engine.core1 = (u32)sb_core1_start(core1_loop, core1_stack + sizeof core1_stack / sizeof core1_stack[0]);
}

void sb_engine_block(s32 *out, u32 frames)
{
    struct input_event e;
    struct midi_msg m;
    u32 n, seq = job_seq + 1, wait;

    /* Core 1's job for this block, waited for after the samples. */
    if (sb_test_engine.core1)
        sb_publish(&job_lock, &job_seq, seq);
    while (input_read_audio(&e))
        if (e.kind == INPUT_PRESS)
            sb_test_engine.presses++;
    midi_poll();
    while (midi_read(&m)) {
        if (m.status >= 0xF8u)
            sb_test_engine.realtime++;
        else if ((m.status & 0xF0u) == MIDI_NOTE_ON)
            sb_test_engine.notes++;
    }
    /* Clocks and notes queued while the raw bytes go out, and after. */
    if (sb_test_engine.raw_started && sb_audio.blocks - sb_test_engine.raw_started < RAW_BLOCKS) {
        u32 k = sb_audio.blocks - sb_test_engine.raw_started;

        queue_out(MIDI_CLOCK, 0, 0, 0);
        sb_test_engine.out_clocks++;
        if (k % 16 == 0) {
            queue_out((u8)(k % 32 ? MIDI_NOTE_OFF : MIDI_NOTE_ON), (u8)(60 + k / 32 % 12), 100, 2);
            sb_test_engine.out_notes++;
        }
    }
    midi_out_poll();
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
    /* MIDI out's raw bytes, from the first whole second. */
    if (!sb_test_engine.raw_started && sb_seconds >= 1) {
        u32 i;

        raw[0] = MIDI_SYSEX;
        for (i = 1; i < RAW_LEN - 1; i++)
            raw[i] = (u8)((i * 5 + 1) & 0x7Fu);
        raw[RAW_LEN - 1] = MIDI_EOX;
        if (midi_out_raw(raw, RAW_LEN))
            sb_test_engine.raw_started = sb_audio.blocks;
    } else if (sb_test_engine.raw_started && !sb_test_engine.raw_done && !midi_out_raw_busy()) {
        sb_test_engine.raw_done = sb_audio.blocks;
    }
    /* A whole SysEx message the tap kept: the work on it, here. */
    if (sysex_ready) {
        u32 n = sysex_ready, i, sum = 0;

        for (i = 0; i < n; i++)
            sum += sysex_buf[i] * (i + 1);
        sb_test_engine.sysex_len = n;
        sb_test_engine.sysex_sum = sum;
        sb_test_engine.sysex_first = n ? sysex_buf[0] : 0;
        sb_test_engine.sysex_last = n ? sysex_buf[n - 1] : 0;
        sb_test_engine.sysex_served++;
        sysex_ready = 0;
    }
}
