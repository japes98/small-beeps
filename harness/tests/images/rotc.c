/* SPDX-License-Identifier: MIT */
/* SPDX-FileCopyrightText: 2026 japes98 */
/* Rotates as the compiler emits them. Built with the firmware's CPU flags
   (build.sh), which make clang compile rotl() to `r1 = 0x20 - r1` and
   `r0 = r0 <> r1`, rotl_m() (defined for every amount) to `r1 = 0x0 - r1`,
   `r1 = r1 & 0x1F` and the same rotate, and rotr7() to the rotate by a
   constant `r0 = r0 <> 7`; build.sh fails if the disassembly no longer
   has a rotate by a register. OUT(4 + s) = rotl(X, s), s = 1..31;
   OUT(36 + s) = rotl_m(X, s), s = 0..31; OUT(68) = rotr7(X).
   OUT(0), X = 0x12345678, passes the value, so nothing is folded. */
#include "board.h"

u32 rotl(u32 x, u32 s);
u32 rotl_m(u32 x, u32 s);
u32 rotr7(u32 x);

__attribute__((noinline)) u32 rotl(u32 x, u32 s)
{
    return (x << s) | (x >> (32u - s));
}

__attribute__((noinline)) u32 rotl_m(u32 x, u32 s)
{
    return (x << (s & 31u)) | (x >> (-s & 31u));
}

__attribute__((noinline)) u32 rotr7(u32 x)
{
    return (x >> 7) | (x << 25);
}

int main(void)
{
    OUT(0) = 0x12345678u;
    for (u32 s = 1u; s < 32u; s++) {
        OUT(4u + s) = rotl(OUT(0), s);
    }
    for (u32 s = 0u; s < 32u; s++) {
        OUT(36u + s) = rotl_m(OUT(0), s);
    }
    OUT(68) = rotr7(OUT(0));
    return 0;
}
