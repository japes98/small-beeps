<!--
SPDX-License-Identifier: MIT
SPDX-FileCopyrightText: 2026 japes98
-->

# Vendored: the emulator's core crates (spec side only)

- Repository: https://github.com/joakimeriksson/fm1-emu (public, MIT)
- Commit: `43ed5580064885e93bc8d20be931ae950d10cd4f` (main on 2026-10-22,
  "Merge pull request #39 from joakimeriksson/windows-jit", committed
  2026-10-21T22:07:20+02:00)
- Licence: MIT, copyright 2026 Joakim Eriksson (`LICENSE` here, copied
  unmodified).
- What: `crates/fm1-isa`, `crates/fm1-core` and `crates/fm1-soc`, at the
  same paths, unmodified but for one bug fix in `fm1-soc` (patch 0002,
  below), and the workspace manifest `Cargo.toml` (patched, below).
  Nothing else from that repository: no other crates, no `fm1-sid/`, no
  probes, no firmware files.
- Fetched by `tools/fetch-emulator.sh --fetch` (a blob-less clone with a
  sparse checkout of exactly those paths) and checked by
  `tools/fetch-emulator.sh --verify` (C-EMU-PIN): every file against
  `SHA256SUMS`, whose own SHA-256 (the tree hash) is
  `3027510f8282be30861fc22978a8f556b4b0a9ce208e4d816d5e53448d9738e8`.
- Provenance: PROVENANCE.md P-7. Exposure: docs/EXPOSURE.md (session M0b).

## Patches

Applied in file-name order by the fetch script, after checkout:

- `patches/0001-workspace-members.patch`: the three crates take their
  version, edition and licence from the workspace manifest, which upstream
  lists with seven members. The patch keeps the manifest and lists only the
  three vendored crates, so they build as path dependencies of `harness/`.
  No code is changed.
- `patches/0002-spi1-con-writes-replace.patch` (session SR-3, 2026-10-23,
  chosen by the owner): `crates/fm1-soc/src/lib.rs`, SPI1's `CON` write
  (0x11D00). Upstream merged each written value into the stored one, so a
  bit once written 1 could never be cleared, and after any write with bit
  13 every SPI1 transfer raised IRQ 16. With the patch a write replaces
  `CON` (bit 14 stays a strobe that clears the pending flag, not stored).
  The harness test `spi1_interrupt_follows_con_bit_13` fails without it.
  Reported upstream by the owner from `harness/upstream/fm1-emu-spi1-con.md`;
  drop the patch when the pinned commit has the fix.

## Not used

The harness never calls the crates' update-package and stock-boot paths
(`fwsc`, `stock_from_package`, `stock_boot`, `write_boot_info`); they are
vendored only because the crate is kept whole. C-HARNESS-SCOPE checks
that `harness/src` names none of them.
