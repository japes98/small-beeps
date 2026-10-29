/* SPDX-License-Identifier: MIT */
/* SPDX-FileCopyrightText: 2026 japes98 */
/* The toolchain audit (session spec-isa-audit): forms only the assembler
   emits (-mcpu=r3 -mfprev1) whose syntax is explicit but a detail of
   whose result the toolchain leaves open (HARDWARE-SPEC Q-31 to Q-33);
   fwtest 0.9.0 could not run them:
     rD = rH_rL >> n | >>> n (up | round | even | zero)  the pair rounded
     rH_rL (=|+=|-=) [rA ++= i]*rB and the other memory multiplies
     rD = [npc + rI], rD = [npc + #i]
     rD = rev16(rS)
   OUT(k) get the results; tests/fwtest.rs (forms_with_an_open_detail) has
   the values. */
	.text
	.globl main
main:
	r7 = 0x01C00100
	/* 0..7: 320 / 128 = 2.5 and -192 / 128 = -1.5 in the four modes */
	r2 = 320
	r3 = 0
	r5 = r3_r2 >> 7 (up)
	[r7+0] = r5
	r5 = r3_r2 >> 7 (round)
	[r7+4] = r5
	r5 = r3_r2 >> 7 (even)
	[r7+8] = r5
	r5 = r3_r2 >> 7 (zero)
	[r7+12] = r5
	r2 = -192
	r3 = -1
	r11 = 7
	r5 = r3_r2 >>> r11 (up)
	[r7+16] = r5
	r5 = r3_r2 >>> r11 (round)
	[r7+20] = r5
	r5 = r3_r2 >>> r11 (even)
	[r7+24] = r5
	r5 = r3_r2 >>> r11 (zero)
	[r7+28] = r5
	/* 8..11: [r6] = -3, [r6+4] = 0x0000ffff; r5_r4 = [r6 ++= 4]*r9 (s), r9 = 5,
	   then += h[r6 ++= 4]*r9 (u): -15 + 65535 * 5; r6 at the end */
	r6 = 0x01C00400
	r0 = -3
	[r6+0] = r0
	r0 = 0xFFFF
	[r6+4] = r0
	r9 = 5
	r5_r4 = [r6 ++= 4]*r9 (s)
	[r7+32] = r4
	[r7+36] = r5
	r5_r4 += h[r6 ++= 4]*r9 (u)
	[r7+40] = r4
	[r7+44] = r6
	/* 12..13: r9_r8 = [r3 ++= 4]*[r11 ++= 8] (s) of 7 and -2 */
	r3 = 0x01C00410
	r11 = 0x01C00420
	r0 = 7
	[r3+0] = r0
	r0 = -2
	[r11+0] = r0
	r9_r8 = [r3 ++= 4]*[r11 ++= 8] (s)
	[r7+48] = r8
	[r7+52] = r9
	/* 14..15: r1 = [npc + r2] and r12 = [npc + 2], r2 = 2: each the word
	   after the 2-byte goto that follows */
	r2 = 2
	r1 = [npc + r2]
	goto 3f
	.long 0x600DF00D
3:	[r7+56] = r1
	r12 = [npc + 2]
	goto 4f
	.long 0x5A5AA5A5
4:	[r7+60] = r12
	/* 16: rev16 */
	r9 = 0x12345678
	r3 = rev16(r9)
	[r7+64] = r3
	rts
