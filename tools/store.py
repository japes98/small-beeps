#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
"""The store's format (docs/STORE-FORMAT.md; firmware/src/store.c, M7):
reads a flash image as the firmware does, and writes one as the firmware
would, for the tests (tools/fw-suite.py) and for people.

  store.py show FLASH.bin      what the store in a flash image holds

The reader follows store.c's rules exactly: the valid sector with the
highest sequence number is the head; every valid sector is read whole in
16-byte steps; a block that is erased or fails is skipped; of the records
with the same key the newest valid one counts, and a reset voids every
record older than it. The writer (Store) appends the same way, including
the ring's compaction, so an image it makes is one the firmware could
have made; Store.raw_record writes anywhere, for images it never would.
"""

import struct
import sys
import zlib

CHIP = 0x100000
BASE = 0xEA000
SIZE = 0x12000
SECTOR = 4096
SECTORS = SIZE // SECTOR
PAGE = 256
BLOCK = 16
HEADER = 12
MAX_PAYLOAD = 112
SECTOR_MAGIC = 0x31534253
FORMAT = 1
RECORD_MAGIC = 0xA5
CUT_PARAM = 0xE8000            # the power cut test build's two words (store.c)

PATCH, SELECTION, SETTINGS, RESET = 1, 2, 3, 4
SLOTS = 16
KIND_NAMES = {PATCH: "patch", SELECTION: "selection", SETTINGS: "settings", RESET: "reset"}


def crc32(b):
    return zlib.crc32(bytes(b)) & 0xFFFFFFFF


def record_size(length):
    return (HEADER + length + 4 + BLOCK - 1) // BLOCK * BLOCK


def key_of(kind, ident):
    if kind == PATCH:
        return ident if ident < SLOTS else None
    if ident:
        return None
    return {SELECTION: SLOTS, SETTINGS: SLOTS + 1, RESET: SLOTS + 2}.get(kind)


KEYS = SLOTS + 3


def key_name(k):
    return "slot %d" % (k + 1) if k < SLOTS else ("selection", "settings", "reset")[k - SLOTS]


def sector_header(seq):
    h = struct.pack("<IIB3x", SECTOR_MAGIC, seq, FORMAT)
    return h + struct.pack("<I", crc32(h))


def record(kind, ident, version, payload, seq):
    body = struct.pack("<BBBBHHI", RECORD_MAGIC, kind, ident, version, len(payload), 0, seq) + bytes(payload)
    return body + struct.pack("<I", crc32(body))


def blank(b):
    return all(x == 0xFF for x in b)


def check_record(b, off, room):
    """(length, problem): the payload's length if the record at off is
    valid; else (None, "skipped" or "crc_bad"), as store.c counts them."""
    p = b[off:off + HEADER]
    length = p[4] | p[5] << 8
    if p[0] != RECORD_MAGIC or length > MAX_PAYLOAD or record_size(length) > room:
        return None, "skipped"
    body = b[off:off + HEADER + length]
    (crc,) = struct.unpack_from("<I", b, off + HEADER + length)
    return (length, None) if crc32(body) == crc else (None, "crc_bad")


class Image:
    """What the firmware's start-up finds in a flash image (1 MiB, or the
    store's 72 KiB alone)."""

    def __init__(self, data):
        data = bytes(data)
        self.region = data[BASE:BASE + SIZE] if len(data) == CHIP else data
        assert len(self.region) == SIZE, "a 1 MiB chip or the store's 72 KiB"
        self.valid, self.seq = [False] * SECTORS, [0] * SECTORS
        self.head, self.append, self.next_seq = None, 0, 1
        self.counts = {"crc_bad": 0, "skipped": 0, "unknown": 0, "voided": 0}
        self.keys = [None] * KEYS     # (seq, addr, kind, id, version, payload)
        self.records = []             # every valid record: (sector, offset, seq, kind, id, version, payload)
        best = 0
        for s in range(SECTORS):
            h = self.region[s * SECTOR:s * SECTOR + BLOCK]
            magic, seq, fmt = struct.unpack_from("<IIB", h)
            if magic == SECTOR_MAGIC and fmt == FORMAT and crc32(h[:12]) == struct.unpack_from("<I", h, 12)[0]:
                self.valid[s], self.seq[s] = True, seq
                if self.head is None or seq > best:
                    best, self.head = seq, s
        self.head_seq = best
        for s in range(SECTORS):
            if self.valid[s]:
                self._scan(s)
        reset = self.keys[SLOTS + 2]
        if reset:
            for k in range(SLOTS + 2):
                if self.keys[k] and self.keys[k][0] < reset[0]:
                    self.keys[k] = None
                    self.counts["voided"] += 1

    def _scan(self, s):
        b = self.region[s * SECTOR:(s + 1) * SECTOR]
        off = end = BLOCK
        while off + BLOCK <= SECTOR:
            if blank(b[off:off + BLOCK]):
                off += BLOCK
                continue
            length, problem = check_record(b, off, SECTOR - off)
            if length is None:
                self.counts[problem] += 1
                off += BLOCK
                end = off
                continue
            _, kind, ident, version, _, _, seq = struct.unpack_from("<BBBBHHI", b, off)
            payload = b[off + HEADER:off + HEADER + length]
            self.next_seq = max(self.next_seq, seq + 1)
            self.records.append((s, off, seq, kind, ident, version, payload))
            k = key_of(kind, ident)
            if k is None:
                self.counts["unknown"] += 1
            elif self.keys[k] is None or seq > self.keys[k][0]:
                self.keys[k] = (seq, BASE + s * SECTOR + off, kind, ident, version, payload)
            off += record_size(length)
            end = off
        if s == self.head:
            self.append = end

    def get(self, kind, ident=0):
        """(version, payload) of the key's newest valid record, or None."""
        k = key_of(kind, ident)
        e = self.keys[k] if k is not None else None
        return (e[4], e[5]) if e else None

    def live(self):
        return {key_name(k): (e[4], e[5]) for k, e in enumerate(self.keys) if e}


class Store:
    """A flash image the firmware's way: Store().put(...), then .chip()."""

    def __init__(self, chip=None):
        self.data = bytearray(chip) if chip is not None else bytearray(b"\xff" * CHIP)
        img = Image(self.data)
        self.head, self.head_seq, self.append, self.next_seq = img.head, img.head_seq, img.append, img.next_seq
        self.key = [(e[0], e[1]) if e else None for e in img.keys]
        self.erases = [0] * SECTORS
        # Every command, as store.c sends them: ("erase", addr, None) or
        # ("program", addr, bytes), a page program for each page touched.
        self.commands = []

    def chip(self):
        return bytes(self.data)

    # The chip's own rules: an erase sets a sector to 0xFF, a program
    # clears bits only.
    def erase(self, s):
        a = BASE + s * SECTOR
        self.data[a:a + SECTOR] = b"\xff" * SECTOR
        self.erases[s] += 1
        self.commands.append(("erase", a, None))

    def program(self, addr, b):
        b = bytes(b)
        while b:
            k = min(len(b), PAGE - addr % PAGE)
            for i, x in enumerate(b[:k]):
                self.data[addr + i] &= x
            self.commands.append(("program", addr, b[:k]))
            addr, b = addr + k, b[k:]

    def _sector_of(self, addr):
        return (addr - BASE) // SECTOR

    def _open(self, s):
        self.erase(s)
        self.program(BASE + s * SECTOR, sector_header(self.head_seq + 1))
        self.head, self.head_seq, self.append = s, self.head_seq + 1, BLOCK

    def _append(self, k, kind, ident, version, payload):
        addr = BASE + self.head * SECTOR + self.append
        self.program(addr, record(kind, ident, version, payload, self.next_seq))
        self.key[k] = (self.next_seq, addr)
        self.next_seq += 1
        self.append += record_size(len(payload))

    def _next(self):
        return 0 if self.head is None else (self.head + 1) % SECTORS

    def _compact(self):
        m = self._next()
        for k in range(KEYS):
            if self.key[k] and self._sector_of(self.key[k][1]) == m:
                img = Image(self.data)
                e = img.keys[k]
                if self.append + record_size(len(e[5])) > SECTOR:
                    raise RuntimeError("full")
                self._append(k, e[2], e[3], e[4], e[5])

    def put(self, kind, ident, version, payload):
        k = key_of(kind, ident)
        size = record_size(len(payload))
        if self.head is None:
            self._open(0)
        self._compact()
        if self.append + size > SECTOR:
            n = self._next()
            if any(e and self._sector_of(e[1]) == n for e in self.key):
                raise RuntimeError("full")
            self._open(n)
            self._compact()
        self._append(k, kind, ident, version, payload)

    def reset(self):
        self.put(RESET, 0, 0, b"")
        self.key = [None] * (SLOTS + 2) + [self.key[SLOTS + 2]]

    def raw_sector(self, s, seq):
        """Erases sector s and writes its header with seq, whatever the ring."""
        self.erase(s)
        self.program(BASE + s * SECTOR, sector_header(seq))

    def raw_record(self, s, off, kind, ident, version, payload, seq):
        """A record at sector s, offset off, whatever the ring."""
        self.program(BASE + s * SECTOR + off, record(kind, ident, version, payload, seq))


def apply(chip, commands):
    """The chip after these commands (Store.commands), as the chip would be."""
    d = bytearray(chip)
    for kind, addr, b in commands:
        if kind == "erase":
            d[addr:addr + SECTOR] = b"\xff" * SECTOR
        else:
            for j, x in enumerate(b):
                d[addr + j] &= x
    return bytes(d)


def with_cut(chip, after, nbytes=0):
    """The image with the power cut test build's parameters: the cut after
    `after` whole commands, and nbytes of the next page program first."""
    d = bytearray(chip)
    d[CUT_PARAM:CUT_PARAM + 8] = struct.pack("<II", after, nbytes)
    return bytes(d)


def main(argv):
    if len(argv) != 3 or argv[1] != "show":
        print(__doc__.split("\n\n")[1])
        return 2
    with open(argv[2], "rb") as f:
        img = Image(f.read())
    print("head: %s (seq %d), append %d, next seq %d" % (img.head, img.head_seq, img.append, img.next_seq))
    print("valid sectors: %s" % [s for s in range(SECTORS) if img.valid[s]])
    print("counts: %s" % img.counts)
    for name, (version, payload) in img.live().items():
        print("%-10s version %d, %d bytes: %s" % (name, version, len(payload), payload[:16].hex()))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
