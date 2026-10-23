<!--
SPDX-License-Identifier: MIT
SPDX-FileCopyrightText: 2026 japes98
-->

# Vendored: Plaits' sound engine (Mutable Instruments, by Emilie Gillet)

For M4b's platform load test only: a separate demo build
(`firmware/demos/plaits/`), never part of the base image.

- **eurorack:** https://github.com/pichenettes/eurorack, commit
  `f4cfa7697095a28d292bff758beb51deb49b5a86` (2026-10-12, "Update
  README.md"). Under `eurorack/`: `plaits/` (the voice, its engines and
  its tables) and the repository's `README.md`, whose licence section
  says the STM32 projects' code, Plaits' included, is under the MIT
  licence. The repository has no licence file of its own.
- **stmlib:** https://github.com/pichenettes/stmlib, commit
  `e3bd7c9cc00e4364166f9905c0509b6ffd0535ec` (2023-05-30, "Make table
  tables const too"): the commit eurorack's `stmlib` submodule is pinned
  to at the eurorack commit above. Under `stmlib/`: its `LICENSE` and the
  DSP and utility headers Plaits uses. Both repositories are the author's
  own originals; nothing comes from a fork or a port.
- **Licence:** MIT, copyright Emilie Gillet. Every file taken carries the
  MIT notice in its own header (checked file by file at these commits:
  126 source files, all "Copyright 2012" to "2021 Emilie Gillet", MIT);
  `stmlib/LICENSE` states it for stmlib. stmlib's third-party code (ST's
  drivers, under other terms) is not taken.
- **Which files:** those `plaits/dsp/voice.cc` and `plaits/resources.cc`
  include, directly or not, and their `.cc` files; none of the hardware
  drivers, the bootloader, the tests or the hardware designs. Listed with
  their SHA-256 in `SHA256SUMS`, at their upstream paths.
- **Unmodified.** The demo builds them with `-DTEST`, upstream's own
  portable configuration (plain C++ instead of the STM32's assembly and
  flash access), and gives them the few standard headers they include from
  our own runtime. A change to a vendored file would be a patch file in
  `patches/` with its reason; there is none.
- **Trademark:** upstream's README asks that the name "Mutable
  Instruments" not be used on derivative works. The demo is a load test,
  named after the engine it measures, and is not released.
- Fetched and checked by `tools/fetch-plaits.sh`; checked in CI by
  C-PLAITS-PIN. Provenance: PROVENANCE.md P-28.
