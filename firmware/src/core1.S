/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * Core 1's entry (M5): core 1 starts here in supervisor mode with stack
 * pointers it must not rely on (HW-10), so it sets its own, on a stack of
 * its own, and runs the FM engine's loop (fm_play.c), which never
 * returns. It takes no interrupt: no source is enabled on it (HW-64).
 */

	.text
	.globl	fm_core1_entry
	.type	fm_core1_entry,@function
fm_core1_entry:
	r1 = fm_core1_stack_top
	sp = r1
	ssp = r1
	call	fm_core1_main
	cli
.Lcore1_stop:
	goto	.Lcore1_stop
	.size	fm_core1_entry, .-fm_core1_entry

	.section .bss.fm_core1_stack,"aw",@nobits
	.balign	8
	.globl	fm_core1_stack
fm_core1_stack:
	.space	1024
fm_core1_stack_top:
