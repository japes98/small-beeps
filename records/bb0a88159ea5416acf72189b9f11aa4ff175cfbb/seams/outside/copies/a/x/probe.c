/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * A file named as a base file is (firmware/src/probe.c): its object is
 * named by its path, so both are built and neither replaces the other.
 */

#include "sb.h"

u32 sb_outside_probe(void)
{
    return 0x5EA5u;
}
