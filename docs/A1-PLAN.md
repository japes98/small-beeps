<!--
SPDX-License-Identifier: MIT
SPDX-FileCopyrightText: 2026 japes98
-->

# Phase A1: our firmware as a standard `.fwsc` package

A note from the spec side (session spec-a1-fwsc, 2026-10-27) to the
firmware side, in the manner of a spec request's answer: what to build,
from which facts, and how it is tested. Nothing here is built on the
firmware side yet. Its facts are docs/HARDWARE-SPEC.md HW-87 to HW-93
(section 21); this note adds none of its own and gives no code.

## The goal

The firmware side builds our firmware into an update package (`.fwsc`)
in JieLi's standard format that loads, the same way a stock package does,
in three places:

1. the F-Emulator app's package path (it opens `.fwsc` files as the
   imported type `io.github.japes98.fwsc`, docs/M9-PLAN.md section 1);
2. fwtest, through its package path (`--package`, docs/HARNESS.md
   "Packages", from fwtest 0.8.0);
3. the upstream fm1-emu web build, which boots every firmware from its
   package.

The `.fm1img` stays our release format; the `.fwsc` is for compatibility
with tools that take packages (docs/M9-PLAN.md section 1). A1 does not
make a package for real hardware: what the chip's loaders and updater
check is open (Q-26), and M10 decides the boot area and the packaging
tool. A package that passes all three paths may still be refused by a
unit; nobody installs one on a unit in A1.

## Note A1-1 (to the firmware side): a packager in `tools/`

- Status: open (for the firmware side).
- What to build, from HW-87 to HW-91 only:
  - **A second link of the firmware**, for the package, at the address a
    package's app runs from: the window's start plus the app's offset in
    the app area, `0x02000120` with the SDK's `0x120`-byte directory
    (HW-91). The raw image (`app.bin`, linked at `0x02000000`) stays as
    it is, for fwtest's raw path, the `.fm1img` and the app's raw loader.
    The two are the same code linked twice; nothing in the firmware may
    depend on which.
  - **A packager**, `tools/` (say `tools/fwsc.py`), that makes
    `small-beeps-<version>.fwsc` from that link's binary: the package
    header in 20 blocks with our identity in the markers (HW-88: ASCII,
    at most 19 characters, not another board's prefix); one entry, the
    flash image (type 0); the flash image (HW-89): the flash header, a
    directory with the configuration head and the app area's head, a key
    block of our own with its CRC-16; the app area at flash `0x4000`
    (HW-90): its head, its directory with `app.bin` (attribute `0x82`)
    at offset `0x120`, the app, scrambled with the key the key block
    gives. Every CRC by HW-87's rule: header, flash header, each head and
    each head's data. Fields the facts don't define (Q-25) are written as
    0 and listed in the packager's own documentation as unknown.
  - **What it leaves alone.** The flash image ends at the app area's end,
    so a package writes nothing past it: not the store's region, not the
    stock user-patch region (answer 5 in M9-PLAN.md).
  - **No loader binaries.** None of the three paths runs one (HW-93); the
    boot area holds only the flash header, the directory and the key
    block ("Loaders", below).
  - **Reproducible** (R-REPRO): the same tag gives a byte-identical
    `.fwsc`, built in the pinned container by the release tooling beside
    the `.fm1img`.
  - **A reference reader** in `tools/` that runs HW-93's checks in its
    order and prints which one fails, so the tests, the app's author and
    fwtest agree on them.
- Why: Phase A1 (the owner's prompt, docs/prompts/spec-a1-fwsc.md);
  answers M9-PLAN.md's question 4 for the emulated paths (our own packer).
- Logged as: the facts reach the firmware side through HARDWARE-SPEC.md
  only; the firmware side's PROVENANCE entry names HW-87 to HW-93.

## How it is tested: the three load paths

1. **fwtest** (automatic, in CI). With fwtest 0.8.0 pinned: the firmware
   suite runs a case from the package (`tools/fwtest run
   small-beeps-<version>.fwsc --package ...`) beside the same case from
   the raw image; both must show the firmware's normal start (its first
   screen, its own start-up marks) and the same outputs where the entry
   address can't matter. `result.json`'s `run.package` must name our
   identity, the app area `0x04000` and the entry `0x02000120`. The
   reference reader runs on the package. Unit tests of the packager make
   a package with each check of HW-93 broken in turn and show fwtest and
   the reader refuse each, naming the check.
2. **The F-Emulator app** (by hand, the owner): open the `.fwsc` from
   Files; the firmware starts as it does from the `.fm1img` of the same
   tag. The owner records the result in the release notes. (The app's
   package path is upstream's unchanged, with checks of its own around
   it; confirmed by the app session, 2026-10-27; docs/EMULATOR-PARITY.md,
   "Packages".)
3. **The upstream web build** (by hand, the owner, or a spec-side
   session; not the firmware side): open the `.fwsc` with the hosted
   page's "Open .fwsc…" button; the firmware starts. The page's own
   catalog fetches and runs other firmwares from other sites, some of
   them on CONTRIBUTING.md's list of material the firmware side never
   opens or fetches, so a clean session doesn't use the page at all.

A1 is done when all three boot the same tag's package and the CI case
passes.

## Loaders

- **What a package needs.** None of the three load paths runs the mask
  ROM, the second-stage loader or the update loader (HW-92, HW-93): they
  need no loader file at all, so A1's package carries none.
- **For a hardware package (M10, not A1)**: the SDK's own second-stage
  loader `uboot.boot` and update loader `ota.bin` (`cpu/wl82/tools/` at
  the pinned SDK commit, JieLi's, Apache-2.0) are the candidates; a
  release package may carry them, with the SDK's licence text and a
  `NOTICE` entry, as named binaries checked by SHA-256 that nobody opens.
  Whether a stock unit accepts them is unknown (M9-PLAN.md section 2;
  Q-26).
- **Not used:** FM1 Open's boot and update files (M-VAVE's, Apache-2.0):
  the owner keeps every M-VAVE binary out of the repository, these
  included (recorded by session spec-answers-a1); M-VAVE's stock package
  and anything from it: never.
- The SDK's packaging programs are Windows binaries; A1 doesn't need
  them.

## Order

1. The owner merges the spec side's pull requests (the harness's package
   path; fwtest 0.8.0 is then published from main).
2. The firmware side pins fwtest 0.7.0 (its pull request, as the owner
   decided), then 0.8.0 (a pin pull request after the image is
   published; the clean side opens it too, the owner's answer recorded
   by session spec-answers-a1).
3. The firmware side builds Note A1-1 and its CI case; the owner checks
   the app and the web build by hand.
