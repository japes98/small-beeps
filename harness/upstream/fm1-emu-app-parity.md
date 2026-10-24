<!--
SPDX-License-Identifier: MIT
SPDX-FileCopyrightText: 2026 japes98
-->

# For the F-Emulator app: the patches it doesn't have yet

For the owner, to apply in the app (and, where marked, to file upstream).
Spec side only. Session emulator-parity, 2026-10-24, against the app's
patch notes as the owner dropped them (PROVENANCE P-37) and upstream
`43ed5580064885e93bc8d20be931ae950d10cd4f`. docs/EMULATOR-PARITY.md has
the whole table.

## What to apply

Three of fwtest's patches, in this order, on the app's tree (upstream, its
fwtest-0001/0002 base, its 0003 to 0006):

| fwtest patch | What | Upstream report |
|--------------|------|-----------------|
| `vendor/emulator/patches/0003-block-moves-below-the-base.patch` | The block moves with a register base, all eight modes (SR-7) | `fm1-emu-block-moves.md` |
| `vendor/emulator/patches/0005-rotate-by-a-register.patch` | `rD = rS <> rT` (`cc e1` / `cc f1`) | `fm1-emu-undecoded-forms.md` |
| `vendor/emulator/patches/0006-push-pop-any-register-list.patch` | `d8 e8` / `d4 e8` with any mask | `fm1-emu-undecoded-forms.md` |

Checked in this session on a copy: upstream with fwtest's 0001 and 0002,
then the app's 0003, 0004, 0005 and 0006 (as dropped), then these three
with `git apply`. Every hunk applies, none needs its context refreshed,
only line offsets move (0003: -1 to +25 lines; 0005 and 0006: -1). The
crates' own tests pass after (73: 44, 7 and 22). `crates/fm1-core` is then
byte for byte fwtest 0.4.0's; `crates/fm1-soc` differs only by the app's
raw-image loader (its 0006), 61 added lines.

The app's notes say SR-7's form "faults" in fwtest and that the two
patches meet only in `decode_any`: true of fwtest 0.2.0. fwtest 0.3.0's
0003 decodes the `xm eb` block moves in `exec_syntax` and `fast_of`, not
in `decode_any`, so it and the app's pair-head fix touch different
functions.

## Already the app's, now fwtest's too

The app's 0003 (A, the pair heads), 0004 (C) and 0005 (D) are fwtest's
0004, 0007 and 0008, with the same added and removed lines. A's upstream
report is the app's own (its notes' "Upstream bug reports", 1); file that
one. fwtest's harness test `alu_pair_heads_hold_their_result` (image
`harness/tests/images/pairhead.S`, one word of each fallback family, plain
and as a pair head) can go with it: in 0.3.0's emulator two of its 25
cases saw the new value (`94 f1 51 63` and `c8 f1 53 63`), so which words
reach the fallback depends on the registers, not only the family.

## Two things in the drop to look at

- The app's `0006-raw-image-boot.patch` inserts `RAW_IMAGE_MAX`,
  `RawImage`, `raw_image` and `raw_boot` inside fm1-soc's `mod tests`,
  after its `use super::*;`, so they compile only in test builds and are
  not part of the crate's API. The app's own branch may differ from the
  file dropped; fwtest doesn't use the patch either way.
- The notes give the reproduction for A as a fwtest command line not yet
  run on fwtest. It now is (its 32-byte image, `--ms 1 --ram
  0x01c00020:4@end`): fwtest built on 0.3.0's emulator stores 0x108, on
  0.4.0's 0x55, as the notes expect.
