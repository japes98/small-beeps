/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * The soft-float test (M4b, docs/DESIGN-NOTES.md), run first by the bench
 * image (bench.c): it runs every routine of runtime/softfloat.c
 * through C's own operators, as Plaits' code calls them, on operands from
 * a fixed generator (special values, then random patterns of four kinds:
 * any bits, the same exponent, small and subnormal numbers, near-equal
 * pairs), and prints a hash of each operation's results to the debug
 * console. tools/plaits-bench.py runs the same generator, works each
 * result out exactly with rational arithmetic, rounds it to nearest even,
 * and checks the hashes: a match is every result bit for bit.
 */

#if defined(PLAITS_BENCH)

#include "sb.h"

#define CASES  20000u

typedef union { float f; u32 u; } bits;

static u32 seed = 0x5EEDF10Au;

static u32 next(void)
{
    seed = seed * 1664525u + 1013904223u;
    return seed;
}

static const u32 special[] = {
    0x00000000u, 0x80000000u, 0x7F800000u, 0xFF800000u, 0x7FC00000u, 0x00000001u,
    0x80000001u, 0x007FFFFFu, 0x00800000u, 0x7F7FFFFFu, 0xFF7FFFFFu, 0x3F800000u,
    0xBF800000u, 0x3F800001u, 0x4B000000u, 0x4EFFFFFFu, 0x4F000000u, 0xCF000000u,
    0x4F800000u, 0x00400000u, 0x33800000u, 0x34000000u,
};
#define SPECIALS (sizeof special / sizeof special[0])

/* Operand pair i: the same sequence as tools/plaits-bench.py's. */
static void operands(u32 i, u32 *a, u32 *b)
{
    if (i < SPECIALS * SPECIALS) {
        *a = special[i / SPECIALS];
        *b = special[i % SPECIALS];
        return;
    }
    *a = next();
    switch (i & 3u) {
    case 0: *b = next(); break;
    case 1: *b = (*a & 0xFF800000u) | (next() & 0x007FFFFFu); *b ^= next() & 0x80000000u; break;
    case 2: *a &= 0x80FFFFFFu; *b = next() & 0x80FFFFFFu; break;
    default: *b = *a + (next() & 3u) - 1u; break;
    }
}

#define OPS 15
static u32 hash[OPS];

static void mix(int op, u32 v)
{
    hash[op] = (hash[op] ^ v) * 16777619u;
}

static void put_hex(char *p, u32 v)
{
    static const char hex[] = "0123456789abcdef";
    int i;

    for (i = 0; i < 8; i++)
        p[i] = hex[(v >> (28 - 4 * i)) & 15u];
}

void plaits_test_softfloat(void)
{
    char out[16];
    u32 i;
    int op;

    for (op = 0; op < OPS; op++)
        hash[op] = 2166136261u;
    for (i = 0; i < CASES; i++) {
        bits a, b, r;
        u32 x, y;

        operands(i, &x, &y);
        a.u = x;
        b.u = y;
        r.f = a.f + b.f; mix(0, r.u);
        r.f = a.f - b.f; mix(1, r.u);
        r.f = a.f * b.f; mix(2, r.u);
        r.f = a.f / b.f; mix(3, r.u);
        r.f = __builtin_sqrtf(a.f); mix(4, r.u);
        r.f = (float)(int)x; mix(5, r.u);
        r.f = (float)x; mix(6, r.u);
        mix(7, (u32)(int)a.f);
        mix(8, (u32)a.f);
        mix(9, a.f < b.f);
        mix(10, a.f <= b.f);
        mix(11, a.f > b.f);
        mix(12, a.f >= b.f);
        mix(13, a.f == b.f);
        mix(14, a.f != b.f);
    }
    /* "SFT nn hhhhhhhh\n": 16 bytes a line. */
    for (op = 0; op < OPS; op++) {
        out[0] = 'S'; out[1] = 'F'; out[2] = 'T'; out[3] = ' ';
        out[4] = (char)('a' + op); out[5] = ' ';
        put_hex(out + 6, hash[op]);
        out[14] = ' ';
        out[15] = '\n';
        sb_console_write(out, 4);
    }
}

#endif
