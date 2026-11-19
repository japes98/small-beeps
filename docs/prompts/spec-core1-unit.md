Unit facts, 2026-11-19 (source UNIT, relayed by the owner), from core1 A
(31bc037f…), core1 B (c9115aaf…) and their finder, PA0 pulled up:
- Core 1 runs after setting C1_CON bit 3 and then clearing bit 1, with or
  without the SYS_DIV step (A and B both sign YES at once). C1_CON reads
  01000002 after setting bit 3 (bit 3 doesn't read back set), 01000000
  after clearing bit 1. A's SYS_DIV went 00010200 > 00010208 > restored.
- Encoders in the matrix: KNOB1 row PA5 columns 8/9; KNOB2 row PA0 columns
  8/9; KNOB3 row PA0 columns 6/7; KNOB4 row PA0 columns 4/5; ALGORITHM row
  PA0 columns 2/3; SELECT row PA0 columns 0/1 (seen on B's finder only).
  PA0 is a matrix row that needs its pull-up.
- PRESETS: not found in the matrix, ports A/B/C/H or ADC 0–11.
Record them; keep PRESETS as a note. End with "done, ready to clear".
