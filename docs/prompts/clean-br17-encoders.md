Core 1 and finder results, on the unit, 2026-11-19.

Core 1 A (31bc037f…, hw3d): sign YES 0ms, count 32801254 and rising.
SD 00010200 > SD+3 00010208 > SD= 00010200. C1 01000002, C1+3 01000002,
C1-1 01000000. W ok 01C2D8D0. In the finder its counter keeps rising (to
over 10^9).
Core 1 B (c9115aaf…, hw3e, no SYS_DIV): sign YES 0ms, count 32801308.
SD 00010200, SD+3 not written, SD= 00010200. C1 01000002, C1+3 01000002,
C1-1 01000000. W ok 01C2D8D0.
So clearing C1_CON bit 1 (after setting bit 3) is what starts core 1;
the SYS_DIV step isn't needed. Use B's release.

Finder, power-cycled before each control, PU A01E1 (PA0 pulled up). On A
unless noted:
- KNOB1: c8/c9 PA5 (as before)
- KNOB2: c8/c9 PA0, x32 each (the finder labels it KNOB1 by column)
- KNOB3: c7 PA0 x200, c6 PA0 x186
- KNOB4: c5 PA0 x62, c4 PA0 x58
- ALGORITHM: c3 PA0 x286, c2 PA0 x242
- SELECT: c1 PA0 x28, c0 PA0 x28, on B's finder only. On A it showed just
  c2 PA0 x8 and didn't repeat. Say whether anything in A could explain
  that, or whether it was just my turning.
- PRESETS: nothing on either build: not found.
- MASTER: AD4, as known.
- Neighbouring columns bleed a few to a few dozen counts (c4 with ALGORITHM,
  c8 with KNOB3, c10 with KNOB1/2).

Next build: use these encoders (decode each pair, and say which column is
which phase from a slow turn), keep core 1 running with B's release, and
look for PRESETS on pins the finder doesn't read yet (port D's masked bits,
other ports). If HARDWARE-SPEC lacks what you need, file an SR. Same rules;
file to try at the end.

---

Follow-up on SELECT: it works reliably on B's finder over several power
cycles, c1 PA0 and c0 PA0 (c2 bleeding). A's one try showing only c2 x8
was most likely my turning, so no need to look into A for it.
