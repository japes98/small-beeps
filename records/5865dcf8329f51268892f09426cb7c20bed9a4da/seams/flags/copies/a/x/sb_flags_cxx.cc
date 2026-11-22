/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * C++ in the folder given flags (tools/seams_suite.py, case flags): it
 * gets --cxxflags and not --cflags.
 */

#ifndef SB_FLAGS_CXX
#error "built without its folder's flags (--cxxflags)"
#endif
#ifdef SB_FLAGS_OUTER
#error "the folder's C flags reached its C++"
#endif

extern "C" unsigned sb_flags_cxx(unsigned x)
{
    return x - SB_FLAGS_CXX;
}
