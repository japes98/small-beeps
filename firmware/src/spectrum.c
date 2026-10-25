/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * The live spectrum on the patch view (M8a part 5; docs/DESIGN-NOTES.md,
 * M8a): our own FFT of the output's last SPEC_N samples, as bars on a
 * logarithmic frequency axis (the owner's answer: log frequency).
 *
 * - While the patch view shows, the engine copies each block's output
 *   into a ring (spectrum_feed); at rest it clears the ring once, so a
 *   silent output costs nothing more.
 * - Main, about 30 times a second, takes the ring, applies a Hann
 *   window and a 256-point FFT in fixed point (Q15 values, each stage
 *   halving them, so nothing overflows 32 bits and no float is needed;
 *   real input, as a 128-point complex transform and a split), and makes
 *   SPEC_BARS bars from 200 Hz to 20 kHz.
 * - Bins are 172 Hz apart (44 117.6 Hz / 256): the bars below about
 *   700 Hz are narrower than a bin, so each takes the power between its
 *   two nearest bins, in proportion; the bars above take the most
 *   powerful bin in their band. 60 dB over the bars' height.
 */

#include "sb.h"
#include "ui.h"


/* The ring, written by the engine (audio interrupt), read by main. */
volatile u32 spec_wanted;
volatile s16 spec_ring[SPEC_N];
volatile u32 spec_pos;
static volatile u32 ring_clear;

/* cos(pi/2 * i / 64), i = 0 to 64, in Q15 (made offline, by round()). */
static const s16 quarter[65] = {
    32767, 32757, 32728, 32678, 32609, 32521, 32412, 32285, 32137, 31971,
    31785, 31580, 31356, 31113, 30852, 30571, 30273, 29956, 29621, 29268,
    28898, 28510, 28105, 27683, 27245, 26790, 26319, 25832, 25329, 24811,
    24279, 23731, 23170, 22594, 22005, 21403, 20787, 20159, 19519, 18868,
    18204, 17530, 16846, 16151, 15446, 14732, 14010, 13279, 12539, 11793,
    11039, 10278, 9512, 8739, 7962, 7179, 6393, 5602, 4808, 4011,
    3212, 2410, 1608, 804, 0,
};

/* Each bar's edges in sixteenths of a bin: 200 Hz x 100^(j / 56), at
 * 44 117.6 / 256 Hz a bin (made offline, by round()). */
static const u16 edge[SPEC_BARS + 1] = {
    19, 20, 22, 24, 26, 28, 30, 33, 36, 39, 42, 46,
    50, 54, 59, 64, 69, 75, 82, 89, 96, 104, 113, 123,
    134, 145, 158, 171, 186, 202, 219, 238, 258, 280, 304, 330,
    359, 389, 423, 459, 498, 541, 587, 638, 692, 751, 816, 886,
    962, 1044, 1134, 1231, 1336, 1451, 1575, 1710, 1857,
};
_Static_assert(SPEC_BARS == 56, "the edge table is for 56 bars");

/* cos(2 pi k / 256), Q15. */
static s32 cos256(u32 k)
{
    k &= 255u;
    if (k <= 64)
        return quarter[k];
    if (k <= 128)
        return -quarter[128 - k];
    if (k <= 192)
        return -quarter[k - 128];
    return quarter[256 - k];
}

/* The engine's side: one block's output (stereo, 24-bit), while the
 * patch view shows; or, at rest, the ring cleared once. */
void spectrum_feed(const s32 *out, u32 frames)
{
    u32 n, p = spec_pos;

    if (!out) {
        if (!ring_clear) {
            for (n = 0; n < SPEC_N; n++)
                spec_ring[n] = 0;
            ring_clear = 1;
        }
        return;
    }
    for (n = 0; n < frames; n++)
        spec_ring[(p + n) & (SPEC_N - 1u)] = (s16)(out[2 * n] >> 8);
    spec_pos = p + frames;
    ring_clear = 0;
}

/* 1 once the engine has cleared the ring at rest. */
u32 spectrum_quiet(void)
{
    return ring_clear;
}

/* The transform of 256 real samples as one of 128 complex ones (the
 * even samples real, the odd imaginary), then split into the 128 bins:
 * half the butterflies of a 256-point complex transform. */
#define M (SPEC_N / 2u)
static s16 hann[SPEC_N];              /* (1 - cos) / 2, Q15 */
static s16 twr[M], twi[M];            /* e^(-i 2 pi k / 256), Q15 */
static u32 tables;
static s32 zr[M], zi[M];
static u32 power[M];

static void make_tables(void)
{
    u32 i;

    for (i = 0; i < SPEC_N; i++)
        hann[i] = (s16)((32768 - cos256(i)) >> 1);
    for (i = 0; i < M; i++) {
        twr[i] = (s16)cos256(i);
        twi[i] = (s16)-cos256(i + 192u);
    }
    tables = 1;
}

/* The transform, in three steps so that each is a part of the screen's
 * drawing within its budget (views.c): spectrum_start takes the ring and
 * windows it (0 if it holds only silence), spectrum_stages runs stages
 * first to last - 1 of the seven, spectrum_bars splits the bins and
 * makes the bars. */
u32 spectrum_start(void)
{
    u32 i, j, start = spec_pos, any = 0;

    if (!tables)
        make_tables();
    for (i = 0; i < SPEC_N; i++)
        any |= (u32)spec_ring[i];
    if (!any)
        return 0;
    for (i = 0; i < M; i++) {
        s32 a = spec_ring[(start + 2 * i) & (SPEC_N - 1u)], b = spec_ring[(start + 2 * i + 1) & (SPEC_N - 1u)];
        zr[i] = (a * hann[2 * i]) >> 15;
        zi[i] = (b * hann[2 * i + 1]) >> 15;
    }
    /* Bit-reversed order for the butterflies. */
    for (i = 1, j = 0; i < M; i++) {
        u32 bit = M >> 1;
        while (j & bit) {
            j ^= bit;
            bit >>= 1;
        }
        j |= bit;
        if (i < j) {
            s32 t = zr[i];
            zr[i] = zr[j];
            zr[j] = t;
            t = zi[i];
            zi[i] = zi[j];
            zi[j] = t;
        }
    }
    return 1;
}

/* Radix-2 butterflies, each stage halving the values (so they stay
 * within 16 bits, and their products within 32). */
void spectrum_stages(u32 first, u32 last)
{
    u32 stage, i;

    for (stage = first; stage < last; stage++) {
        u32 size = 2u << stage, half = size >> 1, step = 2u * (M / size), k;
        for (k = 0; k < half; k++) {
            s32 wr = twr[k * step], wi = twi[k * step];   /* e^(-i 2 pi k / size) */
            for (i = k; i < M; i += size) {
                u32 b = i + half;
                s32 tr = (zr[b] * wr - zi[b] * wi) >> 15, ti = (zr[b] * wi + zi[b] * wr) >> 15;
                zr[b] = (zr[i] - tr) >> 1;
                zi[b] = (zi[i] - ti) >> 1;
                zr[i] = (zr[i] + tr) >> 1;
                zi[i] = (zi[i] + ti) >> 1;
            }
        }
    }
}

/* The bins from the complex transform (X[k] = E[k] + W^k O[k], E and O
 * the even and odd samples' transforms, from Z[k] and Z[128 - k]), then
 * the bars' heights (0 to height). */
void spectrum_bars(u8 *bars, u32 height)
{
    u32 k, j, i;

    power[0] = 0;
    for (k = 1; k < M; k++) {
        s32 er = (zr[k] + zr[M - k]) >> 1, ei = (zi[k] - zi[M - k]) >> 1;
        s32 orr = (zi[k] + zi[M - k]) >> 1, oi = (zr[M - k] - zr[k]) >> 1;
        s32 tr = (orr * twr[k] - oi * twi[k]) >> 15, ti = (orr * twi[k] + oi * twr[k]) >> 15;
        s32 xr = (er + tr) >> 1, xi = (ei + ti) >> 1;
        power[k] = (u32)(xr * xr) + (u32)(xi * xi);
    }
    for (j = 0; j < SPEC_BARS; j++) {
        u32 lo = (edge[j] + 15u) >> 4, hi = edge[j + 1] >> 4, p = 0, lg, q;
        if (lo > hi) {
            u32 c = (edge[j] + edge[j + 1]) >> 1, k0 = c >> 4, f = c & 15u;
            p = (power[k0] >> 4) * (16u - f) + (k0 + 1 < M ? (power[k0 + 1] >> 4) * f : 0);
        } else {
            for (i = lo; i <= hi && i < M; i++)
                if (power[i] > p)
                    p = power[i];
        }
        /* log2 of the power in sixteenths; a full-scale sine's peak bin
         * is about 2^24 here, 60 dB below it about 2^4. */
        if (!p) {
            bars[j] = 0;
            continue;
        }
        lg = 31u - (u32)__builtin_clz(p);
        q = lg * 16u + (lg >= 4 ? (p >> (lg - 4)) & 15u : 0);
        bars[j] = (u8)(q <= 4u * 16u ? 0 : q >= 24u * 16u ? height : (q - 4u * 16u) * height / (20u * 16u));
    }
}
