# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
import os
import random
import re
import unittest
import zlib

from tests.helpers import ROOT, load_tool

st = load_tool("store.py")


def source(name):
    with open(os.path.join(ROOT, "firmware", *name.split("/"))) as f:
        return f.read()


def patch(n):
    return bytes([n]) * 112


class StoreFormatTest(unittest.TestCase):
    """Requirements: R-STORE-1"""

    def test_the_tool_and_the_firmware_agree_on_the_layout(self):
        h, c, ld = source("src/store.h"), source("src/store.c"), source("platform.ld")
        for name, value in (("STORE_BASE", st.BASE), ("STORE_SIZE", st.SIZE), ("STORE_SECTOR", st.SECTOR),
                            ("STORE_PAGE", st.PAGE), ("STORE_SLOTS", st.SLOTS),
                            ("STORE_MAX_PAYLOAD", st.MAX_PAYLOAD), ("STORE_PATCH", st.PATCH),
                            ("STORE_SELECTION", st.SELECTION), ("STORE_SETTINGS", st.SETTINGS),
                            ("STORE_RESET", st.RESET)):
            # The shipping region's, not the wide region test build's (BR-12).
            m = re.search(r"#define %s\s+(0x[0-9A-Fa-f]+|\d+)u" % name, h.split("#else", 1)[-1]
                          if name in ("STORE_BASE", "STORE_SIZE") else h)
            self.assertIsNotNone(m, name)
            self.assertEqual(int(m.group(1), 0), value, name)
        for name, value in (("SECTOR_MAGIC", st.SECTOR_MAGIC), ("RECORD_MAGIC", st.RECORD_MAGIC),
                            ("HEADER", st.HEADER), ("BLOCK", st.BLOCK), ("FORMAT", st.FORMAT),
                            ("CUT_PARAM", st.CUT_PARAM)):
            m = re.search(r"#define %s\s+(0x[0-9A-Fa-f]+|\d+)u" % name, c)
            self.assertIsNotNone(m, name)
            self.assertEqual(int(m.group(1), 0), value, name)
        # The image's window ends where the stock firmware's user patch
        # region begins (HW-5: window offset n is chip offset 0x4000 + n).
        self.assertIn("LENGTH = 0x%X - 0x4000" % st.USER_REGION[0], ld)
        self.assertIn("STORE_BASE = 0x%X;" % st.BASE, ld)
        # HW-80: since M8a the unused region, out of the boot area, the
        # Bluetooth sector, the stock user patch region and the per-unit
        # last sector.
        self.assertEqual(st.USER_REGION, (0xEA000, 0xFC000))
        self.assertGreaterEqual(st.BASE, st.USER_REGION[1])
        self.assertLessEqual(st.BASE + st.SIZE, 0xFF000)
        self.assertLess(st.CUT_PARAM + 8, st.USER_REGION[0])

    def test_the_firmware_crc_table_is_the_common_crc32(self):
        table = re.search(r"crc_nibble\[16\] = \{(.*?)\};", source("src/store.c"), re.S).group(1)
        values = [int(x, 16) for x in re.findall(r"0x([0-9A-Fa-f]{8})u", table)]
        want = []
        for n in range(16):
            c = n
            for _ in range(4):
                c = c >> 1 ^ (0xEDB88320 if c & 1 else 0)
            want.append(c)
        self.assertEqual(values, want)
        self.assertEqual(st.crc32(b"123456789"), zlib.crc32(b"123456789") & 0xFFFFFFFF)

    def test_records_are_blocks(self):
        self.assertEqual(st.record_size(112), 128)
        self.assertEqual(st.record_size(4), 32)
        self.assertEqual(st.record_size(40), 64)
        self.assertEqual(st.record_size(0), 16)


class StoreModelTest(unittest.TestCase):
    """Requirements: R-STORE-3, R-STORE-4, R-STORE-5, R-STORE-8"""

    def test_put_and_read_back(self):
        s = st.Store()
        s.put(st.PATCH, 3, 1, patch(7))
        s.put(st.SELECTION, 0, 1, b"\x02\0\0\0")
        img = st.Image(s.chip())
        self.assertEqual(img.get(st.PATCH, 3), (1, patch(7)))
        self.assertEqual(img.get(st.SELECTION), (1, b"\x02\0\0\0"))
        self.assertIsNone(img.get(st.PATCH, 4))

    def test_the_newest_valid_copy_wins_and_a_damaged_one_is_skipped(self):
        s = st.Store()
        s.put(st.PATCH, 0, 1, patch(1))
        s.put(st.PATCH, 0, 1, patch(2))
        chip = bytearray(s.chip())
        self.assertEqual(st.Image(chip).get(st.PATCH, 0), (1, patch(2)))
        chip[st.Image(chip).keys[0][1] + 20] ^= 1
        img = st.Image(chip)
        self.assertEqual(img.get(st.PATCH, 0), (1, patch(1)))
        self.assertEqual(img.counts["crc_bad"], 1)

    def test_a_torn_record_leaves_the_old_copy_and_the_head_writable(self):
        s = st.Store()
        s.put(st.PATCH, 0, 1, patch(1))
        before = s.chip()
        s.commands = []
        s.put(st.PATCH, 0, 1, patch(2))
        kind, addr, data = s.commands[-1]
        for k in range(1, len(data)):
            torn = st.apply(before, [(kind, addr, data[:k])])
            img = st.Image(torn)
            self.assertEqual(img.get(st.PATCH, 0), (1, patch(1)), k)
            again = st.Store(torn)
            again.put(st.PATCH, 0, 1, patch(3))
            self.assertEqual(st.Image(again.chip()).get(st.PATCH, 0), (1, patch(3)), k)

    def test_a_reset_voids_what_came_before(self):
        s = st.Store()
        s.put(st.PATCH, 0, 1, patch(1))
        s.reset()
        s.put(st.PATCH, 1, 1, patch(2))
        img = st.Image(s.chip())
        self.assertIsNone(img.get(st.PATCH, 0))
        self.assertEqual(img.get(st.PATCH, 1), (1, patch(2)))
        self.assertEqual(img.counts["voided"], 1)

    def test_the_ring_keeps_every_live_record_and_wears_evenly(self):
        s = st.Store()
        rng = random.Random(3)
        want = {}
        for i in range(6000):
            slot = rng.randrange(st.SLOTS)
            want[slot] = patch(i % 251)
            s.put(st.PATCH, slot, 1, want[slot])
            if i % 7 == 0:
                s.put(st.SELECTION, 0, 1, bytes([i % 9, 0, 0, 0]))
        img = st.Image(s.chip())
        for slot, p in want.items():
            self.assertEqual(img.get(st.PATCH, slot), (1, p))
        self.assertGreaterEqual(min(s.erases), 10)
        self.assertLessEqual(max(s.erases) - min(s.erases), 1)

    def test_no_free_sector_is_refused_without_writing(self):
        s = st.Store()
        for sec in range(st.SECTORS):
            s.raw_sector(sec, sec + 1)
        s.raw_record(0, 16, st.PATCH, 0, 1, patch(1), 1)
        seq = 2
        for sec in range(1, st.SECTORS):
            for off in range(16, st.SECTOR - 31, 32):
                s.raw_record(sec, off, st.SELECTION, 0, 1, b"\0\0\0\0", seq)
                seq += 1
        chip = s.chip()
        again = st.Store(chip)
        with self.assertRaises(RuntimeError):
            again.put(st.PATCH, 1, 1, patch(2))
        self.assertEqual(again.chip(), chip)

    def test_the_live_records_always_fit_one_sector(self):
        # Every key at its largest, copied forward with the new record: the
        # compaction never runs out of room in a fresh head (store.c).
        live = st.SLOTS * st.record_size(112) + st.record_size(4) + st.record_size(40) + st.record_size(0)
        self.assertLessEqual(live + st.record_size(112), st.SECTOR - st.BLOCK)


class SettingsLayoutTest(unittest.TestCase):
    """Requirements: R-STORE-6"""

    def test_version_1_is_version_2_without_its_tail(self):
        """Since M8a version 3 is version 2's 40 bytes, its last (always 0
        in version 2) the knobs' mode; since ARP version 4 is version 3's
        40 bytes, then the tempo and the arpeggiator's MIDI out."""
        h = source("src/midi.h")
        self.assertIn("#define MIDI_SETTINGS_VERSION 4u", h)
        self.assertRegex(h, r"u8 local;[^\n]*\n(?:\s*/\*[^\n]*\n)?\s*u8 knobs;")
        self.assertRegex(h, r"u8 knobs;[^\n]*\n(?:\s*/\*[^\n]*\n)?\s*u8 tempo;[^\n]*\n\s*u8 arp_out;")
        self.assertIn('sizeof(struct midi_settings) == 10 + 2 * MIDI_CC_ROUTES', h)
        self.assertIn("#define MIDI_CC_ROUTES        16u", h)
        self.assertIn("#define SETTINGS_V1_BYTES (4u + 2u * MIDI_CC_ROUTES)", source("src/saving.c"))
        self.assertIn("#define SETTINGS_V3_BYTES (8u + 2u * MIDI_CC_ROUTES)", source("src/saving.c"))


if __name__ == "__main__":
    unittest.main()


def fill_head(s, size, r=0):
    """Saves (the settings, then one filler payload to the byte) until the
    ring has wrapped and the head has no room for a record of size bytes."""
    while True:
        room = st.SECTOR - s.append
        if s.head_seq >= st.SECTORS + 1 and room < size:
            return
        if s.head_seq < st.SECTORS + 1 or room >= st.record_size(42) + size:
            s.put(st.SETTINGS, 0, 4, bytes([r % 256]) * 42)
            r += 1
        else:
            s.put_fw(0x82, 0, 1, bytes(room - 24))      # a record of room bytes


class FirmwareKindsTest(unittest.TestCase):
    """Requirements: R-STORE-10, R-STORE-11"""

    def test_constants_agree_with_the_firmware(self):
        h = source("src/store.h")
        for name, value in (("STORE_FW_KIND_FIRST", st.FW_KIND_FIRST), ("STORE_FW_KIND_LAST", st.FW_KIND_LAST),
                            ("STORE_FW_TAG", st.TAG), ("STORE_FW_PART", st.PART_DATA),
                            ("STORE_FW_PARTS", st.FW_PARTS), ("STORE_FW_KEYS", st.FW_KEYS),
                            ("STORE_FW_PAYLOADS", st.FW_PAYLOADS)):
            m = re.search(r"#define %s\s+(0x[0-9A-Fa-f]+|\d+)u" % name, h)
            self.assertIsNotNone(m, name)
            self.assertEqual(int(m.group(1), 0), value, name)
        # The wide region test build's region (BR-12): WIDE_SECTORS ending
        # where today's ends.
        wide = re.search(r"#if defined\(SB_TEST_STORE_WIDE\)(.*?)#else", h, re.S).group(1)
        self.assertIn("#define STORE_BASE       0x%Xu" % st.region_base(st.WIDE_SECTORS), wide)
        self.assertIn("#define STORE_SIZE       0x%Xu" % (st.WIDE_SECTORS * st.SECTOR), wide)

    def test_a_payload_in_parts_reads_back_whole(self):
        s = st.Store()
        data = bytes(range(256)) * 16
        s.put_fw(0x80, 7, 3, data)
        s.put_fw(0x81, 0, 1, b"tiny")
        img = st.Image(s.chip())
        self.assertEqual(img.get_fw(0x80, 7), (3, data))
        self.assertEqual(img.get_fw(0x81, 0), (1, b"tiny"))
        self.assertEqual(sum(1 for f in img.fw if f), 9 + 1)    # 4 096 bytes in 9 parts, and 1
        self.assertIsNone(img.get_fw(0x80, 6))

    def _cut_everywhere(self, sectors, before, put, old, new, step=1):
        """Every state a cut can leave during the save `put` makes from
        `before`: each payload in `old` and `new` ((kind, id) to (version,
        bytes) or None; a base kind's id below 0x100) reads old or new,
        whole; the old until a moment, then the new."""
        s = st.Store(before, sectors)
        s.commands = []
        put(s)
        seen = []
        for i, done, chip in st.cut_states(before, s.commands, step):
            img = st.Image(chip, sectors)
            now = []
            for key in old:
                kind, ident = key
                got = img.get_fw(kind, ident) if st.fw_kind(kind) else img.get(kind, ident)
                self.assertIn(got, (old[key], new[key]),
                              "0x%02x/%d after %d commands and %d bytes" % (kind, ident, i, done))
                now.append(got == new[key] and old[key] != new[key])
            seen.append(tuple(now))
        for k in range(len(old)):
            col = [n[k] for n in seen]
            self.assertEqual(col, sorted(col), "a payload went back from new to old")
            self.assertTrue(col[-1] or list(old.values())[k] == list(new.values())[k])
        return s.commands

    def test_a_large_rewrite_cut_anywhere_is_old_or_new(self):
        # BR-12: 3 000 bytes (7 parts) rewritten in today's region; every
        # byte of every command.
        s = st.Store()
        s.put_fw(0x80, 0, 1, bytes([1]) * 3000)
        s.put_fw(0x81, 0, 1, b"small")
        commands = self._cut_everywhere(
            st.SECTORS, s.chip(), lambda t: t.put_fw(0x80, 0, 1, bytes([2]) * 3000),
            {(0x80, 0): (1, bytes([1]) * 3000), (0x81, 0): (1, b"small")},
            {(0x80, 0): (1, bytes([2]) * 3000), (0x81, 0): (1, b"small")})
        self.assertTrue(any(c[0] == "erase" for c in commands))     # it took a new sector

    def test_a_4096_byte_rewrite_beside_the_full_store_cut_anywhere(self):
        # The wide region: the base's full store, then 4 096 bytes rewritten
        # until a rewrite takes a new sector and compacts; every 4th byte.
        s = st.Store(sectors=st.WIDE_SECTORS)
        for i in range(16):
            s.put(st.PATCH, i, 2, patch(i))
        s.put(st.SELECTION, 0, 1, b"\x05\0\0\0")
        s.put(st.SETTINGS, 0, 4, bytes(42))
        s.put_fw(0x80, 7, 1, bytes([1]) * 4096)
        s.put_fw(0x80, 7, 1, bytes([2]) * 4096)
        old = {(0x80, 7): (1, bytes([2]) * 4096), (st.PATCH, 3): (2, patch(3))}
        new = {(0x80, 7): (1, bytes([3]) * 4096), (st.PATCH, 3): (2, patch(3))}
        commands = self._cut_everywhere(st.WIDE_SECTORS, s.chip(),
                                        lambda t: t.put_fw(0x80, 7, 1, bytes([3]) * 4096), old, new, step=4)
        self.assertTrue(any(c[0] == "erase" for c in commands))

    def test_a_small_save_cut_anywhere_is_old_or_new(self):
        # A patch and a one-part payload, each saved as the head fills, so
        # the save opens a new sector and compacts the next.
        for put, key, old, new in (
                (lambda t: t.put(st.PATCH, 3, 2, patch(9)), (st.PATCH, 3), (2, patch(3)), (2, patch(9))),
                (lambda t: t.put_fw(0x81, 0, 1, b"new one"), (0x81, 0), (1, b"old"), (1, b"new one"))):
            s = st.Store()
            for i in range(16):
                s.put(st.PATCH, i, 2, patch(i))
            s.put_fw(0x81, 0, 1, b"old")
            fill_head(s, st.record_size(112) if key[0] == st.PATCH else st.record_size(st.TAG + 7))
            commands = self._cut_everywhere(st.SECTORS, s.chip(), put, {key: old}, {key: new})
            self.assertTrue(any(c[0] == "erase" for c in commands))

    def test_a_rewrite_that_cant_fit_is_refused_before_anything_is_written(self):
        # In today's region 4 096 bytes are written once, and a rewrite,
        # which needs room for both, is refused with the old one kept.
        s = st.Store()
        s.put_fw(0x80, 0, 1, bytes([1]) * 4096)
        before = s.chip()
        s.commands = []
        with self.assertRaises(RuntimeError):
            s.put_fw(0x80, 0, 1, bytes([2]) * 4096)
        self.assertEqual(s.commands, [])
        self.assertEqual(st.Image(s.chip()).get_fw(0x80, 0), (1, bytes([1]) * 4096))
        self.assertEqual(s.chip(), before)

    def test_fewer_parts_leave_the_old_ones_dead(self):
        s = st.Store()
        s.put_fw(0x80, 0, 1, bytes(3000))
        s.put_fw(0x80, 0, 1, b"short")
        img = st.Image(s.chip())
        self.assertEqual(img.get_fw(0x80, 0), (1, b"short"))
        self.assertEqual(sum(1 for f in img.fw if f), 1)
        self.assertEqual(img.counts.get("stale"), 7)    # the old write's 7 records

    def test_a_reset_voids_them(self):
        s = st.Store()
        s.put_fw(0x90, 1, 1, bytes(1000))
        s.put(st.PATCH, 2, 1, patch(2))
        s.reset()
        img = st.Image(s.chip())
        self.assertIsNone(img.get_fw(0x90, 1))
        self.assertIsNone(img.get(st.PATCH, 2))

    def _beside(self, sectors, size):
        s = st.Store(sectors=sectors)
        for i in range(16):
            s.put(st.PATCH, i, 2, patch(i))
        s.put(st.SELECTION, 0, 1, b"\x05\0\0\0")
        s.put(st.SETTINGS, 0, 4, bytes(42))
        for r in range(40):
            s.put_fw(0x80, 0, 1, bytes([r]) * size)
            s.put(st.PATCH, r % 16, 2, patch(r % 7))
        return st.Image(s.chip(), sectors).get_fw(0x80, 0)

    def test_what_the_regions_hold(self):
        # BR-12: a rewrite needs room for the old payload and the new.
        # Alone in today's region: 3 920 bytes, rewritten again and again;
        # one more is too many.
        s = st.Store()
        for r in range(40):
            s.put_fw(0x80, 0, 1, bytes([r]) * 3920)
        self.assertEqual(st.Image(s.chip()).get_fw(0x80, 0), (1, bytes([39]) * 3920))
        with self.assertRaises(RuntimeError):
            t = st.Store()
            for r in range(40):
                t.put_fw(0x80, 0, 1, bytes([r]) * 3921)
        # Beside the base's full store, saved in between: 2 316 bytes in
        # today's; 4 096 needs the wide region's 5 sectors (4 too few).
        self.assertEqual(self._beside(st.SECTORS, 2316), (1, bytes([39]) * 2316))
        with self.assertRaises(RuntimeError):
            self._beside(st.SECTORS, 2317)
        self.assertEqual(self._beside(st.WIDE_SECTORS, 4096), (1, bytes([39]) * 4096))
        with self.assertRaises(RuntimeError):
            self._beside(4, 4096)
