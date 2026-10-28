/* SPDX-License-Identifier: MIT */
/* SPDX-FileCopyrightText: 2026 japes98 */
/* SR-10: C that stores a pointer, as it was, where the pointer then
   points. Built with the firmware's CPU flags (build.sh), clang compiles
   pre_w() to `[++r0=748] = r0`, post_w() to `[r0++=8] = r0`, pre_h() to
   `h[++r0=8] = r0` and pre_b() to `b[++r0=8] = r0`: one instruction each,
   whose stored register is its own base, so the value the C stores is the
   base before the instruction. moved() stores the moved pointer instead,
   which clang never gives that form; build.sh fails if the disassembly no
   longer has `[++rN=k] = rN`. OUT(0..7) get each function's stored value
   and returned pointer, OUT(8..9) moved()'s. */
#include "board.h"

typedef unsigned short u16;
typedef unsigned char u8;

#define BUF ((u32 *)0x01c00400u)

u32 *pre_w(u32 *p);
u32 *post_w(u32 *p);
u16 *pre_h(u16 *p);
u8 *pre_b(u8 *p);
u32 *moved(u32 *p);

__attribute__((noinline)) u32 *pre_w(u32 *p)
{
    u32 *q = p + 187;
    *q = (u32)p;
    return q;
}

__attribute__((noinline)) u32 *post_w(u32 *p)
{
    *p = (u32)p;
    return p + 2;
}

__attribute__((noinline)) u16 *pre_h(u16 *p)
{
    u16 *q = p + 4;
    *q = (u16)(u32)p;
    return q;
}

__attribute__((noinline)) u8 *pre_b(u8 *p)
{
    u8 *q = p + 8;
    *q = (u8)(u32)p;
    return q;
}

__attribute__((noinline)) u32 *moved(u32 *p)
{
    u32 *q = p + 187;
    *q = (u32)q;
    return q;
}

int main(void)
{
    u32 *w = pre_w(BUF);
    OUT(0) = *w;
    OUT(1) = (u32)w;
    w = post_w(BUF + 200);
    OUT(2) = BUF[200];
    OUT(3) = (u32)w;
    u16 *h = pre_h((u16 *)(BUF + 210));
    OUT(4) = *h;
    OUT(5) = (u32)h;
    u8 *b = pre_b((u8 *)(BUF + 220));
    OUT(6) = *b;
    OUT(7) = (u32)b;
    w = moved(BUF + 230);
    OUT(8) = *w;
    OUT(9) = (u32)w;
    return 0;
}
