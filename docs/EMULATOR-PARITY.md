<!--
SPDX-License-Identifier: MIT
SPDX-FileCopyrightText: 2026 japes98
-->

# Emulator parity: fwtest and the F-Emulator app

fwtest (this repository's harness) and the owner's F-Emulator app both run
the public emulator upstream, `joakimeriksson/fm1-emu`, with patches of
their own. This file lists every patch and which of the two has it, so
that a firmware behaves the same in both. Written by the spec side
(session emulator-parity, 2026-10-24); kept in general terms, as every file
outside `harness/` and `vendor/emulator/` is (CONTRIBUTING.md).

## The upstream commit

Both build on `43ed5580064885e93bc8d20be931ae950d10cd4f` (main on
2026-10-22; vendor/emulator/UPSTREAM.md), the same three crates.

## Every patch

fwtest's patches are `vendor/emulator/patches/`, applied in order by
`tools/fetch-emulator.sh`. The app's are its own branch, numbered as its
patch notes (`emulator-patches.md`, from the owner; PROVENANCE P-39) number
them, against upstream with fwtest's 0001 and 0002.

| fwtest | App | What | Kind | fwtest | App |
|--------|-----|------|------|--------|-----|
| 0001 | none | The workspace manifest lists only the three vendored crates | build | yes | not needed: only for fwtest's three-crate copy |
| 0002 | B | A write to the LCD's SPI port's control register replaces it, so its interrupt enable can be cleared (SR-3) | bug fix | yes (0.2.0) | yes (its base) |
| 0003 | applied (`b6eced1`) | The block moves with a register base run in all eight modes (SR-7) | bug fix | yes (0.3.0) | yes (harness/upstream/fm1-emu-block-moves.md) |
| 0004 | 0003 (A) | A dual-issue pair's head among the 4-byte ALU forms with no table class holds its result until after the pair | bug fix | yes (0.4.0) | yes |
| 0005 | applied (`2eab4fc`) | The rotate right by a register runs, as a pair's head too | gap | yes (0.4.0) | yes (harness/upstream/fm1-emu-undecoded-forms.md) |
| 0006 | applied (`e2bbc4e`) | The 4-byte push and pop of any register list run, not only lists from r0 | gap | yes (0.4.0) | yes (same note) |
| 0007 | 0004 (C) | Peripheral addresses looked up before the memories | speed only | yes (0.4.0) | yes |
| 0008 | 0005 (D) | Code blocks in RAM found current by a count of writes to code, on every build | speed only | yes (0.4.0) | yes |
| 0009 | applied (`a78092f`) | The MIDI output: the UART's transmit side sends bytes at the wire's pace and keeps them with their times, and its pending flag rises when the last has gone (it used to finish at once and send nothing) | model | yes (0.5.0) | yes (harness/upstream/fm1-emu-midi-out.md) |
| 0010 | applied (`67ae970`) | The flash chip: the P25Q80H's command rules (write enable, start on chip select high, a program wraps within its page, the other erase sizes); with a timing set, busy times (status bit 0, other commands ignored); an operations log; a power cut that keeps the part done; a record of code-window reads while busy | model | yes (0.6.0; fwtest sets the datasheet's maximum times and ends a run on window use while busy) | yes: the rules; the timing is off by default (harness/upstream/fm1-emu-flash-busy.md) |
| 0011 | applied (`38d767a`) | A dual-issue pair whose halves write one register keeps the head's result (it kept the second half's) | bug fix | yes (0.6.0) | yes (harness/upstream/fm1-emu-pair-same-register.md) |
| 0012 | its own (branch `stock-016`, `f60b86b`) | The USB core's register access port answers: an access is done at once, a read gives the byte last written to its index, the interrupt flags read as nothing pending (it used to keep the word as written, so every access waited out the firmware's own timeout) | model | yes (0.7.0) | yes: the app's change, which fwtest's was written from (its behaviour-only note, PROVENANCE P-59; harness/upstream/fm1-emu-usb-port.md) |
| none | 0006 (E) | Boot a raw image | the app's loader | no: fwtest has its own (in `harness/`, docs/HARNESS.md "The raw image") | yes |
| none | not a patch | Two pattern guards rewritten so the crates build on an older Rust | build | no: fwtest builds on Rust 1.99 | yes |

**2026-10-27, from the app session, through the owner (recorded by
session spec-1027):** the app confirms, with the commits on its
`ios-app` branch named in the table, that it has fwtest's 0003, 0005,
0006, 0009, 0010 (its rules; the timing off by default), 0011 and 0012
(`f60b86b`). It replaces the dated note session spec-answers-a1 left
here. The app is now at fwtest 0.7.0's emulator but for its own raw-image
loader and its rewrite for an older Rust (the last two rows). This side
doesn't open the app's branch; the commits are the app session's.

fwtest 0004, 0007 and 0008 are the app's 0003, 0004 and 0005 as they
stand: their added and removed lines are byte for byte the app's, only the
line offsets refreshed for fwtest's 0003. With fwtest's 0003, 0005 and
0006 now applied (the app's report above), the two are the same emulator
but for the app's raw-image loader and its Rust 1.94 rewrite (which, its
notes say, changes nothing that decodes); this side has not compared the
app's branch itself. That was checked on the app's patches as the owner
dropped them, not on its branch, which this side doesn't open: on upstream
with them, fwtest's three apply with line offsets only, the crates' own
tests pass, and the core crate is then byte for byte fwtest's. fwtest's
three need nothing newer than the Rust the app builds with.

## Packages

Both load an update package (`.fwsc`) through upstream's package reader,
which no patch here changes; so does the upstream web build, whose page
boots every firmware from its package through the same crates (its
`web/fwsc.js` at the pinned commit, read for Phase A1; PROVENANCE P-60).
fwtest does so from 0.8.0 (`--package`, docs/HARNESS.md "Packages"),
with checks of its own on top and without the stock-firmware extras the
app and the web build add (a default patch bank in a blank user region,
the other board).

**The app's path (confirmed).** From the app session's own description,
relayed by the owner on 2026-10-27 (recorded by session spec-1027; this
side doesn't open the app's branch, and the description is of behaviour
only): the app loads a `.fwsc` through upstream's package reader, the
conversion to the flash image and the stock boot, all unchanged from
upstream `43ed558`. Around them:

- **Before the reader** it refuses, with a message: a file over 16 MiB; a
  package under 960 bytes or over 8 MiB; a catalog download whose SHA-256
  differs from the catalog's; an M-VAVE version newer than 015, by the
  package's own name.
- **The reader:** a package that crashes the reader is refused as
  malformed.
- **The user-patch area:** the app loads no patch bank of its own into
  it; the defaults are filled as upstream does.
- **After boot:** the firmware's own saved flash sectors are written over
  the image, after checks (whole 4 KiB sectors, in range, none repeated).
- **Running:** the interpreted CPU, idle skipping, and each firmware at
  its own measured clock.

docs/A1-PLAN.md tests a package of ours in all three.

## How each was checked

- **0004 (the pair heads).** From the vendor toolchain (PROVENANCE P-40):
  its disassembler prints the second twin of each of these forms (byte 1
  `f0` / `f1`) as a pair's head, and the compiler's own code for our
  firmware relies on a pair's second half seeing the registers as they
  were before the head. fwtest's harness test runs one word of every
  family, plain and as a pair's head, and fails without the patch. The
  app's own test comes with it.
- **0005 and 0006 (the two gaps SR-7 found).** Encodings from the vendor
  assembler and disassembler; the rotate's behaviour from the compiler's
  rotate idioms, including one built with the firmware's flags in a test
  image; the lists' from the lists from r0 the compiler emits. Each has a
  harness test that fails without it (docs/HARNESS.md, "Instructions").
- **0007 and 0008 (speed only).** Taken because a test shows they change
  no behaviour. The app's test for 0007 compares the new address lookup
  with the old one at every address up to the end of the memories and a
  sweep above. For 0008 every way RAM can be written was checked to count
  as a write to code, and a harness test runs RAM code changed by stores,
  with and without the patch. Then the firmware's suite (at `cdfd067`), the
  spec experiments and the harness's own suite were run on fwtest built
  with and without 0007 and 0008: all 284 output files are byte for byte
  the same.
- **0008's own test (session pin-050).** The crate test that came with
  0008 runs RAM code changed by a store with the JIT off and on, but its
  JIT half never ran compiled code: each run entered the block too few
  times for the JIT to compile it, so both halves checked the same path.
  The app found this and fixed the test (F-Emulator, 2026-10-24); fwtest's
  0008 takes that fix unchanged, the test only. Each run now enters the
  block 40 times and checks the result every time, and on the hosts where
  the JIT is built in it checks that compiled code ran with the JIT on
  and not with it off, and ran again after the store. On an Apple silicon
  Mac the fixed test passes; with the count of writes to code switched
  off it fails, and its JIT half fails on its own. The old test, by the
  same count, ran no compiled code in either half. The patch's code is
  unchanged, so fwtest stays at 0.5.0 and no new image is pinned. Not run
  on an x86-64 host: fwtest's CI runs the harness's tests, not the
  crates'.
- **0009 (the MIDI output, session midi-in-out).** The transmit side's
  registers from the SDK's register map and FM-1-RE's MIDI document; its
  timing from the MIDI wire format. A harness test and a suite case run a
  DMA, a single byte and one queued behind a transfer, with the UART off
  and on, and check every byte's time, the pending interrupt and the
  decoded messages. Without the patch there is nothing to capture, and
  the same image's interrupt record shows the difference: on 0.4.0 its
  handler ran twice, at once on each transfer (0 and 4.0 ms; a single
  byte raised nothing), on 0.5.0 three times, as each transfer's last
  byte ended (1.600, 3.320 and 5.281 ms); the suite case's golden file
  holds that record. The spec experiment E-21 does the same against the
  checkout's fwtest (C-SPEC-EXPERIMENTS). The
  input side and every other output are unchanged: the harness suite and
  the spec experiments match their earlier golden files, and the firmware
  suite (at `1537391`) gives the same 176 files as on 0.4.0 but for the
  version each `result.json` records and its new `midi_out_bytes_dropped`
  (0).
- **0010 (the flash chip, session day-1024).** The rules and times from
  the P25Q80H's datasheet (HARDWARE-SPEC.md HW-77, HW-78). Crate tests in
  `spiflash.rs` (the write enable, the wrap, bits only cleared, a timed
  erase busy and ignoring commands, a cut part done, untimed operations
  at once); harness tests and suite cases run erases and programs from
  RAM, a handler in RAM through them, the window used while busy (a
  fault), the chip carried across runs and a power cut during an erase;
  the spec experiment E-22's results change as HW-83 says. Without the
  timing (the app's default) only a firmware that breaks the rules sees a
  difference.
- **0011 (pairs writing one register, session day-1024).** From the
  vendor compiler's code: every pair whose halves write one register in
  the firmware at `6ba587e`, the harness's test images and the spec
  experiments (at `-Os` and `-O2`) uses the head's value next. The crate
  test and the harness test (`pairwaw.S`, the compiler's own pairs as
  bytes) fail without it; the harness's image build checks that the
  compiler still emits such a pair (in `flashkeep.c`).
- **0010 and 0011 together.** The firmware's suite at `6ba587e` on fwtest
  0.5.0 (pinned) and 0.6.0 (local build): every output fwtest writes is
  byte for byte the same (342 files; `result.json` and `junit.xml`
  differ only in the version). The harness's suite and the spec
  experiments: only `flashrw` (now 15 ms of erase and program where it
  ran 5 ms) and E-22 change.
- **0012 (the USB core's port, session spec-overnight-1025).** The
  app's change, written for fwtest from the app's behaviour-only note
  (PROVENANCE P-59); the port's bits and register indexes confirmed from
  the SDK's headers and FM-1-RE (HARDWARE-SPEC.md, HW-86). Its crate test
  and harness test fail without it. The firmware's
  suite at `cf07f9e5` on fwtest 0.6.0 (pinned) and 0.7.0 (local build):
  every output fwtest writes is byte for byte the same (2 202 files;
  `result.json` differs only in the version): our firmware doesn't use
  USB.
- **The firmware.** The same comparison between fwtest 0.3.0's emulator
  and 0.4.0's (0004 to 0008): no output of the three suites changed.

## Keeping them together

A patch that changes what the emulator does goes into both: in fwtest as a
numbered patch with a harness test that fails without it, in the app from
the note in `harness/upstream/`; this table gets a row. A speed-only patch
goes into fwtest only with a test that shows it changes nothing. When the
pinned upstream commit has a fix, both drop the patch.
