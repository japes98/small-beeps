Start3 result (99e769ea…, identity FM-1_0.10.0-hw3), on the unit:
- The bands and rows flash by in about 2 s (too fast to read the "win" row).
- Then the address pattern (the gradient) comes and stays. The test screen
  never comes.
- No LED lights; [pressing a button lights its LED / does nothing].
- No red line seen, but the start-up rows were too brief to read.

Per your table this looks like taking the flash hanging, but I can't give you
the "win" row. Make the next build hold the start-up rows on screen: draw the
"win" row (and every row before the flash step) where the pattern won't
cover it, or pause about 5 s on them before going on, so I can read them.
Also light one LED just before taking the flash and another just after, so a
hang shows which side it's on.

Nothing should have been written to flash (power-on counter not reached).
