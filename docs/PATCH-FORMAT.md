<!--
SPDX-License-Identifier: MIT
SPDX-FileCopyrightText: 2026 japes98
-->

# The FM engine's patch format, version 2

A patch is everything the FM engine (M5, `firmware/src/fm.h`) needs to
play a sound, and since version 2 (ARP) how the arpeggiator plays it:
112 bytes, each field one byte, or two bytes little-endian (the
arpeggiator's, since version 2, a few to a byte), so a patch can be
saved to flash (M7) and shared (the app) as it is, without conversion. `tools/fm_patch.py` writes and checks patches in this
format (its `encode` and `problems`), and `fm_patch_valid()` in
`firmware/src/fm_play.c` checks them the same way. The test patches are
defined once, in `tools/fm_patch.py`, and generated into
`firmware/src/patches.c`; they are our own (R-FM-7).

## Layout

| Offset | Bytes | Field | Values |
|-------:|------:|-------|--------|
| 0 | 2 | magic | `F` `M` (0x46, 0x4D) |
| 2 | 1 | version | 2 (since ARP; 1 before it, below) |
| 3 | 1 | length | 112, the whole patch |
| 4 | 12 | name | printable ASCII (32 to 126), padded with 0 |
| 16 | 1 | algorithm | 1 to 10 ("The algorithms", docs/DESIGN-NOTES.md, M5) |
| 17 | 1 | feedback | 0 (none) to 7, on the algorithm's feedback operator |
| 18 | 1 | flags | bit 0: mono; the other bits 0 |
| 19 | 1 | glide | a time code (below); 0: none. Mono only |
| 20 | 1 | transpose | signed semitones, -24 to 24 |
| 21 | 1 | pitch depth | signed semitones that a pitch level of 127 means, -48 to 48 |
| 22 | 3 | pitch rates | time codes: P0 to P1, P1 to P2 (then held), and to P3 on release |
| 25 | 4 | pitch levels | P0 (at note on) to P3, signed, -127 to 127 |
| 29 | 1 | arpeggiator | bit 0: on; bit 1: latch; bits 2 to 4: the mode, 0 to 5 (UP, DOWN, UP/DOWN, ORDER, RANDOM, CHORD); bits 5 and 6: octaves - 1 (1 to 4 octaves); bit 7: 0 |
| 30 | 1 | arpeggiator rate | bits 0 to 3: the rate, 0 to 9 (1/2, dotted 1/4, 1/4, dotted 1/8, 1/8, 1/8 triplet, dotted 1/16, 1/16, 1/16 triplet, 1/32); bits 4 to 7: the swing in steps of 5%, 0 to 15 (0 to 75%) |
| 31 | 1 | arpeggiator gate | 10 to 100: how long each note sounds, in % of its step |
| 32 | 6 x 13 | operators | operator 1 first (below) |
| 110 | 2 | check sum | Fletcher-16 of bytes 0 to 109: low byte the first sum, high byte the second, each mod 255 |

Each operator, 13 bytes from its first:

| Offset | Bytes | Field | Values |
|-------:|------:|-------|--------|
| 0 | 1 | mode | 0: a ratio of the note's frequency; 1: a fixed frequency |
| 1 | 2 | frequency | ratio x 256 (256 is 1.0, up to 255.996), or a fixed frequency in quarter hertz |
| 3 | 1 | detune | signed cents, -100 to 100 |
| 4 | 1 | level | 0 (off) to 127; gain 2^((level - 127) / 8) |
| 5 | 1 | velocity | sensitivity 0 to 7: at 7, velocity 0 is 8 octaves (48.2 dB) quieter than 127, in proportion between |
| 6 | 4 | rates | time codes: attack, decay 1, decay 2, release |
| 10 | 3 | levels | 0 to 127, as level: the attack's peak, the level after decay 1, the level held |

## Units

- **A time code** t, 0 to 127, is 2^(t / 8) ms, from 1 ms to 60.1 s: the
  time a stage takes over its whole range. The attack's range is a gain
  of 0 to 1; the decays' and the release's is 16 octaves (96.3 dB); the
  pitch envelope's 254 levels. A stage that moves only part of its range
  takes that part of the time.
- **A level** step is 2^(1/8), 0.753 dB; 127 is 0 dB.
- **An operator's index**: a modulator at full level moves its carrier's
  phase by 4 pi radians at the most (fm.c, `MOD_SHIFT`); level 103 (a gain
  of 1/8) is index pi/2.
- **Feedback** k (1 to 7) moves the operator's phase by up to
  pi / 2^(7 - k) times the mean of its last two outputs.

## Versions

Version 1 is the first (M5): bytes 29 to 31 reserved, 0. Version 2 (ARP)
gives those three bytes the arpeggiator's settings (the layout above,
docs/DESIGN-NOTES.md, "ARP"), so a patch keeps its 112 bytes and the
store its records' sizes. A version 1 patch is read as version 2 with the
arpeggiator's defaults: off, no latch, UP, one octave, 1/16, no swing, a
gate of 50% (bytes 29 to 31: 0, 7, 50), the version 2 and the check sum
worked out again (`fm_patch_upgrade()` in `firmware/src/fm_play.c`,
`upgrade` in `tools/fm_patch.py`). The arpeggiator's tempo, and what
MIDI out sends while it runs, belong to the instrument, not the patch
(docs/STORE-FORMAT.md, the settings).

A reader must refuse a patch with another
magic, version or length, a bad check sum or a field out of range: it
never guesses. A later version will keep the first four bytes' meaning,
so any reader can tell a patch it doesn't know from a damaged one, and
will say here what changed.
