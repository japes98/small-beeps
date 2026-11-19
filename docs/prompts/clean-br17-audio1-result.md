audio1 (fb827761…, identity FM-1_0.10.0-hw3h) on the unit, 2026-11-19:
- ALNK0 does not run. Audio page: IRQ 0, b15 0, fps 0.0, h/s 0 (all red),
  alt 0, pend 0. Nothing heard on the speaker or on headphones.
- Registers, at call → tone on:
  PLL2 0940022B → 0940022B; CLK2 00000006 → 00000006;
  DAA0–DAA3 0; DAA7 0000C901 → 0000C901; ADA0–ADA2 0; DAC 0;
  AL0 00000000 → 00000800 (run bit set); AL1–AL3 0;
  MAP0 0000000F, MAP1 00000010, both unchanged;
  PCOUT 00000180 → 00000100; PCDIR 0000F87F; PCDIE 0000FFFF; PCPU 0; PCPD 0.
- Bug: the status line shows "vol 0" with MASTER turned well up, so the
  audio page isn't picking up MASTER (ADC 4). Please fix it in the next
  audio build.
#209 is merged. Nothing else for now; the next audio build waits on the
spec side's prompt (clock set-up and SR-20).
