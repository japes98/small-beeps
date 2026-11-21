#225 is merging. Rulings (owner):
1. Allowed: write HW-157's fields to ALNK0's CON0, CON1 and CON3 as you
   proposed (oscillator set-up first: CON3 0xC2, CON1 0x1000, CON0 bit 11
   with bits 7 and 8 clear; then the PLL audio clock: CON3 0x83 with
   CLK_CON2 bit 9 set and clear), one set-up per key press, each undone by
   the firmware with D's safety machinery (log before each write, matrix
   check, self-undo), every reading logged including LEN and the expected
   halves a second under both readings.
2. D is held: keep it out of the next run's order; a null D doesn't count
   toward E and F.
Write the clean prompt (audio7) as additions to the build clean is
finishing now (audio6 with the CRC/sb_now fix and the next-key LED
guide), with the new set-ups in the next-key order and D removed from
that order. End with "done, ready to clear".
