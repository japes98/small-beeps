/* SPDX-License-Identifier: MIT */
/* SPDX-FileCopyrightText: 2026 japes98 */
/* Code in RAM, changed by the image's own stores between runs. A routine
   `r0 = 0x12345678; rts` (c0 ff 78 56 34 12, 80 00) is written to RAM
   and called three times a step (so fwtest has built and reused it), then
   a store changes its immediate, and so on. OUT(k) holds r0 after step k:
   0  as written                       0x12345678
   1  h[+2] = 0xBEEF (a halfword)      0x1234BEEF
   2  b[+5] = 0x77 (a byte)            0x7734BEEF
   3  [+4] = 0x00805566 (a word)       0x5566BEEF
   (fwtest models no instruction cache: this checks only that it runs RAM
   code as memory holds it.) Then main returns and start.S halts. */
	.text
	.globl main
main:
	[--sp] = rets
	r1 = 0x01C02000
	r6 = 0x01C00100
	r2 = 0x5678FFC0
	[r1+0] = r2
	r2 = 0x00801234
	[r1+4] = r2
	call run3
	[r6+0] = r0

	r2 = 0xBEEF
	h[r1+2] = r2
	call run3
	[r6+4] = r0

	r2 = 0x77
	b[r1+5] = r2
	call run3
	[r6+8] = r0

	r2 = 0x00805566
	[r1+4] = r2
	call run3
	[r6+12] = r0
	pc = [sp++]

	/* the routine at r1, three times; r0 its last result */
run3:
	[--sp] = rets
	r5 = 3
1:	r0 = 0
	call r1
	if (--r5 != 0) goto 1b
	pc = [sp++]
