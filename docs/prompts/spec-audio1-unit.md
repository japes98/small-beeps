Unit facts, 2026-11-19 (source UNIT, relayed by the owner), from audio1
(fb827761…), with ALNK0 set up as fwtest's audio.c does and nothing written
to the clock, PLL2, analogue or JL_AUDIO registers:
- ALNK0 does not run after m-bootloader hands over: its run bit is set
  (CON0 00000000 → 00000800) but there are no source-11 interrupts, CON0
  bit 15 never changes, and frames per second is 0. Nothing heard on the
  speaker or on headphones.
- Values as read, unchanged when the tone started:
  PLL2_CON0 0940022B; CLK_CON2 00000006; DAA_CON0–3 0; DAA_CON7 0000C901;
  ADA_CON0–2 0; DAC_CON 0; ALNK0 CON1–CON3 0; pin-map registers 0000000F
  and 00000010.
So this is the "doesn't run" outcome: ALNK0 needs its clock after the
hand-over. Record these facts. Then, from the sources my rulings allow:
1. Work out what ALNK0 needs to get a clock: which source the audio
   clock is selected from, whether PLL2 must run (and what 0940022B says
   about its current state), and which gates or enables apply. For every
   register value you'd have clean write, give its source; if a value has
   no allowed source, say so and don't guess it.
2. Answer clean's SR-20 (how ALNK0 is routed to the port C pins).
3. Write a clean prompt for audio2: the same probe, plus the clock set-up
   from 1 and the routing from 2, writing only registers whose values have
   a source, and still reading back everything audio1 reads.
End with "done, ready to clear".
