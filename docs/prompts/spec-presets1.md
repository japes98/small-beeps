#206 has merged (it carried #207). The audio1 prompt went to clean.

Unit facts, 2026-11-19 (source UNIT, relayed by the owner), from presets1
(ffa5bb1e…):
- PRESETS turned clockwise closes column 12 before 11 (+1 c12, -1 c11).
  All seven encoders now decoded.
- The 14-slot scan works: all encoders and keys as before, core 1 still
  runs, button LEDs perhaps a little dimmer.
Record them.

On your question (ALNK0 runs but is silent): don't choose yet. audio1's
readback includes listening on the speaker and then on headphones, and
that decides it:
- Heard on headphones but not on the speaker: look into the amplifier's
  enable pin. Write down the candidate pins no source assigns, with what
  is known about each, but don't propose driving any of them until the
  owner rules on it.
- Silent on both: the problem comes before the amplifier. Look into
  whether ALNK0 feeds a part outside the chip that needs setting up (and
  over which bus), against the chip's own DAC path. Say for each what an
  allowed source gives and what it doesn't.
Nothing more to do on it until the audio1 results come in. End with
"done, ready to clear".
