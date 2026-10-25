#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
"""A reference model of the firmware's MIDI 1.0 byte parser (M6a;
firmware/src/midi.c, docs/DESIGN-NOTES.md, M6a, "The parser").

Written again from the same rules, not from the C, so the fwtest MIDI
cases can check the firmware's record against it: the messages it logs
(status, data 1, data 2, length) and its counters, for any byte stream.

  midi_model.py HH HH ...      prints the messages and counters

Rules (the MIDI 1.0 specification's):
- 0xF8 to 0xFF are realtime: a message of their own wherever they come,
  even between a status and its data, changing nothing else; 0xF9 and
  0xFD are undefined (counted, dropped); 0xFF, a reset, also clears
  running status and any SysEx.
- 0xF0 starts a System Exclusive message: its data bytes are skipped
  (counted; past SYSEX_LIMIT it is counted as too long). 0xF7 ends it and
  is logged as (0xF0, length & 0x7F, min(length >> 7, 0x7F), 2). Any other
  status but realtime cuts it short (counted).
- Every non-realtime status ends running status. A channel status (0x80
  to 0xEF) starts it: its data bytes follow (one for 0xC0 and 0xD0, two
  for the rest), and further data bytes reuse it. System common: 0xF1 and
  0xF3 take one, 0xF2 two, 0xF6 none; no running status after them. 0xF4
  and 0xF5 are undefined, and an 0xF7 with no SysEx is a stray: counted.
- A status that arrives while a message still waits for its data cuts it
  short (counted). A data byte with no status is an orphan (counted).
"""

import sys

SYSEX_LIMIT = 4096
COUNTERS = ("parsed", "messages", "realtime", "sysex", "sysex_bytes", "sysex_long",
            "sysex_cut", "orphans", "undefined", "cut")


def data_bytes(s):
    if s < 0xF0:
        return 1 if (s & 0xF0) in (0xC0, 0xD0) else 2
    return {0xF1: 1, 0xF3: 1, 0xF2: 2, 0xF6: 0}.get(s)


class Parser:
    def __init__(self):
        self.count = dict.fromkeys(COUNTERS, 0)
        self.log = []
        self.reset()

    def reset(self):
        self.status, self.need, self.data = 0, 0, []
        self.sysex, self.sysex_len = False, 0

    def emit(self, status, d1=0, d2=0, length=0):
        self.log.append((status, d1, d2, length))
        self.count["messages"] += 1

    def end_pending(self):
        if self.sysex:
            self.count["sysex_cut"] += 1
            self.sysex = False
        if self.status and self.data:
            self.count["cut"] += 1
        self.data = []

    def byte(self, b):
        c = self.count
        c["parsed"] += 1
        if b >= 0xF8:
            if b in (0xF9, 0xFD):
                c["undefined"] += 1
                return
            c["realtime"] += 1
            self.emit(b)
            if b == 0xFF:
                self.end_pending()
                self.reset()
            return
        if b >= 0x80:
            ended = False
            if b == 0xF7 and self.sysex:
                n = self.sysex_len
                self.emit(0xF0, n & 0x7F, min(n >> 7, 0x7F), 2)
                self.sysex = False
                ended = True
            else:
                self.end_pending()
            self.status, self.need = 0, 0
            if b == 0xF0:
                self.sysex, self.sysex_len = True, 0
                c["sysex"] += 1
            elif b == 0xF7:
                if not ended:
                    c["undefined"] += 1
            else:
                n = data_bytes(b)
                if n is None:
                    c["undefined"] += 1
                elif n == 0:
                    self.emit(b)
                else:
                    self.status, self.need = b, n
            return
        if self.sysex:
            self.sysex_len += 1
            c["sysex_bytes"] += 1
            if self.sysex_len == SYSEX_LIMIT + 1:
                c["sysex_long"] += 1
            return
        if not self.status:
            c["orphans"] += 1
            return
        self.data.append(b)
        if len(self.data) < self.need:
            return
        d = self.data + [0]
        self.emit(self.status, d[0], d[1] if self.need > 1 else 0, self.need)
        self.data = []
        if self.status >= 0xF0:
            self.status = 0


def parse(stream):
    p = Parser()
    for b in stream:
        p.byte(b)
    return p


# The four knobs' controllers (M6a's map, firmware/src/fm_play.c): a
# controller's 64 is no offset, 0 and 127 the ends of each knob's span.
KNOB_SPAN = ((-24, 24), (-32, 32), (-64, 32), (-7, 7))
# Since M8a, the macros' (BRIGHT, COLOR, SHAPE, MOTION), by the same rule
# (KNOB_SPAN is "Knobs: direct"'s).
MACRO_SPAN = ((-64, 32), (-32, 32), (-64, 64), (0, 64))


def _div(a, b):
    """C's integer division: toward zero."""
    q = abs(a) // abs(b)
    return q if (a >= 0) == (b > 0) else -q


def knob_offset(k, v, spans=KNOB_SPAN):
    """The knob offset MIDI in takes from controller value v."""
    lo, hi = spans[k]
    return _div((v - 64) * hi, 63) if v >= 64 else _div((64 - v) * lo, 64)


def knob_value(k, p, spans=KNOB_SPAN):
    """MIDI out's inverse (M6b): the smallest controller value whose
    offset is the knob position p, held to the span. Written from the
    rule, not the C: searched, not computed."""
    lo, hi = spans[k]
    p = max(lo, min(hi, p))
    cands = [v for v in range(128) if knob_offset(k, v, spans) == p]
    if not cands:
        # Since M8a: a span of more than 127 steps (SHAPE, MOTION) leaves a
        # few positions no controller value gives; MIDI out sends the first
        # one past it, away from 64.
        return min(v for v in range(64, 128) if knob_offset(k, v, spans) >= p) if p > 0 else \
            max(v for v in range(0, 65) if knob_offset(k, v, spans) <= p)
    return min(cands, key=lambda v: abs(v - 64))


def main(argv):
    p = parse(int(x, 16) for x in argv)
    for m in p.log:
        print("%02x %02x %02x %d" % m)
    for k in COUNTERS:
        print("%s %d" % (k, p.count[k]))


if __name__ == "__main__":
    main(sys.argv[1:])
