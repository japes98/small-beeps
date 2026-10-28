/* SPDX-License-Identifier: MIT */
/* SPDX-FileCopyrightText: 2026 japes98 */
/* The toolchain audit (session spec-isa-audit): more forms only the
   assembler emits (-mcpu=r3 -mfprev1) that fwtest 0.9.0 could not run:
     rD.l|h = rS.l|h                 a half moved, the other half kept
     rD.l|h = sat8(rS.l|h) (s|u)     a half clamped to 8 bits
     u/sextra, insert with the field in a register (p:rP[12:8], l:rP[4:0])
     [rB+k] <<<= rS, <<<= n           the saturating shift, in memory
     h[rB+rI<<1] = rS.h              the high half stored
     rN = retx, sr4 = rN, sspn = rN  special registers fwtest models
     [--sp] = {sspn, sr4, retx, rete} and back, the 4-byte mask forms
   OUT(k) get the results; tests/fwtest.rs (registers_halves_and_fields)
   has the values. */
	.text
	.globl main
main:
	r7 = 0x01C00100
	/* 0..1: half moves */
	r1 = 0x11111111
	r3 = 0xABCD0000
	r1.l = r3.h
	[r7+0] = r1
	r2 = 0x22222222
	r4 = 0x99990004
	r2.h = r4.l
	[r7+4] = r2
	/* 2..3: sat8 of 0xff00 (-256) signed, of 0xfff0 (-16) unsigned */
	r3 = 0xABCD0000
	r5 = 0x0000FF00
	r3.l = sat8(r5.l) (s)
	[r7+8] = r3
	r4 = 0x99990004
	r6 = 0xFFF00000
	r4.h = sat8(r6.h) (u)
	[r7+12] = r4
	/* 4..6: fields at p 4, l 8 */
	r11 = 0x408
	r2 = 0x00000F80
	r1 = uextra(r2, p:r11[12:8], l:r11[4:0])
	[r7+16] = r1
	r3 = sextra(r2, p:r11[12:8], l:r11[4:0])
	[r7+20] = r3
	r4 = -1
	r5 = 0x12
	r4 <= insert(r5, p:r11[12:8], l:r11[4:0])
	[r7+24] = r4
	/* 7..8: [r1+4] <<<= r3 (1) of 0x40000000, [r2+0] <<<= 32 of 0xfffffff0 */
	r1 = 0x01C00400
	r0 = 0x40000000
	[r1+4] = r0
	r3 = 1
	[r1+4] <<<= r3
	r0 = [r1+4]
	[r7+28] = r0
	r2 = 0x01C00410
	r0 = 0xFFFFFFF0
	[r2+0] = r0
	[r2+0] <<<= 32
	r0 = [r2+0]
	[r7+32] = r0
	/* 9: h[r0+r5<<1] = r4.h at 0x01C00420 + 16 */
	r0 = 0x01C00420
	r5 = 8
	r4 = 0xBEEF0000
	r6 = 0
	[r0+16] = r6
	h[r0+r5<<1] = r4.h
	r6 = [r0+16]
	[r7+36] = r6
	/* 10..12: special registers */
	r12 = 0x1234
	r13 = 0x5678
	sr4 = r12
	r11 = sr4
	[r7+40] = r11
	sspn = r13
	r11 = sspn
	[r7+44] = r11
	r12 = 0xAA
	retx = r12
	r11 = retx
	[r7+48] = r11
	/* 13..15: push {sspn, sr4, retx, rete}, change them, pop: the old values back */
	r12 = 0xBB
	rete = r12
	r5 = sp
	[--sp] = {sspn, sr4, retx, rete}
	r6 = sp
	r6 = r5 - r6
	[r7+52] = r6
	r12 = 0
	sr4 = r12
	retx = r12
	rete = r12
	{sspn, sr4, retx, rete} = [sp++]
	r11 = sr4
	[r7+56] = r11
	r11 = rete
	[r7+60] = r11
	rts
