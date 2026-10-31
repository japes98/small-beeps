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
 * off every 16th. Since BR-9 it starts the store and does what a control
 * record (kind CONTROL_KIND, written by the suite between runs) asks in
 * its first serve: writes payloads of the firmware kinds, large and
 * small, or a reset; and records what it read at start-up and what its
 * write read back. Since BR-12 a step of 0x80 or more waits for the
 * first key press (so a run without one only reads the store at
 * start-up): a payload rewritten, large or small, or a user slot's patch
 * (the base's kind), for the suite to cut the power part way; and it
 * records a user slot's patch at start-up too. Since BR-16 its first
 * serve records the heartbeat's time and what the screen shows, and
 * built with SB_NO_START_SCREENS it draws its own first frame there: a
 * square of DRAWN_COLOUR on black.
 */

#include "audio.h"
#include "core1.h"
#include "engine.h"
#include "input.h"
#include "midi.h"
#include "midi_out.h"
#include "store.h"

#define TEST_ENGINE_MARKER 0x31474E45u   /* "ENG1" in memory order */
#define HALF_PERIOD        50u           /* frames: about 441 Hz */
#define LEVEL              (AUDIO_FULL / 16)

/* Since BR-16: its own first frame (tools/seams_suite.py, case
 * nostart), the square's place and colour. */
#define DRAWN_X      100u
#define DRAWN_Y      100u
#define DRAWN_SIZE   40u
#define DRAWN_COLOUR RGB565(0, 63, 31)

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
    /* Since BR-9 (store_get's length, or 0xFFFFFFFF for none; sums by place): */
    u32 step;           /* the control record's step, 0 without one */
    u32 boot_large;     /* LARGE_KIND, LARGE_ID at start-up */
    u32 boot_large_sum;
    u32 boot_small;     /* SMALL_KIND, 0 at start-up */
    u32 boot_small_sum;
    s32 put_result;     /* the step's last store_put or store_reset */
    s32 put2_result;    /* step 5's second, refused */
    u32 put_len;        /* what it read back */
    u32 put_sum;
    /* Since BR-12: */
    u32 boot_patch;     /* STORE_PATCH, PATCH_SLOT at start-up */
    u32 boot_patch_sum;
    u32 stepped;        /* the block in which the serve did the step, or 0 */
    /* Since BR-16, what main left when the first serve came: */
    u32 first_beats;    /* the heartbeat's beats (ms since main started it) */
    u32 first_screen;   /* sb_beacon.screen */
    u32 first_frames;   /* whole frames sent to the panel */
    u32 drawn_beats;    /* with SB_NO_START_SCREENS: beats when it sent its own frame, or 0 */
};

u32 sb_test_runtime(void);

/* Among the engine's records (firmware/platform.ld): linked with the
 * platform alone, the first after the store's, where engine.ld asserts
 * it; with the base's instrument, after its records. */
volatile struct sb_test_engine_record sb_test_engine __attribute__((section(".beacon.engine")));

static u32 phase;

/* The store's steps (tools/seams_suite.py, case store): the payloads,
 * byte i of pattern p being (i * (2p + 1) + p) & 0xFF. */
#define CONTROL_KIND 0x8Fu
#define LARGE_KIND   0x80u
#define LARGE_ID     7u
#define SMALL_KIND   0x81u
#define HUGE_KIND    0x82u
#define LARGE_LEN    4096u
#define SMALL_LEN    10u
#define HUGE_LEN     5000u
#define SMALL2_LEN   300u            /* the small payload rewritten (BR-12): still one part */
#define MID_LEN      3400u           /* the large payload in today's region (BR-12): 7 parts */
#define PATCH_SLOT   3u
#define PATCH_LEN    112u
static u8 store_buf[STORE_FW_MAX];

static void pattern(u32 p, u32 len)
{
    u32 i;

    for (i = 0; i < len; i++)
        store_buf[i] = (u8)(i * (2 * p + 1) + p);
}

/* Reads (kind, id) into store_buf: its length, or 0xFFFFFFFF; its sum. */
static u32 read_back(u32 kind, u32 id, volatile u32 *sum)
{
    u32 version, i, s = 0;
    int n = store_get(kind, id, store_buf, STORE_FW_MAX, &version);

    for (i = 0; n > 0 && i < (u32)n; i++)
        s += store_buf[i] * (i + 1);
    *sum = s;
    return n < 0 ? 0xFFFFFFFFu : (u32)n;
}

static void store_step(void)
{
    u32 s = sb_test_engine.step;

    if (s == 1 || s == 2 || s == 3) {
        /* 1: pattern 1 (and the small payload); 2: pattern 2; 3:
         * pattern 3, the suite cutting the power part way. */
        pattern(s, LARGE_LEN);
        sb_test_engine.put_result = store_put(LARGE_KIND, LARGE_ID, 1, store_buf, LARGE_LEN);
        if (s == 1) {
            pattern(9, SMALL_LEN);
            store_put(SMALL_KIND, 0, 1, store_buf, SMALL_LEN);
        }
        sb_test_engine.put_len = read_back(LARGE_KIND, LARGE_ID, &sb_test_engine.put_sum);
    } else if (s == 4) {
        sb_test_engine.put_result = store_reset();
    } else if (s == 5) {
        /* The largest the region holds, alone, then more than it can. */
        pattern(5, HUGE_LEN);
        sb_test_engine.put_result = store_put(HUGE_KIND, 0, 1, store_buf, HUGE_LEN);
        pattern(6, STORE_FW_MAX);
        sb_test_engine.put2_result = store_put(HUGE_KIND, 1, 1, store_buf, STORE_FW_MAX);
        sb_test_engine.put_len = read_back(HUGE_KIND, 0, &sb_test_engine.put_sum);
    } else if (s == 0x83) {
        /* BR-12, on the first key press: the large payload rewritten,
         * pattern 3 (in a region of the test engine's own, store5.ld or
         * store16.ld; since clean-store-region). */
        pattern(3, LARGE_LEN);
        sb_test_engine.put_result = store_put(LARGE_KIND, LARGE_ID, 1, store_buf, LARGE_LEN);
        sb_test_engine.put_len = read_back(LARGE_KIND, LARGE_ID, &sb_test_engine.put_sum);
    } else if (s == 0x84) {
        /* The large payload rewritten as 3 400 bytes, pattern 4, in
         * today's region: room for both copies only if the ring copies
         * the old one forward during the rewrite. */
        pattern(4, MID_LEN);
        sb_test_engine.put_result = store_put(LARGE_KIND, LARGE_ID, 1, store_buf, MID_LEN);
        sb_test_engine.put_len = read_back(LARGE_KIND, LARGE_ID, &sb_test_engine.put_sum);
    } else if (s == 0x86) {
        /* The small payload rewritten, pattern 10, longer. */
        pattern(10, SMALL2_LEN);
        sb_test_engine.put_result = store_put(SMALL_KIND, 0, 1, store_buf, SMALL2_LEN);
        sb_test_engine.put_len = read_back(SMALL_KIND, 0, &sb_test_engine.put_sum);
    } else if (s == 0x87) {
        /* A user slot's patch rewritten (the base's kind), pattern 12. */
        u32 version;
        int n;

        pattern(12, PATCH_LEN);
        sb_test_engine.put_result = store_put(STORE_PATCH, PATCH_SLOT, 2, store_buf, PATCH_LEN);
        n = store_get(STORE_PATCH, PATCH_SLOT, store_buf, PATCH_LEN, &version);
        sb_test_engine.put_len = n < 0 ? 0xFFFFFFFFu : (u32)n;
    }
}

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
    /* The store, and what it holds at start-up. */
    store_init();
    {
        u32 version;
        u8 step = 0;

        if (store_get(CONTROL_KIND, 0, &step, 1, &version) == 1)
            sb_test_engine.step = step;
    }
    sb_test_engine.boot_large = read_back(LARGE_KIND, LARGE_ID, &sb_test_engine.boot_large_sum);
    sb_test_engine.boot_small = read_back(SMALL_KIND, 0, &sb_test_engine.boot_small_sum);
    {
        u32 version, i, sum = 0;
        int n = store_get(STORE_PATCH, PATCH_SLOT, store_buf, PATCH_LEN, &version);

        for (i = 0; n > 0 && i < (u32)n; i++)
            sum += store_buf[i] * (i + 1);
        sb_test_engine.boot_patch = n < 0 ? 0xFFFFFFFFu : (u32)n;
        sb_test_engine.boot_patch_sum = sum;
    }
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
    /* The store's step, in the first serve (main's loop: the flash may
     * keep it waiting); since BR-12 a step of 0x80 or more in the first
     * serve after a key press. */
    if (!sb_test_engine.stepped && (sb_test_engine.step < 0x80u ? !sb_test_engine.serves
                                    : sb_test_engine.presses > 0)) {
        sb_test_engine.stepped = sb_audio.blocks + 1;
        store_step();
    }
    if (!sb_test_engine.serves) {
        sb_test_engine.first_beats = sb_beacon.beats;
        sb_test_engine.first_screen = sb_beacon.screen;
        sb_test_engine.first_frames = sb_beacon.frames;
#if defined(SB_NO_START_SCREENS)
        sb_beacon.screen = SB_SCREEN_PANEL;
        gfx_fill(DRAWN_X, DRAWN_Y, DRAWN_SIZE, DRAWN_SIZE, DRAWN_COLOUR);
        while (lcd_busy())
            ;
        lcd_send_rect(DRAWN_X, DRAWN_Y, DRAWN_SIZE, DRAWN_SIZE);
        sb_test_engine.drawn_beats = sb_beacon.beats;
#endif
    }
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
