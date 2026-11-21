audio2 (73604762…, identity FM-1_0.10.0-hw3i) on the unit, 2026-11-20:
- MASTER fix works (vol 768 with MASTER up).
- Before the step: as audio1. IRQ 0, b15 0, fps 0.0, h/s 0.
- REC step: CLK2 00000006 → 00000206 as intended, no hang. ALNK0 still
  doesn't run: IRQ 0, b15 0, fps 0.0, h/s 0. Nothing heard on the speaker
  or on headphones. Second REC: line ends in U, CLK2 put back, screen and
  keys keep working.
- Core 1 (new, repeated after a power cycle): core 1 runs ONLY while the
  step is taken.
  1) After power-on, before any step: the core1 count does not move.
  2) After REC (T): it rises.
  3) After the second REC (U): it stops again. c1con reads 01000000.
  The main loop (beat) keeps running throughout. In encoders1 and
  presets1 core 1 ran with no step. Please explain this from your own
  code: what core 1 does in audio2 (and audio1) that it doesn't in
  presets1, and why CLK_CON2 bit 9 would let it run. If you can't tell,
  add what would tell us to the next build rather than guessing.
- Page 1/2, unchanged by the step apart from CLK2: PLL2 0940022B;
  DAA0–3 0; DAA7 0000C901; ADA0–2 0; DAC 0; AL0 00000800 (tone on);
  AL1–3 0; MAP0 0000000F; MAP1 00000010; PCOUT 00000100; PCDIR 0000F87F;
  PCDIE 0000FFFF; PCPU 0; PCPD 0.
- Page 2/2, identical at call, with the tone on, and after the step:
  CLK0 000001C1; CLK1 00010000; SYSDV 00010200; PLL0 45400203;
  PLL1 3F503026; PL2_1 0750310C; MAP2 003C0000; MAP3 00008888; MAP4 0;
  MAP5 0; MAP6 FFFFFFFF; MAP7 0; MAP8 0.
#212 is merged. Reply with your explanation of the core 1 result; the
next audio build waits on the spec side.
