/* SPDX-License-Identifier: MIT */
/* SPDX-FileCopyrightText: 2026 japes98 */
/* Dual-issue pairs whose two halves write the same register, as the
   vendor compiler emits them (the four seen in its code, flashkeep.c and
   E-22 at -O2, each a word load of an SPI0 BUF read whose result is unused
   paired after a head computing a value used next): the head's result is
   the one there after the pair. The heads are given as bytes; the objdump
   text of each is beside it. The load reads 0xDEADBEEF from 0x01C01008.
   OUT(k) gets the register after pair k:
   0  r7 = r6 + 0x80000 #, r7 = [r1+8]      r6 = 0x300: 0x00080300
   1  r0 = r1.b0 (u) #, r0 = [r3+8]           r1 = 0x12345678: 0x78
   2  r0 = uextra(r1, p:8, l:8) #, r0 = [r3+8]   0x56
   3  r0 = uextra(r1, p:16, l:8) #, r0 = [r3+8]  0x34
   (fwtest 0.5.0 left 0xDEADBEEF, the second half's value, in each.)
   Then main returns and start.S halts. */
	.text
	.globl main
main:
	r4 = 0x01C00100
	r3 = 0x01C01000
	r2 = 0xDEADBEEF
	[r3+8] = r2

	r1 = 0x01C01000
	r6 = 0x300
	r7 = 0
	.byte 0xe7, 0xf0, 0x00, 0x6a	/* r7 = r6 + 0x80000 # */
	r7 = [r1+8]
	[r4+0] = r7

	r1 = 0x12345678
	r0 = 0
	.byte 0x10, 0xd7		/* r0 = r1.b0 (u) # */
	r0 = [r3+8]
	[r4+4] = r0

	r0 = 0
	.byte 0xb0, 0xf1, 0x20, 0x14	/* r0 = uextra(r1, p:8, l:8) # */
	r0 = [r3+8]
	[r4+8] = r0

	r0 = 0
	.byte 0xb0, 0xf1, 0x20, 0x18	/* r0 = uextra(r1, p:16, l:8) # */
	r0 = [r3+8]
	[r4+12] = r0
	rts
