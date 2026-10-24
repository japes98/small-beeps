/* SPDX-License-Identifier: MIT */
/* SPDX-FileCopyrightText: 2026 japes98 */
/* E-18: the block moves with a register base, every mode (SR-7), as the
   pinned toolchain assembles them. SRC (0x01C01000) holds 0xA5000000 + i in
   word i (32 words); DST (0x01C01200, 64 words) is cleared. Each case keeps
   the registers it loaded and its base in OUT(k), as listed; the stores
   show in DST. Then main returns and start.S halts.
   A  {r3, r1, r0} = [r6+]          r6 = SRC + 0x10   OUT 0-3: r0 r1 r3 r6
   B  {r2, r1} = [r7++]             r7 = SRC + 0x20   OUT 4-6: r1 r2 r7
   C  {r3, r0} = [-r4]              r4 = SRC + 0x10   OUT 7-9: r0 r3 r4
   D  {r3, r0} = [-r0]              r0 = SRC + 0x10   OUT 10-11: r0 r3
   E  {r12, r11, r10} = [--r9]      r9 = SRC + 0x40   OUT 12-15: r10 r11 r12 r9
   F  [-r8] = {r5, r2}              r8 = DST + 0x10   OUT 16: r8
   G  [--r13] = {r15, r14, r0}      r13 = DST + 0x30  OUT 17: r13
   H  [r10+] = {r6, r3}             r10 = DST + 0x40  OUT 18: r10
   I  [r11++] = {r4, r2, r1}        r11 = DST + 0x50  OUT 19: r11
   J  [-r5] = {r5, r1}              r5 = DST + 0x70   OUT 20: r5
   K  {r14-r0} = [-r15]             r15 = SRC + 0x7C, then
      [r15+] = {r14-r0}             r15 = DST + 0x80 */
	.text
	.globl main
main:
	r1 = 0x01C01000
	r2 = 0xA5000000
	r3 = 32
1:	[r1++=4] = r2
	r2 += 1
	if (--r3 != 0) goto 1b
	r1 = 0x01C01200
	r2 = 0
	r3 = 64
2:	[r1++=4] = r2
	if (--r3 != 0) goto 2b

	r6 = 0x01C01010
	{r3, r1, r0} = [r6+]
	r5 = 0x01C00100
	[r5+0] = r0
	[r5+4] = r1
	[r5+8] = r3
	[r5+12] = r6

	r7 = 0x01C01020
	{r2, r1} = [r7++]
	[r5+16] = r1
	[r5+20] = r2
	[r5+24] = r7

	r4 = 0x01C01010
	{r3, r0} = [-r4]
	[r5+28] = r0
	[r5+32] = r3
	[r5+36] = r4

	r0 = 0x01C01010
	{r3, r0} = [-r0]
	[r5+40] = r0
	[r5+44] = r3

	r9 = 0x01C01040
	{r12, r11, r10} = [--r9]
	[r5+48] = r10
	[r5+52] = r11
	[r5+56] = r12
	[r5+60] = r9

	r8 = 0x01C01210
	r2 = 0xB2
	r5 = 0xB5
	[-r8] = {r5, r2}
	r5 = 0x01C00100
	[r5+64] = r8

	r13 = 0x01C01230
	r0 = 0xC0
	r14 = 0xCE
	r15 = 0xCF
	[--r13] = {r15, r14, r0}
	[r5+68] = r13

	r10 = 0x01C01240
	r3 = 0xD3
	r6 = 0xD6
	[r10+] = {r6, r3}
	[r5+72] = r10

	r11 = 0x01C01250
	r1 = 0xE1
	r2 = 0xE2
	r4 = 0xE4
	[r11++] = {r4, r2, r1}
	[r5+76] = r11

	r5 = 0x01C01270
	r1 = 0xF1
	[-r5] = {r5, r1}
	r0 = 0x01C00100
	[r0+80] = r5

	r15 = 0x01C0107C
	{r14-r0} = [-r15]
	r15 = 0x01C01280
	[r15+] = {r14-r0}
	rts
