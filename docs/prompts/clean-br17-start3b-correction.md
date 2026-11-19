Start3 result (99e769ea…, identity FM-1_0.10.0-hw3), on the unit. Correction
to my earlier note: the flash round trip works; the hang is after it.

- Bands: blue, green, white.
- "win" row, from a phone photo (some digits uncertain):
  win 0098038? 04000 key 0980F/980F   (CON reads non-zero; no red "reads 0"
  line, so the round trip was tried)
- "flash 856014 s1 00 s2 02 back": clear.
- Then the address pattern comes and stays. The test screen never comes.
- No LED lights, and buttons light nothing: the main loop never runs.

So taking and giving back the flash works, and CON appears to read back the
mode word (SR-17's open question). The hang is between "back" and the test
screen: the power-on counter's save (c), or the matrix, ADC or core 1
set-up. Next build: hold the start-up rows on screen, and draw a short row
(or light one LED) after each of those steps, so a hang shows exactly where.
If the counter's save is first, say whether anything could have been written
at 0xFC000.
