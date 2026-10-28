<!--
SPDX-License-Identifier: MIT
SPDX-FileCopyrightText: 2026 japes98
-->

# Vendored: the emulator's core crates (spec side only)

- Repository: https://github.com/joakimeriksson/fm1-emu (public, MIT)
- Commit: `43ed5580064885e93bc8d20be931ae950d10cd4f` (main on 2026-10-22,
  "Merge pull request #39 from joakimeriksson/windows-jit", committed
  2026-10-21T22:07:20+02:00)
- Licence: MIT, copyright 2026 Joakim Eriksson (`LICENSE` here, copied
  unmodified).
- What: `crates/fm1-isa`, `crates/fm1-core` and `crates/fm1-soc`, at the
  same paths, unmodified but for the patches below (0002 to 0016: bug
  fixes, two speed-only changes and MIDI out) and the workspace manifest
  `Cargo.toml` (patched, 0001). docs/EMULATOR-PARITY.md compares them with
  the F-Emulator app's.
  Nothing else from that repository: no other crates, no `fm1-sid/`, no
  probes, no firmware files.
- Fetched by `tools/fetch-emulator.sh --fetch` (a blob-less clone with a
  sparse checkout of exactly those paths) and checked by
  `tools/fetch-emulator.sh --verify` (C-EMU-PIN): every file against
  `SHA256SUMS`, whose own SHA-256 (the tree hash) is
  `35c06f37c29f5ec8c70acc8d897c190eb2ea411a5cf7882c55d8ed173ba7cdd8`.
- Provenance: PROVENANCE.md P-7. Exposure: docs/EXPOSURE.md (session M0b).

## Patches

Applied in file-name order by the fetch script, after checkout:

- `patches/0001-workspace-members.patch`: the three crates take their
  version, edition and licence from the workspace manifest, which upstream
  lists with seven members. The patch keeps the manifest and lists only the
  three vendored crates, so they build as path dependencies of `harness/`.
  No code is changed.
- `patches/0002-spi1-con-writes-replace.patch` (session SR-3, 2026-10-23,
  chosen by the owner): `crates/fm1-soc/src/lib.rs`, SPI1's `CON` write
  (0x11D00). Upstream merged each written value into the stored one, so a
  bit once written 1 could never be cleared, and after any write with bit
  13 every SPI1 transfer raised IRQ 16. With the patch a write replaces
  `CON` (bit 14 stays a strobe that clears the pending flag, not stored).
  The harness test `spi1_interrupt_follows_con_bit_13` fails without it.
  To be reported upstream by the owner from
  `harness/upstream/fm1-emu-spi1-con.md`; drop the patch when the pinned commit has the fix.
- `patches/0003-block-moves-below-the-base.patch` (session SR-7,
  2026-10-24, asked for by the firmware side's SR-7):
  `crates/fm1-core/src/lib.rs`, the block moves with a register base
  (`xm eb <mask>`, m < 8). Upstream ran only the four ascending modes,
  chosen by the table's syntax; `{..} = [-rN]`, `[-rN] = {..}` and the
  `[--rN]` forms ended the run as "an instruction the emulator does not
  implement", and the vendor compiler emits the first two on its own. With
  the patch the family is chosen on its raw bits and one helper runs all
  eight modes, for the interpreter and the fast path; the ascending modes
  behave as before. Behaviour from the vendor compiler's own code
  (`harness/upstream/fm1-emu-block-moves.md`, docs/HARDWARE-SPEC.md HW-66).
  The harness tests `block_moves_every_mode`,
  `block_move_below_the_base_sr7` and `block_moves_from_the_compiler` fail
  without it. To be reported upstream by the owner from that file; drop the
  patch when the pinned commit has the fix.
- `patches/0004-pair-heads-without-a-table-class.patch` (session
  emulator-parity, 2026-10-24; the F-Emulator app's 0003, taken with its
  added and removed lines unchanged, licensed MIT here by the owner,
  PROVENANCE P-39): `crates/fm1-core/src/lib.rs`. A 4-byte ALU word that no
  table class fits and the fallback decoder takes (`decode_any`'s
  `decode_alu4` arm), with byte 1 `f0` / `f1`, a dual-issue pair's head,
  ran unpaired: the pair's second half saw the new value. It now decodes
  through `ALU4_PAIR_CRAW`, whose syntax ends in `#`. Its crate test
  `alu4_fallback_keeps_pair_head`; the harness test
  `alu_pair_heads_hold_their_result` fails without it. Upstream report: the
  app's (`harness/upstream/fm1-emu-app-parity.md`).
- `patches/0005-rotate-by-a-register.patch` (emulator-parity):
  `crates/fm1-core/src/lib.rs`. `rD = rS <> rT` (`cc e1` / `cc f1`) had no
  decoder; `ROTR_CRAW` / `ROTR_PAIR_CRAW` beside the constant rotate's, and
  a slow-path arm in `exec_syntax`. The harness tests
  `rotate_by_a_register` and `rotates_from_the_compiler` fail without it.
  Upstream report: `harness/upstream/fm1-emu-undecoded-forms.md`.
- `patches/0006-push-pop-any-register-list.patch` (emulator-parity):
  `crates/fm1-core/src/lib.rs`. `[--sp] = {mask}` / `{mask} = [sp++]`
  (`d8 e8` / `d4 e8`) decoded only for the table's masks from r0;
  `LIST_PUSH_MASK_CRAW` / `LIST_POP_MASK_CRAW` take every mask, run by the
  existing block push / pop arm. The harness test
  `push_pop_any_register_list` fails without it. Upstream report:
  `harness/upstream/fm1-emu-undecoded-forms.md`.
- `patches/0007-peripherals-before-memories.patch` (emulator-parity; the
  app's 0004, unchanged, P-39): `crates/fm1-soc/src/lib.rs`, speed only:
  `Soc::region` sends addresses below 16 MB to `region_low` first. Its
  crate test `region_is_what_it_was` compares it with the old function
  (the test's copy is the old one exactly, whitespace aside) at every
  address below 0x04200000 and a sweep above.
- `patches/0008-ram-blocks-by-write-count.patch` (emulator-parity; the
  app's 0005, unchanged, P-39): `crates/fm1-core/src/lib.rs` and
  `crates/fm1-soc/src/lib.rs`, speed only: `ram_block_ok` trusts the bus's
  `code_writes` count on every build, not only wasm. Checked: `Ram`'s bytes
  are private and all four of its write methods count; the only raw pointer
  to them (`JitMem.ram`) is read by `ram_code` and written only by the JITs'
  inline stores, which check the code flags first (AArch64 and x86-64
  `store`); a block marks exactly the bytes it snapshots. fwtest runs with
  `jit_on` false. Its crate test `ram_block_sees_patched_code`; the harness
  test `ram_code_runs_as_written` passes with and without it. Session
  pin-050 took the app's fix to that crate test (the test only): as first
  taken its JIT half never ran compiled code (3 entries a run; the JIT
  compiles on the 32nd). Now each run enters the block 40 times, checks
  `r0` every pass and, where `build.rs` turns the native JIT on, that
  compiled code ran with the JIT only and again after the patch; with the
  count in `Ram::wrote` switched off the JIT half fails on its own.
- `patches/0009-midi-out-transmit-side.patch` (session midi-in-out,
  2026-10-24; our own, PROVENANCE P-46): `crates/fm1-soc/src/lib.rs`,
  UART1's transmit side for MIDI out: a TX DMA or a `BUF` write puts bytes
  on the wire one per 320 us, after any still going, with the TX pending
  (and its interrupt) when the last has gone; nothing is sent with the
  UART off. The bytes are kept until the runner drains them
  (`Periph::midi_take_sent`), for fwtest's `--midi-out` and the app's
  MIDI output (`harness/upstream/fm1-emu-midi-out.md`). The harness test
  `transmits_midi` and the suite case `midiout` check it.
- `patches/0010-flash-chip-busy-times-and-power-cut.patch` and
  `patches/0011-pair-head-wins-over-its-second-half.patch` (session
  day-1024, 2026-10-24; our own, PROVENANCE P-54): the flash chip's
  command rules, busy times, operations log and power cut; a dual-issue
  pair whose halves write one register keeps the head's result. Their own
  headers and `harness/upstream/fm1-emu-flash-busy.md`,
  `harness/upstream/fm1-emu-pair-same-register.md` describe them (fwtest
  0.6.0). (Listed here by session spec-overnight-1025.)
- `patches/0012-usb-port-answers.patch` (session spec-overnight-1025,
  2026-10-26; the F-Emulator app's change, from its behaviour-only note,
  PROVENANCE P-59): `crates/fm1-soc/src/lib.rs`, the USB core's access
  port at 0x11804 (`JL_USB->CON1`): reading it gives the last value
  written with bit 15 (`MACK`, done) set; for a read (bit 14 set)
  bits 0-7 hold the byte last written to that index, the interrupt flags
  (indexes 2-6) 0. Upstream kept the word as plain storage, so a firmware
  waited out its own timeout on every access. The crate test and the
  harness test `usb_port_answers` (image `tests/images/usbport.c`, suite
  case `usbport`) fail without it (`harness/upstream/fm1-emu-usb-port.md`;
  fwtest 0.7.0). Licence: the owner confirmed the note is covered by MIT
  on the same terms as P-47 (recorded by session spec-a1-fwsc).
- `patches/0013-store-of-the-base-keeps-its-old-value.patch` (session
  spec-1027, 2026-10-27; SR-10, from the vendor toolchain's code,
  PROVENANCE P-1): `crates/fm1-core/src/lib.rs`, a store with a base
  update whose stored register is its base stores the base as it was (the
  pre-increment forms with an immediate step stored the moved base). The
  crate test and the harness test `stores_of_the_base_keep_its_old_value`
  (images `tests/images/selfstore.S` and `selfc.c`, suite case
  `selfstore`) fail without it (`harness/upstream/fm1-emu-store-of-the-base.md`;
  fwtest 0.9.0).

- `patches/0014-toolchain-audit-compiler-and-float-forms.patch` (session
  spec-isa-audit, 2026-10-28; from the vendor toolchain, PROVENANCE P-1
  and P-64): `crates/fm1-isa/src/fpu.rs` and `crates/fm1-core/src/lib.rs`,
  the forms the toolchain audit found the compiler emits, or that are
  float, and fwtest could not run or ran wrongly: the FPU's unary row
  (rounding conversions, half precision), `fcmp` and the flag branches, the
  memory row's `&= ~R` and shifts by a register (and `6c e8`'s shift by
  32), the 64-bit index scaled by 8, `zcmp`. The crate tests and the
  harness tests `forms_the_compiler_emits` and
  `forms_only_the_assembler_emits` (images `tests/images/isac.c`,
  `isaasm.S`) fail without it (fwtest 0.10.0).
- `patches/0015-toolchain-audit-registers-halves-and-fields.patch` (session
  spec-isa-audit, as 0014): `crates/fm1-core/src/lib.rs`, forms only the
  assembler emits whose result the printed form fixes: half moves, a half
  clamped to 8 bits, bit fields with the field in a register, `<<<=` in memory,
  the high half stored, the special registers retx, sr4 and sspn, and the
  4-byte push and pop of special registers. The crate tests and the
  harness test `registers_halves_and_fields` (image
  `tests/images/isaregs.S`) fail without it (fwtest 0.10.0).

- `patches/0016-toolchain-audit-forms-with-an-open-detail.patch` (session
  spec-isa-audit, as 0014): `crates/fm1-core/src/lib.rs`, forms only the
  assembler emits whose printed form is explicit but a detail of whose
  result the toolchain leaves open, each detail a recorded choice
  (HARDWARE-SPEC Q-31 to Q-33): the pair shifts with rounding, the
  multiplies with a memory operand, the `npc` loads, the halves swap
  (`70 e0 40`). The crate tests and the harness test
  `forms_with_an_open_detail` (image `tests/images/isaops.S`) fail
  without it (fwtest 0.10.0).

0007 and 0008 change no output: the firmware suite, the spec experiments
and the harness suite gave byte-identical outputs (284 files) from fwtest
built with and without them (docs/EMULATOR-PARITY.md).

## Not used

The harness never calls the crates' update-package and stock-boot paths
(`fwsc`, `stock_from_package`, `stock_boot`, `write_boot_info`); they are
vendored only because the crate is kept whole. C-HARNESS-SCOPE checks
that `harness/src` names none of them.
