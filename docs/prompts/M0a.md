Addendum 1 and Addendum 2 at the end are part of this milestone; do them before finishing. Where Addendum 2 differs from Addendum 1, Addendum 2 wins.

Setup notes for this session:
- You are running in ~/work/small-beeps/clean on the owner's Docker machine. Make this folder the repo root (git init here); do not clone anything into it.
- .claude/settings.json in this folder was created by hand by the owner before this session started. Never edit, remove or loosen it (Addendum 2 says how to record it).
- <github-user> below means the owner's personal GitHub account. Run `gh auth status`, tell the owner which account it shows, and confirm before creating anything.
- The owner is driving this session from a phone via Remote Control: keep questions short and one at a time.

# M0a: project foundation for a clean-room, MIT-licensed base firmware
# (repo, rules, roles, records, signing, toolchain, SDK, CI; no firmware code yet)

## What this project is

We're writing an original firmware for the M-VAVE FM-1 pocket synthesizer (JieLi AC791N chip:
two pi32v2 CPU cores, a 240x240 LCD, a key matrix, rotary encoders, I2S audio), MIT-licensed,
so it can ship inside the F-Emulator iOS app (an emulator of the FM-1). The FM-1's existing
community firmwares are GPL-licensed; ours must be provably independent of them.

Four requirements shape everything, from the first commit:
1. **History:** every change shows what was done, why, how, and the result.
2. **Tests:** thorough tests throughout, with a permanent record of them passing.
3. **Reproducible:** anyone can rebuild any commit and re-check its results if challenged.
4. **Public and efficient:** public (low profile for now), and performance is tested, not
   hoped for.

This session (M0a) builds the foundation only. Later milestones get their own prompts and
sessions (see the plan below). Ask me before creating the GitHub repo, before pushing, and
whenever a rule here is unclear.

## 1. Two roles, and the exposure register

Clean-room work separates people who have seen the protected code from people who write ours.
- **Spec side (exposed):** may read the F-Emulator emulator's source, whose chip model was
  partly written from the GPL Felucca firmware's hardware layer. It builds the test harness
  and writes `HARDWARE-SPEC.md`: facts only (addresses, bits, pins, timings, protocols),
  never code or code structure, each fact citing a non-GPL source where one exists.
- **Firmware side (clean):** writes the firmware. It reads only `HARDWARE-SPEC.md`, the JieLi
  SDK (Apache-2.0), FM-1-RE's hardware documents (WTFPL), public datasheets, and results of
  its own black-box experiments. It uses the harness only as a command-line tool and never
  opens `vendor/emulator/` or `harness/` source.
- **This session is firmware side (clean).** Stay clean: don't open anything on the forbidden
  list, the emulator's source, or `vendor/emulator/` once it exists.

Create `docs/EXPOSURE.md`, the record a clean-room claim rests on: who or which session saw
what, and when. Start it with these entries (dates as today's):
- **The owner (<github-user>):** has read no FM-1 firmware source. Clean. May review
  firmware-side work.
- **The planning conversation** (Claude, in the Claude app; it designed this process and
  wrote this prompt): saw the F-Emulator emulator's source, including comments that say its
  chip model was written from Felucca's hardware layer; the README of FM-1 SID (a GPL firmware
  in the emulator repo), which describes Felucca's engine interface; and the community
  firmware catalog's metadata. It has never seen Felucca's source. Spec side only.
- **The F-Emulator app session** (Claude Code on the owner's Mac): read FM-1 SID's firmware
  source (built on Felucca's code) and parts of Felucca's web installer page code. Spec side
  only.
- **This session (M0a):** no exposure. Firmware side.
Every later session adds its own entry when it starts, and again whenever its exposure
changes.

## 2. Clean-room rules (CONTRIBUTING.md; you follow them too)

- **Firmware side never opens, fetches, searches or quotes:**
  - hugelton/Felucca and every fork or firmware built on it (Felucca Salt, Felucca 8 Patterns,
    Hortator, GHOULBOX, Melodee, Skiff, ...);
  - zvenson/dinghy and anything built on it;
  - the F-Emulator / fm1-emu repository's `fm1-sid/` directory, its `probes/lcdtest.c`, and
    its emulator source (`crates/`);
  - any other FM-1 firmware source;
  - M-VAVE's stock firmware and any disassembly or function database of it (including
    AL-255/FM-1-RE's `firmware-images/` and disassembly material).
- **Firmware side may use** (log every use in PROVENANCE.md: an ID, the source, what was
  learned, where it was used):
  - `HARDWARE-SPEC.md`, once it exists (each fact there already cites its own source);
  - JieLi's AC79 SDK, `Jieli-Tech/fw-AC79_AIoT_SDK` (Gitee), Apache-2.0: headers, register
    definitions, drivers. Not its prebuilt libraries (plan to need none);
  - AL-255/FM-1-RE (GitHub, WTFPL): its hardware, memory-map, boot-chain and update-protocol
    documents only;
  - public datasheets;
  - our own experiments: test programs run in the emulator, observed only through the
    harness.
- **Unsure whether something is allowed:** stop and ask the owner.

## 3. The repo

- Account: **<github-user>** (personal; it moves to an organisation when it goes public).
  Name: **`small-beeps`**. **Public** from the first commit: GitHub's public push history is
  part of our evidence of when things were written.
- **Low profile for now** (unpromoted, not secret). In the repo's name, description, topics
  and the README's front page, never mention FM-1, M-VAVE, JieLi, synth or firmware:
  - description: "Embedded audio experiments.";
  - no topics;
  - README opens with "Embedded audio experiments. Work in progress.", then generic build and
    verification steps.

  Don't link it from anywhere, star it, fork it or announce it.
- **Everything inside stays complete and truthful:** docs, prompts, requirements,
  provenance, exposure register, commit messages and test records say exactly what this is.
  Nothing secret ever goes in (keys, tokens, private notes): it's public, and history is
  never rewritten.
- `docs/GOING-PUBLIC.md`: the steps for later, covering:
  - transfer to the organisation and rename (history, tags, records and timestamps carry
    over; GitHub redirects);
  - the description, topics and README front page;
  - updating pinned URLs.

## 4. How every change is recorded

- **Bootstrap:** the first commit (the skeleton, this section's rules included) goes straight
  to main, because protection needs a commit to exist. Record that in its message. Then turn
  on the rulesets and use pull requests for everything after.
- **Rulesets** (repository rulesets; free on public repos):
  - main: changes only through merged pull requests that pass CI; merge commits only (no
    squash, no rebase-merge); no force pushes; no deletion; nobody bypasses;
  - the `records` branch: no force pushes, no deletion;
  - tags `m*`: no deletion or update.
- **Signing:** you (the agent) make unsigned commits on branches. The owner merges each pull
  request with a **signed merge commit**, so every change on main carries the owner's
  signature. Milestone tags are signed by the owner. Walk the owner through setting up SSH
  commit signing (Git and GitHub) once, and document it in CONTRIBUTING.md.
- **Commit messages** follow `.gitmessage`, checked by a commit-msg hook and by CI:
  ```
  <area>: <what changed, one line>

  What:    what this commit does
  Why:     the reason (the milestone and requirement IDs it serves)
  How:     the approach, and anything tried and rejected
  Result:  what the author saw when testing (the CI record is the authoritative result)
  Sources: PROVENANCE IDs used (or "none")
  Exposure: the session's role and exposure (e.g. "firmware side, none")
  ```
  plus a `Claude-Session:` trailer when an agent wrote it. Small commits: one idea each.
- **Pull requests** use the same sections (a PR template) and link the CI run and the record.
- **Prompts are part of the record:** each milestone's prompt goes in `docs/prompts/<Mx>.md`,
  unedited, in the commit that starts the milestone. Start with this one as `docs/prompts/M0a.md`.
- **Requirements and traceability:** `docs/REQUIREMENTS.md` lists numbered requirements
  (R-PROC-1, R-REPRO-1, R-BOOT-1, ...). Every test names the requirements it checks, and
  every record includes a traceability table (requirement → tests → result).

## 5. Permanent test records

- For every commit CI tests, it writes `records/<commit-sha>/`:
  - `report.json` and `report.md`: the environment (every pinned version and digest), each
    check with its requirement IDs, result and duration, and output SHA-256s;
  - the full logs.
- A records workflow runs **only for pushes to main** (never for pull requests, so a fork can
  never write a record). It appends the record to an orphan `records` branch using a deploy
  key that only that workflow holds, and uploads the same files as artifacts.
- **Independent timestamps:** each record gets an OpenTimestamps proof (`.ots`) beside it.
  Proofs are pending at first; a scheduled workflow (daily) upgrades them once Bitcoin
  confirms, and appends the upgraded proofs as new files, never rewriting the old ones.
- Milestones end with a tag `mN` (signed by the owner) and a GitHub release carrying the
  build outputs, the record and an SBOM. Release notes stay generic while the repo is low
  profile; the attached record is complete.

## 6. The toolchain, reproducible and preserved

- JieLi's toolchain `jieli-linux-toolchains-20250324.1`, downloaded from
  https://pkgman.jieliapp.com/s/linux-toolchain (Clang/LLVM 4.0.1 with a pi32v2 backend;
  Linux x86-64). Its licence terms are unknown, so:
  - never commit it or publish anything containing it;
  - the Dockerfile downloads it and checks a SHA-256 you record;
  - `docs/TOOLCHAIN.md` records the URL, the SHA-256, the download date, any licence or
    terms files found inside it (quote their names and summarise, don't copy), where clang's
    compiler builtins come from and their licence, and the risk: if the download disappears,
    a full rebuild needs another copy, but every released binary stays verifiable by its
    recorded hash;
  - **preservation copy:** after asking the owner, upload the archive as a release asset in
    a separate **private** repo `<github-user>/small-beeps-toolchain`, kept only to preserve
    it, and note that in TOOLCHAIN.md.
- Docker: the base image pinned by digest. Builds run under `--platform linux/amd64` (works on
  Apple Silicon too) through `tools/build.sh`.
- **Deterministic builds** from day one: fixed `SOURCE_DATE_EPOCH`, no absolute paths or
  timestamps in outputs, a stable file order. Freestanding C11: `-ffreestanding -nostdlib`;
  our own small runtime later, never the toolchain's C library.
- For M0a, prove the pipeline with a placeholder translation unit
  (`firmware/src/placeholder.c`, a trivial function) compiled and linked to a `.o` and an
  `.elf`. CI builds it twice in fresh containers and fails if any output byte differs.

## 7. The SDK

- Vendor JieLi's AC79 SDK (`Jieli-Tech/fw-AC79_AIoT_SDK`, Gitee) at a pinned commit, through
  a fetch script with a checksum. Commit only the parts we'll use (headers and register
  definitions first), with their licence files, under `vendor/jieli-sdk/`.
- Check the SDK's licence covers the files we take; list anything with other terms
  (prebuilt libraries especially) in `docs/TOOLCHAIN.md` as "not used". `NOTICE` carries the
  SDK's Apache-2.0 notice.

## 8. Licence evidence

- Every file we write has an SPDX header (`SPDX-License-Identifier: MIT` and
  `SPDX-FileCopyrightText: 2026 <github-user>`); vendored files keep theirs. `REUSE.toml`
  covers files that can't carry headers. CI runs `reuse lint` (FSFE REUSE) and fails on any
  gap.
- The similarity audit and performance tracking come in M0e (below).

## 9. Layout

```
LICENSE (MIT), NOTICE, README.md, CONTRIBUTING.md, PROVENANCE.md, REUSE.toml, .gitmessage
docs/PLAN.md, docs/REQUIREMENTS.md, docs/EXPOSURE.md, docs/TOOLCHAIN.md,
docs/GOING-PUBLIC.md, docs/prompts/M0a.md
firmware/src/placeholder.c
vendor/jieli-sdk/          (pinned, only the parts used, with licence files)
tools/Dockerfile, tools/build.sh, tools/record.py (writes the record), tools/hooks/
.github/workflows/ci.yml, records.yml, ots-upgrade.yml; .github/pull_request_template.md
```

## 10. docs/PLAN.md

The milestones, each with its role, requirement IDs and a "done when":
- **M0a** (firmware side): this foundation.
- **M0b** (spec side): vendor the emulator crates (`fm1-isa`, `fm1-core`, `fm1-soc`, copied
  from the public upstream `joakimeriksson/fm1-emu` at a pinned commit, with its MIT
  licence, into `vendor/emulator/`; never the rest of that repo). Build the harness: a Rust
  library and `fwtest` CLI that boots a raw image, runs N emulated ms with a timed input
  script, captures RAM, the LCD (PNG), LEDs, flash, audio (WAV) and instructions per audio
  block, detects halts, compares golden files, and emits JUnit and JSON.
- **M0c** (spec side): `HARDWARE-SPEC.md`, facts only, each with its source; facts with
  only an emulator source are marked so. Reviewed for "facts, not code" before firmware side
  reads it.
- **M0d** (firmware side): the smallest firmware. Startup, linker script and `main` (a marker
  word, a heartbeat), from `HARDWARE-SPEC.md`, the SDK and FM-1-RE only; booted and checked
  with `fwtest`.
- **M0e** (spec side for the audit, firmware side for performance):
  - the **similarity audit**: an isolated CI job that fetches the GPL firmwares at pinned
    commits, compares our firmware against them with JPlag (the SDK given as base code,
    `vendor/` excluded, an unrelated permissive embedded C project scored as a control),
    and publishes scores and file names only;
  - **performance tracking**: per-commit size and RAM, and later emulated instructions per
    audio block. A 3% regression gate on instructions per audio block (deterministic in the
    emulator); per-milestone budgets for size and RAM, raised only by a PR that says why.
- **M1** boot (clocks, interrupts, timer). **M2** screen. **M3** keys, encoders, pot, LEDs.
  **M4** audio. **M5** the FM engine. **M6** MIDI in. **M7** flash storage. **M8** UI and
  original presets (no Yamaha factory voices). **M9** packaging, and a raw-image boot path in
  the app.
- Level 2 (real hardware): **M10** recovery kit; **M11** USB-MIDI and the update handler;
  **M12** hardware checklist.
- **Risks:**
  - The toolchain's availability and terms (above).
  - **Packages for real hardware:** a `.fwsc` may need M-VAVE's boot or update loader,
    which we can't redistribute. Find out from FM-1-RE's documents only, before M9, and
    record the answer here. The app is unaffected (it can boot our raw image).
  - The emulator's USB isn't modelled (M11 is hardware-only).

## Done when

- The repo exists (after asking the owner), with the bootstrap commit and then the rulesets
  on.
- CI on a pull request runs:
  - `reuse lint`;
  - the commit-message check;
  - the low-profile check (the repo's name, description, topics and README first line contain
    none of the quiet words);
  - the toolchain container build with its checksum;
  - the double build compared byte for byte.
- The owner's signed merge to main triggers the first record on the `records` branch, with a
  pending OpenTimestamps proof.
- `./tools/reproduce <commit>` rebuilds that commit in the pinned container and compares its
  output hashes with its record. Documented in the README as "How to verify our work".
- `docs/EXPOSURE.md` has all the entries above, and PROVENANCE.md logs every source used
  this session (the toolchain, the SDK, FM-1-RE if consulted).
- Nothing on the forbidden list, and no emulator source, was opened.
