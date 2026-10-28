/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * The Plaits bench (M4b, docs/DESIGN-NOTES.md): built with PLAITS_BENCH,
 * it measures what each of Plaits' engines costs, and stops. It runs in
 * main before interrupts are on, so nothing else runs while it measures.
 *
 * - **Instructions a block.** Each block is 64 frames, rendered as four
 *   renders of 16 like the demo's, timed with the time base: 24 MHz, so
 *   10 of core 0's cycles a tick in fwtest, where an instruction is a
 *   cycle (HW-11, HW-13). The time base is read only before and after a
 *   block, far apart, so fwtest never takes the reads for a wait.
 * - **At its heaviest.** For each engine: one block after switching to it
 *   (its set-up, reported apart), then BENCH_BLOCKS blocks at each of nine
 *   settings (HARMONICS, TIMBRE and MORPH each at 0 and 1, and all at
 *   0.5), a key struck at the first block of each and held. Reported: the
 *   largest block, and the mean.
 * - **Clean.** Each block's samples are summed into a checksum (the same
 *   inputs must give the same sound in every build), and samples at full
 *   scale are counted (clipping). Soft-float's exception counts
 *   (runtime/softfloat.c) say whether anything made a NaN or an infinity.
 * - **Core 1.** Core 1 is started (HW-9) on a loop that renders a second
 *   voice whenever core 0 asks; core 0 times a block of its own voice
 *   with core 1 rendering another at once, against the same two one
 *   after the other, for three engines.
 *
 * First it runs the soft-float test (sftest.c). Results go to the debug
 * console (HW-25) as lines of hex words, which
 * tools/plaits-bench.py reads; then the core stops with interrupts off,
 * which fwtest reports as a halt.
 */

#if defined(PLAITS_BENCH)

#include "audio.h"
#include "core1.h"
#include "plaits_voice.h"

#define BENCH_BLOCKS   4
#define BENCH_POINTS   9
#define CYCLES_A_TICK  10
#define FULL_SCALE     32767
#define RATE_OFFSET    1.4140377f
#define BENCH_NOTE     (48.0f + RATE_OFFSET)

extern volatile u32 softfloat_flags[3];
void plaits_test_softfloat(void);   /* sftest.c */

/* --- the console: lines of hex words ------------------------------- */

static char line[96];
static u32 used;

static void put(char c)
{
    if (used < sizeof line)
        line[used++] = c;
}

static void put_hex(u32 v)
{
    static const char hex[] = "0123456789abcdef";
    int i;

    put(' ');
    for (i = 28; i >= 0; i -= 4)
        put(hex[(v >> i) & 15u]);
}

static void start_line(const char *tag)
{
    used = 0;
    while (*tag)
        put(*tag++);
}

/* Ends the line, padded with spaces to whole words, and writes it. */
static void end_line(void)
{
    while ((used + 1) % 4)
        put(' ');
    put('\n');
    sb_console_write(line, used / 4);
}

/* --- one block ------------------------------------------------------ */

struct sums {
    u32 checksum;
    u32 clipped;
    u32 peak;
};

static void render_block(unsigned v, const struct plaits_params *p, struct sums *s)
{
    short buf[2 * PLAITS_RENDER];
    u32 n, i;

    for (n = 0; n < AUDIO_FRAMES; n += PLAITS_RENDER) {
        plaits_voice_render(v, p, buf, PLAITS_RENDER);
        if (!s)
            continue;
        for (i = 0; i < 2 * PLAITS_RENDER; i += 2) {
            int x = buf[i];
            u32 a = (u32)(x < 0 ? -x : x);

            s->checksum = s->checksum * 31u + (u32)(u16)buf[i];
            if (a >= FULL_SCALE)
                s->clipped++;
            if (a > s->peak)
                s->peak = a;
        }
    }
}

static u32 timed_block(unsigned v, const struct plaits_params *p, struct sums *s)
{
    u32 t0 = sb_now(), t1;

    render_block(v, p, s);
    t1 = sb_now();
    return t1 - t0;
}

static void point(int k, struct plaits_params *p)
{
    if (k == BENCH_POINTS - 1) {
        p->harmonics = p->timbre = p->morph = 0.5f;
    } else {
        p->harmonics = (k & 1) ? 1.0f : 0.0f;
        p->timbre = (k & 2) ? 1.0f : 0.0f;
        p->morph = (k & 4) ? 1.0f : 0.0f;
    }
}

/* --- core 1 --------------------------------------------------------- */

struct core1_job {
    volatile u32 go;        /* core 0 adds one to start a block */
    volatile u32 done;      /* core 1 copies go when it has finished */
    volatile u32 alive;     /* core 1 sets it on starting */
    struct plaits_params params;
};
static struct core1_job job;

void plaits_core1_main(void) __attribute__((noreturn));

/* Core 1's stack: 8 KiB (Plaits' render goes deep). */
static u32 core1_stack[2048] __attribute__((aligned(8)));

/* Core 1's loop: a block of voice 1 for each step of go. It never reads
 * the time base, whose reads count towards core 0's waits in fwtest
 * (docs/HARNESS.md, "Time"). */
void plaits_core1_main(void)
{
    u32 seen = 0;

    job.alive = 1;
    for (;;) {
        while (job.go == seen)
            ;
        seen = job.go;
        render_block(1, &job.params, 0);
        job.done = seen;
    }
}

/* Since clean-1027 through the platform (core1.h, BR-3). */
static int start_core1(void)
{
    return sb_core1_start(plaits_core1_main, core1_stack + sizeof core1_stack / sizeof core1_stack[0]);
}

/* --- the bench ------------------------------------------------------ */

void plaits_bench(void)
{
    static const int dual[3] = { 0, 8, 19 };   /* VA-VCF, VA, the string */
    struct plaits_params p;
    int e, k, b;
    u32 i;

    start_line("PLAITS-BENCH");
    put_hex(1);                         /* format */
    put_hex(PLAITS_ENGINES);
    put_hex(BENCH_POINTS);
    put_hex(BENCH_BLOCKS);
    put_hex(AUDIO_FRAMES);
    put_hex(PLAITS_RENDER);
#if defined(PLAITS_HWFLOAT)
    put_hex(1);
#else
    put_hex(0);
#endif
    end_line();

    plaits_test_softfloat();
    /* The flags count Plaits' operations only: the test made its own on
     * purpose (infinities, NaN). */
    for (i = 0; i < 3; i++)
        softfloat_flags[i] = 0;

    plaits_voice_init(0);
    p.note = BENCH_NOTE;
    p.decay = 0.5f;
    p.lpg_colour = 0.5f;
    for (e = 0; e < PLAITS_ENGINES; e++) {
        struct sums s = { 0, 0, 0 };
        u32 set_up, t, max = 0, sum = 0, count = 0;

        p.engine = e;
        p.trigger = 0;
        point(BENCH_POINTS - 1, &p);
        set_up = timed_block(0, &p, 0);
        for (k = 0; k < BENCH_POINTS; k++) {
            point(k, &p);
            for (b = 0; b < BENCH_BLOCKS; b++) {
                p.trigger = 1;
                if (b == 0) {
                    /* a fresh strike: the trigger low for one render */
                    struct plaits_params q = p;
                    short buf[2 * PLAITS_RENDER];

                    q.trigger = 0;
                    plaits_voice_render(0, &q, buf, PLAITS_RENDER);
                }
                t = timed_block(0, &p, &s);
                sum += t;
                count++;
                if (t > max)
                    max = t;
            }
        }
        start_line("E");
        put_hex((u32)e);
        put_hex(set_up * CYCLES_A_TICK);
        put_hex(max * CYCLES_A_TICK);
        put_hex(sum * CYCLES_A_TICK / count);
        put_hex(s.checksum);
        put_hex(s.clipped);
        put_hex(s.peak);
        end_line();
    }
    start_line("FLAGS");
    for (i = 0; i < 3; i++)
        put_hex(softfloat_flags[i]);
    end_line();

    /* Core 1: the same block of two voices, one after the other on core
     * 0, then at once on both cores. */
    plaits_voice_init(1);
    start_line("CORE1");
    put_hex((u32)start_core1());
    end_line();
    if (job.alive) {
        for (k = 0; k < 3; k++) {
            u32 seq, both, apart;

            p.engine = dual[k];
            p.trigger = 1;
            point(BENCH_POINTS - 1, &p);
            job.params = p;
            /* settle both voices on the engine first */
            for (b = 0; b < 2; b++) {
                render_block(0, &p, 0);
                render_block(1, &p, 0);
            }
            seq = sb_now();
            render_block(0, &p, 0);
            render_block(1, &p, 0);
            apart = sb_now() - seq;
            seq = job.go + 1;
            {
                u32 t0 = sb_now();

                job.go = seq;
                render_block(0, &p, 0);
                while (job.done != seq)
                    ;
                both = sb_now() - t0;
            }
            start_line("D");
            put_hex((u32)p.engine);
            put_hex(apart * CYCLES_A_TICK);
            put_hex(both * CYCLES_A_TICK);
            end_line();
        }
    }
    start_line("END");
    end_line();
    __asm__ volatile("cli");
    for (;;)
        ;
}

#endif
