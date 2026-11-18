Start-up build result (start1, c02427d9…, identity FM-1_0.10.0-hw1), on the
unit, 2026-11-18:
- The backlight came on; the blue, green and white bands were drawn in order.
- Then nothing more: no address pattern, no test screen. The screen stays on
  the three bands (no red halt screen).
- While stuck there, every button tried, PLAY, OCT− and OCT+ included,
  lights its own LED while held and puts it out on release. (Whether OCT−
  and OCT+ register as their own buttons on the test screen is still
  untested: there's no test screen yet.)

So the panel bring-up, running from RAM, interrupts, TIMER0's tick, the key
scan and the LEDs all work on the chip. Only the drawing is stuck: it stops
at the first DMA transfer to the panel (or SPI1's interrupt), as your band
table says, while the timer interrupt keeps running.

Next: find which, with one more probe-style step if needed: e.g. a band after
the DMA is started, one when its completion interrupt fires, and one if a
polled wait sees it finish without the interrupt. If HARDWARE-SPEC doesn't
give what DMA or SPI1's interrupt needs on the chip, file an SR naming it.
Same rules: key 0x980F, flash 0x4000 up only. End with "done, ready to
clear", Questions, merge order and the file to try, with what each outcome
means.
