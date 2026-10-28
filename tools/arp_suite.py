#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
"""The arpeggiator's tests (ARP; docs/ARP-PROPOSAL.md with the owner's
answers, docs/DESIGN-NOTES.md, "ARP"): the shipping image in fwtest,
four runs at a time, each against tools/arp_model.py and its golden
files (tests/fw/golden/arp/: each run's MIDI out, its messages in order
without their times, which move with any change of code and which the
runs check against the model instead; the screen's images; arp.json:
the SHA-256 of each run's sound, from its first sample to its last, as
tools/preset_suite.py keeps the presets').

  arp_suite.py --image APP.bin --out DIR [--only NAME ...] [--write-golden [--replace]]

The runs (R-ARP-1 to R-ARP-8):
- mode-up ... mode-chord: each mode (2 octaves, 1/16, 120 beats a
  minute, gate 50%) for G4 C4 E4 arriving by MIDI in 30 ms apart: the
  notes of every step and their velocities, against the model, exactly;
  each step's frame (the arpeggiator's record) against the model,
  exactly; each step's sound starting in the WAV at its frame (the same
  offset for every step); each note on and off on MIDI out within a
  block and three bytes of its ideal time.
- rate-1-2 ... rate-1-32: each rate (UP, 1 octave), the same checks.
- swing: 1/8 with 50% swing and gate 30%: odd steps half a step late.
- minute: one note held 60 s at 1/16 and gate 100%, so each step takes
  the voice still sounding again (the same note): the last 32 steps'
  frames from the first's, exactly, and their sound at their frames; the
  last note on within a block of its ideal time (no drift).
- clock: MIDI clock in. Notes held, then Start and 120 beats a minute
  for 2 s, 90 for 2 s, Stop (the clock goes on, ignored), Continue and
  120 for 1 s, then no clock (lost after 250 ms): the steps on MIDI out
  within a block and three bytes of their clock (Start's first clock is
  the first step), the clock's source and tempo at each stage, back to
  the internal tempo after the Stop and the loss.
- follow: 0xF8 at 100 beats a minute with no Start: followed, 150 ms a
  step.
- keys-out: the settings' MIDI out "keys": the keys go out, the
  arpeggiator's notes don't; it still plays.
- local-off: local control off: its notes go out, the engine plays
  nothing.
- clock-out: on the internal clock, Start, a 0xF8 a pulse, Stop.
- clock-quiet: MIDI thru on; on the internal clock, then MIDI clock in
  (Start, 1 s), Stop with the clock going on (0.6 s, ignored), then no
  clock: none of our clocks goes out while the sender's come in (only
  theirs, passed on), and ours continue 250 ms after its last.
- stuck: modes, octaves and rates changed on the ARP screen while it
  plays, LATCH, the pedal, PRESETS to a program without it and back, a
  mono patch, ARP off: every note on MIDI out ends, nothing sounds or
  is held at the end.
- screen: ARP held shows its screen (golden images of both pages), its
  knobs change its settings, a short press turns it off and on (ARP's
  LED, the event line).
- save: turned on and edited on the ARP screen, SAVE to slot 2; the next
  start plays slot 2 with those settings (the store's record checked by
  tools/store.py).
- load: tests/fw/scripts/audioload.txt's heaviest input with a patch
  arpeggiating CHORD at 1/32 and 240 beats a minute: no underrun.
tools/record.py's check C-ARP runs it.
"""

import argparse
import concurrent.futures
import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arp_model as am  # noqa: E402  (tools/, our own)
import audio_analysis as aa  # noqa: E402
import fm_patch  # noqa: E402
import goldtime  # noqa: E402
import store as st  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOLDEN_DIR = os.path.join(ROOT, "tests", "fw", "golden", "arp")
GOLDEN_SUMS = os.path.join(ROOT, "tests", "fw", "golden", "arp.json")
WORKERS = 4

ARP_ADDR, ARP_LEN = 0x01C008D0, 0xE0        # arp.h's record
AUDIO_ADDR, AUDIO_LEN = 0x01C00550, 0x40    # audio.h's
FM_ADDR, FM_LEN = 0x01C00590, 0x40          # fm.h's
ARP_FIELDS = ("marker on steps notes_on notes_off sounding held clock tempo_x10 pulses starts continues stops"
              " losses log_count clocks_out").split()
FM_FIELDS = ("marker core1 core1_blocks patch algorithm mono voices0 voices1 voices_max stolen notes"
             " wait_max pitch_knob glide depth feedback").split()
BLOCK_MS = 64 * 544 / 24000.0               # 1.451 ms
BYTE_MS = 0.32                              # a MIDI byte on the wire
SLACK_MS = BLOCK_MS + 3 * BYTE_MS           # MIDI out: a block and three bytes
FIRST_SLOT = 9                              # program of user slot 1 (fm.h)
ARP_BUTTON, KEY_SAVE = 10, 9
ENC_SELECT, ENC_PRESETS = 0, 6
ENC_KNOB = (2, 3, 4, 5)                     # KNOB1 to KNOB4 (fwtest encoders 2 to 5)
CLICK = fm_patch.patch("Click", 8, [fm_patch.op(1.0, 127, rates=(0, 24, 0, 24), levels=(127, 0, 0))])
# A click a note: attack 1 ms, then down to level 0 (-96 dB) within 8 ms
# and held there, so each step's sound starts from silence in the WAV,
# also when it takes a voice still sounding (the same note again).


def key(n):
    """fwtest's key number for KEYn (HW-37)."""
    return 13 + n


def rel(path):
    return os.path.relpath(path, ROOT)


def with_arp(p, **kw):
    q = dict(p)
    q["arp"] = fm_patch.arp(on=True, **kw)
    return fm_patch.encode(q)


def settings(tempo=120, arp_out=0, local=1, thru=0):
    """struct midi_settings, version 4 (midi.h): the defaults but these."""
    routes = ((1, 1), (7, 2), (11, 3), (64, 4), (16, 5), (17, 6), (18, 7), (19, 8), (5, 6), (74, 7))
    r = [b for x in routes for b in x] + [0] * (2 * (16 - len(routes)))
    return bytes([4, 0, 2, len(routes)] + r + [1, thru, local, 0, tempo, arp_out])


def chip(slots, settings_bytes=None):
    s = st.Store()
    for i, b in enumerate(slots):
        if b is not None:
            s.put(st.PATCH, i, fm_patch.VERSION, b)
    if settings_bytes:
        s.put(st.SETTINGS, 0, 4, settings_bytes)
    return s.chip()


# --- The runs ------------------------------------------------------------

# Where a run's own length ends too near an audio block's end, the end
# the timing goldens' policy takes instead (tools/goldtime.py, rule 1:
# 1 ms before the next block's end, 0.2 ms after the last). Each run
# starts from its own flash chip, so its blocks fall at their own times.
END_MS = {"clock-out": 1700.1, "follow": 3599, "load": 10998.9, "minute": 60800.3, "mode-chord": 2708.9,
          "mode-down": 2708.9, "mode-order": 2708.9, "mode-random": 2708.9, "mode-up": 2708.9,
          "mode-updown": 2708.9, "rate-1-16": 3509.6, "rate-1-16d": 3509.6, "rate-1-16t": 3509.6,
          "rate-1-2": 9009.1, "rate-1-32": 3384.9, "rate-1-4": 5259.1, "rate-1-4d": 7134.9, "rate-1-8": 3509.6,
          "rate-1-8t": 3509.6, "save": 2000.1, "save-next": 2709.8, "screen": 3700.3, "stuck": 5799.7,
          "swing": 2709.8}

class Case:
    def __init__(self, name, ms, script, flash=None, rams=(), lcds=(), leds=False, flash_out=False, check=None,
                 golden=True, sound=True, **info):
        self.name, self.ms, self.script, self.flash = name, END_MS.get(name, ms), script, flash
        self.rams, self.lcds, self.leds, self.flash_out = rams, lcds, leds, flash_out
        self.check, self.golden, self.info = check, golden, info
        # sound: the WAV's hash a golden too (not for MIDI clock in: which
        # block takes a clock moves a step there, with the code's timing).
        self.sound = sound

    def run(self, image, out):
        d = os.path.join(out, self.name)
        shutil.rmtree(d, ignore_errors=True)
        os.makedirs(out, exist_ok=True)
        s = os.path.join(out, self.name + ".txt")
        with open(s, "w") as f:
            f.write("\n".join(self.script) + "\n")
        argv = ["sh", "tools/fwtest", "run", rel(image), "--ms", str(self.ms), "--script", rel(s), "--midi-out",
                "--wav", "--ipb", "--console", "--ram", "0x%08x:0x%x@end" % (ARP_ADDR, ARP_LEN),
                "--ram", "0x%08x:0x%x@end" % (AUDIO_ADDR, AUDIO_LEN), "--ram", "0x%08x:0x%x@end" % (FM_ADDR, FM_LEN)]
        for when in self.rams:
            argv += ["--ram", "0x%08x:0x%x@%s" % (ARP_ADDR, ARP_LEN, when)]
        for when in self.lcds:
            argv += ["--lcd", str(when)]
        if self.leds:
            argv += ["--leds-every", "10"]
        if self.flash is not None:
            fp = os.path.join(out, self.name + ".flash.bin")
            with open(fp, "wb") as f:
                f.write(self.flash)
            argv += ["--flash", rel(fp)]
        if self.flash_out:
            argv += ["--flash-out"]
        g = os.path.join(GOLDEN_DIR, self.name)
        if self.golden and self.lcds and os.path.isdir(g) and not self.info.get("write_golden"):
            argv += ["--golden", rel(g)]
        argv += ["--out", rel(d)]
        p = subprocess.run(argv, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        return d, p.returncode, p.stdout.decode("utf-8", "replace")


def arp_record(d, when="end"):
    when = when if when == "end" else "%sms" % when
    with open(os.path.join(d, "ram-%08x-%x-%s.bin" % (ARP_ADDR, ARP_LEN, when)), "rb") as f:
        b = f.read()
    r = dict(zip(ARP_FIELDS, struct.unpack("<16I", b[:64])))
    times = struct.unpack("<32I", b[64:192])
    n = r["log_count"]
    k0 = max(0, n - 32)
    r["log"] = [(k, times[k % 32], b[192 + k % 32]) for k in range(k0, n)]
    return r


def record(d, addr, length, fields, when="end"):
    with open(os.path.join(d, "ram-%08x-%x-%s.bin" % (addr, length, when)), "rb") as f:
        b = f.read()
    return dict(zip(fields, struct.unpack("<%dI" % len(fields), b[:4 * len(fields)])))


def midi_messages(d):
    """MIDI out as (ms of the first byte, status, data...) tuples."""
    rows = []
    with open(os.path.join(d, "midi-out.csv")) as f:
        next(f)
        for line in f:
            ms, h = line.strip().split(",")
            rows.append((float(ms), int(h, 16)))
    out, status, cur, t0, need = [], 0, [], 0.0, 0
    for ms, b in rows:
        if b >= 0xF8:
            out.append((ms - BYTE_MS, b))
            continue
        if b & 0x80:
            status, cur, t0 = b, [], ms - BYTE_MS
            need = 0 if b >= 0xF0 else (1 if b & 0xF0 in (0xC0, 0xD0) else 2)
            if not need:
                out.append((t0, b))
            continue
        if not cur:
            t0 = ms - BYTE_MS if not cur and status and len(cur) == 0 and out and out[-1][1:] and True else t0
        cur.append(b)
        if len(cur) == need:
            out.append((t0, status) + tuple(cur))
            cur = []
            t0 = ms                     # running status: the next message's first byte follows
    return out


def notes_out(msgs):
    """Note ons and offs (a note on at velocity 0 is an off): (ms, note, velocity)."""
    return [(m[0], m[2], m[3]) for m in msgs if len(m) == 4 and m[1] & 0xF0 == 0x90]


def wav_left(d):
    _, x, _ = aa.read_wav(os.path.join(d, "audio.wav"))
    return x


def onsets(x, quiet=16, floor=2):
    """Each sound's first sample after at least `quiet` silent ones (under
    `floor`: a level held at 0, -96 dB, leaves +-1 in 16 bits)."""
    out, zeros = [], quiet
    for i, v in enumerate(x):
        if abs(v) >= floor:
            if zeros >= quiet:
                out.append(i)
            zeros = 0
        else:
            zeros += 1
    return out


def messages_text(d):
    """MIDI out's messages as fwtest decodes them, one a line, without
    their times or whether they took running status (which follows from
    the times: whether the wire went quiet before them), and without the
    realtime ones (MIDI clock out, Start, Stop: where they fall among the
    notes follows from the blocks too; clock-out checks them)."""
    realtime = ("clock", "start", "stop", "continue")
    with open(os.path.join(d, "midi-out.txt")) as f:
        lines = [l.split(" ", 1)[1].replace(" (running status)", "") for l in f if " " in l]
    return "".join(l for l in lines if l.strip() not in realtime)


def wav_sha256(d):
    """The SHA-256 of the sound, from its first sample at +-2 or more to
    its last (16-bit left, little-endian): a run whose input came a block
    earlier or later as a whole (MIDI in's bytes are taken once a block)
    gives the same sound, and the same hash."""
    x = wav_left(d)
    loud = [i for i, v in enumerate(x) if abs(v) >= 2]
    if not loud:
        return hashlib.sha256(b"").hexdigest()
    return hashlib.sha256(struct.pack("<%dh" % (loud[-1] + 1 - loud[0]), *x[loud[0]:loud[-1] + 1])).hexdigest()


def common(name, d, code, log):
    p = []
    if code:
        p.append("%s: fwtest exited %d: %s" % (name, code, log.strip().splitlines()[-1:] if log.strip() else ""))
    try:
        with open(os.path.join(d, "result.json")) as f:
            res = json.load(f)
        for g in res.get("golden") or []:
            if g.get("result") != "match":
                p.append("%s: golden %s: %s" % (name, g.get("name"), g.get("detail")))
        if res["run"].get("unmodelled_accesses"):
            p.append("%s: unmodelled accesses" % name)
    except (OSError, ValueError, KeyError):
        p.append("%s: no result.json" % name)
    try:
        a = record(d, AUDIO_ADDR, AUDIO_LEN, "marker blocks filled underruns late fill_max".split())
        if a["underruns"]:
            p.append("%s: %d underruns" % (name, a["underruns"]))
    except OSError:
        p.append("%s: no audio record" % name)
    return p


# --- Checks ----------------------------------------------------------------

HELD = [(67, 100), (60, 90), (64, 80)]      # G4, C4, E4, 30 ms apart, by MIDI in
# The keys are let go together, OFF_GRID_MS after a whole number of steps
# of every rate, never on a step: there, which came first moved with a
# few microseconds of the code's timing (the timing goldens' policy).
OFF_GRID_MS = 10
T_NOTES, HOLD_MS = 300, 2000 + OFF_GRID_MS


def held_script(t=T_NOTES, hold=HOLD_MS, program=None):
    s = ["100 midi c0 %02x" % program] if program is not None else []
    for i, (n, v) in enumerate(HELD):
        s.append("%d midi 90 %02x %02x" % (t + 30 * i, n, v))
    # All let go at once (nine bytes, 2.9 ms on the wire): no step falls
    # among them, so every step has all three held or none.
    s.append("%d midi %s" % (t + hold, " ".join("80 %02x 00" % n for n, _ in HELD)))
    return s


def expected_steps(a, steps):
    """Each step's notes and velocities: step 0 plays with G4 alone held
    (C4 and E4 arrive before step 1)."""
    rng, out = am.Random(), []
    vel = dict(HELD)
    for k in range(steps):
        held = [HELD[0][0]] if k == 0 else [n for n, _ in HELD]
        out.append([(n, vel[n % 12 + 12 * (n // 12)] if n in vel else vel[[h for h in vel if h % 12 == n % 12][0]])
                    for n in am.pattern(held, a, k, rng)])
    return out


def velocity_of(note, held):
    """A step's note's velocity: the held note it was played from."""
    for n, v in held:
        if (note - n) % 12 == 0 and note >= n:
            return v
    return None


RATE_KHZ = 24000000.0 / 544 / 1000         # frames a millisecond


def check_steps(name, d, a, tempo=120, hold_ms=HOLD_MS, sound=True):
    """The notes of each step on MIDI out and in the record, their frames,
    their sound in the WAV and their times on MIDI out."""
    p, lines = [], []
    r = arp_record(d)
    msgs = midi_messages(d)
    ons = [(t, n, v) for t, n, v in notes_out(msgs) if v]
    offs = [(t, n) for t, n, v in notes_out(msgs) if not v]
    step_ms = am.RATE_PULSES[a["rate"]] * 60000.0 / (24 * tempo)
    expect = sum(1 for k in range(1000) if am.ideal_ms(a, k, tempo) < hold_ms)
    steps = r["steps"]
    if not expect <= steps <= expect + 1:
        p.append("%s: %d steps played, expected %d" % (name, steps, expect))
    rng = am.Random()
    want = []
    for k in range(steps):
        held = [HELD[0][0]] if k == 0 else [n for n, _ in HELD]
        want.append(am.pattern(held, a, k, rng))
    flat = [(n, velocity_of(n, HELD)) for w in want for n in w]
    got = [(n, v) for _, n, v in ons]
    if got != flat:
        p.append("%s: notes on MIDI out %s, the model %s" % (name, got[:12], flat[:12]))
    log = r["log"]
    if not log or log[0][0] != 0 or len(log) != steps:
        return p + ["%s: the step log holds %d of %d steps from the first" % (name, len(log), steps)], lines
    frames = am.step_frames(a, steps, tempo)
    f0 = log[0][1]
    bad = [(k, t - f0, frames[k]) for k, t, _ in log if t - f0 != frames[k]]
    if bad:
        p.append("%s: step frames from the first %s, the model %s" % (name, bad[:4], [b[2] for b in bad[:4]]))
    notes = [n for _, _, n in log]
    if notes != [min(w) for w in want]:
        p.append("%s: the record's step notes %s, the model %s" % (name, notes[:12], [min(w) for w in want][:12]))
    # The sound: each step's first sample after silence, at the same
    # offset from its frame.
    on = onsets(wav_left(d))
    offs_f = []
    for k, t, _ in log:
        near = [o for o in on if t <= o < t + 256]
        offs_f.append(near[0] - t if near else None)
    if sound and (None in offs_f or len(set(offs_f)) != 1):
        p.append("%s: each step's sound from its frame: %s (one offset expected)" % (name, offs_f[:12]))
    # MIDI out: each step's first note on, from its frame, within a block
    # and three bytes of the others (MIDI out sends once a block).
    firsts, i = [], 0
    for k, w in enumerate(want):
        if i < len(ons):
            firsts.append((k, ons[i][0]))
        i += len(w)
    lag = [t - log[k][1] / RATE_KHZ for k, t in firsts]
    if lag and max(lag) - min(lag) > SLACK_MS:
        p.append("%s: note ons from their frames %.3f to %.3f ms (more than %.2f apart)"
                 % (name, min(lag), max(lag), SLACK_MS))
    gate_ms = min(step_ms * a["gate"] / 100.0, step_ms)
    offs_late = []
    for (k, t), w in zip(firsts, want):
        mine = [o for o, n in offs if n in w and o > t]
        if mine and not -SLACK_MS <= mine[0] - t - gate_ms <= SLACK_MS:
            offs_late.append((k, round(mine[0] - t, 2)))
    if offs_late:
        p.append("%s: note offs %s ms after their note on, the gate %.2f" % (name, offs_late[:4], gate_ms))
    p += balanced(name, msgs)
    lines.append("  %s: %s, 120 beats a minute: %d steps, their notes as the model's (MIDI out and the record),"
                 " their frames as the model's, their sound %s frames after their frames, note ons within"
                 " %.2f ms of one another from their frames" % (name, describe(a), steps,
                                                               offs_f[0] if offs_f else "?", max(lag) - min(lag)
                                                               if lag else 0))
    return p, lines


def describe(a):
    return "%s %s, %d octave%s, gate %d%%%s" % (
        fm_patch.ARP_MODES[a["mode"]], fm_patch.ARP_RATES[a["rate"]][0], a["octaves"], "s" if a["octaves"] > 1 else "",
        a["gate"], ", swing %d%%" % a["swing"] if a["swing"] else "")


def balanced(name, msgs):
    """Every note on MIDI out ends."""
    held = {}
    for t, n, v in notes_out(msgs):
        held[n] = held.get(n, 0) + (1 if v else -1)
    left = {n: c for n, c in held.items() if c}
    return ["%s: notes left on at the far end: %s" % (name, left)] if left else []


def silent_at_end(name, d):
    p = []
    r, f = arp_record(d), record(d, FM_ADDR, FM_LEN, FM_FIELDS)
    if r["sounding"] or f["voices0"] + f["voices1"]:
        p.append("%s: at the end the arpeggiator plays %d notes and %d voices sound"
                 % (name, r["sounding"], f["voices0"] + f["voices1"]))
    return p


# --- The cases ----------------------------------------------------------------

def mode_settings(m):
    return dict(fm_patch.ARP_DEFAULT, on=True, mode=m, octaves=2)


def rate_settings(i):
    return dict(fm_patch.ARP_DEFAULT, on=True, rate=i)


MODE_NAMES = ("up", "down", "updown", "order", "random", "chord")
RATE_NAMES = ("1-2", "1-4d", "1-4", "1-8d", "1-8", "1-8t", "1-16d", "1-16", "1-16t", "1-32")
SLOTS = ([with_arp(CLICK, mode=m, octaves=2) for m in range(6)]
         + [with_arp(CLICK, rate=i) for i in range(10)])


def cases():
    out = []
    bank = chip(SLOTS)
    for m in range(6):
        a = mode_settings(m)
        out.append(Case("mode-" + MODE_NAMES[m], T_NOTES + HOLD_MS + 400, held_script(program=FIRST_SLOT + m),
                        bank, check=lambda n, d, a=a: check_steps(n, d, a)))
    for i in range(10):
        a = rate_settings(i)
        # 8 steps at least, at most 30 (the record logs the last 32).
        step_ms = am.RATE_PULSES[i] * 60000.0 / (24 * 120)
        hold = int(min(max(2000, 7.5 * step_ms), 30 * step_ms)) + OFF_GRID_MS
        out.append(Case("rate-" + RATE_NAMES[i], T_NOTES + hold + 1200,
                        held_script(hold=hold, program=FIRST_SLOT + 6 + i), bank,
                        check=lambda n, d, a=a, hold=hold: check_steps(n, d, a, hold_ms=hold)))
    a = dict(fm_patch.ARP_DEFAULT, on=True, rate=4, swing=50, gate=30)
    out.append(Case("swing", T_NOTES + HOLD_MS + 400, held_script(program=FIRST_SLOT),
                    chip([with_arp(CLICK, rate=4, swing=50, gate=30)]),
                    check=lambda n, d, a=a: check_steps(n, d, a)))
    out.append(minute_case())
    out += clock_cases()
    out += out_cases()
    out.append(stuck_case())
    out.append(screen_case())
    out += save_cases()
    out.append(load_case())
    return out


def minute_case():
    a = dict(fm_patch.ARP_DEFAULT, on=True, gate=100)
    script = ["100 midi c0 09", "300 midi 90 3c 64", "%d midi 80 3c 00" % (60300 + OFF_GRID_MS)]

    def check(name, d):
        p, lines = [], []
        r1, r = arp_record(d, "1000"), arp_record(d)
        if not r1["log"] or r1["log"][0][0] != 0:
            return ["%s: no first step at 1 s" % name], lines
        f0 = r1["log"][0][1]
        frames = am.step_frames(a, r["log_count"], 120)
        bad = [(k, t - f0, frames[k]) for k, t, _ in r["log"] if t - f0 != frames[k]]
        if bad:
            p.append("%s: step frames %s, the model %s" % (name, bad[:3], [b[2] for b in bad[:3]]))
        want = sum(1 for k in range(2000) if am.ideal_ms(a, k, 120) < 60000)
        if not want - 1 <= r["log_count"] <= want + 1:
            p.append("%s: %d steps in 60 s, the model %d" % (name, r["log_count"], want))
        x = wav_left(d)
        on = onsets(x)
        offs_f = []
        for k, t, _ in r["log"]:
            near = [o for o in on if t <= o < t + 256]
            offs_f.append(near[0] - t if near else None)
        if None in offs_f or len(set(offs_f)) != 1:
            p.append("%s: the last steps' sound from their frames: %s" % (name, offs_f[:8]))
        # No drift on MIDI out: the first logged step's note on and the
        # last's, from their frames, within a block and three bytes.
        ons = [t for t, _, v in notes_out(midi_messages(d)) if v]
        drift = None
        if len(ons) == r["log_count"] and ons:
            lag0 = ons[1] - r1["log"][1][1] / RATE_KHZ
            drift = ons[-1] - r["log"][-1][1] / RATE_KHZ - lag0
        if drift is None or abs(drift) > SLACK_MS:
            p.append("%s: the last note on %s ms from where the second's lag puts it" % (name, drift))
        lines.append("  %s: %d steps in 60 s, each the same voice taken again (gate 100%%); the last 32 at the"
                     " model's frames from the first, their sound %s frames after; MIDI out's last note on %.3f"
                     " ms from the second's lag" % (name, r["log_count"], offs_f[0] if offs_f else "?", drift or 0))
        return p + balanced(name, midi_messages(d)), lines
    return Case("minute", 60800, script, chip([with_arp(CLICK, gate=100)]), rams=("1000",), check=check,
                golden=False)


def clock_script():
    """Notes held, then MIDI clock: Start, 120 for 2 s, 90 for 2 s, Stop
    (clock on, ignored) 0.5 s, Continue, 120 for 1 s, then nothing."""
    s = ["100 midi c0 09", "200 midi 90 3c 64", "210 midi 90 40 64"]
    t, clocks = 500.0, []
    # (the notes are let go at the end: clock_cases)
    s.append("%.3f midi fa" % t)
    t += 5
    for bpm, dur, kind in ((120, 2000, "play"), (90, 2000, "play"), (120, 500, "stopped"), (120, 1000, "cont")):
        step = 60000.0 / (24 * bpm)
        if kind == "stopped":
            s.append("%.3f midi fc" % t)
            t += 2
        if kind == "cont":
            s.append("%.3f midi fb" % t)
            t += 2
        end = t + dur
        while t < end:
            s.append("%.3f midi f8" % t)
            clocks.append((t, kind))
            t += step
    return s, clocks, t


def clock_cases():
    script, clocks, end = clock_script()
    a = dict(fm_patch.ARP_DEFAULT, on=True)
    stop_at = [t for t, k in clocks if k == "stopped"][0]
    cont_at = [t for t, k in clocks if k == "cont"][0]

    def check(name, d):
        p, lines = [], []
        msgs = midi_messages(d)
        ons = [t for t, _, v in notes_out(msgs) if v]
        played = [t for t, k in clocks if k == "play"]
        # Following: step k on clock 6k after Start (its first clock is pulse 0).
        follow = [(i, played[i] + BYTE_MS) for i in range(0, len(played), 6)]
        bad = []
        for i, ideal in follow:
            near = [t for t in ons if ideal - 2 * BLOCK_MS <= t <= ideal + 3 * BLOCK_MS]
            # the first steps after the tempo change may run up to a pulse early
            changed = 2000 / (60000.0 / (24 * 120)) <= i < 2000 / (60000.0 / (24 * 120)) + 12
            if not near or (not changed and not -BYTE_MS <= near[0] - ideal <= SLACK_MS):
                bad.append((i, ideal, near[:1]))
        if bad:
            p.append("%s: steps against their clocks (pulse, ideal ms, note on): %s" % (name, bad[:5]))
        # The tempo, the mean of the last 24 clocks, at 90 once 24 have come.
        stages = {"1000": (1, 1200), "4000": (1, 900), "4700": (0, 1200), "5600": (1, 1200), "6800": (0, 1200)}
        for when, (src, tempo) in stages.items():
            r = arp_record(d, when)
            if r["clock"] != src or abs(r["tempo_x10"] - tempo) > tempo // 100:
                p.append("%s: at %s ms the clock %d at %.1f, expected %d at %.1f"
                         % (name, when, r["clock"], r["tempo_x10"] / 10, src, tempo / 10))
        r = arp_record(d)
        if (r["starts"], r["stops"], r["continues"], r["losses"]) != (1, 1, 1, 1):
            p.append("%s: starts %d, stops %d, continues %d, losses %d; expected 1 each"
                     % (name, r["starts"], r["stops"], r["continues"], r["losses"]))
        # After the Stop: the internal tempo, 125 ms a step.
        after = [t for t in ons if stop_at + 200 < t < cont_at]
        gaps = [b - a_ for a_, b in zip(after, after[1:])]
        if not gaps or any(abs(g - 125) > SLACK_MS for g in gaps):
            p.append("%s: steps after the Stop %s ms apart, not 125" % (name, [round(g, 2) for g in gaps]))
        lost = [t for t in ons if t > end + 400]
        gaps = [b - a_ for a_, b in zip(lost, lost[1:])]
        if not gaps or any(abs(g - 125) > SLACK_MS for g in gaps):
            p.append("%s: steps after the clock was lost %s ms apart, not 125" % (name, [round(g, 2) for g in gaps]))
        lines.append("  %s: Start, 120 and 90 beats a minute, Stop, Continue, loss: the steps within %.2f ms of"
                     " their clocks (but the first after the tempo change), the internal tempo after the Stop"
                     " and the loss" % (name, SLACK_MS))
        return p + balanced(name, msgs), lines

    follow_script = ["100 midi c0 09", "200 midi 90 3c 64"]
    t = 400.0
    while t < 3400:
        follow_script.append("%.3f midi f8" % t)
        t += 60000.0 / (24 * 100)

    def check_follow(name, d):
        p, lines = [], []
        r = arp_record(d, "3000")
        if r["clock"] != 1 or abs(r["tempo_x10"] - 1000) > 10:
            p.append("%s: clock %d at %.1f, expected MIDI at 100" % (name, r["clock"], r["tempo_x10"] / 10))
        ons = [t for t, _, v in notes_out(midi_messages(d)) if v and 1000 < t < 3300]
        gaps = [b - a_ for a_, b in zip(ons, ons[1:])]
        if not gaps or any(abs(g - 150) > 2 * BLOCK_MS for g in gaps):
            p.append("%s: steps %s ms apart, not 150" % (name, [round(g, 2) for g in gaps[:8]]))
        lines.append("  %s: 0xF8 with no Start followed: 100 beats a minute, steps 150 ms apart" % name)
        return p, lines

    bank = chip([with_arp(CLICK)])
    script = script + ["%d midi 80 3c 00" % (end + 1100), "%d midi 80 40 00" % (end + 1100)]
    return [Case("clock", int(end) + 1300, script, bank, rams=("1000", "4000", "4700", "5600", "6800"), check=check,
                 sound=False),
            Case("follow", 3600, follow_script, bank, rams=("3000",), check=check_follow, sound=False)]


def out_cases():
    # The two keys 10 ms apart: at the same time their order on MIDI out
    # would be the scan's, which moves with the code's timing.
    keys = ["100 midi c0 09", "300 key %d down" % key(1), "310 key %d down" % key(8),
            "%d key %d up" % (1300 + OFF_GRID_MS, key(1)), "%d key %d up" % (1310 + OFF_GRID_MS, key(8))]

    def check_keys(name, d):
        p = []
        msgs = midi_messages(d)
        notes = [(n, v) for _, n, v in notes_out(msgs)]
        if sorted(notes) != sorted([(53, 100), (60, 100), (53, 0), (60, 0)]):
            p.append("%s: MIDI out's notes %s, expected KEY1's and KEY8's only" % (name, notes))
        if arp_record(d)["steps"] < 6:
            p.append("%s: the arpeggiator played %d steps" % (name, arp_record(d)["steps"]))
        return p, ["  %s: MIDI out \"keys\": the keys held out, the arpeggiator's notes not; it played %d steps"
                   % (name, arp_record(d)["steps"])]

    def check_local(name, d):
        p = []
        msgs = midi_messages(d)
        r, f = arp_record(d), record(d, FM_ADDR, FM_LEN, FM_FIELDS)
        ons = [n for _, n, v in notes_out(msgs) if v]
        if len(ons) < 6 or f["notes"]:
            p.append("%s: %d notes out, the engine started %d" % (name, len(ons), f["notes"]))
        if any(wav_left(d)):
            p.append("%s: the engine made a sound" % name)
        return p + balanced(name, msgs), ["  %s: local control off: %d arpeggiated notes out, none played"
                                          % (name, len(ons))]

    def check_clock_out(name, d):
        p = []
        msgs = midi_messages(d)
        rt = [(t, m[1]) for m in msgs for t in [m[0]] if len(m) == 2 and m[1] >= 0xF8]
        starts = [t for t, s in rt if s == 0xFA]
        stops = [t for t, s in rt if s == 0xFC]
        clocks = [t for t, s in rt if s == 0xF8]
        r = arp_record(d)
        between = [t for t in clocks if starts and stops and starts[-1] <= t <= stops[-1]]
        want = round((stops[-1] - starts[-1]) / (60000.0 / (24 * 120))) if starts and stops else None
        if not starts or not stops or want is None or abs(len(between) - want) > 1 or r["clocks_out"] != len(clocks):
            p.append("%s: %d Starts, %d Stops, %d clocks between them (expected %s), record %d"
                     % (name, len(starts), len(stops), len(between), want, r["clocks_out"]))
        gaps = [b - a_ for a_, b in zip(between, between[1:])]
        # Sent once a block: the average over n gaps within two blocks / n.
        if gaps and (abs(sum(gaps) / len(gaps) - 20.833) > 2 * BLOCK_MS / len(gaps)
                     or max(gaps) - min(gaps) > 2 * SLACK_MS):
            p.append("%s: clocks %.3f ms apart on average, from %.3f to %.3f"
                     % (name, sum(gaps) / len(gaps), min(gaps), max(gaps)))
        return p + balanced(name, msgs), ["  %s: on the internal clock: Start, %d clocks 20.833 ms apart on average,"
                                          " Stop with ARP off" % (name, len(between))]

    # clock-quiet: Start and 120 beats a minute from 500 ms for 1 s, Stop,
    # the clock on for 0.6 s (ignored), then none.
    quiet_script = ["100 midi c0 09", "200 midi 90 3c 64", "210 midi 90 40 64", "500 midi fa"]
    t0, period, ins = 505.0, 60000.0 / (24 * 120), []
    for k in range(int(1600 / period)):
        t = t0 + k * period
        if ins and ins[-1] < 1505 <= t:
            quiet_script.append("1505 midi fc")
        quiet_script.append("%.3f midi f8" % t)
        ins.append(t)
    last_in = ins[-1]
    # (note ons at velocity 0 to end them: what thru passes on, balanced() counts)
    quiet_script += ["2900 midi 90 3c 00", "2900 midi 90 40 00"]

    def check_clock_quiet(name, d):
        p = []
        msgs = midi_messages(d)
        rt = [(t, m[1]) for m in msgs for t in [m[0]] if len(m) == 2 and m[1] >= 0xF8]
        ours = {w: arp_record(d, w)["clocks_out"] for w in ("480", "1400", "2050", "2300")}
        end = arp_record(d)["clocks_out"]
        # (at 480 ms on the internal clock; from the first clock in, none)
        if not ours["480"] or len(set(ours[w] for w in ("1400", "2050", "2300"))) != 1:
            p.append("%s: our clocks out at 480, 1400, 2050, 2300 ms: %s; expected some, then none from 1400"
                     % (name, [ours[w] for w in ("480", "1400", "2050", "2300")]))
        # Every 0xF8 out is ours (the record counts them) or one passed on.
        passed = len([1 for _, s_ in rt if s_ == 0xF8]) - end
        if passed != len(ins):
            p.append("%s: %d clocks out not ours, %d came in" % (name, passed, len(ins)))
        conts = [t for t, s_ in rt if s_ == 0xFB and t > last_in]
        want = last_in + 250
        if len(conts) != 1 or not want - 2 * BLOCK_MS <= conts[0] <= want + 2 * BLOCK_MS:
            p.append("%s: our Continue at %s ms, expected one 250 ms after the last clock in (%.1f)"
                     % (name, [round(t, 2) for t in conts], want))
        after = [t for t, s_ in rt if s_ == 0xF8 and conts and conts[0] <= t <= 2890]
        want_n = round((2890 - conts[0]) / period) if conts else None
        if want_n is None or abs(len(after) - want_n) > 1 or end - ours["2300"] < len(after):
            p.append("%s: %d clocks of ours after the Continue (expected %s), the record %d"
                     % (name, len(after), want_n, end - ours["2300"]))
        return p + balanced(name, msgs), ["  %s: MIDI thru on: none of our clocks while the sender's came in"
                                          " (%d passed on), ours continued %.1f ms after its last"
                                          % (name, passed, (conts[0] - last_in) if conts else -1)]

    arp_btn = ["%d key %d down" % (1400, ARP_BUTTON), "%d key %d up" % (1460, ARP_BUTTON)]
    return [Case("keys-out", 1600, keys, chip([with_arp(CLICK)], settings(arp_out=1)), check=check_keys),
            Case("local-off", 1600, ["50 midi b0 7a 00"] + keys, chip([with_arp(CLICK)]), check=check_local),
            Case("clock-out", 1700, keys + arp_btn, chip([with_arp(CLICK)]), check=check_clock_out),
            Case("clock-quiet", 3000, quiet_script, chip([with_arp(CLICK)], settings(thru=1)),
                 rams=("480", "1400", "2050", "2300"), check=check_clock_quiet, sound=False)]


def stuck_case():
    """Changes while it plays: none may leave a note on."""
    t = 300
    s = ["100 midi c0 09"]
    s += ["%d key %d down" % (t, key(k)) for k in (1, 5, 8)]
    late = len(s) + 2                     # after its screen: 7 ms off the 1/16 grid (125 ms from 300)
    s += ["%d key %d down" % (600, ARP_BUTTON), "%d key %d up" % (1200, ARP_BUTTON)]     # its screen
    s += ["1300 enc %d +2" % ENC_KNOB[1], "1500 enc %d +1" % ENC_KNOB[2], "1700 enc %d +2" % ENC_KNOB[0]]
    s += ["1900 enc %d +1" % ENC_SELECT, "2000 enc %d +1" % ENC_KNOB[1]]                 # LATCH on
    s += ["%d key %d up" % (2200, key(k)) for k in (1, 5, 8)]                             # latched
    s += ["2600 midi b0 40 7f", "2650 midi 90 48 64", "2700 midi 80 48 00"]               # the pedal
    s += ["2900 key %d down" % key(3), "3000 key %d up" % key(3)]                        # a new chord
    s += ["3100 midi b0 40 00"]
    s += ["3300 enc %d -1" % ENC_PRESETS, "3600 enc %d +1" % ENC_PRESETS]                # off the slots, back
    s += ["3800 midi c0 0a"]                                                             # the mono patch
    # (10 ms apart: pressed together, which comes first is the scan's order)
    s += ["3900 key %d down" % key(1), "3910 key %d down" % key(5), "4500 key %d up" % key(5)]
    s += ["4700 key %d down" % ARP_BUTTON, "4750 key %d up" % ARP_BUTTON]                # ARP off, KEY1 held
    s += ["5000 key %d up" % key(1)]
    s = s[:late] + ["%d %s" % (int(e.split(" ", 1)[0]) + 7, e.split(" ", 1)[1]) for e in s[late:]]
    bank = chip([with_arp(CLICK), with_arp(fm_patch.TEST_PATCHES[3], mode=4, octaves=3)])

    def check(name, d):
        p = balanced(name, midi_messages(d)) + silent_at_end(name, d)
        r = arp_record(d)
        if r["on"] or r["held"]:
            p.append("%s: at the end on %d, holding %d" % (name, r["on"], r["held"]))
        return p, ["  %s: mode, octaves, rate, LATCH, the pedal, PRESETS, a mono patch and ARP off while it"
                   " played: every note on MIDI out ended, nothing sounds or is held at the end (%d steps)"
                   % (name, r["steps"])]
    # (no sound hash: its last notes are the panel's keys played as they
    # are, their starts and ends taken by different paths, the key scan
    # and the audio block, so their lengths move by a scan with the
    # code's timing; what it checks is that every note ends)
    return Case("stuck", 5800, s, bank, check=check, sound=False)


def screen_case():
    s = ["300 key %d down" % ARP_BUTTON, "360 key %d up" % ARP_BUTTON,           # on
         "600 key %d down" % ARP_BUTTON, "1300 key %d up" % ARP_BUTTON,          # held: the screen
         "1400 enc %d +1" % ENC_KNOB[0], "1500 enc %d +5" % ENC_KNOB[1], "1700 enc %d +1" % ENC_KNOB[2],
         "1800 enc %d -20" % ENC_KNOB[3],
         "2300 enc %d +1" % ENC_SELECT, "2400 enc %d +3" % ENC_KNOB[0], "2500 enc %d +1" % ENC_KNOB[1],
         "2600 enc %d +12" % ENC_KNOB[2], "2800 enc %d +1" % ENC_KNOB[3],
         "3200 key %d down" % ARP_BUTTON, "3260 key %d up" % ARP_BUTTON,         # off
         "3400 key %d down" % ARP_BUTTON, "3460 key %d up" % ARP_BUTTON]         # on again

    def check(name, d):
        p = []
        leds = []
        with open(os.path.join(d, "leds.csv")) as f:
            head = next(f).strip().split(",")
            col = head.index("10") if "10" in head else head.index("led10") if "led10" in head else None
            for line in f:
                v = line.strip().split(",")
                leds.append((float(v[0]), int(v[col]) if col is not None else 0))

        def lit(ms):
            return [v for t, v in leds if t <= ms][-1] > 0
        if not (lit(2000) and not lit(3350) and lit(3600)):
            p.append("%s: ARP's LED at 2000, 3350, 3600 ms: %s %s %s" % (name, lit(2000), lit(3350), lit(3600)))
        return p, ["  %s: ARP held shows its screen (golden images of both pages); a short press turns it off"
                   " and on (its LED)" % name]
    return Case("screen", 3700, s, None, lcds=(1350, 2250, 3000), leds=True, check=check)


def save_cases():
    s = ["300 key %d down" % ARP_BUTTON, "360 key %d up" % ARP_BUTTON,
         "500 key %d down" % ARP_BUTTON, "1200 key %d up" % ARP_BUTTON,
         "1300 enc %d +3" % ENC_KNOB[1], "1400 enc %d +1" % ENC_KNOB[2],
         "1600 key %d down" % KEY_SAVE, "1650 key %d tap" % key(2), "1750 key %d up" % KEY_SAVE]

    def check_a(name, d):
        p = []
        try:
            with open(os.path.join(d, "flash.bin"), "rb") as f:
                img = st.Image(f.read())
            got = img.get(st.PATCH, 1)
        except OSError:
            got = None
        want = fm_patch.arp(on=True, mode=3, octaves=2)
        if not got or got[0] != fm_patch.VERSION or fm_patch.arp_of(got[1]) != want:
            p.append("%s: slot 2 holds %s" % (name, fm_patch.arp_of(got[1]) if got else None))
        return p, ["  %s: ARP on, ORDER and 2 octaves on its screen, saved to slot 2 as version %d"
                   % (name, fm_patch.VERSION)]
    return [Case("save", 2000, s, None, flash_out=True, check=check_a, golden=False)]


def save_b_case(out):
    """The next start, from the flash save left."""
    with open(os.path.join(out, "save", "flash.bin"), "rb") as f:
        flash = f.read()
    a = dict(fm_patch.ARP_DEFAULT, on=True, mode=3, octaves=2)
    return Case("save-next", T_NOTES + HOLD_MS + 400, held_script(program=FIRST_SLOT + 1), flash,
                check=lambda n, d: check_steps(n, d, a, sound=False), golden=False)


def load_case():
    ev = []
    with open(os.path.join(ROOT, "tests", "fw", "scripts", "audioload.txt")) as f:
        for line in f:
            line = line.split("#")[0].strip()
            # (not its PRESETS turns: the run stays on the slot that
            # arpeggiates, whatever programs follow it)
            if line and not line.split()[1:3] == ["enc", "6"]:
                ev.append(line)
    s = ["40 midi c0 09"] + ev
    ms = 11000

    def check(name, d):
        p = []
        a = record(d, AUDIO_ADDR, AUDIO_LEN, "marker blocks filled underruns late fill_max".split())
        r = arp_record(d)
        if r["steps"] < 100:
            p.append("%s: only %d steps" % (name, r["steps"]))
        return p, ["  %s: audioload's input with CHORD at 1/32, 240 beats a minute: %d steps, no underrun,"
                   " the longest fill %.0f us" % (name, r["steps"], a["fill_max"] / 24.0)]
    return Case("load", ms, s, chip([with_arp(fm_patch.TEST_PATCHES[6], mode=5, rate=9, octaves=2)],
                                    settings(tempo=240)), check=check, golden=False)


# --- Running ----------------------------------------------------------------

def run(image, out, only=None, write_golden=False, replace=False):
    """Runs and checks the cases (all, or those named): (problems, lines)."""
    todo = [c for c in cases() if only is None or c.name in only]
    for c in todo:
        c.info["write_golden"] = write_golden
    with concurrent.futures.ThreadPoolExecutor(WORKERS) as ex:
        results = list(ex.map(lambda c: (c,) + c.run(image, out), todo))
    if (only is None or "save-next" in only or "save" in only) and os.path.exists(os.path.join(out, "save", "flash.bin")):
        c = save_b_case(out)
        results.append((c,) + c.run(image, out))
    problems, lines, sums = [], [], {}
    golden = {}
    if os.path.exists(GOLDEN_SUMS):
        with open(GOLDEN_SUMS) as f:
            golden = json.load(f)
    for c, d, code, log in results:
        p = common(c.name, d, code, log)
        # The timing goldens' policy (tools/goldtime.py): the end clear of the blocks.
        p += goldtime.check_end(c.name, d, c.ms,
                                lambda ms, n=c.name: 'in tools/arp_suite.py, END_MS: set "%s": %s' % (n, ms))[0]
        if not p:
            try:
                more, l2 = c.check(c.name, d)
            except (OSError, ValueError, KeyError, IndexError) as e:
                more, l2 = ["%s: %s: %s" % (c.name, type(e).__name__, e)], []
            p += more
            lines += l2
        if c.golden and os.path.exists(os.path.join(d, "midi-out.txt")):
            got = messages_text(d)
            gpath = os.path.join(GOLDEN_DIR, c.name + ".midi.txt")
            if write_golden and os.path.exists(gpath) and open(gpath).read() != got and not replace:
                p.append("%s: MIDI out's messages differ from %s; not written (a change of behaviour: --replace)"
                         % (c.name, rel(gpath)))
            elif write_golden:
                os.makedirs(GOLDEN_DIR, exist_ok=True)
                with open(gpath, "w") as f:
                    f.write(got)
            elif not os.path.exists(gpath):
                p.append("%s: no golden MIDI out" % c.name)
            elif open(gpath).read() != got:
                p.append("%s: MIDI out's messages differ from %s" % (c.name, rel(gpath)))
        if c.golden and c.sound and os.path.exists(os.path.join(d, "audio.wav")):
            sums[c.name] = wav_sha256(d)
            if not write_golden and golden.get(c.name) != sums[c.name]:
                p.append("%s: the WAV differs from its golden SHA-256" % c.name if c.name in golden
                         else "%s: no golden SHA-256" % c.name)
        if write_golden and c.golden and c.lcds:
            g = os.path.join(GOLDEN_DIR, c.name)
            os.makedirs(g, exist_ok=True)
            for n in os.listdir(d):
                if n.startswith("lcd-"):
                    old = os.path.join(g, n)
                    if os.path.exists(old) and not goldtime.identical(old, os.path.join(d, n)) and not replace:
                        p.append("%s: %s differs from its golden image; not written (--replace)" % (c.name, n))
                        continue
                    shutil.copyfile(os.path.join(d, n), old)
        print("%-12s %s" % (c.name, "PASS" if not p else "FAIL"), flush=True)
        problems += p
    if write_golden:
        # The runs written now replace theirs; the others' (--only) stay.
        # A hash that moved is written only with --replace (a change of
        # behaviour); one that moved with the timing, by tools/regolden.py.
        for k in sorted(sums):
            if k in golden and golden[k] != sums[k] and not replace:
                problems.append("%s: the WAV differs from its golden SHA-256; not written (tools/regolden.py, or"
                                " --replace for a change of behaviour)" % k)
                sums[k] = golden[k]
        golden.update(sums)
        golden["comment"] = "SHA-256 of each tools/arp_suite.py run's sound (wav_sha256)"
        with open(GOLDEN_SUMS, "w") as f:
            json.dump(golden, f, indent=2, sort_keys=True)
            f.write("\n")
    return problems, lines


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--image", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--write-golden", action="store_true",
                    help="write the goldens of runs that have none (new runs)")
    ap.add_argument("--replace", action="store_true",
                    help="with --write-golden, also those that differ: a change of behaviour, said so in its commit")
    a = ap.parse_args()
    problems, lines = run(os.path.abspath(a.image), os.path.abspath(a.out), a.only, a.write_golden, a.replace)
    print("\n".join(lines))
    for q in problems:
        print("FAIL: " + q)
    print("arp suite: %s" % ("PASS" if not problems else "FAIL"))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
