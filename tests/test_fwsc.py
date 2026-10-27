# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
import struct
import unittest

from tests.helpers import load_tool

fw = load_tool("fwsc.py")

APP = bytes(range(256)) * 40 + b"tail"


class FwscTest(unittest.TestCase):
    """Requirements: R-PKG-1"""

    def test_jieli_crc_and_mask_by_hw_87(self):
        self.assertEqual(fw.jieli_crc(b"123456789"), 0x31C3)
        self.assertEqual(fw.mask(b"\0" * 4, 0xFFFF), bytes([0xFF, 0xDF, 0x9F, 0x1F]))
        self.assertEqual(fw.mask(fw.mask(APP, 0x2B5D), 0x2B5D), APP)

    def test_key_from_block_by_hw_90(self):
        self.assertEqual(fw.key_from_block(bytes(32)), 0xFFFF)                  # s 0 -> 0x55; 0 < 0x55: every bit
        self.assertEqual(fw.key_from_block(bytes([0xFF] * 16 + [0] * 16)), 0)   # s 0xF0 -> 0xAA; 0xFF >= 0xAA
        kb = bytes([0x20] + [0] * 30 + [0x40])                            # s 0x20; bit 15: 0x40 ^ 0x20 >= 0x20
        self.assertEqual(fw.key_from_block(kb), 0x7FFF)

    def test_a_package_reads_back_as_written(self):
        p = fw.pack(APP, "small-beeps-0.9.0")
        self.assertEqual(p, fw.pack(APP, "small-beeps-0.9.0"))     # reproducible
        r = fw.check(p)
        self.assertEqual(r["identity"], "small-beeps-0.9.0")
        self.assertEqual(r["area"], 0x4000)
        self.assertEqual(r["entry"], 0x02000120)
        self.assertEqual(r["app"], APP)
        self.assertEqual(r["key"], fw.key_from_block(fw.KEY_BLOCK))

    def test_layout_by_hw_88_to_hw_91(self):
        p = fw.pack(APP, "small-beeps-0.9.0")
        # The markers: the identity's characters plus their block's number,
        # then 0x7D; nothing at offset 1007 looks like a 21st marker.
        self.assertEqual([p[48 * i + 47] for i in range(3)], [ord("s") + 1, ord("m") + 2, ord("a") + 3])
        self.assertTrue(all(p[48 * i + 47] == 0x7D for i in range(17, 20)))
        self.assertNotEqual(p[1007], 0x7D)
        fi = fw.check(p)["flash"]
        # The flash image ends at the app area's end: nothing past it.
        self.assertEqual(len(fi), 0x4000 + 0x120 + len(APP))
        self.assertEqual(len(p), fw.DATA_FILE + len(fi))
        # Every CRC by HW-87's rule, the heads masked one by one.
        for at in (0, 32, 64):
            h = fw.mask(fi[at:at + 32], fw.HEADER_KEY)
            self.assertEqual(struct.unpack_from("<H", h)[0], fw.jieli_crc(h[2:]), at)
        area = fw.scramble(fi[0x4000:], fw.key_from_block(fw.KEY_BLOCK))
        for at in (0, 32):
            self.assertEqual(struct.unpack_from("<H", area, at)[0], fw.jieli_crc(area[at + 2:at + 32]), at)
        app = fw.HEAD.unpack(area[32:64])
        self.assertEqual((app[2], app[3], app[4], app[6], app[7].rstrip(b"\0")), (0x120, len(APP), 0x82, 1, b"app.bin"))
        self.assertEqual(area[0x120:], APP)
        # Scrambled on the chip: the stored area is not the plain one.
        self.assertNotEqual(fi[0x4120:0x4140], APP[:32])

    def test_identities(self):
        for bad in ("", "x" * 20, "SMK-37", "mke", "StarryKey 61", "small beeps", "café"):
            self.assertTrue(fw.identity_problems(bad), bad)
        self.assertEqual(fw.identity_problems("small-beeps-0.9.0"), [])
        self.assertEqual(fw.identity_problems("a" * 19), [])

    def test_too_big_an_app_is_refused(self):
        with self.assertRaises(ValueError):
            fw.pack(b"\0" * (0xEA000 - 0x4120 + 1), "small-beeps-0.0.0")
        fw.pack(b"\0" * (0xEA000 - 0x4120), "small-beeps-0.0.0")

    def test_each_check_refuses_its_broken_package_in_order(self):
        fw.check(fw.pack(APP, "small-beeps-0.0.0"))
        seen = set()
        for n, label, p in fw.broken(APP):
            seen.add(n)
            with self.assertRaises(ValueError, msg=label) as e:
                fw.check(p)
            self.assertTrue(str(e.exception).startswith("%d: " % n), (label, str(e.exception)))
        self.assertEqual(seen, set(range(1, 10)))


if __name__ == "__main__":
    unittest.main()
