<!--
SPDX-License-Identifier: MIT
SPDX-FileCopyrightText: 2026 japes98
-->

# Upstream note: a dual-issue pair whose halves write one register

For the owner to apply in the F-Emulator app, and to offer to
`joakimeriksson/fm1-emu` if wanted. Spec side only; not filed by a
session. Written in session day-1024 (2026-10-24) against commit
`43ed5580064885e93bc8d20be931ae950d10cd4f`; our copy carries the change as
`vendor/emulator/patches/0011-pair-head-wins-over-its-second-half.patch`
(fwtest 0.6.0). docs/EMULATOR-PARITY.md lists it.

## What upstream does

`fm1-core` holds a pair head's register results until the second half has
run, then commits those the second half didn't change. When both halves
write the same register, the second half's value stays.

## What the vendor compiler expects

The head's. It pairs a head computing a value with a word load into the
same register whose result it doesn't use, then uses the register as the
head's value:

```
r7 = r6 + 0x80000  #
r7 = [r1+8]
r5 = r7 >> 16
```

(an unused read of SPI0's `BUF` in a flash routine at `-Os`; at `-O2` also
`r0 = r1.b0 (u) #` and `r0 = uextra(r1, p:8, l:8) #` with `r0 = [r3+8]`,
then `[r3+8] = r0`). In everything we compiled, these are the only pairs
whose halves write one register, and each uses the head's value next.

## What the patch does

Both commit loops (`step` and `exec_fast_paired`) commit every register
the head changed, over the second half's write. The JIT needs nothing: the
block builder glues a pair into compiled code only when the head's writes
miss the second half's reads and writes, so a pair whose halves write one
register always takes those two paths, with the JIT on or off. A head that leaves a
register's value as it was can't be told from one that didn't write it;
then the second half's value stays. Crate test
`pair_head_wins_over_its_second_half`; fwtest's harness test of the same
name. fwtest's firmware suite gives the same outputs with and without it.
