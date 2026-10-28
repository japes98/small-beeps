<!--
SPDX-License-Identifier: MIT
SPDX-FileCopyrightText: 2026 japes98
-->

# Upstream note: a store whose stored register is its own base

For the owner to apply in the F-Emulator app, and to offer to
`joakimeriksson/fm1-emu` if wanted. Spec side only; not filed by a
session. Written in session spec-1027 (2026-10-27) against commit
`43ed5580064885e93bc8d20be931ae950d10cd4f`; our copy carries the change as
`vendor/emulator/patches/0013-store-of-the-base-keeps-its-old-value.patch`
(fwtest 0.9.0). docs/EMULATOR-PARITY.md lists it.

## What upstream does

A pre-increment store with a number step moves the base, then reads the
register to store, so `[++r4=748] = r4` stores the moved base. That holds
for the word, halfword and byte forms, on every path that runs them
(`Fast::StPre`, the syntax-driven store, routes 19 and 35). The
post-increment stores, and the pre-increment store with a register step
(route 32), read the register first and store the base as it was.

## What the vendor compiler expects

The base as it was. For

```
int *f(int *p) { int *q = p + 187; *q = (int)p; return q; }
```

it emits the one instruction `[++r0=748] = r0`, and `[r0++=8] = r0`,
`h[++r0=8] = r0` and `b[++r0=8] = r0` for the post-increment, halfword
and byte versions. For the same C storing the moved pointer (`*q = q`) it
computes the new base in another register and stores that. A firmware
built on small-beeps faulted on code compiled this way, depending only on
register allocation. What the chip stores has not been measured.

## What the patch does

Each store path reads the register to store before it moves the base.
Loads, and register-pair accesses whose base is in the pair, are
unchanged. The JIT has no pre-increment store of its own. Crate test
`stores_of_the_base_keep_its_old_value` (all fifteen forms the assembler
takes); fwtest's harness test of the same name.
