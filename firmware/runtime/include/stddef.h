/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * <stddef.h>, freestanding (the target is 32-bit): the platform's runtime
 * (firmware/runtime/, BR-4), written for the Plaits demo (M4b).
 */

#ifndef SB_RUNTIME_STDDEF_H
#define SB_RUNTIME_STDDEF_H

typedef __SIZE_TYPE__ size_t;
typedef __PTRDIFF_TYPE__ ptrdiff_t;
#define NULL 0
#define offsetof(type, member) __builtin_offsetof(type, member)

#endif
