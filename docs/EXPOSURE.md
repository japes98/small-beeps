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
  has run. (The owner's answer to session day-1024's question, recorded
  again in session evening-1024; the other project's details are not
  recorded here.)

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
- Later in the session:
  - **SR-9's answer before it merged:** from the open spec pull request
    #97 (head `c1e68efa`), the session read `docs/HARDWARE-SPEC.md`,
    `docs/HARNESS.md` and `docs/SPEC-REQUESTS.md` alone, each through
    GitHub's contents API into its scratch folder (nothing fetched into
    `.git`), and used HW-76 to HW-82 (P-55).
  - **Metadata only:** the file lists of #96 and #97 (names, among them
    a spec transcript's and its redaction note's, and files under
    `harness/spec-experiments/`); from #97's file list, the git blob
    hashes of four files it shares with #95 (all four identical to
    #95's) and the count of lines it adds to PROVENANCE.md (three, so
    P-51 to P-53), to number P-54; #99 then took P-54 too, so it became
    P-55 when main was merged in. No content of any other file was
    fetched or shown, and nothing under the spec-side folders.
  - **CI artifacts:** to find C-SEP-TERMS' hit on #98 and the build's
    hash on #106, the session downloaded those two runs' report
    artifacts whole into its scratch folder and opened only
    `logs/C-SEP-TERMS.log`, `outputs/SHA256SUMS` and the artifact's
    top-level listing. Each artifact also held the record's `harness/`
    folder (the harness's own test results, which records keep); nothing
    in it was opened, and both artifacts were deleted at 16:10Z.
    Next time, take only the named files.
  - **On 2026-10-25,** to see why #98 still failed C-SEP-TERMS, the
    session downloaded that run's report artifact again, copied out only
    `logs/C-SEP-TERMS.log` and deleted the rest unopened at 01:42Z.
  - **The toolchain** built the firmware and its test images in the
    build container, as before. Disk stayed between 3 and 4 GB free.

### Session M8a (the store's region, then the instrument's interface)
- Date: 2026-10-25
- Role: firmware side (clean).
- Exposure: none.
- Tool: Claude Code 2.1.310 (banner), largely unattended (the owner
  checks in now and then).
- Model ID: `claude-opus-5-5` (Claude Opus 5.5). Published cutoffs: reliable
  knowledge Jun 2026, training data Jun 2026 (PROVENANCE P-4). Flag: none.
- Session: Claude Code session `93de9c87-4f4f-427b-9b35-3c7addd90fd8`,
  started by a `/clear` at 02:12:20Z (banner `source: clear`,
  `status: OK`). Its own transcript is left for the next clean session to
  archive.
- Where it ran: the owner's Mac, in `~/<top>/clean`.
- Start: the role file says `clean`. `tools/clean-update.sh` found main
  at `1123eca` and ended "no spec-side files on disk or in .git";
  `tools/private-terms.local` exists (not opened). The Mac had 3.1 GB
  free. It archived M7 (`cd82f4be`) into `sessions/clean/`; every other
  clean session was already archived. `tools/check-transcripts.py`
  flagged two of M7's calls; the session printed only those two commands
  from the redacted archive. One deletes the two scratch folders of the
  CI artifacts M7 downloaded whole (already recorded above), the other
  writes a memory note; each names a spec-side folder only in text. Two
  `REVIEWED.json` entries clear them, for the owner to approve in the
  pull request, and the check then passed.
- Reads: CONTRIBUTING.md, this file, sessions/README.md,
  sessions/REVIEWED.json, the redacted archive of `cd82f4be` (the two
  flagged commands only), docs/HARDWARE-SPEC.md (HW-36, HW-76 to HW-82),
  docs/M8-PROPOSAL.md, docs/STORE-FORMAT.md, docs/DESIGN-NOTES.md, and
  this repository's tools, tests, docs and firmware. FM-1-RE's
  `docs/io/09-storage.md` is no longer allowed for the firmware side (the
  spec side's change of 2026-10-25); this session never opened it.
- Later in the session:
  - **Open spec pull requests, metadata and named files only:** the
    file lists of #110 and #112 (names only; among them a spec
    transcript's, never opened), #112's description, and through GitHub's
    contents API `config/fwtest-image` on #112's branch and
    `PROVENANCE.md` on the branches of #110, #112, #113, #114 and #115
    (only the last row's ID read, to number P-58). Nothing fetched into
    `.git`, nothing under the spec-side folders.
  - **fwtest 0.6.0 before its pin merged:** with only
    `config/fwtest-image` changed locally (never committed), the store's
    nine cases on main's firmware and on #111's, both PASS, and one
    diagnostic run of the env case (the same hang as on 0.5.0: our own
    `gfx_line`, fixed in #121). The results went to #112 as a comment.
  - **The toolchain** built the firmware and its test images in the
    build container; the disassembler in that container
    (`/opt/jieli/pi32v2/bin/objdump`) was run on our own ELF to read the
    spectrum's compiled loop.
  - **Disk:** 3.1 GB free at the start, 2.3 to 2.4 GB through the day;
    `out/` cleared between runs; Docker left alone.

### Session evening-1024 (fwtest 0.6.0's pin, the flash pins, M9's plan, spec requests)
- Date: 2026-10-25 (UTC)
- Role: **spec side (exposed).** Never writes firmware.
- Tool: Claude Code 2.1.310 (banner).
- Model ID: `claude-opus-5-5` (Claude Opus 5.5). Published cutoffs: reliable
  knowledge Jun 2026, training data Jun 2026 (PROVENANCE P-4). Flag: none.
- Session: Claude Code session `e7979b06-3055-45cf-9e7c-11ab22ca1ee7`,
  started by `/clear` at 02:13:03Z (banner `source: clear`,
  `status: OK`), on main at `1123eca`. Largely unattended: the owner
  checks in occasionally.
- Where it ran: the owner's Mac, in `~/<top>/spec`; `tools/spec-setup.sh`
  banner `status: OK`; `tools/private-terms.local` exists (not opened).
  3.1 GB free at the start.
- What it archived: day-1024's transcript (`4fc544d9`) into
  `sessions/spec/`; `tools/check-transcripts.py` PASS. M7's (clean) is
  left for the next clean session.
- Exposure: the spec side's usual material (the vendored emulator and
  `harness/`, the pinned toolchain, this repository).
- fwtest 0.6.0's pin: the published image pulled; the firmware at main's
  `1123eca` built in the build container and its suite run on 0.6.0 and
  0.5.0 to compare.
- The flash's pins (HW-85), all allowed sources: single files of the
  pinned JieLi SDK through Gitee's contents API, and its file list through
  Gitee's tree API (a blob-less fetch failed); the AC7911B datasheet,
  found by web search; five FM-1-RE documents re-fetched by raw URL (as
  P-51) and searched for pin names, of which `docs/io/09-storage.md`
  (allowed to the spec side only since this session) was searched for
  pin names alone (P-56). A Python virtual environment with `pypdf` in
  the scratch folder, to read the datasheet's text.
- From the firmware side's open pull requests (#111) it read only
  `docs/SPEC-REQUESTS.md`, through GitHub's contents API.
- The audit's discovery (`tools/audit-discover.py --write`, once):
  repository metadata only, through GitHub's API and `git ls-remote`; no
  target's files, README or page opened.
- M9's plan (docs/M9-PLAN.md): FM-1-RE's `docs/io/11-ota-protocol.md`
  and `docs/io/12-v15-reflash-proof.md` re-fetched by raw URL (as P-51);
  the SDK's `cpu/wl82/tools/note.txt`, and the blob hashes and sizes of
  the SDK's loader and packaging files (none opened) (P-57). Nothing of
  FM1 Open was fetched; its file sizes and hashes come from docs/PLAN.md.
- Spec requests, every 20 minutes from 03:22Z to 11:52Z: only
  `docs/SPEC-REQUESTS.md` on main and on the firmware side's open
  branches (#111, #116 to #126); none new.
- At the end, the firmware side's latest open branches (#124, which
  carries #111 and #116 to #123, and #125) were merged into this
  session's branches; their files were merged, not reviewed. #126 is a
  draft not for merging and was left out.
- #112's CI after that merge failed C-FW-SUITE. From that run's report
  artifact the session opened only `logs/C-FW-SUITE.log`, the artifact's
  listing and `fwtest/fmgold/result.json`, then deleted it at 12:04Z.
  fmgold and fmgold2's `audio.wav` is 256 bytes (128 samples) shorter
  than the golden on fwtest 0.6.0 with M8a's firmware. Main's firmware
  matched it on 0.6.0 earlier in this session. Left to the firmware side.

### Session fwtest-060-and-presets (fwtest 0.6.0's pin, the presets draft's CI)
- Date: 2026-10-25
- Role: firmware side (clean).
- Exposure: none.
- Tool: Claude Code 2.1.310 (banner), unattended (a background session).
- Model ID: `claude-opus-5-5` (Claude Opus 5.5). Published cutoffs: reliable
  knowledge Jun 2026, training data Jun 2026 (PROVENANCE P-4). Flag: none.
- Session: Claude Code session `7572a4b5-269a-4514-bd2e-fd7ae24e79e6`,
  started by a `/clear` at 13:21:03Z (banner `source: clear`,
  `status: OK`). Its own transcript is left for the next clean session to
  archive.
- Where it ran: the owner's Mac, in `~/<top>/clean`.
- Start: the role file says `clean`. `tools/clean-setup.sh` installed
  #110's `clean.json` (banner `status: OK` on it); `tools/clean-update.sh`,
  run from main, found main at `ce58670` and ended "no spec-side files on
  disk or in .git"; `tools/private-terms.local` exists (not opened); lazy
  fetching off (`GIT_NO_LAZY_FETCH=1`). It archived M8a (`93de9c87`) into
  `sessions/clean/`; every other clean session was already archived.
  `tools/check-transcripts.py` PASS. The Mac had 10 GB free.
- Reads: this file, sessions/README.md, docs/HARNESS.md ("The flash
  chip", "Time", "Golden files", "Versions"), docs/DESIGN-NOTES.md and
  docs/M8-PROPOSAL.md (searched for the programs and the presets), and
  this repository's tools, tests, scripts and firmware.
- Later in the session:
  - **Open spec pull request #112, metadata and one named file:** its
    description and file list (names only), and through GitHub's contents
    API `config/fwtest-image` on its branch, for the digest. Nothing
    fetched into `.git`.
  - **fwtest 0.6.0 and 0.5.0** (both images already pulled): the
    firmware suite on 0.6.0, and fmgold, env and the preset suite on both
    (`FWTEST_IMAGE`), to compare; `--flash-log` on fmgold. A scratch git
    worktree of this branch in the session's temporary folder, to build
    main's firmware beside the presets draft's (sparse like this folder:
    no spec-side folder on disk, checked), removed at the end.
  - **CI:** #126's failed run read with `gh run view --log-failed` (the
    log only); no artifact downloaded.
  - **The presets draft's listening set** in `~/<top>/drop/presets/`
    (our own renders, M8b), compared sample for sample with this
    session's renders; not re-rendered (no preset's sound changed).
  - **Disk:** 10 GB free at the start, 9.1 GB at the lowest; `out/`
    cleared between runs; Docker left alone.

### Session ARP (PRESETS stops at the ends; the presets' requirements; the arpeggiator)
- Date: 2026-10-25
- Role: firmware side (clean).
- Exposure: none.
- Tool: Claude Code 2.1.310 (banner), unattended (a background session).
- Model ID: `claude-opus-5-5` (Claude Opus 5.5). Published cutoffs: reliable
  knowledge Jun 2026, training data Jun 2026 (PROVENANCE P-4). Flag: none.
- Session: Claude Code session `cd24c9a8-eea5-478d-999a-cfff4f352a34`,
  started by a `/clear` at 15:03:08Z (banner `source: clear`,
  `status: OK`). Its own transcript is left for the next clean session to
  archive.
- Where it ran: the owner's Mac, in `~/<top>/clean`.
- Start: the role file says `clean`. `tools/clean-update.sh`, run from
  #130's branch, found it at `bbe2da0` and ended "no spec-side files on
  disk or in .git"; `tools/private-terms.local` exists (not opened); lazy
  fetching off (`GIT_NO_LAZY_FETCH=1`). It archived fwtest-060-and-presets
  (`7572a4b5`) into `sessions/clean/`; every other clean session was
  already archived. `tools/check-transcripts.py` PASS. The Mac had 9.1 GB
  free.
- Reads: this file, sessions/README.md, docs/ARP-PROPOSAL.md,
  docs/PATCH-FORMAT.md, docs/STORE-FORMAT.md, docs/HARNESS.md (MIDI in
  and out), docs/HARDWARE-SPEC.md (HW-36, the ARP button),
  docs/DESIGN-NOTES.md and docs/REQUIREMENTS.md (searched), and this
  repository's tools, tests, scripts and firmware.
- **Open spec pull request #128, docs only:** its file list (names only),
  and through GitHub's contents API on its branch at `7322117` four docs:
  docs/ARP-PROPOSAL.md (the owner's answers), docs/HARDWARE-SPEC.md,
  docs/M9-PLAN.md and docs/PLAN.md, into the session's temporary folder.
  Nothing fetched into `.git`.
- Later in the session:
  - **fwtest 0.6.0** (the pinned image, already pulled): the firmware
    suite, and single cases with `tools/fwtest run`.
  - **Two scratch git worktrees** in the session's temporary folder:
    one for the arpeggiator, one for #131's last commit while the suite
    ran here. Both sparse like this folder (no spec-side folder on disk,
    checked). In each, `tools/private-terms.local` was a symbolic link to
    this folder's, so the commit hook checked the terms (never opened).
    Both worktrees and links are removed at the end.
  - **CI:** the runs of #131, #126 and #132 read with `gh run view
    --log` (the logs only). For #132's two C-SEP-TERMS failures, the
    runs' report artifacts' zips were fetched three times in all (the
    first run's twice, the second's once) through GitHub's API into the
    session's temporary folder, and only `logs/C-SEP-TERMS.log` was read
    from it (`unzip -p`, to the terminal; the first time its file list
    was filtered for that name with `grep`, only that line printed;
    nothing else extracted), the zip deleted at once each time. The hits
    were one of our own names in arp.c (found by hashing the flagged
    line's words; renamed, and the name kept out of every text since),
    then that rename's own commit message (reworded and force-pushed to
    #132's and #133's branches, unmerged).
  - **The presets draft's listening set** (`~/<top>/drop/presets/`):
    not re-rendered (no preset's sound changed; the preset suite 64 of
    64 on #126 with #131).
  - **The drop build:** `~/<top>/drop/small-beeps-25497f0.bin` (#132's
    image, built again from its head in the worktree: the same bytes as
    the build the suites ran) and its SHA-256 beside it.
  - **Disk:** 9.1 GB free at the start, 8.3 GB at the lowest; stale
    `out/` folders removed as the session went.

### Session owner-answers-1025 (the owner's answers to the ARP and M9 proposals, MIDI clock in the harness, spec requests)
- Date: 2026-10-25 (UTC)
- Role: **spec side (exposed).** Never writes firmware.
- Tool: Claude Code 2.1.310 (banner).
- Model ID: `claude-opus-5-5` (Claude Opus 5.5). Published cutoffs: reliable
  knowledge Jun 2026, training data Jun 2026 (PROVENANCE P-4). Flag: none.
- Session: Claude Code session `e9c791d0-c0ad-48c5-bdb9-ede17aa9736a`,
  started by `/clear` at 13:23:41Z (banner `source: clear`,
  `status: OK`), with the folder still at `1123eca`, before #110 had
  reached it. The session therefore loaded the old settings
  (`eaa5f875…`), which lack only #110's deny rule against cloning the
  port repository, and keeps them while it runs.
- Where it ran: the owner's Mac, in `~/<top>/spec`; 13:24:11Z:
  `tools/spec-setup.sh` on main at `ce586704`, banner `status: OK`
  (`84a7e56c…`); `tools/private-terms.local` exists (not opened). 11 GB
  free at the start.
- What it archived: evening-1024's transcript (`e7979b06`) into
  `sessions/spec/`. `tools/check-transcripts.py` first failed on it: its
  banner after a compaction (04:32:36Z) reported `CONFIG MISMATCH`, the
  one evening-1024's own entry foresaw (Corrections, below).
  `tools/check-transcripts.py` gained `ALLOWED_MISMATCH`, which allows
  that one banner by its session, source and both hashes, for the owner
  to approve by merging; then PASS (29 archived transcripts).
- Exposure: the spec side's usual material (the vendored emulator and
  `harness/`, the pinned toolchain, this repository).
- Section 2 (ahead of ARP): read `harness/src/` and the vendored
  emulator's MIDI input to check how a script's MIDI bytes queue; added
  a harness test and docs/HARNESS.md's "MIDI clock in and timing" (#129),
  with no change to fwtest; `cargo test --release` in `harness/`.
- Spec requests, every 20 minutes from 13:38Z to 21:43Z: only
  `docs/SPEC-REQUESTS.md` on main and on the firmware side's open
  branches (#126, #130 to #133), through GitHub's contents API, its blob
  hash only; none new. Of those pull requests it also listed the changed
  files' names, to check for conflicts.
- At the end, the firmware side's latest open branch `arp/budgets`
  (#133, which carries #130 to #132) was merged into this session's
  start branch for EXPOSURE.md's conflict; its files were merged, not
  reviewed. Free disk stayed between 7 and 11 GB.

### Session overnight-1025 (the timing goldens' policy, M9's app release, six preset candidates)
- Date: 2026-10-26 (UTC; the evening of 2026-10-25 local time)
- Role: firmware side (clean).
- Exposure: none.
- Tool: Claude Code 2.1.310 (banner), unattended (a background session).
- Model ID: `claude-opus-5-5` (Claude Opus 5.5). Published cutoffs: reliable
  knowledge Jun 2026, training data Jun 2026 (PROVENANCE P-4). Flag: none.
- Session: Claude Code session `4bb588e8-5900-430e-ae7a-c38dea0a337a`,
  started by a `/clear` at 02:27:04Z (banner `source: clear`,
  `status: OK`). Its own transcript is left for the next clean session to
  archive.
- Where it ran: the owner's Mac, in `~/<top>/clean`.
- Start: the role file says `clean`. `tools/clean-update.sh`, run from
  main, found main at `cf07f9e` and ended "no spec-side files on disk or
  in .git"; `tools/clean-setup.sh` then installed `clean.json` (banner
  `status: OK`); `tools/private-terms.local` exists (not opened); lazy
  fetching off (`GIT_NO_LAZY_FETCH=1`). It archived ARP (`cd24c9a8`) into
  `sessions/clean/`; every other clean session was already archived (an
  older live transcript whose file time had changed was compared with its
  archived copy: the same lines). `tools/check-transcripts.py` failed on
  two of ARP's calls (a scratch worktree's sparse checkout, which names
  the spec-side folders only to leave them out); six reviewed entries in
  `sessions/REVIEWED.json`, for the owner's approval; then PASS. The Mac
  had 7.3 GB free.
- Reads: this file, CONTRIBUTING.md, sessions/README.md, docs/PLAN.md,
  docs/M9-PLAN.md, docs/HARNESS.md ("Time", "Outputs", "MIDI output",
  "MIDI clock in and timing", "Golden files", "Suites"), ARP's archived
  transcript (its two flagged calls and its last message, for the
  owner's questions), the m1 release's description and file names
  (`gh release view`), and this repository's tools, tests, scripts,
  workflows and firmware.
- Later in the session:
  - **Open spec pull request #136, docs only:** its description and file
    list (names only), and through GitHub's contents API on its branch at
    `1da34f9` one doc, docs/M9-PLAN.md (the release format 1.0), into the
    session's temporary folder. Nothing fetched into `.git`. The
    session's release tooling follows it. Of #134 and #137 (spec side)
    only their titles and #134's file list (names).
  - **Records, named files only, through GitHub's contents API:** the
    `report.json` of main's `cf07f9e` and of m1's `9fe07f8` (the latter at
    the records commit `a34b3f8`), `logs/C-FW-SUITE.log` of `cf07f9e`
    (searched for fwtest's version: not in it), and a listing of the
    records branch's `records/` folder at `a34b3f8` filtered to m1's entry
    (its tree hash `a9839d5…`, as m1's release notes state). Nothing
    fetched into `.git`.
  - **The m1 release:** its SBOM (`m1-sbom.spdx.json`, our own) downloaded
    into the session's temporary folder, to follow its form.
  - **A dry run of the app release of m1** (`tools/release.sh m1 --version
    0.1.0`, output in the session's temporary folder, nothing published):
    `tools/reproduce`'s export of m1's files (never the spec-side folders;
    git fetched m1's other files one at a time), two builds, fwtest 0.1.0's
    image pulled by digest for its version, then removed. It rebuilt m1's
    image byte for byte (`ee2ad8a0…`).
  - **A scratch git worktree** in the session's temporary folder, of
    `m8b/presets` (#126) for the preset candidates, sparse like this
    folder (the patterns built from `config/spec-side-folders`; no
    spec-side folder on disk, checked), with `tools/private-terms.local`
    a symbolic link to this folder's (never opened); removed at the end.
    And `tools/reproduce --export-only` of #126's head (`c8e2594`) into
    the temporary folder, to build its image as a base (no spec-side
    folder in it, checked).
  - **Merging this session's branches into `m8b/presets`** staged main's
    changes under the spec-side folders since #126's last merge (main's
    spec pull requests): the merge's `git status` showed one such path's
    name; git took them by object ID, lazy fetching off. The barrier
    check of `tools/clean-update.sh` (every branch, the worktree too)
    found no spec-side contents on disk or in `.git` afterwards.
  - **fwtest 0.6.0** (the pinned image): the firmware suite and the ARP
    suite on main's image, on this session's images, and on a test build
    that starts late (`SB_TEST_LATE_START`, at about 0.4 and 0.14 ms).
  - **The presets draft's listening set** (`~/<top>/drop/presets/`):
    the six candidates rendered there (`65-...wav` to `70-...wav`) and
    added to INDEX.md; the 64 others left as they were (their sound's
    hashes unchanged).
  - **Force-pushes:** none (commits amended only before their first
    push).
  - **Disk:** 7.3 GB free at the start, 3.1 GB at the lowest (other
    folders on the Mac grew meanwhile; this session's outputs were
    cleared as it went).

### Session spec-overnight-1025 (the app's USB patch note, M9's single-file release format, spec requests)
- Date: 2026-10-26 (UTC)
- Role: **spec side (exposed).** Never writes firmware.
- Tool: Claude Code 2.1.310 (banner).
- Model ID: `claude-opus-5-5` (Claude Opus 5.5). Published cutoffs: reliable
  knowledge Jun 2026, training data Jun 2026 (PROVENANCE P-4). Flag: none.
- Session: Claude Code session `98ff9a1a-2e3d-4ab8-b9ba-49f89dc695c5`,
  started by `/clear` at 02:27:25Z (banner `source: clear`,
  `status: OK`).
- Where it ran: the owner's Mac, in `~/<top>/spec`; 02:27:36Z:
  `tools/spec-setup.sh` on main at `cf07f9e5`, banner `status: OK`
  (`84a7e56c…`); `tools/private-terms.local` exists (not opened). 7.3 GB
  free at the start.
- What it archived: owner-answers-1025's transcript (`e9c791d0`) into
  `sessions/spec/`; `tools/check-transcripts.py` PASS (32 archived
  transcripts).
- The owner's decisions it records: owner-answers-1025's
  `ALLOWED_MISMATCH` (Corrections, "evening-1024's mismatched banner") is
  approved, by the merge of #127; a script event for a MIDI clock at a
  given BPM is declined, not needed (HARNESS.md's "MIDI clock in and
  timing" stays as written: generate the clock's `midi` lines).
- Exposure: the spec side's usual material (the vendored emulator and
  `harness/`, the pinned toolchain, this repository).
- Section 1 (the app's USB note): read the owner's drop file
  `~/<top>/drop/emulator-patches/usb-port-done.md` only, nothing else in
  that folder; the SDK's file list (Gitee's tree API) and three USB
  headers (Gitee's blobs API) into a scratch folder; FM-1-RE's
  `docs/io/06-usb.md` by raw URL; a GitHub code search of the AC63 SDK for
  `MACK` (P-59). Built the harness's test images with the pinned
  toolchain, a local fwtest image (`harness/ci.sh image`), and the
  firmware at main in a scratch worktree; ran the firmware suite on the
  pinned and the local image (the USB pull request's commit message).
- Section 2 (M9's release format, #136): docs/M9-PLAN.md and the clean
  side's committed prompt on its open branch, to match the fields its
  release tooling expects.
- Section 3 (the watch): docs/SPEC-REQUESTS.md, that file only, on main
  and on each of the clean side's open branches, every 20 minutes from
  02:43Z to 10:44Z (27 checks): unchanged throughout (blob `7ba8c928`), no
  new requests.
- Also read of the clean side's open PRs: their titles and file lists
  (#135, #138, #139, #140), #140's `tools/fm1img.py` (its constants and
  checks, against format 1.0: they match), and, while merging, their
  docs/EXPOSURE.md entry and the files where the branches meet
  (PROVENANCE.md, docs/PLAN.md, docs/REQUIREMENTS.md; no overlap).
- End: the clean side's chain (tip `099b4199`, #140) merged into #134,
  then #134 into #137; one conflict, this file's two new entries, both
  kept. The local fwtest image, the firmware worktree and the suite
  outputs were deleted after use. Disk: 7.3 GB free at the start, 3.5 GB
  at the lowest (other folders on the Mac grew meanwhile), 3.9 GB at the
  end.

### Session spec-a1-fwsc (the owner's answers to spec-overnight-1025, Phase A1: our firmware as a `.fwsc` package)
- Date: 2026-10-27 (UTC)
- Role: **spec side (exposed).** Never writes firmware.
- Tool: Claude Code 2.1.311 (banner).
- Model ID: `claude-opus-5-5` (Claude Opus 5.5). Published cutoffs: reliable
  knowledge Jun 2026, training data Jun 2026 (PROVENANCE P-4). Flag: none.
- Session: Claude Code session `4030c83c-4fbc-479f-8903-779f366fe66d`,
  started by `/clear` at 01:18:21Z (banner `source: clear`,
  `status: OK`).
- Where it ran: the owner's Mac, in `~/<top>/spec`; 01:19:05Z:
  `tools/spec-setup.sh` on main at `90827129`, banner `status: OK`
  (`84a7e56c…`); `tools/private-terms.local` exists (not opened). 2.8 GB
  free at the start.
- What it archived: spec-overnight-1025's transcript (`98ff9a1a`) into
  `sessions/spec/`; `tools/check-transcripts.py` PASS (34 archived
  transcripts).
- Exposure: the spec side's usual material (the vendored emulator and
  `harness/`, the pinned toolchain, this repository). Never opened,
  fetched or searched M-VAVE's stock firmware files or any disassembly of
  them.
- Section 1 (the owner's answers): this repository only; the
  fwtest-image workflow's log for #137's merge (run 40431196083: 0.7.0
  published, its digest).
- Section 2 (Phase A1), what it read:
  - JieLi AC79 SDK (P-2), the pinned commit, through Gitee's tree, blobs
    and raw-file APIs into a scratch folder, not vendored: read
    `cpu/wl82/tools/download.c`, `download_linux.c`,
    `isd_config_rule.c`, `note.txt`, `script.ver`,
    `packufw/source/JLpack.cpp`, `packufw/example/JLpack.bat`,
    `cpu/wl82/sdk_ld_sfc.c` and `include_lib/system/boot.h`; downloaded
    but not read `isd_config_rule_loader.c`, `生成升级固件.bat`,
    `include_lib/update/update_loader_download.h` and
    `doc/stuff/ISD_CONFIG.INI配置文件说明.pdf` (no PDF reader on the Mac).
    The commit's file list (tree API).
  - AL-255/FM-1-RE (P-51), the pinned commit, by raw URL:
    `docs/architecture.md`, `docs/io/01-boot.md`,
    `docs/io/11-ota-protocol.md`, `docs/io/12-v15-reflash-proof.md`,
    `docs/reversing/02-boot-and-runtime.md`. `01-boot.md` quotes
    disassembly of the stock app in places; it is one of the allowed
    documents, and none of its code was used, only its addresses' +0x120
    finding. The current `docs/` and `docs/io/` listings, names only
    (they include its disassembly documents and an OTA loader document,
    none opened).
  - The emulator upstream (P-7), at the pinned commit, by raw URL, new
    spec-side exposure: `web/fwsc.js` (the web build's package reader;
    the same at `master` `a374e75e`) and `web/main.js` (its page), and
    the `web/` listing, names only. The GPL package code that
    `fwsc.js`'s comment names was not opened, nor any other file there.
  - The vendored emulator's package path, and `harness/` (this side's
    usual material).
  - Never opened, fetched or searched: any stock package, FM1 Open's
    files, any disassembly or function database.
- Section 2, what it ran: the harness's tests natively and in the
  container (`harness/ci.sh test`), a local fwtest 0.8.0 image
  (`harness/ci.sh image`) for the suite (`harness/ci.sh suite`), the test
  images rebuilt with the pinned toolchain (`build.sh`, then
  `--check`), the tools' unit tests, `reuse lint` (in `fsfe/reuse:5`).
  The local images and the scratch outputs were deleted after use.
- Disk: 2.8 GB free at the start (above the 2 GB stop), 24 GB once other
  folders on the Mac shrank, 22 GB at the end.

### Session clean-pin-answers (fwtest 0.7.0's pin, the owner's answers to overnight-1025's questions)
- Date: 2026-10-27 (UTC; the evening of 2026-10-26 local time)
- Role: firmware side (clean).
- Exposure: none.
- Tool: Claude Code 2.1.311 (banner), a background session.
- Model ID: `claude-opus-5-5` (Claude Opus 5.5). Published cutoffs: reliable
  knowledge Jun 2026, training data Jun 2026 (PROVENANCE P-4). Flag: none.
- Session: Claude Code session `b46c273c-270e-40c1-b2fc-24573aac19a6`,
  started by a `/clear` at 01:36:15Z (banner `source: clear`,
  `status: OK`). Its own transcript is left for the next clean session to
  archive.
- Where it ran: the owner's Mac, in `~/<top>/clean`.
- Start: the role file says `clean`. `tools/clean-update.sh`, run from
  main, found main at `9082712` and ended "no spec-side files on disk or
  in .git" (it re-runs `tools/clean-setup.sh`, which installed
  `clean.json`); `tools/private-terms.local` exists (not opened); lazy
  fetching off (`GIT_NO_LAZY_FETCH=1`). It archived overnight-1025
  (`4bb588e8`) into `sessions/clean/`; every other clean session was
  already archived (one older live transcript's file time had changed;
  its entries' times end on 2026-10-22, as its archived copy's).
  `tools/check-transcripts.py` failed on five of overnight-1025's calls:
  four name the spec-side folders only as `:!` pathspecs or name the
  emulator app in a doc's text; the fifth is the file list below. Five
  reviewed entries in `sessions/REVIEWED.json`, for the owner's approval;
  then PASS. The Mac had 3.8 GB free.
- **A line overnight-1025's entry lacks** (it said so in its last
  message): late in that session it also printed the changed-file list of
  the spec side's #137 (`gh pr view 137 --json files`, names only). Its
  filter was meant to drop spec-side paths and missed one of the three
  folders, so four of the names printed were of files under a spec-side
  folder (names only; nothing opened or fetched). Its entry above stays
  as written; this line completes it.
- Reads: this file, CONTRIBUTING.md, sessions/README.md,
  sessions/REVIEWED.json, overnight-1025's transcript (its five flagged
  calls and the one call's output, in the archived copy; its last
  message, for the owner's questions, in the original under
  `~/.claude/projects/`, which is the same session unredacted),
  docs/PLAN.md, docs/M9-PLAN.md ("The release format"), docs/HARNESS.md
  (the versions' list), docs/EMULATOR-PARITY.md (0012),
  docs/TOOLCHAIN.md, docs/DESIGN-NOTES.md, docs/RELEASING.md, and this
  repository's tools, tests, workflows and firmware.
- Later in the session:
  - **fwtest 0.7.0's digest:** from the log of the image workflow's run
    on main's `d28ec99` (#137's merge), through `grep`. The first grep
    (for "digest", "0.7.0" or "@sha256") printed 20 lines: the image
    build's lines naming its pinned base images, fwtest's compile line
    and version line, and the first lines of the push step's script;
    the second, the push step's digest only.
  - **fwtest 0.6.0 and 0.7.0** (pinned images, pulled by digest): the
    firmware suite (with the store's cases) and the ARP suite on main's
    image, once on each, outputs in the session's temporary folder and
    under `out/pin-check/` (gitignored; the ARP suite's image and outputs
    must be inside the folder), compared file by file, then deleted. The
    0.6.0 ARP run named its image by `FWTEST_IMAGE`. One `grep -r` over
    this folder for the old pin was denied by Claude Code's permission
    check and never ran; a `git grep` of tracked files, with the
    spec-side folders left out, did the same.
  - **m1's record, a named file only:** `records/9fe07f8…/report.json`
    through GitHub's contents API on the records branch, into the
    temporary folder, for a local dry run of the app release of m1
    (`tools/release.sh m1 --version 0.1.0`, nothing published; the
    record's tree hash given as a stand-in, as a clean folder must give
    it by hand). It rebuilt m1's image byte for byte (`ee2ad8a0…`), and
    the same run with `GITHUB_ACTIONS=true` stopped at the unpinned build
    image, as it should. m1's release notes read for the hash (not in
    them). The dry run pulled fwtest 0.1.0's image (`fa74baf9…`, the one
    m1's record names) by digest, removed afterwards with the session's
    other outputs.
  - **Force-pushes:** none.
  - **Disk:** 3.8 GB free at the start; 23 GB from shortly after (other
    folders on the Mac shrank meanwhile).

### Session spec-answers-a1 (the owner's answers to spec-a1-fwsc's questions, a parity note)
- Date: 2026-10-27 (UTC; the evening of 2026-10-26 local time)
- Role: **spec side (exposed).** Never writes firmware.
- Tool: Claude Code 2.1.311 (banner).
- Model ID: `claude-opus-5-5` (Claude Opus 5.5). Published cutoffs: reliable
  knowledge Jun 2026, training data Jun 2026 (PROVENANCE P-4). Flag: none.
- Session: Claude Code session `6fd5a71c-53d5-4b70-b151-fe03bb59a4cf`,
  started by `/clear` at 03:01:44Z (banner `source: clear`,
  `status: OK`).
- Where it ran: the owner's Mac, in `~/<top>/spec`; the role file says
  `spec`. 03:01:56Z: `tools/spec-setup.sh`, banner `status: OK`
  (`84a7e56c…`); main at `88bc8325` (#141 to #146 merged);
  `tools/private-terms.local` exists (not opened). 20 GB free at the
  start.
- What it archived: spec-a1-fwsc's transcript (`4030c83c`) into
  `sessions/spec/`; `tools/check-transcripts.py` PASS (36 archived
  transcripts).
- Exposure: the spec side's usual material (the vendored emulator and
  `harness/`, the pinned toolchain, this repository). Never opened,
  fetched or searched M-VAVE's stock firmware files or any disassembly of
  them.
- Sections 1 and 2: this repository only (its docs, and spec-a1-fwsc's
  archived transcript for its final questions). No downloads, no other
  source opened; nothing run but the repository's checks
  (`check-transcripts`, `check-emulator-terms`, `check-private`).
- Disk: 20 GB free at the start and at the end.

### Session clean-a1-packager (fwtest 0.8.0's pin, the build's identity, Phase A1's `.fwsc` packager)
- Date: 2026-10-27 (UTC; the evening of 2026-10-26 local time)
- Role: firmware side (clean).
- Exposure: none.
- Tool: Claude Code 2.1.311 (banner), a background session.
- Model ID: `claude-opus-5-5` (Claude Opus 5.5). Published cutoffs: reliable
  knowledge Jun 2026, training data Jun 2026 (PROVENANCE P-4). Flag: none.
- Session: Claude Code session `581bd4e1-c017-41a5-9331-a48f0fdcfc90`,
  started by a `/clear` at 03:01:26Z (banner `source: clear`,
  `status: OK`). Its own transcript is left for the next clean session to
  archive.
- Where it ran: the owner's Mac, in `~/<top>/clean`.
- Start: the role file says `clean`. `tools/clean-update.sh`, run from
  main, found main at `88bc832` (#146's merge) and ended "no spec-side
  files on disk or in .git"; `tools/private-terms.local` exists (not
  opened); lazy fetching off (`GIT_NO_LAZY_FETCH=1`). It archived
  clean-pin-answers (`b46c273c`) into `sessions/clean/`; every other
  clean session was already archived (M0d's live transcript's file time
  had changed again; its entries end on 2026-10-22, as its archived
  copy's). `tools/check-transcripts.py` failed on three of
  clean-pin-answers' calls, each naming the spec-side folders only as
  `:!` pathspecs that leave them out of a `git log` or `git show --stat`;
  three reviewed entries in `sessions/REVIEWED.json`, for the owner's
  approval; then PASS. The Mac had 20 GB free.
- **The owner's answer 2** (this session's prompt): overnight-1025's
  names-only listing of #137's changed files is approved and recorded as
  it is, a real names-only listing (clean-pin-answers' entry above and its
  `REVIEWED.json` entry), not a false positive. Neither is changed.
- Reads: this file, CONTRIBUTING.md, sessions/README.md,
  sessions/REVIEWED.json, clean-pin-answers' three flagged calls (in the
  archived copy), docs/A1-PLAN.md, docs/HARDWARE-SPEC.md section 21
  (HW-87 to HW-93), docs/HARNESS.md ("Running it", "The raw image",
  "Packages", "Versions"), docs/RELEASING.md, docs/TOOLCHAIN.md,
  docs/M9-PLAN.md ("The release format"), docs/REQUIREMENTS.md,
  PROVENANCE.md, four docs on the spec side's open #148 (`docs/A1-PLAN.md`,
  `docs/HARNESS.md`, `docs/REQUIREMENTS.md`, `docs/M9-PLAN.md`, by name
  through GitHub's contents API, diffed against main; they change no
  fact this session uses), and this repository's tools, tests, workflows and
  firmware.
- Later in the session:
  - **fwtest 0.8.0's digest:** from the log of the image workflow's run
    on main's `ecd9fb8` (#143's merge), through `grep -o` for the
    published reference and fwtest's version only. The run on `fc62b76`
    (#142's merge) was read the same way: it pushed a 0.7.0 image of
    another digest (`26102ae9…`) than the pinned `d7804526…`.
  - **fwtest 0.7.0 and 0.8.0** (pinned images, pulled by digest): the
    firmware suite (with the store's cases) and the ARP suite on main's
    image, once on each, outputs under `out/pin-check/` (gitignored),
    compared file by file, then deleted. The first 0.7.0 firmware run
    is void: the session changed branches while it was still building
    its test images, so some were built from this session's A1
    `tools/build.sh`. Two failed: test-storebusy (a shell syntax error,
    the script replaced while it was read) and test-storewipe (the A1
    RAM check, since narrowed to the firmware build). It was run again
    on an untouched tree.
  - **The spec side's open pull requests:** `gh pr view 147/148/149
    --json files`, filtered by `jq` to paths under `docs/` and `config/`
    and PROVENANCE.md only, so nothing else was printed; then the four
    docs named above, by name.
  - **A1:** the package link prototyped in a scratch copy of `firmware/`,
    `vendor/jieli-sdk/` and the build script in the session's temporary
    folder, then built here. fwtest 0.8.0 run on our packages and on
    broken ones (P-62), outputs under `out/` (gitignored).
  - **m1's record, a named file only:** `records/9fe07f8…/report.json`
    through GitHub's contents API on the records branch, into the
    temporary folder, for the local dry run of m1
    (`tools/release.sh m1 --version 0.1.0`, main's tools, nothing
    published; the record's tree hash given as 64 zeros, a stand-in, as
    a clean folder must give it by hand). It rebuilt m1's image byte for
    byte (`ee2ad8a0…`) and pulled fwtest 0.1.0's image by digest. The
    `.fm1img` (`355208eb…`) copied to `~/<top>/drop/releases/`. The same
    run on the identity branch with `GITHUB_ACTIONS=true` checked the
    identity and built the image fresh (its release deleted); with the
    Dockerfile hash changed by one digit it stopped before building.
  - **`drop/releases/stand-in.fm1img`:** tested by name with `test -f`
    (the folder not listed), then `tools/fm1img.py` on it; only its
    reader's one-line result printed.
  - **A blocked command:** while resolving a merge of main into
    `a1/start`, an `ls` of the spec-side transcript folder was sent
    together with a `grep` of docs/EXPOSURE.md. Claude Code's deny rule
    blocked it and it never ran; nothing under the folder was listed or
    opened. The merge itself staged #147's new spec-side transcript by
    name (`git status` printed its two file names); its contents were
    never on disk or in `.git` (the barrier check after the merge: 0).
  - **Pushing:** the first pushes stopped with "could not fetch … from
    promisor remote": git checked a branch tip GitHub advertised that this
    folder had not fetched, and lazy fetching is off. A plain
    `GIT_NO_LAZY_FETCH=1 git fetch -q origin` fixed it; the barrier check
    after it found no spec-side file in `.git`. Looking for the object
    first, `git ls-tree -r` over main's last 20 commits and `git rev-list
    --objects --all --missing=allow-any` walked trees that include
    spec-side paths, each piped straight into a `grep` for the one hash
    (they printed nothing). How clean-pin-answers pushed was read from
    its archived transcript with `git show a1/start:…` (its push
    commands only).
  - **#153's C-SEP-TERMS failure:** read first from `gh run view --log`
    (result lines only), then one named file of the CI report artifact:
    its zip fetched by GitHub's API into the temporary folder,
    `unzip -p … logs/C-SEP-TERMS.log` (nothing else extracted), the zip
    deleted at once. The log gives places and hashes only; the four
    words, all names this session chose, were found by hashing the
    flagged lines' own words, and renamed. The log copy was deleted.
  - **Force-pushes:** none.
  - **Disk:** 20 GB free at the start; 19 GB at the lowest.

### Session clean-1027 (the owner's answers to clean-a1-packager's questions, seams for firmwares built on small-beeps, M8b)
- Date: 2026-10-27 (UTC; the evening of 2026-10-27 local time)
- Role: firmware side (clean).
- Exposure: none.
- Tool: Claude Code 2.1.312 (banner), a background session.
- Model ID: `claude-opus-5-5` (Claude Opus 5.5). Published cutoffs: reliable
  knowledge Jun 2026, training data Jun 2026 (PROVENANCE P-4). Flag: none.
- Session: Claude Code session `f63e5c6c-e5b4-4ee8-a042-a302bc13f665`,
  started by a `/clear` at 23:41:56Z (banner `source: clear`,
  `status: OK`). Its own transcript is left for the next clean session to
  archive.
- Where it ran: the owner's Mac, in `~/<top>/clean`.
- Start: the role file says `clean`. `tools/clean-update.sh`, run from
  main, found main at `fd07f7f` (#153's merge) and ended "no spec-side
  files on disk or in .git"; `tools/private-terms.local` exists (not
  opened); lazy fetching off (`GIT_NO_LAZY_FETCH=1`). It archived
  clean-a1-packager (`581bd4e1`) into `sessions/clean/`; every other
  clean session was already archived. `tools/check-transcripts.py` failed
  on three of clean-a1-packager's calls: a `git show --stat` naming the
  spec-side folders only as `:!` exclusions, #153's `gh pr create` (its
  body names the F-Emulator app), and the blocked `ls` (below). Three
  reviewed entries in `sessions/REVIEWED.json`; then PASS. The Mac had
  14 GB free.
- **The owner's answer 1** (this session's prompt): clean-a1-packager's
  blocked `ls` is recorded as a reviewed entry that says what happened:
  an attempt, denied by the settings, never ran, nothing listed. Approved.
- A spec session works at the same time; this session opens none of its
  branches.
- Reads: this file, CONTRIBUTING.md, sessions/README.md,
  sessions/REVIEWED.json, clean-a1-packager's three flagged calls (in the
  archived copy, by tool-call ID), docs/HARNESS.md ("Running it", "The
  flash chip", "The command line", "Input scripts", "Outputs", "MIDI
  output", "Outcomes and exit codes", "Instructions", "Golden files"),
  docs/STORE-FORMAT.md, docs/TOOLCHAIN.md, docs/RELEASING.md ("Loading
  one into the app"), docs/DESIGN-NOTES.md and docs/REQUIREMENTS.md (the
  parts these changes touch), docs/PLAN.md and docs/M8-PROPOSAL.md (a
  search for the presets' wording), README.md, `audit/audit.json`, #126's
  description, and this repository's firmware, tools and tests. Nothing
  fetched from outside the repository but the build image's own
  downloads.
- Later in the session:
  - **The `.fwsc` for the app (the owner's answer 4):** a fresh build of
    main (`fd07f7f`; `app.bin` `7c41f08a…`, #153's), its package link
    packed as the CI package suite packs it (identity
    `small-beeps-0.0.0`), checked with `tools/fwsc.py`, copied to
    `~/<top>/drop/releases/small-beeps-dev.fwsc` (`27d1d60e…`) with
    `small-beeps-dev.fwsc.sha256` beside it. No CI artifact fetched.
    The drop folder was not listed.
  - **#126 (M8b):** main taken in (two conflicts, both sides kept), the
    presets' text says all 70 stay, made ready for review.
  - **The seams (section 2):** #158 to #161 and #163 to #168. fwtest
    0.8.0 (the pinned image) ran the seams suite's cases, the firmware,
    ARP, package and preset suites, the release selftest and the Plaits
    bench, from copies of the working tree in the session's temporary
    folder (so a branch change could not reach a running suite). One
    firmware suite run was ended by the host (SIGTERM) part way and run
    again alone.
  - **One golden changed by hand** (#163): midiout's capture, the
    chord's order after BR-3's later start; said so in its commit and in
    DESIGN-NOTES.
  - **CI failures, fixed:** a comment that broke a unit test's reading
    of `tools/build.sh` (#160), and the ID `R-CORE1-1`, renamed
    `R-CORE-1` (#163), each merged forward through the later branches,
    read from the CI log's result lines and by running the unit tests
    here; then on #168 C-SEP-TERMS (an 8-digit hex number in
    `tools/seams_suite.py`, found by hashing the flagged line's words)
    and C-ARP (the timing policy's end check on sixteen runs, after
    BR-9's later start), fixed in #167. For those two, two named files
    of the run's report artifact: its zip fetched by GitHub's API into
    the session's temporary folder, `unzip -p` of `logs/C-SEP-TERMS.log`
    and `logs/C-ARP.log` only (nothing else extracted), the zip deleted
    at once; the copies deleted at the end.
  - **Rebases:** BR-4 to the guide, before any of them was pushed, onto
    BR-3's golden commit. **Force-pushes:** none.
  - **GitHub:** `gh pr create`, `edit`, `ready`, `checks`, `view` of this
    session's pull requests and #126; `gh run list` and `gh run view`
    (result lines) of their CI runs; `gh api` for the one report
    artifact above. `gh pr list` twice (numbers, titles or branch names
    only), which showed the spec side's open #155 to #157 and #162. Of
    those four, `gh pr view --json files` filtered by `jq` to eleven
    shared file names this session's pull requests change (README.md,
    docs/EXPOSURE.md, docs/REQUIREMENTS.md, docs/DESIGN-NOTES.md,
    docs/STORE-FORMAT.md, docs/HARNESS.md, PROVENANCE.md,
    sessions/REVIEWED.json, tools/build.sh, tools/record.py,
    tools/store.py), to predict merge conflicts: file names only, nothing
    else printed. No spec-side branch was fetched or opened.
  - **Disk:** 14 GB free at the start; 8.5 GB at the lowest.

### Session spec-1027 (the app's answers, clean's two questions, SR-10, Phase B candidates)
- Date: 2026-10-27 (UTC; the evening of 2026-10-27 local time)
- Role: **spec side (exposed).** Never writes firmware.
- Tool: Claude Code 2.1.312 (banner).
- Model ID: `claude-opus-5-5` (Claude Opus 5.5). Published cutoffs: reliable
  knowledge Jun 2026, training data Jun 2026 (PROVENANCE P-4). Flag: none.
- Session: Claude Code session `541eb13f-b668-464e-8c3f-1afa1d12dab8`,
  started by `/clear` at 23:42:28Z (banner `source: clear`,
  `status: OK`).
- Where it ran: the owner's Mac, in `~/<top>/spec`; the role file says
  `spec`. 23:43:03Z: `tools/spec-setup.sh`, banner `status: OK`
  (`84a7e56c…`); main at `fd07f7f5` (#147 to #153 merged);
  `tools/private-terms.local` exists (not opened). 14 GB free at the
  start.
- What it archived: spec-answers-a1's transcript (`6fd5a71c`) into
  `sessions/spec/`; `tools/check-transcripts.py` PASS (38 archived
  transcripts).
- Exposure: the spec side's usual material (the vendored emulator and
  `harness/`, the pinned toolchain, this repository). Never opened,
  fetched or searched M-VAVE's stock firmware files or any disassembly of
  them.
- Sections 1, 2, 3.1 and 5: this repository only (its docs, spec-answers-a1's
  archived transcript for its final questions). The app's answers are the
  owner's relay; the app's branch was not opened. M-Flasher, M-Bootloader
  and jl-uboot-tool: names only, as the prompt gives them; nothing of them
  fetched, opened or searched.
- Section 3.2 (the two 0.7.0 images): GHCR's public registry API for this
  repository's package (an anonymous pull token): the manifests of
  `d7804526…` and `26102ae9…`, their two configs and their five new
  layers each, into the scratch folder; the layers' tar listings and file
  hashes compared, then the blobs deleted. The fwtest-image workflow's two
  runs' logs (`gh run view --log`, the build and push lines). BuildKit
  options tried on throwaway images of a one-line Dockerfile of our own.
  This PR's own CI report artifact: one log, `logs/C-HARNESS-IMAGE-REPRO.log`
  (`unzip -p`, the zip deleted at once).
- Section 4 (SR-10): the pinned toolchain in the build container
  (assembler, disassembler, compiler on C of our own; PROVENANCE P-63);
  the vendored emulator's store paths (`vendor/emulator/`), patched as
  0013; the upstream emulator fetched by `tools/fetch-emulator.sh --fetch`
  (its sparse checkout of the three crates) to show the patches apply.
  The JieLi SDK (Apache-2.0) at `5fa84a9b`: its file tree through Gitee's
  tree API (names), and the C and header files under `cpu/wl82/`,
  `include_lib/driver/cpu/wl82/` and `include_lib/system/` by raw URL into
  the scratch folder (128 of 189 arrived; the rest timed out), searched
  for inline assembly and the form (none); its
  prebuilt libraries not opened or disassembled. main's firmware built
  (`tools/build.sh build`) and its disassembly scanned. No downloads of
  any other kind.
- The firmware suite run twice (pinned 0.8.0, local 0.9.0) from a separate
  worktree of main (`fd07f7f5`), in the scratch folder, removed after.
  A first pair of runs from this checkout was discarded: branches were
  switched under it.
- Clean's open pull requests: their file lists and the lines they add to
  the shared files (PROVENANCE.md, REQUIREMENTS.md, SPEC-REQUESTS.md),
  read to keep IDs apart and to merge; their firmware changes not read.
- Disk: 14 GB free at the start; 9.4 GB at the lowest.

### Session clean-1028 (pin fwtest 0.9.0, BR-12 power-cut-safe saves, BR-11 per-folder flags, a hardware-phase note)
- Date: 2026-10-28 (UTC; the morning of 2026-10-28 local time)
- Role: firmware side (clean).
- Exposure: none.
- Tool: Claude Code 2.1.312 (banner), a background session.
- Model ID: `claude-opus-5-5` (Claude Opus 5.5). Published cutoffs: reliable
  knowledge Jun 2026, training data Jun 2026 (PROVENANCE P-4). Flag: none.
- Session: Claude Code session `f7d5db1b-d10a-40b3-be14-82c18d108c60`,
  started by a `/clear` at 15:56:06Z (banner `source: clear`,
  `status: OK`). Its own transcript is left for the next clean session to
  archive.
- Where it ran: the owner's Mac, in `~/<top>/clean`.
- Start: the role file says `clean`. `tools/clean-update.sh`, run from
  main, found main at `f9a9bc64` (#162's merge; #155 to #168 merged) and
  ended "no spec-side files on disk or in .git"; `tools/private-terms.local`
  exists (not opened); lazy fetching off (`GIT_NO_LAZY_FETCH=1`). It
  archived clean-1027 (`f63e5c6c`) into `sessions/clean/`; every other
  clean session was already archived. `tools/check-transcripts.py`: 22
  archived transcripts, PASS; clean-1027's only marks were three
  report-only mentions, so no reviewed entries were added. The Mac had
  7 GB free.
- A spec session may work at the same time; this session opens none of its
  branches.
- Reads: this file, sessions/README.md, docs/STORE-FORMAT.md,
  docs/HARNESS.md ("The flash chip", the outputs, the command line,
  "When fwtest treats core 0 as waiting"),
  docs/HARDWARE-SPEC.md (HW-67, for PLAN.md's USB MIDI note),
  docs/DESIGN-NOTES.md, docs/REQUIREMENTS.md and docs/PLAN.md (the parts
  these changes touch), docs/BUILDING-ON-SMALL-BEEPS.md, #152's
  description (as a model), and this repository's firmware, tools and
  tests. Nothing fetched from outside the repository but the build
  image's and fwtest's own downloads.
- GitHub: the image workflow's runs listed; of the runs on `c298dcf9`
  and `f9a9bc64`, the logs read through a filter that printed only the
  pushed digest and fwtest's version lines; open pull requests listed
  with their file lists (none open); #126 and #154's state; #152's
  description; #169, #170 and #171 opened. No CI artifact fetched.
- **#169 (the pin, fwtest 0.9.0):** the firmware, ARP and seams suites on
  main's image on 0.8.0 and 0.9.0, from copies of the tree in the job's
  temporary folder, one suite at a time: all PASS on both, outputs the
  same but for fwtest's version and the runner (and the copies' paths in
  the seams suite's build logs). A first ARP run and a seams run were
  void (their outputs outside the copy, which tools/fwtest refuses) and
  run again. PLAN.md's USB MIDI note (BR-10) rides on it.
- **#170 (BR-12) and #171 (BR-11):** C-UNIT, the firmware suite, the ARP
  suite, the seams suite (with the new cases powercut and flags: 624
  power cuts over four saves, the fourth added after the session's
  review: a rewrite whose old parts the ring copies forward) and perf,
  from copies; the store's space
  figures from tools/store.py's model over random histories. The flags
  case failed once (the container looked the options up by another
  name), was fixed, and passed.
- **#170's first CI run failed C-PERF-PROBES** (read from the run's log
  through a filter printing only its checks' result lines, as before for
  the image runs): the big probe's start-up no longer over the limit.
  Run here, a probe rerun into an output folder already used read its
  first runs' results (perf.py doesn't clear one), which looked like
  the fix not working, until run into a new folder; fixed in #170 (the
  probe's work done 64 times) and merged forward into #171.
- Force-pushes: none (the branches were rebased locally before their
  first push).
- Disk: 7 GB free at the start; 5 GB at the lowest.

### Session clean-store-region (each firmware chooses its own store region, BR-13's write-back check)
- Date: 2026-10-28 (UTC; the afternoon and evening of 2026-10-28 local time)
- Role: firmware side (clean).
- Exposure: none.
- Tool: Claude Code 2.1.312 (banner), a background session.
- Model ID: `claude-opus-5-5` (Claude Opus 5.5). Published cutoffs: reliable
  knowledge Jun 2026, training data Jun 2026 (PROVENANCE P-4). Flag: none.
- Session: Claude Code session `264a9b42-e7d0-4570-86ec-6938ca430c38`,
  started by a `/clear` at 20:56:55Z (banner `source: clear`,
  `status: OK`). Its own transcript is left for the next clean session to
  archive.
- Where it ran: the owner's Mac, in `~/<top>/clean`.
- Start: the role file says `clean`. `tools/clean-update.sh`, run from
  main, found main at `e90f07c4` (#171's merge; #169 to #171 merged) and
  ended "no spec-side files on disk or in .git";
  `tools/private-terms.local` exists (not opened); lazy fetching off
  (`GIT_NO_LAZY_FETCH=1`). It archived clean-1028 (`f7d5db1b`) into
  `sessions/clean/`; every other clean session was already archived.
  `tools/check-transcripts.py`: 23 archived transcripts, PASS; clean-1028's
  marks were report-only mentions, so no reviewed entries were added. The
  Mac had 6.1 GB free.
- A spec session works at the same time; this session opens none of its
  branches.
- Reads: this file, docs/HARDWARE-SPEC.md (HW-80, HW-87 to HW-94, for
  where the app area ends), docs/SPEC-REQUESTS.md (its rules, SR-10 as a
  model), docs/STORE-FORMAT.md, docs/DESIGN-NOTES.md, docs/REQUIREMENTS.md
  and docs/BUILDING-ON-SMALL-BEEPS.md (the parts these changes touch),
  #171's description (as a model), and this repository's firmware, tools
  and tests. Nothing fetched from outside the repository.
- GitHub: open pull requests listed with their file lists (none open,
  twice: before numbering SR-11 and before pushing); #171's description;
  this session's pull requests opened. No CI artifact or log fetched.
- Toolchain probes, in the build image from the job's temporary folder:
  the disassembler on a float-heavy test object with and without the CPU
  options (BR-13), every float add, subtract, multiply and divide form
  assembled and read both ways, one vendored Plaits object compiled as the
  hardware-float build compiles it and read both ways; ld 2.26's
  `DEFINED()` with a symbol set before an `INCLUDE`; clang's `-###` for
  each flag form.

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

### 2026-10-25: M8a's disk figures
*Written by session fwtest-060-and-presets. The entry is left as written.*

- **What was stated.** Session M8a's entry says "3.1 GB free at the
  start, 2.3 to 2.4 GB through the day".
- **What it was.** Free disk went down to 1.9 GB (the owner's
  correction), below the 2 GB at which a session is to stop its work.

### 2026-10-25: evening-1024's mismatched banner
*Written by session owner-answers-1025.*

- **What happened.** Session evening-1024 installed `config/claude/spec.json`
  (`eaa5f875…`) at its start, then added a deny rule to it (#110,
  `84a7e56c…`: `Bash(git clone*small-beeps-ports*)`, the only change).
  At 04:32:36Z, after a compaction, its banner (`source: compact`)
  compared the running settings with the changed file and reported
  `status: CONFIG MISMATCH`, saying to stop and tell the owner. The
  session went on working and did not mention it; its entry above
  foresaw the mismatch, but not this banner.
- **What it means.** The settings in force were the older, looser ones:
  every deny rule but the new one held. Nothing in its transcript clones
  the port repository (`tools/check-transcripts.py` PASS).
- **What changed.** `tools/check-transcripts.py`'s `ALLOWED_MISMATCH`
  allows this one banner, by its session, `source`, settings hash and
  config hash, all four exactly; any other mismatch still fails.

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
| 2026-10-25T02:13:03Z (session start, `/clear`) | `~/<top>/spec` | `eaa5f875…ed542f810` | Session evening-1024 starts; banner `status: OK`. 02:13:28Z: `tools/spec-setup.sh`, banner `status: OK`; day-1024's transcript archived into `sessions/spec/`; `tools/check-transcripts.py` PASS; this entry written. `config/claude/spec.json` changes in this session (a deny rule added); the running session keeps the old settings, so its banner would show a mismatch until it restarts |
| 2026-10-25T04:32:36Z | `~/<top>/spec` | `eaa5f875…ed542f810` | Session evening-1024, after a compaction: banner `status: CONFIG MISMATCH` (the running settings against #110's `config/claude/spec.json`, `84a7e56c…`); recorded by session owner-answers-1025 (Corrections) |
| 2026-10-25T13:23:41Z (session start, `/clear`) | `~/<top>/spec` | `eaa5f875…ed542f810` | Session owner-answers-1025 starts; banner `status: OK` (the folder still at `1123eca`). 13:24:11Z: `tools/spec-setup.sh` on main at `ce586704`, banner `status: OK` (`84a7e56c…f947bc`); evening-1024's transcript archived into `sessions/spec/`; `tools/check-transcripts.py` PASS with `ALLOWED_MISMATCH`; this entry written. The running session keeps the old settings |

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
