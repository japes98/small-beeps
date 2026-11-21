audio7 on the unit (hw3q, from the flash log; source UNIT):
- L1: CON3 C2, CON1 1000, CON0 0800 written, read back the same. ALNK0
  RAN: 366 half changes and 366 source-11 interrupts in the 1 s watch, 366.2
  halves a second = 46 873.6 frames a second if a half is LEN (128) frames
  (expected 46 875), so reading (a) holds. CLK_CON2 00000006 throughout.
  Kept, then undone by key; put back cleanly.
- L2 with CLK_CON2 bit 9 SET (00000206): CON3 83, CON1 1000, CON0 0800
  written and read back, but nothing moved (0 changes, 0 interrupts). Put
  back by the firmware.
- L2 with bit 9 CLEAR (00000006): RAN: 345 changes, 345 interrupts, 344.7
  halves a second = 44 121.6 frames a second (expected 44 117.6). Kept,
  then undone by key.
- In every try: the matrix check passed (idle rows 3F before, during and
  after), port A unchanged, core 1 kept counting, no hang, log_fails 0.
- So HW-157/158's fields hold on this chip. The PLL audio clock reaches
  ALNK0 with bit 9 clear, and setting bit 9 stops it. 44 117.6 frames a
  second needs no PLL write.

Next, in one PR with the results recorded: the routing of data 3 to the
pins, the amplifier enable and headphone sensing, as a clean prompt that
builds on L2 (bit 9 clear). Per the owner's new rule, set out the options
and their risks (the port A group B1 overlap with the matrix included)
for the owner to rule on before clean starts. Every clean prompt from
now on: run only the touched seams cases while iterating, no full local
run before the PR, and say where the build time went.
