/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * The test engine with its store at chip offset 0x80000, 16 sectors, as
 * RevoiceDX keeps its saves (tools/seams_suite.py, case parts; SR-15):
 * set as a firmware built on the base sets its own region
 * (docs/BUILDING-ON-SMALL-BEEPS.md, "Where the store goes"), the symbol
 * pair first, then the engine's script, which includes
 * firmware/platform.ld.
 */

STORE_BASE = 0x80000;
STORE_SIZE = 0x10000;

INCLUDE engine.ld
