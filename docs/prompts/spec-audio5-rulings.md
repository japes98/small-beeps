#219 is merging. Rulings (owner):
1. K allowed, as you describe it (read-modify-write of CLK_CON1 bits 4–6
   and 2–3 and the counter's own register; undo restores as read).
2. J allowed, narrowly: ALNK0's own CON1 and CON3 only, one bit at a
   time, each by key press with readback, watching CON0 bit 15 and the
   interrupt count, each undoable; no pins routed, no other register.
   Every try logged.
3. Yes: if K shows input 5 is the shared PLL 48 MHz, that counts as "no
   audio clock". But E and F come up for my ruling only after K and J
   have both been tried and failed. Not in this build.
Clean is finishing leds1 (key LEDs on top of report1). Write the clean
prompt for K and J as additions to leds1, in the same build, with every
reading in the flash log. End with "done, ready to clear".
