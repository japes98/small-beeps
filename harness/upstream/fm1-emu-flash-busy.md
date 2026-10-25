<!--
SPDX-License-Identifier: MIT
SPDX-FileCopyrightText: 2026 japes98
-->

# Upstream note: the flash chip's busy times, its command rules, and a power cut

For the owner to apply in the F-Emulator app, and to offer to
`joakimeriksson/fm1-emu` if wanted. Spec side only; not filed by a
session. Written in session day-1024 (2026-10-24) against commit
`43ed5580064885e93bc8d20be931ae950d10cd4f`; our copy carries the change as
`vendor/emulator/patches/0010-flash-chip-busy-times-and-power-cut.patch`
(fwtest 0.6.0). docs/EMULATOR-PARITY.md lists it.

## What upstream does

`spiflash.rs` erases a sector as the third address byte arrives, runs a
page program on past the end of its 256-byte page, programs without a
write enable, and finishes every erase and program at once, so the status
register never reads busy. A firmware that forgets the write enable or
the wait, or writes across a page, works in the emulator and not on the
chip.

## What the patch does

In `fm1-soc`'s `spiflash.rs` and `lib.rs`:

- Command rules as the P25Q80H's datasheet gives them (the part whose
  JEDEC ID the model answers): an erase or program needs WREN and starts
  when CS goes high; a program wraps within its page (of more than 256
  bytes the last 256 count) and only clears bits; erases `0x81`, `0x52`,
  `0x60` and `0xC7` join `0x20` and `0xD8`. These hold with or without
  the next item.
- `SpiFlash::timing` (default: none, every operation at once, as now).
  With it, an operation keeps the chip busy for that many cycles: status
  bit 0 (WIP) and bit 1 (WEL) read 1, and every command but `0x05` and
  `0x35` is ignored. `Soc` sets `flash.now` from `periph.cycles` before
  each SPI0 or PD0 access. fwtest sets 3 ms a program and 12 ms an
  erase.
- `SpiFlash::log`: every operation started (start and end cycle, command,
  offset, length). `SpiFlash::power_cut(now)` and `Soc::power_cut()` put
  back the part of an operation in progress not done by then.
- `Soc::window_read_busy`: the first code-window read while the chip is
  busy (fetches that miss the decode cache, and data reads; not the JIT's
  direct reads). fwtest ends the run on it, and checks each core's pc in
  its own copy of the run loops; the app may want to show a warning
  instead, since the stock firmware's behaviour on the chip is to keep
  its flash routines and handlers in RAM.

## For the app

The rules in the first item change what a firmware sees only when it
breaks them. The busy time is opt-in (`timing`). Whether the app turns it
on, and what it does about window reads while busy, is the owner's
choice; with it on, the stock firmware and community firmwares must keep
their flash routines in RAM, as they do on the chip.
