/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * The image's first instruction. Core 0 starts here with every register
 * but r0 at zero and no usable stack (HW-1, HW-2), so this sets the stack
 * pointer and hands over to C. Nothing else needs assembly yet.
 */

	.section .text.entry,"ax",@progbits
	.globl	_start
	.type	_start,@function
_start:
	/* r0 holds the loader's block pointer (HW-4); M0d doesn't use it. */
	r1 = __stack_top
	sp = r1
	call	sb_start

	/* sb_start never returns. If it ever did, stop on purpose: interrupts
	 * off and a jump to itself, which fwtest reports as a halt. */
	cli
.Lstop:
	goto	.Lstop
	.size	_start, .-_start
