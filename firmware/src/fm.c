/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * The FM engine's rendering (M5; docs/DESIGN-NOTES.md, M5, "The FM
 * engine"): the tables, the algorithms, the envelopes and one voice's
 * block, run by whichever core owns the voice. Phase modulation of sine
 * operators (Chowning 1973; PROVENANCE P-34), in fixed point: phases in
 * 2^-32 of a cycle, samples in 24 bits, gains in 2^-30, attenuations in
 * 2^-16 octaves. Floats only per block (the index limit), never per
 * sample (DESIGN-NOTES.md, M5, "built for the chip's CPU model").
 */

#include "fm.h"

/* The sine: 1024 steps a cycle and one more, 24-bit full scale, from its
 * series (as M4's), read with linear interpolation. */
#define SINE_BITS  10u
#define SINE_STEPS (1u << SINE_BITS)
static s32 sine[SINE_STEPS + 1];

/* 2^(i / 256) for i = 0 to 256, in 2^-30 (1 to 2), from the series of
 * e^(i ln 2 / 256). */
static u32 exp2_table[257];

/* A modulator's output at full scale (2^23) moves its carrier's phase by
 * 2^33, two cycles: 4 pi radians, the largest index. */
#define MOD_SHIFT   10u
/* Attenuation: 16 octaves (96.3 dB) is silence. */
#define ATT_SILENT  (16 << 16)
#define GAIN_ONE    (1 << 30)

/* Our algorithms (docs/DESIGN-NOTES.md, M5, "The algorithms", has their
 * diagrams): where each operator's output goes, operator 1 first, as the
 * index of the operator it modulates (always a lower one) or FM_TO_OUT;
 * the operator with the feedback; how many carriers. */
#define O FM_TO_OUT
const struct fm_algorithm fm_algorithms[FM_ALGORITHMS] = {
    /*  1 */ { { O, 0, 1, 2, 3, 4 }, 5, 1 },   /* one stack: 6 5 4 3 2 1 */
    /*  2 */ { { O, 0, 1, O, 3, 4 }, 5, 2 },   /* two stacks of three */
    /*  3 */ { { O, 0, O, 2, O, 4 }, 5, 3 },   /* three pairs */
    /*  4 */ { { O, 0, 1, 2, 1, 4 }, 5, 1 },   /* 6 5 and 4 3 into 2, 2 into 1 */
    /*  5 */ { { O, 0, 0, 0, 0, 0 }, 5, 1 },   /* five modulators into 1 */
    /*  6 */ { { O, O, O, 2, 3, 4 }, 5, 3 },   /* a stack of four, and 2 and 1 */
    /*  7 */ { { O, 0, 0, O, 3, 3 }, 5, 2 },   /* two branches: 3 2 into 1, 6 5 into 4 */
    /*  8 */ { { O, O, O, O, O, O }, 5, 6 },   /* six carriers */
    /*  9 */ { { O, 0, O, O, 3, 4 }, 5, 3 },   /* a stack of three, 3 alone, a pair */
    /* 10 */ { { O, 0, 0, 2, 2, 4 }, 1, 1 },   /* a tree: 6 into 5, 5 4 into 3, 3 2 into 1 */
};
#undef O

/* The carriers' sum is divided by how many of them sound (as
 * attenuation, log2 n octaves), so every algorithm and patch is about as
 * loud (fm_carrier_att). */
static const s32 carrier_att[FM_OPS + 1] = { 0, 0, 65536, 103872, 131072, 152170, 169408 };

s32 fm_carrier_att(u32 carriers)
{
    return carrier_att[carriers > FM_OPS ? FM_OPS : carriers];
}

/* a * b / 2^29, for the sine's series. */
static s32 q29(s32 a, s32 b)
{
    return (s32)((s64)a * b >> 29);
}

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

void fm_tables(void)
{
    u32 i, k;

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
    /* e^y = sum of y^k / k!, y = i ln 2 / 256 at most ln 2, in 2^-30
     * (ln 2 is 744261118): to y^12, within 2^-30. */
    for (i = 0; i <= 256; i++) {
        s32 y = (s32)((s64)744261118 * i >> 8), term = GAIN_ONE;
        s64 sum = GAIN_ONE;
        for (k = 1; k <= 12; k++) {
            term = (s32)((s64)term * y >> 30) / (s32)k;
            sum += term;
        }
        exp2_table[i] = (u32)sum;
    }
}

u32 fm_exp2_frac(u32 f)
{
    u32 i = f >> 8, r = f & 0xFFu, a;

    if (i >= 256)
        return exp2_table[256];
    a = exp2_table[i];
    return a + (u32)(((u64)(exp2_table[i + 1] - a) * r) >> 8);
}

s32 fm_exp2_neg(s32 att)
{
    u32 i, f;

    if (att <= 0)
        return GAIN_ONE;
    i = (u32)att >> 16;
    f = (u32)att & 0xFFFFu;
    if (i >= 30)
        return 0;
    /* 2^-f = 2^(1 - f) / 2. */
    return (s32)((f ? fm_exp2_frac(65536 - f) >> 1 : (u32)GAIN_ONE) >> i);
}

/* The attenuation of a gain (2^-30, more than 0): -log2(gain) octaves,
 * the inverse of fm_exp2_neg, by bisection (only when a key is released
 * during an attack). */
s32 fm_att_of(s32 gain)
{
    s32 k = 0, lo = 0, hi = 65536;

    if (gain <= 0)
        return ATT_SILENT;
    if (gain >= GAIN_ONE)
        return 0;
    while (gain < GAIN_ONE) {
        gain <<= 1;
        k++;
    }
    /* gain is now in [2^30, 2^31): find f with 2^(f / 65536) = gain. */
    while (hi - lo > 1) {
        s32 mid = (lo + hi) / 2;
        if (fm_exp2_frac((u32)mid) <= (u32)gain)
            lo = mid;
        else
            hi = mid;
    }
    return (k << 16) - lo;
}

/* The phase step of MIDI note 0 (8.1758 Hz) at the output's rate, in
 * 2^-8: 8.1758 / (24 MHz / 544) x 2^32 x 2^8, computed offline. */
#define INC_REF_Q8 203759415u

u32 fm_pitch_inc(s32 pitch)
{
    /* pitch / 4096 semitones is pitch / 49152 octaves: in 2^-16 octaves
     * that is pitch x 4 / 3. Kept within 0 and note 135 (19.9 kHz). */
    u32 oct;

    if (pitch < 0)
        pitch = 0;
    if (pitch > 135 * 4096)
        pitch = 135 * 4096;
    oct = (u32)pitch * 4u / 3u;
    return (u32)(((u64)INC_REF_Q8 * fm_exp2_frac(oct & 0xFFFFu)) >> (38 - (oct >> 16)));
}

/* One sample of the sine at a phase. */
static inline __attribute__((always_inline)) s32 osc(u32 phase)
{
    u32 i = phase >> (32 - SINE_BITS), f = phase >> (17 - SINE_BITS) & 0x7FFFu;
    s32 a = sine[i];

    return a + ((sine[i + 1] - a) * (s32)f >> 15);
}

s32 fm_sine(u32 phase)
{
    return osc(phase);
}

/* One operator's block: its phase moved on by inc each sample, modulated
 * by in[] (if mod) and by its own last two outputs' mean (if feed, with
 * the multiplier going from fb0 to fb1 over the block, in 2^-8 of a
 * phase shift), its gain going from g0 by dg a sample; its output stored
 * into dst[] or added to it. The compiler makes one loop of each kind. */
static inline __attribute__((always_inline)) void op_block(struct fm_op *o, const s32 *in, s32 *dst,
                                                           s32 g0, s32 dg, s32 fb0, s32 dfb,
                                                           const int mod, const int feed, const int add)
{
    u32 ph = o->phase, inc = o->inc, n;
    s32 g = g0, y1 = o->y1, y2 = o->y2, fb = fb0;

    for (n = 0; n < AUDIO_FRAMES; n++) {
        u32 p = ph;
        s32 y;
        if (mod)
            p += (u32)in[n] << MOD_SHIFT;
        if (feed) {
            p += (u32)(s32)(((s64)((y1 + y2) >> 1) * fb) >> 8);
            fb += dfb;
        }
        y = (s32)((s64)osc(p) * g >> 30);
        g += dg;
        if (feed) {
            y2 = y1;
            y1 = y;
        }
        dst[n] = add ? dst[n] + y : y;
        ph += inc;
    }
    o->phase = ph;
    o->y1 = y1;
    o->y2 = y2;
}

static void op_dispatch(struct fm_op *o, const s32 *in, s32 *dst, s32 g0, s32 dg, s32 fb0, s32 dfb,
                        u32 kind)
{
    switch (kind) {
    case 0: op_block(o, in, dst, g0, dg, fb0, dfb, 0, 0, 0); break;
    case 1: op_block(o, in, dst, g0, dg, fb0, dfb, 0, 0, 1); break;
    case 2: op_block(o, in, dst, g0, dg, fb0, dfb, 0, 1, 0); break;
    case 3: op_block(o, in, dst, g0, dg, fb0, dfb, 0, 1, 1); break;
    case 4: op_block(o, in, dst, g0, dg, fb0, dfb, 1, 0, 0); break;
    case 5: op_block(o, in, dst, g0, dg, fb0, dfb, 1, 0, 1); break;
    case 6: op_block(o, in, dst, g0, dg, fb0, dfb, 1, 1, 0); break;
    default: op_block(o, in, dst, g0, dg, fb0, dfb, 1, 1, 1); break;
    }
}

/* d / step in 2^-16, for 0 <= d <= step: in 32 bits, both shifted down
 * until step fits 15. */
static s32 share(s32 d, s32 step)
{
    while (step >= 1 << 15) {
        step >>= 1;
        d >>= 1;
    }
    return step ? (d << 16) / step : 0;
}

/* One operator's envelope, a block on: its gain at the end of this block
 * (before the operator's own level), 2^-30. The attack rises linearly in
 * gain; the decays and the release move linearly in attenuation, so they
 * fall exponentially, as struck and plucked things do (DESIGN-NOTES.md,
 * M5, "The envelopes"). A stage that ends within the block hands what is
 * left of the block to the next, so no stage loses time to the blocks. */
static s32 envelope(struct fm_op *o)
{
    s32 left = 1 << 16;   /* the share of the block still to move, 2^-16 */

    for (;;) {
        s32 step, to, d, move;
        if (o->stage == ENV_ATTACK) {
            s32 peak = fm_exp2_neg(o->target[0]);
            step = o->step[0];
            move = (s32)(((s64)step * left) >> 16);
            d = peak - o->lin;
            if (move < d) {
                o->lin += move;
                return o->lin;
            }
            left -= share(d > 0 ? d : 0, step);
            o->lin = peak;
            o->att = o->target[0];
            o->stage = ENV_DECAY1;
            continue;
        }
        if (o->stage == ENV_HOLD)
            return fm_exp2_neg(o->att);
        if (o->stage > ENV_RELEASE)
            return 0;
        to = o->stage == ENV_RELEASE ? ATT_SILENT : o->target[o->stage];
        step = o->step[o->stage == ENV_RELEASE ? 3 : o->stage];
        move = (s32)(((s64)step * left) >> 16);
        d = to > o->att ? to - o->att : o->att - to;
        if (move < d) {
            o->att += to > o->att ? move : -move;
            return fm_exp2_neg(o->att);
        }
        left -= share(d, step);
        o->att = to;
        o->stage = o->stage == ENV_RELEASE ? ENV_OFF : o->stage + 1;
        if (o->stage == ENV_OFF)
            return 0;
    }
}

void fm_render(struct fm_voice *v, s32 *mix, s32 (*buf)[AUDIO_FRAMES])
{
    /* buf[i] is operator i's input, summed from its modulators, and
     * buf[FM_OPS] the carriers' sum; written says which already hold this
     * block's first writer (so the first stores and the rest add). */
    const struct fm_algorithm *a = &fm_algorithms[v->algorithm];
    u32 written = 0, sounding = 0, n;
    int i;

    for (i = FM_OPS - 1; i >= 0; i--) {
        struct fm_op *o = &v->op[i];
        u32 dest = a->dest[i], to = dest == FM_TO_OUT ? FM_OPS : dest, kind = 0;
        s32 e = envelope(o), target, dg, fb0 = 0, dfb = 0;

        if (o->stage != ENV_OFF && dest == FM_TO_OUT)
            sounding = 1;
        /* The operator's own level, its velocity and, for a modulator,
         * KNOB3's depth; a carrier its share of the output. */
        target = (s32)(((s64)e * fm_exp2_neg(o->fixed_att + (dest == FM_TO_OUT ? v->out_att : v->mod_att)))
                       >> 30);
        if (o->inc >= 0x80000000u) {
            target = 0;          /* above half the rate: silent, never aliased */
        } else if (dest != FM_TO_OUT && o->inc) {
            /* The index limit (DESIGN-NOTES.md, M5, "Aliasing"): by
             * Carson's rule a modulator of frequency fm at index I spreads
             * its carrier fc over about fc +- (I + 1) fm; keep that below
             * half the rate. */
            float room = (2147483648.0f - (float)v->op[dest].inc) / (float)o->inc - 1.0f;
            float cap = room * (1073741824.0f / 12.566371f);
            if (cap < (float)target)
                target = cap > 0.0f ? (s32)cap : 0;
        }
        dg = (target - o->gain) >> 6;
        if ((u32)i == a->feedback_op) {
            fb0 = v->fb_now;
            dfb = (v->fb_target - v->fb_now) >> 6;
        }
        if (!o->gain && !target) {
            o->phase += o->inc * AUDIO_FRAMES;   /* silent: keep its phase */
            o->y1 = o->y2 = 0;
            continue;
        }
        kind = (written >> i & 1) ? 4 : 0;
        kind |= (u32)i == a->feedback_op && (fb0 || dfb) ? 2 : 0;
        kind |= written >> to & 1;
        op_dispatch(o, buf[i], buf[to], o->gain, dg, fb0, dfb, kind);
        o->gain += dg * (s32)AUDIO_FRAMES;
        written |= 1u << to;
    }
    v->fb_now += ((v->fb_target - v->fb_now) >> 6) * (s32)AUDIO_FRAMES;
    v->silent = !sounding;
    if (!(written >> FM_OPS & 1))
        return;
    /* A voice at full level is a quarter of full scale: -12 dBFS. A
     * stolen voice fades to nothing over this block. */
    if (v->fade) {
        s32 g = 1 << 16;
        for (n = 0; n < AUDIO_FRAMES; n++, g -= 1 << 10)
            mix[n] += (s32)(((s64)(buf[FM_OPS][n] >> 2) * g) >> 16);
        v->fade_done = 1;
        return;
    }
    for (n = 0; n < AUDIO_FRAMES; n++)
        mix[n] += buf[FM_OPS][n] >> 2;
}
