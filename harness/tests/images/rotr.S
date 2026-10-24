/* SPDX-License-Identifier: MIT */
/* SPDX-FileCopyrightText: 2026 japes98 */
/* The rotate right by a register, `rD = rS <> rT` (cc e1), across
   registers and amounts, its dual-issue pair head (cc f1), and the rotate
   by a constant beside it. Each result goes to the next OUT word, in this
   order:
   0  r0 = r0 <> r1      r0 = 0x12345678, r1 = 8
   1  r5 = r9 <> r2      r9 = 0x80000001, r2 = 1
   2  r15 = r3 <> r14    r3 = 0x12345678, r14 = 31
   3  r4 = r4 <> r4      r4 = 0x00000013 (by itself, 19)
   4  r8 = r10 <> r11    r10 = 0xDEADBEEF, r11 = 0
   5  r8 = r10 <> r11    r11 = 32
   6  r8 = r10 <> r11    r11 = 33
   7  r8 = r10 <> r11    r11 = 0xFFFFFFE1
   8  r0 = r0 <> 7       r0 = 0x12345678 (the constant form)
   9  r6 = r5 <> r3 #    r6 = 0x0BADF00D, r5 = 0x12345678, r3 = 4: the
      pair's second half stores r6, then r6 again after the pair (10)
   Then main returns and start.S halts. */
	.text
	.globl main
main:
	r7 = 0x01C00100

	r0 = 0x12345678
	r1 = 8
	r0 = r0 <> r1
	[r7+0] = r0

	r9 = 0x80000001
	r2 = 1
	r5 = r9 <> r2
	[r7+4] = r5

	r3 = 0x12345678
	r14 = 31
	r15 = r3 <> r14
	[r7+8] = r15

	r4 = 0x13
	r4 = r4 <> r4
	[r7+12] = r4

	r10 = 0xDEADBEEF
	r11 = 0
	r8 = r10 <> r11
	[r7+16] = r8
	r11 = 32
	r8 = r10 <> r11
	[r7+20] = r8
	r11 = 33
	r8 = r10 <> r11
	[r7+24] = r8
	r11 = 0xFFFFFFE1
	r8 = r10 <> r11
	[r7+28] = r8

	r0 = 0x12345678
	r0 = r0 <> 7
	[r7+32] = r0

	r6 = 0x0BADF00D
	r5 = 0x12345678
	r3 = 4
	r6 = r5 <> r3 #
	[r7+36] = r6
	[r7+40] = r6
	rts
