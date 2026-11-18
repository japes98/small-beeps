# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
import os
import struct
import subprocess
import sys
import tempfile
import unittest

from tests.helpers import ROOT, load_tool

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
        for at in (32, 64, 96):
            h = fw.mask(fi[at:at + 32], fw.HEADER_KEY)
            self.assertEqual(struct.unpack_from("<H", h)[0], fw.jieli_crc(h[2:]), at)
        area = fw.scramble(fi[0x4000:], fw.key_from_block(fw.KEY_BLOCK))
        for at in (0, 32):
            self.assertEqual(struct.unpack_from("<H", area, at)[0], fw.jieli_crc(area[at + 2:at + 32]), at)
        app = fw.HEAD.unpack(area[32:64])
        self.assertEqual((app[2], app[3], app[4], app[6], app[7]), (0x120, len(APP), 0x82, 1, b"app.bin\0" + b"\xff" * 8))
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


def logical(p):
    """The logical image, by HW-88, from the file's bytes."""
    return b"".join(p[48 * i:48 * i + 47] for i in range(20)) + p[960:]


def crc(b):
    """JieLi's CRC-16 (HW-87), written out here, not the packager's."""
    c = 0
    for x in b:
        c ^= x << 8
        for _ in range(8):
            c = ((c << 1) ^ 0x1021) & 0xFFFF if c & 0x8000 else (c << 1) & 0xFFFF
    return c


class Section24Test(unittest.TestCase):
    """Requirements: R-PKG-1, R-PKG-3. BR-17: section 24's fields (HW-104,
    HW-105), each recomputed from the package's bytes."""

    def test_crc_written_out_is_hw_87s(self):
        self.assertEqual(crc(b"123456789"), 0x31C3)

    def test_the_header_and_entry_by_hw_104(self):
        for p, data_len in ((fw.pack(APP, "small-beeps-0.9.0"), 0x4000 + 0x120 + len(APP)),
                            (fw.pack_app_area(APP, "small-beeps-0.9.0", 0xFFFF), 0x120 + len(APP))):
            lg = logical(p)
            h = fw.mask(lg[:64], 0xFFFF)
            self.assertEqual(struct.unpack_from("<H", h)[0], crc(h[2:]))
            count = struct.unpack_from("<H", h, 8)[0]
            self.assertEqual(count, 1)
            # The list CRC: the entry list as stored (masked), from logical
            # 64, the markers taken out; the image size: the file less 20.
            self.assertEqual(struct.unpack_from("<H", h, 2)[0], crc(lg[64:64 + 80 * count]))
            self.assertEqual(struct.unpack_from("<I", h, 4)[0], len(p) - 20)
            self.assertEqual(struct.unpack_from("<HI", h, 10), (4, 0x200))   # the tools' values; meaning Q-25
            self.assertEqual(h[16:32], b"AC791N".ljust(16, b"\0"))
            self.assertEqual(h[32:64], bytes(32))
            e = fw.mask(lg[64:144], 0xFFFF)
            etype, index, dcrc, z = struct.unpack_from("<HHHH", e)
            off, length, rounded = struct.unpack_from("<III", e, 8)
            self.assertEqual((etype, index, z, off, length), (0, 0, 0, 0x400, data_len))
            self.assertEqual(off % 32, 0)
            self.assertEqual(rounded, (length + 31) // 32 * 32)
            self.assertEqual(e[20:64], bytes(44))
            self.assertEqual(e[64:80], b"flash.bin".ljust(16, b"\0"))
            self.assertEqual(dcrc, crc(lg[off:off + length]))
            self.assertEqual(len(lg), off + length)
            self.assertNotEqual(p[1007], 0x7D)

    def test_the_flash_image_by_hw_105(self):
        fi = fw.check(fw.pack(APP, "small-beeps-0.9.0"))["flash"]
        u = fw.mask(fi[:32], 0xFFFF)
        self.assertEqual(struct.unpack_from("<H", u)[0], crc(u[2:]))   # over the head unmasked whole
        self.assertEqual(fi[4:8], b"0.01")                            # plain on flash
        self.assertEqual(fi[16:32], b"AC791N_STORY" + b"\xff" * 4)
        self.assertEqual(struct.unpack_from("<HIBBBB", u, 2)[0:1] + struct.unpack_from("<IBBBB", u, 8),
                         (0x8020, 0xFF000, 0x10, 0x10, 0xA4, 0xFF))
        heads = {}
        for at in range(32, 0x4000, 32):
            raw = fw.mask(fi[at:at + 32], 0xFFFF)
            hcrc, dcrc, o, n, attr, res, last, name = struct.unpack("<HHIIBBH16s", raw)
            self.assertEqual(hcrc, crc(raw[2:]))
            nm = name.split(b"\0", 1)[0]
            self.assertEqual(name, (nm + b"\0").ljust(16, b"\xff"))   # one zero byte, then 0xFF
            heads[nm] = (dcrc, o, n, attr, res, last)
            if last:
                break
        self.assertEqual(sorted(heads), [b"app_dir_head", b"isd_config.ini", b"key_mac"])
        d, o, n, attr, res, _ = heads[b"isd_config.ini"]
        self.assertEqual((attr, res, d), (2, 0x80, crc(fi[o:o + n])))
        self.assertEqual(heads[b"app_dir_head"], (0xFFFF, 0x4000, 0xFFFFFFFF, 0x81, 0xFF, 0))
        self.assertEqual(heads[b"key_mac"], (0xFFFF, 0xFF000, 0x1000, 0x12, 1, 0xFFFF))
        area = fw.scramble(fi[0x4000:], fw.key_from_block(fi[0x80:0xA0]))
        hcrc, dcrc, o, n, attr, res, last, name = struct.unpack("<HHIIBBH16s", area[:32])
        self.assertEqual((o, n, attr, res, name), (0x02000120, len(area), 0x83, 0xFF, b"app_area_head\0\xff\xff"))
        self.assertEqual((hcrc, dcrc), (crc(area[2:32]), crc(area[32:n])))
        hcrc, dcrc, o, n = struct.unpack_from("<HHII", area, 32)
        self.assertEqual((hcrc, dcrc), (crc(area[34:64]), crc(APP)))
        self.assertEqual(fw.fields(fw.pack(APP, "small-beeps-0.9.0")), [])

    def test_the_reader_matches_names_up_to_the_first_zero_byte(self):
        self.assertEqual(fw.name_of(b"app.bin\0" + b"\xff" * 8), b"app.bin")
        self.assertEqual(fw.name_of(b"app.bin".ljust(16, b"\0")), b"app.bin")
        self.assertNotEqual(fw.name_of(b"app.bin\xff" + b"\0" * 8), b"app.bin")

    def test_fields_finds_a_wrong_list_crc(self):
        p = fw._relogical(fw.pack(APP, "small-beeps-0.9.0"),
                          lambda h, e: (fw._set(h, 2, b"\0\0"), fw._set(h, 0, struct.pack("<H", fw.jieli_crc(bytes(h[2:]))))))
        fw.check(p)                                                      # fwtest reads no list CRC (HW-93)
        self.assertTrue(any("list CRC" in q for q in fw.fields(p)))


class AppAreaTest(unittest.TestCase):
    """Requirements: R-PKG-3. BR-17 (b): the app area alone, nothing below
    0x4000, read as fwsc.py's reader reads it."""

    def entry_regions(self, p, key):
        """Every entry and region of a package as placed by the reader's
        reading (an app-area package's flash.bin at 0x4000, SR-12)."""
        lg = logical(p)
        h = fw.mask(lg[:64], 0xFFFF)
        regions = []
        for k in range(struct.unpack_from("<H", h, 8)[0]):
            e = fw.mask(lg[64 + 80 * k:144 + 80 * k], 0xFFFF)
            off, length = struct.unpack_from("<II", e, 8)
            regions.append(("entry %d" % k, 0x4000, length))
            area = fw.scramble(lg[off:off + length], key)
            for at in range(32, 0x120, 32):
                o, n, attr, _, last = struct.unpack_from("<IIBBH", area, at + 4)
                regions.append((area[at + 16:at + 32].split(b"\0")[0], 0x4000 + o if attr == 0x82 else o, n))
                if last:
                    break
        return regions

    def test_nothing_below_0x4000(self):
        for key in (0xFFFF, 0x980F):
            p = fw.pack_app_area(APP, "small-beeps-0.9.0", key)
            self.assertEqual(p, fw.pack_app_area(APP, "small-beeps-0.9.0", key))     # R-REPRO
            self.assertEqual(fw.below_area(p, key), [])
            for name, start, n in self.entry_regions(p, key):
                self.assertGreaterEqual(start, 0x4000, name)
            r = fw.check_app_area(p, key)
            self.assertEqual((r["app"], r["entry"]), (APP, 0x02000120))
            with self.assertRaises(ValueError):
                fw.check(p)                                              # no flash header, no directory
            self.assertNotIn(fw.KEY_BLOCK, p)
            # The area's bytes are the full image's from 0x4000, under the
            # same key (the full image's area is its key block's).
            lg = logical(p)
            self.assertEqual(fw.scramble(lg[0x400:], key)[32:], fw.scramble(
                fw.check(fw.pack(APP, "x"))["flash"][0x4000:], fw.key_from_block(fw.KEY_BLOCK))[32:])

    def test_below_0x4000_is_refused(self):
        key = 0xFFFF
        self.assertTrue(fw.below_area(fw.pack(APP, "small-beeps-0.9.0"), key))          # the full image
        good = fw.pack_app_area(APP, "small-beeps-0.9.0", key)
        area = bytearray(fw.scramble(logical(good)[0x400:], key))
        struct.pack_into("<H", area, 32 + 14, 0)                         # app.bin no longer last
        area[64:96] = fw.head(b"VM", 0x3000, 0x1000, attr=0x12, last=1, data_crc=0xFFFF)
        low = fw.package(fw.scramble(bytes(area), key), "small-beeps-0.9.0")
        self.assertTrue(any("0x3000" in q for q in fw.below_area(low, key)))
        self.assertTrue(any(start < 0x4000 for _, start, _ in self.entry_regions(low, key)))
        self.assertTrue(fw.below_area(good, 0x980F))                       # the wrong key reads no area head
        with self.assertRaises(ValueError):
            fw.pack_app_area(APP, "small-beeps-0.9.0", 0xFFFF ^ 1)      # a key the spec doesn't give

    def run_pack(self, *args):
        with tempfile.TemporaryDirectory() as d:
            app, out = os.path.join(d, "app.bin"), os.path.join(d, "o.fwsc")
            with open(app, "wb") as f:
                f.write(APP)
            r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "fwsc.py"), "pack", app, "--version",
                                "0.9.0", "--out", out] + list(args), capture_output=True, text=True)
            return r, os.path.exists(out)

    def test_hardware_mode_refuses_naming_each_open_question(self):
        for args in (["--app-area", "--key", "0xFFFF", "--hardware"], ["--hardware"]):
            r, written = self.run_pack(*args)
            self.assertEqual(r.returncode, 2, args)
            self.assertFalse(written)
            for q in ("Q-25", "Q-26"):
                self.assertIn(q, r.stderr)
        r, _ = self.run_pack("--app-area", "--key", "0xFFFF", "--hardware")
        self.assertIn("SR-12", r.stderr)
        r, _ = self.run_pack("--hardware")
        self.assertIn("boot area", r.stderr)

    def test_every_pack_names_what_is_open(self):
        r, written = self.run_pack("--app-area", "--key", "0x980F")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(written)
        for q in ("Q-25", "Q-26", "SR-12"):
            self.assertIn("open (%s)" % q, r.stdout)
        r, _ = self.run_pack()
        self.assertIn("never for a unit", r.stdout)
        self.assertNotIn("SR-12", r.stdout)
        r, written = self.run_pack("--app-area")
        self.assertEqual(r.returncode, 2)
        self.assertFalse(written)


if __name__ == "__main__":
    unittest.main()


class OtaTest(unittest.TestCase):
    """Requirements: R-PKG-4. BR-17, round 2: HW-106's OTA update file,
    the app area alone, recomputed from the file's bytes."""

    def test_the_two_heads_by_hw_106(self):
        for key in (0xFFFF, 0x980F):
            b = fw.pack_ota(APP, key)
            self.assertEqual(b, fw.pack_ota(APP, key))                     # R-REPRO
            h1 = struct.unpack("<HHIIBBH16s", b[:32])
            h2 = struct.unpack("<HHIIBBH16s", b[32:64])
            self.assertEqual(h1[0], crc(b[2:32]))
            self.assertEqual(h1[1:], (crc(b[32:]), 32, len(b), 3, 0xFF, 1, b"update_data\0" + b"\xff" * 4))
            self.assertEqual(h2[0], crc(b[34:64]))
            self.assertEqual(h2[2:6], (64, 0x120 + len(APP) + 64, 2, 0xFF))
            self.assertEqual(h2[7].split(b"\0")[0], b"app_core")
            self.assertEqual(h2[1], crc(b[64:64 + h2[3]]))
            self.assertEqual(len(b), 64 + h2[3])
            # The data: the area from 0x4000 under key, then 64 bytes (Q-25).
            area = fw.scramble(b[64:-64], key)
            self.assertEqual(area[16:32], b"app_area_head\0\xff\xff")
            self.assertEqual(area[0x120:], APP)
            self.assertEqual(b[-64:], b"\xff" * 64)
            self.assertEqual(fw.check_ota(b, key)["app"], APP)

    def test_nothing_below_0x4000(self):
        key = 0xFFFF
        b = fw.pack_ota(APP, key)
        self.assertEqual(fw.ota_problems(b, key), [])
        self.assertNotIn(fw.KEY_BLOCK, b)
        with self.assertRaises(ValueError):
            fw.check(b)                                                    # no .fwsc blocks, no flash header
        area = bytearray(fw.scramble(b[64:-64], key))
        struct.pack_into("<H", area, 32 + 14, 0)
        area[64:96] = fw.head(b"VM", 0x3000, 0x1000, attr=0x12, last=1, data_crc=0xFFFF)
        data = fw.scramble(bytes(area), key) + b"\xff" * 64
        core = fw.head(b"app_core", 64, len(data), data, 2, reserved=0xFF)
        low = fw.head(b"update_data", 32, 64 + len(data), core + data, 3, last=1, reserved=0xFF) + core + data
        self.assertTrue(any("0x3000" in q for q in fw.ota_problems(low, key)))
        self.assertTrue(fw.ota_problems(b, 0x980F))                          # the wrong key

    def run_pack(self, *args):
        with tempfile.TemporaryDirectory() as d:
            app, out = os.path.join(d, "app.bin"), os.path.join(d, "o.ufw")
            with open(app, "wb") as f:
                f.write(APP)
            r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "fwsc.py"), "pack", app, "--version",
                                "0.9.0", "--out", out] + list(args), capture_output=True, text=True)
            return r, os.path.exists(out)

    def test_the_command_line(self):
        r, written = self.run_pack("--ota", "--key", "0xFFFF")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(written)
        self.assertIn("HW-106's OTA file", r.stdout)
        for q in ("Q-25", "Q-26"):
            self.assertIn("open (%s)" % q, r.stdout)
        self.assertNotIn("SR-12", r.stdout)                                  # HW-106 places the data
        r, written = self.run_pack("--ota", "--key", "0xFFFF", "--hardware")
        self.assertEqual((r.returncode, written), (2, False))
        self.assertIn("64 bytes after the area", r.stderr)
        r, written = self.run_pack("--ota", "--app-area", "--key", "0xFFFF")
        self.assertEqual((r.returncode, written), (2, False))
