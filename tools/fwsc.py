#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
"""Phase A1's packager and reference reader of the update package, the
`.fwsc` (docs/A1-PLAN.md, Note A1-1), from docs/HARDWARE-SPEC.md HW-87 to
HW-93 only.

  fwsc.py pack APP.bin --version X.Y.Z --out FILE.fwsc [--identity ID]
      Packs the package link's raw image (tools/build.sh's app-pkg.bin,
      linked at 0x02000120, HW-91) into a package with one entry, the
      flash image: its flash header, a directory of two heads (the key
      block's and the app area's), our own key block, and the app area at
      flash 0x4000 with app.bin at 0x120 in it, scrambled with the key the
      key block gives (HW-88 to HW-90). The identity (the header blocks'
      markers) is small-beeps-<version> unless given. The same inputs
      give the same bytes (R-REPRO).
  fwsc.py FILE.fwsc [--unpack DIR]
      Runs fwtest's checks on a package, in fwtest's order
      (docs/HARNESS.md, "Packages"; HW-93), and prints what it found or
      the first check that failed (exit 1); --unpack writes the app
      (app.bin) and the flash image (flash.bin).
  fwsc.py broken APP.bin --out DIR
      Writes one broken package per check, DIR/<check>-<what>.fwsc, each
      failing that check and passing those before it (the tests').

What the facts leave open (Q-25, Q-26) the packager writes as 0, and the
reader checks nothing of: in the header, every field but its CRC and the
entry count (the list CRC and the image size: where, and over what, is
not given); in the entry, every field but its type, offset and length
(its name and CRC); in the flash header, the size for the programmer, the
VID, the file system's version, the alignment, the special options and
the PID (the flash size is written, 1 MiB, HW-77); in every directory
head, the reserved byte, and the attribute of the key block's head; in
the area head, every field but its length and its two CRCs. Data CRCs,
which nothing in the three load paths checks (HW-93), are our choice
where the facts don't say over which bytes: the key block's head's over
the key block and its CRC as stored (34 bytes); the app area's head (in
the flash directory) over the area as stored, scrambled; the area head's
over the rest of the area and app.bin's over the app, both plain. The
flash image covers the boot area and the app area only, so a package
writes nothing past the app area's end: not the stock user patch region
(0xEA000, HW-80), not the store (0xFC000). No loader is in it (HW-92,
HW-93; docs/A1-PLAN.md, "Loaders").
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
# Where the flash image starts in the file: past the header blocks, with
# zero bytes between, so the byte at file offset 1007 (where a 21st block's
# marker would sit, HW-88) is 0, not 0x7D, and no reader tries a longer
# header first.
DATA_FILE = 1024

# HW-87: the header key, the mask's seed.
HEADER_KEY = 0xFFFF

# HW-89: the flash image's heads.
HEAD = struct.Struct("<HHIIBBH16s")         # hdrcrc, datacrc, offset, length, attr, reserved, last, name
FLASH_HEAD = struct.Struct("<HH4sIBBBB16s")  # crc, size4burner, VID, flash size, fs version, align, reserved, options, PID
KEY_NAME = b"isd_config.ini"
AREA_NAME, AREA_ATTR = b"app_dir_head", 0x81
FLASH_SIZE = 0x100000                       # the FM-1's 1 MiB flash chip (HW-77)
KEY_BLOCK_AT = 0x60                         # right after the directory's two heads

# HW-90, HW-91: the app area, its directory, the app.
AREA = 0x4000
DIR_SIZE = 0x120                            # the area head and eight heads: the SDK's directory
APP_NAME, APP_ATTR = b"app.bin", 0x82
WINDOW = 0x02000000
ENTRY = WINDOW + DIR_SIZE                   # 0x02000120, where the package link puts the app
USER_REGION = 0xEA000                       # the stock user patch region (HW-80): the app area ends before it
CHUNK = 32

# Our own key block (HW-89, HW-90): 32 bytes, any of which gives a key.
# The FM-1's own key is unknown (Q-26); the emulated load paths take any
# key the area is scrambled with.
KEY_BLOCK = hashlib.sha256(b"small-beeps key block 1").digest()


def _crc_table():
    t = []
    for x in range(256):
        c = x << 8
        for _ in range(8):
            c = ((c << 1) ^ 0x1021) & 0xFFFF if c & 0x8000 else (c << 1) & 0xFFFF
        t.append(c)
    return t


CRC_TABLE = _crc_table()


def crc16(b, crc=0):
    """JieLi's CRC-16 (HW-87): polynomial 0x1021, from 0, MSB first."""
    for x in b:
        crc = ((crc << 8) & 0xFFFF) ^ CRC_TABLE[(crc >> 8) ^ x]
    return crc


def mask(b, seed):
    """The mask (HW-87); its own inverse."""
    k, out = seed & 0xFFFF, bytearray(len(b))
    for i, x in enumerate(b):
        out[i] = x ^ (k & 0xFF)
        k = ((k << 1) & 0xFFFF) ^ (0x1021 if k & 0x8000 else 0)
    return bytes(out)


def chip_key(kb):
    """The chip key from a key block's 32 bytes (HW-90)."""
    s = sum(kb[:16]) % 256
    s = 0xAA if s >= 0xE0 else 0x55 if s <= 0x10 else s
    return sum(1 << i for i in range(16) if kb[16 + i] ^ kb[15 - i] < s)


def scramble(area, key):
    """The app area's scrambling (HW-90), chunk by chunk; its own inverse."""
    return b"".join(mask(area[r:r + CHUNK], key ^ (r // 4)) for r in range(0, len(area), CHUNK))


def head(name, offset, length, data, attr=0, last=0):
    """A directory head (HW-89), unmasked, its CRCs filled."""
    b = HEAD.pack(0, crc16(data), offset, length, attr, 0, last, name)
    return struct.pack("<H", crc16(b[2:])) + b[2:]


def with_crc(b):
    """A structure whose CRC-16 sits in its first two bytes (HW-87)."""
    return struct.pack("<H", crc16(b[2:])) + b[2:]


def identity_problems(identity):
    p = []
    if not identity or len(identity) > IDENTITY_MAX or not all(0x20 < ord(c) < 0x7F for c in identity):
        p.append("identity %r: not 1 to %d printable ASCII characters" % (identity, IDENTITY_MAX))
    elif identity.upper().startswith(OTHER_BOARDS):
        p.append("identity %r: another board's (it starts with %s)" % (identity, "/".join(OTHER_BOARDS)))
    elif any((ord(c) + i + 1) % 256 == END_MARK for i, c in enumerate(identity)):
        p.append("identity %r: a character would make its marker 0x7D, the markers' end" % identity)
    return p


def flash_image(app, key_block=KEY_BLOCK, area=AREA):
    """The flash image (HW-89, HW-90): boot area, then the app area."""
    key = chip_key(key_block)
    app_head = head(APP_NAME, DIR_SIZE, len(app), app, APP_ATTR, last=1)
    rest = app_head.ljust(DIR_SIZE - CHUNK, b"\0") + app
    area_len = CHUNK + len(rest)
    area_head = head(b"", 0, area_len, rest)
    stored = scramble(area_head + rest, key)
    kb = key_block + struct.pack("<H", crc16(key_block))
    flash = with_crc(FLASH_HEAD.pack(0, 0, b"\0" * 4, FLASH_SIZE, 0, 0, 0, 0, b"\0" * 16))
    d1 = head(KEY_NAME, KEY_BLOCK_AT, len(kb), kb)
    d2 = head(AREA_NAME, area, area_len, stored, AREA_ATTR, last=1)
    boot = b"".join(mask(h, HEADER_KEY) for h in (flash, d1, d2)) + kb
    return boot.ljust(area, b"\xff") + stored


def pack(app, identity, area=AREA):
    """A package (HW-88) holding the flash image as its one entry."""
    p = identity_problems(identity)
    if area + DIR_SIZE + len(app) > USER_REGION:
        p.append("the app (%d bytes) would run into the stock user patch region at 0x%X" % (len(app), USER_REGION))
    if not app:
        p.append("no app")
    if p:
        raise ValueError("; ".join(p))
    fi = flash_image(app, area=area)
    hdr = bytearray(HEADER_SIZE)
    struct.pack_into("<H", hdr, 8, 1)
    entry = bytearray(ENTRY_SIZE)
    struct.pack_into("<HII", entry, 0, ENTRY_FLASH, 0, 0)
    struct.pack_into("<II", entry, 8, DATA_FILE - SHIFT, len(fi))
    logical = mask(with_crc(bytes(hdr)), HEADER_KEY) + mask(bytes(entry), HEADER_KEY)
    logical = logical.ljust(LOGICAL, b"\0")
    blocks = bytearray()
    for i in range(BLOCKS):
        mark = (ord(identity[i]) + i + 1) % 256 if i < len(identity) else END_MARK
        blocks += logical[BLOCK_DATA * i:BLOCK_DATA * (i + 1)] + bytes([mark])
    return bytes(blocks).ljust(DATA_FILE, b"\0") + fi


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
    if struct.unpack_from("<H", hdr)[0] != crc16(hdr[2:]):
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
        name = h[7].rstrip(b"\0")
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
            and struct.unpack_from("<H", fi, h[2] + 32)[0] == crc16(fi[h[2]:h[2] + 32])]
    kh = good[0] if good else keys[-1]
    kb = fi[kh[2]:kh[2] + 32].ljust(32, b"\0")
    key = chip_key(kb)
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
        if h[7].rstrip(b"\0") == APP_NAME:
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
    o, key = DATA_FILE + AREA, chip_key(KEY_BLOCK)
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
        (2, "no-flash-image", _relogical(good, lambda h, e: (no_flash(h, e), _set(h, 0, struct.pack("<H", crc16(bytes(h[2:]))))))),
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
        a = ap.parse_args(sys.argv[2:])
        with open(a.app, "rb") as f:
            app = f.read()
        try:
            blob = pack(app, a.identity or "small-beeps-" + a.version)
        except ValueError as e:
            print("fwsc: %s" % e, file=sys.stderr)
            return 2
        with open(a.out, "wb") as f:
            f.write(blob)
        print("fwsc: wrote %s, %d bytes, SHA-256 %s" % (a.out, len(blob), hashlib.sha256(blob).hexdigest()))
        return 0
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("file")
    ap.add_argument("--unpack")
    a = ap.parse_args()
    with open(a.file, "rb") as f:
        blob = f.read()
    try:
        r = check(blob)
    except ValueError as e:
        print("fwsc: FAIL at check %s" % e)
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
