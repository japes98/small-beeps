Unit facts, 2026-11-21 (source UNIT, from report1/hw3k's flash log, read
back exactly; no photo reading):
- Correction: DAA_CON7 reads exactly 00004901 (not C901 as relayed from
  a photo).
- H, counter check: CLK_CON1 → 00010030, GPCNT CON 00001A09, gate 32768
  cycles: NUM 245760 twice (exactly 7.5×, 180 MHz vs 24 MHz). The pending
  flag never appeared (timed out each time) but both readings agree.
- H, "audio clock" (CLK_CON1 bits 4–6 = 5, CLK_CON1 00010050), same gate:
  NUM 65537/65537 with CLK_CON2 00000006 (bit 9 clear); 65536/65536 with
  00000206 (bit 9); 65537/65537 with 00000306 (bits 9 and 8). So ~48.00
  MHz (2× the crystal) in every state, unchanged by bits 8 and 9; not
  11.29 or 12.31 MHz.
- I: ALNK1 CON0 00000800 (run), CLK_CON2 00000306 → 00000B06 (bit 11) →
  00000F06 (bit 10): no CON0 bit 15 changes, no pending, over 1000 poll
  beats. ALNK0 dead throughout (irq 0). Both links fail the same way.
- Core 1 counted throughout. All undos/refusals behaved as designed.
Record them. Then interpret: what is the 48 MHz on the counter's input 5
(a fixed source, or is input 5 not the links' clock on this chip)? Does
this count as "an audio clock while ALNK0 stays dead" (my D condition),
or does it point elsewhere? Set out the next options with source and risk
for my ruling. Don't write a clean prompt yet. End with "done, ready to
clear".
