Rulings (owner):
1. Allowed: audio2 may set CLK_CON2 bit 9, as the prompt describes:
   only by the key press, read-modify-write of that bit alone, a second
   press restoring the value read before, nothing else written. Keep the
   prompt as it is.
2. No probe of PLL2 or any PLL for now. Decide after audio2's results;
   if bit 9 doesn't start ALNK0, set out the options with their risks and
   I'll rule then.
#211 is merging. Nothing else until audio2's results; no need to reply
beyond "done, ready to clear".
