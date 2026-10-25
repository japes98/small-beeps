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
quotes no code from any of them. Decisions wanted are at the end.

M9 has two deliverables (docs/PLAN.md, "M1 to M9"): a release the
F-Emulator app can run, and the groundwork for a package real hardware can
install. Level 2 (M10 to M12) does the hardware itself; M9 does not flash
a unit.

## 1. A release for the app

The app boots a raw image (docs/EMULATOR-PARITY.md, patch 0006): the same
flat binary fwtest runs, linked to start at `0x02000000` (HW-1). The build
already makes it reproducibly (R-REPRO-3) as `app.bin`, with `app.elf`
and a `SHA256SUMS` beside it.

A release is a folder (and a `.zip` of it) attached to a signed git tag
(`m9`, `v0.x.y`):

| File | What |
|------|------|
| `small-beeps-<version>.bin` | the raw image, byte for byte the build's `app.bin` |
| `small-beeps-<version>.elf` | the same build's ELF, for symbols (optional for users) |
| `release.json` | metadata, below |
| `SHA256SUMS` | SHA-256 of every file above, in `sha256sum` format |
| `LICENSE`, `NOTICE` | this repository's licence and notices, as at the tag |
| `RELEASE-NOTES.md` | what changed, the test record's CI run, known limits |

`release.json`, one object:

- `name`, `version` (semantic), `git_commit` (full SHA), `tag`;
- `image`: file name, size, SHA-256, `load_address` `0x02000000`,
  `entry` `0x02000000` (HW-1, HW-2), `ram_used` (data + bss + stacks,
  from the build's size report);
- `toolchain`: the pinned toolchain's SHA-256 (docs/TOOLCHAIN.md) and the
  build container's image digest (R-REPRO-2);
- `fwtest`: the pinned image digest the release's suite ran on, and the
  CI run that recorded it;
- `store`: the store's chip region and format version
  (docs/STORE-FORMAT.md), so a user knows whether saved patches carry
  over between releases;
- `targets`: `["f-emulator-app"]` for this release kind.

What the firmware side needs: nothing new in the firmware. A
`tools/release.sh` that runs `tools/build.sh build`, checks the outputs
against the commit's CI record (`tools/reproduce`, R-REPRO-4), writes
`release.json` and `SHA256SUMS`, and stops if the tree is dirty or the tag
is missing. A CI job that rebuilds the tag and compares the hashes. A new
requirement (R-REL-1, say): a release's image is byte-identical to the
reproducible build of its tag, and its metadata and checksums match it.

How the app takes it: the owner's app loads `*.bin` as today. Whether the
app should read `release.json` (to show the version, or to refuse an
image whose hash doesn't match) is the owner's call (question 1).

## 2. A package for real hardware (`.fwsc`)

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
  entries: `flash.bin`, `info.log`, `USR`, `isd_config.ini`, `ota.bin`,
  `script.ver`, `blimit.bin`, `tail.bin`. CRCs are JieLi's CRC-16
  (CRC-16/CCITT-FALSE).
- `flash.bin` is the flash image from `0x00000` to `0x93FFF` (HW-80): a
  flash header, the second-stage loader `uboot.boot` from `0x000A0`, the
  loader's configuration (`isd_config.ini`, which carries the chip key
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
  USB ID); step 2 pulls the whole image and writes it; two raw addresses
  (`0xE0000000`, `0xF0000000`) mark the ends of the steps.
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
  updater allows it (question 3).
- `ota.bin`: the update loader the stock updater stages. The SDK warns
  that an update across versions fails its file checks if the old and new
  loaders differ, or if the reserved and VM regions in the old and new
  `isd_config` differ in count, size or address (SDK
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
  tool under Wine, pinned by hash, as a build step (question 4).
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

## 4. Questions for the owner

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
