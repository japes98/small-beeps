Start3 on the unit (99e769ea…, identity FM-1_0.10.0-hw3):
- The flash round trip works: "flash 856014 s1 00 s2 02 back".
- The "win" row, from a phone photo (some digits uncertain):
  win 0098038? 04000 key 0980F/980F. CON reads non-zero, apparently the mode
  word 0x00980381, which bears on SR-17's open CON question; no red
  "reads 0" line.
- Then it hangs on the address pattern, before the test screen: no LEDs,
  buttons dead, so the main loop never runs. The hang is after the flash
  step: the power-on counter's save, or the matrix, ADC or core 1 set-up.

Clean is making a build that holds the start-up rows on screen and marks
each step, so the next result shows exactly where. Keep #196 and the clean
prompt held until that result.

Also: HW-132 cites FM-1-RE for CON's bit 31. Say what FM-1-RE is, its
licence, and which ruling or earlier section allows it as a source. If none
does, take that fact out (the unit's "win" row settles it anyway) and log it
in EXPOSURE.
