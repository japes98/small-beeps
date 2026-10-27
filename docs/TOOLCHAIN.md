<!--
SPDX-License-Identifier: MIT
SPDX-FileCopyrightText: 2026 japes98
-->

# Toolchain and SDK

## JieLi Linux toolchain (PROVENANCE P-1)

| Item | Value |
|------|-------|
| Name | `jieli-linux-toolchains-20250324.1` |
| Published at | `https://pkgman.jieliapp.com/s/linux-toolchain` (vendor short link) |
| Pinned URL | `https://jl-update.oss-cn-shenzhen.aliyuncs.com/jieli-linux-toolchains-20250324.1.tar.xz` |
| Size | 26,009,040 bytes |
| SHA-256 | `f686586bcfb45e0f0bb27fd2b39c7a7f313cb4f0e88a66a14da621ffa8225958` |
| MD5 (server ETag) | `22a619513462abfc4d86ed50b2922ef7` |
| Server Last-Modified | Mon, 24 Mar 2025 02:39:21 GMT |
| Downloaded | 2026-10-21 |
| Contents | Clang/LLVM 4.0.1 with a pi32v2 backend; GNU Binutils ld 2.26.51.20160621 (targets `elf32-pi32v2`); Linux x86-64 binaries |

**The short link has moved on.** On 2026-10-21 the short link redirected to
`jieli-linux-toolchains-20260730.1.tar.xz` (a newer release), not the pinned
20250324.1. The pinned file is still served at its direct URL, which is what
`tools/Dockerfile` uses. Moving to a newer toolchain is a deliberate change
in its own pull request, with a new SHA-256 here.

### How it is used

- `tools/Dockerfile` downloads the pinned URL, checks the SHA-256 above
  (`sha256sum -c`; the build fails on any mismatch), and unpacks only
  `common/` and `pi32v2/` into `/opt/jieli` in a locally built image.
- The archive and the image are **never committed or published**: not in this
  repository, not in releases, and not pushed to any registry. CI builds the
  image fresh every run. `.gitignore` excludes `*.tar.xz`, and check
  C-NO-TOOLCHAIN fails if any tracked file looks like part of the toolchain.
- A release records the build's identity instead of an image (the owner's
  answer, 2026-10-27): the base image's digest, the SHA-256 of
  `tools/Dockerfile` and the archive's SHA-256 above, in
  `config/build-image`. A CI release checks the tag's Dockerfile against
  it before it builds, and builds the image fresh (docs/RELEASING.md,
  "The build image").
- We compile with `clang -target pi32v2 -mcpu=r3 -mfprev1 -std=c11
  -ffreestanding -nostdlib` and link with the toolchain's `ld`. Since M5
  `-mcpu=r3 -mfprev1` build for the chip's CPU model and its
  single-precision float instructions, as the SDK does (HW-62); the
  toolchain then emits them inline instead of calling a float library. We never link the toolchain's C library
  or its other runtime libraries (R-BUILD-1).

### Licence and terms files found inside

The archive has 695 entries. A search of every path for licence, copying,
notice, terms, EULA, readme and copyright found one file:

- `README.md` (Chinese, about 20 lines): usage notes only. After unpacking
  there are `common/`, `pi32/`, `pi32v2/` and `q32s/` directories; each chip
  family's tools are in its own directory, so set `CC` and similar variables
  in the Makefile; raise the open-file limit (`ulimit -n 8192`) before
  linking, or `ld` may fail with "File format not recognized". **No licence,
  copyright or terms of use.**

No other licence or terms file is present. The toolchain's licence terms are
therefore **unknown**, which is why we never redistribute it. It contains
components normally released under open licences (LLVM/Clang, GNU Binutils,
a newlib C library: `include/newlib.h` and libraries), but the archive
carries none of their licence texts.

### Compiler builtins

Clang's builtins (helpers such as 64-bit division the compiler may call)
would come from `pi32v2/lib/<variant>/libcompiler-rt.a` in the archive. That
is JieLi's build of LLVM's compiler-rt. Upstream compiler-rt of the LLVM 4.x
era is dual-licensed under the University of Illinois/NCSA licence and the
MIT licence. JieLi's build ships no licence text and no source, so we cannot
confirm what is in it. **We don't link it.** `-nostdlib` keeps it out, and
when the firmware needs builtins, our own runtime will provide them (M0d and
later). If that ever changes, the change records the reason here.
Since M4b the Plaits demo (`firmware/demos/plaits/`, its own image only)
carries soft-float routines of its own (`runtime/softfloat.c`) for the float
calls clang makes; the firmware itself still needs none.

### Risk

If the download disappears, a full rebuild needs another copy of exactly this
archive, matched by the SHA-256 above. Every released binary stays
verifiable without the toolchain, because each record lists its output
hashes. To preserve the archive, a copy is kept in a separate **private**
repository, `japes98/small-beeps-toolchain`, as a release asset, only for
preservation. It is never public and never linked from releases.
*Status: see the end of this file.*

## JieLi AC79 SDK (PROVENANCE P-2)

| Item | Value |
|------|-------|
| Repository | `https://gitee.com/Jieli-Tech/fw-AC79_AIoT_SDK` |
| Branch | `release/AC79NN_SDK_V1.2.0` (the repository's HEAD) |
| Pinned commit | `5fa84a9b2f723a5e9337ad79dc2ad741fc98fe2d`, "AC79NN_SDK_V1.2.14_2026-10-13" |
| Licence | Apache License 2.0 (top-level `LICENSE`) |
| Fetched by | `tools/fetch-sdk.sh` (checks each file against `vendor/jieli-sdk/SHA256SUMS`) |

### What we take

Only these files, unmodified, under `vendor/jieli-sdk/` (the AC791N is the
SDK's `wl82` CPU family):

- `LICENSE`: the SDK's Apache-2.0 licence;
- `include_lib/driver/cpu/wl82/asm/WL82.h`: special-function register
  definitions;
- `include_lib/driver/cpu/wl82/asm/csfr.h`: core register definitions, which
  `WL82.h` includes.

More headers are added only when a firmware milestone needs them, each in
its own commit, logged in PROVENANCE.md.

### Licence coverage

The SDK's top-level `LICENSE` is the Apache License 2.0 and covers the
repository. Many SDK headers also carry JieLi's own notice in the form
"Copyright:(c)JIELI 2011 @ , All Rights Reserved." This is a copyright
notice; it doesn't grant other terms, and the repository-level Apache-2.0
grant applies. `WL82.h` and `csfr.h` carry no per-file notice. `REUSE.toml`
marks `vendor/jieli-sdk/**` as Apache-2.0, copyright JIELI.

### Not used: parts with other or unknown terms

These parts of the SDK are **not used** and never vendored:

- **Prebuilt libraries:** 151 `.a` archives under `cpu/wl82/`, plus 3 under
  `include_lib/c++/` and 3 under `include_lib/newlib/` (binary only; terms
  unknown beyond the repository licence; we use none).
- **Windows tool binaries:** `.exe`/`.dll` files under `tools/utils/` and
  `cpu/wl82/tools/`. Not inspected; judging by their names (`make.exe`,
  `libiconv2.dll`, `libintl3.dll`), some are likely GNU tools under their own
  licences.
- **Bundled third-party code under its own licences**, including
  `apps/common/example/third_party/` (coremark, FlashDB, littlefs, ugfx's
  tinygl), `include_lib/net/uC-HTTPc/` (own LICENSE and NOTICE),
  `include_lib/system/os/POSIX/` (own LICENSE) and `lib/net/mbedtls_3_4_0/`
  (own LICENSE).
- **Linker scripts** under `include_lib/driver/cpu/wl82/` (`*.ld`): not used.
  M0d writes its own linker script from `HARDWARE-SPEC.md`.

## Preservation copy status

- 2026-10-22 (UTC): uploaded with the owner's approval by session M0a.
  Private repository `japes98/small-beeps-toolchain`, release
  `toolchain-20250324.1`, asset `jieli-linux-toolchains-20250324.1.tar.xz`.
  Downloaded back and checked: SHA-256
  `f686586bcfb45e0f0bb27fd2b39c7a7f313cb4f0e88a66a14da621ffa8225958`
  (matches). The release notes repeat the hash and say the terms are unknown
  and that it is not for redistribution.
