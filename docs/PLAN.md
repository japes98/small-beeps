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
- Requirements: R-AUDIT-1 to R-AUDIT-6, R-PERF-1 to R-PERF-5.
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
  - **C-MERGE's three failures, and the fix** (pull request #17): every
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
       Its `perf-history.csv` line says FAIL.

    Since #17, an empty answer is asked again like an unfinished run, with
    backoff (10 s, doubling, at most 300 s) up to the same 30 minutes.
    Triggering the records workflow from the ci run's completion
    (`workflow_run`) was considered, so there would be nothing to search
    for. It can't serve: `ci` runs only on pull requests, and a trigger of
    the push to main describes the merge commit's run, not the pull
    request head's run, which is what C-MERGE must prove passed.
  - **Four merges in two minutes, and what followed** (pull request #18):
    - #15, #16, #14 and #17 merged between 15:12:43Z and 15:14:02Z. The
      records workflow had one concurrency group, and GitHub keeps only
      one waiting run per group, so it cancelled the records of #15
      (`f5740bc8`), #16 (`3c83ffed`) and #14 (`9ebd2588`). Since #18 each
      commit has its own group, and a push to `records` that another run
      beat is redone on a fresh clone (never forced).
    - The cancelled runs were re-run one at a time. #14's record is PASS.
      #15's and #16's, and two re-runs of #13's (`rerun-39801409823-2`
      and `-3`), are FAIL on C-MERGE alone: GitHub's "pull requests of a
      commit" endpoint answered HTTP 500 in CI, and an empty answer from
      here, for those heads.
    - Since #18 the check finds the pull request that GitHub's merge
      message names, and accepts it only if its head is the merge's
      second parent and its merge commit is the merge. Failing that, it
      looks among closed pull requests into main. It also asks again
      after a GitHub API error that may pass (5xx, 429, no answer). Run
      from here against the merges of #13, #14, #15 and #16, it passes
      all four (for #16's, the run search found nothing at first and the
      retry found it 10 s later).
    - A re-run uses the check of its own commit, so those FAIL records
      can't be re-run to PASS; they stay, and every later record uses the
      fixed check.
    - `perf-history.csv` has one line for each main commit since #12
      (`a754ebc9`, `a2086340`, `193cb61c`, `f5740bc8`, `3c83ffed`,
      `9ebd2588`), in the order the records were written, not the order
      of the commits. The lines of #13, #15 and #16 say FAIL.
  - **Those three merges, re-checked** (pull request #20,
    `.github/workflows/recheck-merge.yml`): a workflow started by hand
    re-runs only C-MERGE on a merge already on main, with the merge
    check on main, and adds `records/<sha>/verified-<date>/` beside the
    record. It holds the check's log, the result, the checker's commit
    and SHA-256, the reason, the run, checksums and their OpenTimestamps
    proof. Its push is refused unless every change is a new file in that
    folder.
    - Run on 2026-10-22 with the checker from `d474fd3c` (main after
      #20), for #13 (`a2086340`), #15 (`f5740bc8`) and #16 (`3c83ffed`):
      **PASS** for all three. Each found its pull request, merged by the
      owner, and that pull request's head's successful ci run (#13:
      39799063783, #15: 39801730601, #16: 39801503047).
    - The records branch's three commits for these runs only add the five
      files of each `verified-2026-10-22/`; the original records, their
      re-runs and `perf-history.csv` are unchanged, so those lines still
      say FAIL, and the verification beside each record says why.
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
    heartbeat period). Pull request #13's merge adds the second.
  - **The stack measurement, proved** (the owner's request after #12's
    record read 0): a test build with a 1 KiB frame written with zeros
    read 0 by the first method (lowest non-zero word), so that method
    could not see stack written as zero. Now `sb_stack_fill` (`crt0.S`)
    fills the unused stack with a pattern right after the time base
    starts, and the mark is the lowest word no longer holding it.
    C-PERF-PROBES' new `SB_PROBE_STACK` build must read at least 1 024
    bytes (it reads 1 024). The firmware itself still reads 0, and its
    disassembly says why: no push, pop or `sp`-relative access anywhere,
    and `sb_start` and `main` never return, so neither saves `rets`
    (docs/DESIGN-NOTES.md). Cost: code 280 bytes (+28), 358.934
    instructions per heartbeat period (+0.57%, within the gate).
  - The similarity audit is the spec side's part of M0e. M1 is next on
    the firmware side.
- Status 2026-10-22, spec part (session M0e-spec, spec side, on the
  owner's Mac):
  - **Start** (pull request #15): M0c's transcript archived; the prompt
    saved as `docs/prompts/M0e-spec.md`.
  - **The two doors** (pull request #15): `check-emulator-terms.py`
    accepts any term in `docs/HARDWARE-SPEC.md` or `docs/HARNESS.md` as on
    main, read from main's blobs (a branch can't launder a term into a
    door). Eight reviewed entries dropped, one kept.
  - **Timer polling** (pull request #16): docs/HARNESS.md ("Time") now says
    exactly what counts as waiting: the wait-for-interrupt instruction, or
    three or more reads of the free-running timer's count within 64 cycles
    of each other outside an interrupt handler. It says what that does to
    capture times, and how to get exact timing. The behaviour is as
    designed, so the harness is unchanged and there is no new image.
    Exact captures while waiting would change capture times, and with them
    golden files on both sides. That is an option for the owner.
  - **The similarity audit** (docs/AUDIT.md, R-AUDIT-1 to R-AUDIT-6):
    - **Targets:** 780 FM-1 repositories found from metadata alone (the
      owner chose every FM-1 repository): 516 scored, 262 duplicates by
      tree, 2 empty. All are pinned by commit and tree in
      `audit/targets.json`. Felucca Salt and Felucca 8 Patterns are
      unresolved: no repository found.
    - **Rediscovery:** monthly, by `audit-discover.yml`, which opens or
      updates an issue when the targets change; a spec-side session turns
      it into a pull request (the owner chose an issue over letting
      workflows open pull requests).
    - **The job:** `audit.yml` runs JPlag 6.3.0 (pinned by hash, in a Java
      image pinned by digest) on our firmware and the control
      (pico-examples at sdk-2.2.0), with the SDK as base code.
    - **The gate:** a pair fails above the control's longest match plus
      24 tokens. The longest match was chosen by a calibration between two
      unrelated permissive projects: chance runs stay at 33 tokens or
      below, while the ratio reaches 0.857.
    - **Isolation:** the targets exist only in a job with no secrets, and
      only scores and file names reach the record
      (`records/<sha>/audit/`).
    - **First run** (the merge `362480c8`, docs/AUDIT.md "The first run"):
      PASS in under 4 minutes, so pushes run the full set. 516 targets,
      18,498 files; the control's baseline was 35 tokens (threshold 59), no
      target was control-related, and our best pair was a 12-token match.
      Its report is in the record, beside the main record.
    - **The self-test gap** (2026-10-23, a spec session; docs/AUDIT.md,
      "The self-test gap"). From M2's firmware on, the self-test failed
      with "8 of our 9 files found". The file was `src/font.c`, a single
      table JPlag makes 5 tokens of, so it drops it as `TOO_SMALL`. In
      these runs the gate passed, but `src/font.c` was compared with
      nothing. The merges that ran without a passing self-test:
      - #34, #35 and #36: their own audit runs were cancelled while
        queued. #37's run covered their commits;
      - #37 (run 39877916755), #40 (run 39886734506) and #45 (run
        39888000310): self-test FAIL, gate PASS.

      Those runs stay red in the records. **The fix:** a file JPlag cannot
      score is reported as "not scorable by JPlag", with the reason, and
      goes to a text check (C-AUDIT-TEXT). That check finds exact copies,
      and the share of the file's normalised text in each target file, and
      fails at 0.5. The threshold is calibrated on the same permissive
      pair as the gate. The self-test now also finds a reformatted copy of
      each file, so it covers the text check too.
  - **Auditor role**: CONTRIBUTING.md, `config/claude/auditor.json`,
    `tools/auditor-setup.sh`. Its transcripts go to the owner's private
    repository (created when the first auditor session runs), never here.
    None has run.
  - No spec requests were open.

### M1: boot (firmware side)
- Clocks, interrupts and a timer: from reset to a known, timed,
  interrupt-driven state (docs/prompts/M1.md).
- Requirements: R-CLK-1, R-IRQ-1 to R-IRQ-5; R-BOOT-3, R-BOOT-5 and
  R-PERF-3 amended.
- Status 2026-10-22 (session M1, firmware side, on the owner's Mac):
  - **Start**: `tools/clean-update.sh` passed. M0e's clean transcript was
    archived; the archiver's host-name rule was fixed on the way (it broke
    a line's JSON after a newline escape). Three of its commands were
    listed in `sessions/REVIEWED.json` with the owner's approval (#24).
    The M0 release was made from the signed tag `m0`: the image and ELF,
    rebuilt bit for bit, an SPDX SBOM, and the record linked by its tree
    hash. The record itself is not attached: its C-TRANSCRIPTS log holds a
    private term.
  - **Checks, at the owner's request** (#25):
    - The transcript check clears a quoted `python3` heredoc that provably
      opens only `sessions/REVIEWED.json` or `sessions/clean/` files, and
      its log never quotes a transcript (19 of 21 earlier records carry
      such lines; they stay as they are).
    - Records, audit reports and re-checks withhold any file holding a
      private term, keeping its name and SHA-256 (C-RECORD-PRIVATE).
    - Artifacts are kept 14 days.
  - **Spec requests** (#26): SR-1, what raises the exception source, on
    the chip and in fwtest; SR-2, clock set-up on the chip (Q-2). Both
    open.
  - **Budgets** (#27): M1's are code 2048, static RAM 160 and stack 256
    bytes.
  - **Firmware** (#28; docs/DESIGN-NOTES.md, M1):
    - **Clock:** no clock register is written. The core clock is measured
      at startup: 240 time-base ticks for 2 402 cycles, i.e. 240 MHz.
    - **Vector table:** all 128 slots are written. TIMER0's is the tick;
      every other source has its own 2-byte stub that reports it by number
      and halts.
    - **Tick:** TIMER0 at 1 ms keeps the heartbeat in whole milliseconds of
      the 24 MHz time base. In fwtest TIMER0's 1 ms is 24 000.7 to 24 001
      time-base ticks, so the heartbeat doesn't count ticks.
    - **Idle:** core 0 idles between ticks.
    - **Faults:** a stack guard is checked every tick. A stray interrupt,
      a stack overrun or a CPU fault is reported on the debug channel and
      halts cleanly. Core 1 stays parked.
  - **Results** (local runs; the records of the merges are authoritative):
    - First tick by 1.013 ms; every tick interval is 24 001 time-base
      ticks (jitter 0, tolerance ±24).
    - The suite run twice gives identical outputs, all 27 files.
    - **69.2 instructions per period against M0's 358.9: −80.7%.**
    - Code 1168, static RAM 80, stack 64 bytes.
    - The fault and stray test builds halt with `HALT stack 001` and
      `HALT stray 07f`.
  - **Open:**
    - R-IRQ-5, a real CPU fault: no deliberate fault reaches the exception
      source in fwtest, and an undecodable instruction is fwtest's own
      fault (a suite case shows that limit). It waits for SR-1.
    - The clock set-up on the chip waits for SR-2.
  - **Next: M2, the screen.**

### M2: the screen (firmware side)
- Drive the LCD from our own code: bring-up, a frame buffer sent by DMA,
  drawing, our own font, a test screen with the heartbeat on it
  (docs/prompts/M2.md).
- Requirements: R-LCD-1 to R-LCD-5; R-IRQ-1, R-IRQ-2, R-BOOT-3 and
  R-PERF-1 to R-PERF-5 amended.
- Status 2026-10-22 (session M2, firmware side, on the owner's Mac):
  - **Start** (#30): `tools/clean-update.sh` passed. M1's transcript was
    archived. The transcript check's gap was closed: a folder name ended
    by `;` or another shell operator is now matched. 22 flagged calls were
    listed in `sessions/REVIEWED.json` with the owner's approval.
    The M1 release was made from the signed tag `m1`: the image and ELF,
    rebuilt bit for bit, an SBOM and checksums, with the record linked by
    tree hash and SHA256SUMS hash.
  - **Two barrier gaps closed:**
    - `tools/reproduce` used `git archive`, which with lazy fetching on
      downloads spec-side files into a clean folder's `.git` (#30).
    - The pre-commit private-terms scan read staged spec-side files after
      a merge, which with lazy fetching on would fetch them (#34).
    - Neither fetched anything here: lazy fetching was off, and the
      barrier checks passed before and after.
  - **The speed gate, by the owner's decision** (#31): perf measures
    startup and steady state apart, from two runs (1.25 and 2.25 s). Each
    has a budget per milestone. The 3% gate applies to steady state
    between records under the same budget. M1 re-measured: startup 5 193
    instructions, steady state exactly 64.000 a period.
  - **M2 budgets** (#33): code 8 192, static RAM 122 880, stack 512,
    startup 1 572 864, steady state 72 a period (unchanged).
  - **Firmware** (#35; docs/DESIGN-NOTES.md, M2):
    - **Bring-up:** software reset, 120 ms, sleep out, 5 ms (waited on the
      tick), 16-bit pixels, `MADCTL` 0, the first frame with the display
      off, display on.
    - **Frame buffer:** 240 × 240 RGB565, high byte first (115 200
      bytes). Sent by DMA straight from the buffer: a whole frame is 15
      chunks of 16 rows, chained by SPI1's interrupt, below the tick in
      priority.
    - **Drawing and font:** fill, frames, lines, text, and our own font
      (printable ASCII, 5 × 8, drawn as `#`/`.` rows).
    - **Screens:** an address pattern, in which each pixel's colour
      encodes its address, then a test screen (border, corner colours,
      ramps, lines, every glyph). The heartbeat's seconds are drawn once a
      second, and only their rows sent.
    - **Found on the way:**
      - fwtest raises source 16 at the end of every DMA transfer, even with
        `CON` bit 13 clear (reported in SR-3).
      - An idle wait for a chained frame's end could sleep until the next
        tick; it now spins.
      - Startup's clearing of the frame buffer delays the time base by
        0.24 ms, so the end check's slack follows bss.
  - **Results** (local runs; the records of the merges are authoritative):
    - Every one of the 57 600 pattern pixels is right; the test screen's
      border, corners and ramps are right; the golden images match.
    - With whole frames back to back for 1 s (233 809 frames), every tick
      interval stays 24 001 or 24 002 (±24 allowed).
    - **A whole frame: 6.3 µs of the core in fwtest**, where a transfer
      finishes at once; on the chip at least 60.8 ms of transfer (the
      datasheet's 66 ns a bit), with the core free.
    - **Steady state 65.415 instructions a period, +2.2%** on M1.
      Startup 1 036 288. Code 4 180, static RAM 115 340, stack 188 bytes.
  - **Spec request** (#36): SR-3, the panel's wiring, SPI1's set-up,
    offset, orientation and inversion on the chip (Q-6), the longest
    transfer, and source 16 in fwtest. M2 doesn't depend on it.
  - **Next: M3, keys, encoders, the pot and LEDs.**

### M3: keys, encoders, the pot and LEDs (firmware side)
- Read every control on the panel and drive its LEDs, through one input
  API, with a live panel screen (docs/prompts/M3.md).
- Requirements: R-KEY-1 to R-KEY-3, R-ENC-1, R-ENC-2, R-POT-1, R-POT-2,
  R-LED-1 to R-LED-3, R-INPUT-1 to R-INPUT-3; R-IRQ-1, R-IRQ-2 and R-PERF-2
  amended.
- Status 2026-10-23 (session M3, firmware side, on the owner's Mac):
  - **Start** (#38): `tools/clean-update.sh` passed. M2's transcript was
    archived. Its 5 flagged calls (13 entries) were reviewed and the owner
    approved them in the session.
  - **The speed gate** (#39, the owner's decision): the first record made
    under a raised steady-state budget, the raise's own merge, which still
    holds the older firmware, is not a 3% baseline. The change is
    reported, and every budget still holds.
  - **M3 budgets** (#41): as M2's, except steady state 72 to 1 152 a
    period.
  - **Barrier tools** (#43, the owner's request): the three spec-side
    folders are listed once, in `config/spec-side-folders`. The barrier
    tools build every name and pattern from that list, and their tests
    use made-up names; a test pins the generated rules to the old ones by
    hash.
  - **Firmware** (#42; docs/DESIGN-NOTES.md, M3):
    - **The scan:** TIMER1, 12 slots of 83.3 µs a millisecond, one column
      each and one blank. A single 0 walks through the column shift
      registers, one shift and one latch a slot. Rows are read at the
      next slot, and the LEDs are lit with their column. The tick stays
      above it in priority.
    - **Keys:** 41, debounced over 4 scans.
    - **Encoders:** 7, decoded from their contacts' order, one event per
      detent.
    - **The pot:** polled once a scan; the mean of 4 readings, a dead band
      of 3, both ends reachable.
    - **LEDs:** 41, with 9 brightness steps.
    - **The input API** (`firmware/src/input.h`): one queue of 8-byte
      events (control, kind, value, time), `input_read`, `input_value`
      and `input_led`. Control IDs are named after the printed labels.
    - **The panel screen:** from the first touch on, every control's state,
      the last event and the heartbeat.
  - **Results** (local runs and the pull requests' CI; the merges' records
    are authoritative):
    - Each of fwtest's 41 keys and 7 encoders gave its control by our own
      black-box test, and each key lit only its own LED.
    - Key latency 2.83 to 4.11 ms; detents within 1.10 ms; the pot's
      first event within 0.82 ms and its value within 3.82 ms.
    - From an event to its LED: set by main within 1.0 µs, then driven by
      the scan within 0.916 ms (its column comes round again), measured
      by the firmware; brightness within 1.25 thousandths of each step.
    - No ghost at a matrix rectangle's fourth corner in fwtest.
    - Tick intervals stayed 24 001 to 24 002 time base ticks under the
      heaviest input.
    - **Steady state 992.03 instructions a period** on fwtest 0.2.0 (991.99
      on 0.1.x; M2: 65.415), 0.41% of
      core 0 at 240 MHz: keys about 127, encoders 94, the pot 27, LEDs
      142, and about 533 for 12 interrupts and main's wakes a
      millisecond. A slower or interrupt-driven scan was weighed and not
      taken.
    - Startup 1 037 912 instructions; code 7 024 bytes, static RAM
      117 792, stack 280.
  - **Open:** which printed label each fwtest number is (HW-37, HW-39) is
    emulator-only; the owner is to confirm it by hand on the app's panel
    screen. The board's wiring, diodes and pin set-up are Q-7 (SR-3).
  - **Next: M4, audio.**

### M4: audio (firmware side)
- Get sound out: the audio output double-buffered on its interrupt, one
  audio API for engines, a test instrument, underruns reported
  (docs/prompts/M4.md).
- Requirements: R-AUD-1 to R-AUD-7; R-IRQ-1, R-IRQ-2, R-PERF-2 and
  R-PERF-4 amended.
- Status 2026-10-23 (session M4, firmware side, on the owner's Mac):
  - **Start** (#49): `tools/clean-update.sh` passed. M3's transcript was
    archived; the restart session after M3's server stopped is in the same
    transcript. Its 18 flagged calls (47 entries) were reviewed, and the
    owner approved them in the session.
  - **The transcript check** (#51, the owner's request): it now tells an
    access from a mention. It strips only the spans it can prove are
    mentions, matches the same rules against the rest, and never flags
    more than text matching. Text matching still runs, report only. Of the
    124 REVIEWED.json entries that clear a hit, 70 would not have been
    flagged.
  - **Tidy-up** (#50): SPI1's handler path for a polled transfer's
    interrupt, unused since fwtest 0.2.0, removed. A build that halted on
    that path passed the whole suite first.
  - **M4 budgets** (#52): code 10 240, static RAM 131 072, stack 512,
    startup 1 572 864, steady state 2 048 instructions an audio block.
  - **Firmware** (docs/DESIGN-NOTES.md, M4):
    - **Output:** `JL_ALNK0` at 24 MHz / 544 = 44 117.647 Hz, two halves of
      64 stereo frames (1.451 ms each), 24-bit samples. Source 11's handler
      refills the finished half at the lowest priority; the scan and SPI1
      are at 1 and the tick at 2. Output latency is one to two blocks.
    - **The audio API** (`firmware/src/audio.h`): one block callback that
      writes 64 frames straight into the half to be played. The engine
      reads events with `input_read_audio` (`input.h`), from its own queue
      of the same events.
    - **Underruns:** a half missed, or a refill still going when the next
      half finishes, is counted and reported as `AUDIO UNDERRUN nnnn` on
      the debug channel.
    - **The test instrument** (`firmware/src/synth.c`): four sine voices
      on the 27 keys (KEY1 = F3, OCT-/OCT+ two octaves each way), 5 ms
      attack and 20 ms release, level from MASTER (its position squared),
      and a 1 kHz test tone at -6 dBFS on PLAY. Fixed point throughout,
      with the sine table computed at startup. Core 1 stays parked.
  - **Results** (local runs; the merges' records are authoritative), by
    our own analysis at the true rate (`tools/audio_analysis.py`):
    - Test tone: 1 000.000000 Hz (0.00000 cents), -6.021 dBFS, THD+N
      -92.2 dB.
    - Eight notes F1 to G7 within 0.0003 cents, levels within 0.001 dB.
    - No clicks at any start or stop; digital silence at rest.
    - Key contact to sound 4.8 to 6.8 ms; press event to sound 1.6 to
      2.9 ms.
    - 11 s of M3's heaviest input with every voice and the tone: no
      underrun, every tick on time, and every one of 5 886 events reached
      the engine. The longest refill was 40 µs of a 1 451 µs block.
    - A test build late for one block in 64 reported each late block
      once. The golden WAV matched exactly.
  - **Cost and headroom for M5**, instructions an audio block of 348 160
    cycles (R-PERF-2's period from M4):
    - Without audio, about 1 440 (M3's input).
    - The output path alone, 1 742.
    - The instrument at rest, 1 813 (0.52% of core 0).
    - All five oscillators, 9 927 (2.85%).
    - About 345 000 cycles a block, 99% of core 0, are left for M5's engine
      (less main's drawing), and core 1 is free. fwtest runs one
      instruction a cycle; the chip, running from flash through its
      cache, will be slower.
    - Code 8 636 bytes, static RAM 123 936, stack 336, startup 1 058 323.
  - **Open:** Q-9, the chip's codec, clock and true rate (fwtest needs no
    set-up).
  - **Next:**
    - **M4b**, a platform test: port a permissively licensed engine from
      its original source as a separate demo build, to measure real DSP
      load through the audio API. Mutable Instruments' Plaits (MIT) is
      the first candidate. Each source is logged in PROVENANCE.md, and
      the firmware itself is unchanged.
    - Then **M5**, the FM engine.

### M4b: platform load test, and the loaded-case budget (firmware side)
- Measure what the chip can afford before M5's engine is designed: a
  loaded speed measure and its budget, and Mutable Instruments' Plaits
  (MIT) ported as a separate demo build (docs/prompts/M4b.md).
- Requirements: R-PERF-1, R-PERF-2, R-PERF-4, R-PERF-5 and R-SEP-1
  amended; R-REPRO-7 and R-PLAITS-1 to R-PLAITS-4 new.
- Status 2026-10-23 (session M4b, firmware side, on the owner's Mac):
  - **Start** (#55): M4's transcript archived; its 3 flagged calls, each
    naming a rule only, approved by the owner. **Neutral rule IDs** (#56,
    the owner's request): the transcript check's rules are `F-1` to
    `F-13`, so naming one no longer flags a command.
  - **The loaded measure** (#57): the perf runs again under a fixed script
    driving every voice and every control (`tests/fw/scripts/perfload.txt`),
    with its own budget, 3% gate and baseline rule, a probe build that
    proves the gate, and `perf-measures.csv` (one row per commit and
    measure; the owner's design). **M4 loaded budget** (#58): 131 072.
    M4's firmware: **114 173 instructions a block** under load, against
    1 813 at rest. Of that, 90% is the panel's drawing (about 66 000 an
    input event), 7% the audio engine, 2% the scan, 1% sending.
  - **Plaits vendored** (#59): 127 files from pichenettes/eurorack and
    stmlib at pinned commits, unmodified, every file MIT; C-PLAITS-PIN.
    C-SEP-TERMS counts its terms as public like the SDK's (the owner's
    decision, with conditions).
  - **The demo** (#61): its own image (`tools/build.sh build --demo
    plaits`), our audio and input APIs only. It needed our own IEEE 754
    soft-float (bit for bit against an exact reference), memory functions,
    six standard headers and two C++ handlers; Plaits builds unmodified.
    C-PLAITS-BENCH measures it in every record.
  - **Spec requests** (#60): SR-4 (the audit: Plaits as base code, spec
    side to make), SR-5 (hardware float on the chip), SR-6 (both cores
    on the chip).
  - **Results** (fwtest, an instruction a cycle; docs/DESIGN-NOTES.md,
    M4b):
    - **Soft-float:** 0.6 to 1.8 million instructions a block per engine,
      2 to 5 blocks' time: only chiptune plays live. Not viable for M5.
    - **Hardware float** (the toolchain's `fprev1`, which fwtest runs and
      the SDK's builds use; SR-5 open): 10 600 to 52 600 a block, 6 to 32
      voices an engine on core 0, the same sound bit for bit.
    - **Core 1** starts and renders a second voice: two at once take half
      the time (fwtest has no contention; SR-6).
    - **For M5:** an FM operator is at most 40 instructions a sample
      (Plaits' six-op, all-in) against M4's fixed-point sine at 25.6: about
      135 operators on core 0 at rest, 91 under the heaviest input, and
      about 135 more on core 1. Plan for half on the chip.
    - **API before M5:** an engine context pointer, knobs as clamped
      parameters, a deadline the engine can see, core 1 as an API, and the
      screen's redraws coalesced to a frame rate.
  - **Next: M5, the FM engine.** Fixed point needs no answer from SR-5;
    floats would. The demo is not shipped in releases.

### M5: the FM engine (firmware side)
- Status 2026-10-23 (session M5, firmware side, on the owner's Mac): done,
  in pull requests #64 (start), #65 (build flags), #66 (screen), #68
  (SR-7), #69 (budgets) and #70 (the engine).
  - **Build flags** (#65): `-mcpu=r3 -mfprev1` as SR-5's answer says
    (HW-62); the image didn't change. `-mcpu=r3` alone turns the float
    instructions on, so the Plaits demo's own C keeps its old flags.
  - **The screen** (#66): drawn in frames of 16 ms, within a drawing
    budget of an eighth of each audio block (R-LCD-6). **Loaded measure
    114 173 to 15 522 instructions a block, 86% less**; LEDs still set as
    each event comes.
  - **The engine** (#70; docs/DESIGN-NOTES.md, M5): six operators a
    voice, our own sine and ten algorithms, envelopes per operator and
    for pitch, velocity, an index limit against aliasing; 16 voices, 8 on
    each core, allocation and click-free stealing; mono with legato and
    glide; a versioned patch format (docs/PATCH-FORMAT.md) and nine test
    patches of our own; minimal controls (PRESETS, ALGORITHM, KNOB1 to
    KNOB4, SEL with MONO/POLY). R-FM-1 to R-FM-9.
  - **Tests**: FM sidebands within 0.002 dB of the Bessel functions;
    envelope stages within 0.9 ms; glides within 0.05 semitones; velocity
    within 0.03 dB; stealing without a click; 11 s of the heaviest input on
    all 16 voices without an underrun; identical output on two runs;
    golden WAVs for every test patch.
  - **Figures** (fwtest): about 24 instructions an operator-sample; at
    rest 1 803 a block; loaded 84 918 (24% of core 0; core 1 about 22%);
    about 37 six-operator voices a core would fit, 16 ship, a margin of
    four times for the chip. Code 15 696 bytes, static RAM 142 008, stack
    388 (the M5 budgets, #69).
  - **Spec request SR-7** (#68): fwtest doesn't run a two-register load
    the compiler emits; a short, documented workaround until it does.
  - **The similarity audit** passes on #70's commit (no pair flagged,
    no text match). Its self-test has failed on every main commit since
    #61 (it finds 25 of our 30 files in its made-up copy; the Plaits
    demo's small files are the likely misses): the owner decides who fixes
    it (the audit's tooling is the spec side's, SR-4).
  - **The self-test fixed** (2026-10-24, session midi-in-out; docs/AUDIT.md,
    "The second self-test gap"). The misses were four of the demo's files,
    matched in full but split by the Plaits base code, and `src/audio.h`,
    which JPlag matched with nothing. A copy is now also found by its
    similarity, and a file JPlag matches with nothing goes to the text
    check; the self-test finds 30 of 30. The merges that ran without a
    passing self-test, the gate and the text check passing in each:
    - #61, #64, #65, #66, #68 and #69: "23 of our 27 files";
    - #70 to #79 (#70, #71, #72, #73, #74, #75, #76, #77, #78, #79): "25 of
      our 30 files";
    - #62: its audit run was cancelled while queued (no record); #64's
      run covered its commit.
  - **Next: M6, MIDI in.** The engine already takes notes with velocity
    (`fm_note_on`); M6 needs UART1 and the MIDI jack from the spec side
    (Q-12).

### M6a: MIDI in (firmware side)
- Status 2026-10-24 (session M6a, firmware side, on the owner's Mac): done,
  in pull requests #74 (start), #75 (SR-7's workaround removed), #76
  (spec request SR-8), #79 (the build's last instruction guard removed,
  fwtest 0.4.0) and the MIDI pull request (the parser, the engine's side,
  the receiver and the tests), which builds on SR-8's answer (#81).
  - **The receiver** (HW-67 to HW-71): the MIDI IN jack's UART1, by DMA
    into a ring, read once a block from the engine's callback; no
    interrupt. The chip's baud rate, clock and pin are still open (Q-12)
    and set only with real hardware.
  - **The parser** (our own, MIDI 1.0's rules; tools/midi_model.py is the
    same rules again for the tests): running status, realtime anywhere,
    SysEx skipped at any length, junk dropped and counted.
  - **The engine's side**: notes held apart by the panel, MIDI and the
    sustain pedal, so neither ends the other's; velocity, pitch bend (2
    semitones, RPN 0 up to 24), vibrato on the mod wheel, volume and
    expression, all notes off, all sound off, program change, mono and
    poly; a receive channel (omni by default) and a controller map in a
    versioned settings struct for M7 to save and M8 to extend; MIDI's
    notes on the panel screen.
  - **Tests**: nine fwtest MIDI cases from generated scripts, each byte
    stream checked against the model; bends within 0.002 semitones,
    vibrato ±0.49, volume and expression on their curve, all sound off
    silent within 6 ms, sustain at five times, channel 10 only, panel and
    MIDI together without stuck notes (golden screen), a full wire for
    6 s without a drop or underrun. R-MIDI-1 to R-MIDI-7.
  - **Figures** (fwtest): latency 1.7 to 2.9 ms from a note's last byte to
    its first sample (at most two blocks); at rest +2.0% (36 instructions a
    block), loaded +1.0%; code 18 408 bytes, static RAM 143 256: the M5
    budgets hold, none raised.
  - **The owner's decisions** (2026-10-24): the loaded measure includes
    MIDI (#86's M6 budgets, #87's script: 109 899 a block of 131 072);
    a program change and the mono and poly messages release held notes,
    as PRESETS does, by design.
  - **Open items:**
    - **The receiver on the chip.** HW-70 (the receive set-up bits) is
      known from the emulator only, and the baud rate, UART clock, pin
      and port set-up are not set (Q-12). The receiver also writes
      UART1's `CON0` once a block to latch the byte count (HW-69); what
      that write does on the chip, beyond the latch, is not known. To
      settle with real hardware (Level 2) or a further spec request.
    - **The dense case the prompt named can't happen on the wire.** At
      31 250 baud a block (1.45 ms) carries about 4.5 bytes, two notes
      in running status, so "all 16 voices struck again every block"
      can't arrive by MIDI. The test (mididense) and the loaded measure
      fill the wire instead (all 16 voices sounding, notes struck again
      continuously); a faster input (USB MIDI, M11) could come closer.
  - **Next: M6b, MIDI out**, waiting on the spec side (which port the FM-1
    sends MIDI on; the spec side has #82 open on MIDI output).

### M6b: MIDI out (firmware side)
- Status 2026-10-24 (session M6b, firmware side, on the owner's Mac): done,
  in pull requests #90 (start) and the MIDI out pull request (the sender,
  what the panel sends, thru, local control, the settings on the screen,
  the tests), which needs fwtest 0.5.0's pin (#91) on main first.
  - **The sender** (HW-72 to HW-74): a 32-message queue that only the
    engine's block callback writes and drains; UART1's transmit DMA,
    started only when the last transfer has gone (`CON0` bit 15), whole
    messages up to 12 bytes a transfer; no interrupt, no lock, nothing
    waits for the wire. Running status while messages keep coming; the
    first message after the wire goes quiet carries its status.
  - **The policy:** controllers, bends, pressure and program changes merge
    with a waiting one; 8 places kept for note offs; others dropped and
    counted when full; a note on dropped takes its note off with it; a
    note off that finds the queue full drops the newest message that ends
    no notes. Nothing is left on at the far end.
  - **What is sent**, on the out channel (1): the keys (velocity 100, the
    off as velocity 0), KNOB1 to KNOB4 as controllers 16 to 19 (the
    inverse of M6a's map, when the value changes), PRESETS as program
    changes, SEL with MONO or POLY as the mode messages. The panel has no
    other pitch control.
  - **Thru** (off by default) passes on every message received but SysEx,
    before the channel filter; **local control** (on by default, CC 122
    too) off sends the panel to MIDI out only. The settings are in
    `struct midi_settings` version 2 and on the screen's bottom line.
  - **Tests** (fwtest 0.5.0, `--midi-out`): six cases, R-MIDIOUT-1 to
    R-MIDIOUT-8. midiout's 60 messages exactly as its script implies
    (golden); the round trip (midiout's golden capture into MIDI in) ends
    with the same patch, mode and knobs and the same pitches; thru passes
    on 18 messages in order and the panel's 4 once each (golden); local
    control off plays nothing from the panel (golden screen); a burst of
    94 messages in one block: 28 merged, 18 dropped with 16 note offs, none
    lost, every note sent ended, the panel's keys out again after (golden);
    the wire's timing and one run per transfer in every case.
  - **Figures** (fwtest 0.5.0): latency from a key going down to its note
    on's first start bit 3.26 to 5.29 ms (mean 4.20; debounce, then at most
    a block); the wire carries about 88% of its rate under a stream (a
    transfer starts only at a poll). At rest 1 863.9 instructions a block,
    +25 (+1.4%); loaded 110 207.6, +0.3%; code 20 144 bytes (+1 736),
    static RAM 143 776 (+520): the M6 budgets hold, none raised. audiogold
    and fmgold unchanged; chords' and midipanel's screens moved only by
    the settings line.
  - **Open items:**
    - **The transmitter on the chip.** Which pin, if any, carries UART1's
      transmit side on the FM-1 is open (Q-20); the FM-1 has no MIDI OUT
      jack, so on the device the bytes go nowhere; in the app they reach
      other programs. What a `CON0` write during a transfer does on the
      chip, beyond the acknowledge, is not known.
    - **Throughput:** with polling once or twice a block, a full input
      wire passed on by thru is about 12% more than the out wire carries;
      the policy then merges or drops. A transmit interrupt (its enable is
      known only from the emulator) would close the gap.
    - **No UI for the settings yet:** they are set by test builds and CC
      122; M8's UI changes them, M7 saves them.
  - **Next: M7, flash storage.**

### M7: flash storage (firmware side)
- Status 2026-10-24 (session M7, firmware side, on the owner's Mac,
  unattended): done, in pull requests #95 (start, SR-9), #98 (the M7
  budgets) and the store pull request; SR-9 answered by the spec side in
  #97 (HW-76 to HW-82), read from its branch.
  - **Nothing runs from the code window** once main runs: every
    instruction and constant is copied to RAM at start-up with the
    initial data (24 KiB; HW-79: nothing may be read through the window
    while the flash is busy, on either core). Only the boot code runs
    from the window.
  - **The store** (docs/STORE-FORMAT.md, our own design): a ring of 18
    sectors in the stock layout's user region, `0xEA000` to `0xFBFFF`
    (HW-80); append-only records with a kind, an id, a version, a length,
    a sequence number and a CRC-32; the newest valid copy wins; a full
    head takes the next sector and copies the live records of the oldest
    forward; a reset is a record. Read and written over SPI0 only (HW-81);
    a part other than the P25Q80H (HW-76) is never written.
  - **What it keeps:** 16 user slots (patches in M5's format), the
    selection, `struct midi_settings` (version 1 migrated to 2). The
    selection and the settings are written 2 s after they change, at most
    once in 2 s; patches when saved.
  - **The panel (minimal):** SAVE held with one of the 16 leftmost keys
    saves the patch playing now to that slot, which PRESETS reaches after
    the test patches; SAVE and HOME held 2 s restore the factory
    defaults; the event line says what happened.
  - **Tests** (R-STORE-1 to R-STORE-9, `tools/store_suite.py`, run by
    the fw suite): persistence across runs; a power cut after each of a
    compacting save's 28 flash commands and part way through every page
    program (109 cuts), plus 29 torn images (bits half cleared, erases
    half done), each the store model's image exactly, each started from
    and saved again; a damaged record, garbage, an unknown kind; no
    free sector (refused, nothing written); 36 saves wearing the ring in
    order; version 1 settings migrated; 24 saves under audioload's input
    (core 0 at 82 000 instructions a block on average), with the part's
    longest erase and program times, and with the firmware's own image
    erased: no underrun, every tick on time. The screen's message after a
    save, a refused save and a reset: golden images.
  - **Figures** (fwtest 0.5.0): a save that takes a new sector and copies
    17 records 0.6 ms in fwtest (its chip is never busy), 95 ms with the
    part's longest times; one that erases a sector and copies one record,
    18 ms; start-up
    reads an empty store in 20 us, a full one in 5.8 ms. At rest
    1 877.1 instructions a block (+0.7%), loaded 107 136.9 (-2.8%);
    code 24 188 bytes (+4 044), static RAM 180 784 (with the 24 068
    bytes of code run from RAM), stack 564: the M7 budgets (#98).
    audiogold unchanged; fmgold and the MIDI out captures moved only in
    time (the copy at start-up moves events across block edges; checked
    sound by sound and byte by byte, then made again).
  - **Wear:** 100 000 cycles a sector (HW-77) give about 2.3 years of the
    selection and the settings both changing every 2 s without a break.
  - **Open items:** Q-21 (the FM-1's part), Q-22 (handing the flash from
    the window to SPI0 on the chip, SPI0's clock, the chip select pin),
    Q-23 (write protection), Q-24 (whether an update keeps the user
    region; M9). fwtest's next version (busy times, the page wrap, the
    write enable, a power cut inside an operation) can replace the busy
    test build and add cuts inside an erase.
  - **Next: M8, the UI and our own presets** (docs/M8-PROPOSAL.md, for
    the owner's review first).

### M8a: the instrument's interface (firmware side)
- Status 2026-10-25 (session M8a, firmware side, on the owner's Mac,
  largely unattended): built in pull requests #111 (start; the store
  moved to the unused region), #116 (M8's budgets), #117 (the screens'
  framework), #118 (the loaded budget, for the macros), #119 (the
  macros), #120 (EDIT), #121 (ENV), #122 (the loaded budget, for the
  spectrum), #123 (the spectrum) and #124 (the settings), in that merge
  order; the ARP proposal is #125 (docs/ARP-PROPOSAL.md). docs/M8-PROPOSAL.md with the owner's answers
  (docs/prompts/M8a.md); docs/DESIGN-NOTES.md, M8a, has the details.
  - **The store** now lives in the stock layout's unused region,
    `0xFC000` to `0xFEFFF`, three sectors: the stock firmware's saved
    patches are never touched. It still holds everything with room; its
    wear life by M7's bound is a sixth of M7's (a heavy day's use: about
    117 years).
  - **Screens:** one at a time; HOME back to the patch view; every
    screen a header, a body, an event line and the strip naming KNOB1 to
    KNOB4 with their values; MASTER, PRESETS, OCT- and OCT+ the same
    everywhere; only what changed redrawn, within M5's drawing budget,
    rectangles for the live parts (`lcd_send_rect`). The engine owns the
    state; main draws it. LEDs: the screen's button, the selected
    operator's key at half.
  - **The patch view:** the algorithm, the macros BRIGHT, COLOR, SHAPE
    and MOTION (offsets, controllers 16 to 19; "Knobs: direct" in the
    settings gives M5's controls back), and a live spectrum (our own
    fixed-point FFT, 56 bars on a log axis, about 30 a second while
    there is sound).
  - **EDIT:** the algorithm with each operator's live level; SEL with
    OP1 to OP6 picks one, KNOB1 to KNOB4 edit it over three pages.
    **ENV:** the envelope to scale with the newest note's dot; SEL with
    PIT the pitch envelope, with GLO the glide; edits as EDIT's, on a
    copy of the program that SAVE writes.
  - **Settings (GLO):** MIDI in and out channels, thru, local control,
    bend range, the knobs, the store's use; factory reset with a
    confirmation (SAVE), replacing M7's hold of SAVE and HOME.
  - **Tests:** golden screens of every view; each control's effect
    measured on the sound (the macros: upper partials, partials off the
    harmonics, attack and release, the pitch's swing; every operator and
    envelope edit; every setting); drawing within its budget and the
    audio never late under the heaviest input; R-UI-1 to R-UI-14.
  - **Fixed on the way:** M2's `gfx_line` never ended on about one line
    in five (the envelope view found it); the frames' wakes replaced
    the live parts'; events before main's loop were left waiting.
  - **Costs:** code 36 KiB, static RAM 200 KiB (M8's budgets, #116);
    steady state unchanged (1 880 a block); loaded 110 309, raised by
    the macros' new meaning of the heaviest input (#118) and by the
    spectrum (#122), whose cost under load is about four times its own
    timing: not explained yet (a question for the owner).
  - **Next: M8b, our own preset bank** (64 presets, docs/M8-PROPOSAL.md,
    "Presets"): the owner listens before it merges. Then ARP, M9 (the
    app release), SEQ and FX (below, "After M8").

### M1 to M9 (firmware side)
- **M1** boot: clocks, interrupts, timer (done; above).
- **M2** screen (done; above).
- **M3** keys, encoders, pot, LEDs (done; above).
- **M4** audio (done; above). **M4b** a platform test: Plaits (MIT) as
  a demo build, and the loaded-case budget (done; above).
- **M5** the FM engine (done; above).
- **M6a** MIDI in (done; above). **M6b** MIDI out (done; above).
- **M7** flash storage (done; above).
- **M8** UI and original presets (no Yamaha factory voices): M8a the
  interface (above); M8b the preset bank (next; docs/M8-PROPOSAL.md).
- **ARP** the arpeggiator (docs/ARP-PROPOSAL.md, with the owner's
  answers), after M8 (done; below).
- **M9** the app release (docs/M9-PLAN.md, section 1, with the owner's
  answers), after ARP (built; below); the hardware package waits for
  M10.
- **SEQ** the sequencer, then **FX** the effects (below).

### After M8: ARP, SEQ and FX
The owner's answers (2026-10-25, recorded by session owner-answers-1025,
docs/prompts/owner-answers-1025.md):
- **The order after M8:** ARP, then SEQ, then FX. M9, the app release,
  fits after ARP.
- **FX v1,** three effects, designed from published literature only
  (never another project's code):
  - **Reverb:** a small feedback delay network of four delay lines,
    mixed by a Hadamard matrix, with SIZE and DECAY.
  - **Chorus:** stereo, one modulated delay a side, their LFOs in
    opposite phase.
  - **Delay:** stereo or ping-pong, its time synced to the ARP and SEQ
    clock.
- What each costs (core 0's or core 1's time, RAM for the delay lines),
  where it sits after the voices, and its controls are FX's proposal,
  for the owner's review first, as M8's and ARP's were.

### Level 2: real hardware
- **M10** recovery kit; it also decides the hardware package's boot
  area, its packaging tool (leaning towards our own packer) and its
  version scheme (docs/M9-PLAN.md, the owner's answers). A package keeps
  the stock user-patch region untouched.
- **M11** USB-MIDI and the update handler.
- **M12** hardware checklist.

### ARP: the arpeggiator (firmware side, after M8)
- Status 2026-10-25 (session ARP, firmware side, on the owner's Mac,
  unattended): built in pull request #132, on #131 (PRESETS stops at
  the ends) and #130 (fwtest 0.6.0); docs/ARP-PROPOSAL.md with the
  owner's answers (#128), docs/prompts/ARP.md; docs/DESIGN-NOTES.md,
  "ARP", has the details and the choices the proposal left open.
  - **What it does:** six modes (UP, DOWN, UP/DOWN, ORDER, RANDOM with a
    fixed generator, CHORD), ten rates from 1/2 to 1/32 with the dotted
    and triplet ones, 1 to 4 octaves, gate 10 to 100%, swing to 75%,
    LATCH; the panel's keys, MIDI in and the pedal feed it. ARP: a short
    press on or off (its LED), held its screen (RATE, MODE, OCTAVES,
    GATE; SWING, LATCH, TEMPO, MIDI OUT).
  - **Timing:** an exact internal clock (no drift over a minute, every
    step at the model's frame), each step's notes started (and ended) at
    their frame within the audio block: the renderer splits a block at a
    pending start or release. MIDI clock in followed whenever it comes
    (Start, Continue, Stop; the rate of the last 24 clocks between
    them); after a Stop or 250 ms without a clock, the internal TEMPO
    from where the pattern is. MIDI clock out on the internal clock.
  - **Kept:** with each patch (the patch format's version 2, in version
    1's reserved bytes: patches and the store keep their sizes; version
    1 patches, the presets too, read with the defaults); the tempo and
    MIDI out's choice (its notes, or the keys held) with the settings
    (version 4).
  - **Tests:** tools/arp_suite.py (C-ARP) against tools/arp_model.py:
    each mode's and rate's notes, frames, sound and MIDI out, golden
    captures; MIDI clock at 120 and 90 beats a minute, Start, Stop,
    Continue and loss; MIDI out's setting, local control off, clock out;
    no stuck notes; its screen; saving and the next start; no underrun
    under the heaviest input with it at its fastest; the store's
    migration of version 1 patches (C-FW-SUITE). R-ARP-1 to R-ARP-8.
  - **Costs:** code 45 060 bytes (+8.5 KiB), static RAM 214 332, stack
    576 (M8's budgets); steady state 1 880 a block (+0.75%), loaded
    109 459 (+0.7%); the heaviest input with CHORD at its fastest: no
    underrun. With the presets (#126) the code passes M8's 48 KiB: #133
    (ARP's budgets, code 56 KiB) comes between #132 and #126.
  - **Open items** (the ARP session's questions; the owner's answers of
    2026-10-25, recorded by session overnight-1025,
    docs/prompts/overnight-1025.md):
    - ARP on or off stays with each patch (PRESETS to a patch without it
      turns it off).
    - TEMPO and MIDI OUT's choice (the arpeggiator's notes, or the keys
      held) belong to the instrument, not the patch.
    - The clock has stopped at a MIDI Stop, or after 250 ms without a
      clock; the definition stands.
    - While an external clock is coming in, our own MIDI clock out is
      suppressed, also after a Stop while the sender's clocks go on
      (with MIDI thru on, a follower saw both); built and tested by
      overnight-1025.
    - keys.txt tapping ARP on and off is fine.
    - Timing goldens: a policy (overnight-1025, docs/DESIGN-NOTES.md,
      "Timing goldens").
    - A session may force-push its own unmerged branches, if it records
      that in docs/EXPOSURE.md.
    - The stack (576 of the 768-byte budget) and the vendor compiler's
      one crash while building a test image in parallel runs (not seen
      again): answered on 2026-10-26, under M9's open items below.
  - **Next: M9, the app release** (docs/M9-PLAN.md; below), then SEQ,
    then FX.

### M9: the app release (firmware side)
- Status 2026-10-26 (session overnight-1025, firmware side, on the
  owner's Mac, unattended): built in its pull request, cumulative on the
  session's others; docs/M9-PLAN.md, section 1, with the owner's answers,
  and its release format 1.0 (the spec side's #136, followed as at
  `1da34f9`); docs/RELEASING.md says how a release is cut, checked and
  loaded into the app.
  - **What a release holds:** `small-beeps-X.Y.Z.fm1img` (release.json
    and the raw image in one file, the one a user needs), the raw image,
    `release.json`, the ELF, an SPDX 2.3 SBOM, LICENSE, NOTICE and
    SHA256SUMS. App releases start at 0.9.0; `config/releases.json`
    lists each tag's version (`m9`: 0.9.0).
  - **How it is made:** `tools/release.sh TAG` refuses a tag GitHub
    doesn't show as Verified, exports the tag's files (never the
    spec-side folders), builds them twice with the tag's own build
    script (the same bytes, and the record's), asks the record's fwtest
    for its version, and runs `tools/release.py build` twice (the same
    bytes) and `verify`; `tools/fm1img.py` is the reference reader, the
    app's seven checks in order. `.github/workflows/release.yml` does
    this on a tag's push (or by hand) and attaches the files to the
    tag's release, making a missing one as a draft; it never makes a
    tag and never replaces a file.
  - **Tests:** C-RELEASE (a release made twice from build A, byte for
    byte the same, verified) and the unit tests (reproducibility, the
    hashes, format 1.0's fields and bytes, the reader's checks in order,
    refusals). R-REL-1 to R-REL-3. A dry run on the signed tag m1
    (version 0.1.0, not published) rebuilt m1's image byte for byte
    (`ee2ad8a0…`) and passed every check.
  - **Not done tonight:** no release made. Tags m2 to m8 aren't signed,
    and none is listed in `config/releases.json`.
  - **Open items** (overnight-1025's questions; the owner's answers of
    2026-10-26, recorded by session clean-pin-answers,
    docs/prompts/clean-pin-answers.md):
    1. Steam Pipes' breath (#126's P68: a full-level feedback modulator
       on a quiet second carrier, about 25 dB under the pipe): accepted
       for now. The owner decides by ear, with the preset notes.
    2. Tutti Swell (#126's P65) stays a pad, its stab 15 dB under the
       swell; the owner may move it after listening.
    3. The run-end check (the timing goldens' rule 1) keeps failing CI,
       since the fix is mechanical; its message now gives the exact
       replacement `--ms` and where to make it (docs/DESIGN-NOTES.md,
       "Timing goldens").
    4. The four exceptions to "goldens re-recorded only by the tool" are
       accepted; docs/DESIGN-NOTES.md, "Timing goldens", lists each with
       its reason.
    5. The 250 ms before our clock out resumes after the sender stops:
       accepted, and documented (docs/DESIGN-NOTES.md, "ARP", MIDI clock
       out).
    6. Releases:
       - m2 to m8 get no versions. The release workflow skips a tag that
         `config/releases.json` doesn't list, with a notice, and
         succeeds.
       - `record.tree_sha256`: the records branch is not added to a clean
         folder's allowed fetches (a wholesale fetch brought spec-side
         blobs into one before, docs/EXPOSURE.md, M1). The workflow reads
         it in CI; given by hand only for a local dry run
         (docs/RELEASING.md).
       - `build.container`: in CI the release builds in the build image
         pinned by registry digest and records that digest; a local
         image ID only for a local dry run, marked as one. Open: no such
         pinned image exists, and docs/TOOLCHAIN.md keeps the image off
         every registry (the toolchain's terms are unknown). Until the
         owner decides, a CI release stops with a message saying so
         (`config/build-image` says `unpublished`); local dry runs work
         and say what they are (docs/RELEASING.md, "The build image").
    7. The stack: raised when SEQ needs it, with a measured high-water
       mark in the record. The compiler crash: its details logged if it
       recurs, nothing else.
  - **Next: SEQ**, then FX.

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
  unaffected (it can boot our raw image). *Answer, in part (2026-10-24,
  session midi-in-out, from FM1 Open's terms only; docs/EXPOSURE.md):*
  M-VAVE now distributes its boot and update resources (`uboot.boot`,
  `ota.bin`, `cfg_tool.bin`, `boot-config.bin`) and the FM-1's recovery
  image (`FM-1_015.fwsc`) under Apache-2.0, which allows redistribution,
  binary included, with the licence, the notices and modified files
  marked. So the loader is no longer a licence obstacle; whether a package
  of ours needs it is still to find out from FM-1-RE's documents. The
  recovery image is still M-VAVE's stock firmware: clean sessions never
  open or disassemble it (CONTRIBUTING.md), whatever its licence.
- **FM1 Open's terms** (M-VAVE's `m-vave/fm1_open`, read 2026-10-24: its
  `LICENSE.md` and `THIRD_PARTY.md` only, at
  `4c7496daac04a95ff10d1afdcc8f9ead2dbabc41`; never its code). It is a GPL
  firmware, so it stays forbidden to the firmware side and outside the
  spec side's allowed sources. What the terms allow, for the record:
  - its own app sources: GPLv3 only, with an additional permission under
    GPLv3 section 7 to link with M-VAVE's binary SDK and convey the result
    without that SDK's source (the third party's summary, "GPLv3 with a
    linking exception plus a proprietary binary SDK", is right; it is
    GPLv3 *only*, not "or later");
  - the binary engine library: proprietary, no source; anyone
    may copy it, link it, build, install and run the result, and
    redistribute it in binary form, commercially too, but only for
    M-VAVE FM1 devices, with the notices and `THIRD_PARTY.md`;
  - the boot and update resources and the recovery image: Apache-2.0
    (above); the third-party parts (FreeRTOS, micro-ecc, Newlib,
    compiler-rt, MSFA and Dexed, Open303, DaisySP, stmlib, emu2149, the SEA
    codec, the packager) and JieLi's SDK material keep their own licences;
  - flashing: the terms permit installing and running such firmware on FM1
    devices, warn that defects may lose data or make the device
    malfunction, and disclaim warranty for the app and the binary SDK.
  For us: our firmware links nothing of FM1 Open, so none of its
  conditions applies to our code; the engine grant names FM1 devices only,
  so it would not cover the SMK-37.
- **Vendoring FM1 Open's boot and update files for M9** (session day-1024,
  from FM1 Open's `LICENSE.md`, `THIRD_PARTY.md`, its file list and git's
  blob hashes only, at `4c7496daac04a95ff10d1afdcc8f9ead2dbabc41`; no file
  of it opened beyond those two). Which files are Apache-2.0, as
  `THIRD_PARTY.md` ("Boot/update resources and recovery firmware") names
  them; all are binaries, so none carries a licence header:

  | File | Bytes | Git blob | What |
  |------|------:|----------|------|
  | `sdk/tools/pack/uboot.boot` | 14 488 | `b81f8de1…` | the second-stage loader |
  | `sdk/tools/pack/ota.bin` | 19 969 | `062ad5e0…` | the update loader |
  | `sdk/tools/pack/boot-config.bin` | 721 | `dc7bcaa7…` | the loader's configuration |
  | `sdk/tools/pack/cfg_tool.bin` | 383 | `e197b6db…` | a configuration resource; byte for byte the pinned AC79 SDK's `cpu/wl82/tools/cfg_tool.bin` (same blob) |
  | `sdk/firmware/FM-1_015.fwsc` | 699 956 | `ce49cc15…` | M-VAVE's stock V15 firmware as a recovery package |

  Nothing else in the repository is under these terms but the FM model
  (Apache-2.0 from MSFA and Dexed, part of the GPL app, not ours to take).
  The repository has no `NOTICE` file. What M9 would need to vendor the
  loaders properly:
  - **Only what a package needs.** Find out from FM-1-RE's update and
    boot documents which of `uboot.boot`, `ota.bin` and `boot-config.bin`
    a package of ours must carry (HW-80: the update package holds a flash
    image from `0x00000`, so the loader at `0x000A0` and its
    configuration at `0x038D0` are in it). Never the `.fwsc`: it is the
    stock firmware, which no session here opens or disassembles, and the
    SMK-37 and our image don't need it.
  - **`cfg_tool.bin` from the AC79 SDK**, not FM1 Open: it is the same
    file, and the SDK is already an allowed source (P-2), so it can be
    added to `tools/fetch-sdk.sh` and its `SHA256SUMS` like any SDK file.
  - **The other loaders from FM1 Open's pinned commit**, as opaque files:
    fetched by raw URL into `vendor/fm1-open-boot/` by a script like
    `tools/fetch-sdk.sh` that checks each SHA-256, never by cloning the
    repository (a clone puts its GPL app on disk), with a `SOURCE.md`
    naming the commit, the files and where `THIRD_PARTY.md` grants them.
    FM1 Open stays off the firmware side's reading list: whoever writes
    the packaging treats these as named binaries with hashes, never
    opening or disassembling them. Whether the firmware side may hold
    them at all is the owner's call (Questions, day-1024).
  - **The licence and notices.** `LICENSES/Apache-2.0.txt` (already here, for the SDK), and
    `REUSE.toml` entries for the vendored files with
    the Apache-2.0 licence identifier and the copyright as
    `THIRD_PARTY.md` gives it: M-VAVE's (珠海笙科智能科技有限公司,
    2026) for the loaders it distributes, and Zhuhai Jieli Technology
    Co., Ltd. (2024-2026) for JieLi material. Our `NOTICE` names the
    files, M-VAVE's grant (the section of `THIRD_PARTY.md` quoted with
    its commit) and that FM1 Open has no NOTICE file of its own
    (Apache-2.0 section 4(d) then asks for nothing more).
  - **Changes marked.** If M9 changes any of them (`boot-config.bin`,
    say, for our image's size or name), the changed file carries a
    prominent statement of the change (section 4(b)), in `SOURCE.md` and
    in the release notes; a release ships the Apache-2.0 text with it
    (section 4(a)).
  - **Recorded.** PROVENANCE.md entries for the fetch; EXPOSURE.md for
    the session that does it.
- **The owner's answers to session day-1024's questions (2026-10-24):**
  - fwtest 0.6.0 (#99) is pinned only after M7's store (#106) merges,
    and the firmware side re-runs its suite on the pin's pull request
    first.
  - Vendor patch 0011 stays in #99.
  - M7's store: the unused `0xFC000`-`0xFEFFF` is preferred, if the
    firmware side shows it meets the store's capacity and wear needs
    (HW-77, HW-80); never the chip's last 4 KiB.
  - M9 may vendor FM1 Open's loader binaries in principle (Risks,
    "Vendoring FM1 Open's boot and update files"); the details are
    decided then.
  - `config/claude/clean.json` and `spec.json` get a deny rule against
    cloning the port repository, at the start of the next sessions
    (done in session evening-1024: `Bash(git clone*small-beeps-ports*)`).
- **The owner's further answers to session day-1024's questions,
  recorded in session evening-1024 (2026-10-25):**
  - The Claude session once run in a folder named for the porter was for
    an unrelated project, with no FM-1 firmware, emulator or small-beeps
    material; no porter session has run (docs/EXPOSURE.md, "Porter").
  - FM-1-RE's `docs/io/09-storage.md` is no longer allowed to the
    firmware side, since most of it describes the stock firmware's own
    code; the spec side keeps it and cites only its hardware facts
    (CONTRIBUTING.md; `tools/check-transcripts.py` rule F-15).
- **The emulator doesn't model USB**, so M11 is hardware-only.
- **Merge signatures are GitHub's.** Since 2026-10-22 the owner merges with
  GitHub's button, so merge commits are signed by GitHub (`web-flow`) and the
  owner's identity rests on GitHub's `merged_by` record, checked by C-MERGE.
  Milestone tags carry the owner's own SSH signature. The first merge's
  record shows C-MERGE FAIL under the earlier rule (CONTRIBUTING.md, "Merge
  policy and its history").
