<!--
SPDX-License-Identifier: MIT
SPDX-FileCopyrightText: 2026 japes98
-->

# Upstream note: MIDI out from UART1's transmit side, and the app's CoreMIDI output

For the owner to apply in the F-Emulator app, and to offer to
`joakimeriksson/fm1-emu` if wanted. Spec side only; not filed by a
session. Written in session midi-in-out (2026-10-24) against commit
`43ed5580064885e93bc8d20be931ae950d10cd4f`; our copy carries the change as
`vendor/emulator/patches/0009-midi-out-transmit-side.patch` (fwtest 0.5.0).
docs/EMULATOR-PARITY.md lists it.

## What upstream does

UART1 (`0x12100`) models only the MIDI IN jack's receive DMA. A write of
`TXCNT` (`0x12118`) sets the transmit pending (`CON0` bit 15) at once and
sends nothing ("no TX pin on the board"); a `BUF` (`0x1210C`) write is
plain storage. So a firmware's MIDI out vanishes, and its transmit
interrupt comes the instant it starts a transfer, not 320 µs per byte
later, which hides pacing bugs.

## What the patch does

In `fm1-soc`'s `periph.rs` and `lib.rs`:

- `TXCNT` written: `lib.rs` reads `TXCNT & 0xffff` bytes from `TXADR`
  (`0x12114`, kept in SFR storage) at that moment and hands them to
  `Periph::uart_transmit`. A `BUF` write hands over its low byte.
- `uart_transmit` drops them (counted in `midi_out_dropped()`) when
  `CON0` bit 0 is clear; otherwise it queues them behind anything still
  going. One byte goes per `midi_byte_time()` (10 bits at 31 250 baud:
  76 800 cycles at 240 MHz), whatever `BAUD` says, as the receive side
  does. `next_event` includes the transmitter, so the core never runs or
  skips past a byte's end.
- When the queue empties, `tpnd` is set and `uart_update` raises IRQ 20
  if `CON0` bit 2 is set; the existing `CON0` bit 13 write clears it.
- Every byte sent is kept as `(cycle its stop bit ended, byte)` until
  `Periph::midi_take_sent()` drains them, oldest first.

The patch applies to upstream after fwtest's 0001 to 0008 with line
offsets only; it touches no instruction decoding. fwtest's harness test
`transmits_midi` and the suite case `midiout` check it; without the patch
the same image's transmit interrupt runs twice, at once on each DMA (0 and
4.0 ms), instead of three times as each transfer's last byte ends (1.600,
3.320 and 5.281 ms).

## The app: sending the bytes to CoreMIDI

The board each package runs on matters only for what the user is told:
the SMK-37 has a MIDI OUT jack these bytes model; a real FM-1 has none
(docs/HARDWARE-SPEC.md, HW-67, HW-72 to HW-74), so for an FM-1 package
this is the emulator's extra, and should say so in the UI.

1. **A virtual source.** At start-up, `MIDIClientCreateWithBlock`, then
   `MIDISourceCreateWithProtocol` (`kMIDIProtocol_1_0`) named, say, "FM-1
   Emulator MIDI Out", so a DAW or another synth can pick it as an input.
   Give it a stable `kMIDIPropertyUniqueID` (saved in the app's
   preferences) so DAWs keep the routing across launches.
2. **Drain every frame.** After each slice of emulation, call
   `soc.periph.midi_take_sent()`. Never let the bytes pile up: the
   emulator keeps them only until taken.
3. **Bytes to messages.** CoreMIDI wants whole messages: parse the byte
   stream as MIDI 1.0 does, keeping the running status, passing real-time
   bytes (`F8` to `FF`) on at once even inside another message, and
   collecting system exclusive from `F0` to `F7` (a status byte other than
   real-time ends it unterminated: drop it). fwtest's decoder,
   `harness/src/midi.rs` (MIT, ours, no emulator code), does exactly this
   and can be ported; its tests list the edge cases. Expand running status
   into full messages before sending.
4. **Times.** Each byte's cycle is emulated time at 240 MHz. Keep one
   anchor, the host time (`mach_absolute_time()`) and emulated cycle when
   emulation (re)starts or the user changes speed; a message's host time is
   `anchor_host + (cycle - anchor_cycle) / 240e6` seconds, converted with
   `mach_timebase_info`, plus a fixed latency (say 5 ms) so messages
   scheduled from a frame already in the past still go out evenly. If
   emulation runs slower than real time, or a computed time is already
   past, send with timestamp 0 (now) rather than late-stamped.
5. **Send.** Build a `MIDIEventList` with `MIDIEventListInit` and
   `MIDIEventListAdd`, one MIDI 1.0 UMP per channel message (system
   exclusive as UMP data packets of up to six bytes each), and
   `MIDIReceivedEventList` on the virtual source. On macOS before 11,
   the `MIDIPacketList` and `MIDIReceived` calls do the same with the
   bytes as they are.
6. **Panic on stop.** When emulation stops, pauses, resets or loads
   another package mid-note, send note-off for every note the stream left
   on (track note-ons per channel and key as you parse), or `B0+n 7B 00`
   (all notes off) on each channel used, so nothing downstream hangs.

## Checking it

Run the harness test image `harness/tests/images/midiout.bin` in the app
with the output connected to a MIDI monitor (MIDI Monitor, or a DAW's MIDI
input view): two note-ons on channel 1 (60 and 62), a clock, a note-off
for 60 and an active-sensing byte, as `harness/tests/golden/midiout/
midi-out.txt` lists them, the five at 0.96, 1.6, 3.32, 4.96 and 5.28 ms
after start.
