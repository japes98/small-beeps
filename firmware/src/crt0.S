/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * The image's first instruction. Core 0 starts here with every register
 * but r0 at zero and no usable stack (HW-1, HW-2), so this sets the stack
 * pointers and hands over to C. Also what C can't write: sb_stack_fill
 * (it needs the stack pointer), sb_clock_measure (it needs an exact
 * instruction count), and the interrupt stubs (they need the address they
 * were called from).
 */

	.section .text.entry,"ax",@progbits
	.globl	_start
	.type	_start,@function
_start:
	/* r0 holds the loader's block pointer (HW-4); M1 doesn't use it. */
	r1 = __stack_top
	sp = r1
	/* Core 0 runs in user mode, and an interrupt switches to ssp (HW-3,
	 * confirmed by our own run: docs/DESIGN-NOTES.md, M1), so ssp must
	 * be valid before interrupts are enabled. */
	r1 = __irq_stack_top
	ssp = r1
	/* Before any C, so every use of either stack shows (R-PERF-3). */
	call	sb_stack_fill
	call	sb_start

	/* sb_start never returns. If it ever did, stop on purpose: interrupts
	 * off and a jump to itself, which fwtest reports as a halt. */
	cli
.Lstop:
	goto	.Lstop
	.size	_start, .-_start

/* Fills the unused stack area, from its limit up to the current sp, with
 * SB_STACK_FILL, so a test can see how deep each stack ever went: the
 * lowest word no longer holding the pattern (tools/perf.py, R-PERF-3).
 * The area holds both stacks, so this fills the interrupt stack whole,
 * and the lowest word of each stack is left holding the pattern as its
 * guard (sb_tick checks both). _start calls it before anything else,
 * so nothing has used either stack yet. A leaf: a call keeps its return
 * address in rets, so nothing below sp is in use. */
	.set	SB_STACK_FILL, 0x4B415453	/* "STAK"; also in sb.h */

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

/* Measures the core clock against the 24 MHz time base (HW-13): reads
 * TIMER4's count (its address in r0, from C), runs exactly
 * SB_CLOCK_CYCLES instructions, reads it again and returns the difference. fwtest runs one instruction a cycle
 * (HW-11), so at 240 MHz the result is SB_CLOCK_CYCLES / 10, give or take
 * one for where in a count the reads fall. The two reads are far apart,
 * so fwtest never treats this as waiting (docs/HARNESS.md, "Time"). */
	.set	SB_CLOCK_LOOPS, 1200		/* 2 instructions each */

	.globl	sb_clock_measure
	.type	sb_clock_measure,@function
sb_clock_measure:
	r2 = [r0+0]
	r3 = SB_CLOCK_LOOPS
.Lspin:
	r3 += -1
	if (r3 != 0) goto .Lspin
	r1 = [r0+0]
	r0 = r1 - r2
	rts
	.size	sb_clock_measure, .-sb_clock_measure

/* One stub per interrupt source, 2 bytes each (the short form of call,
 * which reaches sb_irq_stub_common from every stub; app.ld asserts the
 * size), in source order: every
 * slot of the vector table that has no handler of its own points at its
 * source's stub (firmware/src/irq.c). A stub calls sb_irq_stub_common,
 * which works out the source from the stub's address (the return address
 * in rets) and halts with a report. Nothing returns, so clobbering rets
 * and the scratch registers is fine. */
	.p2align 1
	.globl	sb_irq_stubs, sb_irq_stubs_end
	.type	sb_irq_stubs,@function
sb_irq_stubs:
	.rept	128
	call	sb_irq_stub_common
	.endr
sb_irq_stubs_end:
	.size	sb_irq_stubs, .-sb_irq_stubs

	.type	sb_irq_stub_common,@function
sb_irq_stub_common:
	cli
	r0 = rets
	r1 = sb_irq_stubs + 2
	r0 = r0 - r1
	r0 >>= 1				/* the source number */
	r1 = reti				/* where the interrupt came in */
	call	sb_irq_unexpected
.Lnever:
	goto	.Lnever
	.size	sb_irq_stub_common, .-sb_irq_stub_common
