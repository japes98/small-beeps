/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * The audio layer (audio.h): the audio link's output (HW-43 to HW-46)
 * playing a two-half buffer in RAM, and source 11's interrupt, at the
 * lowest priority, calling the engine to refill the half that has just
 * finished while the other plays (docs/DESIGN-NOTES.md, M4).
 */

#include "audio.h"
#include "WL82.h"

/* HW-44, HW-45: ADR3 holds the buffer, LEN the 32-bit words of one half;
 * CON0 bit 11 runs the output and bit 15 reads the half now playing;
 * CON2 bit 7 says a half has finished, and writing CON2 with bit 3
 * clears it. Source 11 (HW-19). */
#define CON0_RUN     (1u << 11)
#define CON0_PLAYING (1u << 15)
#define CON2_DONE    (1u << 7)
#define CON2_CLEAR   (1u << 3)
#define SRC_ALNK     11u
/* The lowest priority: below the input scan and SPI1 (1) and the tick
 * (2), which may interrupt the engine (docs/DESIGN-NOTES.md, M4). */
#define PRIO_AUDIO   0u

#define WORDS        (2u * AUDIO_FRAMES)

volatile struct sb_audio_record sb_audio __attribute__((section(".beacon.audio")));

static s32 buffer[2][WORDS] __attribute__((aligned(8)));
static audio_engine_fn engine;
/* The half the next interrupt should find free. */
static u32 expect;

static const char hex[16] = "0123456789abcdef";

/* One console line a late block, "AUDIO UNDERRUN nnnn\n" with the count
 * so far in hex (HW-25): an underrun is never silent. Only the engine's
 * interrupt writes the line, so one copy serves. */
static char line[20] = "AUDIO UNDERRUN 0000\n";

static void underrun(void)
{
    u32 n = sb_audio.underruns + 1, i;

    sb_audio.underruns = n;
    for (i = 0; i < 4; i++)
        line[18 - i] = hex[n >> 4 * i & 0xF];
    sb_console_write(line, sizeof line / 4);
}

/* Source 11: a half has finished. Refill it while the other plays. A
 * half that went by without a refill, or a refill still going when the
 * next half finished (so the one refilled had begun to play before it
 * was full, on the chip), is an underrun. */
void audio_block(void)
{
    u32 t = sb_now(), free = (JL_ALNK0->CON0 & CON0_PLAYING) ? 0u : 1u, d;

    JL_ALNK0->CON2 = CON2_CLEAR;
    if (free != expect)
        underrun();
    engine(buffer[free], AUDIO_FRAMES);
    if (JL_ALNK0->CON2 & CON2_DONE)
        underrun();
    expect = free ^ 1;
    sb_audio.blocks++;
    d = sb_now() - t;
    sb_audio.fill_last = d;
    if (d > sb_audio.fill_max)
        sb_audio.fill_max = d;
}

void audio_start(audio_engine_fn fn)
{
    engine = fn;
    expect = 0;
    sb_irq_enable(SRC_ALNK, audio_block, PRIO_AUDIO);
    JL_ALNK0->ADR3 = (u32)buffer;
    JL_ALNK0->LEN = WORDS;
    JL_ALNK0->CON2 = CON2_CLEAR;
    sb_audio.start = sb_ticks();
    sb_audio.marker = AUDIO_MARKER;
    JL_ALNK0->CON0 = CON0_RUN;
}
