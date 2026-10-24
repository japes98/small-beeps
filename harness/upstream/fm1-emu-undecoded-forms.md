<!--
SPDX-License-Identifier: MIT
SPDX-FileCopyrightText: 2026 japes98
-->

# Upstream report: two instruction forms that don't decode

For the owner to file with `joakimeriksson/fm1-emu` and, if wanted, to
apply in the F-Emulator app. Spec side only; not filed by a session. Found
in session SR-7 (2026-10-24) against commit
`43ed5580064885e93bc8d20be931ae950d10cd4f`, after the block-move fix
(`fm1-emu-block-moves.md`). Not patched in our copy: fwtest 0.3.0 still
stops on both, and docs/HARNESS.md ("Instructions") lists them as known
gaps.

How they were found: a corpus of C and C++ (our firmware, Mutable
Instruments' Plaits, generated C) built with the vendor compiler (clang
4.0.1 pi32v2, `-mcpu=r3 -mfprev1`, `-Os` and `-O2`); each of the 660
forms in its assembly output, with every register slot set in turn to r0
to r15 and every number to a spread of values, assembled by the vendor
assembler and run on its own. 34 437 distinct encodings; these two forms
are the only ones that stop the run. Both fail in `decode_any`
(`decode_info` returns `None`): "an instruction the emulated CPU cannot
decode".

## 1. Rotate by a register: `rD = rS <> rT`

| Instruction | Bytes |
|-------------|-------|
| `r0 = r0 <> r1` | `cc e1 00 01` |
| `r5 = r9 <> r2` | `cc e1 90 52` |
| `r15 = r3 <> r14` | `cc e1 30 fe` |

None decodes, for any registers. The rotate by a constant,
`rD = rS <> n` (`c4 e1 ...`, class `r_mov_r_ltgt_i`), works. The compiler
emits the register form for any rotate by a variable amount:
`(x << s) | (x >> (32 - s))` becomes `r1 = 0x20 - r1; r0 = r0 <> r1`, and
`(x >> 7) | (x << 25)` becomes `r0 = r0 <> 7`. So `<>` rotates right, by
the register's amount; what it does with amounts of 32 or more, the
compiler's code doesn't show.

## 2. 4-byte register-list push and pop, lowest register above r0

`[--sp] = {list}` is `d8 e8 <mask>` and `{list} = [sp++]` is
`d4 e8 <mask>` (no `rets`, no `pc`; mask bit k: rk). They decode only
when the list starts at r0:

| Runs | Doesn't decode |
|------|----------------|
| `d8 e8 03 00` `[--sp] = {r1, r0}` | `d8 e8 06 00` `[--sp] = {r2-r1}` |
| `d8 e8 ff 00` `[--sp] = {r7-r0}` | `d8 e8 3e 00` `[--sp] = {r5-r1}` |
| `d4 e8 ff 0f` `{r11-r0} = [sp++]` | `d4 e8 c0 0f` `{r11-r6} = [sp++]` |
| | `d4 e8 00 0c` `{r11-r10} = [sp++]` |

The table's classes fit only the masks the corpora used, like the `d9 e8`,
`d1 e8` and `d5 e8` mask families that already have raw decoders
(`RETS_PUSH_MASK_CRAW`, `RETS_POP_MASK_CRAW`, `PC_POP_MASK_CRAW`). The
compiler was not seen to emit the failing lists: its interrupt handlers
save a list from r0 (`[--sp] = {r1, r0}`, `{r7-r0} = [sp++]`). Hand-written
assembly can. A raw decoder for `d8 e8` and `d4 e8` like those three would
cover every mask.

## Reproduction

Raw image at `0x02000000`: set the registers (and sp to RAM), then the
bytes above, then a halt. The run stops at the start of that code,
"cannot decode".
