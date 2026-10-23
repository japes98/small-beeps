/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * memcpy, memmove and memset for the Plaits demo: the compiler calls them
 * for structure copies and clears even where the source never does. Ours,
 * byte by byte (docs/DESIGN-NOTES.md, M4b); the base firmware has none
 * and needs none.
 */

#include "sb.h"

typedef __SIZE_TYPE__ size_t;

void *memcpy(void *dst, const void *src, size_t n)
{
    u8 *d = dst;
    const u8 *s = src;

    while (n--)
        *d++ = *s++;
    return dst;
}

void *memmove(void *dst, const void *src, size_t n)
{
    u8 *d = dst;
    const u8 *s = src;

    if (d < s) {
        while (n--)
            *d++ = *s++;
    } else {
        d += n;
        s += n;
        while (n--)
            *--d = *--s;
    }
    return dst;
}

void *memset(void *dst, int c, size_t n)
{
    u8 *d = dst;

    while (n--)
        *d++ = (u8)c;
    return dst;
}
