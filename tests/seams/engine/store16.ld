/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * The test engine with a store region of its own (tools/seams_suite.py,
 * cases powercut and region; clean-store-region): 16 sectors from chip
 * offset 0x20000, in the app area after the small image, set as a
 * firmware built on the base sets its own (docs/BUILDING-ON-SMALL-BEEPS.md,
 * "Where the store goes"): the symbol pair first, then the script that
 * includes firmware/platform.ld. tools/store.py's TEST_REGIONS has the
 * same.
 */

STORE_BASE = 0x20000;
STORE_SIZE = 0x10000;

INCLUDE engine.ld
