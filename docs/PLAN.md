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
- Status 2026-10-22 (session M0b, spec side, on the owner's Mac):
  - **Setup** (pull request #3): the spec folder, its hand-made settings kept
    and guarded, M0a's transcripts archived in `sessions/clean/`; spec-side
    transcripts go to `sessions/spec/`, which clean folders leave out and
    deny (R-SEP-2).
  - **Emulator** (pull request #4): three crates vendored at upstream commit
    `43ed5580`, reproducible by `tools/fetch-emulator.sh` with a tree hash
    (C-EMU-PIN). One patch, to the workspace manifest only.
  - **Harness** (pull request #4): `fwtest`, a Rust library and CLI with no
    third-party crates, built offline in a container on digest-pinned bases
    (Rust 1.99.0). It boots raw images, takes timed inputs, captures RAM,
    the LCD (PNG), LEDs, flash, audio (WAV), instructions per audio block
    and the debug console, tells faults, halts and hangs apart, compares
    golden files, and writes JSON and JUnit. Its own tests: 23 cargo tests
    and a 13-case suite on 12 small test images built with the pinned
    toolchain. The suite's outputs were byte-identical in two amd64
    containers at different paths and on Apple Silicon natively.
  - **Separation**: docs/HARNESS.md (the clean side's manual) and
    docs/SPEC-REQUESTS.md; checks C-SEP-TERMS, C-CLEAN-FOLDER and
    C-FWTEST-PIN; requirements R-SEP-1..3 and R-HARN-1..10.
  - **Merged**: #3 as `0ad38801`, #4 as `5d4d6fd2`. The records for both
    merges are PASS, with every check run, none skipped. The second
    record's `harness/` holds the suite's JSON, JUnit and output hashes.
  - **Publishing**: `.github/workflows/fwtest-image.yml` pushed the image
    built from `5d4d6fd2` as
    `ghcr.io/japes98/small-beeps@sha256:fa74baf9…` (public; pulls without
    logging in). `config/fwtest-image` pins it, and the suite run through
    `tools/fwtest` with it gives all 47 output files with the same SHA-256
    as that record.
  - **Before the next clean session**, in the clean folder, from a shell:
    `export GIT_NO_LAZY_FETCH=1; git fetch origin;` then
    `env -u GIT_NO_LAZY_FETCH git merge -q --no-stat --ff-only origin/main`
    (only the folder's own files are fetched; without `--no-stat` the merge
    summary downloads the excluded files to count their lines, as
    happened in clean maintenance session 1), then `tools/clean-setup.sh`.
    Its live settings predate the new deny rule and the lazy-fetch
    setting, so its banner would otherwise say CONFIG MISMATCH. From then
    on, `tools/clean-update.sh` updates it.

### M0c: hardware spec (spec side)
`HARDWARE-SPEC.md`: facts only (addresses, bits, pins, timings, protocols),
each with its source. Facts whose only source is the emulator are marked as
such. It also maps fwtest's key, LED and encoder numbers to the panel and
the key matrix, and covers what docs/HARNESS.md defers to it (the memories,
the second core's release, the audio output's format and rate, the debug
message register), and answers any open spec requests.
- Done when: reviewed for "facts, not code" before the firmware side reads it.
- Requirements: R-SPEC-1..4.
- Status 2026-10-22 (session M0c, spec side, on the owner's Mac):
  - **Start** (pull request #7): the prompt; M0b's transcript archived in
    `sessions/spec/`, clean maintenance session 1's in `sessions/clean/`
    with its merge summary's spec-side file names redacted (the archiver
    now does this for clean transcripts); ten of that session's commands
    listed in `sessions/REVIEWED.json` with the owner's approval.
  - **Clean updates** (pull request #8): `tools/clean-update.sh` and the
    steps above merge with `--no-stat -q`; C-CLEAN-FOLDER updates a clean
    clone across a commit that changes `vendor/emulator/` and `harness/`
    and checks none of their blobs arrive (a control merge with a summary
    fetches 6).
  - **The spec** (pull request #9): `docs/HARDWARE-SPEC.md`, 47 entries
    (HW-1 to HW-47: 38 confirmed, 9 emulator-only) for M0d to M4, flash
    preliminary for M7, and 12 open questions. Sources: the JieLi SDK,
    FM-1-RE's hardware documents, the ST7789V datasheet, the panel's
    printed labels (the owner's app screenshot, `docs/sources/`, and
    M-VAVE's product photo, cited by URL), and nine spec-side black-box
    experiments in fwtest (E-1 to E-9, `harness/spec-experiments/`, spec
    side), rerun in CI by C-SPEC-EXPERIMENTS. Reviewed by a fresh
    subagent given only the spec, CONTRIBUTING.md and the rules;
    its report and the response are in `docs/reviews/M0c-spec-review.md`.
  - **Checks**: C-SPEC-LINT (entries, sources, standings, no code, IDs
    kept), C-SPEC-EXPERIMENTS; C-SEP-TERMS now scans the two doors for
    emulator-only identifiers.
  - **Found on the way**: while an image waits, fwtest's captures can come
    several milliseconds late; docs/HARNESS.md ("Time") now says so.
  - No spec requests were open. M0d (firmware side) is next.

### M0d: smallest firmware (firmware side)
Startup, linker script and `main` (a marker word, a heartbeat), written only
from `HARDWARE-SPEC.md`, the SDK and FM-1-RE's documents; booted and checked
with `fwtest`. Design choices explained in docs/DESIGN-NOTES.md.
- Requirements: R-BOOT-1 to R-BOOT-5, R-BUILD-1, R-BUILD-2.
- Done when: CI boots the image in the harness and the record shows the
  marker word and heartbeat.
- Status 2026-10-22 (session M0d, firmware side, on the owner's Mac):
  - **Start**: the clean folder fast-forwarded with lazy fetching off;
    `tools/clean-update.sh` passed. Nothing was left to archive (the
    session the prompt named is this one); `tools/check-transcripts.py`
    PASS.
  - **The firmware** (`firmware/`): `crt0.S` sets the stack and calls
    `sb_start`, which copies initialised data, clears zeroed data and runs
    `main`. `main` writes the marker `SB0D` to a four-word beacon at
    `0x01C00000` and a line to the debug console, then keeps a heartbeat
    of one beat per millisecond of TIMER4, without interrupts. Freestanding
    C11 with `-nostdinc`, no library code of any kind, one assembly file.
    Sources: HW-1 to HW-7, HW-12, HW-13, HW-25, HW-26 (all confirmed; no
    emulator-only fact relied on), the SDK's `WL82.h`, and our own
    toolchain experiments (PROVENANCE P-13 to P-15).
  - **Size**: code 252, data 4, bss 20 bytes; raw image 256 bytes; stack
    4 KiB reserved. Recorded by C-FW-SIZE (R-BUILD-2).
  - **Tests**: `tests/fw/boot.suite` through `tools/fwtest`, checked by
    `tools/fw-suite.py` (C-FW-SUITE): golden marker, console line and top
    of RAM; a one-second heartbeat whose time base agrees with fwtest's
    emulated time within 10 µs. Requirements R-BOOT-3 to R-BOOT-5 and
    R-BUILD-2 added.
  - **Found on the way**: fwtest counts the heartbeat's polling loop as
    waiting even though it stores to RAM each pass, so captures came up to
    1.6 ms late; the beacon's stored tick count keeps the timing checks
    exact (docs/DESIGN-NOTES.md). `ld --oformat binary` resolved a data
    address wrongly, so the raw image is made with `objcopy`.
  - **Privacy** (the owner's addendum, `docs/prompts/M0d-addendum.md`):
    no private term (username, real name, e-mail, hostname, local folder
    names) in the repository. `tools/check-private.py` (C-PRIVATE,
    R-PUB-3) scans tracked files and commit messages against terms the
    owner keeps in the gitignored `tools/private-terms.local` and the
    `PRIVATE_TERMS` secret, reporting file and line only; the pre-commit
    and commit-msg hooks run it too. Records unchanged since the base
    commit `80864b9` are exempt by blob hash (CONTRIBUTING.md, "Privacy").
    `tools/archive-session.py` now redacts the username, the top folder
    (as `<top>`) and the terms. The pull request's branch was rewritten
    once, before merge and with the owner's approval, so the local path
    in the saved M0d prompt never reached main; `docs/EXPOSURE.md`'s
    older paths are redacted in its current text.
  - **Merged**: pull request #10 as `4760d561`. Its first record
    (`records/4760d561…/`) is FAIL on C-MERGE alone: the records workflow
    read the head's ci run while GitHub still reported it in progress,
    although its only job had finished with success (13:25:15Z; GitHub
    marked the run complete at 13:35:00Z). That record stays as it is. A
    re-run of the records workflow wrote `rerun-39787187755-2/` beside
    it: **PASS**, every check run, traceability PASS for R-BOOT-1 to
    R-BOOT-5, R-BUILD-1, R-BUILD-2 and R-PUB-3, firmware size code 252,
    data 4, bss 20 bytes. Since pull request #11, C-MERGE waits up to 30
    minutes for an unfinished ci run on the head.
  - `firmware/src/placeholder.c` removed. M0e is next.

### M0e: audit and performance
- **Similarity audit** (spec side): an isolated CI job fetches the GPL
  firmwares at pinned commits, compares our firmware against them with JPlag
  (SDK as base code, `vendor/` excluded, an unrelated permissive embedded C
  project scored as a control), and publishes scores and file names only.
- **Performance tracking** (firmware side): per-commit size and RAM, later
  emulated instructions per audio block. A 3% regression gate on
  instructions per audio block; per-milestone budgets for size and RAM,
  raised only by a pull request that says why.
- Requirements: R-AUDIT-1, R-PERF-1 to R-PERF-5.
- Status 2026-10-22, performance part (session M0e, firmware side, on the
  owner's Mac):
  - **Start**: `tools/clean-update.sh` passed; M0d's two transcripts
    archived (the archiver's e-mail rule fixed on the way: it broke a
    line's JSON when an address followed a tab escape); three of their
    commands, which only wrote text naming the spec-side folders, listed
    in `sessions/REVIEWED.json` with the owner's approval.
  - **Measured on every commit** (`tools/perf.py`, check C-PERF, in each
    record's report and its "Performance" section): code, data, bss, the
    raw image, static RAM (data + bss), the stack reserved and its
    high-water mark, and emulated core-0 instructions per period. Until
    M4 the period is the heartbeat: a one-second perf run of its own in
    fwtest, its instructions divided by the beats. The stack's mark is
    the lowest non-zero word of the stack captured at the end (fwtest
    starts RAM at zero), so the firmware needs no change for it.
  - **Gates**: the budgets in `config/budgets.json` for the current
    milestone, and a rise of at most 3% in instructions per period
    against the latest main record, whose own image is re-run under the
    same fwtest. A fall of more than 3% shows as IMPROVED in the record
    and in the CI run's summary. Raising a budget takes its own pull
    request (CONTRIBUTING.md). C-PERF-PROBES builds the firmware once
    deliberately slower and once deliberately bigger and checks that the
    gates fail each for its own reason, against the unmodified build
    measured in the same run. Requirements R-PERF-1 to
    R-PERF-5; design: docs/DESIGN-NOTES.md (M0e).
  - **History**: the records workflow appends one line per main commit
    to `perf-history.csv` at the root of the `records` branch, never
    rewriting it; a re-run adds no line.
  - **C-MERGE's three failures, and the fix** (pull request #15): every
    other check passed in each of these records, and each FAIL record
    stays as it is.
    1. M0a's merge (`2fd28219`) failed under the merge rule of that time
       (CONTRIBUTING.md, "Merge policy and its history").
    2. #10's merge (`4760d561`) failed because GitHub still reported the
       head's ci run as in progress after its job had passed. Since #11,
       the check waits for an unfinished run.
    3. #13's merge (`a2086340`) failed because GitHub's run search briefly
       found no ci run for the head, though its CI had passed about ten
       minutes before; the check took no answer as a failure at once.
       Its `perf-history.csv` line says FAIL. A re-run of the records
       workflow writes a PASS record beside it and, being a re-run, adds
       no line.

    Since #15, an empty answer is asked again like an unfinished run, with
    backoff (10 s, doubling, at most 300 s) up to the same 30 minutes.
    Triggering the records workflow from the ci run's completion
    (`workflow_run`) was considered, so there would be nothing to search
    for. It can't serve: `ci` runs only on pull requests, and a trigger of
    the push to main describes the merge commit's run, not the pull
    request head's run, which is what C-MERGE must prove passed.
  - **M0d's firmware, measured**: code 252, data 4, bss 20 bytes; image
    256; static RAM 24; stack high-water 0 of 4 096 bytes (no function
    uses the stack); 356 887 instructions over 1 000 heartbeat periods,
    356.887 per period. Nothing in it looked wasteful in the
    disassembly, so no fix was needed. The probes: the slower build
    reads 439.450 per period (+23.13%, FAIL), the bigger one code 1 348,
    static RAM 280 and stack high-water 516 bytes (each FAIL).
  - **M0 budgets**: code 512, static RAM 64, stack high-water 256 bytes;
    speed gate 3%.
  - **Merged**: pull request #12 as `a754ebc9`. Its record
    (`records/a754ebc9…/`) is **PASS**, every check run, traceability
    PASS for R-PERF-1 to R-PERF-5. C-PERF found the record of `5c6efc66`
    (main before the merge) as its baseline, re-ran that image: +0.00%.
    `perf-history.csv` on `records` started with the merge's line (code
    252, static RAM 24, stack high-water 0, 356.887 instructions per
    heartbeat period). This pull request's merge adds the second.
  - The similarity audit is the spec side's part of M0e. M1 is next on
    the firmware side.

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
