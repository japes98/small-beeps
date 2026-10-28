/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * The platform's runtime in use (firmware/runtime/, BR-4): C++ with a
 * virtual class (its tables refer to __cxa_pure_virtual and operator
 * delete), a static object with a constructor (main() runs it) and one
 * with a destructor (registered with __cxa_atexit), <algorithm>'s sort,
 * and memcpy, memmove and memset called with lengths known only at run
 * time. The test engine records the result, which tools/seams_suite.py
 * checks (301 + 1000: the constructed object's value).
 */

#include <algorithm>
#include <inttypes.h>
#include <string.h>

namespace {

class Shape {
public:
    virtual ~Shape() {}
    virtual uint32_t area() const = 0;
};

class Rect : public Shape {
public:
    Rect(uint32_t w, uint32_t h) : w_(w), h_(h) {}
    uint32_t area() const override { return w_ * h_; }

private:
    uint32_t w_, h_;
};

volatile size_t four = 4, eight = 8;

// Built by its constructor, which main() runs before the engine's init.
struct Counter {
    Counter() : v(1000) {}
    uint32_t v;
};
Counter constructed;

uint32_t area_of(const Shape &s) { return s.area(); }

}  // namespace

extern "C" uint32_t sb_test_runtime(void)
{
    static Rect r(6, 7);
    uint32_t sum = area_of(r);                       // 42
    uint32_t v[8] = { 5, 3, 7, 1, 8, 2, 6, 4 };
    uint32_t x[40], y[40];
    uint8_t b[16];

    std::sort(v, v + 8);
    for (uint32_t i = 0; i < 8; i++)
        sum += v[i] * (i + 1);                       // 204
    for (uint32_t i = 0; i < 40; i++)
        x[i] = i;
    memcpy(y, x, eight * 20);
    sum += y[39];                                    // 39
    for (uint32_t i = 0; i < 16; i++)
        b[i] = (uint8_t)i;
    memmove(b + 1, b, eight);
    sum += b[8];                                     // 7
    memset(b, 9, four);
    sum += b[0];                                     // 9
    return sum + constructed.v;                      // 1000
}
