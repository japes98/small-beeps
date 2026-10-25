/* SPDX-License-Identifier: MIT */
/* SPDX-FileCopyrightText: 2026 japes98 */
/* A helper in the window, run once (so fwtest has decoded it), then called
   from a RAM routine right after it starts a 4 KiB erase at 0x80000:
   fwtest ends the run as a fault at the helper, though its code is
   already decoded. OUT(2) the first call's result (4); OUT(1) and OUT(0)
   are never written. */
#include "flash.h"

typedef u32 (*helper_fn)(u32);

static __attribute__((noinline)) u32 helper(u32 x)
{
    return x * 3u + 1u;
}

static RAMCODE void erase_then_call(helper_fn f)
{
    fl_wren();
    fl_sel();
    fl_addr(0x20u, 0x80000u);
    fl_desel();
    OUT(1) = f(5u);
    fl_wait();
    OUT(0) = 0xbadu;
}

int main(void)
{
    ram_init();
    fl_desel();
    volatile helper_fn f = helper;
    OUT(2) = f(1u);
    erase_then_call(f);
    return 0;
}
