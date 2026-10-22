<!--
SPDX-License-Identifier: MIT
SPDX-FileCopyrightText: 2026 japes98
-->

# Plan

An original, MIT-licensed base firmware for the M-VAVE FM-1 pocket
synthesizer (JieLi AC791N: two pi32v2 cores, 240x240 LCD, key matrix, rotary
encoders, I2S audio), written clean-room so it can ship inside the
F-Emulator iOS app, provably independent of the FM-1's GPL community
firmwares.

Each milestone has its own prompt (`docs/prompts/<Mx>.md`) and its own fresh
session. Roles are defined in CONTRIBUTING.md; requirement IDs are in
docs/REQUIREMENTS.md.

## Milestones

### M0a: foundation (firmware side)
Repo, rules, roles, exposure register, records, signing, toolchain, SDK, CI.
No firmware code yet; a placeholder translation unit proves the pipeline.
- Requirements: R-PROC-1..4, R-REC-1..2, R-REPRO-1..5, R-BUILD-1,
  R-LIC-1..2, R-PUB-1..2, R-CLEAN-1..5.
- Done when: the repo exists with the bootstrap commit and rulesets; CI on a
  pull request runs reuse lint, the commit-message check, the low-profile
  check, the toolchain container build with its checksum and the
  byte-for-byte double build; the owner's signed merge produces the first
  record with a pending OpenTimestamps proof; `tools/reproduce` works;
  EXPOSURE.md and PROVENANCE.md are complete; nothing forbidden was opened.
- Status 2026-10-22: pull request #1 merged as `2fd28219`. Its record
  (`records/2fd28219…/` on `records`) has 13 checks PASS and C-MERGE FAIL
  under the merge rule of the time (CONTRIBUTING.md, "Merge policy and its
  history"), with a pending OpenTimestamps proof (three calendars).
  `tools/reproduce 2fd28219` on the owner's Mac: REPRODUCED (both outputs
  match the record).

### M0b: harness (spec side)
Vendor the emulator crates `fm1-isa`, `fm1-core`, `fm1-soc` from the public
upstream `joakimeriksson/fm1-emu` at a pinned commit, with its MIT licence,
into `vendor/emulator/` (never the rest of that repo). Build the harness: a
Rust library and `fwtest` CLI that boots a raw image, runs N emulated ms with
a timed input script, captures RAM, the LCD (PNG), LEDs, flash, audio (WAV)
and instructions per audio block, detects halts, compares golden files, and
emits JUnit and JSON.
- Requirements: R-REPRO-*, R-LIC-*, new harness requirements (R-HARN-*).
- Done when: `fwtest` runs in CI from a pinned container, its outputs are
  deterministic, and `tools/clean-setup.sh` excludes `vendor/emulator/` and
  `harness/` from clean clones.

### M0c: hardware spec (spec side)
`HARDWARE-SPEC.md`: facts only (addresses, bits, pins, timings, protocols),
each with its source. Facts whose only source is the emulator are marked as
such.
- Done when: reviewed for "facts, not code" before the firmware side reads it.

### M0d: smallest firmware (firmware side)
Startup, linker script and `main` (a marker word, a heartbeat), written only
from `HARDWARE-SPEC.md`, the SDK and FM-1-RE's documents; booted and checked
with `fwtest`. Design choices explained in docs/DESIGN-NOTES.md.
- Requirements: R-BOOT-1, R-BOOT-2, R-BUILD-1.
- Done when: CI boots the image in the harness and the record shows the
  marker word and heartbeat.

### M0e: audit and performance
- **Similarity audit** (spec side): an isolated CI job fetches the GPL
  firmwares at pinned commits, compares our firmware against them with JPlag
  (SDK as base code, `vendor/` excluded, an unrelated permissive embedded C
  project scored as a control), and publishes scores and file names only.
- **Performance tracking** (firmware side): per-commit size and RAM, later
  emulated instructions per audio block. A 3% regression gate on
  instructions per audio block; per-milestone budgets for size and RAM,
  raised only by a pull request that says why.
- Requirements: R-AUDIT-1, R-PERF-1, R-PERF-2.

### M1 to M9 (firmware side)
- **M1** boot: clocks, interrupts, timer.
- **M2** screen.
- **M3** keys, encoders, pot, LEDs.
- **M4** audio.
- **M5** the FM engine.
- **M6** MIDI in.
- **M7** flash storage.
- **M8** UI and original presets (no Yamaha factory voices).
- **M9** packaging, and a raw-image boot path in the app.

### Level 2: real hardware
- **M10** recovery kit.
- **M11** USB-MIDI and the update handler.
- **M12** hardware checklist.

## Risks

- **The toolchain's availability and terms.** JieLi's Linux toolchain has no
  licence file (docs/TOOLCHAIN.md). We never redistribute it. If the
  download disappears, a full rebuild needs another copy (the private
  preservation repo), but every released binary stays verifiable by its
  recorded hash. The vendor's short link already points at a newer release
  (20260730.1) than the pinned one; the pinned file is fetched by its direct
  URL.
- **Packages for real hardware.** A `.fwsc` package may need M-VAVE's boot or
  update loader, which we can't redistribute. Find out from FM-1-RE's
  documents only, before M9, and record the answer here. The app is
  unaffected (it can boot our raw image). *Answer: not yet investigated.*
- **The emulator doesn't model USB**, so M11 is hardware-only.
- **Merge signatures are GitHub's.** Since 2026-10-22 the owner merges with
  GitHub's button, so merge commits are signed by GitHub (`web-flow`) and the
  owner's identity rests on GitHub's `merged_by` record, checked by C-MERGE.
  Milestone tags carry the owner's own SSH signature. The first merge's
  record shows C-MERGE FAIL under the earlier rule (CONTRIBUTING.md, "Merge
  policy and its history").
