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
REC_OF = {1: 1024, 2: 1024, 3: 2048, 4: 2048, 5: 2048, 6: 4096, 7: 4096, 8: 4096, 9: 4096}   # a record's size by its layout
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


A10_FMTS = ("P", "U", "L", "N", "N'")


def _layout9():
    """Layout 9 (clean-br17-audio10): layout 8 with the sense scan's event
    list cut from 120 to 32, the first words kept for each of F's five
    formats (S2's three before), and audio10's fields after MIDI out's
    bytes, before layout 4's log health."""
    l8 = _layout8()
    health = len(_layout4()) - len(_layout3())
    body = [n for n in l8[:len(l8) - health]
            if not (n.startswith("se_ev_") and int(n[6:]) >= 32) and not n.startswith("a9_words_")]
    i = body.index("midi_out_bytes")
    words = ["a9_words_%s_%d" % (st, k) for st in A10_FMTS for k in range(4)]
    f = ["a10_fmt_changes"] + ["a10_fmt_t_%d" % k for k in range(8)]
    f += ["a10_fill_max_units", "a10_fill_max8_units", "a10_voices_max", "a10_soft_clipped", "a10_saturated"]
    f += ["m_value", "m_raw_at_change", "m_raw_now", "m_tone_gain", "m_synth_level", "m_changes", "m_raw_jumps",
          "m_raw_max_step", "m_ring_n"] + ["m_ring_%d" % k for k in range(40)]
    f += ["holds", "hold_n"] + ["hold_t_%d" % k for k in range(8)] + ["log_dropped", "scan_until"]
    return body[:i] + words + ["midi_out_bytes"] + f + body[i + 1:] + l8[len(l8) - health:]


A11_SETUPS = ("SDK", "old")
A11_CHANS = (0, 1, 3, 4, 5, 6, 7, 10, 11)


def _layout10():
    """Layout 10 (clean-br17-audio11): layout 9 without the sense scan's
    fields and F's change list (N is fixed), with audio11's after the scan
    hold's end, before layout 4's log health: the SARADC's set-up and its
    changes, each set-up's CON writes and conversion times, each kept
    channel's readings in each set-up (least << 16 | greatest, the count,
    the two values with the most readings as value << 22 | count, the
    rest), MASTER's raw reading at each ring entry, its jumps, the fill per
    algorithm, the level, and the large area's three lines."""
    l9 = _layout9()
    health = len(_layout4()) - len(_layout3())
    body = [n for n in l9[:len(l9) - health] if not n.startswith("se_") and not n.startswith("a10_fmt_t_")]
    f = ["adc_setup", "adc_set_n"] + ["adc_set_t_%d" % k for k in range(8)]
    f += ["sar_con_%s_%s" % (st, w) for st in A11_SETUPS for w in ("w1", "w2", "w3", "read")]
    for w in ("conv_n", "conv_timeouts", "conv_min_units", "conv_max_units", "conv_tight_units"):
        f += ["adc_%s_%s" % (w, st) for st in A11_SETUPS]
    f += ["adc_slot_max_units", "adc_passes"]
    for st in A11_SETUPS:
        for c in A11_CHANS:
            f += ["adc_%s_ch%d_%s" % (st, c, w) for w in ("minmax", "n", "v0", "v1", "rest")]
    f += ["m_raw_ring_%d" % k for k in range(20)] + ["m_jump_n"] + ["m_jump_t_%d" % k for k in range(8)]
    f += ["fill_alg_%d" % k for k in range(1, 11)] + ["m_level"] + ["big_%d" % k for k in range(12)]
    return body + f + l9[len(l9) - health:]


A12_MODES = ("?", "the test screen, then the instrument (SEL)", "the test screen")
A12_SWEEP = ("not run", "playing a chord", "waiting for a release", "done (all ten)", "stopped by the key")


def _layout11():
    """Layout 11 (clean-br17-audio12): layout 10 without what audio11
    settled (the set-up's change list, the old set-up's channels, MASTER's
    raw ring and jump list, the fill per algorithm), with audio12's after
    the large area, before layout 4's log health: the start, the sweep
    (its state, algorithm, runs, stop, chords; per algorithm the longest
    fill in 0.1 us with the voices then << 16, soft-clipped and saturated
    samples, late halves, the release's frames), and G's note-on list and
    ALGORITHM's turns."""
    l10 = _layout10()
    health = len(_layout4()) - len(_layout3())
    body = [n for n in l10[:len(l10) - health]
            if not n.startswith(("adc_set_t_", "adc_old_", "m_raw_ring_", "m_jump_t_", "fill_alg_"))]
    f = ["start_mode", "as_state", "as_alg", "as_runs", "as_stop", "as_chords"]
    for w in ("fill", "soft", "hard", "late", "rel_frames"):
        f += ["as_%s_%d" % (w, k) for k in range(1, 11)]
    f += ["g_note_n"] + ["g_note_%d" % k for k in range(16)] + ["g_turns", "g_turns_off", "g_turn_alg"]
    return body + f + l10[len(l10) - health:]


A13_STARTS = ("?", "the instrument from power-on", "the test screen (HOME held)")
A13_WORDS = ("CON0", "CON1", "IO_CON0", "IO_CON1", "IO_CON2")
A13_STATES = "abcde"
A13_STATE_NAMES = ("no cable", "a charger", "a computer on", "the computer asleep", "the cable out")


def _layout12():
    """Layout 12 (clean-br17-audio13): layout 11 without the old steps'
    snapshots and steps H, I, K, J, D, L1 and L2 (audio2 to audio7), with
    audio13's after audio12's, before layout 4's log health: the start;
    U2-A's readings of the USB block's five words (the app's start, a
    second later with its beat and the audio blocks then, the last key's);
    U2-B (the cable state, the run, the polls, state a's words, the last
    poll's, the state marks as beat << 3 | state, the changes as beat << 3
    | word then the value, each run's and state's bits ever and always set,
    the polls by state); U2-C (on, presses, readings and least << 16 |
    greatest by state and channel, time-outs, each turn-on's first
    readings, the log as value << 22 | state << 19 | ch13 << 18 | beat /
    64); ARP's steps (count, breaks, gaps, the shortest and longest gap in
    frames and sb_now units, the last, the longest chain's steps and ends,
    each step's frame count and sb_now)."""
    l11 = _layout11()
    health = len(_layout4()) - len(_layout3())
    a, b = l11.index("rec_before_CON0"), l11.index("a8_boot")
    body = l11[:a] + l11[b:len(l11) - health]
    f = ["a13_start"] + ["u2_boot_%s" % w for w in A13_WORDS] + ["u2_late_%s" % w for w in A13_WORDS]
    f += ["u2_late_beat", "u2_late_blocks"] + ["u2_key_%s" % w for w in A13_WORDS] + ["u2_key_beat", "u2_key_n"]
    f += ["u2_state", "u2_run", "u2_polls"] + ["u2_ref_%s" % w for w in A13_WORDS] + ["u2_last_%s" % w for w in A13_WORDS]
    f += ["u2_mark_n"] + ["u2_mark_%d" % k for k in range(16)] + ["u2_chg_n"]
    f += ["u2_chg_%d_%s" % (k, w) for k in range(24) for w in ("at", "value")]
    for kind in ("or", "and"):
        f += ["u2_%s_r%d_%s_%s" % (kind, r, st, w) for r in range(2) for st in A13_STATES for w in A13_WORDS]
    f += ["u2_seen_r0", "u2_seen_r1", "u2c_on", "u2c_toggles"]
    f += ["u2c_n_%s_ch%d" % (st, c) for st in A13_STATES for c in (12, 13)]
    f += ["u2c_mm_%s_ch%d" % (st, c) for st in A13_STATES for c in (12, 13)]
    f += ["u2c_timeouts"] + ["u2c_first_%d" % k for k in range(4)] + ["u2c_log_n"] + ["u2c_log_%d" % k for k in range(32)]
    f += ["arp_n", "arp_breaks", "arp_gaps", "arp_gmin_f", "arp_gmax_f", "arp_gmin_units", "arp_gmax_units",
          "arp_last_f", "arp_last_units", "arp_best_n", "arp_best_f0", "arp_best_u0", "arp_best_f1", "arp_best_u1"]
    f += ["arp_log_%d_%s" % (k, w) for k in range(48) for w in ("frames", "units")]
    return body + f + l11[len(l11) - health:]


A14_P_ADDRS = tuple(0x16A00 + 4 * i for i in range(4))


def _layout13():
    """audio14 (clean-br17-audio14): layout 12, then before the log's own
    health the block at 0x16A00's four words (P, read only) at the app's
    start, a second later and on U2-A's key; and R's counts: REC's ARP
    saves in the panel, the last save's result and number, and the records
    ARP turning off wrote."""
    l12 = _layout12()
    health = len(_layout4()) - len(_layout3())
    f = ["p_%s_%05X" % (when, a) for when in ("boot", "late", "key") for a in A14_P_ADDRS]
    f += ["arp_saves", "arp_save_err", "arp_save_seq", "arp_offs"]
    return l12[:len(l12) - health] + f + l12[len(l12) - health:]


# U3-U (clean-br17-u3u): the USB device's record, firmware/src/usb_midi.h's struct sb_usb_record, word by word;
# tools/seams_suite.py reads the same names from it.
USB_STAGES = ("cable", "step1_pins_ie", "step2_pads", "step3_nrst_clr", "step4_con1", "step5_phy", "step6_pulls",
              "step7_nrst_set", "irqs_off", "power", "ep0_buf", "intrusbe", "ep0_on", "irq", "sieie", "host_reset",
              "address", "configured", "first_in", "first_out", "stopped")
USB_REC = (["usb_magic", "usb_gap_units", "usb_poll_limit", "usb_state"] + ["usb_at_" + n for n in USB_STAGES]
           + ["usb_last_stage", "usb_giveup_stage", "usb_giveup_index", "usb_giveup_why", "usb_giveup_value",
              "usb_lines_first", "usb_lines_or", "usb_lines_set", "usb_lines_reads", "usb_cable", "usb_cable_run",
              "usb_cable_checks", "usb_cable_changes"] + ["usb_cable_log_%d" % k for k in range(8)]
           + ["usb_lines_after", "usb_rb_con0", "usb_rb_con1", "usb_rb_io_con0", "usb_irqs", "usb_spurious",
              "usb_resets", "usb_suspends", "usb_setups", "usb_stalls", "usb_last_setup_0", "usb_last_setup_1",
              "usb_address", "usb_configuration", "usb_rx_packets", "usb_rx_events", "usb_rx_dropped",
              "usb_tx_packets", "usb_tx_events", "usb_out_full", "usb_tx_underruns", "usb_rx_overruns",
              "usb_accesses", "usb_polls_max", "usb_addr_late", "usb_configs", "usb_gap_presses", "usb_attempt_n"]
           + ["usb_attempt_%d_%s" % (k, w) for k in range(8) for w in ("gap_flags", "reset", "last")]
           + ["usb_tx_variant", "usb_tx_done", "usb_rx_log_n"] + ["usb_rx_log_%d" % k for k in range(8)]
           + ["usb_tx_log_n"] + ["usb_tx_log_%d" % k for k in range(8)]
           + ["usb_frame_last", "usb_gone_n", "usb_back_n", "usb_irq_peak"])
# Try 2's record (layout 14, the owner's backups of 2026-11-23): the first 98 words.
USB_REC_TRY2 = USB_REC[:USB_REC.index("usb_tx_variant")]
USB_TX_WAYS = ("one buffer", "address each packet", "two buffers")
USB_STATES = ("waiting for a computer", "setting up", "set up", "GIVEN UP")
USB_WHYS = {1: "USB_NRST read clear at a port access", 2: "CON1 bit 15 never came", 3: "the interrupt kept coming"}


def _layout14():
    """U3-U's try 2 (clean-br17-u3u, d20756e7): layout 13 without ARP's
    step log (R is done), then before the log's own health the USB
    device's record as try 2 kept it (98 words). Try 1's own layout 14
    (71 words) was never flashed."""
    l13 = _layout13()
    health = len(_layout4()) - len(_layout3())
    body = [n for n in l13[:len(l13) - health] if not n.startswith("arp_log_")]
    return body + USB_REC_TRY2 + l13[len(l13) - health:]


def _layout15():
    """U3-U's try 3: layout 13 without ARP's step log and U2-C's log
    (HW-177), then before the log's own health the USB device's record
    (usb_midi.h)."""
    l13 = _layout13()
    health = len(_layout4()) - len(_layout3())
    body = [n for n in l13[:len(l13) - health] if not n.startswith(("arp_log_", "u2c_log"))]
    return body + USB_REC + l13[len(l13) - health:]


FIELDS = {1: _layout1(), 2: _layout2(), 3: _layout3(), 4: _layout4(), 5: _layout5(), 6: _layout6(), 7: _layout7(),
          8: _layout8(), 9: _layout9(), 10: _layout10(), 11: _layout11(), 12: _layout12(), 13: _layout13(),
          14: _layout14(), 15: _layout15()}
HOLDS = ("zero", "LED", "screen", "log", "scan")
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


def raw_at(f, k):
    """Layout 10: the raw reading at MASTER's ring entry k, as "/raw"."""
    if "m_raw_ring_0" not in f:
        return ""
    return "/r%d" % (f["m_raw_ring_%d" % (k % 40 // 2)] >> (16 * (k % 2)) & 0xFFFF)


def big_text(f):
    """The large area's three lines (E)."""
    b = b"".join(struct.pack("<I", f.get("big_%d" % k, 0)) for k in range(12))
    return [b[16 * i:16 * i + 16].split(b"\0")[0].decode("ascii", "replace") for i in range(3)]


def audio11_lines(f):
    us = lambda u: u / 24.0
    out = []
    n = f["adc_set_n"]
    sets = [f["adc_set_t_%d" % (k % 8)] for k in range(max(0, n - 8), n) if "adc_set_t_0" in f]
    out.append("audio11: SARADC set-up %s (%d changes: %s); the slot's longest service %.1f us, %d sweep passes"
               % (A11_SETUPS[min(f["adc_setup"], 1)], n,
                  ", ".join("beat %d %s" % (w >> 1, A11_SETUPS[w & 1]) for w in sets) or "none",
                  us(f["adc_slot_max_units"]), f["adc_passes"]))
    for st in A11_SETUPS:
        if "adc_%s_ch0_n" % st not in f:
            continue
        out.append("  %s: CON %04X %04X %04X, read after %04X; %d conversions, %d timed out; start to bit 7 seen"
                   " %.1f to %.1f us (the slot's 83 us steps), by a tight poll %.1f us"
                   % (st, f["sar_con_%s_w1" % st], f["sar_con_%s_w2" % st], f["sar_con_%s_w3" % st],
                      f["sar_con_%s_read" % st], f["adc_conv_n_%s" % st], f["adc_conv_timeouts_%s" % st],
                      us(f["adc_conv_min_units_%s" % st]), us(f["adc_conv_max_units_%s" % st]),
                      us(f["adc_conv_tight_units_%s" % st])))
        for c in A11_CHANS:
            k = "adc_%s_ch%d_" % (st, c)
            if not f[k + "n"]:
                continue
            vs = [f[k + w] for w in ("v0", "v1") if f[k + w] & 0x3FFFFF]
            out.append("    ch%-2d %d readings, %d to %d: %s%s" % (
                c, f[k + "n"], f[k + "minmax"] >> 16, f[k + "minmax"] & 0xFFFF,
                ", ".join("%d x%d" % (v >> 22, v & 0x3FFFFF) for v in vs),
                ", other values x%d" % f[k + "rest"] if f[k + "rest"] else ""))
    n = f["m_jump_n"]
    js = [f["m_jump_t_%d" % (k % 8)] for k in range(max(0, n - 8), n) if "m_jump_t_0" in f]
    out.append("  MASTER's raw jumps (over 32): %d%s" % (n, ": " + ", ".join(
        "beat ~%d (mod 16384) %d->%d" % ((w >> 20) * 4, w >> 10 & 0x3FF, w & 0x3FF) for w in js) if js else ""))
    fa = [(k, f.get("fill_alg_%d" % k, 0)) for k in range(1, 11)]
    out.append("  fill per algorithm (us, any / with 8 voices): " + ", ".join(
        "A%d %.1f/%.1f" % (k, (w & 0xFFFF) / 10.0, (w >> 16) / 10.0) for k, w in fa if w))
    out.append("  level %.2f%% of full; large area: %s" % (f["m_level"] / 100.0, " | ".join(big_text(f))))
    if "as_state" in f:
        out += audio12_lines(f)
    if "a13_start" in f:
        out += audio13_lines(f)
    return out


def audio12_lines(f):
    mode = A12_MODES[min(f["start_mode"], 2)]
    if f.get("a13_start") == 1 and f["start_mode"] == 1:
        mode = "the instrument (from power-on)"
    out = ["audio12: running %s; sweep %s (algorithm %d, %d runs, %d chords%s)" % (
        mode, A12_SWEEP[min(f["as_state"], 4)], f["as_alg"], f["as_runs"],
        f["as_chords"], ", a stop asked" if f["as_stop"] else "")]
    for k in range(1, 11):
        w, r = f["as_fill_%d" % k], f["as_rel_frames_%d" % k]
        if not w and not r:
            continue
        out.append("  A%-2d longest fill %.1f us with %d voices; soft clipped %d, saturated %d, late %d; release %d"
                   " frames%s" % (k, (w & 0xFFFF) / 10.0, w >> 16, f["as_soft_%d" % k], f["as_hard_%d" % k],
                                  f["as_late_%d" % k], r & 0x7FFFFFFF, " (NOT ENDED: the bound)" if r >> 31 else ""))
    n = f["g_note_n"]
    ns = [f["g_note_%d" % (k % 16)] for k in range(max(0, n - 16), n)]
    out.append("  G: %d note ons; ALGORITHM turns taken %d, dropped (local off) %d, algorithm after the last %d;"
               " last (note voice read->voice local): %s" % (
                   n, f["g_turns"], f["g_turns_off"], f["g_turn_alg"],
                   " ".join("%d v%d A%d->A%d%s" % (w >> 24, w >> 16 & 0xFF, w >> 8 & 0xFF, w >> 1 & 0x7F,
                                                   "" if w & 1 else " LOCAL OFF") for w in ns)))
    return out


def _hexes(f, pre):
    return " ".join("%s %08X" % (w, f["%s_%s" % (pre, w)]) for w in A13_WORDS)


def audio13_lines(f):
    """audio13's U2-A, U2-B, U2-C and ARP, as the owner's run reads them."""
    us = lambda u: u / 24.0
    out = ["audio13: started %s" % A13_STARTS[min(f["a13_start"], 2)],
           "  U2-A at the app's start: %s" % _hexes(f, "u2_boot"),
           "  U2-A a second later (beat %d, %d audio blocks then): %s" % (
               f["u2_late_beat"], f["u2_late_blocks"], _hexes(f, "u2_late"))]
    if f["u2_key_n"]:
        out.append("  U2-A on the key (%d presses, the last at beat %d): %s" % (
            f["u2_key_n"], f["u2_key_beat"], _hexes(f, "u2_key")))
    if f["u2_polls"] or f["u2_mark_n"]:
        n = f["u2_mark_n"]
        marks = [f["u2_mark_%d" % (k % 16)] for k in range(max(0, n - 16), n)]
        out.append("  U2-B: state %s (%s), run %d, %d polls; marks: %s" % (
            A13_STATES[min(f["u2_state"], 4)], A13_STATE_NAMES[min(f["u2_state"], 4)], f["u2_run"] + 1, f["u2_polls"],
            ", ".join("beat %d %s" % (m >> 3, A13_STATES[min(m & 7, 4)]) for m in marks) or "none"))
        n = f["u2_chg_n"]
        chg = [(f["u2_chg_%d_at" % (k % 24)], f["u2_chg_%d_value" % (k % 24)]) for k in range(max(0, n - 24), n)]
        out.append("  U2-B: %d changes%s" % (n, ": " + ", ".join(
            "beat %d %s=%08X" % (a >> 3, A13_WORDS[min(a & 7, 4)], v) for a, v in chg) if chg else ""))
        for r in range(2):
            for i, st in enumerate(A13_STATES):
                seen = f["u2_seen_r%d" % r] >> (6 * i) & 63
                if not seen:
                    continue
                out.append("    run %d state %s (%d polls%s): %s" % (
                    r + 1, st, seen, "+" if seen == 63 else "", "; ".join(
                        "%s set %08X always %08X" % (w, f["u2_or_r%d_%s_%s" % (r, st, w)], f["u2_and_r%d_%s_%s" % (r, st, w)])
                        for w in A13_WORDS)))
    if f["u2c_toggles"]:
        out.append("  U2-C: %s, %d presses, %d timed out; first readings after each turn-on (ch12/ch13): %s" % (
            "on" if f["u2c_on"] else "off", f["u2c_toggles"], f["u2c_timeouts"], ", ".join(
                "%s/%s" % tuple("-" if v == 0xFFFF else str(v) for v in (w >> 16, w & 0xFFFF))
                for w in (f["u2c_first_%d" % k] for k in range(4)) if w != 0xFFFFFFFF) or "none"))
        for st in A13_STATES:
            cs = [(c, f["u2c_n_%s_ch%d" % (st, c)], f["u2c_mm_%s_ch%d" % (st, c)]) for c in (12, 13)]
            if any(n for _, n, _ in cs):
                out.append("    state %s: %s" % (st, ", ".join(
                    "ch%d %d readings %d to %d" % (c, n, mm >> 16, mm & 0xFFFF) for c, n, mm in cs if n)))
        n = f["u2c_log_n"]
        log = [f["u2c_log_%d" % (k % 32)] for k in range(max(0, n - 32), n)]
        out.append("    logged (beat~ state ch value): " + ", ".join(
            "%d %s %d %d" % ((w & 0x3FFFF) * 64, A13_STATES[min(w >> 19 & 7, 4)], 12 + (w >> 18 & 1), w >> 22) for w in log))
    if f["arp_n"]:
        span_f, span_u = f["arp_best_f1"] - f["arp_best_f0"], (f["arp_best_u1"] - f["arp_best_u0"]) & 0xFFFFFFFF
        out.append("  ARP: %d steps, %d gaps, %d breaks; gap %d to %d frames, %.1f to %.1f us; the last %d frames, %.1f us"
                   % (f["arp_n"], f["arp_gaps"], f["arp_breaks"], f["arp_gmin_f"], f["arp_gmax_f"],
                      us(f["arp_gmin_units"]), us(f["arp_gmax_units"]), f["arp_last_f"], us(f["arp_last_units"])))
        if f["arp_best_n"] > 1 and span_u:
            out.append("    the longest chain: %d steps, %d frames in %.1f us: %.1f frames a second, %.3f ms a step"
                       % (f["arp_best_n"], span_f, us(span_u), span_f * 24e6 / span_u,
                          us(span_u) / 1000.0 / (f["arp_best_n"] - 1)))
        n = f["arp_n"]
        if "arp_log_0_frames" in f:   # layout 14 leaves ARP's step log out
            steps = [(f["arp_log_%d_frames" % (k % 48)], f["arp_log_%d_units" % (k % 48)])
                     for k in range(max(0, n - 48), n)]
            out.append("    steps (frames/us): " + " ".join("%d/%.0f" % (a, us(b)) for a, b in steps))
    if "p_boot_16A00" in f:
        out += audio14_lines(f)
    if "usb_magic" in f:
        out += u3u_lines(f)
    return out


def audio14_lines(f):
    """audio14's P (the block at 0x16A00) and R (the panel's ARP save)."""
    p = lambda when: " ".join("%05X=%08X" % (a, f["p_%s_%05X" % (when, a)]) for a in A14_P_ADDRS)
    b1_state = lambda when: "set" if f["p_%s_16A00" % when] & 2 else "clear"
    out = ["audio14: P, the block at 0x16A00, read only",
           "  at the app's start: %s (0x16A00 bit 1 %s)" % (p("boot"), b1_state("boot")),
           "  a second later: %s (0x16A00 bit 1 %s)" % (p("late"), b1_state("late"))]
    if f["u2_key_n"]:
        out.append("  on U2-A's key: %s" % p("key"))
    if f["arp_saves"] or f["arp_offs"]:
        if not (f["arp_save_seq"] or f["arp_save_err"]):
            last = "none before this record"
        elif f["arp_save_err"]:
            last = "the last NOT saved, %s" % LOG_ERRORS.get(f["arp_save_err"], "error %d" % f["arp_save_err"])
        else:
            last = "the last saved as #%d" % f["arp_save_seq"]
        out.append("  R: %d ARP saves by REC (%s), %d records on ARP off" % (f["arp_saves"], last, f["arp_offs"]))
    return out


def u3u_lines(f):
    """U3-U: the USB device's stages with their beats, the cable reading,
    the read-back after the set-up, a give-up, the counts."""
    out = ["U3-U: USB %s; the port's spacing %.1f us, bit 15 polled up to %d times" % (
        USB_STATES[f["usb_state"]] if f["usb_state"] < len(USB_STATES) else f["usb_state"],
        f["usb_gap_units"] / 24.0, f["usb_poll_limit"])]
    at = [(n, f["usb_at_" + n]) for n in USB_STAGES if f["usb_at_" + n]]
    out.append("  stages (beat): " + (", ".join("%s %d" % x for x in at) if at else "none"))
    if f["usb_cable_checks"]:
        log = [f["usb_cable_log_%d" % (k % 8)] for k in range(max(0, f["usb_cable_changes"] - 8),
                                                                f["usb_cable_changes"])]
        out.append("  the cable reading: %d checks, the last %s (%d of %d reads with CON0 bit 16 or 17 set, bits"
                   " %08X, first CON0 %08X), %d in a row steadily 0; changes (beat: reading): %s; once set up %d"
                   " changes of the lines" % (
                       f["usb_cable_checks"], {1: "steadily 0: a computer", 2: "not steadily 0"}.get(
                           f["usb_cable"], "none"), f["usb_lines_set"], f["usb_lines_reads"], f["usb_lines_or"],
                       f["usb_lines_first"], f["usb_cable_run"],
                       ", ".join("%d: %s" % (w >> 2, "computer" if w & 3 == 1 else "none") for w in log) or "none",
                       f["usb_lines_after"]))
    if f["usb_at_sieie"]:
        out.append("  read back after the set-up: CON0 %08X (bits 16-17 %d), CON1 %08X, IO CON0 %08X" % (
            f["usb_rb_con0"], f["usb_rb_con0"] >> 16 & 3, f["usb_rb_con1"], f["usb_rb_io_con0"]))
    if f["usb_giveup_why"]:
        out.append("  GAVE UP at stage %s, index %d: %s (read %08X); nothing more written to USB" % (
            USB_STAGES[f["usb_giveup_stage"]] if f["usb_giveup_stage"] < len(USB_STAGES) else f["usb_giveup_stage"],
            f["usb_giveup_index"], USB_WHYS.get(f["usb_giveup_why"], f["usb_giveup_why"]), f["usb_giveup_value"]))
    out.append("  interrupts %d (%d with no flag), resets %d, suspends %d, setups %d (last %08X %08X), stalls %d,"
               " address %d, configuration %d; in %d packets %d events (%d bytes dropped), out %d packets %d events"
               " (%d dropped); underruns %d, overruns %d; port accesses %d, most polls %d; address written late %d;"
               " babble: a device can't see it (HW-172)" % (
                   f["usb_irqs"], f["usb_spurious"], f["usb_resets"], f["usb_suspends"], f["usb_setups"],
                   f["usb_last_setup_0"], f["usb_last_setup_1"], f["usb_stalls"], f["usb_address"],
                   f["usb_configuration"], f["usb_rx_packets"], f["usb_rx_events"], f["usb_rx_dropped"],
                   f["usb_tx_packets"], f["usb_tx_events"], f["usb_out_full"], f["usb_tx_underruns"],
                   f["usb_rx_overruns"], f["usb_accesses"], f["usb_polls_max"], f["usb_addr_late"]))
    n = f["usb_attempt_n"]
    if n:
        att = []
        for k in range(max(1, n - 7), n + 1):
            w = f["usb_attempt_%d_gap_flags" % (k % 8)]
            got = [x for b, x in ((1, "address"), (2, "configured"), (4, "in"), (8, "out")) if w & b]
            att.append("#%d at beat %d, spacing %.0f us: %s (last at %d)" % (
                k, f["usb_attempt_%d_reset" % (k % 8)], (w >> 8) / 24.0, ", ".join(got) or "reset only",
                f["usb_attempt_%d_last" % (k % 8)]))
        out.append("  the host's attempts (%d; spacing key pressed %d times): %s" % (
            n, f["usb_gap_presses"], "; ".join(att)))
    if "usb_tx_variant" in f:
        n = f["usb_rx_log_n"]
        rx = [f["usb_rx_log_%d" % (k % 8)] for k in range(max(0, n - 8), n)]
        out.append("  the last packets in (RXCOUNT1/RXCOUNT2: events, RXCSR1): " + (", ".join(
            "%d/%d: %d, %02X" % (w & 0xFF, w >> 8 & 0xFF, w >> 16 & 0xFF, w >> 24) for w in rx) or "none"))
        n = f["usb_tx_log_n"]
        tx = [f["usb_tx_log_%d" % (k % 8)] for k in range(max(0, n - 8), n)]
        out.append("  out: %s; %d packets taken by the host; the last packets out (TXCSR1 before, bytes, way): %s" % (
            USB_TX_WAYS[f["usb_tx_variant"]] if f["usb_tx_variant"] < 3 else f["usb_tx_variant"], f["usb_tx_done"],
            ", ".join("%02X %d %d" % (w & 0xFF, w >> 8 & 0xFF, w >> 16 & 0xFF) for w in tx) or "none"))
    if "usb_gone_n" in f:
        out.append("  the host's frames: stopped %d times, again %d (the last number %d); the most interrupts in one"
                   " ms %d" % (f["usb_gone_n"], f["usb_back_n"], f["usb_frame_last"], f["usb_irq_peak"]))
    return out


def derived(fields):
    """What step H's counts say: the bus count per gate cycle (7.5
    expected, HW-119 over HW-54) and the audio clock in MHz (the gate is
    the 24 MHz crystal)."""
    out = []
    f = fields
    if "adc_setup" in f:
        out += audio11_lines(f)
    if "a10_fmt_changes" in f and (f.get("daa7_reads") or f.get("m_value")):
        n = f["a10_fmt_changes"]
        fl = [f.get("a10_fmt_t_%d" % (k % 8), 0) for k in range(max(0, n - 8), n)]
        out.append("audio10: F %s (%d changes: %s); synth fill longest %.1f us, with 8 voices %.1f us, most voices %d;"
                   " soft clipped %d, saturated %d" % (
                       A10_FMTS[min(f["a9_s2"], 4)] if "a9_s2" in f else "?", n,
                       ", ".join("beat %d %s" % (w >> 3, A10_FMTS[min(w & 7, 4)]) for w in fl),
                       f["a10_fill_max_units"] / 24.0, f["a10_fill_max8_units"] / 24.0, f["a10_voices_max"],
                       f["a10_soft_clipped"], f["a10_saturated"]))
        n = f["m_ring_n"]
        ring = [f["m_ring_%d" % (k % 40)] for k in range(max(0, n - 40), n)]
        out.append("MASTER %d (raw %d at the change, %d now); tone gain %d, synth level %d of 16777216; %d changes,"
                   " raw jumps %d, largest raw step %d; last changes (beat value): %s" % (
                       f["m_value"], f["m_raw_at_change"], f["m_raw_now"], f["m_tone_gain"], f["m_synth_level"],
                       f["m_changes"], f["m_raw_jumps"], f["m_raw_max_step"],
                       " ".join("%d:%d%s" % ((w >> 10) * 4, w & 0x3FF, raw_at(f, k)) for k, w in
                                zip(range(max(0, n - 40), n), ring))))
        n = f["hold_n"]
        ht = [f["hold_t_%d" % (k % 8)] for k in range(max(0, n - 8), n)]
        out.append("holds now: %s; changes: %s; log records dropped %d" % (
            ", ".join(h for i, h in enumerate(HOLDS) if f["holds"] >> i & 1) or "none",
            ", ".join("beat %d %s %s" % (w >> 8, HOLDS[min(w >> 1 & 127, 4)], "on" if w & 1 else "off") for w in ht),
            f["log_dropped"]))
    if "a9_route" in f and (f.get("a9_route") or f.get("daa7_reads")):
        out.append("audio9: route %s (up %d, down %d); %s, S2 %s; late halves %d since the synth came on, longest fill"
                   " %.1f us (a half is 2902 us), fallback %s; engine blocks %d; underruns %d" % (
                       A9_ROUTE[min(f["a9_route"], 4)], f["a9_route_ups"], f["a9_route_downs"],
                       "SYNTH" if f["a9_synth"] else "tone", (A10_FMTS[min(f["a9_s2"], 4)] if "a10_fmt_changes" in f else A9_S2[min(f["a9_s2"], 2)]), f["a9_late_halves"],
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
DECIMAL = {"a10_fmt_changes", "a10_fill_max_units", "a10_fill_max8_units", "a10_voices_max", "a10_soft_clipped",
           "a10_saturated", "m_value", "m_raw_at_change", "m_raw_now", "m_tone_gain", "m_synth_level", "m_changes",
           "m_raw_jumps", "m_raw_max_step", "m_ring_n", "hold_n", "log_dropped", "a9_route", "a9_route_ups", "a9_route_downs", "a9_synth", "a9_synth_ons", "a9_s2", "a9_underruns_at_synth_on",
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
DECIMAL |= {n for n in FIELDS[10] if n.startswith(("adc_conv", "adc_passes", "adc_slot", "adc_setup", "adc_set_n",
                                                     "m_jump_n", "m_level"))
            or (n.startswith("adc_") and n.endswith(("_n", "_rest")))}
DECIMAL |= {n for n in FIELDS[12] if n.startswith(("a13_start", "u2_late_beat", "u2_late_blocks", "u2_key_beat",
                                                     "u2_key_n", "u2_state", "u2_run", "u2_polls", "u2_mark_n",
                                                     "u2_chg_n", "u2c_on", "u2c_toggles", "u2c_n_", "u2c_timeouts",
                                                     "u2c_log_n", "arp_"))}
DECIMAL |= {"arp_saves", "arp_save_err", "arp_save_seq", "arp_offs"}
DECIMAL |= {n for n in USB_REC if not n.startswith(("usb_magic", "usb_lines_first", "usb_lines_or", "usb_rb_",
                                                     "usb_last_setup", "usb_giveup_value", "usb_cable_log"))
            and not n.endswith("_gap_flags") and not n.startswith(("usb_rx_log_", "usb_tx_log_"))}
DECIMAL |= {"usb_rx_log_n", "usb_tx_log_n"}
DECIMAL |= {n for n in FIELDS[11] if n.startswith(("start_mode", "as_state", "as_alg", "as_runs", "as_stop",
                                                     "as_chords", "as_soft", "as_hard", "as_late", "as_rel",
                                                     "g_note_n", "g_turn"))}
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
