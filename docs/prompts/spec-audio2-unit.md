Unit facts, 2026-11-20 (source UNIT, relayed by the owner), from audio2
(73604762…):
- CLK_CON2 bit 9 taken by key: 00000006 → 00000206, no hang, put back
  cleanly. ALNK0 still does not run: no source-11 interrupts, CON0 bit 15
  never changes, frames per second 0, nothing heard on speaker or
  headphones. So bit 9 alone does not start ALNK0.
- Core 1 in audio2 runs only while bit 9 is set, repeatably: stopped after
  power-on, running after the step, stopped again after the undo.
  C1_CON reads 01000000 throughout. (In encoders1 and presets1 core 1 ran
  without any step.) I've asked clean what core 1 does in this build; treat
  the cause as open until it answers.
- Readback after m-bootloader's call, unchanged with the tone on and after
  the step: CLK_CON0 000001C1; CLK_CON1 00010000; SYS_DIV 00010200;
  PLL_CON0 45400203; PLL_CON1 3F503026 (both as HW-144 expected);
  PLL2_CON0 0940022B; PLL2_CON1 0750310C; JL_IOMAP CON2 003C0000,
  CON3 00008888, CON4 0, CON5 0, CON6 FFFFFFFF, CON7 0, CON8 0.
  Page 1/2 as audio1 (DAA_CON7 0000C901, DAC_CON 0, ALNK0 CON0 00000800
  with the tone on, CON1–CON3 0).
Record them. Then:
1. Say what these values tell you: which PLL outputs are on (from
   PLL_CON1 and PLL2_CON1), whether the 192 MHz source ALNK0 needs looks
   available, and what CON2/CON3/CON5/CON6 say about the clock gate or
   pin group that FM-1-RE describes two ways.
2. Does any allowed source say what CLK_CON2 bit 9 clocks besides ALNK0,
   something core 1 could depend on?
3. One cheap thing to check: audio2 set ALNK0's run bit before the clock
   step. Does any source say the link must be (re)started after its clock
   is enabled, or that CON0 needs more than bit 11 set?
4. Set out the remaining options to get ALNK0 running, each with its
   source and its risk (anything touching PLL2 or the system clock needs
   my ruling, as before). Don't write a clean prompt yet; I'll rule first.
End with "done, ready to clear".
