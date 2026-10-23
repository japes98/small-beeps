/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * What C++ needs from a runtime, for the Plaits demo: a handler for a call
 * of a pure virtual function, and the deallocation functions a virtual
 * destructor refers to. The demo never allocates or deletes, and never
 * calls a pure virtual function, so each stops the firmware if reached.
 */

typedef __SIZE_TYPE__ size_t;

extern "C" void sb_halt(unsigned reason, unsigned source, unsigned reti) __attribute__((noreturn));

namespace {
const unsigned kHaltFault = 2;   // SB_HALT_FAULT (firmware/src/sb.h)
}

extern "C" void __cxa_pure_virtual()
{
    sb_halt(kHaltFault, 0x0C0, 0);
}

void operator delete(void *)
{
    sb_halt(kHaltFault, 0x0C1, 0);
}

void operator delete(void *, size_t)
{
    sb_halt(kHaltFault, 0x0C2, 0);
}
