/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * Core 1 in the FM-1 hardware build (SB_HW_FM1, start3 (d); R-HW-1):
 * released as HW-135 says (hw_start3.c), it sets hw_core1_flag, then runs
 * this loop from RAM (the copied .text), adding one to hw_core1_count for
 * ever. Interrupts off
 * first, so it never takes the vector table core 0 shares (HW-18). It
 * uses r0 and r1 alone, and no stack: its stack pointers are whatever it
 * starts with (HW-10 is fwtest's).
 */

#if defined(SB_HW_FM1) && defined(SB_HW_TEST)
	.text
	.globl	hw_core1_loop
	.type	hw_core1_loop,@function
hw_core1_loop:
	cli
	/* Its own sign first (start3c, HW-135 step 4): core 0 waits for it. */
	/* audio3: the flag and the count in their own 64-byte block,
	 * hw_core1_blk (hw_fm1.h), the flag first. */
	r0 = hw_core1_blk
	r1 = 1
	[r0+0] = r1
	r0 += 4
.Lcount:
	r1 = [r0+0]
	r1 += 1
	[r0+0] = r1
	goto	.Lcount
	.size	hw_core1_loop, .-hw_core1_loop
#endif
