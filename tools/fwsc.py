#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
"""Phase A1's packager and reference reader of the update package, the
`.fwsc` (docs/A1-PLAN.md, Note A1-1), from docs/HARDWARE-SPEC.md only:
HW-87 to HW-93 and, since BR-17 (clean-br17), section 24 (HW-103 to
HW-108) and section 25 (HW-109 to HW-114: what the unit's installer and
bootloader check).

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
  fwsc.py pack APP.bin --hardware --key K --store-base ADDR --version X.Y.Z
               --out FILE.fwsc
      The hardware package (BR-17, round 2), for a unit's installer: the
      flash image from flash 0, as the emulator package but with the app
      area scrambled with K, the unit's own key (HW-111: `m-flasher info`
      shows it; no default), the area's unused head slots 0xFF before
      scrambling (HW-114), and the image padded with 0xFF to the first
      4 KiB boundary at or after the area's end and its 64 trailing bytes
      (HW-114). Its identity is FM-1_<version> (HW-109 step 9). The
      installer writes it from 0x4000 to its end, never the boot area
      (HW-110), so the image must not reach the stock VM region
      (0x94000, HW-80) or the firmware's store region (ADDR, its first
      flash offset: the ELF's sb_store_base; 0xFC000 for the base). It is
      checked with unit_check() before it is written.
  fwsc.py pack APP.bin --ota --key 0xFFFF|0x980F --version X.Y.Z
               --out FILE.ufw [--hardware]
      HW-106's OTA update file (BR-17, round 2): the flash image's bytes
      from 0x4000 only, behind two heads, update_data and app_core, as
      JieLi's tools write db_update_files_data.bin (the SDK's
      update-ota.ufw). No .fwsc blocks, no entry list, no type-0 entry:
      by HW-106 it holds nothing below 0x4000. The unit's installer
      refuses it (no type-0 flash.bin, HW-109 step 7): no more OTA
      candidates for that installer.
  fwsc.py FILE.ufw --ota --key KEY
      Reads an OTA file (check_ota()): both heads' CRCs, the area under
      KEY, nothing below 0x4000.
  fwsc.py FILE.fwsc [--unpack DIR]
      Runs fwtest's checks on a full-image package, in fwtest's order
      (docs/HARNESS.md, "Packages"; HW-93), then section 24's fields
      (fields()), and prints what it found or the first check that failed
      (exit 1); --unpack writes the app (app.bin) and the flash image
      (flash.bin).
  fwsc.py check FILE.fwsc --key K
      The unit's checks (unit_check()): HW-109's installer checks 1 to 11,
      then HW-112's bootloader checks 1 to 3, in that order, stopping at
      the first that fails, with the installer's own words where HW-109
      gives them; then the flash range the installer writes.
  fwsc.py broken APP.bin --out DIR
      Writes one broken package per check, DIR/<check>-<what>.fwsc, each
      failing that check and passing those before it (the tests').

The same inputs give the same bytes (R-REPRO). Every pack prints the
fields the spec leaves open (OPEN: Q-25 and Q-26), and what it writes for
each.

Section 24's fields (HW-104, HW-105), written as JieLi's tools write
them: in the header, the list CRC (over the entry list as stored, masked,
from logical offset 64, the block markers taken out), the image size (the
logical image's length: the file's less 20), the entry count, bytes 10-15
(4 and 0x200, taken from the tools, their meaning open, Q-25) and the
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
cfg_tool.bin and the VM, PRCT and BTIF regions), padded to 0x120 with
zero bytes in the emulator package (as it always was) and with 0xFF in
the hardware package (HW-114). The flash image covers the boot area and the app area only, so a
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
# Header bytes 10-11 and 12-15: 4 and 0x200, as the tools write them in
# every run; their meaning is open (Q-25). Taken from the tools on the
# owner's answer (docs/prompts/clean-br17-answers-3.md); fixed, so the
# same inputs still give the same bytes.
HEADER_TOOL_FIELDS = (4, 0x200)
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

# HW-106: the OTA update file's two heads (HW-89's layout, not masked).
OTA_FILE_HEAD = (b"update_data", 3)          # name, attribute
OTA_CORE_HEAD = (b"app_core", 2)
OTA_TAIL = 64                                # the bytes after the area in app_core's data (Q-25)

# Section 25: the hardware package.
AREA_TRAIL = 64                              # the area's 64 trailing bytes (HW-105, HW-114)
SECTOR = 0x1000                              # the image ends on a 4 KiB boundary (HW-114, HW-109 step 8)
FLASH_BYTES = 0x100000                       # no image longer than the flash (HW-109 step 10)
STOCK_VM = 0x94000                           # the stock VM region's start, past the app area (HW-80)
MODEL = "FM-1"                               # the identity up to its last _ (HW-109 step 9)
AREA_RECORDS = 8                             # at most eight records after the area head (HW-112)
# The installer's own words (HW-109), by step.
INSTALLER = {3: "not a firmware package, or a damaged one (header CRC)",
             5: "damaged firmware package (file list CRC)",
             8: "unexpected flash image size %d",
             11: "does not decrypt with this unit's chip key"}

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
# what we write), and for which mode.
OPEN = [
    ("Q-25", "the meaning of the package header's bytes 10-15",
     "4 and 0x200, taken from the tools (the owner's answer, clean-br17); the installer doesn't read them (HW-109)",
     ("full", "hardware")),
    ("Q-25", "the 64 bytes the tools write after the app area", "not written", ("full",)),
    ("Q-25", "the 64 bytes the tools write after the app area",
     "0xFF, the image's filler (HW-114); neither the installer nor the bootloader checks them", ("hardware",)),
    ("Q-25", "which program adds a .fwsc's 48-byte header blocks and their markers (HW-107)",
     "the blocks, by HW-88 and HW-109 step 2", ("full", "hardware")),
    ("Q-25", "isd_config.ini's binary configuration past the key block and its CRC (765 bytes, HW-105)",
     "the key block and its CRC only, in the boot area, which the installer never writes (HW-110)",
     ("full", "hardware")),
    ("Q-26", "which of blimit.bin, info.log, ota.bin, script.ver, tail.bin and isd_config.ini an installer needs",
     "flash.bin alone (the owner's answer 1, clean-br17; HW-109 needs no other)", ("full",)),
    ("Q-26", "the chip key a unit runs (HW-108)", "our key block's", ("full",)),
    ("Q-25", "the 64 bytes after the area, part of app_core's data and CRC (HW-105, HW-106)",
     "0xFF (our choice)", ("ota",)),
    ("Q-25", "the OTA heads' name padding (HW-106 doesn't say)", "one zero byte, then 0xFF, as HW-105's heads (our choice)",
     ("ota",)),
    ("Q-26", "whether an updater takes the OTA file at all", "the file as HW-106 gives it; the unit's installer "
     "refuses it (HW-109 step 7)", ("ota",)),
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


def app_area(app, key, fill=b"\0"):
    """The app area as stored (HW-90, HW-105): the area head, its
    directory (app.bin alone, the unused slots fill) and the app,
    scrambled with key."""
    app_head = head(APP_NAME, DIR_SIZE, len(app), app, APP_ATTR, last=1)
    rest = app_head.ljust(DIR_SIZE - CHUNK, fill) + app
    area_len = CHUNK + len(rest)
    area_head = head(AREA_HEAD_NAME, ENTRY, area_len, rest, AREA_HEAD_ATTR, reserved=0xFF)
    return scramble(area_head + rest, key)


def flash_image(app, key_block=KEY_BLOCK, area=AREA, key=None, fill=b"\0", length=None):
    """The flash image (HW-89, HW-90, HW-105): boot area, then the app
    area, scrambled with key (the key block's if None), padded with 0xFF
    to length if given."""
    stored = app_area(app, key_from_block(key_block) if key is None else key, fill)
    kb = key_block + struct.pack("<H", jieli_crc(key_block))
    d1 = head(KEY_NAME, KEY_BLOCK_AT, len(kb), kb, KEY_ATTR, reserved=KEY_RESERVED)
    d2 = head(AREA_NAME, area, 0xFFFFFFFF, attr=AREA_ATTR, reserved=0xFF, data_crc=NO_CRC)
    name, off, size, attr, reserved = KEY_MAC
    d3 = head(name, off, size, attr=attr, reserved=reserved, last=0xFFFF, data_crc=NO_CRC)
    boot = flash_header() + b"".join(mask(h, HEADER_KEY) for h in (d1, d2, d3)) + kb
    return (boot.ljust(area, b"\xff") + stored).ljust(length or 0, b"\xff")


def package(data, identity):
    """A package (HW-88, HW-104) with one entry, flash.bin, holding data."""
    entry = bytearray(ENTRY_SIZE)
    struct.pack_into("<HHH", entry, 0, ENTRY_FLASH, 0, jieli_crc(data))
    struct.pack_into("<III", entry, 8, DATA_LOGICAL, len(data), round_up(len(data)))
    entry[64:64 + len(ENTRY_NAME)] = ENTRY_NAME
    entries = mask(bytes(entry), HEADER_KEY)
    hdr = bytearray(HEADER_SIZE)
    struct.pack_into("<HIHHI", hdr, 2, jieli_crc(entries), DATA_LOGICAL + len(data), 1, *HEADER_TOOL_FIELDS)
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


def hardware_identity(version):
    """FM-1_ and the version (HW-109 step 9)."""
    return MODEL + "_" + version


def hardware_length(app):
    """The flash image's length (HW-114): from 0 to the first 4 KiB
    boundary at or after the area's end and its 64 trailing bytes."""
    return round_up(AREA + DIR_SIZE + len(app) + AREA_TRAIL, SECTOR)


def hardware_image(app, key, length=None, fill=b"\xff"):
    return flash_image(app, key=key, fill=fill, length=hardware_length(app) if length is None else length)


def pack_hardware(app, version, key, store_base):
    """The hardware package (BR-17, round 2): one flash.bin from flash 0
    that passes every check of HW-109 and HW-112 under key, the unit's
    own (HW-111)."""
    identity = hardware_identity(version)
    p = pack_problems(app, identity)
    if "_" in version:
        p.append("version %r: no _ in it, or the installer reads the model as %r (HW-109 step 9)"
                 % (version, identity.rsplit("_", 1)[0]))
    if not 0 <= key <= 0xFFFF:
        p.append("key 0x%X: not 16 bits" % key)
    n = hardware_length(app)
    if n > STOCK_VM:
        p.append("the image would end at 0x%X, into the stock VM region at 0x%X, which the installer would "
                 "overwrite (HW-80, HW-110)" % (n, STOCK_VM))
    if n > store_base:
        p.append("the image would end at 0x%X, past the store region's start 0x%X, which the installer would "
                 "overwrite (HW-110)" % (n, store_base))
    if p:
        raise ValueError("; ".join(p))
    blob = package(hardware_image(app, key), identity)
    unit_check(blob, key)
    return blob


def pack_ota(app, key):
    """HW-106's OTA update file: head 1 update_data (offset 32, the
    file's length, data CRC from byte 32, attribute 3, reserved 0xFF,
    last 1), head 2 app_core (offset 64, the area's length plus 64, data
    CRC over those bytes, attribute 2, reserved 0xFF), then the flash
    image's bytes from 0x4000: the area, scrambled with key, and the 64
    bytes after it (0xFF here, Q-25)."""
    p = pack_problems(app, "small-beeps")
    if key not in KEYS:
        p.append("key 0x%04X: not one the spec gives (%s)" % (key, ", ".join("0x%04X" % k for k in KEYS)))
    if p:
        raise ValueError("; ".join(p))
    data = app_area(app, key) + b"\xff" * OTA_TAIL
    core = head(OTA_CORE_HEAD[0], 64, len(data), data, OTA_CORE_HEAD[1], reserved=0xFF)
    rest = core + data
    first = head(OTA_FILE_HEAD[0], 32, 32 + len(rest), rest, OTA_FILE_HEAD[1], last=1, reserved=0xFF)
    blob = first + rest
    p = ota_problems(blob, key)
    if p:
        raise ValueError("; ".join(p))
    return blob


def ota_problems(blob, key):
    """Problems with an OTA file (HW-106), read as this reader reads it:
    its two heads and their CRCs; app_core's data the flash image from
    0x4000 (HW-106), so placed nowhere below it; an area head first
    under key, its CRCs, and no head in the area naming a region below
    0x4000."""
    if len(blob) < 64 + 2 * CHUNK:
        return ["too short for an OTA file"]
    h1, h2 = HEAD.unpack(blob[:32]), HEAD.unpack(blob[32:64])
    p = head_problems("update_data", h1, blob[:32], blob[32:])
    p += head_problems("app_core", h2, blob[32:64], blob[64:64 + h2[3]])
    if (name_of(h1[7]), h1[2], h1[3], h1[4], h1[6]) != (OTA_FILE_HEAD[0], 32, len(blob), OTA_FILE_HEAD[1], 1):
        p.append("head 1 is not update_data over the whole file (HW-106)")
    if (name_of(h2[7]), h2[2], h2[4]) != (OTA_CORE_HEAD[0], 64, OTA_CORE_HEAD[1]) or 64 + h2[3] != len(blob):
        p.append("head 2 is not app_core over the rest of the file (HW-106)")
    if p:
        return p
    area = scramble(blob[64:len(blob) - OTA_TAIL], key)
    ah = HEAD.unpack(area[:32])
    if name_of(ah[7]) != AREA_HEAD_NAME or ah[3] != len(area):
        return ["app_core's data does not start with the app area's head under key 0x%04X" % key]
    p += area_problems(area)
    at = CHUNK
    while at + 32 <= min(len(area), DIR_SIZE):
        h = HEAD.unpack(area[at:at + 32])
        start = AREA + h[2] if h[4] == APP_ATTR else h[2]
        if start < AREA:
            p.append("%r reaches 0x%X, below 0x%X" % (name_of(h[7]), start, AREA))
        if h[6]:
            break
        at += 32
    return p


def check_ota(blob, key):
    """An OTA file's reading: a dict of what it found, or
    ValueError naming what failed."""
    p = ota_problems(blob, key)
    if p:
        raise ValueError("; ".join(p))
    area = scramble(blob[64:len(blob) - OTA_TAIL], key)
    app = HEAD.unpack(area[CHUNK:2 * CHUNK])
    return {"area": AREA, "entry": WINDOW + app[2], "key": key, "app": area[app[2]:app[2] + app[3]]}


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
    if struct.unpack_from("<HI", hdr, 10) != HEADER_TOOL_FIELDS:
        p.append("header bytes 10-15 are %r, not the tools' %r" % (struct.unpack_from("<HI", hdr, 10),
                                                                   HEADER_TOOL_FIELDS))
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


def area_records(fi, at, key):
    """(the area unscrambled, its records): from flash offset at, under
    key, the area head then at most eight records, ending at the first
    whose own CRC fails (HW-112)."""
    area = scramble(fi[at:], key)
    recs = []
    for r in range(1, AREA_RECORDS + 1):
        raw = area[CHUNK * r:CHUNK * (r + 1)]
        if len(raw) < CHUNK or struct.unpack_from("<H", raw)[0] != jieli_crc(raw[2:]):
            break
        recs.append((raw, HEAD.unpack(raw)))
    return area, recs


def unit_check(blob, key):
    """The unit's checks on a package under key, the unit's own: HW-109's
    installer checks 1 to 11 in order, then HW-112's bootloader checks 1
    to 3. ValueError("HW-109 N: ...") at the first that fails, with the
    installer's own words where HW-109 gives them; else what the
    installer would write."""
    def fail(n, why, src="HW-109"):
        raise ValueError("%s %d: %s" % (src, n, why))
    # 1. At least 4 096 bytes.
    if len(blob) < 4096:
        fail(1, "the file is %d bytes, under 4 096" % len(blob))
    # 2. The prefix blocks: 20, and more while the next block's byte 47
    # is 0x7D; the identity from the markers up to the first 0x7D.
    if blob[BLOCK * BLOCKS + BLOCK_DATA] == END_MARK:
        fail(2, "file byte %d is 0x7D, so the installer takes a 21st header block" % (BLOCK * BLOCKS + BLOCK_DATA))
    identity = ""
    for i in range(BLOCKS):
        m = blob[BLOCK * i + BLOCK_DATA]
        if m == END_MARK:
            break
        identity += chr((m - i - 1) % 256)
    lg = logical_image(blob)
    hdr = mask(lg[:HEADER_SIZE], HEADER_KEY)
    # 3. The header's CRC.
    if struct.unpack_from("<H", hdr)[0] != jieli_crc(hdr[2:]):
        fail(3, INSTALLER[3])
    list_crc, count = struct.unpack_from("<H", hdr, 2)[0], struct.unpack_from("<H", hdr, 8)[0]
    # 4. The list fits in the image.
    end = HEADER_SIZE + ENTRY_SIZE * count
    if end > len(lg):
        fail(4, "the list of %d entries runs past the image" % count)
    # 5. The list CRC.
    if list_crc != jieli_crc(lg[HEADER_SIZE:end]):
        fail(5, INSTALLER[5])
    es = []
    for k in range(count):
        e = mask(lg[HEADER_SIZE + ENTRY_SIZE * k:HEADER_SIZE + ENTRY_SIZE * (k + 1)], HEADER_KEY)
        etype, _, dcrc = struct.unpack_from("<HHH", e)
        off, length = struct.unpack_from("<II", e, 8)
        es.append((etype, name_of(e[64:80]), dcrc, off, length))
    # 6. Every entry's data inside the image.
    for etype, name, dcrc, off, length in es:
        if off + length > len(lg):
            fail(6, "%r's data runs past the image" % name.decode("ascii", "replace"))
    # 7. flash.bin, type 0, its data CRC over the bytes as stored.
    fl = [e for e in es if e[0] == ENTRY_FLASH and e[1] == ENTRY_NAME]
    if not fl:
        fail(7, "no flash.bin of type 0")
    _, _, dcrc, off, length = fl[0]
    fi = lg[off:off + length]
    if dcrc != jieli_crc(fi):
        fail(7, "flash.bin's data CRC is 0x%04X, its data's 0x%04X" % (dcrc, jieli_crc(fi)))
    # 8. The flash image's size.
    if not (len(fi) > AREA and len(fi) % SECTOR == 0):
        fail(8, INSTALLER[8] % len(fi))
    # 9. The model.
    model = identity.rsplit("_", 1)[0] if "_" in identity else identity
    if model != MODEL:
        fail(9, "the identity %r gives the model %r, not %r" % (identity, model, MODEL))
    # 10. No longer than the flash.
    if len(fi) > FLASH_BYTES:
        fail(10, "the flash image is %d bytes, longer than the flash" % len(fi))
    # 11. The chip key: a valid file table under key, at least one
    # attribute-0x82 file, every one's CRC over its unscrambled data.
    area, recs = area_records(fi, AREA, key)
    if struct.unpack_from("<H", area)[0] != jieli_crc(area[2:CHUNK]):
        fail(11, INSTALLER[11] + " (no file table)")
    files = [h for _, h in recs if h[4] == APP_ATTR]
    if not files:
        fail(11, INSTALLER[11] + " (no file of attribute 0x82)")
    for h in files:
        if h[1] != jieli_crc(area[h[2]:h[2] + h[3]]):
            fail(11, INSTALLER[11] + " (%s's CRC)" % name_of(h[7]).decode("ascii", "replace"))
    # HW-112 1. app_dir_head in the flash directory, by name.
    at, d = 32, None
    while at + 32 <= min(len(fi), AREA):
        h = HEAD.unpack(mask(fi[at:at + 32], HEADER_KEY))
        if name_of(h[7]) == AREA_NAME:
            d = h
            break
        if h[6]:
            break
        at += 32
    if d is None:
        fail(1, "no app_dir_head in the flash directory", "HW-112")
    if d[3] not in (0, 0xFFFFFFFF):
        fail(1, "app_dir_head's length is 0x%X, not 0 or 0xFFFFFFFF (one bank)" % d[3], "HW-112")
    # HW-112 2. The area head first, then its records; no all-zero slot
    # read as a record (HW-114).
    area, recs = area_records(fi, d[2], key)
    ah = HEAD.unpack(area[:CHUNK])
    if (ah[4], name_of(ah[7])) != (AREA_HEAD_ATTR, AREA_HEAD_NAME) or \
            struct.unpack_from("<H", area)[0] != jieli_crc(area[2:CHUNK]):
        fail(2, "the area's first record is not the area head (attribute 0x83, app_area_head)", "HW-112")
    if any(raw == bytes(CHUNK) for raw, _ in recs):
        fail(2, "an all-zero head slot reads as a record: unused slots must be 0xFF (HW-114)", "HW-112")
    # HW-112 3. Every attribute-0x82 file: its CRC and its bounds; app.bin
    # non-empty; the entry inside the mapped area.
    app = None
    for _, h in recs:
        if h[4] != APP_ATTR:
            continue
        if h[1] != jieli_crc(area[h[2]:h[2] + h[3]]):
            fail(3, "%r's CRC" % name_of(h[7]), "HW-112")
        if d[2] + h[2] + h[3] > FLASH_BYTES:
            fail(3, "%r runs past the flash" % name_of(h[7]), "HW-112")
        if name_of(h[7]) == APP_NAME:
            app = h
    if app is None or not app[3]:
        fail(3, "no app.bin, or an empty one", "HW-112")
    if not WINDOW <= ah[2] < WINDOW + ah[3]:
        fail(3, "the entry 0x%08X is outside the mapped area" % ah[2], "HW-112")
    return {"identity": identity, "key": key, "length": len(fi), "writes": (AREA, len(fi)), "entry": ah[2],
            "app": area[app[2]:app[2] + app[3]]}


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


def broken_hardware(app, key, version="0.0.0"):
    """(check, label, package) for each of unit_check()'s checks, each
    failing that check and passing those before it, under key."""
    ident = hardware_identity(version)
    fi = hardware_image(app, key)
    good = package(fi, ident)

    def area_edit(edit, image=fi):
        b = bytearray(image)
        area = bytearray(scramble(b[AREA:], key))
        edit(area)
        b[AREA:] = scramble(bytes(area), key)
        return package(bytes(b), ident)

    def recrc(a, at):
        a[at:at + 2] = struct.pack("<H", jieli_crc(bytes(a[at + 2:at + 32])))

    def header_edit(edit):
        b = bytearray(good)
        lg = bytearray(logical_image(b))
        hdr, ent = bytearray(mask(lg[:64], HEADER_KEY)), bytearray(mask(lg[64:144], HEADER_KEY))
        edit(hdr, ent)
        lg[64:144] = mask(bytes(ent), HEADER_KEY)
        if not edit.__name__.startswith("keep_list"):
            struct.pack_into("<H", hdr, 2, jieli_crc(bytes(lg[64:144])))
        hdr[:2] = struct.pack("<H", jieli_crc(bytes(hdr[2:])))
        lg[:64] = mask(bytes(hdr), HEADER_KEY)
        for i in range(BLOCKS):
            b[BLOCK * i:BLOCK * i + BLOCK_DATA] = lg[BLOCK_DATA * i:BLOCK_DATA * (i + 1)]
        return bytes(b)

    def keep_list_bad_crc(h, e):
        h[2] ^= 1

    def count_past(h, e):
        struct.pack_into("<H", h, 8, len(logical_image(good)) // ENTRY_SIZE + 1)

    def keep_list_count(h, e):
        count_past(h, e)

    def entry_past(h, e):
        struct.pack_into("<I", e, 12, len(logical_image(good)))

    b1007 = bytearray(good)
    b1007[BLOCK * BLOCKS + BLOCK_DATA] = END_MARK
    hcrc = bytearray(good)
    hcrc[0] ^= 1
    fcrc = bytearray(fi)
    fcrc[0x3000] ^= 1                          # the boot area's filler: only flash.bin's CRC changes
    no_dir = bytearray(fi)
    h = bytearray(mask(no_dir[64:96], HEADER_KEY))
    h[16:32] = head_name(b"app_dir_heaX")
    recrc(h, 0)
    no_dir[64:96] = mask(bytes(h), HEADER_KEY)

    def flip_app(a):
        a[DIR_SIZE] ^= 1

    def area_attr(a):
        a[12] = 0x84
        recrc(a, 0)

    def entry_out(a):
        struct.pack_into("<I", a, 4, WINDOW + struct.unpack_from("<I", a, 8)[0])
        recrc(a, 0)

    return [
        ("HW-109 1", "short", good[:4000]),
        ("HW-109 2", "byte-1007", bytes(b1007)),
        ("HW-109 3", "header-crc", bytes(hcrc)),
        ("HW-109 4", "list-past-image", header_edit(keep_list_count)),
        ("HW-109 5", "list-crc", header_edit(keep_list_bad_crc)),
        ("HW-109 6", "entry-past-image", header_edit(entry_past)),
        ("HW-109 7", "flash-bin-crc", package(fi, ident)[:DATA_FILE] + bytes(fcrc)),
        ("HW-109 8", "size", package(fi[:-CHUNK], ident)),
        ("HW-109 9", "model", package(fi, "FM-2_" + version)),
        ("HW-109 9", "underscore-in-version", package(fi, "FM-1_A_1")),
        ("HW-109 10", "longer-than-flash", package(fi.ljust(FLASH_BYTES + SECTOR, b"\xff"), ident)),
        ("HW-109 11", "file-crc", area_edit(flip_app)),
        ("HW-112 1", "no-app-dir-head", package(bytes(no_dir), ident)),
        ("HW-112 2", "zero-head-slots", package(hardware_image(app, key, fill=b"\0"), ident)),
        ("HW-112 2", "area-head-attribute", area_edit(area_attr)),
        ("HW-112 3", "entry-outside-area", area_edit(entry_out)),
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
        ap.add_argument("--hardware", action="store_true", help="the hardware package, for a unit's installer")
        ap.add_argument("--ota", action="store_true", help="HW-106's OTA file: the app area alone, no .fwsc")
        ap.add_argument("--key", type=lambda v: int(v, 0),
                        help="the unit's chip key (--hardware: `m-flasher info` shows it), or the OTA file's")
        ap.add_argument("--store-base", type=lambda v: int(v, 0),
                        help="--hardware: the store region's first flash offset (the ELF's sb_store_base)")
        a = ap.parse_args(sys.argv[2:])
        if a.hardware and a.ota:
            ap.error("--hardware or --ota, not both")
        mode = "ota" if a.ota else "hardware" if a.hardware else "full"
        if a.key is not None and mode == "full":
            ap.error("--key goes with --hardware or --ota (the emulator package's key is its key block's)")
        if mode == "hardware" and (a.key is None or a.store_base is None):
            ap.error("--hardware needs --key (the unit's chip key: `m-flasher info`; no default, HW-111) "
                     "and --store-base (the store region's first flash offset)")
        if mode == "hardware" and a.identity:
            ap.error("--hardware sets the identity: FM-1_<version> (HW-109 step 9)")
        if mode == "ota" and a.key is None:
            ap.error("--ota needs --key: %s" % "; ".join("0x%04X, %s" % kv for kv in KEYS.items()))
        with open(a.app, "rb") as f:
            app = f.read()
        identity = a.identity or "small-beeps-" + a.version
        try:
            blob = (pack_ota(app, a.key) if mode == "ota" else pack_hardware(app, a.version, a.key, a.store_base)
                    if mode == "hardware" else pack(app, identity))
        except ValueError as e:
            print("fwsc: %s" % e, file=sys.stderr)
            return 2
        with open(a.out, "wb") as f:
            f.write(blob)
        print("fwsc: wrote %s (%s%s), %d bytes, SHA-256 %s" % (
            a.out, {"ota": "HW-106's OTA file, the app area alone, key 0x%04X" % (a.key or 0),
                    "hardware": "the hardware package, key 0x%04X" % (a.key or 0),
                    "full": "the emulator package, for the emulated load paths"}[mode],
            ", never for a unit" if mode == "full" else "", len(blob), hashlib.sha256(blob).hexdigest()))
        if mode == "hardware":
            r = unit_check(blob, a.key)
            print("fwsc: the unit's checks pass (HW-109 1-11, HW-112 1-3); the installer writes flash 0x%05X to "
                  "0x%05X (HW-110)" % (r["writes"][0], r["writes"][1] - 1))
        for q, what, ours in open_fields(mode):
            print("fwsc: open (%s): %s: %s" % (q, what, ours))
        return 0
    if len(sys.argv) > 1 and sys.argv[1] == "check":
        ap = argparse.ArgumentParser(prog="fwsc.py check")
        ap.add_argument("file")
        ap.add_argument("--key", type=lambda v: int(v, 0), required=True, help="the unit's chip key")
        a = ap.parse_args(sys.argv[2:])
        with open(a.file, "rb") as f:
            blob = f.read()
        try:
            r = unit_check(blob, a.key)
        except ValueError as e:
            print("fwsc: FAIL at %s" % e)
            return 1
        print("fwsc: OK: the unit's checks pass (HW-109 1-11, HW-112 1-3) under key 0x%04X: identity %s, image "
              "%d bytes; the installer writes flash 0x%05X to 0x%05X (HW-110); entry 0x%08X, app %d bytes, "
              "SHA-256 %s" % (r["key"], r["identity"], r["length"], r["writes"][0], r["writes"][1] - 1,
                              r["entry"], len(r["app"]), hashlib.sha256(r["app"]).hexdigest()))
        return 0
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("file")
    ap.add_argument("--unpack")
    ap.add_argument("--ota", action="store_true")
    ap.add_argument("--key", type=lambda v: int(v, 0))
    a = ap.parse_args()
    with open(a.file, "rb") as f:
        blob = f.read()
    if a.ota:
        if a.key is None:
            ap.error("--ota needs --key")
        try:
            r = check_ota(blob, a.key)
        except ValueError as e:
            print("fwsc: FAIL: %s" % e)
            return 1
        print("fwsc: OK: HW-106's OTA file, nothing below 0x%X; entry 0x%08X, key 0x%04X, app %d bytes, SHA-256 %s"
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
