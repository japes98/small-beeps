<!--
SPDX-License-Identifier: MIT
SPDX-FileCopyrightText: 2026 japes98
-->

# Upstream note: the USB core's access port never answers

For the owner to offer to `joakimeriksson/fm1-emu` if wanted. Spec side
only; not filed by a session. The F-Emulator app found it and already
carries a fix (its branch `stock-016`, `f60b86b`, test `usb_port_answers`
in fm1-soc), described in a behaviour-only note the owner dropped
(PROVENANCE P-59). Written in session spec-overnight-1025 (2026-10-26)
against commit `43ed5580064885e93bc8d20be931ae950d10cd4f`; our copy carries
the same behaviour, written here from that note, as
`vendor/emulator/patches/0012-usb-port-answers.patch` (fwtest 0.7.0).
docs/EMULATOR-PARITY.md lists it.

## What the chip does

A firmware reaches the USB core's (MUSB-style) registers through one
word, `JL_USB->CON1` at 0x11804:

- **write a register:** write `index << 8 | byte`, bit 14 clear;
- **read a register:** write `index << 8`, bit 14 (`MC_RNW`) set;
- then poll the word until bit 15 (`MACK`) is set; a read's byte is then
  in bits 0-7.

Sources: the JieLi AC79 SDK at `5fa84a9b`:
`include_lib/driver/cpu/wl82/asm/WL82.h` lines 15-16, 464-485 (`JL_USB`
at `lsfr_base + map_adr(0x18, 0)` = 0x11800, `CON1` its second word);
`include_lib/driver/cpu/wl82/asm/usb.h` lines 42-44 (`USB_CON1`: `MC_RNW`
14, `MACK` 15) and 148-150 (`musb_read_usb`, `musb_write_usb`);
`include_lib/driver/device/usb/usb_phy.h` lines 61-90 (the indexes: 0
`FADDR`, 1 `POWER`, 2-5 `INTRTX1/2`, `INTRRX1/2`, 6 `INTRUSB`, 7-11 their
enables, ...). The functions themselves are in the SDK's prebuilt
libraries, not in its source, and were not opened. AL-255/FM-1-RE's
`docs/io/06-usb.md` section 2.1 describes the same port in the FM-1's
stock firmware: `(idx<<8)|val`, "sign-bit completion" (bit 15 of the
halfword), with the same index map. The AC63 SDK's `usb.h` for five other
JieLi chips also has `MACK` at 15 (corroboration only).

## What upstream does

The word is plain storage: it reads back what was written, so bit 15
never sets unless the firmware wrote it. Every access waits out the
firmware's own poll limit; the app's note counts about 19 000 polls each,
and a USB stack that then retries about once a second.

## What the patch does

- Reading 0x11804 gives the last value written with bit 15 set.
- For a read (bit 14 set), bits 0-7 hold the register's byte: 0 for the
  interrupt flags (indexes 2-6), since nothing is on the bus and nothing
  is pending; for any other index the last byte written to it (0 before
  any write). These two are modelling choices, not facts from the
  sources: on the chip the flags clear when read and the other registers
  have their own reset values and read-only bits.
- A write (bit 14 clear) keeps bits 0-7 as that index's byte. The index
  is bits 8-13 (0-63).
- Nothing else changes: no interrupt, no bus events (reset, connect,
  suspend, SOF), no endpoint FIFOs, and the rest of the USB block reads
  as before. A firmware waiting for a bus event waits forever, as with no
  cable.

Crate test `usb_port_answers` (the app's test's three checks, plus an
index never written and a halfword read); fwtest's harness test of the
same name and suite case `usbport` (image `tests/images/usbport.c`: each
access polled at most 1000 times; without the patch every poll runs out).

## Left open

FM-1-RE names bit 2 of the word before it (0x11800, `CON0`) the port's
"busy" bit; the SDK names that bit `USB_NRST` (the core's reset). Neither
the app nor fwtest models a busy bit. It stays open (the owner's answer,
recorded by session spec-a1-fwsc), on the list of things to confirm on a
real FM-1 (docs/M9-PLAN.md, "To confirm on a real FM-1 (Phase B)").
