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

### M1 to M9 (firmware side)
- **M1** boot: clocks, interrupts, timer (done; above).
- **M2** screen (done; above).
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
