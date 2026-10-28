/* SPDX-License-Identifier: MIT */
/* SPDX-FileCopyrightText: 2026 japes98 */
/* The toolchain audit (session spec-isa-audit): forms the pinned
   assembler takes with the firmware's CPU flags (-mcpu=r3 -mfprev1) that
   fwtest 0.9.0 could not run, or ran wrongly, and the compiler never
   emits:
     r = ftoi(r) / ftou(r) rounding to even, up and down; r = ftof(r) (even)
     fcmp rA, rB and the ten flag branches ifeq .. ifle after it
     testset, then ifne forward (0.9.0 took `41 e8`, no instruction, for it)
     [r+k] <<= 32 and >>>= 32 (0.9.0 shifted by 0)
   OUT(k) get the results; tests/fwtest.rs (forms_only_the_assembler_emits)
   has the values. */
	.text
	.globl main
main:
	r7 = 0x01C00100
	/* 0..6: conversions of 2.5 (0x40200000) and -2.5 (0xC0200000) */
	r2 = 0x40200000
	r3 = 0xC0200000
	r1 = ftoi(r2) (even)
	[r7+0] = r1
	r1 = ftoi(r3) (ceil)
	[r7+4] = r1
	r1 = ftoi(r3) (floor)
	[r7+8] = r1
	r1 = ftou(r2) (even)
	[r7+12] = r1
	r1 = ftou(r2) (ceil)
	[r7+16] = r1
	r1 = ftou(r2) (floor)
	[r7+20] = r1
	r1 = ftof(r3) (even)
	[r7+24] = r1

	/* 7..16: fcmp 1.0, 2.0, then each flag branch: 1 taken, 0 not */
	r2 = 0x3F800000
	r3 = 0x40000000
	r0 = 0
	r6 = 1
	fcmp r2, r3
	ifeq goto 1f
	goto 2f
1:	r0 = 1
2:	[r7+28] = r0
	r0 = 0
	ifne goto 1f
	goto 2f
1:	r0 = 1
2:	[r7+32] = r0
	r0 = 0
	ifcs goto 1f
	goto 2f
1:	r0 = 1
2:	[r7+36] = r0
	r0 = 0
	ifcc goto 1f
	goto 2f
1:	r0 = 1
2:	[r7+40] = r0
	r0 = 0
	ifhi goto 1f
	goto 2f
1:	r0 = 1
2:	[r7+44] = r0
	r0 = 0
	ifls goto 1f
	goto 2f
1:	r0 = 1
2:	[r7+48] = r0
	r0 = 0
	ifge goto 1f
	goto 2f
1:	r0 = 1
2:	[r7+52] = r0
	r0 = 0
	iflt goto 1f
	goto 2f
1:	r0 = 1
2:	[r7+56] = r0
	r0 = 0
	ifgt goto 1f
	goto 2f
1:	r0 = 1
2:	[r7+60] = r0
	r0 = 0
	ifle goto 1f
	goto 2f
1:	r0 = 1
2:	[r7+64] = r0

	/* 17: testset of a free byte, then ifne forward: taken */
	r4 = 0x01C00400
	r0 = 0
	b[r4+0] = r0
	testset b[r4]
	ifne goto 1f
	goto 2f
1:	r0 = 1
2:	[r7+68] = r0

	/* 18, 19: [r4+0] <<= 32 of 0x12345678, [r4+4] >>>= 32 of 0x80000001 */
	r0 = 0x12345678
	[r4+0] = r0
	r0 = 0x80000001
	[r4+4] = r0
	[r4+0] <<= 32
	[r4+4] >>>= 32
	r0 = [r4+0]
	[r7+72] = r0
	r0 = [r4+4]
	[r7+76] = r0
	rts
