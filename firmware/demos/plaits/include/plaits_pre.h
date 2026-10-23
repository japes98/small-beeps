/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * Included before every vendored Plaits file (-include). Plaits' portable
 * configuration (-DTEST) mentions printf in a flash-saving function the
 * demo never calls; this declares it so the file compiles. Nothing
 * defines it, so a call would fail to link.
 */

#ifdef __cplusplus
extern "C"
#endif
int printf(const char *format, ...);
