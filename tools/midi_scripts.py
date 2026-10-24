#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
"""Writes the fwtest scripts of M6a's MIDI cases (tests/fw/scripts/midi*.txt;
R-MIDI-*), and reads their byte streams back for tools/fw-suite.py.

  midi_scripts.py            writes every script, and perfload.txt's MIDI part
  midi_scripts.py --check    exits 1 if a committed script differs

A `midi` event's bytes arrive one every 320 us, the first 320 us after its
time (docs/HARNESS.md, "Scripts"); the writer never lets two `midi`
events overlap, so the bytes reach the firmware in the order written.
Streams that are long or random (a SysEx flood, garbage, the dense
stream) come from a fixed seed, so the scripts are the same every time.
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "tests", "fw", "scripts")
BYTE_MS = 0.32
CHUNK = 32          # bytes per `midi` line


class Script:
    def __init__(self, name, about):
        self.name, self.about, self.lines, self.t = name, about, [], 0.0

    def at(self, ms):
        """The next event no earlier than ms (and after the last byte)."""
        self.t = max(self.t, ms)
        return self

    def wait(self, ms):
        self.t += ms
        return self

    def midi(self, *data):
        b = [x for d in data for x in (d if isinstance(d, (list, tuple, bytes)) else [d])]
        for i in range(0, len(b), CHUNK):
            part = b[i:i + CHUNK]
            self.lines.append("%-8s midi %s" % (fmt(self.t), " ".join("%02x" % x for x in part)))
            self.t = round(self.t + BYTE_MS * len(part), 3)
        return self

    def event(self, text):
        self.lines.append("%-8s %s" % (fmt(self.t), text))
        return self

    def text(self):
        head = ["# SPDX-License-Identifier: MIT", "# SPDX-FileCopyrightText: 2026 japes98", "#",
                "# Written by tools/midi_scripts.py; don't edit by hand.", "#"]
        head += ["# " + l if l else "#" for l in self.about.split("\n")]
        return "\n".join(head + ["#", "# time   event"] + self.lines) + "\n"


def fmt(ms):
    s = "%.3f" % ms
    return s.rstrip("0").rstrip(".")


def rng(seed):
    x = seed
    while True:
        x = (x * 1103515245 + 12345) & 0x7FFFFFFF
        yield x >> 16 & 0xFF


def on(note, vel, ch=0):
    return [0x90 | ch, note, vel]


def off(note, ch=0):
    return [0x80 | ch, note, 0x40]


def cc(n, v, ch=0):
    return [0xB0 | ch, n, v]


def bend(v, ch=0):
    return [0xE0 | ch, v & 0x7F, v >> 7]


# --- The cases ---------------------------------------------------------

def midimsg():
    s = Script("midimsg", "midimsg (R-MIDI-2, R-MIDI-3): every message the engine takes, on\n"
               "channel 1, test patch 0 then 8 by program change. Ends with every\n"
               "note off and every voice idle.")
    s.at(100).midi(on(60, 100)).wait(150).midi(off(60))
    s.wait(150).midi(on(62, 90)).wait(150).midi(on(62, 0))          # velocity 0 is an off
    s.wait(150).midi(on(64, 127)).wait(50).midi(bend(16383)).wait(100).midi(bend(0))
    s.wait(100).midi(bend(8192)).wait(50).midi(cc(1, 127)).wait(200).midi(cc(1, 0)).midi(off(64))
    # The bend range by RPN 0: 12 semitones, then a bend to the top.
    s.wait(100).midi(cc(101, 0), cc(100, 0), cc(6, 12), cc(101, 127), cc(100, 127))
    s.wait(50).midi(on(65, 100)).midi(bend(16383)).wait(100).midi(bend(8192)).midi(off(65))
    s.wait(100).midi(cc(7, 64), cc(11, 100)).midi(on(67, 100)).wait(100).midi(off(67))
    s.wait(100).midi(cc(7, 127), cc(11, 127))
    # The knobs' controllers, then back to the middle.
    s.wait(50).midi(cc(16, 127), cc(17, 0), cc(18, 0), cc(19, 127))
    s.wait(50).midi(cc(16, 64), cc(17, 64), cc(18, 64), cc(19, 64))
    # All notes off, all sound off.
    s.wait(100).midi(on(60, 100), on(64, 100), on(67, 100)).wait(100).midi(cc(123, 0))
    s.wait(200).midi(on(60, 100), on(64, 100)).wait(100).midi(cc(120, 0)).midi(off(60), off(64))
    # A program change: test patch 8; one past the patches is ignored.
    s.wait(200).midi([0xC0, 8]).midi([0xC0, 9]).midi(on(60, 100)).wait(100).midi(off(60))
    # Aftertouch is taken and ignored.
    s.wait(100).midi([0xD0, 50], [0xA0, 60, 50])
    return s


def midirun():
    s = Script("midirun", "midirun (R-MIDI-1): running status and realtime bytes everywhere: a\n"
               "chord in running status with clock, start, stop and active sensing\n"
               "between and inside its messages; then notes off, each byte apart.")
    s.at(100).midi(0x90, 60, 0xF8, 100, 64, 0xFE, 100, 0xF8, 67, 100, 0xFA)
    s.wait(200).midi(0xF8, 0x90, 0xF8, 60, 0xF8, 0, 0xF8, 64, 0xF8, 0, 0xFC, 67, 0xFE, 0)
    s.wait(100).midi(0xB0, 1, 0xF8, 64, 7, 0xF8, 127, 1, 0)       # running status on a controller
    for _ in range(4):
        s.wait(50).midi([0xF8] * 6, 0xFE)
    return s


def midisysex():
    r = rng(7)
    s = Script("midisysex", "midisysex (R-MIDI-1): a SysEx flood: 40 short SysEx messages,\n"
               "one of 6 000 bytes (past the limit), one cut short by a note on,\n"
               "realtime inside them, and an EOX with no SysEx; notes play after each.")
    s.at(100)
    for i in range(40):
        s.midi(0xF0, [next(r) & 0x7F for _ in range(8 + i % 9)], 0xF8, 0xF7)
    s.midi(on(60, 100)).wait(50).midi(off(60))
    s.wait(20).midi(0xF0, [next(r) & 0x7F for _ in range(6000)], 0xF7)
    s.midi(on(62, 100)).wait(50).midi(off(62))
    s.wait(20).midi(0xF0, 1, 2, 3, on(64, 100)).wait(50).midi(off(64))
    s.wait(20).midi(0xF7, on(65, 100)).wait(50).midi(off(65))
    return s


def midijunk():
    r = rng(1234)
    s = Script("midijunk", "midijunk (R-MIDI-1): truncated messages and 3 000 random bytes, then a\n"
               "reset of what the junk may have set (all sound off, controllers,\n"
               "the pedal, poly mode, patch 0 on each channel), then a clean note.")
    s.at(100).midi(0x90, 60).midi(0xB0).midi(0xE0, 5).midi(0xC0).midi(0x80, 60, 0)
    s.wait(20).midi([next(r) for _ in range(3000)])
    for ch in range(16):
        s.midi(cc(120, 0, ch), cc(121, 0, ch), cc(64, 0, ch), cc(127, 0, ch), [0xC0 | ch, 0],
               cc(7, 127, ch), cc(16, 64, ch), cc(17, 64, ch), cc(18, 64, ch), cc(19, 64, ch),
               cc(101, 0, ch), cc(100, 0, ch), cc(6, 2, ch))
    s.wait(50).midi(on(60, 100)).wait(100).midi(off(60))
    return s


def mididense():
    s = Script("mididense", "mididense (R-MIDI-4): the wire full for 6 s: 16 notes held, each struck\n"
               "again in turn (running status, note on then off at velocity 0),\n"
               "the mod wheel and pitch bend moving between; then every note off.")
    notes = list(range(48, 80, 2))
    s.at(100).midi(0x90, [x for n in notes for x in (n, 100)])
    t_end = 6100
    i = 0
    while s.t < t_end:
        n = notes[i % 16]
        s.midi(0x90, n, 0, n, 60 + i % 60)
        if i % 8 == 7:
            s.midi(cc(1, i % 128), bend((i * 997) % 16384))
        i += 1
    s.midi(bend(8192), cc(1, 0), 0x80, [x for n in notes for x in (n, 0)])
    return s


def midisustain():
    s = Script("midisustain", "midisustain (R-MIDI-3): the sustain pedal. A note released under the\n"
               "pedal goes on until the pedal is up; one struck again under it\n"
               "starts again; a panel key (KEY1, note 53) and a MIDI note under\n"
               "the pedal; all notes off with the pedal down (the pedal still\n"
               "holds); the pedal up ends them all.")
    s.at(100).midi(cc(64, 127), on(60, 100)).wait(50).midi(off(60))
    s.wait(200).midi(on(60, 100)).wait(50).midi(off(60), on(64, 100))
    s.wait(100).event("key 14 down").wait(100).event("key 14 up").wait(10)
    s.midi(off(64)).wait(200).midi(cc(64, 0))
    s.wait(300).midi(on(67, 100), cc(64, 127), cc(123, 0)).wait(300).midi(cc(64, 0))
    return s


def midichan():
    s = Script("midichan", "midichan (R-MIDI-5): the channel test build receives on channel 10\n"
               "only: notes, controllers and program changes on every other channel\n"
               "are filtered; channel 10's play.")
    s.at(100)
    for ch in range(16):
        if ch != 9:
            s.midi(on(60 + ch, 100, ch), cc(7, 0, ch), [0xC0 | ch, 3], off(60 + ch, ch))
    s.wait(50).midi(on(72, 100, 9)).wait(200).midi(off(72, 9))
    return s


def midipanel():
    s = Script("midipanel", "midipanel (R-MIDI-6): MIDI and the panel together. KEY1 (note 53)\n"
               "and MIDI note 53 overlap, each released while the other holds; MIDI\n"
               "notes in the keyboard's range shown in cyan (screen at 900 ms, MIDI\n"
               "holding 60 and 64, KEY5 down, the event line MIDI's last note);\n"
               "nothing left sounding.")
    s.at(100).event("key 14 down").wait(50).midi(on(53, 100)).wait(100).event("key 14 up")
    s.wait(100).midi(off(53))
    s.wait(100).midi(on(53, 100)).wait(50).event("key 14 down").wait(100).midi(off(53))
    s.wait(100).event("key 14 up")
    s.at(800).event("key 18 down").wait(20).midi(on(60, 100), on(64, 100))
    s.at(1000).midi(off(60), off(64)).wait(5).event("key 18 up")
    return s


def midilat():
    s = Script("midilat", "midilat (R-MIDI-7): 20 notes, one every 150 ms, alone, so the time\n"
               "from each note on's last byte to its first sample can be measured.")
    s.at(100)
    for i in range(20):
        s.at(100 + 150 * i).midi(on(60 + i % 12, 100)).wait(60).midi(off(60 + i % 12))
    return s


# The loaded measure's input (tools/perf.py) ends with a full MIDI wire
# through its window (since M6a): written here, after this marker line.
PERFLOAD = os.path.join(SCRIPTS, "perfload.txt")
PERFLOAD_MARK = "# --- MIDI, since M6a (written by tools/midi_scripts.py; don't edit below) ---"


def perfload_midi():
    """From 1 000 ms to past 2 300 ms (the perf runs' window is 1 250 to
    2 250 ms): 16 notes held, each struck again in turn in running status
    (note on, then off at velocity 0), the mod wheel and pitch bend moving
    every eighth note; the wire never rests."""
    s = Script("perfload", "")
    notes = list(range(48, 80, 2))
    s.at(1000).midi(0x90, [x for n in notes for x in (n, 100)])
    i = 0
    while s.t < 2300:
        n = notes[i % 16]
        s.midi(0x90, n, 0, n, 60 + i % 60)
        if i % 8 == 7:
            s.midi(cc(1, i % 128), bend((i * 997) % 16384))
        i += 1
    s.midi(bend(8192), cc(1, 0), 0x80, [x for n in notes for x in (n, 0)])
    return s


def perfload_text(old):
    head = old.split(PERFLOAD_MARK)[0].rstrip("\n") + "\n"
    return head + PERFLOAD_MARK + "\n" + "\n".join(perfload_midi().lines) + "\n"


CASES = (midimsg, midirun, midisysex, midijunk, mididense, midisustain, midichan, midipanel, midilat)


def stream(path):
    """The bytes of a script's `midi` events in order, and each byte's
    arrival time (ms)."""
    out = []
    with open(path) as f:
        for line in f:
            w = line.split("#")[0].split()
            if len(w) >= 3 and w[1] == "midi":
                t = float(w[0])
                for i, h in enumerate(w[2:]):
                    out.append((round(t + BYTE_MS * (i + 1), 3), int(h, 16)))
    return out


def main(argv):
    check = "--check" in argv
    bad = 0
    for case in CASES:
        s = case()
        path = os.path.join(SCRIPTS, s.name + ".txt")
        text = s.text()
        if check:
            old = open(path).read() if os.path.exists(path) else None
            if old != text:
                print("%s differs from what tools/midi_scripts.py writes" % path)
                bad = 1
        else:
            with open(path, "w") as f:
                f.write(text)
            print("wrote %s (%d lines, ends %.1f ms)" % (os.path.relpath(path, ROOT), len(s.lines), s.t))
    with open(PERFLOAD) as f:
        old = f.read()
    text = perfload_text(old)
    if check and old != text:
        print("%s's MIDI part differs from what tools/midi_scripts.py writes" % PERFLOAD)
        bad = 1
    elif not check:
        with open(PERFLOAD, "w") as f:
            f.write(text)
        print("wrote the MIDI part of %s" % os.path.relpath(PERFLOAD, ROOT))
    return bad


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
