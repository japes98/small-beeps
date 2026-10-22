/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * The image's first instruction. Core 0 starts here with every register
 * but r0 at zero and no usable stack (HW-1, HW-2), so this sets the stack
 * pointer and hands over to C. Also sb_stack_fill, which C can't write:
 * it needs the stack pointer.
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

/* Fills the unused stack, from its limit up to the current sp, with
 * SB_STACK_FILL, so a test can see how deep the stack ever went: the
 * lowest word no longer holding the pattern (tools/perf.py, R-PERF-3).
 * main calls it once, after starting the time base, so it costs none of
 * the heartbeat's start tolerance (R-BOOT-3). A leaf: a call keeps its
 * return address in rets, so nothing below sp is in use. */
	.set	SB_STACK_FILL, 0x4B415453	/* "STAK" in memory order */

	.text
	.globl	sb_stack_fill
	.type	sb_stack_fill,@function
sb_stack_fill:
	r0 = __stack_limit
	r1 = sp + 0
	r2 = SB_STACK_FILL
	if (r0 >= r1) goto .Lfilled
.Lfill:
	[r0++=4] = r2
	if (r0 < r1) goto .Lfill
.Lfilled:
	rts
	.size	sb_stack_fill, .-sb_stack_fill
