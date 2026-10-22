/* SPDX-License-Identifier: MIT */
/* SPDX-FileCopyrightText: 2026 japes98 */

/* Startup for the harness's own test images: both stacks below the vector */
/* table, then main(); when main returns, a halt (interrupts off, a jump to */
/* itself), which fwtest reports as `halt`. */
	.section .text.start, "ax"
	.globl _start
_start:
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
