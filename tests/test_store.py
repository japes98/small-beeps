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
        h, c, ld = source("src/store.h"), source("src/store.c"), source("app.ld")
        for name, value in (("STORE_BASE", st.BASE), ("STORE_SIZE", st.SIZE), ("STORE_SECTOR", st.SECTOR),
                            ("STORE_PAGE", st.PAGE), ("STORE_SLOTS", st.SLOTS),
                            ("STORE_MAX_PAYLOAD", st.MAX_PAYLOAD), ("STORE_PATCH", st.PATCH),
                            ("STORE_SELECTION", st.SELECTION), ("STORE_SETTINGS", st.SETTINGS),
                            ("STORE_RESET", st.RESET)):
            m = re.search(r"#define %s\s+(0x[0-9A-Fa-f]+|\d+)u" % name, h)
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
