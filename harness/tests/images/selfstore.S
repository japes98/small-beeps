/* SPDX-License-Identifier: MIT */
/* SPDX-FileCopyrightText: 2026 japes98 */
/* SR-10: stores with a base update whose stored register is the base
   itself, every form the vendor assembler takes (pre- and post-increment,
   word, halfword and byte, an immediate or a register step, the 2-byte
   short forms). The vendor compiler emits them for C that stores the base
   as it was (`q = p + 187; *q = p;` gives `[++r0=748] = r0`, and never for
   C that stores the moved base), so the value stored is the base before
   the instruction. Case k uses the 8 bytes at A = 0x01C00100 + 8k: the
   store's address is A, the word at A gets the value stored (a halfword or
   byte one in its low bytes) and the word at A + 4 the base after the
   instruction. (fwtest 0.8.0 stored the moved base in the pre-increment
   cases.) Then main returns and start.S halts. The expected values are
   in tests/fwtest.rs (stores_of_the_base_keep_its_old_value). */
	.text
	.globl main
main:
	r7 = 0x01C00100
	r0 = 0
	r1 = 0x01C00100
	r2 = 0x01C00100 + 120
1:	[r1+0] = r0
	r1 += 4
	if (r1 != r2) goto 1b

	/* 0: [++r4=748] = r4 */
	r4 = 0x01BFFE14
	[++r4=748] = r4
	[r7+4] = r4
	/* 1: [++r1=8] = r1 */
	r1 = 0x01C00100
	[++r1=8] = r1
	[r7+12] = r1
	/* 2: [++r1=-8] = r1 */
	r1 = 0x01C00118
	[++r1=-8] = r1
	[r7+20] = r1
	/* 3: [r1++=8] = r1 */
	r1 = 0x01C00118
	[r1++=8] = r1
	[r7+28] = r1
	/* 4: [r4++=-4] = r4 */
	r4 = 0x01C00120
	[r4++=-4] = r4
	[r7+36] = r4
	/* 5: [r1++=4] = r1 */
	r1 = 0x01C00128
	[r1++=4] = r1
	[r7+44] = r1
	/* 6: [++r1=r2] = r1 */
	r2 = 8
	r1 = 0x01C00128
	[++r1=r2] = r1
	[r7+52] = r1
	/* 7: [r1++=r2] = r1 */
	r2 = 8
	r1 = 0x01C00138
	[r1++=r2] = r1
	[r7+60] = r1
	/* 8: h[++r2=8] = r2 */
	r2 = 0x01C00138
	h[++r2=8] = r2
	[r7+68] = r2
	/* 9: h[++r1=-8] = r1 */
	r1 = 0x01C00150
	h[++r1=-8] = r1
	[r7+76] = r1
	/* 10: h[r5++=2] = r5 */
	r5 = 0x01C00150
	h[r5++=2] = r5
	[r7+84] = r5
	/* 11: h[++r1=r2] = r1 */
	r2 = 8
	r1 = 0x01C00150
	h[++r1=r2] = r1
	[r7+92] = r1
	/* 12: b[++r3=8] = r3 */
	r3 = 0x01C00158
	b[++r3=8] = r3
	[r7+100] = r3
	/* 13: b[r6++=1] = r6 */
	r6 = 0x01C00168
	b[r6++=1] = r6
	[r7+108] = r6
	/* 14: b[r1++=r2] = r1 */
	r2 = 8
	r1 = 0x01C00170
	b[r1++=r2] = r1
	[r7+116] = r1
	rts
