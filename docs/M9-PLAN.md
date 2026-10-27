<!--
SPDX-License-Identifier: MIT
SPDX-FileCopyrightText: 2026 japes98
-->

# M9 plan: packaging a release

A plan for the owner to review, written by the spec side (session
evening-1024) before M9 starts. Nothing here is built. It takes its facts
from HARDWARE-SPEC.md (HW-n), from FM-1-RE's boot, architecture and update
documents (cited as RE, at the commit HARDWARE-SPEC.md's sources table
names), from the JieLi AC79 SDK (cited as SDK, at its pinned commit), and
from FM1 Open's terms files and file list only (docs/PLAN.md, Risks). It
quotes no code from any of them. The owner answered its questions on
2026-10-25 (recorded by session owner-answers-1025, at the end): M9 is
the app release only (section 1); section 2 stays a plan for M10.

M9 has two deliverables (docs/PLAN.md, "M1 to M9"): a release the
F-Emulator app can run, and the groundwork for a package real hardware can
install. Level 2 (M10 to M12) does the hardware itself; M9 does not flash
a unit.

## 1. A release for the app

The app boots a raw image (docs/EMULATOR-PARITY.md, patch 0006): the same
flat binary fwtest runs, linked to start at `0x02000000` (HW-1). The build
already makes it reproducibly (R-REPRO-3) as `app.bin`, with `app.elf`
and a `SHA256SUMS` beside it.

A release is a set of files attached to a GitHub release made from a
signed git tag (`m9`, `v0.x.y`; app releases start at 0.9.0, answer 6).
"The release format" below defines them exactly; this is the list:

| File | What |
|------|------|
| `small-beeps-<version>.fm1img` | **the one file a user needs**: `release.json` and the raw image in one container, which the app opens with one tap |
| `small-beeps-<version>.bin` | the raw image, byte for byte the build's `app.bin` |
| `release.json` | the metadata, byte for byte the copy inside the `.fm1img` |
| `small-beeps-<version>.elf` | the same build's ELF, for symbols (optional for users) |
| `SHA256SUMS` | SHA-256 of every file above, in `sha256sum` format |
| `LICENSE`, `NOTICE` | this repository's licence and notices, as at the tag |
| `RELEASE-NOTES.md` | what changed, the test record's CI run, known limits |

What the firmware side needs: nothing new in the firmware. A
`tools/release.sh` that runs `tools/build.sh build`, checks the outputs
against the commit's CI record (`tools/reproduce`, R-REPRO-4), writes
`release.json`, the `.fm1img` and `SHA256SUMS` (below), and stops if the tree is dirty or the tag
is missing. A CI job that rebuilds the tag and compares the hashes. A new
requirement (R-REL-1, say): a release's image is byte-identical to the
reproducible build of its tag, and its metadata and checksums match it.

How the app takes it: the app opens the `.fm1img`, reads its
`release.json`, shows the release's version, and checks the image's
SHA-256 against it (answer 1; "How the app verifies it", below). That is
the app's change, not the firmware's; the owner makes it in the app.

The `.fm1img` is the release format for our firmware. The stock package
format (`.fwsc`, section 2) is accepted for compatibility: Phase A1
(docs/A1-PLAN.md) builds our firmware into a standard `.fwsc` too, so it
loads wherever a stock package does, but a release's metadata and
checksums live in the `.fm1img` (the owner's decision, recorded by session
spec-a1-fwsc).

### The release format (format 1.0)

Written by the spec side (session spec-overnight-1025) for the firmware
side's release tooling and the F-Emulator app to build to. "Must" is a
rule a writer or reader breaks only by changing the format's version.
Numbers in the container are little-endian; offsets and sizes are in
bytes.

**Why a container of our own, not a zip.** iOS has no public API that
reads a zip archive, so the app would need a zip reader of its own, and
Files offers to expand a file it knows as a zip archive instead of handing
it to the app. A fixed header and two byte ranges take a few lines to read
and verify, and are reproducible byte for byte without fixing timestamps
or compression settings.

#### `release.json`

One JSON object (RFC 8259), UTF-8 without a byte-order mark. Format 1.0's
fields:

| Field | Type | Required | What |
|-------|------|----------|------|
| `format` | object `{"major": int, "minor": int}` | yes | The release format's version: `{"major": 1, "minor": 0}`. Must equal the container header's. |
| `kind` | string | yes | `"app"`: a release for the F-Emulator app. (`"hardware"` is kept for M10's packages; a reader of format 1 refuses any other value.) |
| `name` | string | yes | `"small-beeps"`. |
| `version` | string | yes | The release's version, Semantic Versioning 2.0.0 without build metadata (`MAJOR.MINOR.PATCH`, optionally `-prerelease`), from 0.9.0 (answer 6). |
| `tag` | string | yes | The signed git tag the release was built from (`v0.9.0`, `m9`). |
| `git_commit` | string | yes | The tag's commit, 40 lowercase hex digits. |
| `targets` | array of strings | yes | Where it runs: `["f-emulator-app"]`. A reader that is not one of the targets refuses the release. |
| `image` | object | yes | The raw image, below. |
| `image.file` | string | yes | Its file name in the release, `small-beeps-<version>.bin`: ASCII letters, digits, `.`, `-` and `_` only, no path. |
| `image.size` | integer | yes | Its size in bytes, 1 to 1 032 192 (docs/HARNESS.md, "The raw image"). |
| `image.sha256` | string | yes | Its SHA-256, 64 lowercase hex digits. |
| `image.load_address` | integer | yes | `33554432` (`0x02000000`, HW-1). |
| `image.entry` | integer | yes | `33554432` (`0x02000000`, HW-2). |
| `fwtest` | object | yes | The runner the release's tests passed on. |
| `fwtest.version` | string | yes | fwtest's version (`fwtest version`), as `0.7.0`. |
| `fwtest.image` | string | yes | The pinned image: the one line of `config/fwtest-image` at the tag that is not a comment (`ghcr.io/...@sha256:<64 hex>`). |
| `record` | object | yes | The test record of the tag's commit: `records/<git_commit>/` on the `records` branch (R-REC-1, `tools/record.py`). The tag's commit must therefore be on main. |
| `record.tree_sha256` | string | yes | The record's tree hash: the SHA-256 of that record's `SHA256SUMS` file (the hash of every file in it, as "tree hash" means for `vendor/emulator/`), 64 lowercase hex digits. Not the git tree ID that `report.json` holds as `tree`. |
| `record.ci_run` | string | no | The URL of the CI run that made the record. |
| `build` | object | no | How the image was built. |
| `build.toolchain_sha256` | string | no | The pinned toolchain's SHA-256 (docs/TOOLCHAIN.md). |
| `build.container` | string | no | The build container's image digest (R-REPRO-2). |
| `build.ram_used` | integer | no | RAM the image uses (data, bss and stacks), from the build's size report. |
| `store` | object | no | The patch store the image keeps (docs/STORE-FORMAT.md). |
| `store.format_version` | integer | no | The store format's version, so a user knows whether saved patches carry over. |
| `store.offset`, `store.size` | integer | no | Its flash region, a chip offset and a size in bytes. |

Rules:

- **No time and no host details.** No field holds a build date, a time, a
  user or machine name or a local path: the file must come out the same
  from every rebuild of the tag. The date is the tag's.
- **Exact bytes.** Exactly what Python's
  `json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=True) + "\n"`
  writes: keys sorted, two-space indent, ASCII only, one final newline.
  Integers in decimal (JSON has no hex). At most 65 536 bytes.
- **Unknown fields.** A writer of format 1.0 writes only the fields above.
  A reader ignores fields it doesn't know (a later 1.x may add optional
  ones) and refuses a release that lacks a required field or has one of
  the wrong type.
- The loose `release.json` in the release is byte for byte the one inside
  the `.fm1img`.

#### The `.fm1img` container

File name `small-beeps-<version>.fm1img`. Three parts, in this order, and
nothing after the last:

1. **The header**, 64 bytes in format 1.0:

   | Offset | Size | Field | Format 1.0 value |
   |--------|------|-------|------------------|
   | 0 | 8 | magic | the bytes `46 4D 31 49 4D 47 0D 0A` (`FM1IMG`, CR, LF) |
   | 8 | 2 | `format_major` | 1 |
   | 10 | 2 | `format_minor` | 0 |
   | 12 | 4 | `header_size` | 64 |
   | 16 | 4 | `json_offset` | 64 (= `header_size`) |
   | 20 | 4 | `json_size` | the size of `release.json` |
   | 24 | 4 | `image_offset` | `json_offset + json_size`, rounded up to a multiple of 16 |
   | 28 | 4 | `image_size` | the raw image's size |
   | 32 | 32 | `payload_sha256` | SHA-256 of every byte from `header_size` to the end of the file |

2. **`release.json`**, `json_size` bytes at `json_offset`, then zero bytes
   up to `image_offset` (0 to 15 of them).
3. **The raw image**, `image_size` bytes at `image_offset`, byte for byte
   `image.file`. The file ends at `image_offset + image_size`.

The magic's CR LF catches a file mangled by a text-mode transfer; the
16-byte alignment is for convenience only. One input gives one file:
there is no timestamp, compression or optional padding to vary.

#### The format's version

- `format_major` changes when a reader of the old version would read the
  file wrongly: the header's layout, the parts' order, a required field's
  meaning, or a new required field. A reader refuses a major it doesn't
  know ("this release needs a newer app").
- `format_minor` changes for additions an older reader may ignore: an
  optional `release.json` field, or header bytes after offset 64 (a
  larger `header_size`; `payload_sha256` still covers everything from
  `header_size` on). A reader takes any minor of a major it knows; it
  locates every part by the header's offsets and sizes, never by
  assuming 64.
- `release.json`'s `format` always equals the header's two numbers.
- This document is the format's definition; a change to it changes the
  version as above and says what changed.

#### How the app verifies it

In this order, stopping at the first failure with a message naming it,
and never running an image that failed a step:

1. The file is at least 64 bytes and starts with the magic. (Otherwise:
   not a small-beeps release.)
2. `format_major` is 1. (Otherwise: needs a newer app.)
3. The header is consistent: `header_size` >= 64; `json_offset` >=
   `header_size`; `json_size` is 2 to 65 536; `image_offset` >=
   `json_offset + json_size`; `image_size` is 1 to 1 032 192;
   `image_offset + image_size` is exactly the file's size; every sum
   computed without overflow.
4. The SHA-256 of bytes `header_size` to the end equals `payload_sha256`
   (the file was not damaged in transfer).
5. `release.json` parses as one JSON object in UTF-8 with every required
   field of the right type; its `format` equals the header's; `kind` is
   `"app"`; `targets` holds `"f-emulator-app"`.
6. `image.size` equals `image_size`, and the SHA-256 of the image's bytes
   equals `image.sha256`.
7. `image.load_address` and `image.entry` are both `33554432`.

Then the app shows `name`, `version` and the first 12 digits of
`git_commit`, and boots the image as it boots a raw `.bin` today. A bare
`.bin` still opens as before, with no version shown.

What the checks prove: that the file is whole and the image is the one
its metadata names. They don't prove who made it: the hashes travel in
the same file. Authenticity comes from the signed tag and the
reproducible build: anyone can rebuild the tag and compare `image.sha256`
and the `.fm1img`'s own SHA-256 with `SHA256SUMS` (R-REPRO-4). Signing the
container itself is left for a later major version if it is ever needed.

#### Opening it in one tap (iOS)

What the app declares, so that a `.fm1img` from Files, AirDrop, Mail or a
Safari download opens in it directly:

- An **exported type** (`UTExportedTypeDeclarations`) with the
  identifier `io.github.japes98.fm1img` (the owner's choice, recorded by
  session spec-a1-fwsc): the format is this open project's, under MIT,
  not the app's, so any app or emulator may declare the same identifier.
  Filename extension `fm1img`, conforming to `public.data` only. Not
  `public.zip-archive` or `public.archive`: it isn't one, and Files would
  offer to expand it.
- An **imported type** (`UTImportedTypeDeclarations`) for the stock
  firmware package: identifier `io.github.japes98.fwsc`, filename
  extension `fwsc`, conforming to `public.data`. It is a declaration so
  the app can open such files, not a claim to own the format, which is
  JieLi's update package (section 2). A document type for it with
  `LSHandlerRank` `Alternate`, so the app never takes over another
  app's files.
- A **document type** (`CFBundleDocumentTypes`) for `io.github.japes98.fm1img` with
  `LSHandlerRank` `Owner`, so the app is the default for it.
- `LSSupportsOpeningDocumentsInPlace` false, so the app gets its own copy
  (AirDrop and Mail deliver one anyway), and handles it where it handles
  an opened URL, running the checks above.
- On GitHub the file is served as `application/octet-stream`; the
  extension, not the type, makes iOS hand it to the app.

#### What the release tooling checks

The firmware side's release tool (and its tests) must show: building the
same tag twice gives byte-identical `.fm1img`, `.bin` and `release.json`;
the container passes every check above; its `release.json` and image are
byte for byte the loose files; `SHA256SUMS` matches every file. A small
reference reader in `tools/` that runs the checks above in the same order
lets the tests and the app's author agree on them.

## 2. A package for real hardware (`.fwsc`)

Not in M9 (answer 2): this section stays a plan until M10, which decides
the boot area, the packaging tool and the version scheme (answers 3, 4
and 6). A package keeps the stock user-patch region untouched (answer 5).

### What a stock package is

From RE `docs/architecture.md` §2 and `docs/io/11-ota-protocol.md`:

- The stock file (`FM-1_0nn.fwsc`) is a JieLi "UFW" update package for
  the chip "AC791N". Its first 960 bytes are 20 blocks of 48: each block
  carries 47 bytes of header data and one marker byte; removing the
  markers gives a 940-byte header, and everything after byte 960 is
  plain. The device asks for bytes by their offset in that marker-free
  ("logical") image.
- The header is encrypted with the fixed header key `0xFFFF` and holds a
  header CRC, a list CRC, the image size, the entry count and eight
  entries: `flash.bin`, `info.log`, `USR`, the loader's configuration
  file (an `.ini`), `ota.bin`, `script.ver`, `blimit.bin`, `tail.bin`. CRCs are JieLi's CRC-16
  (CRC-16/CCITT-FALSE).
- `flash.bin` is the flash image from `0x00000` to `0x93FFF` (HW-80): a
  flash header, the second-stage loader `uboot.boot` from `0x000A0`, the
  loader's configuration (the same `.ini`, which carries the chip key
  `0x980F`) from `0x038D0`, then from `0x04000` the app area: a file
  directory, `app.bin` from `0x04120`, `cfg_tool.bin`, and a `cfg` entry.
  The app area is encrypted with the chip key (HW-81).
- `ota.bin` in the package is the update loader the device stages: a
  nested bootable image (`usb_hid_ota.bin`, LZ4-compressed blocks, two
  levels of CRC-16 headers) that runs from RAM. `script.ver` names the
  packaging tool's version (`AC791N-v0.01-cfg_tool-v0.10`).

### How it is installed (the stock path)

From RE `docs/io/11-ota-protocol.md` and `docs/io/12-v15-reflash-proof.md`:

- The running stock firmware is updated over USB-MIDI System Exclusive
  messages: a handshake, an upgrade command, then the *device* pulls the
  package by offset and length. Step 1 checks the package and stages the
  update loader; the device resets into it (it re-enumerates with another
  USB ID); step 2 pulls the whole image and writes it; a request for one
  of two reserved addresses marks the end of each step (RE gives them).
- Step 1 refuses a package it judges the same as what is installed; the
  check is in the stock firmware, and FM-1-RE has not found all of it.
  Stock-to-stock downgrades and a modified package have been installed
  this way.
- So the first install of our firmware on a unit goes through the *stock*
  firmware's updater (or through JieLi's lower-level USB recovery, which
  M10 covers). After that, our firmware must provide its own update path
  (M11) or the unit can only be updated by recovery.

### What a package of ours would carry

A package built the SDK's way, by its packaging tools, from our raw image:

- `flash.bin`: our `app.bin` in the app area, encrypted with the chip key
  by the packaging tool; the boot area (`uboot.boot` and its
  configuration) as the loader we ship. A package that keeps the stock
  boot area and changes only the app area is the smallest change, if the
  updater allows it (question 3; decided at M10).
- `ota.bin`: the update loader the stock updater stages. The SDK warns
  that an update across versions fails its file checks if the old and new
  loaders differ, or if the reserved and VM regions in the old and new
  loader configurations differ in count, size or address (SDK
  `cpu/wl82/tools/note.txt`, points 2(1) and 2(2)); and that single- and
  dual-backup layouts can't update one another (2(4)). So a package that
  a stock unit accepts most likely keeps the stock layout (HW-80) and the
  stock loaders.
- `USR`: the stock package carries one for the stock user-patch region.
  Whether ours carries an empty one, none, or one that keeps the region,
  decides whether the stock patches survive (Q-24).
- A version number that rises with every release: the SDK's packaging
  settings say to raise its firmware version number for every update
  (SDK `note.txt`, point 1), and the stock updater compares versions
  (RE, "ID block decoded").

### Which loader files we would vendor

FM1 Open (M-VAVE's `m-vave/fm1_open`, at
`4c7496daac04a95ff10d1afdcc8f9ead2dbabc41`) grants its boot and update
resources under Apache-2.0 (docs/PLAN.md, Risks, "Vendoring FM1 Open's boot
and update files for M9", from its `THIRD_PARTY.md` and file list only).
All are binaries, so none has a licence header; the grant is in
`THIRD_PARTY.md`:

| File | Bytes | Vendor? |
|------|------:|---------|
| `sdk/tools/pack/uboot.boot` | 14 488 | yes, if a package must carry its own boot area |
| `sdk/tools/pack/ota.bin` | 19 969 | yes: the size matches the stock package's staged update loader (`0x4E01` bytes with its outer header, RE), so it is most likely the loader a stock unit expects |
| `sdk/tools/pack/boot-config.bin` | 721 | yes, with `uboot.boot` |
| `sdk/tools/pack/cfg_tool.bin` | 383 | no: take it from the AC79 SDK, where it is the same file (same git blob `e197b6db…`), already an allowed source |
| `sdk/firmware/FM-1_015.fwsc` | 699 956 | never: M-VAVE's stock firmware |

The pinned AC79 SDK (Apache-2.0) also ships loaders in
`cpu/wl82/tools/` (`uboot.boot` 14 444 bytes, `uboot_no_ota.boot`, `ota.bin`
310 497 bytes, and the same again in `loader_tools/` at other sizes). By
their git blob hashes none is FM1 Open's or the stock package's, so they
are other builds; whether a stock FM-1 accepts them is not known. The
SDK's packaging programs (`isd_download.exe`, `fw_add.exe`,
`ufw_maker.exe`, `packres.exe`) are Windows binaries in the same folder.

How to vendor them: by `tools/fetch-fm1-open-boot.sh`, which fetches the
three files by raw URL at the pinned commit and checks each SHA-256
(never a clone: a clone puts FM1 Open's GPL app on disk), into
`vendor/fm1-open-boot/` with a `SOURCE.md` (commit, files, sizes,
SHA-256s, the section of `THIRD_PARTY.md` that grants them); `REUSE.toml`
entries (Apache-2.0, M-VAVE's copyright as `THIRD_PARTY.md` gives it); our
`NOTICE` naming them; the Apache-2.0 text in every release that carries
them. Nobody opens or disassembles them: they are named binaries with
hashes, like the toolchain.

### What the firmware side would need

- **The packaging tool.** JieLi's tools are Windows programs with no
  licence file of their own beyond the SDK's; running them in our pinned
  Linux container needs Wine, or a reimplementation of the package format
  from RE's description (the UFW header, the 48-byte blocks, the CRCs,
  the chip-key cipher of the app area). A reimplementation is ours and
  testable; but the chip-key cipher is described in FM-1-RE only by name
  (`jl_sfc_cipher`, base `0x4000`), not as a specification, so it would
  need a spec request first, and possibly the SDK's prebuilt code, which
  the firmware side may not read. The safer first step is the SDK's own
  tool under Wine, pinned by hash, as a build step (question 4; decided
  at M10, leaning towards our own packer).
- **What the image must be on the chip,** none of which fwtest checks:
  the app area starts at `0x04120`, so the code window's address
  `0x02000000` is chip offset `0x4120` (HW-81), not `0x4000` as in
  fwtest; the loader passes a boot block in r0 (HW-4, Q-11); the window
  is cached and encrypted (HW-81, HW-84); start-up must leave the flash's
  pins alone (HW-85). A spec request before M9's hardware half: what the
  loader expects at the app's first bytes (the stock app's header), and
  where the `cfg` entry must sit.
- **The store's region** must match what the package keeps: the store
  moves to `0xFC000`-`0xFEFFF` in M8a (the owner's answer to day-1024;
  pull request #111, open when this was written),
  outside every region a stock-style package writes, so a package that
  keeps the stock layout leaves it alone; but whether an update erases
  past `0x93FFF` at all is Q-24.
- **An update path in our firmware (M11):** without one, a unit running
  our firmware can't take the next release over USB. Until M11, every
  later install goes through JieLi's recovery (M10).

## 3. Risks

- **Bricking a unit.** A package the loader rejects after step 2 has begun
  writing can leave no runnable app. FM-1-RE records a recovery through
  the stock updater only while an app still runs; a hard brick needs
  JieLi's USB recovery, which M10 must prove on a unit first. No package
  goes near a unit before M10's recovery kit works.
- **The stock updater may refuse our package.** Its step-1 check is not
  fully understood (RE); a package with a new app and the stock loaders
  is the case most likely to pass, untested.
- **The key and encryption.** The app area is encrypted with the chip's
  key; if the packaging tool can't do that for us (or the key is per
  unit), the loader won't run our image. RE says the key in the loader's
  configuration is `0x980F` for the stock package; whether it is the same
  on every unit is not stated.
- **Licences.** FM1 Open's grant names "M-VAVE FM1 devices" only for its
  binary engine library, not for the boot files (docs/PLAN.md); still,
  check the grant's exact wording when vendoring. JieLi's Windows tools
  have no licence of their own (as with the toolchain): we would run
  them, never redistribute them.
- **Store survival across updates (Q-24).** If an update rewrites the VM
  or USR regions, or more, saved patches might be lost; ours sit in
  `0xFC000`-`0xFEFFF`, which the stock layout leaves unused.
- **Clean-room boundaries.** The stock `.fwsc` is stock firmware: no
  session opens it, and FM1 Open's copy is never vendored. FM-1-RE's
  update documents are allowed (CONTRIBUTING.md); its `firmware-images/`,
  disassembly and its OTA tool's code are not, and nor is its storage
  document for the firmware side (since evening-1024).
- **The app's loader is not the chip's loader.** A release that runs in
  the app (section 1) proves nothing about the chip's boot (HW-81, Q-11,
  Q-22). The two kinds of release are kept apart in their names and
  metadata.

## 4. The owner's answers (2026-10-25)

The questions were:

1. **The app and `release.json`.** Should the F-Emulator app read the
   metadata (show the version; check the hash), or keep loading a bare
   `.bin`?
2. **Release scope for M9.** Only the app release (section 1) in M9, with
   the hardware package left as this plan until M10's recovery kit
   exists? (Recommended.)
3. **Boot area.** Should a hardware package carry its own boot area
   (`uboot.boot` and its configuration from FM1 Open) or keep the unit's
   stock boot area and replace only the app area, if the updater allows
   it?
4. **The packaging tool.** JieLi's Windows tools under Wine in the pinned
   container (pinned by hash, never redistributed), or our own packer
   from FM-1-RE's description of the format, with a spec request for the
   cipher?
5. **Stock patches.** Should our package keep the stock user-patch region
   (`USR`) untouched, so a return to stock finds them, or is losing them
   acceptable?
6. **Version numbers.** Our versions start where? The stock updater
   compares versions; a version above stock's (15) may be needed for the
   first install, and below it for a return to stock (RE records both
   directions working through the stock updater).

The owner's answers (recorded by session owner-answers-1025,
docs/prompts/owner-answers-1025.md):

1. **`release.json`:** the app reads it, shows the version and checks the
   image's hash.
2. **Scope:** M9 is the app release only; the hardware package waits for
   M10.
3. **Boot area:** decided at M10.
4. **The packaging tool:** decided at M10, leaning towards our own
   packer (so the cipher's spec request comes first, then).
5. **Stock patches:** a hardware package keeps the stock user-patch region
   untouched.
6. **Version numbers:** app releases start at 0.9.0; the hardware
   packages' scheme is decided at M10.

Still open: Q-24, whether an update erases past `0x93FFF` at all
(answer 5 decides what our package does, not what the stock updater
does).

## 5. To confirm on a real FM-1 (Phase B)

Things fwtest and the app cannot settle, kept for the first tests on a
unit (Phase B). Each item names where it is
recorded.

- **The USB access port's "busy" bit.** FM-1-RE names a bit of the word
  before the USB core's access port that port's "busy" bit; the SDK names
  the same bit as the core's reset. Neither the app nor fwtest models a
  busy bit, and the owner keeps the question open (recorded by session
  spec-a1-fwsc): `harness/upstream/fm1-emu-usb-port.md`, "Left open";
  HARDWARE-SPEC.md HW-86.
