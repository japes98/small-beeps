/* SPDX-License-Identifier: MIT */
/* SPDX-FileCopyrightText: 2026 japes98 */

/* E-1's startup: before anything else, saves the registers as fwtest */
/* starts the image (r0, r2..r15, sp, usp, ssp, icfg, psr, cnum) at */
/* OUT(0), OUT(2..15), OUT(16..21); r1 is used as the pointer. Then the */
/* usual stacks and main(). */
	.section .text.start, "ax"
	.globl _start
_start:
	r1 = 0x01c00100
	[r1 + 0] = r0
	[r1 + 8] = r2
	[r1 + 12] = r3
	[r1 + 16] = r4
	[r1 + 20] = r5
	[r1 + 24] = r6
	[r1 + 28] = r7
	[r1 + 32] = r8
	[r1 + 36] = r9
	[r1 + 40] = r10
	[r1 + 44] = r11
	[r1 + 48] = r12
	[r1 + 52] = r13
	[r1 + 56] = r14
	[r1 + 60] = r15
	r2 = sp
	[r1 + 64] = r2
	r2 = usp
	[r1 + 68] = r2
	r2 = ssp
	[r1 + 72] = r2
	r2 = icfg
	[r1 + 76] = r2
	r2 = psr
	[r1 + 80] = r2
	r2 = cnum
	[r1 + 84] = r2
	r0 = 0x01c7e000
	ssp = r0
	r0 = 0x01c7d000
	sp = r0
	usp = r0
	call main
	.globl halt
halt:
	cli
1:	goto 1b
