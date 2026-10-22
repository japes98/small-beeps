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

## Barrier log

| When (UTC) | Folder | Settings SHA-256 | Event |
|------------|--------|------------------|-------|
| 2026-10-22T02:33:04Z (session start; 2026-10-21 local time) | `~/Development/F-Irmware/clean` | `a557bd84…bf29b32` | Hand-made settings, owner-made before `git init` |
| 2026-10-22T03:41:31Z | same | `6240e19a…9f639156` | `tools/clean-setup.sh` installed `config/claude/clean.json` (same ten deny rules plus the banner hook); role file `clean` |
| 2026-10-22T03:41:42Z | same | `6240e19a…9f639156` | Banner tested by hand: `status: OK`. The live file was then changed by one appended space for about a second to test `CONFIG MISMATCH` (seen), and restored from a copy (hash re-checked: `6240e19a…`). No deny rule changed. |

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
