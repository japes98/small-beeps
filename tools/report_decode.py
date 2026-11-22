#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
"""Decodes the hardware build's report log from a flash image.

    report_decode.py IMAGE [--all] [--json]

IMAGE is a whole flash read back from a unit (1 MiB) or fwtest's flash.bin.
The log (firmware/src/hw_report.c, SB_HW_REPORT; clean-br17-report1) is a
ring of 96 sectors ending at 0x93FFF (since clean-br17-audio6; 64 in
audio5), of 2048-byte records (since layout 3, clean-br17-audio5);
layouts 1 and 2 were 1024-byte records in 32 sectors, and are still read. Every 4-byte
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
REC = 4096                  # HW_LOG_REC, since layout 6 (audio7); 2048 for layouts 3 to 5, 1024 before
REC_OF = {1: 1024, 2: 1024, 3: 2048, 4: 2048, 5: 2048, 6: 4096, 7: 4096, 8: 4096}   # a record's size by its layout
HEAD = 12                   # HW_LOG_HEAD
LOG_END = 0x94000           # HW_LOG_END
LOG_SECTORS = 96            # HW_LOG_SECTORS, since audio6 (64 in audio5, 32 before)
LOG_BASE = LOG_END - LOG_SECTORS * 4096
SECTOR = 4096


def _layout1():
    """Layout 1's field names, in the firmware's order (hw_report.c's
    fields, then hw_audio.c's hw_audio_report)."""
    f = ["core1_count", "C1_CON", "store_count", "store_put", "WIN_CON", "flash_id", "flash_status1",
         "flash_status2", "log_found_at_start", "log_fails"]
    f += ["PLL2_CON0", "CLK_CON2", "DAA_CON0", "DAA_CON1", "DAA_CON2", "DAA_CON3", "DAA_CON7", "ADA_CON0",
          "ADA_CON1", "ADA_CON2", "DAC_CON", "AL0_CON0", "AL0_CON1", "AL0_CON2", "AL0_CON3", "MAP0",
          "MAP1", "PC_OUT", "PC_DIR", "PC_DIE", "PC_PU", "PC_PD"]
    f += ["CLK_CON0", "CLK_CON1", "SYS_DIV", "PLL_CON0", "PLL_CON1", "PLL2_CON1"]
    f += ["MAP%d" % i for i in range(2, 9)]   # JL_IOMAP CON2 to CON8, as the screen names them
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


K_LABELS = ("in3_bus", "in1_src", "in5_audio", "in6_wireless", "in7_usb", "own480", "in5_dac1", "in5_dac2",
            "in5_dac3", "in5_dac_back")


def _layout3():
    """Layout 3 (since clean-br17-audio5): layout 2 with the snapshots of
    eight steps (K and J too), then steps K and J."""
    l2 = _layout2()
    at = len(_layout1()) - 32
    f = l2[:at]
    for k in ("rec", "seq", "a", "b", "h", "i", "k", "j"):
        for w in ("before", "after"):
            f += ["%s_%s_%s" % (k, w, v) for v in ("CON0", "CLK_CON2", "irq", "core1")]
    f += l2[at + 48:]
    f += ["k_state", "k_presses", "k_clk1_before", "k_gpcnt_before", "k_clk1_back", "k_gpcnt_back"]
    for m in K_LABELS:
        f += ["k_%s_%s" % (m, v) for v in ("clk1", "gpcnt", "num1", "num2", "timeouts", "clk2")]
    f += ["j_state", "j_sweeps", "j_tries", "j_reg", "j_bit", "j_before", "j_written", "j_read", "j_back",
          "j_b15_flips", "j_pend", "j_irq", "j_con0", "j_con2", "j_clk2", "j_clk2_at_sweep", "j_didnt_hold"]
    f += ["j_readback_CON1_b%d" % i for i in range(16)] + ["j_readback_CON3_b%d" % i for i in range(8)]
    f += ["AL0_CON1_now", "AL0_CON3_now"]
    return f


def _layout4():
    """Layout 4 (the build after audio5): layout 3, then the log's own
    health: the last write's error, the takes that found the chip busy,
    the verifies that failed once and read right the second time, the
    records written again after a failed write, the page programs whose
    wait said busy and were waited on again, the failed writes so far, and
    the last four failed writes."""
    f = _layout3() + ["log_last_err", "log_busy_waits", "log_glitches", "log_retries", "log_page_rewaits",
                      "log_fail_count"]
    for i in range(4):
        f += ["log_fail%d_%s" % (i, v) for v in ("seq", "slot", "err", "pages_differ", "first_byte", "bytes_read_ff",
                                                 "word_written", "word_read")]
    return f


D_STATES = ("not run", "done, no stop", "stopped", "BIT KEPT", "undone")
D_STOPS = ("none", "the matrix check failed with the bit set (undone)", "the link moved, the matrix right (bit kept)",
           "the link moved, the matrix check failed (undone)", "the check after the undo failed",
           "stopped by OCT-")
PA_REGS = ("OUT", "IN", "DIR", "DIE", "PU", "PD", "HD0", "HD")


def _layout5():
    """Layout 5 (clean-br17-audio6): layout 3, then step D, then layout 4's
    log health."""
    f = ["d_state", "d_sweeps", "d_tries", "d_bit", "d_stop", "d_phase", "d_clk2", "d_con5_before", "d_con5_written",
         "d_con5_read", "d_con5_back", "d_con5_after"]
    f += ["d_iomap_before_CON%d" % i for i in range(9)] + ["d_iomap_after_CON%d" % i for i in range(9)]
    for w in ("before", "set", "after"):
        f += ["d_pa_%s_%s" % (w, r) for r in PA_REGS]
    f += ["d_pa_in_watch_start", "d_pa_in_watch_end", "d_b15_flips", "d_pend", "d_irq"]
    for w in ("base", "set", "after"):
        f += ["d_rows_idle_%s" % w] + ["d_cells_%s_%d" % (w, i) for i in range(3)]
    f += ["d_check_set", "d_check_after"] + ["d_al0_CON%d" % i for i in range(4)]
    f += ["d_irq_now", "d_core1", "d_j_putback", "d_con5_now"]
    return _layout3() + f + _layout4()[len(_layout3()):]


L_STATES = ("not run", "KEPT, running", "undone by key", "put back (nothing moved)", "STOPPED")


def _layout6():
    """Layout 6 (clean-br17-audio7): layout 5 with set-ups L1 and L2 after
    step D, before layout 4's log health."""
    l5 = _layout5()
    health = len(_layout4()) - len(_layout3())
    f = ["l_state", "l_which", "l_runs", "l_stop", "l_phase", "l_stopped"]
    f += ["l_before_AL0_CON%d" % i for i in range(4)]
    f += ["l_len_read", "l_adr3_read", "l_len_used", "l_clk1", "l_clk2"]
    f += ["l_pa_before_%s" % r for r in PA_REGS] + ["l_irq_before", "l_core1_before"]
    f += ["l_expect_fps_x10", "l_expect_hps_x10_a", "l_expect_hps_x10_b"]
    f += ["l_wrote_%s" % w for w in ("CON0_stop", "CON3", "CON1", "CON0_run")]
    f += ["l_readback_%s" % w for w in ("CON0_stop", "CON3", "CON1", "CON0_run")]
    f += ["l_b15_flips", "l_pend", "l_irq", "l_span_units", "l_hps_x10", "l_fps_x10_a", "l_fps_x10_b"]
    f += ["l_rows_idle_base"] + ["l_cells_base_%d" % i for i in range(3)]
    f += ["l_rows_idle_set"] + ["l_cells_set_%d" % i for i in range(3)] + ["l_pa_set_%s" % r for r in PA_REGS]
    f += ["l_check_set", "l_rows_idle_after"] + ["l_cells_after_%d" % i for i in range(3)]
    f += ["l_pa_after_%s" % r for r in PA_REGS] + ["l_check_after"]
    f += ["l_back_CON0", "l_back_CON1", "l_back_CON3", "l_clk2_end", "l_core1_end"]
    return l5[:len(l5) - health] + f + l5[len(l5) - health:]


A8_PINS = ("PC0", "PC1", "PC2", "PC6", "PA4", "PA5", "PA6", "PA7", "PA8", "PA9", "PA10")
PORTS = "ABCDEFGH"
A8_EVENTS = 120


def _layout7():
    """Layout 7 (clean-br17-audio8): layout 6 with audio8's fields after
    L's, before layout 4's log health. Pin counts are each pin's changes of
    IN over a sample (A8_PINS), then the sample loop's passes and its
    sb_now() span (24 MHz units)."""
    l6 = _layout6()
    health = len(_layout4()) - len(_layout3())
    cnt = lambda pre: ["%s_%s" % (pre, n) for n in A8_PINS] + ["%s_passes" % pre, "%s_span_units" % pre]
    f = ["a8_boot", "a8_off", "a8_pcm16", "rec_watch_b15_flips", "rec_watch_irq", "rec_watch_clk2"]
    f += cnt("ctl")
    f += ["r2_state", "r2_presses", "r2_check"]
    for w in ("before", "set", "after"):
        f += ["r2_pc_%s_%s" % (w, r) for r in PA_REGS]
    f += ["s1_state", "s1_runs"] + cnt("s1a")
    f += ["rt_kind", "rt_bit", "rt_phase", "rt_stop"]
    f += ["rt_con0_%s" % w for w in ("before", "written", "read", "back")]
    f += ["rt_con5_%s" % w for w in ("before", "written", "read", "back")]
    f += ["rt_iomap_before_CON%d" % i for i in range(9)] + ["rt_iomap_after_CON%d" % i for i in range(9)]
    for w in ("base", "set", "after"):
        f += ["rt_rows_idle_%s" % w] + ["rt_cells_%s_%d" % (w, i) for i in range(3)]
    for w in ("before", "set", "after"):
        f += ["rt_pa_%s_%s" % (w, r) for r in PA_REGS]
    f += ["rt_pc_set_%s" % r for r in PA_REGS]
    f += ["rt_check_set", "rt_check_after"] + cnt("rt_s1") + cnt("rt_s2") + ["rt_b15_flips", "rt_irq"]
    f += ["sw_state", "sw_sweeps", "sw_tries", "sw_stop", "sw_pa_bits", "sw_nohold"]
    f += ["se_state", "se_runs", "se_readings"]
    for w in ("dir", "die", "in_start", "changed"):
        f += ["se_%s_P%s" % (w, c) for c in PORTS]
    f += ["se_count_%d" % i for i in range(64)] + ["se_events", "se_events_lost"]
    f += ["se_ev_%d" % i for i in range(A8_EVENTS)]
    return l6[:len(l6) - health] + f + l6[len(l6) - health:]


def _layout8():
    """Layout 8 (clean-br17-audio9): layout 7 with audio9's fields after
    audio8's, before layout 4's log health."""
    l7 = _layout7()
    health = len(_layout4()) - len(_layout3())
    f = ["a9_route", "a9_route_ups", "a9_route_downs", "a9_synth", "a9_synth_ons", "a9_s2", "a9_underruns_at_synth_on",
         "a9_late_halves", "a9_fill_max_units", "a9_fill_last_units", "a9_fallback_beat", "a9_engine_blocks",
         "audio_underruns", "audio_fill_max_units", "pb5_now", "pb5_raw_changes", "pb5_settled", "pb5_logged"]
    f += ["pb5_t_%d" % i for i in range(16)]
    f += ["daa7_boot", "daa7_route", "daa7_last", "daa7_reads", "daa7_changes"]
    f += ["a9_words_%s_%d" % (st, i) for st in ("both", "upper", "lower") for i in range(4)]
    f += ["midi_out_bytes"]
    return l7[:len(l7) - health] + f + l7[len(l7) - health:]


FIELDS = {1: _layout1(), 2: _layout2(), 3: _layout3(), 4: _layout4(), 5: _layout5(), 6: _layout6(), 7: _layout7(),
          8: _layout8()}
A9_ROUTE = ("not up", "UP", "down (key)", "UNDONE by the firmware", "no L2: not tried")
A9_S2 = ("both halves", "upper half only", "lower half only")
A8_OFF = ("on", "not an audio8 build", "L2 not running", "OFF: a check after an undo failed")
S1_STATES = ("not run", "KEPT: port C moves", "port C still, undone", "STOPPED, undone", "undone by key")
SW_STATES = ("not run", "done: port C never moved", "KEPT: port C moves", "STOPPED, undone", "undone by key")
A8_STOPS = ("none", "port C moved, port A still, check passed: kept", "PORT A MOVED: undone before the check",
            "the matrix check failed: undone", "the check after the undo failed", "a key held (rows not idle): not run")


def _counts(f, pre):
    """A sample's counts as text: each pin's changes, and the changes a
    second they mean over the sample's span."""
    span = f.get("%s_span_units" % pre, 0)
    cs = [f.get("%s_%s" % (pre, n), 0) for n in A8_PINS]
    per = (lambda c: " (%d/s)" % (c * 24000000 // span)) if span else (lambda c: "")
    return ("%s: " % pre + ", ".join("%s %d%s" % (n, c, per(c) if c else "") for n, c in zip(A8_PINS, cs))
            + "; %d passes in %.2f ms" % (f.get("%s_passes" % pre, 0), span / 24000.0))


def sense_events(f):
    """The sense scan's kept events as (ms, port letter, bit, level)."""
    out = []
    for i in range(min(f.get("se_events", 0), A8_EVENTS)):
        e = f["se_ev_%d" % i]
        out.append((e >> 16, PORTS[e >> 4 & 7], e & 15, e >> 8 & 1))
    return out


def sense_counts(f):
    """Each changed bit's change count: {"PC7": n, ...}."""
    out = {}
    for p in range(8):
        for b in range(16):
            i = 16 * p + b
            n = f.get("se_count_%d" % (i // 2), 0) >> (16 * (i & 1)) & 0xFFFF
            if n:
                out["P%s%d" % (PORTS[p], b)] = n
    return out
LOG_ERRORS = {0: "none", 1: "no flash (no round trip)", 2: "image too long", 3: "erase", 4: "program", 5: "verify",
              6: "chip busy at the take"}


def bad_record(image, off):
    """What a record whose CRC fails holds: its header as written (magic,
    layout, field count, sequence, beat, build, label), its stored CRC and
    the CRC of what is there, and which 256-byte pages read all 0xFF (a
    program cut short or ignored) or hold other bytes."""
    w1 = struct.unpack_from("<I", image, off + 4)[0]
    size = REC_OF.get(w1 & 0xFFFF, REC)
    r = image[off:off + size]
    pages = []
    for p in range(0, len(r), 256):
        page = r[p:p + 256]
        pages.append("F" if page == b"\xff" * len(page) else "0" if page == bytes(len(page)) else "d")
    return {"offset": off, "slot": (off - LOG_BASE) // size if LOG_BASE <= off < LOG_END else None,
            "layout": w1 & 0xFFFF, "count": w1 >> 16, "seq": struct.unpack_from("<I", r, 8)[0],
            "beat": struct.unpack_from("<I", r, 12)[0], "build": _text(r[16:32]), "label": _text(r[32:48]),
            "crc_stored": struct.unpack_from("<I", r, size - 4)[0],
            "crc_now": zlib.crc32(r[:size - 4]) & 0xFFFFFFFF, "pages": "".join(pages)}


def derived(fields):
    """What step H's counts say: the bus count per gate cycle (7.5
    expected, HW-119 over HW-54) and the audio clock in MHz (the gate is
    the 24 MHz crystal)."""
    out = []
    f = fields
    if "a9_route" in f and (f.get("a9_route") or f.get("daa7_reads")):
        out.append("audio9: route %s (up %d, down %d); %s, S2 %s; late halves %d since the synth came on, longest fill"
                   " %.1f us (a half is 2902 us), fallback %s; engine blocks %d; underruns %d" % (
                       A9_ROUTE[min(f["a9_route"], 4)], f["a9_route_ups"], f["a9_route_downs"],
                       "SYNTH" if f["a9_synth"] else "tone", A9_S2[min(f["a9_s2"], 2)], f["a9_late_halves"],
                       f["a9_fill_max_units"] / 24.0, "at beat %d" % f["a9_fallback_beat"] if f["a9_fallback_beat"]
                       else "no", f["a9_engine_blocks"], f["audio_underruns"]))
        n = f["pb5_raw_changes"]
        times = [f["pb5_t_%d" % (i % 16)] for i in range(max(0, n - 16), n)]
        out.append("PB5 %d (settled %d), %d changes, %d written; last change beats %s; DAA_CON7 %08X at start-up,"
                   " %08X after the route, %08X last, %d reads, %d changes; MIDI out bytes %d" % (
                       f["pb5_now"], f["pb5_settled"], n, f["pb5_logged"], times, f["daa7_boot"], f["daa7_route"],
                       f["daa7_last"], f["daa7_reads"], f["daa7_changes"], f["midi_out_bytes"]))
    if f.get("a8_boot"):
        out.append("audio8: %s; tone %s" % (A8_OFF[min(f["a8_off"], 3)], "16-bit (a word a frame)" if f["a8_pcm16"]
                                             else "fwtest's layout"))
        if f.get("rec_watch_clk2"):
            out.append("REC watch: CLK_CON2 %08X; b15 %d, irq %d in the watch: %s" % (
                f["rec_watch_clk2"], f["rec_watch_b15_flips"], f["rec_watch_irq"],
                "the link runs" if f["rec_watch_b15_flips"] or f["rec_watch_irq"] else "THE LINK STOPPED"))
        if f.get("r2_presses"):
            out.append("R2: %s, check %d; port C OUT %04X>%04X>%04X DIR %04X>%04X>%04X DIE %04X>%04X>%04X"
                       " (before>set>after)" % (("not run", "SET", "undone")[min(f["r2_state"], 2)], f["r2_check"],
                                                f["r2_pc_before_OUT"], f["r2_pc_set_OUT"], f["r2_pc_after_OUT"],
                                                f["r2_pc_before_DIR"], f["r2_pc_set_DIR"], f["r2_pc_after_DIR"],
                                                f["r2_pc_before_DIE"], f["r2_pc_set_DIE"], f["r2_pc_after_DIE"]))
            out.append("    " + _counts(f, "ctl"))
        if f.get("s1_runs"):
            out.append("step 1: %s; " % S1_STATES[min(f["s1_state"], 4)] + _counts(f, "s1a"))
        if f.get("sw_sweeps"):
            out.append("sweep: %s, %d tries; port A moved at bits %08X; bits not read back set %08X"
                       % (SW_STATES[min(f["sw_state"], 4)], f["sw_tries"], f["sw_pa_bits"], f["sw_nohold"]))
        if f.get("rt_kind"):
            bad = lambda b: "ok" if not b else "BAD (" + ", ".join(n for i, n in enumerate(
                ("idle rows", "cells", "port A regs", "not back", "JL_IOMAP not back", "port A moved")) if b >> i & 1) + ")"
            out.append("last routed try: %s (step %d): %s; CON0 %04X>%04X>%04X back %04X; CON5 %08X>%08X>%08X back %08X;"
                       " check %s, after %s; b15 %d, irq %d" % (
                           "step 1 (b)" if f["rt_kind"] == 1 else "sweep bit %d" % f["rt_bit"], f["rt_phase"],
                           A8_STOPS[min(f["rt_stop"], 5)], f["rt_con0_before"], f["rt_con0_written"], f["rt_con0_read"],
                           f["rt_con0_back"], f["rt_con5_before"], f["rt_con5_written"], f["rt_con5_read"],
                           f["rt_con5_back"], bad(f["rt_check_set"]), bad(f["rt_check_after"]), f["rt_b15_flips"],
                           f["rt_irq"]))
            out.append("    " + _counts(f, "rt_s1"))
            if f.get("rt_s2_passes"):
                out.append("    " + _counts(f, "rt_s2"))
        if f.get("se_runs"):
            out.append("sense: %d readings; changed: %s; DIE: %s" % (
                f["se_readings"], " ".join("P%s %04X" % (c, f["se_changed_P%s" % c]) for c in PORTS
                                           if f["se_changed_P%s" % c]) or "nothing",
                " ".join("P%s %04X" % (c, f["se_die_P%s" % c] & 0xFFFF) for c in PORTS)))
            cn = sense_counts(f)
            if cn:
                out.append("    changes by bit: " + ", ".join("%s %d" % kv for kv in cn.items()))
            ev = sense_events(f)
            if ev:
                out.append("    events (ms port bit level): " + ", ".join("%d P%s%d=%d" % e for e in ev)
                           + ("; %d not kept" % f["se_events_lost"] if f.get("se_events_lost") else ""))
    if fields.get("l_runs"):
        out.append("L%d: %s; wrote CON3 %02X CON1 %04X CON0 %04X, read back %02X %04X %04X; b15 %d, irq %d; %.1f halves"
                   " a second: %.1f frames a second if a half is LEN frames (a), %.1f if LEN/2 (b); expected %.1f (LEN %d:"
                   " %.1f or %.1f halves a second); put back %04X %04X %02X; CLK_CON2 %08X"
                   % (fields["l_which"], L_STATES[min(fields["l_state"], 4)], fields["l_wrote_CON3"],
                      fields["l_wrote_CON1"], fields["l_wrote_CON0_run"], fields["l_readback_CON3"],
                      fields["l_readback_CON1"], fields["l_readback_CON0_run"], fields["l_b15_flips"], fields["l_irq"],
                      fields["l_hps_x10"] / 10.0, fields["l_fps_x10_a"] / 10.0, fields["l_fps_x10_b"] / 10.0,
                      fields["l_expect_fps_x10"] / 10.0, fields["l_len_used"], fields["l_expect_hps_x10_a"] / 10.0,
                      fields["l_expect_hps_x10_b"] / 10.0, fields["l_back_CON0"], fields["l_back_CON1"],
                      fields["l_back_CON3"], fields["l_clk2"]))
    if fields.get("d_sweeps"):
        bad = lambda b: "ok" if not b else "BAD (" + ", ".join(n for i, n in enumerate(
            ("idle rows", "cells", "port A", "CON5 not back", "JL_IOMAP not back")) if b >> i & 1) + ")"
        out.append("D: %s, sweep %d, try %d of bit %d (step %d): CON5 %08X written %08X read back %08X put back %08X;"
                   " b15 %d, pend %d, irq %d; check with the bit %s, after the undo %s; stop: %s; CLK_CON2 %08X"
                   % (D_STATES[min(fields["d_state"], 4)], fields["d_sweeps"], fields["d_tries"], fields["d_bit"],
                      fields["d_phase"], fields["d_con5_before"], fields["d_con5_written"], fields["d_con5_read"],
                      fields["d_con5_back"], fields["d_b15_flips"], fields["d_pend"], fields["d_irq"],
                      bad(fields["d_check_set"]), bad(fields["d_check_after"]), D_STOPS[min(fields["d_stop"], 5)],
                      fields["d_clk2"]))
    gate = fields.get("h_gate_cycles")
    if gate and fields.get("k_presses") and fields.get("k_state") == 1:
        out.append("K: " + ", ".join("%s %.3f MHz" % (m, fields["k_%s_num2" % m] * 24.0 / gate) for m in K_LABELS))
    if fields.get("j_sweeps"):
        out.append("J: %s; last try %s bit %d: wrote %04X, read back %04X, put back %04X; b15 %d, irq %d; CLK_CON2 at"
                   " the sweep %08X" % (("not run", "done, none moved", "MOVED, bit left set", "aborted", "undone")
                                        [min(fields["j_state"], 4)], "CON1" if fields["j_reg"] == 1 else "CON3",
                                        fields["j_bit"], fields["j_written"], fields["j_read"], fields["j_back"],
                                        fields["j_b15_flips"], fields["j_irq"], fields["j_clk2_at_sweep"]))
    if gate and fields.get("h_presses"):
        out.append("H: bus %.4f x the gate (7.5 expected); audio clock %.4f MHz (about 11.29, or 12.31 with bit 8, if it is the"
                   " links' clock)" % (fields["h_bus_num2"] / gate, fields["h_audio_num2"] * 24.0 / gate))
    return out

# Shown in decimal; every other field in hex.
DECIMAL = {"a9_route", "a9_route_ups", "a9_route_downs", "a9_synth", "a9_synth_ons", "a9_s2", "a9_underruns_at_synth_on",
           "a9_late_halves", "a9_fill_max_units", "a9_fill_last_units", "a9_fallback_beat", "a9_engine_blocks",
           "audio_underruns", "audio_fill_max_units", "pb5_now", "pb5_raw_changes", "pb5_settled", "pb5_logged",
           "daa7_reads", "daa7_changes", "midi_out_bytes", "a8_off", "rec_watch_b15_flips", "rec_watch_irq", "r2_state", "r2_presses", "s1_state", "s1_runs", "rt_kind",
           "rt_bit", "rt_phase", "rt_stop", "rt_b15_flips", "rt_irq", "sw_state", "sw_sweeps", "sw_tries", "sw_stop",
           "se_state", "se_runs", "se_readings", "se_events", "se_events_lost", "l_state", "l_which", "l_runs", "l_stop", "l_phase", "l_stopped", "l_len_read", "l_len_used", "l_irq_before",
           "l_core1_before", "l_expect_fps_x10", "l_expect_hps_x10_a", "l_expect_hps_x10_b", "l_b15_flips", "l_pend",
           "l_irq", "l_span_units", "l_hps_x10", "l_fps_x10_a", "l_fps_x10_b", "l_core1_end", "d_state", "d_sweeps", "d_tries", "d_bit", "d_stop", "d_phase", "d_b15_flips", "d_pend", "d_irq", "d_irq_now",
           "d_core1", "log_last_err", "log_busy_waits", "log_glitches", "log_retries", "log_page_rewaits", "log_fail_count", "k_state", "k_presses", "j_state", "j_sweeps", "j_tries", "j_reg", "j_bit", "j_b15_flips", "j_pend", "j_irq",
           "h_state", "h_presses", "h_measures", "h_gate_cycles", "h_bus_num1", "h_bus_num2", "h_bus_timeouts",
           "h_audio_num1", "h_audio_num2", "h_audio_timeouts", "GPCNT_NUM_now", "i_state", "i_presses", "i_bit10",
           "i_b15_flips", "i_pend", "i_poll_beats", "i_halves_per_s_x10", "clk2_steps_taken", "core1_count", "store_count", "store_put", "log_found_at_start", "log_fails", "irq", "alt",
           "b15_flips", "pend", "fps_x10", "halves", "master", "gain", "tone_on", "storm_beat",
           "audio_started_beat", "rec_state", "rec_presses", "seq_state", "seq_presses", "seq_irq_at_stop",
           "seq_irq_at_back", "a_state", "a_presses", "b_state", "b_presses", "refused", "core1_last_moved_beat"}
STATES = {"rec_state": ("not taken", "taken", "undone"), "a_state": ("not taken", "taken", "undone"),
          "h_state": ("not taken", "taken", "undone"), "i_state": ("not taken", "taken", "undone"),
          "b_state": ("not taken", "taken", "undone"), "seq_state": ("running", "stopped", "put back")}


def _decimal(name):
    return name in DECIMAL or name.startswith(("mark_", "flash_status")) or name.endswith(tuple(
        "_" + n for n in A8_PINS) + ("_passes", "_span_units")) or name.endswith(
        ("_irq", "_core1", "_num1", "_num2", "_timeouts", "_seq", "_slot", "_err", "_first_byte", "_bytes_read_ff"))


def _text(b):
    return b.split(b"\0", 1)[0].decode("ascii", "replace")


def records(image):
    """Every record whose magic and CRC hold, sorted by sequence: dicts
    with offset, seq, beat, build, label, layout, fields (name to value)."""
    found, bad = [], []
    for off in range(0, len(image) - 1024 + 1, 4):
        if struct.unpack_from("<I", image, off)[0] != MAGIC:
            continue
        size = REC_OF.get(struct.unpack_from("<I", image, off + 4)[0] & 0xFFFF, REC)
        r = image[off:off + size]
        if len(r) < size:
            continue
        crc = struct.unpack_from("<I", r, size - 4)[0]
        if zlib.crc32(r[:size - 4]) & 0xFFFFFFFF != crc:
            # Outside the region the magic is most likely the firmware's own
            # constant in its image: only the region's are counted.
            if LOG_BASE <= off < LOG_END:
                bad.append(off)
            continue
        w = struct.unpack("<%dI" % (size // 4), r)
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
    shown_fails = 0
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
        f = r["fields"]
        if f.get("log_fail_count", 0) == shown_fails:
            continue
        shown_fails = f.get("log_fail_count", 0)
        for i in range(4):
            if f.get("log_fail%d_err" % i):
                print("    failed write %d: #%d slot %d, %s; pages differing %02X, first at byte %d, %d bytes read 0xFF;"
                      " wrote %08X, read %08X" % (i, f["log_fail%d_seq" % i], f["log_fail%d_slot" % i],
                                                 LOG_ERRORS.get(f["log_fail%d_err" % i], "?"),
                                                 f["log_fail%d_pages_differ" % i], f["log_fail%d_first_byte" % i],
                                                 f["log_fail%d_bytes_read_ff" % i], f["log_fail%d_word_written" % i],
                                                 f["log_fail%d_word_read" % i]))


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
    show_bad(image, bad, rs)
    return 0


def show_bad(image, bad, rs):
    """Each record whose CRC fails: where, its header, and its pages (F all
    0xFF, 0 all zero, d other bytes); then what the firmware's own records
    say of failed writes (layout 4)."""
    if not bad:
        return
    print("records with the magic but a failing CRC (pages: F all 0xFF, 0 all zero, d other bytes):")
    for off in bad:
        b = bad_record(image, off)
        blank = [i for i, c in enumerate(b["pages"]) if c == "F"]
        print("  at 0x%05X (slot %s): #%d beat %d %s build %s, layout %d, %d fields; CRC stored %08X, of what is"
              " there %08X; pages %s; blank (all 0xFF): %s" % (b["offset"], b["slot"], b["seq"], b["beat"], b["label"],
                                                               b["build"], b["layout"], b["count"], b["crc_stored"],
                                                               b["crc_now"], b["pages"],
                                                               ", ".join(map(str, blank)) or "none"))
    seen = rs[-1]["fields"] if rs else {}
    if "log_fail_count" in seen:
        print("  the firmware's own count, in record #%d: %d failed writes, %d retried, %d read glitches, %d busy"
              " at the take, %d page waits repeated" % (rs[-1]["seq"], seen["log_fail_count"], seen["log_retries"],
                                                        seen["log_glitches"], seen["log_busy_waits"],
                                                        seen["log_page_rewaits"]))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
