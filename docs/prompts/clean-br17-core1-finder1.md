#201 is merged. On your question 1: I saw KNOB1 light the top row (PA5)
yesterday; I'm running finder1 (879d2d31…) now and will pass on its lines
for every control. Meanwhile, read and follow
~/Development/<top>/drop/prompts/clean-br17-core1.md

finder1 result (879d2d31…, identity FM-1_0.10.0-hw3c), on the unit,
2026-11-19. Controls turned one after another without a power cycle between
them, so lines accumulate; counts below are what each one added.

- KNOB1: c8 PA5 x116 and c9 PA5 x106 (and c10 PA5 x24). KNOB1's row is PA5.
- MASTER: AD4 007:3C0 200 03F. The pot, as known.
- KNOB2, KNOB3, KNOB4: nothing new.
- PRESETS: nothing new (yesterday it seemed to move an ADC value).
- SELECT: c0 PA0 once, not reproducible.
- ALGORITHM: c0 PA0 x6→x12 and c1 PA0 x6→x10, maybe c2, only on the first
  turn.
- Throughout: "pin PA0" and c0–c5 PA0 lines with small counts, and AD8 and
  AD9 wandering on every screen. noisy 5, lost up to 10, ~3100 sweeps/s.
- PU A01E0 B0000 C0000 D002D H0000; DIR AF9E1 BFFFF CF87F DFFC2 HFDBF.
- core1 0; c1con 01000002>01000002 now 01000002; c1 word 01C2D820 fn 01C2D820.

My reading: PA0 may be a fifth matrix row carrying the other encoders, left
floating because nothing pulls it up (only PA5–PA8 have pull-ups). In the
next build, pull PA0 up like PA5–PA8, treat it as a row in the scan and the
finder, and show each encoder's cells as before. Also say why AD8 and AD9
wander (floating inputs?) and leave them out of the noise if so. Fold this
into the core 1 build if that's simpler; same rules, file to try at the end.
