/* SPDX-License-Identifier: MIT */
/* SPDX-FileCopyrightText: 2026 japes98 */
/* Block moves below a base, as the compiler emits them (SR-7). Built with
   the firmware's CPU flags (build.sh), which make clang load p[-2] and
   p[-1] in below2() with one `{rA, r0} = [-r0]`, and store two of down3()'s
   three words a pass with one `[-rN] = {rA, rB}`; build.sh fails if the
   disassembly no longer has both. SRC holds 0xA5000000 + i in word i.
   OUT(0) to OUT(2): below2(SRC + 8, o, 0x100)'s result, o[0] and o[1];
   OUT(3): down3(DST + 12, 0x10, 1, 2)'s result; DST(6) to DST(11) its
   stores. OUT(4) to OUT(6) pass the arguments, so the calls are not
   specialised. */
#include "board.h"

#define SRC ((u32 *)0x01c01000u)
#define DST ((u32 *)0x01c01200u)

u32 below2(const u32 *p, u32 *o, u32 x);
u32 *down3(u32 *p, u32 a, u32 b, int n);

__attribute__((noinline)) u32 below2(const u32 *p, u32 *o, u32 x)
{
    u32 v0 = p[-1];
    u32 v1 = p[-2];
    o[0] = (v0 * 3u) ^ (v1 * 5u);
    o[1] = x + v1;
    return v0 + x;
}

__attribute__((noinline)) u32 *down3(u32 *p, u32 a, u32 b, int n)
{
    while (n--) {
        *--p = a * 3u + b;
        *--p = a * 5u + b;
        *--p = a * 7u + b;
    }
    return p;
}

int main(void)
{
    for (u32 i = 0u; i < 16u; i++) {
        SRC[i] = 0xa5000000u + i;
    }
    OUT(4) = (u32)(SRC + 8);
    OUT(5) = (u32)(DST + 12);
    OUT(6) = 2u;
    u32 o[2];
    OUT(0) = below2((const u32 *)OUT(4), o, 0x100u);
    OUT(1) = o[0];
    OUT(2) = o[1];
    OUT(3) = (u32)down3((u32 *)OUT(5), 0x10u, 1u, (s32)OUT(6));
    return 0;
}
