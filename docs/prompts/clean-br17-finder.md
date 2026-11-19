Start3b result (7ad88397…, identity FM-1_0.10.0-hw3b), on the unit,
2026-11-19:
- Bands, OCT− and OCT+ lit together during the hold, then the last band
  quickly and the test screen. "step 22: test screen up, main loop next";
  beat counting. Every key registers with its number and up/down.
- win 009803B5 04000 key 0000/980F
- flash 856014 s1 00 s2 02 back
- on 14 put 0 get 4 v0 e0 856014, then on 15 after a power cycle: the store
  works on the unit.
- core1 0 c1con 01000002, still 0 later: core 1 doesn't run.
- in A 01E1 B 01BC C 007F H 01AF at rest; ad 0-5 3FF 3FF 000 380 200 3E0,
  ad6-11 3F0 3C0 000 3FF 380 380 at rest.
- MASTER (has end stops) moves the 5th value of "ad 0-5" (channel 4) from
  000 to 3FF: it's the pot.
- PRESETS (endless) reads 200 at rest and changes while turning (too fast
  and too small to read): looks like an encoder read through the ADC.
- KNOB1 toggles the dots under columns 8 and 9 in the matrix, but only when
  spun fast; one direction lights one, the other the other.
- KNOB2, KNOB3, KNOB4, SELECT and ALGORITHM: nothing I could see in the
  matrix, the "in" row or the ADC rows.

The font is too small to read on the unit. In the next build, show the
knob findings big: e.g. one large line per control that names what changed
(a matrix cell, a port bit or an ADC channel, with its value) and holds it
for a second, and fast enough sampling to catch an encoder's steps. Then
find KNOB2-4, SELECT and ALGORITHM, and PRESETS' channel and values.
Core 1: find why it doesn't start (file an SR if HARDWARE-SPEC lacks it).
Same rules; end with "done, ready to clear", Questions, merge order, file.
