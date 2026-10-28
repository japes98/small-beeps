<!--
SPDX-License-Identifier: MIT
SPDX-FileCopyrightText: 2026 japes98
-->

# The store's format, version 1

The firmware keeps its user patches, the patch selection and the settings
in a store of our own design (M7; `firmware/src/store.c`, and
docs/DESIGN-NOTES.md, M7, for why it is built this way). This is its
layout on the flash chip. `tools/store.py` reads and writes the same
format, and `tests/test_store.py` checks that its constants are the
firmware's. Numbers are little-endian.

## The region

Chip offsets `0xFC000` to `0xFEFFF`, the stock layout's unused region
(HW-80): 3 sectors of 4 KiB, used as a ring. The firmware leaves the
stock firmware's user patch region (`0xEA000` to `0xFBFFF`, where M7's
store was) as it is, so the stock firmware's saved patches survive; why
three sectors are enough is in docs/DESIGN-NOTES.md (M8a). The format
does not depend on the number of sectors. Where it sits is one
definition (`STORE_BASE` and `STORE_SIZE` in `store.h`), since where our
own image sits on the chip is M9's; `firmware/app.ld` keeps the image
clear of it. The firmware reads and writes the region only through
SPI0's flash commands (HW-47, HW-78), never through the code window
(HW-81).

## A sector

Each sector starts with a 16-byte header:

| Offset | Bytes | Field |
|-------:|------:|-------|
| 0 | 4 | magic `SBS1` (0x31534253) |
| 4 | 4 | sequence number: one more than the sector that was the head before it |
| 8 | 1 | format: 1 |
| 9 | 3 | 0 |
| 12 | 4 | CRC-32 of bytes 0 to 11 |

A sector whose header is not valid holds nothing. The valid sector with
the highest sequence number is the **head**, the one that takes new
records.

## A record

Records start on a 16-byte boundary after the sector's header:

| Offset | Bytes | Field |
|-------:|------:|-------|
| 0 | 1 | magic 0xA5 |
| 1 | 1 | kind (below) |
| 2 | 1 | id: the user slot, 0 to 15, for a patch; 0 otherwise |
| 3 | 1 | the payload's version |
| 4 | 2 | the payload's length, at most 112 (a firmware kind's part: 496) |
| 6 | 1 | 0 (a firmware kind's part: its index, from 0) |
| 7 | 1 | 0 (a firmware kind's part: how many parts its payload has, 1 to 12) |
| 8 | 4 | sequence number: one more than the record written before it |
| 12 | length | the payload |
| 12 + length | 4 | CRC-32 of the header and the payload |

The bytes after the CRC, up to the next 16-byte boundary, are left erased.
The CRC-32 is the common one (reflected, polynomial 0xEDB88320, all ones in
and out: zlib's).

| Kind | What | Payload, its version |
|-----:|------|----------------------|
| 1 | a user slot's patch | the 112-byte patch (docs/PATCH-FORMAT.md): version 2 (since ARP), the record's version the patch's own; a version 1 patch (before ARP) is read as version 2 with the arpeggiator's defaults, and stays version 1 in the store until the slot is saved again |
| 2 | the patch selection | 4 bytes: the program (0 to 8 the test patches, 9 to 24 the user slots), then 0, 0, 0; version 1 |
| 3 | the settings | `struct midi_settings` (`firmware/src/midi.h`): version 4 (since ARP), 42 bytes: version 3's 40, then the internal tempo (40 to 240 beats a minute) and what MIDI out sends while the arpeggiator runs (0: its notes, 1: the keys held). Version 3 (M8a's), 40 bytes, its last byte the knobs' mode (0: the macros, 1: direct), is read as version 4 with 120 beats a minute and the arpeggiator's notes; version 2 (M6b's), the same 40 bytes with that byte 0, likewise with the macros; version 1 (M6a's), 36 bytes, with its defaults for the out channel (1), thru (off), local control (on) and the knobs (the macros) too |
| 4 | a reset | none; version 0. Every record older than it is void |
| 0x80 to 0xFE | kept for firmwares built on the base (since clean-1027) | below |

## Kinds for firmwares built on the base

Kinds 0x80 to 0xFE are kept for firmwares built on small-beeps; the base
itself writes none. Their id is any byte (0 to 255), and their payload,
of up to 5 904 bytes, is written as parts, one record each:

- each part's payload is a 4-byte tag, then up to 492 bytes of the
  payload, in order (so a part's record is at most 512 bytes);
- the record's byte 6 is the part's index (0 first) and byte 7 how many
  parts the payload has; every part of one write has the same count and
  the same tag, the sequence number the store would give the next record
  when the write began;
- a write appends its parts in order.

Reading a payload: of each part (kind, id, index) the newest valid
record counts, as for any key; the payload is whole when part 0 and every
part below its count are there with part 0's tag and count, and then it
is their data in order. Otherwise there is none: a write cut short is
never read as a mix of two writes (the old payload reads until the new
write's first part is whole, then nothing until its last is). At
start-up a part whose tag or count isn't part 0's, or whose index is past
part 0's count, is not live, and is never copied forward; so are the
parts past a shorter payload's count once it is written. A reset voids
these kinds as it voids every other. A reader that knows none of them
(the base before clean-1027) counts them unknown and never copies them
forward.

## Reading

Every valid sector is read whole, in 16-byte steps from offset 16. A block
that is erased is passed over; a block that is neither erased nor the
start of a valid record (its magic, a length that fits, its CRC) is
passed over too and counted. Of the records with the same kind and id,
the one with the highest sequence number counts; then every record older
than the newest reset is void. A record of a kind or id the reader does
not know is counted and otherwise ignored, and never copied forward.

## Writing

A record is appended in the head after its last byte that is not erased,
programmed in one go (a page program for each 256-byte page it touches),
and read back. Nothing written is ever written again: a record replaces
an older one only by being newer.

When the head has no room, the next sector in the ring becomes the head:
it is erased, and its header written with the next sequence number. Then
every record still live in the sector after the new head (the oldest) is
copied into the new head, with a new sequence number, so that sector holds
nothing live by the time the ring comes round to erase it. If a sector
can't be freed without losing a live record, the write is refused and
nothing is written.

## Versions

Version 1 is the first (M7). The kinds for firmwares built on the base
(clean-1027) are an addition to version 1: their records are version 1's
records, and a reader that doesn't know them skips them. A later format changes the sector header's
format byte, and says here what changed; a payload's own version changes
when its layout does, and the reader migrates what it knows.
