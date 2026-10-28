/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * Single-precision floating point in software, written for the Plaits demo
 * (docs/DESIGN-NOTES.md, M4b); since clean-1027 (BR-4) part of the
 * platform's runtime (firmware/runtime/), linked only into an image that
 * calls them, as code built without the float instructions does. The compiler turns every float operation
 * into a call to one of these when there is no floating-point unit; we
 * don't link the toolchain's own (docs/TOOLCHAIN.md), so these are ours,
 * written from IEEE 754's definition of binary32:
 *
 * - add, subtract, multiply, divide and square root are correctly rounded
 *   to nearest, ties to even, with subnormals, signed zeros, infinities
 *   and NaN (any NaN result is the quiet NaN 0x7FC00000);
 * - comparisons follow the usual soft-float return conventions, so that a
 *   NaN makes every ordered comparison false;
 * - float to integer truncates toward zero and saturates out of range (NaN
 *   gives 0), so a wild value never turns into an arbitrary one;
 * - invalid operations, overflows and bad conversions are counted in
 *   softfloat_flags, IEEE's exception flags as counts, so the bench can
 *   show Plaits made no NaN and no infinity.
 *
 * Only integer operations are used inside (a float operator here would
 * call itself), and no 64-bit shift or division, which would need more
 * helpers: products are split into 32-bit halves by hand. The image test
 * PLAITS_TEST_SOFTFLOAT checks every routine bit for bit against a
 * reference (tools/plaits-bench.py).
 */

#include "sb.h"

typedef union { float f; u32 u; } bits;

/* IEEE 754's exception flags, as counts (bench.c reports them): an
 * invalid operation (a NaN made from numbers: inf - inf, 0 x inf, 0 / 0,
 * inf / inf, the root of a negative number), an overflow to infinity,
 * and a float to integer conversion out of range or of a NaN. */
volatile u32 softfloat_flags[3];
#define FLAG_INVALID   0
#define FLAG_OVERFLOW  1
#define FLAG_CONVERT   2

static u32 invalid(void)
{
    softfloat_flags[FLAG_INVALID]++;
    return 0x7FC00000u;
}

#define SIGN      0x80000000u
#define EXP_MASK  0x7F800000u
#define MANT_MASK 0x007FFFFFu
#define HIDDEN    0x00800000u
#define QNAN      0x7FC00000u
#define INF       0x7F800000u

static inline u32 to_u(float f) { bits b; b.f = f; return b.u; }
static inline float to_f(u32 u) { bits b; b.u = u; return b.f; }

static inline int is_nan(u32 a) { return (a & ~SIGN) > INF; }

/* x >> n, with every bit shifted out ORed into bit 0 (the sticky bit). */
static inline u32 shift_sticky(u32 x, u32 n)
{
    if (n == 0)
        return x;
    if (n >= 32)
        return x != 0;
    return (x >> n) | ((x << (32 - n)) != 0);
}

/* Rounds and packs a result. x is the significand with three extra bits
 * below the 24 that are kept (guard, round, sticky), its leading bit at
 * bit 26 for a normal result; e is the biased exponent that leading bit
 * would have. Handles underflow to subnormal or zero and overflow to
 * infinity. */
static u32 round_pack(u32 sign, s32 e, u32 x)
{
    u32 rem;

    if (e <= 0) {
        /* Below the normal range: the subnormals have exponent field 0
         * and the scale of exponent 1. */
        x = shift_sticky(x, (u32)(1 - e));
        e = 1;
    }
    rem = x & 7u;
    x >>= 3;
    if (rem > 4u || (rem == 4u && (x & 1u))) {
        x++;
        if (x == (HIDDEN << 1)) {
            x >>= 1;
            e++;
        }
    }
    if (e >= 255) {
        softfloat_flags[FLAG_OVERFLOW]++;
        return sign | INF;
    }
    if (!(x & HIDDEN))
        e = 0;
    return sign | ((u32)e << 23) | (x & MANT_MASK);
}

/* The position of the highest set bit of x (x not 0). */
static inline u32 top_bit(u32 x)
{
    u32 n = 0;

    while (x >> 1) {
        x >>= 1;
        n++;
    }
    return n;
}

/* A significand with its hidden bit, and the matching exponent: a
 * subnormal is normalised, so that the hidden bit (bit 23) is set and the
 * exponent may go to 0 or below. a is finite and not zero. */
static inline void unpack_norm(u32 a, s32 *e, u32 *m)
{
    *e = (s32)((a >> 23) & 0xFFu);
    *m = a & MANT_MASK;
    if (*e) {
        *m |= HIDDEN;
    } else {
        u32 shift = 23u - top_bit(*m);
        *m <<= shift;
        *e = 1 - (s32)shift;
    }
}

static u32 add_bits(u32 a, u32 b)
{
    u32 sa = a & SIGN, sb = b & SIGN, ma, mb, x;
    s32 ea, eb, e, d;

    if (is_nan(a) || is_nan(b))
        return QNAN;
    if ((a & ~SIGN) == INF) {
        if ((b & ~SIGN) == INF && sa != sb)
            return invalid();
        return a;
    }
    if ((b & ~SIGN) == INF)
        return b;
    if (!(a & ~SIGN)) {
        if (!(b & ~SIGN))
            return sa & sb;       /* -0 + -0 is -0; any other pair of zeros +0 */
        return b;
    }
    if (!(b & ~SIGN))
        return a;
    /* Subnormals keep exponent 1 and no hidden bit, so that both sides
     * have the same scale per exponent. */
    ea = (s32)((a >> 23) & 0xFFu);
    eb = (s32)((b >> 23) & 0xFFu);
    ma = a & MANT_MASK;
    mb = b & MANT_MASK;
    if (ea) ma |= HIDDEN; else ea = 1;
    if (eb) mb |= HIDDEN; else eb = 1;
    if (ea < eb || (ea == eb && ma < mb)) {
        u32 t;
        s32 te;

        t = ma; ma = mb; mb = t;
        te = ea; ea = eb; eb = te;
        t = sa; sa = sb; sb = t;
    }
    d = ea - eb;
    ma <<= 3;
    mb = shift_sticky(mb << 3, (u32)d);
    e = ea;
    if (sa == sb) {
        x = ma + mb;
        if (x & (1u << 27)) {
            x = shift_sticky(x, 1);
            e++;
        }
    } else {
        x = ma - mb;
        if (!x)
            return 0;             /* exact cancellation is +0 */
        while (!(x & (1u << 26)) && e > 1) {
            x <<= 1;
            e--;
        }
    }
    return round_pack(sa, e, x);
}

float __addsf3(float a, float b)
{
    return to_f(add_bits(to_u(a), to_u(b)));
}

float __subsf3(float a, float b)
{
    return to_f(add_bits(to_u(a), to_u(b) ^ SIGN));
}

/* hi:lo = a * b, from 16-bit halves, so no 64-bit helper is needed. */
static inline void mul32(u32 a, u32 b, u32 *hi, u32 *lo)
{
    u32 al = a & 0xFFFFu, ah = a >> 16, bl = b & 0xFFFFu, bh = b >> 16;
    u32 ll = al * bl, lh = al * bh, hl = ah * bl, hh = ah * bh;
    u32 mid = (ll >> 16) + (lh & 0xFFFFu) + (hl & 0xFFFFu);

    *lo = (ll & 0xFFFFu) | (mid << 16);
    *hi = hh + (lh >> 16) + (hl >> 16) + (mid >> 16);
}

float __mulsf3(float fa, float fb)
{
    u32 a = to_u(fa), b = to_u(fb), sign = (a ^ b) & SIGN, ma, mb, hi, lo, x;
    s32 ea, eb, e;

    if (is_nan(a) || is_nan(b))
        return to_f(QNAN);
    if ((a & ~SIGN) == INF || (b & ~SIGN) == INF) {
        if (!(a & ~SIGN) || !(b & ~SIGN))
            return to_f(invalid());   /* zero times infinity */
        return to_f(sign | INF);
    }
    if (!(a & ~SIGN) || !(b & ~SIGN))
        return to_f(sign);
    unpack_norm(a, &ea, &ma);
    unpack_norm(b, &eb, &mb);
    e = ea + eb - 127;
    /* The product of two 24-bit significands: 47 or 48 bits. Keep 27,
     * the leading one at bit 26, and fold the rest into the sticky bit. */
    mul32(ma, mb, &hi, &lo);
    if (hi & (1u << 15)) {
        x = (hi << 11) | (lo >> 21);
        x |= (lo & 0x1FFFFFu) != 0;
        e++;
    } else {
        x = (hi << 12) | (lo >> 20);
        x |= (lo & 0xFFFFFu) != 0;
    }
    return to_f(round_pack(sign, e, x));
}

float __divsf3(float fa, float fb)
{
    u32 a = to_u(fa), b = to_u(fb), sign = (a ^ b) & SIGN, ma, mb, q = 0, r;
    s32 ea, eb, e, i;

    if (is_nan(a) || is_nan(b))
        return to_f(QNAN);
    if ((a & ~SIGN) == INF) {
        if ((b & ~SIGN) == INF)
            return to_f(invalid());
        return to_f(sign | INF);
    }
    if ((b & ~SIGN) == INF)
        return to_f(sign);
    if (!(b & ~SIGN)) {
        if (!(a & ~SIGN))
            return to_f(invalid());   /* zero over zero */
        return to_f(sign | INF);
    }
    if (!(a & ~SIGN))
        return to_f(sign);
    unpack_norm(a, &ea, &ma);
    unpack_norm(b, &eb, &mb);
    e = ea - eb + 127;
    if (ma < mb) {
        ma <<= 1;
        e--;
    }
    /* ma / mb is in [1, 2): 27 quotient bits by long division, the first
     * always 1, then the remainder as the sticky bit. */
    r = ma;
    for (i = 0; i < 27; i++) {
        q <<= 1;
        if (r >= mb) {
            r -= mb;
            q |= 1u;
        }
        r <<= 1;
    }
    q |= r != 0;
    return to_f(round_pack(sign, e, q));
}

float sqrtf(float fa)
{
    u32 a = to_u(fa), m, hi, rem = 0, root = 0, t;
    s32 e, i;

    if (is_nan(a))
        return to_f(QNAN);
    if (!(a & ~SIGN))
        return fa;                /* sqrt(-0) is -0 */
    if (a & SIGN)
        return to_f(invalid());
    if (a == INF)
        return fa;
    unpack_norm(a, &e, &m);
    e -= 127;
    /* sqrt(m * 2^e / 2^23): with e even, the root of m * 2^29 has its
     * leading bit at bit 26; with e odd, take m * 2^30 and e - 1. That
     * radicand is 56 bits: 28 pairs, high to low. It is held shifted up
     * by 8 so that its first pair is the top of hi; everything below hi
     * is zero. */
    if (e & 1) {
        hi = m << 6;
        e -= 1;
    } else {
        hi = m << 5;
    }
    for (i = 0; i < 28; i++) {
        rem = (rem << 2) | (hi >> 30);
        hi <<= 2;
        t = (root << 2) | 1u;
        if (rem >= t) {
            rem -= t;
            root = (root << 1) | 1u;
        } else {
            root <<= 1;
        }
    }
    root |= rem != 0;
    return to_f(round_pack(0, e / 2 + 127, root));
}

/* Integers to float, rounded to nearest. */
static u32 from_uint(u32 sign, u32 v)
{
    u32 p;

    if (!v)
        return 0;
    p = top_bit(v);
    if (p <= 26)
        return round_pack(sign, 127 + (s32)p, v << (26 - p));
    return round_pack(sign, 127 + (s32)p, shift_sticky(v, p - 26));
}

float __floatsisf(int i)
{
    return i < 0 ? to_f(from_uint(SIGN, 0u - (u32)i)) : to_f(from_uint(0, (u32)i));
}

float __floatunsisf(unsigned int u)
{
    return to_f(from_uint(0, u));
}

/* Float to integer, toward zero, saturating; NaN gives 0. */
int __fixsfsi(float fa)
{
    u32 a = to_u(fa), m;
    s32 e;

    if (is_nan(a)) {
        softfloat_flags[FLAG_CONVERT]++;
        return 0;
    }
    e = (s32)((a >> 23) & 0xFFu) - 127;
    if (e < 0)
        return 0;
    if (e >= 31) {
        if (a != 0xCF000000u)     /* -2^31 itself fits */
            softfloat_flags[FLAG_CONVERT]++;
        return (a & SIGN) ? (int)0x80000000u : 0x7FFFFFFF;
    }
    m = (a & MANT_MASK) | HIDDEN;
    m = e >= 23 ? m << (e - 23) : m >> (23 - e);
    return (a & SIGN) ? -(int)m : (int)m;
}

unsigned int __fixunssfsi(float fa)
{
    u32 a = to_u(fa), m;
    s32 e;

    if (is_nan(a) || ((a & SIGN) && (a & ~SIGN) >= 0x3F800000u)) {
        softfloat_flags[FLAG_CONVERT]++;   /* NaN, or -1 or below */
        return 0;
    }
    if (a & SIGN)
        return 0;
    e = (s32)((a >> 23) & 0xFFu) - 127;
    if (e < 0)
        return 0;
    if (e >= 32) {
        softfloat_flags[FLAG_CONVERT]++;
        return 0xFFFFFFFFu;
    }
    m = (a & MANT_MASK) | HIDDEN;
    return e >= 23 ? m << (e - 23) : m >> (23 - e);
}

/* -1, 0 or 1 for a < b, a == b, a > b; 2 if either is NaN. */
static int compare(u32 a, u32 b)
{
    if (is_nan(a) || is_nan(b))
        return 2;
    if (!((a | b) & ~SIGN))
        return 0;                 /* +0 == -0 */
    if ((a ^ b) & SIGN)
        return (a & SIGN) ? -1 : 1;
    if (a == b)
        return 0;
    if (a & SIGN)
        return a > b ? -1 : 1;
    return a < b ? -1 : 1;
}

/* The soft-float convention: each returns a value whose sign answers its
 * comparison, and a NaN gives the answer that makes it false. */
int __eqsf2(float a, float b) { int c = compare(to_u(a), to_u(b)); return c == 2 ? 1 : c != 0; }
int __nesf2(float a, float b) { int c = compare(to_u(a), to_u(b)); return c == 2 ? 1 : c != 0; }
int __ltsf2(float a, float b) { int c = compare(to_u(a), to_u(b)); return c == 2 ? 1 : c; }
int __lesf2(float a, float b) { int c = compare(to_u(a), to_u(b)); return c == 2 ? 1 : c; }
int __gtsf2(float a, float b) { int c = compare(to_u(a), to_u(b)); return c == 2 ? -1 : c; }
int __gesf2(float a, float b) { int c = compare(to_u(a), to_u(b)); return c == 2 ? -1 : c; }
int __unordsf2(float a, float b) { return compare(to_u(a), to_u(b)) == 2; }
