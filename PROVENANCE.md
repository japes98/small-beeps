<!--
SPDX-License-Identifier: MIT
SPDX-FileCopyrightText: 2026 japes98
-->

# Provenance

Every outside source the firmware side uses is logged here: an ID, the
source, what was learned, and where it was used. Commit messages name these
IDs in their `Sources:` field. Allowed sources are listed in CONTRIBUTING.md
("Clean-room rules"); anything else needs the owner's approval first.

| ID | Date | Session | Source | What was learned or taken | Used in |
|----|------|---------|--------|---------------------------|---------|
| P-1 | 2026-10-21 | M0a | JieLi Linux toolchain `jieli-linux-toolchains-20250324.1.tar.xz`, short link `https://pkgman.jieliapp.com/s/linux-toolchain` (now redirects to 20260730.1), direct URL `https://jl-update.oss-cn-shenzhen.aliyuncs.com/jieli-linux-toolchains-20250324.1.tar.xz`. SHA-256 `f686586bcfb45e0f0bb27fd2b39c7a7f313cb4f0e88a66a14da621ffa8225958` | The archive layout (`common/`, `pi32/`, `pi32v2/`, `q32s/`), its README's usage notes, and the tool versions (clang 4.0.1, GNU ld 2.26.51). `clang -target pi32v2` produces ELF32-pi32v2. No licence or terms file inside. | tools/Dockerfile, tools/build.sh, docs/TOOLCHAIN.md |
| P-2 | 2026-10-21 | M0a | JieLi AC79 SDK, `https://gitee.com/Jieli-Tech/fw-AC79_AIoT_SDK`, branch `release/AC79NN_SDK_V1.2.0`, commit `5fa84a9b2f723a5e9337ad79dc2ad741fc98fe2d` ("AC79NN_SDK_V1.2.14_2026-10-13"), Apache-2.0 | Its LICENSE (Apache-2.0); the file tree (to find chip headers and prebuilt libraries); `include_lib/driver/cpu/wl82/asm/WL82.h` and `csfr.h` (the register definitions), vendored unmodified. Nothing in them was used in our code yet. | vendor/jieli-sdk/, tools/fetch-sdk.sh, NOTICE, docs/TOOLCHAIN.md |
| P-3 | 2026-10-21 | M0a | Docker Hub `debian:bookworm-slim`, amd64 manifest `sha256:ec31d744f83f4a73447ba045aaab9409997efe5cc706eca4890c1be36cc1606a` (index `sha256:7ff6ba31527b9e336162fa061746c366c4b2032f4d2cff2078bea43f78efe3f8`); `snapshot.debian.org` at `20261020T000000Z`; `docker/dockerfile:1.10` at `sha256:865e5dd094beca432e8c0a1d5e1c465db5f998dca4e439981029b3b81fb39ed5` | Build container base, packages and Dockerfile frontend. | tools/Dockerfile |
| P-4 | 2026-10-21 | M0a | Anthropic, "Models overview", `https://platform.claude.com/docs/en/about-claude/models/overview` | Claude Opus 5.5 (`claude-opus-5-5`): reliable knowledge cutoff Jun 2026, training data cutoff Jun 2026. | docs/EXPOSURE.md |
| P-5 | 2026-10-21 | M0a | Check tooling: FSFE REUSE (`reuse` 6.2.0, PyPI), `opentimestamps-client` 0.7.2 (PyPI), GitHub Actions `actions/checkout` v7.0.1, `actions/upload-artifact` v7.0.2, `actions/setup-python` v7.1.0 (pinned by commit SHA) | Versions and commit SHAs to pin. | .github/workflows/, tools/requirements-ci.txt |
| P-6 | 2026-10-21 | M0a | This session's own Claude Code transcript (`~/.claude/projects/…/36860ab8-….jsonl`), structure only | How Claude Code 2.1.307 stores tool calls (`type: assistant` entries with `tool_use` blocks) and attachments, so that `tools/check-transcripts.py` parses the real format. | tools/check-transcripts.py |
| P-7 | 2026-10-22 | M0b (spec side) | The emulator upstream `https://github.com/joakimeriksson/fm1-emu`, commit `43ed5580064885e93bc8d20be931ae950d10cd4f`, MIT: crates `fm1-isa`, `fm1-core`, `fm1-soc`, its LICENSE and workspace manifest; also read, not vendored: its `crates/fm1-emu/src/main.rs` | The emulator itself, vendored unmodified (one manifest patch) as the harness's engine. Spec side only: never a firmware-side source. | vendor/emulator/, tools/fetch-emulator.sh, harness/, NOTICE |
| P-8 | 2026-10-22 | M0b (spec side) | Docker Hub `rust:1.99.0-slim-bookworm`, amd64 manifest `sha256:ba81bc3eaa4422af576c0262515d96b0111a628a6ccc2c86557cf55c9a4bbee0` (index `sha256:2c3a22f0a5533ea2dd5a16627bc841228151faa2d4de2644ac9987e4a2f1f2fa`); Rust 1.99.0 | Build stage of the harness container (harness/Dockerfile) and the toolchain pin (harness/rust-toolchain.toml). The upstream crates need Rust 1.95 or later. | harness/ |
