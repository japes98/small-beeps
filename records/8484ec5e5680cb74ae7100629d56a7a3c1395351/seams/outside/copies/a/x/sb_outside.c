/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * C from an outside source folder (tools/seams_suite.py, case outside):
 * built with the firmware's flags, it includes a base header and one of
 * its own folder's.
 */

#include "sb.h"
#include "outside.h"

const char sb_outside_text[] = "built from outside";

u32 sb_outside_sum(u32 a, u32 b)
{
    return a + b * SB_OUTSIDE_FACTOR;
}
