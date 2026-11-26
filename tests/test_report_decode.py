# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
"""tools/report_decode.py reads every layout a build has written (round 2: the release's layout 18 in both its
forms; round 3: layout 19 in both, and the older layouts no seams case writes any more), from records made here."""
import struct
import unittest
import zlib

from tests.helpers import load_tool

rd = load_tool("report_decode.py")


def record(layout, values, seq=1, label="test", build="0.0.0-test", size=None):
    """One record as hw_report.c writes it: the header, the fields, zeros, the CRC."""
    size = size or rd.REC
    w = [0] * (size // 4)
    w[0], w[1], w[2], w[3] = rd.MAGIC, layout | len(values) << 16, seq, 7
    raw = bytearray(struct.pack("<%dI" % len(w), *w))
    raw[16:16 + len(build)] = build.encode()
    raw[32:32 + len(label)] = label.encode()
    struct.pack_into("<%dI" % len(values), raw, 4 * rd.HEAD, *values)
    struct.pack_into("<I", raw, size - 4, zlib.crc32(bytes(raw[:size - 4])) & 0xFFFFFFFF)
    return bytes(raw)


def chip(*recs):
    image = bytearray(b"\xff" * 0x100000)
    for i, r in enumerate(recs):
        image[rd.LOG_BASE + rd.REC * i:rd.LOG_BASE + rd.REC * i + len(r)] = r
    return bytes(image)


class ReportDecodeTest(unittest.TestCase):
    """The report log's decoder reads every layout back named and whole. Requirements: R-HW-1"""

    def test_every_layout_from_6_reads_back_known_and_whole(self):
        # Layouts 6 on are 4096-byte records (audio7 on); each one's fields come back named, in order.
        for layout in sorted(k for k in rd.FIELDS if k >= 6):
            names = rd.FIELDS[layout]
            rs, bad = rd.records(chip(record(layout, list(range(1, len(names) + 1)))))
            self.assertEqual(bad, [], layout)
            self.assertEqual(len(rs), 1, layout)
            self.assertTrue(rs[0]["known"], layout)
            self.assertEqual(list(rs[0]["fields"]), names, layout)
            self.assertEqual(rs[0]["fields"][names[-1]], len(names), layout)

    def test_the_release_layout_in_both_forms(self):
        # Layout 18: the published release has no USB record, the owner-only one has it; the count tells them apart.
        short, full = rd._layout18(False), rd._layout18(True)
        self.assertEqual(len(full) - len(short), len(rd.USB_REC))
        rs, _ = rd.records(chip(record(18, list(range(len(short))), seq=1, label="Summary"),
                                record(18, list(range(len(full))), seq=2, label="Summary")))
        self.assertEqual([r["known"] for r in rs], [True, True])
        self.assertNotIn("usb_magic", rs[0]["fields"])
        self.assertIn("usb_magic", rs[1]["fields"])
        # The log's health is last in both.
        self.assertEqual(list(rs[0]["fields"])[-1], list(rs[1]["fields"])[-1])
        self.assertEqual(rs[0]["fields"]["log_last_err"], short.index("log_last_err"))

    def test_round_3s_layout_in_both_forms(self):
        # Layout 19: layout 18 with the store's stage and record; the count tells the two forms apart again, and a
        # layout 18 record still reads with round 2's stages.
        short, full = rd._layout19(False), rd._layout19(True)
        self.assertEqual(len(full) - len(short), len(rd.USB_REC))
        self.assertEqual(len(rd.STORE_REC), 0xF0 // 4)
        rs, _ = rd.records(chip(record(19, list(range(len(short))), seq=1, label="Summary"),
                                record(19, list(range(len(full))), seq=2, label="Summary"),
                                record(18, list(range(len(rd._layout18(False)))), seq=3, label="Summary")))
        self.assertEqual([r["known"] for r in rs], [True, True, True])
        self.assertIn("inst_at_store_us", rs[0]["fields"])
        self.assertIn("store_marker", rs[0]["fields"])
        self.assertNotIn("usb_magic", rs[0]["fields"])
        self.assertIn("usb_magic", rs[1]["fields"])
        self.assertNotIn("inst_at_store_us", rs[2]["fields"])
        self.assertTrue(any(line.startswith("the release's start") for line in rd.derived(rs[2]["fields"])))
        self.assertTrue(any("store" in line for line in rd.derived(rs[0]["fields"])))

    def test_the_release_fields_start_with_the_stages(self):
        self.assertEqual(rd.INST_REC[:len(rd.INST_STAGES)], ["inst_at_%s_us" % n for n in rd.INST_STAGES])
        self.assertEqual(rd.INST_STAGES[-1], "ready")
        self.assertIn("store", rd.INST_STAGES)
        self.assertNotIn("store", rd.INST_STAGES_R2)

    def test_no_layout_past_the_record(self):
        self.assertTrue(all(len(v) <= 1011 for v in rd.FIELDS.values()))
        self.assertLessEqual(len(rd._layout18(True)), 1011)
        self.assertLessEqual(len(rd._layout19(True)), 1011)


if __name__ == "__main__":
    unittest.main()
