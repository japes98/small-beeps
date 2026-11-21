#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
"""Decodes the hardware build's report log from a flash image.

    report_decode.py IMAGE [--all] [--json]

IMAGE is a whole flash read back from a unit (1 MiB) or fwtest's flash.bin.
The log (firmware/src/hw_report.c, SB_HW_REPORT; clean-br17-report1) is a
ring of 32 sectors ending at 0x93FFF, of 1024-byte records. Every 4-byte
boundary of the image is searched for a record's magic, so a record turns
up wherever it lies. Each found is checked by its CRC-32 and printed in
sequence order with its fields named; a failing CRC is counted only in
the log's region (elsewhere the magic is most likely the firmware's own
constant in its image). Without --all, the fields that are 0
in every record are left out.

If no valid record is found, it says so, and what the log's region holds:
all 0xFF (erased, never written), other bytes with no magic, or magic with
a CRC that fails. Exit 0 if a record was found, 1 if none, 2 on a bad
argument. Python 3, standard library only.
"""
import json
import struct
import sys
import zlib

MAGIC = 0x4C524253          # "SBRL" (hw_fm1.h, HW_LOG_MAGIC)
REC = 1024                  # HW_LOG_REC
HEAD = 12                   # HW_LOG_HEAD
LOG_END = 0x94000           # HW_LOG_END
LOG_SECTORS = 32            # HW_LOG_SECTORS
LOG_BASE = LOG_END - LOG_SECTORS * 4096
SECTOR = 4096


def _layout1():
    """Layout 1's field names, in the firmware's order (hw_report.c's
    fields, then hw_audio.c's hw_audio_report)."""
    f = ["core1_count", "C1_CON", "store_count", "store_put", "WIN_CON", "flash_id", "flash_status1",
         "flash_status2", "log_found_at_start", "log_fails"]
    f += ["PLL2_CON0", "CLK_CON2", "DAA_CON0", "DAA_CON1", "DAA_CON2", "DAA_CON3", "DAA_CON7", "ADA_CON0",
          "ADA_CON1", "ADA_CON2", "DAC_CON", "AL0_CON0", "AL0_CON1", "AL0_CON2", "AL0_CON3", "IOMAP_CON0",
          "IOMAP_CON1", "PC_OUT", "PC_DIR", "PC_DIE", "PC_PU", "PC_PD"]
    f += ["CLK_CON0", "CLK_CON1", "SYS_DIV", "PLL_CON0", "PLL_CON1", "PLL2_CON1"]
    f += ["IOMAP_CON%d" % i for i in range(2, 9)]
    f += ["irq", "alt", "b15_flips", "pend", "fps_x10", "halves", "master", "gain", "tone_on", "storm_beat",
          "audio_started_beat"]
    f += ["rec_state", "rec_presses", "rec_clk_before", "rec_clk_set", "rec_clk_back"]
    f += ["seq_state", "seq_presses", "seq_con0_before", "seq_con0_stop", "seq_con0_back", "seq_irq_at_stop",
          "seq_irq_at_back"]
    f += ["a_state", "a_presses", "a_con0_before", "a_con0_cleared", "a_con0_set", "a_con0_back"]
    f += ["b_state", "b_presses", "b_clk_before", "b_clk_set", "b_clk_back", "refused"]
    f += ["core1_last_moved_beat"]
    marks = ["rel", "pre", "post", "p10", "p100", "s0", "s1", "poll", "key", "k10", "k100", "page", "now"]
    f += ["mark_beat_" + m for m in marks]
    f += ["mark_core1_" + m for m in marks]
    f += ["corex2_%02X" % (0x80 + i) for i in range(16)]
    for k in ("rec", "seq", "a", "b"):
        for w in ("before", "after"):
            f += ["%s_%s_%s" % (k, w, v) for v in ("CON0", "CLK_CON2", "irq", "core1")]
    return f


def _layout2():
    """Layout 2 (since clean-br17-audio4): layout 1 with the snapshots of
    six steps (H and I too), then steps H and I."""
    f = _layout1()[:-32]
    for k in ("rec", "seq", "a", "b", "h", "i"):
        for w in ("before", "after"):
            f += ["%s_%s_%s" % (k, w, v) for v in ("CON0", "CLK_CON2", "irq", "core1")]
    f += ["h_state", "h_presses", "h_measures", "h_gate_cycles", "h_clk1_before", "h_clk1_bus", "h_clk1_audio",
          "h_clk1_back", "h_gpcnt_before", "h_gpcnt_bus", "h_gpcnt_audio", "h_gpcnt_back", "h_bus_num1",
          "h_bus_num2", "h_bus_timeouts", "h_bus_clk2", "h_audio_num1", "h_audio_num2", "h_audio_timeouts",
          "h_audio_clk2", "CLK_CON1_now", "GPCNT_CON_now", "GPCNT_NUM_now"]
    f += ["i_state", "i_presses", "i_bit10"]
    f += ["i_al1_before_CON%d" % i for i in range(4)]
    f += ["i_al1_after_CON%d" % i for i in range(4)]
    f += ["i_al1_back_CON0", "i_clk2_before", "i_clk2_set11", "i_clk2_set10", "i_clk2_back", "i_b15_flips",
          "i_pend", "i_poll_beats", "i_halves_per_s_x10"]
    f += ["AL1_CON%d_now" % i for i in range(4)]
    f += ["clk2_steps_taken"]
    return f


FIELDS = {1: _layout1(), 2: _layout2()}


def derived(fields):
    """What step H's counts say: the bus count per gate cycle (7.5
    expected, HW-119 over HW-54) and the audio clock in MHz (the gate is
    the 24 MHz crystal)."""
    out = []
    gate = fields.get("h_gate_cycles")
    if gate and fields.get("h_presses"):
        out.append("H: bus %.4f x the gate (7.5 expected); audio clock %.4f MHz (about 11.29, or 12.31 with bit 8, if it is the"
                   " links' clock)" % (fields["h_bus_num2"] / gate, fields["h_audio_num2"] * 24.0 / gate))
    return out

# Shown in decimal; every other field in hex.
DECIMAL = {"h_state", "h_presses", "h_measures", "h_gate_cycles", "h_bus_num1", "h_bus_num2", "h_bus_timeouts",
           "h_audio_num1", "h_audio_num2", "h_audio_timeouts", "GPCNT_NUM_now", "i_state", "i_presses", "i_bit10",
           "i_b15_flips", "i_pend", "i_poll_beats", "i_halves_per_s_x10", "clk2_steps_taken", "core1_count", "store_count", "store_put", "log_found_at_start", "log_fails", "irq", "alt",
           "b15_flips", "pend", "fps_x10", "halves", "master", "gain", "tone_on", "storm_beat",
           "audio_started_beat", "rec_state", "rec_presses", "seq_state", "seq_presses", "seq_irq_at_stop",
           "seq_irq_at_back", "a_state", "a_presses", "b_state", "b_presses", "refused", "core1_last_moved_beat"}
STATES = {"rec_state": ("not taken", "taken", "undone"), "a_state": ("not taken", "taken", "undone"),
          "h_state": ("not taken", "taken", "undone"), "i_state": ("not taken", "taken", "undone"),
          "b_state": ("not taken", "taken", "undone"), "seq_state": ("running", "stopped", "put back")}


def _decimal(name):
    return name in DECIMAL or name.startswith(("mark_", "flash_status")) or name.endswith(("_irq", "_core1"))


def _text(b):
    return b.split(b"\0", 1)[0].decode("ascii", "replace")


def records(image):
    """Every record whose magic and CRC hold, sorted by sequence: dicts
    with offset, seq, beat, build, label, layout, fields (name to value)."""
    found, bad = [], []
    for off in range(0, len(image) - REC + 1, 4):
        if struct.unpack_from("<I", image, off)[0] != MAGIC:
            continue
        r = image[off:off + REC]
        crc = struct.unpack_from("<I", r, REC - 4)[0]
        if zlib.crc32(r[:REC - 4]) & 0xFFFFFFFF != crc:
            # Outside the region the magic is most likely the firmware's own
            # constant in its image: only the region's are counted.
            if LOG_BASE <= off < LOG_END:
                bad.append(off)
            continue
        w = struct.unpack("<%dI" % (REC // 4), r)
        layout, n = w[1] & 0xFFFF, w[1] >> 16
        names = FIELDS.get(layout, [])
        vals = w[HEAD:HEAD + n]
        fields = {(names[i] if i < len(names) else "field_%d" % i): v for i, v in enumerate(vals)}
        found.append({"offset": off, "seq": w[2], "beat": w[3], "build": _text(r[16:32]),
                      "label": _text(r[32:48]), "layout": layout, "count": n, "known": layout in FIELDS
                      and n == len(names), "fields": fields})
    found.sort(key=lambda x: x["seq"])
    return found, bad


def diagnose(image, bad):
    """What the log's region holds, when no record is valid."""
    lines = []
    if len(image) < LOG_END:
        return ["the image is %d bytes: it doesn't reach the log's region (0x%05X to 0x%05X)"
                % (len(image), LOG_BASE, LOG_END - 1)]
    region = image[LOG_BASE:LOG_END]
    erased = sum(1 for s in range(0, len(region), SECTOR) if region[s:s + SECTOR] == b"\xff" * SECTOR)
    if erased == LOG_SECTORS:
        lines.append("the log's region (0x%05X to 0x%05X) is all 0xFF: erased, and nothing was written there"
                     % (LOG_BASE, LOG_END - 1))
    else:
        lines.append("the log's region (0x%05X to 0x%05X): %d of %d sectors all 0xFF, the rest holding other"
                     " bytes" % (LOG_BASE, LOG_END - 1, erased, LOG_SECTORS))
    if bad:
        lines.append("the magic \"SBRL\" found at %d place(s) in the region with a CRC that fails, first at"
                     " 0x%05X" % (len(bad), bad[0]))
    else:
        lines.append("the magic \"SBRL\" found nowhere in the region: what was written doesn't read back as"
                     " written (scrambled?), or nothing was written")
    return lines


def show(rs, all_fields):
    names = []
    for r in rs:
        for k in r["fields"]:
            if k not in names:
                names.append(k)
    if not all_fields:
        names = [k for k in names if any(r["fields"].get(k) for r in rs)]
    for r in rs:
        print("#%d  beat %d  %s  build %s  at 0x%05X%s" % (r["seq"], r["beat"], r["label"], r["build"],
              r["offset"], "" if r["known"] else "  (layout %d, %d fields: names not known)"
              % (r["layout"], r["count"])))
        if not LOG_BASE <= r["offset"] < LOG_END:
            print("    outside the log's region")
        cells = []
        for k in names:
            if k not in r["fields"]:
                continue
            v = r["fields"][k]
            if k in STATES and v < 3:
                s = "%s %s" % (k, STATES[k][v])
            elif _decimal(k):
                s = "%s %d" % (k, v)
            else:
                s = "%s %08X" % (k, v)
            cells.append(s)
        line = "   "
        for c in cells:
            if len(line) + len(c) + 2 > 100:
                print(line)
                line = "   "
            line += " " + c + " "
        if line.strip():
            print(line)
        for d in derived(r["fields"]):
            print("    " + d)


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    opts = {a for a in argv if a.startswith("--")}
    if len(args) != 1 or opts - {"--all", "--json"}:
        print(__doc__.strip().split("\n\n")[1], file=sys.stderr)
        return 2
    with open(args[0], "rb") as f:
        image = f.read()
    rs, bad = records(image)
    if "--json" in opts:
        print(json.dumps({"records": rs, "bad_crc": bad}))
        return 0 if rs else 1
    if not rs:
        print("no valid report record in %s" % args[0])
        for line in diagnose(image, bad):
            print("  " + line)
        return 1
    print("%d record(s) in %s, #%d to #%d%s" % (len(rs), args[0], rs[0]["seq"], rs[-1]["seq"],
          "; %d more with the magic but a failing CRC" % len(bad) if bad else ""))
    show(rs, "--all" in opts)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
