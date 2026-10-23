/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * Core 1's entry for the Plaits bench (bench.c, docs/DESIGN-NOTES.md,
 * M4b): core 1 starts here in supervisor mode with stack pointers it
 * must not rely on (HW-10), so it sets its own, on a stack of its own,
 * and runs plaits_core1_main, which never returns.
 */

#if defined(PLAITS_BENCH)

	.text
	.globl	plaits_core1_entry
	.type	plaits_core1_entry,@function
plaits_core1_entry:
	r1 = plaits_core1_stack_top
	sp = r1
	ssp = r1
	call	plaits_core1_main
	cli
.Lcore1_stop:
	goto	.Lcore1_stop
	.size	plaits_core1_entry, .-plaits_core1_entry

	.section .bss.plaits_core1_stack,"aw",@nobits
	.balign	8
plaits_core1_stack:
	.space	8192
plaits_core1_stack_top:

#endif
