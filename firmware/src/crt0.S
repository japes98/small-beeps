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

#if defined(SB_PROBE_RETURN) + defined(SB_PROBE_LIGHT) + defined(SB_PROBE_PANEL) > 1
#error "SB_PROBE_RETURN, SB_PROBE_LIGHT and SB_PROBE_PANEL are three probes: define one"
#endif

#if defined(SB_PROBE_LIGHT)
	.set	SB_PROBE_HOLD, 900000000	/* passes of the hold loop */

/* Shifts the 16-bit column word WORD into the key matrix's two shift
 * registers, most significant bit first, and latches it (HW-117): data
 * PA4, clock PA3, latch PA1, r0 holding JL_PORTA. Changes r1 to r3. */
	.macro	sb_probe_shift word
	r2 = \word
	r3 = 16
.Lbit\@:
	r1 = r2 & 0x8000
	if (r1 == 0) goto .Lzero\@
	[r0+0] |= 0x10
	goto .Lclock\@
.Lzero\@:
	[r0+0] &= 0xFFFFFFEF
.Lclock\@:
	csync
	[r0+0] |= 0x8
	csync
	[r0+0] &= 0xFFFFFFF7
	csync
	r2 = r2 << 1
	r3 += -1
	if (r3 != 0) goto .Lbit\@
	[r0+0] |= 0x2
	csync
	[r0+0] &= 0xFFFFFFFD
	csync
	.endm
#endif

	.section .text.entry,"ax",@progbits
	.globl	_start
	.type	_start,@function
_start:
#if defined(SB_PROBE_RETURN)
	/* Phase B's entry-return probe (BR-17; docs/DESIGN-NOTES.md,
	 * clean-br17-round2): return to the loader at once, before writing a
	 * register or a byte of RAM. On a unit, m-bootloader opens its
	 * recovery menu when the app it called returns (HW-112). */
	rts
#elif defined(SB_PROBE_LIGHT)
	/* Phase B's light probe (BR-17; docs/DESIGN-NOTES.md, clean-br17-light;
	 * R-PROBE-2): the backlight and PLAY's LED on for about 5 s, both off
	 * again, then a return to the loader, which opens its recovery menu
	 * with "APP EXITED" (HW-119). Ports A and H are HW-56's, the pins
	 * HW-116 to HW-118's. It uses r0 to r3 alone, which a called function
	 * may change (the pinned compiler saves r4 and up, never r0 to r3),
	 * no stack and no RAM, and it never calls, so rets still holds the
	 * loader's return address at the rts. Each pin is driven low before it
	 * becomes an output, and each edge is its own read-modify-write of OUT
	 * with csync after it (HW-117). */
	r0 = 0x00050000			/* JL_PORTA: OUT +0, DIR +8 */
	r1 = 0x000501C0			/* JL_PORTH */
	/* 1. The backlight: PA2 an output driven low (HW-116). */
	[r0+0] &= 0xFFFFFFFB
	[r0+8] &= 0xFFFFFFFB
	/* 2. The shift registers' latch, clock and data (PA1, PA3, PA4) and
	 * the LED lines PA9 and PA10, then PH6 and PH9, outputs driven low
	 * (HW-117, HW-118), one pin at a time. */
	[r0+0] &= 0xFFFFFFFD
	[r0+0] &= 0xFFFFFFF7
	[r0+0] &= 0xFFFFFFEF
	[r0+0] &= 0xFFFFFDFF
	[r0+0] &= 0xFFFFFBFF
	[r0+8] &= 0xFFFFFFFD
	[r0+8] &= 0xFFFFFFF7
	[r0+8] &= 0xFFFFFFEF
	[r0+8] &= 0xFFFFFDFF
	[r0+8] &= 0xFFFFFBFF
	[r1+0] &= 0xFFFFFFBF
	[r1+0] &= 0xFFFFFDFF
	[r1+8] &= 0xFFFFFFBF
	[r1+8] &= 0xFFFFFDFF
	csync
	sb_probe_shift 0xFBFF		/* PLAY's column (HW-117) */
	[r0+0] |= 0x400			/* PA10 high: PLAY's LED (HW-118) */
	csync
	/* 3. Hold: two instructions a pass, so 5 s at 360 MHz (HW-119) at one
	 * instruction a cycle, longer if a taken branch costs more. */
	r2 = SB_PROBE_HOLD
.Lhold:
	r2 += -1
	if (r2 != 0) goto .Lhold
	/* 4. Both out: PA10 low, no column selected, PA2 an input. */
	[r0+0] &= 0xFFFFFBFF
	csync
	sb_probe_shift 0xFFFF
	[r0+8] |= 0x4
	csync
	rts
#elif defined(SB_PROBE_PANEL)
	/* Phase B's panel probe (BR-17; docs/DESIGN-NOTES.md,
	 * clean-br17-panel; R-PROBE-3): sb_probe_panel (probe.c) in C, on a
	 * stack of our own at __stack_top, 0x01C7FC00: above m-bootloader's
	 * RAM (below 0x01C0A800) and below the retained area (from
	 * 0x01C7FD80), so the return keeps both (HW-119). The loader's sp is
	 * kept in r4, whose own value and rets are saved on our stack; ssp is
	 * never written, and interrupts stay off. */
	r1 = sp
	r2 = __stack_top
	sp = r2
	[--sp] = {rets, r4}
	r4 = r1
	call	sb_probe_panel
	r1 = r4
	{rets, r4} = [sp++]
	sp = r1
	rts
#endif
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

	/* Runs before the copy to RAM, so it stays in the window (app.ld). */
	.section .boot.text,"ax",@progbits
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

	.text

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
