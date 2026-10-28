/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * <math.h>: the functions Plaits calls (written for the Plaits demo, M4b;
 * since clean-1027 the platform's runtime, firmware/runtime/, BR-4).
 * sqrtf is the runtime's (softfloat.c); sinf, cosf and tanf are declared
 * only, so a call to one fails to link until a firmware supplies it. No
 * double-precision function is provided.
 */

#ifndef SB_RUNTIME_MATH_H
#define SB_RUNTIME_MATH_H

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
