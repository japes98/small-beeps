/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * Core 1's entry (since clean-1027, BR-3, the platform's; core1.h): core
 * 1 starts here in supervisor mode with stack pointers it must not rely
 * on (HW-10), so it takes the stack sb_core1_start left in sb_core1_sp,
 * and runs sb_core1_main (core1.c), which runs the engine's entry. If
 * that returns, core 1 stops here. It takes no interrupt: no source is
 * enabled on it (HW-64).
 */

	.text
	.globl	sb_core1_entry
	.type	sb_core1_entry,@function
sb_core1_entry:
	r1 = sb_core1_sp
	r1 = [r1+0]
	sp = r1
	ssp = r1
	call	sb_core1_main
	cli
.Lcore1_stop:
	goto	.Lcore1_stop
	.size	sb_core1_entry, .-sb_core1_entry
