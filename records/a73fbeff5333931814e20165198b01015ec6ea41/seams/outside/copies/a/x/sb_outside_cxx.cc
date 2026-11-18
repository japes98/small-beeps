/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * C++ from an outside source folder, built as C++14 without exceptions or
 * RTTI; no runtime is needed for this.
 */

#include "outside.h"

namespace {

class Scale {
public:
    explicit Scale(unsigned k) : k_(k) {}
    unsigned operator()(unsigned x) const { return x * k_; }

private:
    unsigned k_;
};

}  // namespace

extern "C" unsigned sb_outside_cxx(unsigned x)
{
    return Scale(SB_OUTSIDE_FACTOR)(x);
}
