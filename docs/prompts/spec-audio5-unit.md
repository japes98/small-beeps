Unit facts, 2026-11-21 (source UNIT, audio5/hw3n's flash log, exact):
- K: in3 bus 180.000 MHz; in1 sample-rate converter 360.001; in5 audio
  48.000; in6 wireless 48.000; in7 USB 48.000; counter's own input
  480.001. Input 5 with CLK_CON1 bits 2–3 (DAC clock choice) = 1:
  24.000 MHz; = 2: 60.001; = 3: 0.000; back as read (0): 48.000.
  So input 5 is the audio block's clock and follows the DAC choice, and
  choice 0 gives 48 MHz here (not the "PLL 24 MHz" HW-53 names).
- J: ALNK0 CON1 bits 0–15 and CON3 bits 0–7, each alone, 100 ms each,
  with CLK_CON2 00000206 and again with 00000006: every bit read back as
  written and was put back; none moved CON0 bit 15 or the interrupt count.
Record them. By my earlier ruling this meets the condition for D: an
audio clock exists while ALNK0 stays dead. Write the clean prompt for D
(JL_IOMAP->CON5), with: port A's rows shown and logged before and after,
the key matrix checked still working after each try, every try by one
key press or one automatic sweep (your call, say which), each undoable,
and everything logged. Also say whether the audio block's 48 MHz with
choice 0 changes anything else you've set out (the 48 MHz / 1088 =
44 117.6 point). End with "done, ready to clear".

To clean:

audio5 (6c3097a2…, hw3n) ran on the unit: 65 records read back. K and J
worked as designed (results to the spec side). Two things:
and everything logged. Also say whether the audio block's 48 MHz with
choice 0 changes anything else you've set out (the 48 MHz / 1088 =
44 117.6 point). End with "done, ready to clear".
