<!--
SPDX-License-Identifier: MIT
SPDX-FileCopyrightText: 2026 japes98
-->

# Upstream report: a rotate by a register doesn't decode

For the owner to file with `joakimeriksson/fm1-emu`. Spec side only; not
filed by a session. Found in session SR-7 (2026-10-24) against commit
`43ed5580064885e93bc8d20be931ae950d10cd4f`, by running every distinct
instruction the vendor compiler emitted for a corpus of C and C++ on its
own. Not patched in our copy yet: fwtest 0.3.0 still stops on it, and
docs/HARNESS.md ("Instructions") lists it as a known gap.

## What goes wrong

`rD = rS <> rT`, which the vendor toolchain assembles as `cc e1` followed by
two bytes naming the registers, has no decoder entry: `decode_info`
returns `None` and a run stops with "an instruction the emulated CPU cannot
decode". Assembler output:

| Instruction | Bytes |
|-------------|-------|
| `r0 = r0 <> r1` | `cc e1 00 01` |
| `r5 = r9 <> r2` | `cc e1 90 52` |
| `r15 = r3 <> r14` | `cc e1 30 fe` |

The rotate by a constant, `rD = rS <> n` (`c4 e1 ...`, class
`r_mov_r_ltgt_i`), decodes and runs.

The vendor compiler (clang 4.0.1 pi32v2, `-mcpu=r3 -mfprev1`, `-Os` and
`-O2`) emits the register form for any rotate by a variable amount:
`(x << s) | (x >> (32 - s))` becomes `r1 = 0x20 - r1; r0 = r0 <> r1`, and
`(x >> 7) | (x << 25)` becomes `r0 = r0 <> 7`. So `<>` rotates right, by the
register's amount; what it does with amounts of 32 or more, the
compiler's code doesn't show.

## Reproduction

Raw image at `0x02000000`: set r0 and r1, then `cc e1 00 01`, then a halt.
The run stops at the instruction ("cannot decode"); expected: r0 rotated
right by r1.
