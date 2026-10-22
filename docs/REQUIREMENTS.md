<!--
SPDX-License-Identifier: MIT
SPDX-FileCopyrightText: 2026 japes98
-->

# Requirements

Numbered requirements for this project (the original, MIT-licensed base
firmware for the M-VAVE FM-1, JieLi AC791N). Every check names the
requirements it covers (`tools/record.py`, `CHECKS`), and every test record
ends with a traceability table: requirement → checks → result.

A requirement whose "Checked by" says *review* is checked by people when they
review a pull request, not by a machine. *Planned* means a later milestone
adds the check. The record lists both kinds, so nothing looks checked when it
isn't.

The four founding requirements (docs/prompts/M0a.md): **history**,
**tests**, **reproducible**, **public and efficient**.

| ID | Requirement | Since | Checked by |
|----|-------------|-------|------------|
| R-PROC-1 | Every commit message follows `.gitmessage` (subject `<area>: <summary>`; non-empty What, Why, How, Result, Sources, Exposure). Agent-written commits also carry `Model:` and `Claude-Session:` trailers. Merge commits are exempt; their pull request carries the sections. | M0a | C-COMMIT-MSG, C-UNIT |
| R-PROC-2 | main changes only through pull requests that passed CI, merged by the owner with a verified, signed merge commit (GitHub's merge button since 2026-10-22, CONTRIBUTING.md "Merge policy"). Nobody bypasses. No force pushes or deletion on main and `records`; `m*` tags are never moved or deleted. | M0a | rulesets (CONTRIBUTING.md); C-MERGE (records workflow) |
| R-PROC-3 | Each milestone's prompt is committed unedited in `docs/prompts/` in the commit that starts the milestone. | M0a | review |
| R-PROC-4 | Every check names the requirements it checks, and every record has a traceability table. | M0a | C-UNIT |
| R-REC-1 | Each commit pushed to main gets a permanent record `records/<sha>/` (report.json, report.md, logs) on the orphan `records` branch, written only by the records workflow, never for pull requests. | M0a | records.yml; C-UNIT (record writer) |
| R-REC-2 | Each record has an OpenTimestamps proof. Upgraded proofs are added as new files and never replace the originals. | M0a | records.yml, ots-upgrade.yml |
| R-REPRO-1 | The toolchain is downloaded and checked against the SHA-256 in docs/TOOLCHAIN.md. It is never committed or published. | M0a | C-IMAGE, C-NO-TOOLCHAIN |
| R-REPRO-2 | The build container's base image is pinned by digest, its packages come from a pinned snapshot.debian.org date, and builds run under `linux/amd64` through `tools/build.sh`. | M0a | C-IMAGE |
| R-REPRO-3 | Builds are deterministic: two builds in fresh containers, with the source mounted at different paths, are byte-identical. | M0a | C-BUILD-A, C-BUILD-B, C-DETERMINISM |
| R-REPRO-4 | `tools/reproduce <commit>` rebuilds that commit in the pinned container and compares its output hashes with the commit's record. | M0a | review (run by hand; result in the PR) |
| R-REPRO-5 | Vendored SDK files match the SHA-256s listed for the pinned SDK commit. | M0a | C-SDK-PIN |
| R-REPRO-6 | Vendored emulator files (spec side, `vendor/emulator/`) match the pinned upstream commit plus the patches in `vendor/emulator/patches/`, file by file and by one tree hash; `tools/fetch-emulator.sh` reproduces them. | M0b | C-EMU-PIN |
| R-BUILD-1 | Firmware is freestanding C11 (`-std=c11 -ffreestanding -nostdlib`). It never links the toolchain's C library or prebuilt SDK libraries. | M0a | C-BUILD-A |
| R-BUILD-2 | Every record states the firmware image's size in bytes (code, data, bss, the raw image, the stack reserved), from build A. Budgets: R-PERF-1. | M0d | C-FW-SIZE |
| R-LIC-1 | Every file has SPDX licence and copyright information (`reuse lint` passes). | M0a | C-REUSE |
| R-LIC-2 | Vendored files keep their licences and notices. NOTICE carries the SDK's Apache-2.0 notice and the emulator crates' MIT notice. Only SDK headers are vendored, never prebuilt libraries; of the emulator, only the three crates named in `vendor/emulator/UPSTREAM.md`. | M0a | C-REUSE, C-SDK-PIN, C-EMU-PIN |
| R-PUB-1 | Low profile: the repo's name, description and topics, and the README, contain none of the quiet words (CONTRIBUTING.md). The description is exactly "Embedded audio experiments.", there are no topics, and the README opens with "Embedded audio experiments. Work in progress." | M0a | C-LOW-PROFILE |
| R-PUB-2 | No secrets (tokens, private keys) in tracked files. | M0a | C-SECRETS |
| R-PUB-3 | No tracked file, commit message or archived transcript holds one of the owner's private terms (username, hostname, real e-mail, real name, local folder names), which live only in the gitignored `tools/private-terms.local` and the `PRIVATE_TERMS` secret. A hit is reported by file and line only. A file under `sessions/` or `docs/prompts/` unchanged (same blob) since the base commit in `config/private-base` is exempt, decided from object hashes alone; everything added or changed after it is checked in full (CONTRIBUTING.md, "Privacy"). `tools/archive-session.py` redacts the username, the local top-level folder (as `<top>`) and the terms. The pre-commit and commit-msg hooks run the same check. | M0d | C-PRIVATE, C-UNIT |
| R-CLEAN-1 | Firmware side never opens, fetches, searches or quotes forbidden material (CONTRIBUTING.md, "Clean-room rules"). | M0a | C-TRANSCRIPTS, C-CLEAN-FOLDER |
| R-CLEAN-2 | docs/EXPOSURE.md has an entry for every person and session that worked on the project, with role, exposure and (for agents) the exact model ID and its training cutoff. | M0a | review |
| R-CLEAN-3 | Every session's transcript is archived (secrets redacted, redactions noted) in `sessions/`, and every clean-side transcript's reads, searches and fetches are listed and checked. | M0a | C-TRANSCRIPTS |
| R-CLEAN-4 | The deny lists in `config/claude/clean.json` and `config/claude/spec.json` never drop an entry. | M0a | C-DENY-LISTS |
| R-CLEAN-5 | Every archived session after M0a shows the SessionStart banner with matching settings, and never CONFIG MISMATCH. | M0a | C-TRANSCRIPTS |
| R-SEP-1 | Spec-side text discipline: what the spec side learns from emulator source leaves `vendor/emulator/` and `harness/` only through `HARDWARE-SPEC.md` and `docs/HARNESS.md`. Spec-side commit messages, pull request texts and files elsewhere (docs, tools, tests, records, release notes) carry no emulator internals (CONTRIBUTING.md, "Spec-side text discipline"). C-SEP-TERMS finds identifiers that occur only in `vendor/emulator/` in the files, commit messages and pull request texts the firmware side reads; people review `docs/HARNESS.md` and `HARDWARE-SPEC.md`. | M0b | C-SEP-TERMS; review |
| R-SEP-2 | Spec-side session transcripts are archived only in `sessions/spec/`, which clean folders leave out and their settings deny reading; clean sessions never open it, and the transcript check still works without it. A fresh clean folder has none of `vendor/emulator/`, `harness/` or `sessions/spec/` on disk or in its `.git`, denies reading all three, and keeps them out even when the firmware side's tools and history commands run in it or it is updated (clean sessions run with git's lazy fetching off). | M0b | C-UNIT, C-DENY-LISTS, C-TRANSCRIPTS, C-CLEAN-FOLDER |
| R-SEP-3 | `tools/fwtest` runs only the fwtest image pinned by digest in `config/fwtest-image` (no tags), and records which image it ran; the record notes the pinned image. | M0b | C-FWTEST-PIN |
| R-HARN-1 | `fwtest` boots a raw image as docs/HARNESS.md says (load address, size limit, entry, initial state, memory), and refuses images it can't load. | M0b | C-HARNESS-TEST, C-HARNESS-SUITE-A |
| R-HARN-2 | A timed input script drives keys, encoders, the pot and MIDI in, in the text format docs/HARNESS.md gives. | M0b | C-HARNESS-TEST, C-HARNESS-SUITE-A |
| R-HARN-3 | Captures, as asked: RAM regions, the LCD as PNG, LED duty, the flash chip, audio as WAV, instructions per audio block, the debug console. | M0b | C-HARNESS-TEST, C-HARNESS-SUITE-A |
| R-HARN-4 | A fault, a halt and a hang (watchdog) are detected and told apart by exit code; bad input has its own code. | M0b | C-HARNESS-TEST, C-HARNESS-SUITE-A |
| R-HARN-5 | Golden files compare exactly, unless a tolerance file allows a documented difference (PNG pixels, WAV samples, CSV numbers). | M0b | C-HARNESS-TEST, C-HARNESS-SUITE-A |
| R-HARN-6 | Determinism: the same image, script and fwtest build give byte-identical outputs on every run and machine (no JIT, no host time, no environment influence). | M0b | C-HARNESS-TEST, C-HARNESS-SUITE-B, C-HARNESS-DET |
| R-HARN-7 | Every run writes `result.json` and `junit.xml`; the harness suite's are kept in the commit's record (`harness/`). | M0b | C-HARNESS-TEST, C-HARNESS-SUITE-A |
| R-HARN-8 | fwtest builds in a container whose bases are pinned by digest, offline, with the Rust toolchain pinned and no third-party crates (Cargo.lock lists path crates only); the harness's test images rebuild identically with the pinned toolchain. | M0b | C-HARNESS-IMAGE, C-HARNESS-IMAGES |
| R-HARN-9 | The harness runs raw images only: it never uses the vendored crates' update-package or stock-boot paths, nor anything of M-VAVE's. | M0b | C-HARNESS-SCOPE |
| R-HARN-10 | The firmware side's wrapper `tools/fwtest` runs the published image with no network, as linux/amd64, with the working folder read-only and only `--out` writable. | M0b | C-FWTEST-PIN |
| R-SPEC-1 | Every entry in `docs/HARDWARE-SPEC.md` has an ID (`HW-n`, never reused, renumbered or removed: a corrected fact gets a new ID and the old entry is marked superseded), the fact, its sources, its standing (`confirmed`, `emulator-only`, or `superseded by HW-n`) and the milestone that needs it. A confirmed entry cites a source other than the emulator model; every experiment it cites exists. | M0c | C-SPEC-LINT, C-UNIT |
| R-SPEC-2 | `docs/HARDWARE-SPEC.md` and `docs/HARNESS.md` use no identifier that occurs only in `vendor/emulator/` (reviewed exceptions in `config/emulator-terms-reviewed.json`). | M0c | C-SEP-TERMS; review |
| R-SPEC-3 | `docs/HARDWARE-SPEC.md` holds facts, never code, pseudo-code or procedures copied from code, and nothing derived from forbidden material. Before the firmware side reads a version, a reviewer with no other context checks every entry, and the report is kept in `docs/reviews/`; people review it again at merge. | M0c | C-SPEC-LINT (no code blocks), C-UNIT; review |
| R-SPEC-4 | Every black-box experiment `docs/HARDWARE-SPEC.md` cites (E-n, `harness/spec-experiments/`, spec side) rebuilds identically with the pinned toolchain and still gives the cited results in this checkout's fwtest. | M0c | C-SPEC-EXPERIMENTS |
| R-BOOT-1 | The firmware boots in the emulator to `main` and writes a marker word. | M0d | C-FW-SUITE, C-UNIT |
| R-BOOT-2 | The firmware keeps a heartbeat visible through the harness. | M0d | C-FW-SUITE, C-UNIT |
| R-BOOT-3 | The heartbeat counts one beat per millisecond of the chip's 24 MHz time base, and over a one-second run that time base agrees with fwtest's emulated time within 10 µs. Each beacon captured during the run shows the right number of beats for its time base value, taken no more than 5 ms after the time asked (captures can come late while the image waits, docs/HARNESS.md "Time"). | M0d | C-FW-SUITE, C-UNIT |
| R-BOOT-4 | The firmware runs in fwtest without a fault, halt or hang, touches nothing fwtest does not model, and leaves core 1 stopped. | M0d | C-FW-SUITE, C-UNIT |
| R-BOOT-5 | Startup gives C its memory before `main` (initialised data copied, zeroed data cleared; the marker is written only if both are right), and the image stays within its memory layout: RAM from `0x01C7FC00` to the top of the chip's main RAM is left as it was at entry. | M0d | C-FW-SUITE |
| R-AUDIT-1 | A similarity audit compares our firmware with the GPL firmwares and publishes scores and file names only. | M0e | planned |
| R-PERF-1 | Every record states the firmware's code size, static RAM (initialised and zeroed data) and stack high-water mark, and each stays within the budget `config/budgets.json` sets for the current milestone. Raising a budget, or moving to the next milestone's, takes its own pull request that says why (What/Why/How/Result) and changes nothing else. | M0e | C-PERF, C-UNIT; review (a raise in its own pull request) |
| R-PERF-2 | Emulated core-0 instructions per period, measured in fwtest, may not rise by more than 3% against the latest record of a main commit, whose own image is re-measured with the same fwtest and options; a fall of more than 3% is reported in the record and the pull request's checks. No noise allowance: the count is deterministic. Until audio (M4) the period is the heartbeat (one beat per millisecond); from M4 it is the audio block. | M0e | C-PERF, C-UNIT |
| R-PERF-3 | The stack's high-water mark is measured in fwtest: the firmware fills its unused stack with a pattern once at startup (after the time base starts), the stack is captured at the end of a one-second run, and the lowest word no longer holding the pattern marks the deepest use, including words written as zero. A test build with a known 1 KiB of stack, written with zeros, must read at least 1 024 bytes. | M0e | C-PERF, C-PERF-PROBES, C-UNIT |
| R-PERF-4 | The `records` branch's `perf-history.csv` gets one line per main commit (size, RAM, stack high-water, instructions per period, the change against the baseline), appended by the records workflow and never rewritten; a re-run adds no line. | M0e | records.yml; C-UNIT |
| R-PERF-5 | The gates are tested against the unmodified build, measured in the same run: a deliberately slower build fails the speed gate (and no other), and a deliberately bigger build fails each of the three budgets when the unmodified build's sizes are the budgets, so the test holds however far `config/budgets.json` is raised. | M0e | C-PERF-PROBES, C-UNIT |
