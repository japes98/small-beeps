/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * The test engine's linker script (tools/seams_suite.py, case platform;
 * tools/build.sh --platform --ld): the platform's layout, and the test
 * engine's record asserted where an engine's first record goes.
 */

INCLUDE platform.ld

ASSERT(sb_test_engine == 0x01C00870, "the test engine's record must follow the store's")
