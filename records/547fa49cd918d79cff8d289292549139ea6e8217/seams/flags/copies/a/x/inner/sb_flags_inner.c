/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * C in a folder inside the folder given flags, with flags of its own
 * (tools/seams_suite.py, case flags): it gets both folders' flags, the
 * outer's first, and its -Iinclude is from its own folder.
 */

#include "sb.h"
#include "sb_flags_inc.h"

#if !defined(SB_FLAGS_OUTER) || !defined(SB_FLAGS_INNER)
#error "built without both folders' flags"
#endif
#if SB_FLAGS_INC != 3
#error "not the inner folder's include/sb_flags_inc.h"
#endif

u32 sb_flags_inner(u32 x)
{
    return x + SB_FLAGS_INNER + SB_FLAGS_INC;
}
