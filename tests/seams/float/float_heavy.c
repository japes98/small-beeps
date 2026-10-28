/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * A float-heavy object for the write-back store check (tools/seams_suite.py,
 * case ownbase; BR-13, R-BUILD-3): built as an outside source with the
 * firmware's flags, so the compiler uses the chip's float instructions
 * (the fprev1 feature), and holding the conditional block those flags
 * allow, iff (r2 > r5) { ... }, as the compiler writes it in the vendored
 * Plaits. Disassembled without the build's CPU and features, every float
 * instruction reads as an unknown one and the bytes after it as others,
 * and the block's second half reads as [r0++=4] = r0: a store the check
 * would refuse, which isn't there. Read as compiled, the object holds no
 * such store, unless SB_TEST_FLOAT_OWNBASE puts a real one after the float
 * code, which the check must then find. Nothing calls these; the
 * firmware itself is never built with this folder.
 */

void sb_test_float_mix(float *out, const float *a, const float *b, float k, unsigned n)
{
    while (n--) {
        float x = *a++, y = *b++;
        *out++ = x + (y - x) * k;
    }
}

void sb_test_float_ramp(float *out, float start, float step, unsigned n)
{
    while (n--) {
        *out++ = start;
        start += step;
    }
}

float sb_test_float_poly(float x)
{
    return ((x * 0.5f + 1.25f) * x - 3.0f) * x / (x * x + 1.0f);
}

int sb_test_float_count(const float *a, unsigned n, float lo)
{
    int c = 0;

    while (n--)
        c += *a++ > lo;
    return c;
}

int sb_test_float_block(int a, int b)
{
    __asm__ volatile("iff (r2 > r5) {\n\tr4 = r5\n\t}" : : : "r2", "r4", "r5");
    return a + b;
}

#if defined(SB_TEST_FLOAT_OWNBASE)
float sb_test_float_ownbase(float x, float y)
{
    float z = x * y + x / y;

    __asm__ volatile("[++r1=4] = r1" : : : "r1", "memory");
    return z;
}
#endif
