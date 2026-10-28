/* SPDX-License-Identifier: MIT */
/* SPDX-FileCopyrightText: 2026 japes98 */
/* The toolchain audit (session spec-isa-audit): C for which the pinned
   compiler, with the firmware's CPU flags (build.sh), emits instruction
   forms fwtest 0.9.0 could not run, or ran wrongly:
     floorf, ceilf, truncf     r = ftof(r) (floor), (ceil), (trunc)
     __fp16 stores and loads   r.l = ftof(r), r = ftof(r.l)
     *p <<= n, >>= n           [r+k] <<= r, >>= r, >>>= r
     *p &= ~m                  [r+k] &= ~r (offsets below the base too)
     p[1000], 64-bit elements  rH_rL = d[r+r<<3] (0.9.0 left the index unscaled)
     __builtin_pi32v2_zcmp     r = zcmp(r)
   build.sh fails if the disassembly no longer has them. The images keep
   only .text, so every input is written at run time, at fixed addresses.
   OUT(k) get the results; tests/fwtest.rs (forms_the_compiler_emits) has
   the values. */
#include "board.h"

typedef unsigned long long u64;
typedef __fp16 half;

#define FIN ((volatile float *)0x01c00400u)
#define WORD ((volatile u32 *)0x01c00440u)
#define HBUF ((volatile half *)0x01c00480u)
#define ZIN ((volatile int *)0x01c004c0u)
/* 2001 doublewords, the middle one at MID */
#define DBL ((u64 *)0x01c10000u)
#define MID (DBL + 1000)

__attribute__((noinline)) float fl(float x) { return __builtin_floorf(x); }
__attribute__((noinline)) float ce(float x) { return __builtin_ceilf(x); }
__attribute__((noinline)) float tr(float x) { return __builtin_truncf(x); }
__attribute__((noinline)) void to_half(volatile half *p, float x) { *p = x; }
__attribute__((noinline)) float from_half(volatile half *p) { return *p; }
__attribute__((noinline)) void shl(volatile u32 *p, int n) { p[-1] <<= n; }
__attribute__((noinline)) void shr(volatile u32 *p, int n) { p[1] >>= n; }
__attribute__((noinline)) void sar(volatile int *p, int n) { p[2] >>= n; }
__attribute__((noinline)) void andnot(volatile u32 *p, u32 m) { p[-2] &= ~m; }
/* p[1000] and p[-1000]: the index in a register, scaled by 8 */
__attribute__((noinline)) u64 sum(const u64 *p, int i)
{
    return p[i] + p[i + 1] + p[-1] + p[100] + p[1000] + p[-1000];
}
__attribute__((noinline)) int sign(int x) { return __builtin_pi32v2_zcmp(x); }

static u32 bits(float f)
{
    union { float f; u32 u; } v = { f };
    return v.u;
}

int main(void)
{
    FIN[0] = -2.5f;
    FIN[1] = 7.75f;
    FIN[2] = -0.5f;
    OUT(0) = bits(fl(FIN[0]));
    OUT(1) = bits(ce(FIN[0]));
    OUT(2) = bits(tr(FIN[0]));
    OUT(3) = bits(fl(FIN[1]));
    OUT(4) = bits(ce(FIN[2]));
    *(volatile u32 *)HBUF = 0;
    to_half(&HBUF[0], 0.1f);
    to_half(&HBUF[1], 65520.0f);
    OUT(5) = *(volatile u32 *)HBUF;
    OUT(6) = bits(from_half(&HBUF[0]));
    WORD[3] = 0x00000f0fu;
    WORD[5] = 0x80000000u;
    WORD[6] = 0x80000000u;
    WORD[2] = 0x0000ffffu;
    shl(&WORD[4], 4);
    shr(&WORD[4], 31);
    sar((volatile int *)&WORD[4], 1);
    andnot(&WORD[4], 0x0ff0u);
    OUT(7) = WORD[3];
    OUT(8) = WORD[5];
    OUT(9) = WORD[6];
    OUT(10) = WORD[2];
    for (int k = 0; k <= 2000; k++)
        ((volatile u64 *)DBL)[k] = 0;
    ((volatile u64 *)MID)[3] = 0x0000000100000001ull;
    ((volatile u64 *)MID)[4] = 0x0000000200000002ull;
    ((volatile u64 *)MID)[-1] = 0x0000000400000004ull;
    ((volatile u64 *)MID)[100] = 0x0000000800000008ull;
    ((volatile u64 *)MID)[1000] = 0x0000001000000010ull;
    ((volatile u64 *)MID)[-1000] = 0x0000002000000020ull;
    u64 s = sum(MID, 3);
    OUT(11) = (u32)s;
    OUT(12) = (u32)(s >> 32);
    ZIN[0] = 5;
    ZIN[1] = 0;
    ZIN[2] = -7;
    OUT(13) = (u32)sign(ZIN[0]);
    OUT(14) = (u32)sign(ZIN[1]);
    OUT(15) = (u32)sign(ZIN[2]);
    return 0;
}
