#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
"""Phase A1's packager and reference reader of the update package, the
`.fwsc` (docs/A1-PLAN.md, Note A1-1), from docs/HARDWARE-SPEC.md only:
HW-87 to HW-93 and, since BR-17 (clean-br17), section 24 (HW-103 to
HW-108).

  fwsc.py pack APP.bin --version X.Y.Z --out FILE.fwsc [--identity ID]
      The full image, for the emulated load paths (fwtest's --package,
      the emulators, the F-Emulator app): packs the package link's raw
      image (tools/build.sh's app-pkg.bin, linked at 0x02000120, HW-91)
      into a package with one entry, the flash image from flash 0: its
      flash header, a directory (the key block's head, the app area's,
      key_mac's), our own key block, and the app area at flash 0x4000
      with app.bin at 0x120 in it, scrambled with the key the key block
      gives (HW-88 to HW-90, HW-104, HW-105). Never for a unit: it writes
      the boot area (0x0-0x3FFF), where a unit keeps its loader.
  fwsc.py pack APP.bin --app-area --key 0xFFFF|0x980F --version X.Y.Z
               --out FILE.fwsc [--identity ID] [--hardware]
      The app area alone (BR-17): one entry holding the flash image's
      bytes from 0x4000 only (the area head, the area's directory and
      app.bin, scrambled with KEY), nothing below 0x4000: no flash
      header, no directory, no key block. The key is given, as no key
      block travels with the area: 0xFFFF, the tools' key without a key
      file (HW-105, HW-108), or 0x980F, the stock package's (HW-90). With
      --hardware it refuses (exit 2) while any field a unit needs is open,
      naming each; today it always refuses.
  fwsc.py FILE.fwsc [--unpack DIR]
      Runs fwtest's checks on a full-image package, in fwtest's order
      (docs/HARNESS.md, "Packages"; HW-93), then section 24's fields
      (fields()), and prints what it found or the first check that failed
      (exit 1); --unpack writes the app (app.bin) and the flash image
      (flash.bin).
  fwsc.py FILE.fwsc --app-area --key KEY
      Reads an app-area package (check_app_area()): section 24's fields,
      and nothing in it placed below 0x4000.
  fwsc.py broken APP.bin --out DIR
      Writes one broken package per check, DIR/<check>-<what>.fwsc, each
      failing that check and passing those before it (the tests').

The same inputs give the same bytes (R-REPRO). Every pack prints the
fields the spec leaves open (OPEN: Q-25, Q-26 and SR-12), and what it
writes for each.

Section 24's fields (HW-104, HW-105), written as JieLi's tools write
them: in the header, the list CRC (over the entry list as stored, masked,
from logical offset 64, the block markers taken out), the image size (the
logical image's length: the file's less 20), the entry count and the
chip's name; in the entry, its type, index, data CRC (of the flash image
as written to flash), offset (a multiple of 32: flash.bin's at 0x400, as
the tools put it), length, rounded length and name (flash.bin); the flash
header's fields with the FM-1's configuration, its VID and PID plain on
flash; in each head its CRC, data CRC, attribute, reserved byte, "last",
and its name ended by one zero byte and padded with 0xFF; the area head
named app_area_head, its offset the entry (0x02000120), attribute 0x83.
The reader matches names up to their first zero byte (HW-105).

What stays ours: the key block (any key block gives a key, HW-90; ours is
not the FM-1's, Q-26) and its place (0x80, right after the directory: no
loader comes before it); the key block's head's data, the key block and
its CRC (34 bytes), where the tools write a 765-byte binary configuration
that starts with them (its rest is not given); the directory has no
uboot.boot (no loader is in the package, HW-92, HW-93; docs/A1-PLAN.md,
"Loaders"), and the area's directory only app.bin (the tools add
cfg_tool.bin and the VM, PRCT and BTIF regions), padded with zero bytes to
0x120. The flash image covers the boot area and the app area only, so a
package writes nothing past the app area's end: not the stock user patch
region (0xEA000, HW-80), not the store (by default at 0xFC000; a
firmware's own region lies after its image, past the area's end too,
R-STORE-12).
"""

import argparse
import hashlib
import os
import struct
import sys

# HW-88: the header blocks, the logical header, the entries.
BLOCKS, BLOCK, BLOCK_DATA = 20, 48, 47
HEADER_FILE = BLOCKS * BLOCK                # 960 bytes of blocks
LOGICAL = BLOCKS * BLOCK_DATA               # 940 bytes of logical header
SHIFT = HEADER_FILE - LOGICAL               # logical n is file n + 20, n >= 940
END_MARK = 0x7D
HEADER_SIZE, ENTRY_SIZE = 64, 80
ENTRY_FLASH = 0
OTHER_BOARDS = ("SMK", "MKE", "STARRYKEY")  # an identity starting so is another board's
IDENTITY_MAX = 19
# HW-104: the header's and the entry's fields. The flash image's data
# starts at logical offset 0x400, as the tools put flash.bin: file offset
# 1044, past the header blocks with zero bytes between, so the byte at
# file offset 1007 (where a 21st block's marker would sit, HW-88) is 0,
# not 0x7D, and no reader tries a longer header first.
DATA_LOGICAL = 0x400
DATA_FILE = DATA_LOGICAL + 20               # SHIFT, below
DATA_ALIGN = 32                             # every entry's data on a multiple of 32
CHIP_NAME = b"AC791N"                       # header bytes 16-31, the configuration's CHIP_NAME
ENTRY_NAME = b"flash.bin"

# HW-87: the header key, the mask's seed.
HEADER_KEY = 0xFFFF

# HW-89, HW-105: the flash image's heads.
HEAD = struct.Struct("<HHIIBBH16s")         # hdrcrc, datacrc, offset, length, attr, reserved, last, name
FLASH_HEAD = struct.Struct("<HH4sIBBBB16s")  # crc, size4burner, VID, flash size, fs version, align, reserved, options, PID
# HW-105: the flash header with the FM-1's configuration. The VID (bytes
# 4-7) and the PID (16-31) read as plain ASCII on flash; the rest is masked.
FLASH_FIELDS = dict(size4burner=0x8020, vid=b"0.01", flash_size=0xFF000, fs_version=0x10, align=0x10,
                    reserved=0xA4, options=0xFF, pid=b"AC791N_STORY".ljust(16, b"\xff"))
PLAIN_ON_FLASH = tuple(range(4, 8)) + tuple(range(16, 32))
KEY_NAME, KEY_ATTR, KEY_RESERVED = b"isd_config.ini", 2, 0x80
AREA_NAME, AREA_ATTR = b"app_dir_head", 0x81
KEY_MAC = (b"key_mac", 0xFF000, 0x1000, 0x12, 1)   # name, offset, length, attribute, reserved (HW-105)
NO_CRC = 0xFFFF                             # the data CRC of a head that names a region, not data
KEY_BLOCK_AT = 0x80                         # right after the directory's four heads

# HW-90, HW-91: the app area, its directory, the app.
AREA = 0x4000
DIR_SIZE = 0x120                            # the area head and eight heads: the SDK's directory
APP_NAME, APP_ATTR = b"app.bin", 0x82
AREA_HEAD_NAME, AREA_HEAD_ATTR = b"app_area_head", 0x83     # HW-105
KEYS = {0xFFFF: "the tools' key without a key file (HW-105, HW-108)",
        0x980F: "the stock package's key (HW-90)"}
WINDOW = 0x02000000
ENTRY = WINDOW + DIR_SIZE                   # 0x02000120, where the package link puts the app
USER_REGION = 0xEA000                       # the stock user patch region (HW-80): the app area ends before it
CHUNK = 32

# Our own key block (HW-89, HW-90): 32 bytes, any of which gives a key.
# The FM-1's own key is unknown (Q-26); the emulated load paths take any
# key the area is scrambled with.
KEY_BLOCK = hashlib.sha256(b"small-beeps key block 1").digest()

# What a pack leaves to the spec (printed by every pack): (question, what,
# what we write), and for which mode. A hardware pack refuses while any of
# its own is open.
OPEN = [
    ("Q-25", "the package header's bytes 10-15 (the tools write 4 and 0x200, meaning not known)", "0",
     ("full", "app-area")),
    ("Q-25", "the 64 bytes the tools write after the app area", "not written", ("full", "app-area")),
    ("Q-25", "which program adds a .fwsc's 48-byte header blocks and their markers (HW-107)",
     "the blocks, by HW-88", ("full", "app-area")),
    ("Q-25", "isd_config.ini's binary configuration past the key block and its CRC (765 bytes, HW-105)",
     "the key block and its CRC only", ("full",)),
    ("Q-26", "which of blimit.bin, info.log, ota.bin, script.ver, tail.bin and isd_config.ini an installer needs",
     "flash.bin alone (the owner's answer 1, clean-br17)", ("full", "app-area")),
    ("Q-26", "the chip key a unit runs (HW-108): 0xFFFF, its stock 0x980F, or its own",
     "our key block's in the full image; the given key in the app area", ("full", "app-area")),
    ("Q-26", "which CRCs a loader or an installer checks", "every CRC section 24 defines", ("full", "app-area")),
    ("SR-12", "where an installer writes a .fwsc entry's data: by HW-89 a flash.bin entry goes from flash 0, "
     "and no field places it at 0x4000", "flash.bin, taken to go at 0x4000 (our reading)", ("app-area",)),
]


def _crc_table():
    t = []
    for x in range(256):
        c = x << 8
        for _ in range(8):
            c = ((c << 1) ^ 0x1021) & 0xFFFF if c & 0x8000 else (c << 1) & 0xFFFF
        t.append(c)
    return t


JIELI_CRC_TABLE = _crc_table()


def jieli_crc(b, crc=0):
    """JieLi's CRC-16 (HW-87): polynomial 0x1021, from 0, MSB first."""
    for x in b:
        crc = ((crc << 8) & 0xFFFF) ^ JIELI_CRC_TABLE[(crc >> 8) ^ x]
    return crc


def mask(b, seed):
    """The mask (HW-87); its own inverse."""
    k, out = seed & 0xFFFF, bytearray(len(b))
    for i, x in enumerate(b):
        out[i] = x ^ (k & 0xFF)
        k = ((k << 1) & 0xFFFF) ^ (0x1021 if k & 0x8000 else 0)
    return bytes(out)


def key_from_block(kb):
    """The chip key from a key block's 32 bytes (HW-90)."""
    s = sum(kb[:16]) % 256
    s = 0xAA if s >= 0xE0 else 0x55 if s <= 0x10 else s
    return sum(1 << i for i in range(16) if kb[16 + i] ^ kb[15 - i] < s)


def scramble(area, key):
    """The app area's scrambling (HW-90), chunk by chunk; its own inverse."""
    return b"".join(mask(area[r:r + CHUNK], key ^ (r // 4)) for r in range(0, len(area), CHUNK))


def head_name(name):
    """A head's name: ASCII, one zero byte, then 0xFF (HW-105)."""
    return (name + b"\0").ljust(16, b"\xff")


def name_of(field):
    """A head's name as the readers match it: up to its first zero byte
    (HW-105)."""
    return field.split(b"\0", 1)[0]


def head(name, offset, length, data=None, attr=0, last=0, reserved=0, data_crc=None):
    """A directory head (HW-89, HW-105), unmasked, its CRCs filled: its
    data CRC over data, or data_crc for one that names a region."""
    b = HEAD.pack(0, jieli_crc(data) if data_crc is None else data_crc, offset, length, attr, reserved, last,
                  head_name(name))
    return struct.pack("<H", jieli_crc(b[2:])) + b[2:]


def with_crc(b):
    """A structure whose CRC-16 sits in its first two bytes (HW-87)."""
    return struct.pack("<H", jieli_crc(b[2:])) + b[2:]


def identity_problems(identity):
    p = []
    if not identity or len(identity) > IDENTITY_MAX or not all(0x20 < ord(c) < 0x7F for c in identity):
        p.append("identity %r: not 1 to %d printable ASCII characters" % (identity, IDENTITY_MAX))
    elif identity.upper().startswith(OTHER_BOARDS):
        p.append("identity %r: another board's (it starts with %s)" % (identity, "/".join(OTHER_BOARDS)))
    elif any((ord(c) + i + 1) % 256 == END_MARK for i, c in enumerate(identity)):
        p.append("identity %r: a character would make its marker 0x7D, the markers' end" % identity)
    return p


def round_up(n, to=DATA_ALIGN):
    return (n + to - 1) // to * to


def flash_header():
    """The flash header as stored (HW-89, HW-105): its CRC over the head
    unmasked whole, in which the VID and the PID, plain on flash, read
    masked."""
    f = FLASH_FIELDS
    plain = FLASH_HEAD.pack(0, f["size4burner"], f["vid"], f["flash_size"], f["fs_version"], f["align"],
                            f["reserved"], f["options"], f["pid"])
    m = mask(bytes(32), HEADER_KEY)
    u = bytearray(plain)
    for i in PLAIN_ON_FLASH:
        u[i] ^= m[i]
    return mask(with_crc(bytes(u)), HEADER_KEY)


def app_area(app, key):
    """The app area as stored (HW-90, HW-105): the area head, its
    directory (app.bin alone) and the app, scrambled with key."""
    app_head = head(APP_NAME, DIR_SIZE, len(app), app, APP_ATTR, last=1)
    rest = app_head.ljust(DIR_SIZE - CHUNK, b"\0") + app
    area_len = CHUNK + len(rest)
    area_head = head(AREA_HEAD_NAME, ENTRY, area_len, rest, AREA_HEAD_ATTR, reserved=0xFF)
    return scramble(area_head + rest, key)


def flash_image(app, key_block=KEY_BLOCK, area=AREA):
    """The flash image (HW-89, HW-90, HW-105): boot area, then the app
    area."""
    stored = app_area(app, key_from_block(key_block))
    kb = key_block + struct.pack("<H", jieli_crc(key_block))
    d1 = head(KEY_NAME, KEY_BLOCK_AT, len(kb), kb, KEY_ATTR, reserved=KEY_RESERVED)
    d2 = head(AREA_NAME, area, 0xFFFFFFFF, attr=AREA_ATTR, reserved=0xFF, data_crc=NO_CRC)
    name, off, length, attr, reserved = KEY_MAC
    d3 = head(name, off, length, attr=attr, reserved=reserved, last=0xFFFF, data_crc=NO_CRC)
    boot = flash_header() + b"".join(mask(h, HEADER_KEY) for h in (d1, d2, d3)) + kb
    return boot.ljust(area, b"\xff") + stored


def package(data, identity):
    """A package (HW-88, HW-104) with one entry, flash.bin, holding data."""
    entry = bytearray(ENTRY_SIZE)
    struct.pack_into("<HHH", entry, 0, ENTRY_FLASH, 0, jieli_crc(data))
    struct.pack_into("<III", entry, 8, DATA_LOGICAL, len(data), round_up(len(data)))
    entry[64:64 + len(ENTRY_NAME)] = ENTRY_NAME
    entries = mask(bytes(entry), HEADER_KEY)
    hdr = bytearray(HEADER_SIZE)
    struct.pack_into("<HIH", hdr, 2, jieli_crc(entries), DATA_LOGICAL + len(data), 1)
    hdr[16:16 + len(CHIP_NAME)] = CHIP_NAME
    logical = (mask(with_crc(bytes(hdr)), HEADER_KEY) + entries).ljust(LOGICAL, b"\0")
    blocks = bytearray()
    for i in range(BLOCKS):
        mark = (ord(identity[i]) + i + 1) % 256 if i < len(identity) else END_MARK
        blocks += logical[BLOCK_DATA * i:BLOCK_DATA * (i + 1)] + bytes([mark])
    return bytes(blocks).ljust(DATA_FILE, b"\0") + data


def pack_problems(app, identity, area=AREA):
    p = identity_problems(identity)
    if area + DIR_SIZE + len(app) > USER_REGION:
        p.append("the app (%d bytes) would run into the stock user patch region at 0x%X" % (len(app), USER_REGION))
    if not app:
        p.append("no app")
    return p


def pack(app, identity, area=AREA):
    """The full image (for the emulated load paths): a package holding
    the flash image from flash 0 as its one entry."""
    p = pack_problems(app, identity, area)
    if p:
        raise ValueError("; ".join(p))
    return package(flash_image(app, area=area), identity)


def pack_app_area(app, identity, key):
    """The app area alone (BR-17): a package whose one entry holds the
    flash image's bytes from 0x4000, scrambled with key; nothing below
    0x4000."""
    p = pack_problems(app, identity)
    if key not in KEYS:
        p.append("key 0x%04X: not one the spec gives (%s)" % (key, ", ".join("0x%04X" % k for k in KEYS)))
    if p:
        raise ValueError("; ".join(p))
    blob = package(app_area(app, key), identity)
    p = below_area(blob, key)
    if p:
        raise ValueError("; ".join(p))
    return blob


def open_fields(mode):
    """OPEN's entries for a mode ("full" or "app-area")."""
    return [(q, what, ours) for q, what, ours, modes in OPEN if mode in modes]


def check(blob):
    """fwtest's checks on a package, in its order (docs/HARNESS.md,
    "Packages"): a dict of what was found, or ValueError naming the first
    that failed, by its number and then fwtest's own words (what it prints
    after "the package is refused: ", seen in its outputs;
    tools/package_suite.py checks the two agree)."""
    # 1. The header's CRC.
    if len(blob) < HEADER_FILE:
        raise ValueError("1: too short for an FM-1 update package (.fwsc)")
    logical = b"".join(blob[BLOCK * i:BLOCK * i + BLOCK_DATA] for i in range(BLOCKS))
    hdr = mask(logical[:HEADER_SIZE], HEADER_KEY)
    if struct.unpack_from("<H", hdr)[0] != jieli_crc(hdr[2:]):
        raise ValueError("1: not an FM-1 update package (.fwsc)")
    # The identity: every marker read back, less the trailing run of 0x7D
    # (fwtest's reading, seen in its outputs: a 0x7D marker before another
    # character is read as a character).
    marks = [blob[BLOCK * i + BLOCK_DATA] for i in range(BLOCKS)]
    while marks and marks[-1] == END_MARK:
        marks.pop()
    identity = "".join(chr((m - i - 1) % 256) for i, m in enumerate(marks))
    # 2. A flash image entry inside the file.
    count = struct.unpack_from("<H", hdr, 8)[0]
    fi = None
    for k in range(count):
        at = HEADER_SIZE + ENTRY_SIZE * k
        if at + ENTRY_SIZE > LOGICAL:
            break
        e = mask(logical[at:at + ENTRY_SIZE], HEADER_KEY)
        etype, off, length = struct.unpack_from("<H", e)[0], *struct.unpack_from("<II", e, 8)
        if etype == ENTRY_FLASH:
            if off < LOGICAL or off + SHIFT + length > len(blob):
                raise ValueError("2: truncated package")
            fi = blob[off + SHIFT:off + SHIFT + length]
            break
    if fi is None:
        raise ValueError("2: no flash image in the package")
    # 3. A key block and an app area in the directory.
    keys, area_head = [], None
    at = 32
    while at + 32 <= len(fi):
        h = HEAD.unpack(mask(fi[at:at + 32], HEADER_KEY))
        name = name_of(h[7])
        if name == KEY_NAME:
            keys.append(h)
        elif name == AREA_NAME and h[4] == AREA_ATTR and area_head is None:
            area_head = h
        if h[6]:
            break
        at += 32
    if not keys or area_head is None:
        raise ValueError("3: no chip key or app area in the flash image")
    good = [h for h in keys if h[2] + 34 <= len(fi)
            and struct.unpack_from("<H", fi, h[2] + 32)[0] == jieli_crc(fi[h[2]:h[2] + 32])]
    kh = good[0] if good else keys[-1]
    kb = fi[kh[2]:kh[2] + 32].ljust(32, b"\0")
    key = key_from_block(kb)
    # 4. The app area inside the flash image.
    a = area_head[2]
    if a + CHUNK > len(fi):
        raise ValueError("4: app area runs past the flash image")
    alen = HEAD.unpack(mask(fi[a:a + CHUNK], key))[3]
    if alen < CHUNK or a + alen > len(fi):
        raise ValueError("4: app area runs past the flash image")
    area = scramble(fi[a:a + alen], key)
    # 5. An app.bin in the area.
    app = None
    at = CHUNK
    while at + 32 <= len(area):
        h = HEAD.unpack(area[at:at + 32])
        if name_of(h[7]) == APP_NAME:
            app = h
            break
        if h[6]:
            break
        at += 32
    if app is None or app[3] == 0 or app[2] + app[3] > len(area):
        raise ValueError("5: no app.bin in the app area")
    # 6. A key block whose CRC checks.
    if not good:
        raise ValueError("6: no isd_config.ini key block's CRC checks")
    # 7. The app area at flash 0x4000.
    if a != AREA:
        raise ValueError("7: its app area starts at flash 0x%X, not 0x%X" % (a, AREA))
    # 8. app.bin's attribute.
    if app[4] != APP_ATTR:
        raise ValueError("8: app.bin's attribute is 0x%02X, not 0x%02X" % (app[4], APP_ATTR))
    # 9. Not another board's identity.
    if identity.upper().startswith(OTHER_BOARDS):
        raise ValueError("9: its identity \"%s\" is another board's" % identity)
    return {"identity": identity, "area": a, "entry": WINDOW + app[2], "key": key,
            "app": area[app[2]:app[2] + app[3]], "flash": fi}


def logical_image(blob):
    """The logical image (HW-88): the header blocks' data, then the file
    from offset 960."""
    return b"".join(blob[BLOCK * i:BLOCK * i + BLOCK_DATA] for i in range(BLOCKS)) + blob[HEADER_FILE:]


def entries(blob):
    """(header unmasked, [entries unmasked], problems): section 24's
    header and entry fields (HW-104) checked."""
    p, lg = [], logical_image(blob)
    hdr = mask(lg[:HEADER_SIZE], HEADER_KEY)
    crc, list_crc, size, count = struct.unpack_from("<HHIH", hdr)
    if crc != jieli_crc(hdr[2:]):
        p.append("the header's CRC")
    stored = lg[HEADER_SIZE:HEADER_SIZE + ENTRY_SIZE * count]
    if list_crc != jieli_crc(stored):
        p.append("the list CRC is 0x%04X, the entry list's 0x%04X" % (list_crc, jieli_crc(stored)))
    if size != len(lg):
        p.append("the image size is %d, the logical image's %d" % (size, len(lg)))
    if hdr[16:32] != CHIP_NAME.ljust(16, b"\0"):
        p.append("the chip's name is %r" % hdr[16:32])
    es = []
    for k in range(count):
        e = mask(stored[ENTRY_SIZE * k:ENTRY_SIZE * (k + 1)], HEADER_KEY)
        etype, index, dcrc = struct.unpack_from("<HHH", e)
        off, length, rounded = struct.unpack_from("<III", e, 8)
        data = lg[off:off + length]
        if index != k:
            p.append("entry %d: its index is %d" % (k, index))
        if off % DATA_ALIGN or len(data) != length:
            p.append("entry %d: its data at %d (%d bytes) is not on a multiple of 32 inside the file" % (k, off, length))
        elif dcrc != jieli_crc(data):
            p.append("entry %d: its data CRC is 0x%04X, its data's 0x%04X" % (k, dcrc, jieli_crc(data)))
        if rounded != round_up(length):
            p.append("entry %d: its rounded length is %d, not %d" % (k, rounded, round_up(length)))
        es.append((etype, name_of(e[64:80]), data))
    return hdr, es, p


def head_problems(where, h, raw, data=None):
    """A head's CRC (over raw, unmasked) and, given its data, its data
    CRC."""
    p = []
    if struct.unpack_from("<H", raw)[0] != jieli_crc(raw[2:]):
        p.append("%s: its head's CRC" % where)
    if data is not None and h[1] != jieli_crc(data):
        p.append("%s: its data CRC" % where)
    return p


def area_problems(area):
    """The app area's heads, unscrambled (HW-90, HW-105): the area head's
    CRC, data CRC, offset, attribute and name; each head of its directory
    and its data's CRC."""
    ah = HEAD.unpack(area[:32])
    p = head_problems("the area head", ah, area[:32], area[32:ah[3]])
    if (name_of(ah[7]), ah[2], ah[4]) != (AREA_HEAD_NAME, ENTRY, AREA_HEAD_ATTR):
        p.append("the area head: %r at 0x%08X, attribute 0x%02X" % (name_of(ah[7]), ah[2], ah[4]))
    at = CHUNK
    while at + 32 <= min(len(area), DIR_SIZE):
        h = HEAD.unpack(area[at:at + 32])
        p += head_problems(name_of(h[7]).decode("ascii", "replace"), h, area[at:at + 32],
                           area[h[2]:h[2] + h[3]] if h[4] == APP_ATTR else None)
        if h[6]:
            break
        at += 32
    return p


def fields(blob):
    """Problems with section 24's fields in a full-image package (HW-104,
    HW-105): the header's and the entry's, the flash header's, every head's
    and its data's CRC. check() first."""
    r = check(blob)
    hdr, es, p = entries(blob)
    fi = r["flash"]
    if es[0][1] != ENTRY_NAME:
        p.append("the entry's name is %r" % es[0][1])
    u = mask(fi[:32], HEADER_KEY)
    if struct.unpack_from("<H", u)[0] != jieli_crc(u[2:]):
        p.append("the flash header's CRC")
    f = FLASH_FIELDS
    if fi[4:8] != f["vid"] or fi[16:32] != f["pid"]:
        p.append("the flash header's VID or PID is not plain on flash")
    at = 32
    while at + 32 <= len(fi):
        raw = mask(fi[at:at + 32], HEADER_KEY)
        h = HEAD.unpack(raw)
        data = fi[h[2]:h[2] + h[3]] if h[1] != NO_CRC else None
        p += head_problems(name_of(h[7]).decode("ascii", "replace"), h, raw, data)
        if h[7][len(name_of(h[7])):] != b"\0".ljust(16 - len(name_of(h[7])), b"\xff"):
            p.append("%r: its name is not ended by one zero byte and 0xFF" % name_of(h[7]))
        if h[6]:
            break
        at += 32
    return p + area_problems(scramble(fi[r["area"]:], r["key"]))


def check_app_area(blob, key):
    """An app-area package's reading (BR-17): section 24's header and
    entry fields, its one entry flash.bin taken to go at flash 0x4000
    (SR-12: no field places it), the area under key: its heads, CRCs and
    app. A dict like check()'s, or ValueError naming what failed, below
    0x4000 first (below_area())."""
    p = below_area(blob, key)
    if p:
        raise ValueError("; ".join(p))
    hdr, es, p = entries(blob)
    area = scramble(es[0][2], key)
    p += area_problems(area)
    if p:
        raise ValueError("; ".join(p))
    app = HEAD.unpack(area[CHUNK:2 * CHUNK])
    return {"area": AREA, "entry": WINDOW + app[2], "key": key, "app": area[app[2]:app[2] + app[3]]}


def below_area(blob, key):
    """Problems if anything in an app-area package reaches below flash
    0x4000 (BR-17, R-PKG-3), read as this reader reads it: a package
    whose entries are flash.bin alone, its data taken to go at 0x4000
    (our reading, SR-12); no flash header in it (a flash image from 0
    would bring the boot area); an area head first, under key; and no
    head in the area's directory naming a region below 0x4000."""
    try:
        hdr, es, p = entries(blob)
    except struct.error:
        return ["not a package"]
    if hdr[:2] != struct.pack("<H", jieli_crc(hdr[2:])):
        return ["not a package (the header's CRC)"]
    if [(t, n) for t, n, _ in es] != [(ENTRY_FLASH, ENTRY_NAME)]:
        p.append("entries %s: only flash.bin, which goes at 0x%X" % ([(t, n.decode("ascii", "replace")) for t, n, _ in es],
                                                                    AREA))
        return p
    data = es[0][2]
    try:
        check(blob)
        p.append("its flash.bin is a flash image from 0 (a flash header and directory): it writes 0x0-0x3FFF")
    except ValueError:
        pass
    if len(data) < 2 * CHUNK:
        return p + ["its flash.bin is too short for an area head"]
    area = scramble(data, key)
    ah = HEAD.unpack(area[:32])
    if name_of(ah[7]) != AREA_HEAD_NAME or ah[3] != len(data):
        p.append("its flash.bin does not start with the app area's head under key 0x%04X" % key)
        return p
    at = CHUNK
    while at + 32 <= min(len(area), DIR_SIZE):
        h = HEAD.unpack(area[at:at + 32])
        # app.bin's offset is from the area's start; a region's is a flash
        # offset (HW-90).
        start = AREA + h[2] if h[4] == APP_ATTR else h[2]
        if start < AREA:
            p.append("%r reaches 0x%X, below 0x%X" % (name_of(h[7]), start, AREA))
        if h[6]:
            break
        at += 32
    return p


# Broken packages for the tests (tests/test_fwsc.py, tools/package_suite.py):
# one per check fwtest makes, each failing that check and passing those
# before it.
def _relogical(blob, edit):
    b = bytearray(blob)
    logical = bytearray(b"".join(b[BLOCK * i:BLOCK * i + BLOCK_DATA] for i in range(BLOCKS)))
    hdr, ent = bytearray(mask(logical[:64], HEADER_KEY)), bytearray(mask(logical[64:144], HEADER_KEY))
    edit(hdr, ent)
    logical[:64], logical[64:144] = mask(bytes(hdr), HEADER_KEY), mask(bytes(ent), HEADER_KEY)
    for i in range(BLOCKS):
        b[BLOCK * i:BLOCK * i + BLOCK_DATA] = logical[BLOCK_DATA * i:BLOCK_DATA * (i + 1)]
    return bytes(b)


def _flash_head(blob, at, edit):
    b = bytearray(blob)
    o = DATA_FILE + at
    h = bytearray(mask(b[o:o + 32], HEADER_KEY))
    edit(h)
    b[o:o + 32] = mask(bytes(h), HEADER_KEY)
    return bytes(b)


def _area(blob, edit):
    b = bytearray(blob)
    o, key = DATA_FILE + AREA, key_from_block(KEY_BLOCK)
    area = bytearray(scramble(b[o:], key))
    edit(area)
    b[o:] = scramble(bytes(area), key)
    return bytes(b)


def _set(b, at, value):
    b[at:at + len(value)] = value


def broken(app, identity="small-beeps-0.0.0"):
    """(check, label, package) for each of fwtest's checks."""
    good = pack(app, identity)

    def crc_off(h, e):
        h[2] ^= 1

    def no_flash(h, e):
        e[0] = 1

    def past_end(h, e):
        struct.pack_into("<I", e, 12, len(good))

    kcrc = bytearray(good)
    kcrc[DATA_FILE + KEY_BLOCK_AT + 32] ^= 1
    other = bytearray(good)
    for i in range(BLOCKS):
        other[BLOCK * i + BLOCK_DATA] = (ord("SMK-37"[i]) + i + 1) % 256 if i < 6 else END_MARK
    return [
        (1, "short", good[:HEADER_FILE - 60]),
        (1, "header-crc", _relogical(good, crc_off)),
        (2, "no-flash-image", _relogical(good, lambda h, e: (no_flash(h, e), _set(h, 0, struct.pack("<H", jieli_crc(bytes(h[2:]))))))),
        (2, "truncated", _relogical(good, lambda h, e: past_end(h, e))),
        (3, "no-key-block", _flash_head(good, 32, lambda h: _set(h, 16, b"isd_config.txt\0\0"))),
        (3, "no-app-area", _flash_head(good, 64, lambda h: _set(h, 12, b"\x80"))),
        (4, "area-too-long", _area(good, lambda a: struct.pack_into("<I", a, 8, len(a) + CHUNK))),
        (5, "no-app-bin", _area(good, lambda a: _set(a, CHUNK + 16, APP_NAME.replace(b"bin", b"elf")))),
        (6, "key-block-crc", bytes(kcrc)),
        (7, "area-not-at-0x4000", pack(app, identity, area=0x5000)),
        (8, "app-attribute", _area(good, lambda a: _set(a, CHUNK + 12, b"\x83"))),
        (9, "other-board", bytes(other)),
    ]


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "broken":
        ap = argparse.ArgumentParser(prog="fwsc.py broken")
        ap.add_argument("app")
        ap.add_argument("--out", required=True)
        a = ap.parse_args(sys.argv[2:])
        with open(a.app, "rb") as f:
            app = f.read()
        os.makedirs(a.out, exist_ok=True)
        for n, label, blob in broken(app):
            with open(os.path.join(a.out, "%d-%s.fwsc" % (n, label)), "wb") as f:
                f.write(blob)
        return 0
    if len(sys.argv) > 1 and sys.argv[1] == "pack":
        ap = argparse.ArgumentParser(prog="fwsc.py pack")
        ap.add_argument("app")
        ap.add_argument("--version", required=True)
        ap.add_argument("--identity")
        ap.add_argument("--out", required=True)
        ap.add_argument("--app-area", action="store_true", help="the app area alone, nothing below 0x4000")
        ap.add_argument("--key", type=lambda v: int(v, 0), help="the app area's key (--app-area): 0xFFFF or 0x980F")
        ap.add_argument("--hardware", action="store_true", help="refuse while a field a unit needs is open")
        a = ap.parse_args(sys.argv[2:])
        mode = "app-area" if a.app_area else "full"
        if a.key is not None and not a.app_area:
            ap.error("--key goes with --app-area (the full image's key is its key block's)")
        if a.app_area and a.key is None:
            ap.error("--app-area needs --key: %s" % "; ".join("0x%04X, %s" % kv for kv in KEYS.items()))
        if a.hardware:
            why = ["the full image writes the boot area (0x0-0x3FFF), where a unit keeps its loader: "
                   "use --app-area"] if mode == "full" else []
            why += ["%s: %s" % (q, what) for q, what, _ in open_fields(mode)]
            for w in why:
                print("fwsc: hardware: open: %s" % w, file=sys.stderr)
            print("fwsc: hardware: refused, %d open (%s); nothing written" % (
                len(why), ", ".join(sorted(set(w.split(":")[0] for w in why if w[:1] in "QS")))), file=sys.stderr)
            return 2
        with open(a.app, "rb") as f:
            app = f.read()
        identity = a.identity or "small-beeps-" + a.version
        try:
            blob = pack_app_area(app, identity, a.key) if a.app_area else pack(app, identity)
        except ValueError as e:
            print("fwsc: %s" % e, file=sys.stderr)
            return 2
        with open(a.out, "wb") as f:
            f.write(blob)
        print("fwsc: wrote %s (%s%s), %d bytes, SHA-256 %s" % (
            a.out, "the app area alone, key 0x%04X" % a.key if a.app_area else "the full image, for the emulated load paths",
            "" if a.app_area else ", never for a unit", len(blob), hashlib.sha256(blob).hexdigest()))
        for q, what, ours in open_fields(mode):
            print("fwsc: open (%s): %s: %s" % (q, what, ours))
        return 0
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("file")
    ap.add_argument("--unpack")
    ap.add_argument("--app-area", action="store_true")
    ap.add_argument("--key", type=lambda v: int(v, 0))
    a = ap.parse_args()
    with open(a.file, "rb") as f:
        blob = f.read()
    if a.app_area:
        if a.key is None:
            ap.error("--app-area needs --key")
        try:
            r = check_app_area(blob, a.key)
        except ValueError as e:
            print("fwsc: FAIL: %s" % e)
            return 1
        print("fwsc: OK: the app area alone, nothing below 0x%X; entry 0x%08X, key 0x%04X, app %d bytes, SHA-256 %s"
              % (AREA, r["entry"], r["key"], len(r["app"]), hashlib.sha256(r["app"]).hexdigest()))
        return 0
    try:
        r = check(blob)
    except ValueError as e:
        print("fwsc: FAIL at check %s" % e)
        return 1
    p = fields(blob)
    if p:
        print("fwsc: FAIL: section 24's fields: %s" % "; ".join(p))
        return 1
    print("fwsc: OK: identity %s, app area 0x%05X, entry 0x%08X, chip key 0x%04X, app %d bytes, SHA-256 %s"
          % (r["identity"], r["area"], r["entry"], r["key"], len(r["app"]), hashlib.sha256(r["app"]).hexdigest()))
    if a.unpack:
        os.makedirs(a.unpack, exist_ok=True)
        for n in ("app", "flash"):
            with open(os.path.join(a.unpack, n + ".bin"), "wb") as f:
                f.write(r[n])
    return 0


if __name__ == "__main__":
    sys.exit(main())
