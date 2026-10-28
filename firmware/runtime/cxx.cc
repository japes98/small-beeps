/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * What C++ needs from a runtime: a handler for a call of a pure virtual
 * function, and the deallocation functions a virtual destructor refers
 * to. Nothing on the platform allocates or deletes, and a pure virtual
 * function is never meant to be called, so each stops the firmware if
 * reached, as a fault (sb_halt) naming which. Since clean-1027 (BR-4)
 * part of the platform's runtime (firmware/runtime/); written for the
 * Plaits demo (M4b). Also since then: __cxa_atexit and __dso_handle,
 * which a static object with a destructor registers with. The firmware
 * never exits, so no destructor is kept or run. The constructors of
 * static objects run from main() (main.c, before the engine's init).
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

// A static object's destructor, registered to run at exit: the firmware
// never exits, so it is not kept.
extern "C" int __cxa_atexit(void (*)(void *), void *, void *)
{
    return 0;
}

extern "C" {
void *__dso_handle = 0;
}
