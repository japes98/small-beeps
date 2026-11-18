Panel probe result, on the unit, 2026-11-18:
File tried: small-beeps-panel1-bars-key-980f.fwsc, SHA-256 5ffe64fc…9c56747f
(identity FM-1_0.10.0-lcd1), installed before #<PR> CI finished; if CI made
you rebuild, say whether the shipped file differs.

- Colour bars on the screen, with a yellow square in the top right corner,
  backlight on.
- Then the recovery menu said "APP EXITED".

So the panel bring-up from HW-115 works, along with the backlight, the LED
and the return. Check the square's corner and the bars' order against what
the probe draws: if either is mirrored or rotated, fix the panel's
orientation and say so.

Next: small-beeps' real start-up on the unit, its screen, keys, LEDs and
timer from section 26, as one hardware build (no probe), staying in the
firmware instead of returning. Same rules: facts only from HARDWARE-SPEC,
SR for anything missing, key 0x980F, flash 0x4000 up only. End with "done,
ready to clear", Questions, the merge order and the file to try, with what
the unit should show.
