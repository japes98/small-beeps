/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * C in a folder given its own flags (tools/seams_suite.py, case flags;
 * tools/build.sh --cflags, BR-11): it builds only with them, after the
 * base's (-O2 after the base's -Os), and without the inner folder's.
 */

#include "sb.h"

#ifndef SB_FLAGS_OUTER
#error "built without its folder's flags (--cflags)"
#endif
#ifdef SB_FLAGS_INNER
#error "the inner folder's flags reached the outer folder's file"
#endif
#ifdef __OPTIMIZE_SIZE__
#error "the folder's -O2 did not come after the base's -Os"
#endif

u32 sb_flags_outer(u32 x)
{
    return x * SB_FLAGS_OUTER;
}
