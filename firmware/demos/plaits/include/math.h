/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * <math.h> for the Plaits demo: the functions Plaits calls, from our own
 * runtime (runtime/softfloat.c, runtime/mathf.c). No double-precision
 * function is provided: Plaits uses none.
 */

#ifndef PLAITS_DEMO_MATH_H
#define PLAITS_DEMO_MATH_H

#ifdef __cplusplus
extern "C" {
#endif
float sqrtf(float x);
float sinf(float x);
float cosf(float x);
float tanf(float x);
#ifdef __cplusplus
}
#endif

static inline float fabsf(float x) { return __builtin_fabsf(x); }

#define M_PI 3.14159265358979323846

#endif
