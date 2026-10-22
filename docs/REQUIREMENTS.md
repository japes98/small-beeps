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
| R-PROC-2 | main changes only through pull requests that passed CI and were merged with a merge commit signed by the owner. No force pushes or deletion on main and `records`; `m*` tags are never moved or deleted. | M0a | rulesets (CONTRIBUTING.md); C-MERGE (records workflow) |
| R-PROC-3 | Each milestone's prompt is committed unedited in `docs/prompts/` in the commit that starts the milestone. | M0a | review |
| R-PROC-4 | Every check names the requirements it checks, and every record has a traceability table. | M0a | C-UNIT |
| R-REC-1 | Each commit pushed to main gets a permanent record `records/<sha>/` (report.json, report.md, logs) on the orphan `records` branch, written only by the records workflow, never for pull requests. | M0a | records.yml; C-UNIT (record writer) |
| R-REC-2 | Each record has an OpenTimestamps proof. Upgraded proofs are added as new files and never replace the originals. | M0a | records.yml, ots-upgrade.yml |
| R-REPRO-1 | The toolchain is downloaded and checked against the SHA-256 in docs/TOOLCHAIN.md. It is never committed or published. | M0a | C-IMAGE, C-NO-TOOLCHAIN |
| R-REPRO-2 | The build container's base image is pinned by digest, its packages come from a pinned snapshot.debian.org date, and builds run under `linux/amd64` through `tools/build.sh`. | M0a | C-IMAGE |
| R-REPRO-3 | Builds are deterministic: two builds in fresh containers, with the source mounted at different paths, are byte-identical. | M0a | C-BUILD-A, C-BUILD-B, C-DETERMINISM |
| R-REPRO-4 | `tools/reproduce <commit>` rebuilds that commit in the pinned container and compares its output hashes with the commit's record. | M0a | review (run by hand; result in the PR) |
| R-REPRO-5 | Vendored SDK files match the SHA-256s listed for the pinned SDK commit. | M0a | C-SDK-PIN |
| R-BUILD-1 | Firmware is freestanding C11 (`-std=c11 -ffreestanding -nostdlib`). It never links the toolchain's C library or prebuilt SDK libraries. | M0a | C-BUILD-A |
| R-LIC-1 | Every file has SPDX licence and copyright information (`reuse lint` passes). | M0a | C-REUSE |
| R-LIC-2 | Vendored files keep their licences and notices. NOTICE carries the SDK's Apache-2.0 notice. Only SDK headers are vendored, never prebuilt libraries. | M0a | C-REUSE, C-SDK-PIN |
| R-PUB-1 | Low profile: the repo's name, description and topics, and the README, contain none of the quiet words (CONTRIBUTING.md). The description is exactly "Embedded audio experiments.", there are no topics, and the README opens with "Embedded audio experiments. Work in progress." | M0a | C-LOW-PROFILE |
| R-PUB-2 | No secrets (tokens, private keys) in tracked files. | M0a | C-SECRETS |
| R-CLEAN-1 | Firmware side never opens, fetches, searches or quotes forbidden material (CONTRIBUTING.md, "Clean-room rules"). | M0a | C-TRANSCRIPTS |
| R-CLEAN-2 | docs/EXPOSURE.md has an entry for every person and session that worked on the project, with role, exposure and (for agents) the exact model ID and its training cutoff. | M0a | review |
| R-CLEAN-3 | Every session's transcript is archived (secrets redacted, redactions noted) in `sessions/`, and every clean-side transcript's reads, searches and fetches are listed and checked. | M0a | C-TRANSCRIPTS |
| R-CLEAN-4 | The deny lists in `config/claude/clean.json` and `config/claude/spec.json` never drop an entry. | M0a | C-DENY-LISTS |
| R-CLEAN-5 | Every archived session after M0a shows the SessionStart banner with matching settings, and never CONFIG MISMATCH. | M0a | C-TRANSCRIPTS |
| R-BOOT-1 | The firmware boots in the emulator to `main` and writes a marker word. | M0d | planned (fwtest) |
| R-BOOT-2 | The firmware keeps a heartbeat visible through the harness. | M0d | planned (fwtest) |
| R-AUDIT-1 | A similarity audit compares our firmware with the GPL firmwares and publishes scores and file names only. | M0e | planned |
| R-PERF-1 | Code size and RAM use are recorded for every commit and kept within per-milestone budgets. | M0e | planned |
| R-PERF-2 | Emulated instructions per audio block may not regress by more than 3%. | M0e | planned |
