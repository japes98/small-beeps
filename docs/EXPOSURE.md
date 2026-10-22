<!--
SPDX-License-Identifier: MIT
SPDX-FileCopyrightText: 2026 japes98
-->

# Exposure register

This is the record a clean-room claim rests on: who, or which session, saw
what, and when. Roles are defined in CONTRIBUTING.md.

- **Spec side (exposed):** may have seen the emulator's source (whose chip
  model was partly written from the GPL Felucca firmware's hardware layer)
  or other material on the forbidden list. Writes the harness and
  `HARDWARE-SPEC.md`. Never writes firmware.
- **Firmware side (clean):** has seen none of the forbidden material. Writes
  the firmware.

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
  `~/Development/F-Irmware/clean`. The prompt said "~/work/small-beeps/clean
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
  `~/Development/F-Irmware/spec`. The prompt said "~/work/small-beeps/spec
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

## Barrier log

| When (UTC) | Folder | Settings SHA-256 | Event |
|------------|--------|------------------|-------|
| 2026-10-22T02:33:04Z (session start; 2026-10-21 local time) | `~/Development/F-Irmware/clean` | `a557bd84…bf29b32` | Hand-made settings, owner-made before `git init` |
| 2026-10-22T03:41:31Z | same | `6240e19a…9f639156` | `tools/clean-setup.sh` installed `config/claude/clean.json` (same ten deny rules plus the banner hook); role file `clean` |
| 2026-10-22T03:41:42Z | same | `6240e19a…9f639156` | Banner tested by hand: `status: OK`. The live file was then changed by one appended space for about a second to test `CONFIG MISMATCH` (seen), and restored from a copy (hash re-checked: `6240e19a…`). No deny rule changed. |
| 2026-10-22T04:10:18Z (session start) | `~/Development/F-Irmware/spec` | `daa6c52d…ce27d` | Session M0b starts under the owner's hand-made spec settings, no banner hook |
| 2026-10-22T04:10:57Z | same | `daa6c52d…ce27d` | `git init`, fetch and checkout of `main`; hand-made file hashed and copied |
| 2026-10-22T04:11:17Z | same | `eaa5f875…ed542f810` | `tools/spec-setup.sh` installed `config/claude/spec.json` (same seven deny rules plus the banner hook); role file `spec`; banner printed `status: OK` |
| 2026-10-22T04:11Z to 04:20Z | same (upstream copy in the session's scratch folder) | `eaa5f875…ed542f810` | Blob-less, sparse clone of the upstream emulator (three crates, licence, workspace manifest; commit `43ed5580`), read to plan the harness |
| 2026-10-22T04:21Z | same | `eaa5f875…ed542f810` | M0a's two transcripts archived into `sessions/clean/`; `tools/check-transcripts.py` PASS; this entry written |

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
