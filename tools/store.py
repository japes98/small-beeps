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

Since clean-1027 (BR-9; docs/STORE-FORMAT.md, "Kinds for firmwares built
on the base") kinds FW_KIND_FIRST to FW_KIND_LAST are kept for firmwares
built on the base: a payload of up to FW_MAX bytes, written as up to
FW_PARTS records (its parts), read whole or not at all (Image.get_fw,
Store.put_fw), voided by a reset as every other kind.
"""

import struct
import sys
import zlib

CHIP = 0x100000
BASE = 0xFC000
SIZE = 0x3000
USER_REGION = (0xEA000, 0xFC000)   # the stock firmware's saved patches (HW-80): never touched
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

# Kinds for firmwares built on the base (BR-9; store.h): any id, a payload
# in parts, each part's payload a 4-byte tag (the sequence number of the
# write's first part) and up to PART_DATA bytes of the payload.
FW_KIND_FIRST, FW_KIND_LAST = 0x80, 0xFE
TAG = 4
PART_DATA = 492
PART_MAX = TAG + PART_DATA       # a part's payload: its record is 512 bytes
FW_PARTS = 12
FW_MAX = FW_PARTS * PART_DATA     # 5 904 bytes, more than the region can hold beside anything
FW_KEYS = 32                      # parts the store keeps track of at once


def crc32(b):
    return zlib.crc32(bytes(b)) & 0xFFFFFFFF


def record_size(length):
    return (HEADER + length + 4 + BLOCK - 1) // BLOCK * BLOCK


def fw_kind(kind):
    return FW_KIND_FIRST <= kind <= FW_KIND_LAST


def max_payload(kind):
    return PART_MAX if fw_kind(kind) else MAX_PAYLOAD


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


def record(kind, ident, version, payload, seq, part=0, parts=0):
    body = struct.pack("<BBBBHBBI", RECORD_MAGIC, kind, ident, version, len(payload), part, parts, seq) \
        + bytes(payload)
    return body + struct.pack("<I", crc32(body))


def blank(b):
    return all(x == 0xFF for x in b)


def check_record(b, off, room):
    """(length, problem): the payload's length if the record at off is
    valid; else (None, "skipped" or "crc_bad"), as store.c counts them."""
    p = b[off:off + HEADER]
    length = p[4] | p[5] << 8
    if p[0] != RECORD_MAGIC or length > max_payload(p[1]) or record_size(length) > room:
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
        # The firmware kinds' parts, in the order the firmware keeps them:
        # [kind, id, part, parts, seq, addr, version, payload] or None.
        self.fw = [None] * FW_KEYS
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
            for i, f in enumerate(self.fw):
                if f and f[4] < reset[0]:
                    self.fw[i] = None
                    self.counts["voided"] += 1
        # A part that isn't of its payload's newest write (another tag than
        # part 0's, or past its count) is no longer live.
        for i, f in enumerate(self.fw):
            if f and f[2]:
                head = self.fw_entry(f[0], f[1], 0)
                if not head or head[3] != f[3] or head[7][:TAG] != f[7][:TAG] or f[2] >= f[3]:
                    self.fw[i] = None
                    self.counts["stale"] = self.counts.get("stale", 0) + 1

    def fw_entry(self, kind, ident, part):
        for f in self.fw:
            if f and f[0] == kind and f[1] == ident and f[2] == part:
                return f
        return None

    def _fw_take(self, kind, ident, part, parts, seq, addr, version, payload):
        """Keeps the newest record of a firmware kind's part: 0 if there
        was no place left for a new part."""
        f = self.fw_entry(kind, ident, part)
        if f:
            if seq > f[4]:
                f[3:] = [parts, seq, addr, version, payload]
            return 1
        for i in range(FW_KEYS):
            if self.fw[i] is None:
                self.fw[i] = [kind, ident, part, parts, seq, addr, version, payload]
                return 1
        return 0

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
            _, kind, ident, version, _, part, parts, seq = struct.unpack_from("<BBBBHBBI", b, off)
            payload = b[off + HEADER:off + HEADER + length]
            self.next_seq = max(self.next_seq, seq + 1)
            self.records.append((s, off, seq, kind, ident, version, payload))
            k = key_of(kind, ident)
            if fw_kind(kind):
                if not (part < parts <= FW_PARTS and length >= TAG) \
                        or not self._fw_take(kind, ident, part, parts, seq, BASE + s * SECTOR + off, version, payload):
                    self.counts["unknown"] += 1
            elif k is None:
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

    def get_fw(self, kind, ident):
        """(version, payload) of a firmware kind's payload, whole, or None:
        every part of its newest write, read together."""
        head = self.fw_entry(kind, ident, 0)
        if not head:
            return None
        data = b""
        for part in range(head[3]):
            f = self.fw_entry(kind, ident, part)
            if not f or f[3] != head[3] or f[7][:TAG] != head[7][:TAG]:
                return None
            data += f[7][TAG:]
        return head[6], data

    def live(self):
        return {key_name(k): (e[4], e[5]) for k, e in enumerate(self.keys) if e}


class Store:
    """A flash image the firmware's way: Store().put(...), then .chip()."""

    def __init__(self, chip=None):
        self.data = bytearray(chip) if chip is not None else bytearray(b"\xff" * CHIP)
        img = Image(self.data)
        self.head, self.head_seq, self.append, self.next_seq = img.head, img.head_seq, img.append, img.next_seq
        self.key = [(e[0], e[1]) if e else None for e in img.keys]
        self.fw = [list(f) if f else None for f in img.fw]   # f[4], f[5]: seq, addr
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

    def _append(self, k, kind, ident, version, payload, part=0, parts=0):
        addr = BASE + self.head * SECTOR + self.append
        self.program(addr, record(kind, ident, version, payload, self.next_seq, part, parts))
        if k is None:
            self._fw_set(kind, ident, part, parts, self.next_seq, addr, version, payload)
        else:
            self.key[k] = (self.next_seq, addr)
        self.next_seq += 1
        self.append += record_size(len(payload))

    def _fw_set(self, kind, ident, part, parts, seq, addr, version, payload):
        for f in self.fw:
            if f and f[:3] == [kind, ident, part]:
                f[3:] = [parts, seq, addr, version, payload]
                return
        i = self.fw.index(None)
        self.fw[i] = [kind, ident, part, parts, seq, addr, version, payload]

    def _record_at(self, addr):
        b = self.data
        _, kind, ident, version, length, part, parts, _ = struct.unpack_from("<BBBBHBBI", b, addr)
        return kind, ident, version, bytes(b[addr + HEADER:addr + HEADER + length]), part, parts

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
        for f in self.fw:
            if f and self._sector_of(f[5]) == m:
                kind, ident, version, payload, part, parts = self._record_at(f[5])
                if self.append + record_size(len(payload)) > SECTOR:
                    raise RuntimeError("full")
                self._append(None, kind, ident, version, payload, part, parts)

    def _room(self, size):
        if self.head is None:
            self._open(0)
        self._compact()
        if self.append + size > SECTOR:
            n = self._next()
            if any(e and self._sector_of(e[1]) == n for e in self.key) \
                    or any(f and self._sector_of(f[5]) == n for f in self.fw):
                raise RuntimeError("full")
            self._open(n)
            self._compact()
            if self.append + size > SECTOR:
                raise RuntimeError("full")

    def put(self, kind, ident, version, payload):
        k = key_of(kind, ident)
        self._room(record_size(len(payload)))
        self._append(k, kind, ident, version, payload)

    def put_fw(self, kind, ident, version, data):
        """A firmware kind's payload, in parts, as store.c writes it: each
        part's room made and the part appended, in order; then the parts
        past the new count are no longer live."""
        assert fw_kind(kind) and len(data) <= FW_MAX
        n = max(1, (len(data) + PART_DATA - 1) // PART_DATA)
        tag = None
        for part in range(n):
            chunk = data[part * PART_DATA:(part + 1) * PART_DATA]
            if sum(1 for f in self.fw if f is None) == 0 and not any(
                    f and f[:3] == [kind, ident, part] for f in self.fw):
                raise RuntimeError("full")
            if tag is None:
                tag = self.next_seq
            self._room(record_size(TAG + len(chunk)))
            self._append(None, kind, ident, version, struct.pack("<I", tag) + chunk, part, n)
        for i, f in enumerate(self.fw):
            if f and f[0] == kind and f[1] == ident and f[2] >= n:
                self.fw[i] = None

    def reset(self):
        self.put(RESET, 0, 0, b"")
        self.key = [None] * (SLOTS + 2) + [self.key[SLOTS + 2]]
        self.fw = [None] * FW_KEYS

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
