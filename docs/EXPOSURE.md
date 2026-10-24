<!--
SPDX-License-Identifier: MIT
SPDX-FileCopyrightText: 2026 japes98
-->

# Exposure register

*Local paths in older entries were redacted on 2026-10-22 for privacy; git
history keeps the originals; nothing else changed.*

*Which hardware layer the emulator's chip model was written from, and
under which licence, is pinned down in "Corrections" below (2026-10-23).*

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
- **Porter (exposed to the GPL firmwares):** reads GPL FM-1 engines to port
  them onto our base in the separate port repository `small-beeps-ports`
  (CONTRIBUTING.md, "Roles"). Writes here only its own entry and reports in
  `ports/` (measurements and API requests, no code). Never writes
  firmware, spec or harness, and never takes another role. Its entry
  follows the auditor's pattern, and adds what it read: each GPL engine or
  firmware by repository URL, commit and licence, and the files or folders
  opened; the port repository's commit at the session's end; the session
  ID and its transcript's SHA-256, the transcript archived in the port
  repository, never here; and the `ports/` reports it wrote. None has run
  yet (since day-1024).
  The owner confirmed on 2026-10-24 that a Claude Code session once ran
  in a folder named for the porter on the owner's Mac, for an unrelated
  project (not small-beeps): no FM-1 firmware, emulator or small-beeps
  material was involved. It was not a porter session; no porter session
  has run.

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
    - our own fwtest runs and disassembly (PROVENANCE P-24, P-25; P-23 and P-24 until SR-3 took P-23 on main).
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
  - **After a server restart** (the same session, later on 2026-10-23):
    the owner asked for main (SR-3, fwtest 0.2.0, the audit self-test)
    to be merged into #38, #42 and #44. `tools/clean-update.sh` passed
    first, at `7d8e1a7`. Each merge staged spec-side paths by name, as
    in M2; no blob was fetched. One `git diff --stat HEAD` without a
    pathspec asked for a staged spec-side blob and was refused (lazy
    fetching off), so nothing reached `.git`; `tools/clean-update.sh`
    passed again after each merge. Main's SR-3 had taken P-23, so the
    session's provenance became P-24 and P-25. To see why #42's speed
    gate was not compared after the owner merged #38, #39, #41 and #43,
    it fetched the records branch's commits and trees (a blob-less fetch:
    no file contents) and read two named files, the `report.json` of
    #41's and #43's merge records, printing only their perf budgets,
    baseline note and speed verdict; `tools/clean-update.sh` passed
    after.
  - **Exposure:** still none.

### Session SR-3 (spec request SR-3, the panel and SPI1)
*Entry added 2026-10-23 by session record-fixes-1, from SR-3's archived
transcript (`sessions/spec/2026-10-23-spec-0fb48e95-45c5-4b91-bfbb-b527c2511e3e.jsonl`);
SR-3 wrote only its barrier-log row.*
- Date: 2026-10-23
- Role: **spec side (exposed).** Never writes firmware.
- Tool: Claude Code 2.1.309 (banner), Remote Control from the owner's
  phone.
- Model ID: `claude-opus-5-5` (Claude Opus 5.5; the only model in the
  transcript). Published cutoffs: reliable knowledge Jun 2026, training
  data Jun 2026 (PROVENANCE P-4). Flag: none.
- Session: Claude Code session `0fb48e95-45c5-4b91-bfbb-b527c2511e3e`,
  started by `/clear` (banner `source: clear`, `status: OK`).
- Where it ran: the owner's Mac, in `~/<top>/spec`; `tools/spec-setup.sh`
  banner `status: OK`; `tools/private-terms.local` exists (not opened).
- What it archived: SR-1-SR-2's transcript (`a091f4ce`) into
  `sessions/spec/`; `tools/check-transcripts.py` PASS.
- What it read:
  - our own files: `docs/SPEC-REQUESTS.md`, `docs/HARDWARE-SPEC.md`,
    `docs/HARNESS.md`, CONTRIBUTING.md, PROVENANCE.md, the harness source
    and tests (`harness/`), the spec-side experiments
    (`harness/spec-experiments/`), our tools and CI workflows;
  - the vendored emulator (`vendor/emulator/`): its LCD and SPI1 model,
    its bus read and write paths, its timed peripherals (timer and
    SARADC), its CPU and machine loop, its `UPSTREAM.md` and patches. It
    added patch 0002 (SPI1's control register writes) there, chosen by
    the owner;
  - the JieLi SDK (Apache-2.0) at `5fa84a9b`: the vendored
    `vendor/jieli-sdk/` WL82 register header, and a sparse checkout into
    its scratch folder of `cpu/wl82/`, `include_lib/driver/cpu/wl82/`,
    `apps/common/example/peripheral/` (SPI and GPIO examples) and
    `apps/common/ui/` (searched in its LCD drivers);
  - FM-1-RE (WTFPL) at `ec832f28`, three documents fetched raw:
    `docs/io/08-display.md`, `docs/reversing/01-hardware-map.md` and
    `docs/io/01-boot.md`;
  - the Sitronix ST7789V datasheet, from Newhaven Display
    (SHA-256 `8ecf0e438aa25554efc473a4cfe6e436f3fb33e68cd876b25041557235d04ca1`),
    converted to text in a Debian container;
  - one empty read of another spec session's (M0e-spec's) task output in
    the scratch area (it printed nothing).
- Exposure: none beyond the spec side's. It never opens the GPL firmwares,
  fm1-emu's `fm1-sid/` or probes, or the stock firmware's disassembly.
  Whether `docs/reversing/01-hardware-map.md` counts as FM-1-RE
  disassembly material (CONTRIBUTING.md's forbidden list) is the owner's
  call; it is recorded here by its exact path.

### Session audit-selftest (the similarity audit's self-test)
- Date: 2026-10-23
- Role: **spec side (exposed).** Never writes firmware.
- Tool: Claude Code 2.1.309 (banner), Remote Control from the owner's
  phone.
- Model ID: `claude-opus-5-5` (Claude Opus 5.5). Published cutoffs: reliable
  knowledge Jun 2026, training data Jun 2026 (PROVENANCE P-4). Flag: none.
- Session: Claude Code session `dcfce033-7499-43f1-a8c3-adb8e2509ca4`,
  started by `/clear` (banner `source: clear`, `status: OK`).
- Where it ran: the owner's Mac, in `~/<top>/spec`; `tools/spec-setup.sh`
  banner `status: OK`; `tools/private-terms.local` exists (not opened).
- What it archived: SR-3's transcript (`0fb48e95`) into `sessions/spec/`;
  `tools/check-transcripts.py` PASS.
- Exposure: none beyond the spec side's. It reads our own files (the
  audit's tools, tests, settings and docs, and `firmware/`), the audit
  runs' check lines, and the permissive control and calibration projects
  (pico-examples, TinyUSB's `src/`). It runs the self-test, which uses
  only our files and the control, locally. It never opens or fetches an
  audit target, nor anything under `harness/` or `vendor/emulator/`.

### Session record-fixes-1 (two corrections to the record)
- Date: 2026-10-23
- Role: **spec side (exposed).** Never writes firmware.
- Tool: Claude Code 2.1.309 (banner), Remote Control from the owner's
  phone.
- Model ID: `claude-opus-5-5` (Claude Opus 5.5). Published cutoffs: reliable
  knowledge Jun 2026, training data Jun 2026 (PROVENANCE P-4). Flag: none.
- Session: Claude Code session `da964365-f67d-4c41-b313-a7a78fead815`,
  started by `/clear` (banner `source: clear`, `status: OK`).
- Where it ran: the owner's Mac, in `~/<top>/spec`; `tools/spec-setup.sh`
  banner `status: OK`; `tools/private-terms.local` exists (not opened).
- What it archived: audit-selftest's transcript (`dcfce033`) into
  `sessions/spec/`; `tools/check-transcripts.py` PASS.
- Exposure: none beyond the spec side's. It reads SR-3's archived
  transcript; the vendored emulator's comments, `LICENSE` and
  `UPSTREAM.md`; fm1-emu's `README.md`, `docs/*.md` and
  `crates/fm1-plugin/README.md` at `43ed5580`; `audit/targets.json`; and
  GitHub's API metadata (name, licence, description, dates) for
  hugelton/Felucca, hugelton/felucca-bsp and joakimeriksson/fm1-emu. It
  never opens any audit target's files, READMEs or web pages.

### Session M4 (audio)
- Date: 2026-10-23
- Role: firmware side (clean).
- Exposure: none.
- Tool: Claude Code 2.1.309 (banner), Remote Control from the owner's phone.
- Model ID: `claude-opus-5-5` (Claude Opus 5.5). Published cutoffs: reliable
  knowledge Jun 2026, training data Jun 2026 (PROVENANCE P-4). Flag: none.
- Session: Claude Code session `7e415aa7-2f39-4b77-b660-6461b541a9cb`,
  started by a `/clear` at 03:15:52Z (banner `source: clear`,
  `status: OK`). Its own transcript is left for the next clean session to
  archive.
- Where it ran: the owner's Mac, in `~/<top>/clean`.
- Start: the role file says `clean`. `tools/clean-update.sh` found main at
  `c36ae5f` and ended "no spec-side files on disk or in .git";
  `tools/private-terms.local` exists (not opened). It archived M3
  (`9f197bbc`) into `sessions/clean/`. The restart session the prompt
  names (after M3's server stopped) continued in that same transcript, so
  there was one file; no other clean session was left unarchived.
  `tools/check-transcripts.py` flagged 18 of its tool calls (47 entries,
  one per call and rule). The session printed only those commands from the
  redacted archive; each names forbidden folders or projects as text only
  (edits of the barrier tools for #43, `git grep`s of tracked tools and
  tests, pull request bodies, the edits of `sessions/REVIEWED.json`). The
  first attempt to add the last three entries was denied by the safety
  classifier before the owner had approved; the owner then approved all 47
  in the session, and the check passed.
- Privacy: tool output showed the local username and top folder in paths
  (Claude Code's project folder, the archiver's messages); they were never
  written to the repository, and the archiver redacts them from this
  transcript.
- Reads: CONTRIBUTING.md, this file, sessions/README.md,
  sessions/REVIEWED.json, docs/PLAN.md, docs/HARDWARE-SPEC.md,
  docs/HARNESS.md, docs/REQUIREMENTS.md, docs/prompts/M3.md, the redacted
  archive of `9f197bbc` (the flagged commands and its user turns only),
  and this repository's tools, tests, docs and firmware. It does not open
  anything on the forbidden list or anything under the three spec-side
  folders.
- Later in the session:
  - **Pull requests:**
    - #49, the start;
    - #50, the SPI1 tidy-up from M3;
    - #51, the transcript check's access rule, the owner's request;
    - #52, the M4 budgets;
    - #53, the audio firmware, tests and docs;
    - this wrap-up.
  - **Reads:**
    - `docs/HARDWARE-SPEC.md` (HW-43 to HW-46, HW-19 to HW-25, HW-36,
      HW-48, HW-59, the open questions);
    - docs/HARNESS.md;
    - the vendored SDK header `WL82.h` (`JL_ALNK0`'s struct, the register
      width macros);
    - our own fwtest runs and toolchain disassembly (PROVENANCE P-26,
      P-27).
    It fetched nothing from FM-1-RE and opened no datasheet. From CI it
    read only the checks' pass or fail.
  - **Its own transcript, previewed:** both versions of the transcript
    check were run on a scratch copy of it (not archived).
  - **A tool call the safety classifier denied:** the first attempt to
    add the last three reviewed entries, before the owner had approved
    them. The session asked, and the owner approved all 47.
  - **Commands the next clean session will see flagged.** They name a
    forbidden project only as text, the check's own rule IDs and labels;
    none opened, listed, fetched or searched anything forbidden:
    - with #51 merged, three: two `python3 -c` calls that added the
      reviewed entries (a rule's ID as a dictionary key), and the
      `python3 -c` that printed which of this session's calls the preview
      flagged;
    - without #51, also the Python heredoc that drafted the reviewed
      entries and the heredoc that wrote their reasons to a scratch file.

### Session M4b (platform load test, the loaded-case budget)
- Date: 2026-10-23
- Role: firmware side (clean).
- Exposure: none.
- Tool: Claude Code 2.1.309 (banner), Remote Control from the owner's phone.
- Model ID: `claude-opus-5-5` (Claude Opus 5.5). Published cutoffs: reliable
  knowledge Jun 2026, training data Jun 2026 (PROVENANCE P-4). Flag: none.
- Session: Claude Code session `50aec508-1493-4c23-82a2-bcba20250bc4`,
  started by a `/clear` at 09:37:34Z (banner `source: clear`,
  `status: OK`). Its own transcript is left for the next clean session to
  archive.
- Where it ran: the owner's Mac, in `~/<top>/clean`.
- Start: the role file says `clean`. `tools/clean-update.sh` found main at
  `e742f15` and ended "no spec-side files on disk or in .git";
  `tools/private-terms.local` exists (not opened). It archived M4
  (`7e415aa7`) into `sessions/clean/`; no other clean session was left
  unarchived (M0d's `b7ed6c1a` only gained Claude Code's closing metadata
  lines after its archive, as before). `tools/check-transcripts.py`
  flagged the three calls M4 predicted (with #51 merged); the session
  printed only those commands from the redacted archive. Each names a rule
  ID as text; the owner approved all three in the session, and the check
  passed. The owner also asked for the check's rule IDs to stop spelling
  out forbidden names.
- Privacy: tool output showed the local username and top folder in paths
  (Claude Code's project folder, the archiver's messages); they were never
  written to the repository, and the archiver redacts them from this
  transcript.
- Reads: CONTRIBUTING.md, this file, sessions/README.md,
  sessions/REVIEWED.json, docs/prompts/M4.md, the redacted archive of
  `7e415aa7` (the three flagged commands only), and this repository's
  tools, tests, docs and firmware. It does not open anything on the
  forbidden list or anything under the three spec-side folders.
- Later in the session:
  - **Pull requests:** #55, the start; #56, neutral rule IDs (the owner's
    request); #57, the loaded measure; #58, the M4 loaded budget; #59, the
    vendored Plaits and the C-SEP-TERMS change the owner approved; #60,
    spec requests SR-4 to SR-6; #61, the Plaits demo and results; this
    wrap-up.
  - **Reads:** `docs/HARDWARE-SPEC.md` (HW-8 to HW-13, HW-18 to HW-25,
    HW-38, HW-39, HW-43 to HW-50), docs/HARNESS.md; the upstream Plaits
    and stmlib at their pinned commits, in scratch folders (P-28): the
    vendored files, and, not vendored, upstream's `plaits/plaits.cc` and
    the two makefiles (for its buffer size and compiler flags); two of
    the SDK's app Makefiles at its pinned commit, for compiler flags
    (P-29). Nothing from FM-1-RE, no datasheet, nothing on the forbidden
    list. From CI it read the checks' pass or fail and the run logs'
    check lines; it downloaded no record or artifact.
  - **A push that wanted a spec-side object.** After the owner merged #55
    and #56, main on GitHub was a commit this folder didn't have, so
    `git push` of #57's branch tried to pack the branch's whole history
    and asked for a blob of a spec-side folder. Lazy fetching was off, so
    nothing was fetched and the push failed. To find the cause, a loop of
    `git ls-tree -r` over every local branch printed one spec-side file's
    path (a name, no contents). `tools/clean-update.sh` then brought main
    in and ended "no spec-side files on disk or in .git", and the push
    went through. Ref-wide tree listings are not to be repeated.
  - **Lazy fetching** was turned on only for scratch clones of upstream
    Plaits, stmlib and the SDK, command by command (as
    `tools/fetch-plaits.sh` does), never for this repository.
  - **Outside this folder, at the owner's request:** one built firmware
    image copied to `~/<top>/drop/` (`small-beeps-dc82c85.bin`, main's
    firmware); nothing else there was read or written.
  - **Measurement-only edits:** two switches added to `firmware/src/panel.c`
    for the loaded measure's breakdown, then restored from a copy; not
    committed.
  - **Commands the next clean session will see flagged.** A preview of the
    transcript check on a scratch copy of this session's transcript (not
    archived) flags four calls; none opened, listed, fetched or searched
    anything forbidden:
    - `toolu_01SijxKBzKrZqyFaC3SaXHQ2` (rule F-11): a `git log` whose
      pathspec leaves out the three spec-side folders, as CONTRIBUTING.md
      says to;
    - `toolu_01Mto7TBePEeHiwvJDzzp33q` (F-1, F-2, F-3, F-4, F-9, F-11): a
      `git grep` for the old rule IDs (which spelled forbidden names),
      with the same exclusions, for #56;
    - `toolu_019N5AsNFNTysKrLrpz6nhbv` (F-8): a Python heredoc editing
      NOTICE, REUSE.toml, tools/record.py and REQUIREMENTS.md for #59,
      whose text names the vendored emulator's REUSE block as an anchor;
    - `toolu_01DoGqqdewBty2B6xA9yRz4J` (F-8): `git commit -F -` with a
      message about C-SEP-TERMS, which names the emulator's folder.
    Ten more calls are logged as mentions only.
  - **C-SEP-TERMS on #61:** it failed on terms in this session's new files.
    The planning conversation (spec side) ran the check with `--show` and
    passed back only their kind (generic numeric constants: powers of two,
    masks, sign-bit and float-format constants), the three files, and
    seven hashes; no word. At the owner's direction nothing was renamed:
    the spec side is to change the check so universal constants don't
    count, and #61 waits for it.

### Session SR-4-6 (spec requests SR-4, SR-5 and SR-6)
- Date: 2026-10-23
- Role: **spec side (exposed).** Never writes firmware.
- Tool: Claude Code 2.1.309 (banner), Remote Control from the owner's
  phone.
- Model ID: `claude-opus-5-5` (Claude Opus 5.5). Published cutoffs: reliable
  knowledge Jun 2026, training data Jun 2026 (PROVENANCE P-4). Flag: none.
- Session: Claude Code session `d647e20d-4ce1-46cc-a18d-143dabc25c5a`,
  started by `/clear` at 03:13:26Z (banner `source: clear`,
  `status: OK`); its first prompt arrived at 12:25:19Z.
- Where it ran: the owner's Mac, in `~/<top>/spec`; `tools/spec-setup.sh`
  banner `status: OK`; `tools/private-terms.local` exists (not opened).
- What it archived: record-fixes-1's transcript (`da964365`) into
  `sessions/spec/`; `tools/check-transcripts.py` PASS. Clean sessions
  are left to the clean side.
- Exposure: none beyond the spec side's. It reads the spec side's usual
  material (the vendored emulator, `harness/`, the JieLi SDK, public
  datasheets), this repository's tools, tests and docs, the vendored
  Plaits tree (`vendor/plaits/`, MIT) and pull request #59's branch. It
  never opens or fetches an audit target.
- Later in the session: it ran the separation check on #61's branch
  (places and hashes only) and read SDK files at the pinned commit
  (PROVENANCE P-31). The audit's self-test ran locally against copies of
  our own files only. The owner approved deleting the session's scratch
  files when the Mac's disk filled; the container runtime then stopped
  responding, so no new spec experiment was built.

### Session M5 (the FM engine)
- Date: 2026-10-23
- Role: firmware side (clean).
- Exposure: none.
- Tool: Claude Code 2.1.309 (banner), Remote Control from the owner's phone.
- Model ID: `claude-opus-5-5` (Claude Opus 5.5). Published cutoffs: reliable
  knowledge Jun 2026, training data Jun 2026 (PROVENANCE P-4). Flag: none.
- Session: Claude Code session `22963a4d-60e7-4c81-8b7c-1a7d8155032a`,
  started by a `/clear` at 13:09:08Z (banner `source: clear`,
  `status: OK`). Its own transcript is left for the next clean session to
  archive.
- Where it ran: the owner's Mac, in `~/<top>/clean`.
- Start: the role file says `clean`. `tools/clean-update.sh` found main at
  `bdc77c8`, then at `6db115d` once the owner merged #63, and ended "no
  spec-side files on disk or in .git" both times;
  `tools/private-terms.local` exists (not opened). The Mac had 5.6 GB
  free; the owner chose to carry on, rechecking before builds. It archived
  M4b (`50aec508`) into `sessions/clean/`; no other clean session was left
  unarchived (M0d's `b7ed6c1a` again only gained closing metadata).
  `tools/check-transcripts.py` flagged four of M4b's calls; the session
  printed only those commands from the redacted archive. Each names
  forbidden material as text only (pathspec exclusions, a search pattern
  of rule IDs, licence-note anchors, a commit message); nine
  `REVIEWED.json` entries clear them, for the owner to approve in the pull
  request, and the check then passed.
- Privacy: tool output showed the local username and top folder in paths
  (Claude Code's project folder, the disk check); they were never written
  to the repository, and the archiver redacts them from this transcript.
- Reads: CONTRIBUTING.md, this file, sessions/README.md,
  sessions/REVIEWED.json, docs/HARDWARE-SPEC.md (HW-62 to HW-65 first),
  the redacted archive of `50aec508` (the four flagged commands only), and
  this repository's tools, tests, docs and firmware. For the FM engine:
  public literature only (PROVENANCE). It does not open anything on the
  forbidden list, anything under the three spec-side folders, any other
  synthesizer's firmware or any FM engine's source.
- Later in the session:
  - **The container runtime** didn't answer at first (the disk was
    nearly full); with the owner's approval the session quit and
    restarted it. No image or container was deleted.
  - **A push that wanted an object this folder didn't have**, as in M4b:
    after #64 merged, `git push` of #65's branch asked for a missing
    blob. Before running `tools/clean-update.sh` (which then fixed it),
    the session ran a `git ls-tree -r` of main filtered by `grep` for the
    missing object's ID (it printed nothing: no path was shown) and a
    loop of `git rev-list --objects --missing=print` over local branches
    that printed only branch names. Neither showed a spec-side path or
    content; per M4b's note, ref-wide tree listings are not to be
    repeated, and the session didn't again.
  - **The SDK**: one header, `include_lib/driver/cpu/wl82/asm/cpu.h` at
    the pinned commit, fetched by URL into a scratch folder for the
    lock's syntax HW-65 describes (PROVENANCE P-33).
  - **CI artifacts**: the separation check's log of #67's and #69's runs
    (places and hashes only) and their perf logs; the similarity audit's
    run logs (scores and file names only). No record or target was
    fetched.
  - **The engine** was designed from public literature (PROVENANCE P-34)
    and our own experiments (P-35). `vendor/` was left out of every
    search: it holds Plaits, which has an FM engine, and the session
    opened nothing in it (the Plaits demo's builds, in C-PLAITS-BENCH and
    the local record run, compile it as before; their output shows only
    pass or fail and numbers).

### Session SR-7 (spec request SR-7, a two-register load fwtest lacks)
- Date: 2026-10-23 (UTC; work ran into 2026-10-24)
- Role: **spec side (exposed).** Never writes firmware.
- Tool: Claude Code 2.1.309 (banner), Remote Control from the owner's
  phone.
- Model ID: `claude-opus-5-5` (Claude Opus 5.5). Published cutoffs: reliable
  knowledge Jun 2026, training data Jun 2026 (PROVENANCE P-4). Flag: none.
- Session: Claude Code session `a45f3eee-c28c-4d35-8d9d-45e71d04b1e4`,
  started by `/clear` at 13:14:14Z (banner `source: clear`,
  `status: OK`). Its first prompt named no request; the owner then
  pointed it at SR-7 (#68), merged into main at `18d9459`.
- Where it ran: the owner's Mac, in `~/<top>/spec`; `tools/spec-setup.sh`
  banner `status: OK`; `tools/private-terms.local` exists (not opened).
- What it archived: SR-4-6's transcript (`d647e20d`) into
  `sessions/spec/`; `tools/check-transcripts.py` PASS. Clean sessions
  (M5's `22963a4d`) are left to the clean side.
- Exposure: none beyond the spec side's. It reads the spec side's usual
  material (the vendored emulator, its JIT back ends included, and
  `harness/`), the pinned toolchain (run in the build container: its
  assembler, disassembler and compiler; it carries no documents), the
  vendored SDK folder's file list (no SDK document; FM-1-RE not opened),
  the vendored Plaits tree, and this repository's firmware, tools, tests
  and docs. While looking for the request before #68 existed it listed
  the clean folder's git status and changed file names (no file
  contents). It never opens or fetches an audit target.
- Later in the session: it fetched the emulator upstream at the pinned
  commit into its scratch folder (the fetch script's sparse paths only)
  to make patch 0003 against an untouched tree; compiled a corpus (the
  firmware, the vendored Plaits, its own C) with the firmware's flags and
  ran every distinct unit in fwtest; and tried to install the CI's Python
  requirements from PyPI into a scratch environment (`reuse` did not
  install; nothing else was used from it).

### Session M6a (MIDI in)
- Date: 2026-10-24
- Role: firmware side (clean).
- Exposure: none.
- Tool: Claude Code 2.1.310 (banner), Remote Control from the owner's phone.
- Model ID: `claude-opus-5-5` (Claude Opus 5.5). Published cutoffs: reliable
  knowledge Jun 2026, training data Jun 2026 (PROVENANCE P-4). Flag: none.
- Session: Claude Code session `75d8f387-ba4e-4745-971e-20f61025e67b`,
  started by a `/clear` at 02:54:30Z (banner `source: clear`,
  `status: OK`). Its own transcript is left for the next clean session to
  archive.
- Where it ran: the owner's Mac, in `~/<top>/clean`.
- Start: the role file says `clean`. `tools/clean-update.sh` found main at
  `cdfd067` and ended "no spec-side files on disk or in .git";
  `tools/private-terms.local` exists (not opened). The Mac had 4.1 GB
  free. It archived M5 (`22963a4d`) into `sessions/clean/`; no other clean
  session was left unarchived (M0d's `b7ed6c1a` has the same length as
  its archive). `tools/check-transcripts.py` flagged four of M5's calls;
  the session printed only those commands from the redacted archive. Each
  names forbidden material as text only (pull request bodies and commit
  messages about SR-7, a harness gap); four `REVIEWED.json` entries clear
  them, for the owner to approve in the pull request, and the check then
  passed.
- Privacy: tool output showed the local username and top folder in paths
  (Claude Code's project folder, the disk check); they were never written
  to the repository, and the archiver redacts them from this transcript.
- Reads: CONTRIBUTING.md, this file, sessions/README.md,
  sessions/REVIEWED.json, the redacted archive of `22963a4d` (the four
  flagged commands only), docs/HARDWARE-SPEC.md, docs/HARNESS.md, and this
  repository's tools, tests, docs and firmware. For MIDI: the MIDI 1.0
  specification as public literature (PROVENANCE). It does not open
  anything on the forbidden list, anything under the three spec-side
  folders, or any other synthesizer's firmware or MIDI code.
- Later in the session:
  - **A push that wanted an object this folder didn't have**, as in M4b
    and M5: twice (#75's branch and the MIDI branch). Each time
    `tools/clean-update.sh`, run from main, fixed it and ended "no
    spec-side files on disk or in .git". Once it was first run on a
    feature branch, where its fast-forward stopped before its checks; it
    was run again from main at once. No tree listing was made.
  - **Merging main into the MIDI branch after #77** put the spec-side
    folders' changed paths into the index, and `git status` printed their
    names (file names only: emulator patch and harness test file names, a
    spec transcript's name), as in M2. A check found none of them on disk
    and none of their blobs in `.git`. No content was shown or fetched.
  - **SR-8's answer** was read from its open pull request (#81), at the
    owner's direction: only `docs/HARDWARE-SPEC.md`, `docs/HARNESS.md`,
    `docs/SPEC-REQUESTS.md` and `PROVENANCE.md`, each fetched by
    GitHub's contents API at the PR's branch (and `PROVENANCE.md` of
    #80 and #82, for the IDs they take). Nothing under the spec-side
    folders was fetched.
  - **The toolchain** compiled a two-function C file of ours in the build
    container to check the build's rotate guard (P-37).
  - **Disk**: free space fell to 2.1 GB; with the owner's choice the
    session pruned Docker's stopped containers (1.0 GB), and it stayed
    above 5 GB after.
### Session emulator-parity (fwtest and the F-Emulator app on one emulator)
- Date: 2026-10-24 (UTC)
- Role: **spec side (exposed).** Never writes firmware.
- Tool: Claude Code 2.1.310 (banner).
- Model ID: `claude-opus-5-5` (Claude Opus 5.5). Published cutoffs: reliable
  knowledge Jun 2026, training data Jun 2026 (PROVENANCE P-4). Flag: none.
- Session: Claude Code session `9d5d3a07-eba7-4567-8198-f0382f4ba9b0`,
  started by `/clear` at 04:03:28Z (banner `source: clear`,
  `status: OK`), on main at `cdfd067`.
- Where it ran: the owner's Mac, in `~/<top>/spec`; `tools/spec-setup.sh`
  banner `status: OK`; `tools/private-terms.local` exists (not opened).
- What it archived: SR-7's transcript (`a45f3eee`) into `sessions/spec/`;
  `tools/check-transcripts.py` PASS.
- Exposure: none beyond the spec side's. It reads the spec side's usual
  material (the vendored emulator and `harness/`), the pinned toolchain
  (run in the build container: its assembler, disassembler and compiler),
  and this repository's tools, tests and docs. New for this session: the
  F-Emulator app's emulator patch notes and patch files, which the owner
  put in a drop folder outside the repository
  (`~/<top>/drop/emulator-patches/`) and has the right to license MIT
  here. They are patches to the same emulator the spec side already
  reads. The notes also name community firmwares the app was run on (as
  test subjects, with their results: which changed, which halted) and
  quote one of them: a two-instruction fragment, the four bytes of one
  instruction and the instruction after it, that showed the app's
  pair-head bug. That is the only community-firmware content in them: no
  source and no other code. The session takes that fragment only as a bug
  report, confirms the behaviour from the vendor toolchain and our own
  firmware's compiled code instead. It names no community firmware
  outside this file and its transcript, except in two code comments of
  the app's that its patches carry unchanged into `vendor/emulator/`
  (spec side only; a firmware's name and what the app saw it do, no
  code). It opens nothing else of the app's, and never opens or fetches
  an audit target.
- Later in the session: it fetched the emulator upstream at the pinned
  commit (the fetch script's sparse paths only) to re-vendor with the new
  patches; ran the pinned toolchain's assembler, disassembler and
  compiler (PROVENANCE P-40) on our firmware's sources and on code of its
  own; and built fwtest natively three times in its scratch folder (the
  0.3.0 emulator, with the three fixes, with all five patches) to compare
  the outputs of the firmware suite, the spec experiments and the
  harness suite.

### Session midi-in-out (SR-8, MIDI out, housekeeping)
- Date: 2026-10-24 (UTC)
- Role: **spec side (exposed).** Never writes firmware.
- Tool: Claude Code 2.1.310 (banner).
- Model ID: `claude-opus-5-5` (Claude Opus 5.5). Published cutoffs: reliable
  knowledge Jun 2026, training data Jun 2026 (PROVENANCE P-4). Flag: none.
- Session: Claude Code session `fbe11e0f-3e0f-4f6d-b9f2-e00ce09921b7`,
  started by `/clear` at 05:45:26Z (banner `source: clear`,
  `status: OK`), on main at `1537391`.
- Where it ran: the owner's Mac, in `~/<top>/spec`; `tools/spec-setup.sh`
  banner `status: OK`; `tools/private-terms.local` exists (not opened).
- What it archived: emulator-parity's transcript (`9d5d3a07`) into
  `sessions/spec/`; `tools/check-transcripts.py` PASS.
- Exposure: the spec side's usual material (the vendored emulator and
  `harness/`, the pinned toolchain, this repository). New for this
  session, all allowed sources: FM-1-RE's MIDI, USB, Bluetooth, hardware
  map and subsystems documents (hardware facts only; P-41); single files
  of the pinned JieLi SDK (P-41, P-45); M-VAVE's FM-1 manual and the
  SMK-37 Pro's manual as ManualsLib shows it (P-41, P-42); retailer and
  review pages found by web search, read only to find the manuals. It
  did not fetch the SMK-37 board layer the emulator's comments name (a
  firmware port, not an allowed source).
- FM1 Open (`m-vave/fm1_open`), its terms only: at the owner's request it
  listed the repository's file names (the root, `sdk/`, and a search of
  the tree for licence and terms files) and read its two terms files,
  `LICENSE.md` (SHA-256 `fe7344af68a6e65d0cf623e3eca1ff4a4d751ba538bffbc5248134b79d02f1fd`)
  and `THIRD_PARTY.md` (`c10451a1c0b368ec926e86b9296eb0c96c790d4d4768ad07e91b09ca9ea4bfa5`),
  at commit `4c7496daac04a95ff10d1afdcc8f9ead2dbabc41`, fetched by raw URL
  into its scratch folder. No code, script, build file or other document
  of it was opened. What they allow is in docs/PLAN.md, "Risks" ("FM1
  Open's terms"): GPLv3-only app sources with a section 7 permission to
  link M-VAVE's binary SDK; the binary engine copyable, linkable and
  redistributable in binary form for M-VAVE FM1 devices only; the boot and
  update resources and the FM-1's recovery image under Apache-2.0.
- Later in the session: it ran fwtest (pinned and local builds), its own
  spec experiments (E-19 to E-21), the firmware suite on fwtest 0.4.0 and
  0.5.0 to compare, and the similarity audit's self-test locally (its
  made-up target holds only copies of our files; no audit target was
  fetched or opened).

### Session pin-050 (fwtest 0.5.0's pin, the 0008 test fix, Q-12)
- Date: 2026-10-24 (UTC)
- Role: **spec side (exposed).** Never writes firmware.
- Tool: Claude Code 2.1.310 (banner).
- Model ID: `claude-opus-5-5` (Claude Opus 5.5). Published cutoffs: reliable
  knowledge Jun 2026, training data Jun 2026 (PROVENANCE P-4). Flag: none.
- Session: Claude Code session `9406e046-30cd-43f2-b1cd-9c0552cd63d0`,
  started by `/clear` at 12:56:38Z (banner `source: clear`,
  `status: OK`), on main at `7b5144b`.
- Where it ran: the owner's Mac, in `~/<top>/spec`; `tools/spec-setup.sh`
  banner `status: OK`; `tools/private-terms.local` exists (not opened).
- What it archived: midi-in-out's transcript (`fbe11e0f`) into
  `sessions/spec/`; `tools/check-transcripts.py` PASS.
- Exposure: the spec side's usual material (the vendored emulator and
  `harness/`, the pinned toolchain, this repository). New for this
  session: the F-Emulator app's note `test-fix-0008.md` in the owner's
  drop folder (that file only; P-47); a clean upstream copy of the
  emulator's three crates with fwtest's patches, in its scratch folder;
  JieLi's AC63 Bluetooth SDK (Apache-2.0, another chip family's SDK, which
  the owner allowed for Q-12): its licence and English README, three UART
  drivers, six chip headers' UART words and one clock header, by raw URL
  into its scratch folder, plus GitHub's repository list and code search
  for file paths (P-48). The Manuals+ write-up of the SMK-37 Pro's manual
  was given by the owner as a citation and a reading; this session did not
  open it (P-49). Nothing of any firmware was read.
- Later in the session: it ran the firmware suite on fwtest 0.4.0 and
  0.5.0 (pinned), the `midiout` test image through the pinned fwtest, and
  the emulator crates' and harness's own tests.

### Session M6b (MIDI out)
- Date: 2026-10-24
- Role: firmware side (clean).
- Exposure: none.
- Tool: Claude Code 2.1.310 (banner), Remote Control from the owner's phone.
- Model ID: `claude-opus-5-5` (Claude Opus 5.5). Published cutoffs: reliable
  knowledge Jun 2026, training data Jun 2026 (PROVENANCE P-4). Flag: none.
- Session: Claude Code session `89fcb09b-f267-409b-b8c4-776025e3d530`,
  started by a `/clear` at 13:01:56Z (banner `source: clear`,
  `status: OK`). Its own transcript is left for the next clean session to
  archive.
- Where it ran: the owner's Mac, in `~/<top>/clean`.
- Start: the role file says `clean`. `tools/clean-update.sh`, run from
  main, found main at `663f135` and ended "no spec-side files on disk or
  in .git"; `tools/private-terms.local` exists (not opened). The Mac had
  4.8 GB free. It archived M6a (`75d8f387`) into `sessions/clean/`; every
  other clean session was already archived. `tools/check-transcripts.py`
  flagged five of M6a's calls; the session printed only those commands
  from the redacted archive. Each names a spec-side folder as text only
  (a pull request body, and `git diff` pathspecs that leave the folders
  out); five `REVIEWED.json` entries clear them, for the owner to approve
  in the pull request, and the check then passed.
- Reads: CONTRIBUTING.md, this file, sessions/README.md,
  sessions/REVIEWED.json, the redacted archive of `75d8f387` (the five
  flagged commands only), docs/HARDWARE-SPEC.md, docs/HARNESS.md, and this
  repository's tools, tests, docs and firmware. For MIDI: the MIDI 1.0
  specification as public literature (PROVENANCE). It does not open
  anything on the forbidden list, anything under the three spec-side
  folders, or any other synthesizer's firmware or MIDI code.
- Later in the session:
  - **fwtest 0.5.0 before its pin:** the published image of #84's merge
    (digest from its fwtest-image run's log, already pulled), run as a
    black box through `tools/fwtest` with `FWTEST_IMAGE`, as HARNESS.md
    on main documents it (P-50); the pin is the spec side's (#91).
  - **P-IDs:** to number its PROVENANCE entry, it read `PROVENANCE.md`
    alone on the open spec branches of #92 and #93 through GitHub's
    contents API (they take P-47 to P-49), and the file lists of #89,
    #91, #92 and #93: file names only, among them a spec transcript's
    and its redaction note's; no content shown or fetched, nothing under
    the spec-side folders fetched.
  - **The toolchain** built the firmware and its test images in the
    build container, as before. Disk stayed between 4.5 and 4.8 GB free.

### Session M7 (flash storage, then the M8 proposal)
- Date: 2026-10-24
- Role: firmware side (clean).
- Exposure: none to GPL material. One FM-1-RE document that describes the
  stock firmware's internals was read; see "Reads" (for the owner to
  rule on).
- Tool: Claude Code 2.1.310 (banner), unattended (the owner away for the
  day).
- Model ID: `claude-opus-5-5` (Claude Opus 5.5). Published cutoffs: reliable
  knowledge Jun 2026, training data Jun 2026 (PROVENANCE P-4). Flag: none.
- Session: Claude Code session `cd82f4be-e875-4959-b383-d66813d290ce`,
  started by a `/clear` at 14:13:39Z (banner `source: clear`,
  `status: OK`). Its own transcript is left for the next clean session to
  archive.
- Where it ran: the owner's Mac, in `~/<top>/clean`.
- Start: the role file says `clean`. `tools/clean-update.sh`, run from
  main, found main at `6ba587e` and ended "no spec-side files on disk or
  in .git"; `tools/private-terms.local` exists (not opened). The Mac had
  4 GB free. It archived M6b (`89fcb09b`) into `sessions/clean/`; every
  other clean session was already archived. `tools/check-transcripts.py`
  flagged two of M6b's calls; the session printed only those commands
  from the redacted archive. Each names a spec-side folder only as a
  pathspec exclusion; two `REVIEWED.json` entries clear them, for the
  owner to approve in the pull request, and the check then passed.
- Reads: CONTRIBUTING.md, this file, sessions/REVIEWED.json, the redacted
  archive of `89fcb09b` (the two flagged commands only),
  docs/HARDWARE-SPEC.md, docs/HARNESS.md, docs/SPEC-REQUESTS.md, and this
  repository's tools, tests, docs and firmware. Also, at about 14:20Z, FM-1-RE's
  `docs/io/09-storage.md` at commit `ec832f28` (the commit P-9 names),
  fetched alone by raw URL into the session's scratch folder, SHA-256
  `8f11adc0673ac00bbdd6bcd2186874aafbadd69c7f9462a73a94a9113b0155ff`. It is
  one of the documents CONTRIBUTING.md allows and the spec side cited (P-9),
  but most of it describes the stock firmware's own code (its routines'
  addresses and names, and how its own record store and patch storage
  work), which CONTRIBUTING.md also forbids ("any disassembly or function
  database of it"). The session read it once, deleted its copy at
  14:23:18Z, and uses nothing from it: no fact, no layout, no design; the
  questions it touches went to the spec side as SR-9. The store's design
  (a ring of 16 sectors with sequence numbers, records with a CRC-32, the
  newest valid copy winning, live records copied forward before the
  oldest sector is erased, a reset record) was written down in this
  session's transcript before the document was opened, and differs from
  what the document describes. Whether reading it changes this session's
  role is the owner's call (the session's Questions); meanwhile it works
  as firmware side. It does not open anything on the forbidden list's
  other entries, anything under the three spec-side folders, or any other
  synthesizer's firmware.

### Session day-1024 (flash facts for M7, spec requests, the porter role)
- Date: 2026-10-24 (UTC)
- Role: **spec side (exposed).** Never writes firmware.
- Tool: Claude Code 2.1.310 (banner).
- Model ID: `claude-opus-5-5` (Claude Opus 5.5). Published cutoffs: reliable
  knowledge Jun 2026, training data Jun 2026 (PROVENANCE P-4). Flag: none.
- Session: Claude Code session `4fc544d9-3a50-4ba0-9cb1-91fc187048df`,
  started by `/clear` at 14:13:11Z (banner `source: clear`,
  `status: OK`), on main at `6ba587e`. Unattended: the owner reviews on
  return.
- Where it ran: the owner's Mac, in `~/<top>/spec`; `tools/spec-setup.sh`
  banner `status: OK`; `tools/private-terms.local` exists (not opened).
  4.8 GB free at the start.
- What it archived: pin-050's transcript (`9406e046`) into
  `sessions/spec/`; `tools/check-transcripts.py` PASS.
- Exposure: the spec side's usual material (the vendored emulator and
  `harness/`, the pinned toolchain, this repository). New for this
  session, all allowed sources: FM-1-RE's architecture, boot, storage,
  update-protocol and reflash documents and its two reversing overviews
  of the hardware map and boot (hardware and layout facts only; P-51);
  single files of the pinned JieLi SDK (P-52); Puya's P25Q80H datasheet
  and, found while searching for it, the datasheets of four other Puya
  parts, not used (P-53); web search results. A Python virtual
  environment with `pypdf` in its scratch folder, to read the
  datasheets' text.
- From the firmware side's open pull request #95 it read only
  `docs/SPEC-REQUESTS.md` (SR-9), `PROVENANCE.md`'s IDs and the list of
  its files, then merged that branch into SR-9's answer, so its files are
  in that branch; no other file of it was opened.
- Later in the session: spec experiment E-22 (the flash chip in fwtest);
  vendor patches 0010 and 0011 and fwtest 0.6.0, built and tested on the
  Mac with the pinned Rust (the emulator's crates and the harness); the
  firmware at main's `6ba587e` built in the build container and its suite
  run on fwtest 0.5.0 (pinned) and 0.6.0 (local) to compare; the
  toolchain's disassembly of that firmware, the harness's test images and
  the spec experiments, scanned for dual-issue pairs. Docker's build
  cache was pruned once to keep disk free (no image removed).
- The porter role (CONTRIBUTING.md, `config/claude/porter.json`,
  `tools/porter-setup.sh`, `ports/README.md`): written from this
  repository's own rules; no GPL engine was opened for it, and no porter
  session was started.
- FM1 Open (`m-vave/fm1_open`, commit
  `4c7496daac04a95ff10d1afdcc8f9ead2dbabc41`, as session midi-in-out
  read it), its terms only: its file list and git blob hashes (GitHub's
  API), and its two terms files `LICENSE.md` and `THIRD_PARTY.md` (same
  SHA-256 as midi-in-out recorded), by raw URL into the scratch folder.
  No code, script, build file, binary or other document of it was opened.
  The pinned AC79 SDK's file list and blob hashes were compared with them
  (no SDK file opened for it). Result in docs/PLAN.md ("Vendoring FM1
  Open's boot and update files for M9").

## Corrections

### 2026-10-23: which hardware layer, under which licence
*Written by session record-fixes-1. Older entries are left as written.*

- **What was stated.** This register (its opening list and the planning
  conversation's entry), CONTRIBUTING.md ("Roles") and earlier prompts
  (`docs/prompts/M0a.md`) say the emulator's chip model was partly written
  from "the GPL Felucca firmware's hardware layer" or "Felucca's hardware
  layer", without naming a repository or a licence version. The audit's
  metadata (`audit/targets.json`) lists a separate repository by Felucca's
  author, hugelton/felucca-bsp, a board support package licensed MPL-2.0,
  which raised the question whether the hardware layer meant was that one.
- **What the sources show.**
  - The vendored emulator (`vendor/emulator/`, fm1-emu at `43ed5580`)
    credits "Felucca's HAL" and "Felucca HAL headers" in the module
    comments of `crates/fm1-soc/src/` (`lib.rs`, `periph.rs`, `lcd.rs`,
    `spiflash.rs`), and `periph.rs` gives their location as
    `reference/Felucca/firmware/hal/`: the `hal/` folder of a local clone
    of Felucca. No file there names felucca-bsp, a BSP, or MPL. Its own
    licence is MIT (`LICENSE`).
  - fm1-emu's `README.md` ("Credits") names "the hardware layer of
    hugelton/Felucca", linking https://github.com/hugelton/Felucca. Its
    `docs/recon.md` lists hugelton/Felucca as a "GPL-3.0 C firmware" whose
    `hal/` hardware layer is "de-facto peripheral documentation", and its
    list of repositories cloned into `reference/` includes Felucca and no
    BSP. None of fm1-emu's README or `docs/` files mentions felucca-bsp.
  - GitHub's API (2026-10-23) reports hugelton/Felucca's licence as
    GPL-3.0 and hugelton/felucca-bsp's as MPL-2.0 (no description).
    felucca-bsp was created on 2026-10-09, a week after Felucca
    (2026-10-02).
  - Limit: the API reports a repository-level licence for the current
    default branch. Per-file licence headers in Felucca's `hal/` were not
    checked, since opening them is forbidden.
- **What it means.** The chip model credits the hardware layer (`hal/`)
  of **hugelton/Felucca, licensed GPL-3.0**, not hugelton/felucca-bsp. The
  old wording was right; this names the repository and licence version.
  The spec side's exposure is to GPL-3.0 material, as assumed; it is not
  reduced. felucca-bsp's MPL-2.0 licence has no bearing on the emulator's
  provenance, and felucca-bsp stays an audit target like Felucca's other
  repositories. The clean-room rules are unchanged. CONTRIBUTING.md
  ("Roles") now names the repository and licence; the older entries and
  prompts keep their wording.

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
| 2026-10-23T00:25:37Z (session start, `/clear`) | `~/<top>/spec` | `eaa5f875…ed542f810` | Session SR-3 starts; banner `status: OK`. 00:26:15Z: `tools/spec-setup.sh`, banner `status: OK`; SR-1-SR-2's transcript archived into `sessions/spec/`; `tools/check-transcripts.py` PASS; this entry written |
| 2026-10-23T02:10:46Z (session start, `/clear`) | `~/<top>/spec` | `eaa5f875…ed542f810` | Session audit-selftest starts; banner `status: OK`. 02:11:08Z: `tools/spec-setup.sh`, banner `status: OK`; SR-3's transcript archived into `sessions/spec/`; `tools/check-transcripts.py` PASS; this entry written |
| 2026-10-23T02:52:56Z (session start, `/clear`) | `~/<top>/spec` | `eaa5f875…ed542f810` | Session record-fixes-1 starts; banner `status: OK`. 02:53:13Z: `tools/spec-setup.sh`, banner `status: OK`; audit-selftest's transcript archived into `sessions/spec/`; `tools/check-transcripts.py` PASS; this entry written |
| 2026-10-23T03:15:52Z (session start, `/clear`) | `~/<top>/clean` | `aa535102…9f25ab` | Session M4 starts; banner `status: OK`; `tools/clean-update.sh` found main at `c36ae5f` and passed; M3 archived; `tools/check-transcripts.py` PASS with the 47 reviewed entries the owner approved in the session |
| 2026-10-23T09:37:34Z (session start, `/clear`) | `~/<top>/clean` | `aa535102…9f25ab` | Session M4b starts; banner `status: OK`; `tools/clean-update.sh` found main at `e742f15` and passed; M4 archived; `tools/check-transcripts.py` PASS with the 3 reviewed entries the owner approved in the session |
| 2026-10-23T03:13:26Z (session start, `/clear`) | `~/<top>/spec` | `eaa5f875…ed542f810` | Session SR-4-6 starts; banner `status: OK`. 12:25:40Z: `tools/spec-setup.sh`, banner `status: OK`; record-fixes-1's transcript archived into `sessions/spec/`; `tools/check-transcripts.py` PASS; this entry written |
| 2026-10-23T13:14:14Z (session start, `/clear`) | `~/<top>/spec` | `eaa5f875…ed542f810` | Session SR-7 starts; banner `status: OK`. 14:22:19Z: `tools/spec-setup.sh`, banner `status: OK`; after #68, SR-4-6's transcript archived into `sessions/spec/`; `tools/check-transcripts.py` PASS; this entry written |
| 2026-10-24T02:54:30Z (session start, `/clear`) | `~/<top>/clean` | `aa535102…9f25ab` | Session M6a starts; banner `status: OK`; `tools/clean-update.sh` found main at `cdfd067` and passed; M5 archived; `tools/check-transcripts.py` PASS with the 4 reviewed entries listed for the owner's approval |
| 2026-10-24T04:03:28Z (session start, `/clear`) | `~/<top>/spec` | `eaa5f875…ed542f810` | Session emulator-parity starts; banner `status: OK`. 04:04:11Z: `tools/spec-setup.sh`, banner `status: OK`; SR-7's transcript archived into `sessions/spec/`; `tools/check-transcripts.py` PASS; this entry written |
| 2026-10-24T05:45:26Z (session start, `/clear`) | `~/<top>/spec` | `eaa5f875…ed542f810` | Session midi-in-out starts; banner `status: OK`. 05:45:47Z: `tools/spec-setup.sh`, banner `status: OK`; emulator-parity's transcript archived into `sessions/spec/`; `tools/check-transcripts.py` PASS; this entry written |
| 2026-10-24T12:56:38Z (session start, `/clear`) | `~/<top>/spec` | `eaa5f875…ed542f810` | Session pin-050 starts; banner `status: OK`. 12:57:24Z: `tools/spec-setup.sh`, banner `status: OK`; midi-in-out's transcript archived into `sessions/spec/`; `tools/check-transcripts.py` PASS; this entry written |
| 2026-10-24T13:01:56Z (session start, `/clear`) | `~/<top>/clean` | `aa535102…9f25ab` | Session M6b starts; banner `status: OK`; `tools/clean-update.sh` found main at `663f135` and passed; M6a archived; `tools/check-transcripts.py` PASS with the 5 reviewed entries listed for the owner's approval |
| 2026-10-24T14:13:39Z (session start, `/clear`) | `~/<top>/clean` | `aa535102…9f25ab` | Session M7 starts; banner `status: OK`; `tools/clean-update.sh` found main at `6ba587e` and passed; M6b archived; `tools/check-transcripts.py` PASS with the 2 reviewed entries listed for the owner's approval |

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
