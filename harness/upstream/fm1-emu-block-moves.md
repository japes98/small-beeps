<!--
SPDX-License-Identifier: MIT
SPDX-FileCopyrightText: 2026 japes98
-->

# Upstream report: the block moves below a base register don't run

For the owner to file with `joakimeriksson/fm1-emu` and to apply in the
F-Emulator app. Spec side only; not filed by a session. Found in session
SR-7 (2026-10-24) against commit `43ed5580064885e93bc8d20be931ae950d10cd4f`;
our copy carries the fix as
`vendor/emulator/patches/0003-block-moves-below-the-base.patch`.

## What goes wrong

The block moves with a register base are one 4-byte family, `xm eb
<mask>` with m < 8: the base register in bits 0-3, a 16-bit register mask
(bit k: rk) in bits 16-31, and three mode bits in bits 4-6 (4: write the
base back, 5: store, 6: the block lies below the base). The vendor
toolchain's disassembler names the eight modes:

| Bytes | Form |
|-------|------|
| `0N eb` | `{list} = [rN+]` |
| `1N eb` | `{list} = [rN++]` |
| `2N eb` | `[rN+] = {list}` |
| `3N eb` | `[rN++] = {list}` |
| `4N eb` | `{list} = [-rN]` |
| `5N eb` | `{list} = [--rN]` |
| `6N eb` | `[-rN] = {list}` |
| `7N eb` | `[--rN] = {list}` |

`fm1-core` runs only the first four (`exec_syntax`'s "multi-register block
moves with a register base" arm and the fast path's `Fast::BlockMove`, both
selected on the table syntax `} = [R+` / `[R+`). The other four decode (the
table has corpus classes for them, with register counts fitted to the
corpus masks: `44 eb 09 00`, a two-register list, decodes as
`{R*3} = [-R]`) but no arm executes them, so the run stops with "an
instruction the emulator does not implement".

The vendor compiler emits two of them on its own, with or without
`-mcpu=r3 -mfprev1`, at `-Os`, `-O2` and `-O3`: `{rA, rB} = [-rN]` for two
loads at `p[-2]`, `p[-1]` (struct copies, reads below a pointer), and
`[-rN] = {rA, rB}` for two stores there (copies running downwards). So
ordinary C code faults: our firmware's FM engine stopped at the first
struct copy it made.

## What the instructions do

From the vendor compiler's own output, for C whose meaning is known (clang
4.0.1 pi32v2 in `jieli-linux-toolchains-20250324.1`):

- The lowest-numbered register takes the lowest address. `[-rN]` covers the
  words rN - 4n to rN - 4. For `v0 = p[-1]; v1 = p[-2];` it emits
  `{r3, r0} = [-r0]` and then uses r0 as `p[-2]`, r3 as `p[-1]`.
- The forms without `++` / `--` leave the base alone: after
  `{r7, r4} = [-r0]` the same function loads `p[0]` with `r8 = [r0+0]`;
  after `[-r2] = {r6, r5}` a loop steps the pointer itself
  (`r2 += -12`, for three words a pass).
- Every address comes from the original base: `{r3, r0} = [-r0]` above
  needs both words from the old r0.

The compiler wasn't seen to emit the write-back modes (`[rN++]`,
`[--rN]`). The fix gives `[--rN]` the base rN - 4n, mirroring what
`[rN++]` already did (rN + 4n).

## Reproduction

Raw image at `0x02000000` (`--ms 1 --ram 0x01c00020:12@end`):

```
_start:
	r4 = 0x01C00010
	r1 = 0x29F3A1C5
	[r4+-8] = r1
	r1 = 0x7E41D60B
	[r4+-4] = r1
	{r3, r0} = [-r4]        ; 44 eb 09 00
	r5 = 0x01C00020
	[r5+0] = r0
	[r5+4] = r3
	[r5+8] = r4
	cli
1:	goto 1b
```

Expected: r0 `0x29F3A1C5`, r3 `0x7E41D60B`, r4 `0x01C00010`. Observed
before the fix: the run stops at pc `0x02000016`, "an instruction the
emulator does not implement", nothing stored.

## The fix

Select the family on its raw bits (`(raw >> 8) & 0xff == 0xeb && raw &
0x80 == 0`, length 4) instead of the table syntax, in both places, and
run all eight modes through one helper:

```rust
fn block_move_raw(raw: u64) -> (usize, u16, bool, bool, bool) {
    ((raw & 0xf) as usize, (raw >> 16) as u16, raw & 0x20 != 0, raw & 0x40 != 0, raw & 0x10 != 0)
}

fn block_move<B: Bus>(&mut self, bus: &mut B, base: usize, mask: u16, store: bool, down: bool, post: bool) {
    let size = 4 * mask.count_ones();
    let start = if down { self.regs[base].wrapping_sub(size) } else { self.regs[base] };
    let mut addr = start;
    for i in 0..16usize {
        if mask >> i & 1 != 0 {
            if store { bus.write32(addr, self.regs[i]); } else { self.regs[i] = bus.read32(addr); }
            addr = addr.wrapping_add(4);
        }
    }
    if post {
        self.regs[base] = if down { start } else { addr };
    }
}
```

`Fast::BlockMove` gains a `down` field; its register-use summary is
unchanged (only `post` writes the base). The four ascending modes behave
exactly as before. The full diff is the patch named above. The JIT
back ends weren't touched: each runs `Fast::BlockMove` through the
interpreter's executor for that one op, as before.

Checked with: our harness tests (an assembled image covering every mode,
several bases and masks, a base in its own list and a 15-register list; the
reproduction above; and a C image built with `-mcpu=r3 -mfprev1` whose
compiled code holds both descending forms), each of which fails without the
fix; the crate's own tests; and every distinct instruction the compiler
emitted for a corpus of C and C++ (our firmware, Mutable Instruments'
Plaits, generated C) run on its own, and each form of the compiler's
assembly across registers and immediates: with the fix, only two forms
still stop the run (`fm1-emu-undecoded-forms.md`).
