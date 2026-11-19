encoders1 result (f90fec1f…, identity FM-1_0.10.0-hw3f), on the unit,
2026-11-19:
- Core 1: the core1 row rises every second (B's release works in the
  normal build).
- Encoders on the test screen, one slow detent clockwise then one
  anticlockwise:
  KNOB1 +1 c9 / -1 c8; KNOB2 +1 c9 / -1 c8; KNOB3 +1 c7 / -1 c6;
  KNOB4 +1 c5 / -1 c4; SELECT +1 c1 / -1 c0; ALGORITHM +1 c3 / -1 c2.
  So clockwise is +1 for all six, and the higher column of each pair closes
  first when turning clockwise.
- PRESETS: nothing on the test screen, because your table has it at
  columns 0/1. In the finder (HOME), a brisk turn shows c12 PB7 x22 and
  c11 PB7 x22 (a slow one only c11–c13 x2–4). PU B0080, so PB7's pull-up is
  on. PRESETS is row PB7, columns 11/12.

#205 is merging. Next: decode PRESETS at PB7 columns 11/12 (show its
event line in large text, so one run gives its phase order), then move on
to audio per the spec side.
