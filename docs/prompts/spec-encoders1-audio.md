Unit facts, 2026-11-19 (source UNIT, relayed by the owner), from encoders1
(f90fec1f…):
- Each encoder's phase order: turning clockwise, the higher column of the
  pair closes first (KNOB1 and KNOB2 c9 before c8, KNOB3 c7 before c6,
  KNOB4 c5 before c4, SELECT c1 before c0, ALGORITHM c3 before c2).
- Core 1 runs in the normal build by setting C1_CON bit 3, then clearing
  bit 1 (no SYS_DIV step).
- PRESETS reads on row PB7 (pull-up needed), columns 11/12 (a brisk turn:
  c12 PB7 x22, c11 PB7 x22). Its phase order isn't known yet.
Record them. Then start on audio: what small-beeps needs for sound on the
chip (clocks, output, DMA, the analogue side), from the sources my rulings
allow, and a clean prompt for a first audio build. End with "done, ready
to clear".
