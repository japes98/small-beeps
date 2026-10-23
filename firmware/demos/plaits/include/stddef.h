/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * <stddef.h> for the Plaits demo (the target is 32-bit).
 */

#ifndef PLAITS_DEMO_STDDEF_H
#define PLAITS_DEMO_STDDEF_H

typedef __SIZE_TYPE__ size_t;
typedef __PTRDIFF_TYPE__ ptrdiff_t;
#define NULL 0
#define offsetof(type, member) __builtin_offsetof(type, member)

#endif
