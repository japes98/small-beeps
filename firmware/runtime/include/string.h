/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * <string.h>, freestanding: the runtime's memcpy, memmove and memset
 * (firmware/runtime/mem.c; the platform's runtime, BR-4). Nothing else.
 */

#ifndef SB_RUNTIME_STRING_H
#define SB_RUNTIME_STRING_H

#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif
void *memcpy(void *dst, const void *src, size_t n);
void *memmove(void *dst, const void *src, size_t n);
void *memset(void *dst, int c, size_t n);
#ifdef __cplusplus
}
#endif

#endif
