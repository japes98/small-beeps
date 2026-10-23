<!--
SPDX-License-Identifier: MIT
SPDX-FileCopyrightText: 2026 japes98
-->

# Exposure register

*Local paths in older entries were redacted on 2026-10-22 for privacy; git
history keeps the originals; nothing else changed.*

This is the record a clean-room claim rests on: who, or which session, saw
what, and when. Roles are defined in CONTRIBUTING.md.

- **Spec side (exposed):** may have seen the emulator's source (whose chip
  model was partly written from the GPL Felucca firmware's hardware layer)
  or other material on the forbidden list. Writes the harness and
  `HARDWARE-SPEC.md`. Never writes firmware.
- **Firmware side (clean):** has seen none of the forbidden material. Writes
  the firmware.
- **Auditor (exposed to the GPL firmwares):** reads a flagged pair from a
  failed similarity audit, our file and the GPL target's, and writes a
  finding in general terms. Never writes firmware or spec. Its transcript is
  kept in the owner's private repository, not here; its entry records the
  session ID, the transcript's SHA-256 and that repository's commit
  (docs/AUDIT.md, "When the audit fails"). None has run yet.

Every session adds its own entry when it starts, and again whenever its
exposure changes. Agent entries record the exact model ID and its published
training cutoff (see "Model cutoffs" below).

## Entries

### The owner (GitHub: japes98)
- Date: 2026-10-21
- Role: clean. May review firmware-side work.
- Exposure: has read no FM-1 firmware source.

### The planning conversation (Claude, in the Claude app)
- Date: 2026-10-21 (entry recorded; the conversation took place before this
  repository existed)
- Role: spec side only.
- What it did: designed this process and wrote the M0a prompt
  (docs/prompts/M0a.md).
- Exposure: saw the F-Emulator emulator's source, including comments that say
  its chip model was written from Felucca's hardware layer; the README of
  FM-1 SID (a GPL firmware in the emulator repo), which describes Felucca's
  engine interface; and the community firmware catalog's metadata. It has
  never seen Felucca's source.
- Model ID: not recorded by the owner.

### The F-Emulator app session (Claude Code on the owner's Mac)
- Date: 2026-10-21 (entry recorded; the session took place before this
  repository existed)
- Role: spec side only.
- Exposure: read FM-1 SID's firmware source (built on Felucca's code) and
  parts of Felucca's web installer page code.
- Model ID: not recorded by the owner.

### Session M0a (this foundation)
- Date: 2026-10-21
- Role: firmware side (clean).
- Exposure: none.
- Tool: Claude Code 2.1.307 (`claude --version`), Remote Control from the
  owner's phone.
- Model ID: `claude-opus-5-5` (Claude Opus 5.5). Published cutoffs: reliable
  knowledge Jun 2026, training data Jun 2026 (PROVENANCE P-4).
- Session: Claude Code session `36860ab8-77fd-4fd6-aa1d-2063c15a5548`,
  `https://claude.ai/code/session_01CQ8PVaAx6db8cqvV9i53wj`.
- Where it ran: the owner's Mac (macOS, Apple Silicon), in
  `~/<top>/clean`. The prompt said "~/work/small-beeps/clean
  on the owner's Docker machine"; the owner was told and continued. The
  session used only paths inside this folder, its own scratch folder and its
  own transcript, and never listed or opened the parent folder or its other
  entries.
- Sources used: PROVENANCE P-1 to P-6. FM-1-RE was not consulted.
- Barriers:
  - **Hand-made settings.** The session started under
    `.claude/settings.json`, made by hand by the owner before the repository
    existed (before `git init`).
    SHA-256 `a557bd84008372ff9d3e24cd648df9986d76a05928d9f50b5d3e60975bf29b32`.
    Its exact bytes are kept as `config/claude/handmade-settings.json` (same
    hash). Its ten deny rules forbid reading `./vendor/emulator/**`,
    `./harness/**` and `**/fm1-sid/**`, fetching from hugelton.github.io and
    thefirmwarehub.com, and `git clone` of Felucca, dinghy, fm1-emu and
    f-emulator.
  - **No banner.** This was the first session: there was no earlier
    transcript to archive and no SessionStart hook, so its transcript has no
    banner. `tools/check-transcripts.py` exempts exactly this session ID, for
    that reason only.
  - **From clean-setup.sh on.** Partway through, the session ran
    `tools/clean-setup.sh` here, which replaced the live settings with
    `config/claude/clean.json`: the same ten deny rules, unchanged and in the
    same order, plus the SessionStart banner hook. From then on the session
    ran under the committed clean settings (see "Barrier log").
- Also archived as M0a's: `ddebd686-9190-4fa3-b217-30d0a98fda69`, a
  one-prompt `claude -p` run that M0a started in its scratch folder to learn
  how Claude Code stores hook output. It made no tool calls; its only hook
  printed a test marker instead of the banner, so
  `tools/check-transcripts.py` exempts it by ID. *(Added by session M0b,
  which archived it, 2026-10-22.)*

### Session M0b (the emulator harness)
- Date: 2026-10-22
- Role: **spec side (exposed).** Never writes firmware.
- Tool: Claude Code 2.1.307 (`claude --version`), Remote Control from the
  owner's phone.
- Model ID: `claude-opus-5-5` (Claude Opus 5.5). Published cutoffs: reliable
  knowledge Jun 2026, training data Jun 2026 (PROVENANCE P-4). Flag: none.
- Session: Claude Code session `e74c69f7-ff95-4dcc-bf7a-9a980e62a6f9`,
  `https://claude.ai/code/session_01RWVcKRtXA4USAZaVZw4ZzA`.
- Where it ran: the owner's Mac (macOS, Apple Silicon), in
  `~/<top>/spec`. The prompt said "~/work/small-beeps/spec
  on the owner's Docker machine"; as with M0a, the session went on and told
  the owner. It never opened the parent folder's other entries or the clean
  folder; it read the clean session M0a's transcripts only to archive them.
- Exposure: reads the F-Emulator / fm1-emu emulator source from the public
  upstream `joakimeriksson/fm1-emu` (MIT): the crates `fm1-isa`, `fm1-core`
  and `fm1-soc`, which it vendors into `vendor/emulator/`, and, to learn how
  upstream boots an image, `crates/fm1-emu/src/main.rs` (not vendored). Also
  the upstream file list (names only). The clone was blob-less with a sparse
  checkout of just those crates, the licence and the workspace manifest, so
  `fm1-sid/` and `probes/` were never on disk. The crates' comments cite
  Felucca's hardware-layer and panel files by name and describe M-VAVE's
  stock firmware's behaviour and addresses; this session has seen those
  comments, though never Felucca's source or the stock firmware itself.
- Barriers:
  - **Hand-made settings.** The session started under
    `.claude/settings.json`, made by hand by the owner before the folder held
    a repository. SHA-256
    `daa6c52d7e54c363b17ebace836c3019a6c4a9551f9d8af7b9175f88459ce27d`; its
    exact bytes are kept as `config/claude/handmade-spec-settings.json`
    (same hash). Its seven deny rules are `config/claude/spec.json`'s, in the
    same order: no reading `**/fm1-sid/**` or `**/probes/lcdtest.c`, no
    fetching from hugelton.github.io or thefirmwarehub.com, no `git clone`
    of Felucca or dinghy.
  - **No banner.** It had no SessionStart hook when it started, so its
    transcript has no banner. `tools/check-transcripts.py` exempts exactly
    this session ID, for that reason only. `tools/spec-setup.sh` installed
    `config/claude/spec.json` (the same seven rules plus the banner hook)
    early in the session; the hook takes effect from the next session.
  - **Order.** The prompt and CONTRIBUTING.md ask for the archive, the check
    and this entry before anything else. This session first set up the
    repository, ran `tools/spec-setup.sh`, cloned the upstream crates and
    read them to plan, and then archived M0a and wrote this entry (times in
    "Barrier log"). Nothing it read before writing this entry is outside
    what the entry lists.
- Later exposure (added during the session): it also read the names of the
  upstream repository's CI workflows and one of them, to learn the Rust
  version upstream builds with; it built and ran the three crates, and
  listed parts of their generated instruction table to find encodings for
  its test images. Nothing else of that repository was read or fetched.

### Clean maintenance session 1 (before M0d)
- Date: 2026-10-22
- Role: firmware side (clean). **Stays firmware side, by the owner's
  decision** (below).
- Tool: Claude Code 2.1.308 (`claude --version`).
- Model ID: `claude-opus-5-5` (Claude Opus 5.5). Published cutoffs: reliable
  knowledge Jun 2026, training data Jun 2026 (PROVENANCE P-4). Flag: none.
- Session: Claude Code session `3a0a372e-7fbc-4446-b51a-1298219a7562` (a
  local session; it has no claude.ai session URL).
- Where it ran: the owner's Mac, in `~/<top>/clean`. The
  owner's fix steps named `~/work/small-beeps/`; the session asked, and the
  owner chose this folder's paths (the fresh copy was made beside it, in
  `~/<top>/.clean-new`).
- What it did: brought the clean folder up to main (8d55367) by the
  owner's steps. The folder had been a full clone; it was made blob-less
  (promisor remote, `blob:none` filter), fetched, given the narrowed sparse
  checkout and fast-forwarded with lazy fetching allowed.
- What happened: the fast-forward's merge summary listed the names and line
  counts of files under `vendor/emulator/` and `harness/`. No contents were
  displayed or opened. To count lines, git downloaded those files' objects
  into the folder's `.git`; `tools/clean-update.sh` then stopped with
  `STOP: 29 file(s) under vendor/emulator are in .git` and
  `STOP: 67 file(s) under harness are in .git`. None were on disk.
- How it was fixed: after checking that the folder held nothing unique (no
  unpushed commits, no stashes, no changes), the session made a fresh
  blob-less clone with the clean sparse checkout, checked that it held no
  object of the three spec-side folders (0, 0, 0), moved the old `.git`
  aside, put the fresh one in its place and deleted the old one, all
  without opening, listing or printing anything inside it. The fresh
  clone's checkout needed lazy fetching for the files it checks out (this
  session runs with it off), so that one command ran with it allowed, as
  `tools/clean-update.sh` does for its fast-forward. Afterwards
  `git status` showed no changes, `tools/clean-setup.sh` ran, and
  `tools/clean-update.sh` passed: "no spec-side files on disk or in .git".
- Exposure: none. The owner decided that a summary of file names and line
  counts is not exposure to their contents, so this session stays firmware
  side.
- Archive: archived by session M0c (spec side) as
  `sessions/clean/2026-10-22-clean-3a0a372e-….jsonl`. The merge summary's
  lines naming files under `vendor/emulator/` and `harness/` are redacted
  in that copy (its REDACTIONS.md, "The merge summary"); the owner keeps
  the original. The cause is fixed: `tools/clean-update.sh` and the steps
  in docs/PLAN.md merge with `--no-stat -q`, and C-CLEAN-FOLDER tests an
  update across a commit that changes both folders. Ten of its commands
  named the excluded folders only to exclude or count them; they are
  listed, with the owner's approval, in `sessions/REVIEWED.json`. *(Added
  by session M0c, 2026-10-22.)*

### Session M0c (the hardware spec)
- Date: 2026-10-22
- Role: **spec side (exposed).** Never writes firmware.
- Tool: Claude Code 2.1.308 (`claude --version`), Remote Control from the
  owner's phone.
- Model ID: `claude-opus-5-5` (Claude Opus 5.5). Published cutoffs: reliable
  knowledge Jun 2026, training data Jun 2026 (PROVENANCE P-4). Flag: none.
- Session: Claude Code session `91e7ef55-b2f6-424a-981d-e85c57733aaa`,
  `https://claude.ai/code/session_01RWVcKRtXA4USAZaVZw4ZzA`.
- Where it ran: the owner's Mac, in `~/<top>/spec`,
  started by `/clear` after M0b; banner `status: OK`.
- What it archived: M0b's transcript into `sessions/spec/`, and clean
  maintenance session 1's into `sessions/clean/` (reading that one to
  redact its merge summary). It left a later clean session alone
  (`b7ed6c1a-…`, which held only a `/clear` and might still be open).
- Exposure: reads, to write `HARDWARE-SPEC.md`: the vendored emulator
  crates (`vendor/emulator/`) and the harness (`harness/`), as M0b did;
  the JieLi AC79 SDK at the pinned commit (the vendored headers, and other
  headers and driver sources fetched one file at a time from Gitee);
  AL-255/FM-1-RE's hardware, memory-map and boot-chain documents, fetched
  one document at a time by URL (never cloned); public datasheets for the
  board's parts. It writes and runs small black-box test images in fwtest
  (`harness/spec-experiments/`). It does not open Felucca or anything built
  on it, dinghy, fm1-emu's `fm1-sid/` or `probes/`, or the stock firmware
  or its disassembly.
- What it actually read (added during the session): the emulator crates
  `fm1-soc` (all of it) and `fm1-core` (the interrupt and core-mode parts),
  the instruction table's syntax strings, and the harness source. From
  FM-1-RE, seven documents (PROVENANCE P-9); two of them, the boot and
  input documents, include short listings and descriptions of the stock
  firmware's code as FM-1-RE decoded it; only hardware facts were taken
  from them. The SDK files of P-10. The ST7789V datasheet (P-11). For the
  panel's labels, the owner's app screenshot and M-VAVE's product page and
  photo (P-12); the photo's screen shows the stock firmware's interface,
  which was seen but not described or used. A web search for the product
  page listed result titles mentioning M-VAVE's firmware downloads and
  forum; none of those pages was opened.

### Session M0d (the smallest firmware)
- Date: 2026-10-22
- Role: firmware side (clean).
- Exposure: none.
- Tool: Claude Code 2.1.308 (`claude --version`), Remote Control from the
  owner's phone.
- Model ID: `claude-opus-5-5` (Claude Opus 5.5). Published cutoffs: reliable
  knowledge Jun 2026, training data Jun 2026 (PROVENANCE P-4). Flag: none.
- Session: Claude Code session `b7ed6c1a-fb2a-4707-b9e2-303e11f65740`. This
  is the session M0c left alone because it then held only a `/clear`
  (11:31Z); the M0d prompt was pasted into it after that `/clear`, so its
  transcript is this session's own and is left for the next clean session
  to archive. At 13:13:44Z (banner `source: fork`, `status: OK`) Claude
  Code continued the session as `cd816ac2-14a7-4eb6-ba5f-1732c57ec45f`, a
  second transcript holding the rest of M0d; the next clean session
  archives both. Commits made after the fork still name `b7ed6c1a` in
  their `Claude-Session:` trailer; they were not rewritten for it.
- Privacy: the session saw the owner's private terms once, when the owner
  filled in `tools/private-terms.local` and Claude Code showed the changed
  file. It never wrote them anywhere; its transcripts hold them until the
  archiver redacts them.
- Where it ran: the owner's Mac, in `~/<top>/clean`; banner
  `status: OK` at the start and after `tools/clean-setup.sh`.
- Start: fast-forwarded main to `80864b9` with the prompt's steps (lazy
  fetching off, `--no-stat`), `tools/clean-update.sh` ended "no spec-side
  files on disk or in .git", and the merged branch `clean/maintenance-1`
  was deleted. Nothing was left to archive: the finished clean sessions
  (M0a's two, clean maintenance session 1) are in `sessions/clean/`, and
  `tools/check-transcripts.py` passed. M0a's original transcript has grown
  since it was archived by an idle compaction (05:01Z: a summary and
  context attachments, no tool calls); the archive tool refuses to
  overwrite, so the archived copy stays as it is.
- Reads: CONTRIBUTING.md, docs/PLAN.md, REQUIREMENTS.md, TOOLCHAIN.md,
  HARNESS.md, the M0d to M1 sections of docs/HARDWARE-SPEC.md, the vendored
  SDK headers (`WL82.h`, `csfr.h`), and this repository's tools. It runs the
  toolchain on its own test files to learn the pi32v2 assembly syntax, and
  runs its own images in fwtest through `tools/fwtest`. It does not open
  anything on the forbidden list or anything under the three spec-side
  folders.

### Session M0e-spec (the similarity audit, harness follow-ups)
- Date: 2026-10-22
- Role: **spec side (exposed).** Never writes firmware.
- Tool: Claude Code 2.1.308 (`claude --version`), Remote Control from the
  owner's phone.
- Model ID: `claude-opus-5-5` (Claude Opus 5.5). Published cutoffs: reliable
  knowledge Jun 2026, training data Jun 2026 (PROVENANCE P-4). Flag: none.
- Session: Claude Code session `fbbe5c07-7ec8-41d0-a3e4-cabd7765042f`,
  `https://claude.ai/code/session_01RWVcKRtXA4USAZaVZw4ZzA`.
- Where it ran: the owner's Mac, in `~/<top>/spec`, started by `/clear`
  after M0c; banner `status: OK`, and again after `tools/spec-setup.sh`.
- What it archived: M0c's transcript (and its one subagent) into
  `sessions/spec/`; `tools/check-transcripts.py` PASS. It left the clean
  sessions alone (the clean side archives its own).
- Exposure: reads the harness source (`harness/`) and the vendored emulator
  (`vendor/emulator/`) where fwtest decides that core 0 is waiting, and the
  separation check's tools. For the similarity audit it reads **metadata
  only** about the FM-1 firmwares, from GitHub's API and `git ls-remote`:
  repository names, owners, URLs, licences, languages, sizes, fork lists,
  commit and tree SHAs, and the one-line descriptions shown in search
  results and repository metadata (it printed some of them, a line each, to
  tell FM-1 firmwares from unrelated repositories; it read none of the
  descriptions' repositories). It never opens a target's files, README,
  commit messages or web pages, and their sources are fetched only inside
  the audit job in CI, which prints scores and file names alone. It
  fetched, read and ran JPlag on two unrelated permissive projects,
  `raspberrypi/pico-examples` (the control) and TinyUSB (the calibration),
  and on our own firmware. After the merge it read the first audit
  reports in the record: target repository names, the paths of matched
  target files, licence classes and scores, no target code.

### Session M0e, performance part (firmware side)
- Date: 2026-10-22
- Role: firmware side (clean).
- Exposure: none.
- Tool: Claude Code 2.1.308 (banner), Remote Control from the owner's phone.
- Model ID: `claude-opus-5-5` (Claude Opus 5.5). Published cutoffs: reliable
  knowledge Jun 2026, training data Jun 2026 (PROVENANCE P-4). Flag: none.
- Session: Claude Code session `fbe5a7ff-8ae0-4c14-80aa-6bbda288912a`,
  started by a `/clear` at 13:47:30Z (banner `source: clear`,
  `status: OK`) in the same Claude Code job as M0d's second transcript.
  Its own transcript is left for the next clean session to archive.
- Where it ran: the owner's Mac, in `~/<top>/clean`.
- Start: `tools/clean-update.sh` fast-forwarded to `5c6efc6` and ended "no
  spec-side files on disk or in .git"; `tools/private-terms.local` exists
  (not opened). It archived M0d's two transcripts (`b7ed6c1a`,
  `cd816ac2`) into `sessions/clean/`. The first try failed: the archiver's
  e-mail rule took the `t` of a JSON tab escape before an address and broke
  the line's JSON, and nothing was kept; the rule was fixed (with a test)
  and the archive redone. `tools/check-transcripts.py` then flagged three
  of `cd816ac2`'s shell commands, which only wrote code or PR text naming
  the spec-side folders; with the owner's approval they are listed in
  `sessions/REVIEWED.json`, and the check passes.
- Privacy: tool output showed the local username and top folder in paths
  (the archiver's messages, the Claude Code project folder's name); they
  were never written to the repository, and the archiver redacts them
  from this transcript.
- Reads: docs/PLAN.md, REQUIREMENTS.md, DESIGN-NOTES.md, HARNESS.md,
  CONTRIBUTING.md (parts), this file, sessions/README.md, the redacted
  archive of `cd816ac2` (the three flagged commands, to review them), and
  this repository's tools, workflows and firmware. It builds the firmware with
  the pinned toolchain, disassembles it in the build container, and runs it
  in fwtest through `tools/fwtest`. It does not open anything on the
  forbidden list or anything under the three spec-side folders.

### Session M1 (boot: clocks, interrupts, timer)
- Date: 2026-10-22
- Role: firmware side (clean).
- Exposure: none.
- Tool: Claude Code 2.1.308 (banner), Remote Control from the owner's phone.
- Model ID: `claude-opus-5-5` (Claude Opus 5.5). Published cutoffs: reliable
  knowledge Jun 2026, training data Jun 2026 (PROVENANCE P-4). Flag: none.
- Session: Claude Code session `7968e45c-bdf6-4029-950b-1b4d01285ed1`,
  started by a `/clear` at 21:27Z (banner `source: clear`, `status: OK`)
  in the same Claude Code job as M0e's performance part. Its own
  transcript is left for the next clean session to archive.
- Where it ran: the owner's Mac, in `~/<top>/clean`.
- Start: `tools/clean-update.sh` found main at `2513b93` and ended "no
  spec-side files on disk or in .git"; `tools/private-terms.local` exists
  (not opened). It archived M0e's performance part (`fbe5a7ff`) into
  `sessions/clean/`. The first try failed: the archiver's host-name rule
  took the `n` of a JSON newline escape before a file name ending in
  `.local` in a directory listing, and broke the line's JSON; nothing was
  kept, the rule was fixed the way the e-mail rule was (with a test), and
  the archive redone. `tools/check-transcripts.py` then flagged three of
  `fbe5a7ff`'s shell commands, which only edited `sessions/REVIEWED.json`
  or printed lines of an archived clean transcript; with the owner's
  approval they are listed in `sessions/REVIEWED.json`, and the owner
  asked for the check to stop flagging such commands. M0d's first
  transcript (`b7ed6c1a`) has a newer modification time than its archive,
  but its SHA-256 still matches the archived original, so nothing changed.
- Privacy: tool output showed the local username and top folder in paths
  (Claude Code's project folder, the archiver's messages); they were never
  written to the repository, and the archiver redacts them from this
  transcript.
- Reads: CONTRIBUTING.md, this file, sessions/README.md, docs/PLAN.md,
  REQUIREMENTS.md, DESIGN-NOTES.md, HARNESS.md, HARDWARE-SPEC.md, the
  vendored SDK headers, the redacted archive of `fbe5a7ff` (the three
  flagged commands, to review them), and this repository's tools, tests,
  workflows and firmware. It builds with the pinned toolchain and runs its
  own images in fwtest through `tools/fwtest`. It does not open anything on
  the forbidden list or anything under the three spec-side folders.
- Later in the session:
  - **The M0 release.** It is made from the signed tag `m0`. The session
    fetched `records/2513b93…/` from the `records` branch (results only:
    logs, captures, outputs, as written by CI) and rebuilt the image at the
    tag.
  - **A private term, found and withdrawn.** The record's tarball was
    attached for about a minute, then removed: its C-TRANSCRIPTS log holds
    a private term echoed from the oldest archived transcripts. That text
    was already public on the `records` branch, so nothing new was exposed.
  - **The other records.** To count them, the session scanned every record
    on the `records` branch for the private terms, by a script that never
    printed a term (19 of 21 hold one, always in that log). It also showed
    the hit lines with the term masked.
  - **SDK headers.** From the SDK, at its pinned commit, it read `hwi.h`,
    `irq.h` and `cpu.h` (a sparse fetch into a scratch folder; P-16).
  - **Separation check.** When C-SEP-TERMS flagged a line of SR-1, it
    hashed its own words to find which one (an address it had picked); it
    never saw the emulator's list.
  - **A barrier STOP, and a fresh `.git`.** For #29's update,
    `tools/clean-update.sh` printed "STOP: 17 file(s) under harness are in
    .git". The session stopped and told the owner without opening or
    listing them. The planning conversation (spec side) checked them: the
    golden outputs of the spec-side experiments (memory dumps, CSV, PNG,
    text, WAV). The `records` branch holds identical copies, which came in
    when this session fetched records wholesale: the M0 record with
    `git archive`, then the whole branch to count private terms. No
    emulator or harness source was among them. This session read none of
    those files. It had written the two extractions to its scratch folder
    and only scanned their bytes for the private terms by script. Its
    record listings did show their paths.
  - **What was done, at the owner's direction.** The folder's `.git` was
    replaced by a fresh blob-less sparse clone, and the old `.git` and the
    scratch extractions were deleted unread (22:55Z). `tools/clean-update.sh`
    then passed. New rule: clean sessions fetch only named files of the
    firmware's own records (CONTRIBUTING.md, "Records in a clean folder").
    The guard: `tools/clean-update.sh` now also checks every branch,
    records included, and C-CLEAN-FOLDER tests it.
  - **Exposure:** still none.

### Session M2 (the screen)
- Date: 2026-10-22
- Role: firmware side (clean).
- Exposure: none.
- Tool: Claude Code 2.1.309 (banner), Remote Control from the owner's phone.
- Model ID: `claude-opus-5-5` (Claude Opus 5.5). Published cutoffs: reliable
  knowledge Jun 2026, training data Jun 2026 (PROVENANCE P-4). Flag: none.
- Session: Claude Code session `d0aa28c2-493e-48cb-b0fd-be2a2d41a714`,
  started by a `/clear` at 23:04:37Z (banner `source: clear`, `status: OK`)
  in the same Claude Code job as M1. Its own transcript is left for the
  next clean session to archive.
- Where it ran: the owner's Mac, in `~/<top>/clean`.
- Start: the role file says `clean`. `tools/clean-update.sh` found main at
  `9fe07f8` and ended "no spec-side files on disk or in .git";
  `tools/private-terms.local` exists (not opened). It archived M1
  (`7968e45c`) into `sessions/clean/`; no other clean session was left
  unarchived. `tools/check-transcripts.py` flagged 19 of M1's shell
  commands. The session reviewed each in the redacted archive: they wrote
  pull request bodies, commit messages and docs naming the spec-side
  folders, edited the check's own patterns and tests, excluded the folders
  by pathspec, or counted spec-side objects without printing a name. It
  then closed the gap M1 found (a folder name ended by `;` or another
  shell operator wasn't matched), which flags three more calls of older
  clean sessions of the same kinds. All 22 are listed in
  `sessions/REVIEWED.json` for the owner's approval.
- Privacy: tool output showed the local username and top folder in paths
  (Claude Code's project folder, the archiver's messages, and the older
  archived transcripts, which predate the archiver's top-folder rule and
  are exempt by blob hash); they were never written to the repository, and
  the archiver redacts them from this transcript.
- Reads: CONTRIBUTING.md, this file, sessions/README.md,
  sessions/REVIEWED.json, docs/PLAN.md, docs/prompts/M1.md, the redacted
  archives of `7968e45c`, `36860ab8` and `3a0a372e` (the flagged commands
  only, to review them), and this repository's tools and tests. It does
  not open anything on the forbidden list or anything under the three
  spec-side folders.
- Later in the session:
  - **The M1 release.** Made from the signed tag `m1` (`9fe07f8`). From
    the `records` branch the session read only two named files of that
    commit's record, `report.json` and `SHA256SUMS`, one path at a time,
    and printed only the overall result, the checks' results and the two
    output lines of `SHA256SUMS`. The record's tree hash came from the
    trees alone.
  - **A barrier gap in `tools/reproduce`, found and closed.** Its first
    run stopped: `git archive` with pathspecs that leave the spec-side
    folders out still asked for a file under one of them, and lazy
    fetching was off, so nothing was fetched. A test in a made-up
    blob-less repository in the scratch folder showed that, with lazy
    fetching on, `git archive` downloads the excluded files into `.git`,
    even with a pathspec that names only the kept paths.
    `tools/reproduce` now reads each kept file by its object ID, and
    C-CLEAN-FOLDER tests it with lazy fetching on, against a control.
    `tools/clean-update.sh` passed before and after, so no spec-side file
    reached this folder. The session printed only the missing object's ID
    and its folder, never a file name under it.
  - **Commands the next clean session will see flagged.** Several of this
    session's shell commands name the spec-side folders as text: the
    transcript check's review commands (grep and awk over its log and the
    checker's own patterns), the folder test of the classifying command
    above, and a Python edit of the made-up test script in the scratch
    folder. None opened, listed or fetched anything under them. From then
    on the session kept those names out of shell commands.
  - **More reads.** The ST7789V datasheet (P-22: fetched into a scratch
    folder from the spec's URL, its SHA-256 checked against the spec's,
    text extracted in a throwaway container; pages 42, 43, 162, 163, 184,
    196, 215 and 224 read). `docs/HARDWARE-SPEC.md` as changed by the spec
    side's SR-1 and SR-2 answers (#32), read as a diff. The vendored SDK's
    `WL82.h` (`JL_SPI_TypeDef`, the port registers). Its own images'
    fwtest outputs. M1's image, rebuilt from the release's exported tree,
    and both disassembled to compare their idle loops.
  - **A second barrier gap, found and closed.** Merging main into the
    firmware branch staged files that main has under the spec-side folders
    (the sparse checkout keeps them off disk). The session's own
    `git diff --cached --name-only` listed them, and the pre-commit
    private-terms hook tried to read them. Lazy fetching was off, so it
    failed, printing "bad object" with each path. So the session saw the
    names of the spec side's new experiment files and of one spec
    transcript, never their contents. A barrier check (disk, index and
    every branch, counting only) found no spec-side contents in `.git`,
    before and after. The hook now never fetches (#34). Merges in a
    clean folder can stage spec-side paths, so their names can show in
    `git status` and `git diff --cached`.
  - **Exposure:** still none.

### Session SR-1-SR-2 (spec requests SR-1 and SR-2, M1's observations)
- Date: 2026-10-22
- Role: **spec side (exposed).** Never writes firmware.
- Tool: Claude Code 2.1.309 (banner), Remote Control from the owner's
  phone.
- Model ID: `claude-opus-5-5` (Claude Opus 5.5). Published cutoffs: reliable
  knowledge Jun 2026, training data Jun 2026 (PROVENANCE P-4). Flag: none.
- Session: Claude Code session `a091f4ce-8c5f-4da5-83fe-dace0af5b03e`,
  started by `/clear` (banner `source: clear`, `status: OK`).
- Where it ran: the owner's Mac, in `~/<top>/spec`; `tools/spec-setup.sh`
  banner `status: OK`; `tools/private-terms.local` exists (not opened).
- What it archived: M0e-spec's transcript (`fbbe5c07`) into
  `sessions/spec/`; `tools/check-transcripts.py` PASS.
- Exposure: reads the harness source (`harness/`) and the vendored emulator
  (`vendor/emulator/`): its memory map and bus access paths, its division,
  its timers, how fwtest reports faults, and its region handling for the
  exception and clock registers; the
  JieLi SDK (Apache-2.0) and FM-1-RE's hardware documents (WTFPL) for the
  exception and clock questions. It never opens the GPL firmwares or
  anything on the clean side's forbidden list beyond the emulator.

### Session M3 (keys, encoders, pot, LEDs)
- Date: 2026-10-23
- Role: firmware side (clean).
- Exposure: none.
- Tool: Claude Code 2.1.309 (banner), Remote Control from the owner's phone.
- Model ID: `claude-opus-5-5` (Claude Opus 5.5). Published cutoffs: reliable
  knowledge Jun 2026, training data Jun 2026 (PROVENANCE P-4). Flag: none.
- Session: Claude Code session `9f197bbc-a080-4f00-a1b8-6b6e48d827ea`,
  started by a `/clear` at 00:24:53Z (banner `source: clear`,
  `status: OK`) in the same Claude Code job as M1 and M2. Its own
  transcript is left for the next clean session to archive.
- Where it ran: the owner's Mac, in `~/<top>/clean`.
- Start: the role file says `clean`. `tools/clean-update.sh` found main at
  `4c5d76f` and ended "no spec-side files on disk or in .git";
  `tools/private-terms.local` exists (not opened). It archived M2
  (`d0aa28c2`) into `sessions/clean/`; no other clean session was left
  unarchived. `tools/check-transcripts.py` flagged 5 of M2's shell
  commands, as M2 had warned. The session printed only those commands
  from the redacted archive: an `awk` pattern list of forbidden names
  over a scratch log, edits and a `grep` of the check's own patterns, a
  `grep` of the check's log, and a scratch toy repository with dummy
  files named after the folders. The owner approved their 13 entries in
  `sessions/REVIEWED.json` in the session; the check then passed.
- Privacy: tool output showed the local username and top folder in paths
  (Claude Code's project folder, the archiver's messages); they were never
  written to the repository, and the archiver redacts them from this
  transcript.
- Reads: CONTRIBUTING.md, this file, sessions/README.md,
  sessions/REVIEWED.json, docs/PLAN.md, the redacted archive of `d0aa28c2`
  (the 5 flagged commands only), and this repository's tools, tests, docs
  and firmware. It does not open anything on the forbidden list or
  anything under the three spec-side folders.
- Later in the session:
  - **Pull requests:**
    - #38, the start;
    - #39, the speed gate's fix, chosen by the owner;
    - #41, the M3 budgets;
    - #42, the firmware, tests and docs;
    - #43, the barrier tools' shared folder list, the owner's request;
    - this wrap-up.
  - **Reads:**
    - `docs/HARDWARE-SPEC.md` (HW-33 to HW-42, HW-19 to HW-24, HW-48,
      the open questions) and docs/HARNESS.md;
    - the vendored SDK header `WL82.h` (the port, timer and ADC structs);
    - our own fwtest runs and disassembly (PROVENANCE P-23, P-24).
    It fetched nothing from FM-1-RE and did not open the panel screenshot
    in `docs/sources/`. From the CI run it read only the log's check
    lines, never the record artifact. Spec session SR-3's pull request
    was seen by title only.
  - **A tool call the safety classifier denied:** the first attempt to
    add the reviewed entries, before the owner had approved them. The
    session asked, and the owner approved.
  - **Commands the next clean session will see flagged.** They name the
    spec-side folders as text only; none opened, listed or fetched
    anything under them:
    - the two Python heredocs that added the reviewed entries (the
      denied one and the approved one), whose reasons describe M2's
      commands;
    - the `git grep`s that found where tools and tests name the folders;
    - the Python and `sed` edits of the barrier tools and their tests
      for #43, which replaced the literal names;
    - the `awk` checks of the new pattern on made-up tree lines;
    - the `gh pr create` call whose body names a harness check, and the
      edit that wrote this list.
  - **Exposure:** still none.

## Barrier log

| When (UTC) | Folder | Settings SHA-256 | Event |
|------------|--------|------------------|-------|
| 2026-10-22T02:33:04Z (session start; 2026-10-21 local time) | `~/<top>/clean` | `a557bd84…bf29b32` | Hand-made settings, owner-made before `git init` |
| 2026-10-22T03:41:31Z | same | `6240e19a…9f639156` | `tools/clean-setup.sh` installed `config/claude/clean.json` (same ten deny rules plus the banner hook); role file `clean` |
| 2026-10-22T03:41:42Z | same | `6240e19a…9f639156` | Banner tested by hand: `status: OK`. The live file was then changed by one appended space for about a second to test `CONFIG MISMATCH` (seen), and restored from a copy (hash re-checked: `6240e19a…`). No deny rule changed. |
| 2026-10-22T04:10:18Z (session start) | `~/<top>/spec` | `daa6c52d…ce27d` | Session M0b starts under the owner's hand-made spec settings, no banner hook |
| 2026-10-22T04:10:57Z | same | `daa6c52d…ce27d` | `git init`, fetch and checkout of `main`; hand-made file hashed and copied |
| 2026-10-22T04:11:17Z | same | `eaa5f875…ed542f810` | `tools/spec-setup.sh` installed `config/claude/spec.json` (same seven deny rules plus the banner hook); role file `spec`; banner printed `status: OK` |
| 2026-10-22T04:11Z to 04:20Z | same (upstream copy in the session's scratch folder) | `eaa5f875…ed542f810` | Blob-less, sparse clone of the upstream emulator (three crates, licence, workspace manifest; commit `43ed5580`), read to plan the harness |
| 2026-10-22T04:21Z | same | `eaa5f875…ed542f810` | M0a's two transcripts archived into `sessions/clean/`; `tools/check-transcripts.py` PASS; this entry written |
| 2026-10-22T11:17:25Z (session start) | `~/<top>/clean` | `6240e19a…9f639156` | Clean maintenance session 1 starts; banner `status: OK` |
| 2026-10-22T11:18:01Z | same | `aa535102…9f25ab` | After the fast-forward to main, `tools/clean-setup.sh` installed the updated `config/claude/clean.json` (no deny rule dropped); banner `status: OK` |
| 2026-10-22T11:26:43Z | same | `aa535102…9f25ab` | The folder's `.git` replaced by a fresh blob-less clone, the old one deleted unread; `tools/clean-setup.sh` re-run, banner `status: OK`; `tools/clean-update.sh` passed |
| 2026-10-22T11:31:22Z (session start, `/clear`) | `~/<top>/spec` | `eaa5f875…ed542f810` | Session M0c starts; banner `status: OK` |
| 2026-10-22T11:38Z | same | `eaa5f875…ed542f810` | M0b's transcript archived into `sessions/spec/`, clean maintenance session 1's into `sessions/clean/` (merge summary redacted); `tools/check-transcripts.py` PASS; this entry written |
| 2026-10-22T12:37:55Z | `~/<top>/clean` | `aa535102…9f25ab` | Session M0d (started by the `/clear` at 11:31:15Z, banner `status: OK`) fast-forwards to `80864b9`; `tools/clean-setup.sh` banner `status: OK`; `tools/clean-update.sh` passed; `tools/check-transcripts.py` PASS |
| 2026-10-22T12:37:16Z (session start, `/clear`) | `~/<top>/spec` | `eaa5f875…ed542f810` | Session M0e-spec starts; banner `status: OK`. 13:48:09Z: `tools/spec-setup.sh`, banner `status: OK`; M0c's transcript archived into `sessions/spec/`; `tools/check-transcripts.py` PASS; this entry written |
| 2026-10-22T13:47:30Z (session start, `/clear`) | `~/<top>/clean` | `aa535102…9f25ab` | Session M0e (performance part) starts; banner `status: OK`; `tools/clean-update.sh` fast-forwarded to `5c6efc6` and passed; M0d's two transcripts archived; `tools/check-transcripts.py` PASS |
| 2026-10-22T21:27:00Z (session start, `/clear`) | `~/<top>/clean` | `aa535102…9f25ab` | Session M1 starts; banner `status: OK`; `tools/clean-update.sh` found main at `2513b93` and passed; M0e's performance part archived; `tools/check-transcripts.py` PASS with the owner-approved reviewed entries |
| 2026-10-22, before 22:55Z | `~/<top>/clean` | `aa535102…9f25ab` | Session M1: `tools/clean-update.sh` printed STOP (17 spec-side experiment outputs in `.git`, brought in with the records branch); the session stopped and told the owner, opening nothing |
| 2026-10-22T22:55:06Z | same | `aa535102…9f25ab` | The folder's `.git` replaced by a fresh blob-less sparse clone, the old one and the session's scratch extractions of records deleted unread; `tools/clean-setup.sh` re-run, banner `status: OK`; `tools/clean-update.sh` passed, then gained the all-branches check |
| 2026-10-22T23:04:37Z (session start, `/clear`) | `~/<top>/clean` | `aa535102…9f25ab` | Session M2 starts; banner `status: OK`; `tools/clean-update.sh` found main at `9fe07f8` and passed; M1 archived; `tools/check-transcripts.py` PASS with the reviewed entries listed for the owner's approval |
| 2026-10-23, about 00:30Z | `~/<top>/clean` | `aa535102…9f25ab` | Session M2: merging main into a branch staged spec-side paths; `git diff --cached` and the pre-commit hook showed their names, the hook's reads failed (lazy fetching off); a barrier check (disk, index, every branch) found no spec-side contents in `.git`, before and after the merge commit |
| 2026-10-22T23:04:40Z (session start, `/clear`) | `~/<top>/spec` | `eaa5f875…ed542f810` | Session SR-1-SR-2 starts; banner `status: OK`. 23:05:19Z: `tools/spec-setup.sh`, banner `status: OK`; M0e-spec's transcript archived into `sessions/spec/`; `tools/check-transcripts.py` PASS; this entry written |
| 2026-10-23T00:24:53Z (session start, `/clear`) | `~/<top>/clean` | `aa535102…9f25ab` | Session M3 starts; banner `status: OK`; `tools/clean-update.sh` found main at `4c5d76f` and passed; M2 archived; `tools/check-transcripts.py` PASS with the 13 reviewed entries the owner approved in the session |

## Model cutoffs

The FM-1 and its community firmwares (Felucca and the firmwares built on it,
dinghy, FM-1 SID, and others) were released after June 2026. The owner
confirmed this on 2026-10-21; this session cannot check release dates
without touching forbidden repositories. A model whose training cutoff is in
or before June 2026 therefore cannot have learned their source in training.

| Model ID | Reliable knowledge cutoff | Training data cutoff | Source | Flag |
|----------|---------------------------|----------------------|--------|------|
| `claude-opus-5-5` | Jun 2026 | Jun 2026 | P-4 | none |

**Flag rule:** an agent session on a model whose published training cutoff
is later than June 2026 is marked **FLAGGED (cutoff after the FM-1
firmwares' release)** here and in its own entry, and its firmware-side work
needs owner review before merge.
