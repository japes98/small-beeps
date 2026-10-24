/* SPDX-License-Identifier: MIT */
/* SPDX-FileCopyrightText: 2026 japes98 */
/* Dual-issue pair heads among the 4-byte ALU forms: one word of each
   family, as itself (byte 1 e0 / e1) and as a pair's head (f0 / f1, which
   the vendor objdump prints with a trailing `#`). The heads are given as
   bytes, since the assembler picks a 2-byte form for some of them; the
   objdump text of each is beside it. Case k keeps three words at
   OUT(3k): the plain form's result; the destination as the pair's second
   half stores it (the value before the pair); and as stored after the
   pair (the head's result). r5 = 0x92345678 and r3 = 5 before each; the
   destination starts at 0x0BADF00D. Then main returns and start.S halts. */
	.text
	.globl main

	.macro case b0, b1, b2, b3, d
	r5 = 0x92345678
	r3 = 5
	\d = 0x0BADF00D
	.byte \b0, \b1, \b2, \b3
	[r7+0] = \d
	r3 = 5
	\d = 0x0BADF00D
	.byte \b0, \b1 | 0x10, \b2, \b3
	[r7+4] = \d
	[r7+8] = \d
	r7 += 12
	.endm

main:
	r7 = 0x01C00100
	case 0xb4, 0xe0, 0x50, 0x63, r6	/*  0  r6 = r5 + r3 */
	case 0xb4, 0xe0, 0x52, 0x63, r6	/*  1  r6 = r5 - r3 */
	case 0x90, 0xe1, 0x50, 0x63, r6	/*  2  r6 = r5 | r3 */
	case 0x90, 0xe1, 0x51, 0x63, r6	/*  3  r6 = r5 ^ r3 */
	case 0x90, 0xe1, 0x52, 0x63, r6	/*  4  r6 = r5 & r3 */
	case 0x94, 0xe1, 0x50, 0x63, r6	/*  5  r6 = r5 | (1 << r3) */
	case 0x94, 0xe1, 0x51, 0x63, r6	/*  6  r6 = r5 ^ (1 << r3) */
	case 0x94, 0xe1, 0x52, 0x63, r6	/*  7  r6 = r5 & (1 << r3) */
	case 0x94, 0xe1, 0x53, 0x63, r6	/*  8  r6 = r5 & ~(1 << r3) */
	case 0xc8, 0xe1, 0x50, 0x63, r6	/*  9  r6 = r5 << r3 */
	case 0xc8, 0xe1, 0x52, 0x63, r6	/* 10  r6 = r5 >> r3 */
	case 0xc8, 0xe1, 0x53, 0x63, r6	/* 11  r6 = r5 >>> r3 */
	case 0xf0, 0xe1, 0x50, 0x63, r6	/* 12  r6 = r5 * r3 */
	case 0xe3, 0xe0, 0x34, 0x52, r3	/* 13  r3 = r5 + 0x34003400 */
	case 0xf3, 0xe0, 0x34, 0x52, r3	/* 14  r3 = r5 - 0x34003400 */
	case 0xa3, 0xe0, 0x34, 0x52, r3	/* 15  r3 = 0x34003400 - r5 */
	case 0x03, 0xe1, 0x34, 0x52, r3	/* 16  r3 = r5 + 564 */
	case 0x13, 0xe1, 0x34, 0x52, r3	/* 17  r3 = r5 + 4660 */
	case 0x23, 0xe1, 0x34, 0x52, r3	/* 18  r3 = r5 + -7628 */
	case 0x33, 0xe1, 0x34, 0x52, r3	/* 19  r3 = r5 + -3532 */
	case 0x43, 0xe1, 0x34, 0x52, r3	/* 20  r3 = r5 | 0x34003400 */
	case 0x53, 0xe1, 0x34, 0x52, r3	/* 21  r3 = r5 ^ 0x34003400 */
	case 0x63, 0xe1, 0x34, 0x52, r3	/* 22  r3 = r5 & 0x34003400 */
	case 0x73, 0xe1, 0x34, 0x52, r3	/* 23  r3 = r5 & 0xCBFFCBFF */
	case 0xe3, 0xe1, 0x34, 0x52, r3	/* 24  r3 = r5 * 0x34003400 */
	rts
