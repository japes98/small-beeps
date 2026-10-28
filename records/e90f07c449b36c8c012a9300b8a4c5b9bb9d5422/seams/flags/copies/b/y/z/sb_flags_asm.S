/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * Assembly in the folder given flags (tools/seams_suite.py, case flags):
 * it gets --asflags and not --cflags.
 */

#ifndef SB_FLAGS_ASM
#error "built without its folder's flags (--asflags)"
#endif
#ifdef SB_FLAGS_OUTER
#error "the folder's C flags reached its assembly"
#endif

	.text
	.globl	sb_flags_asm
	.type	sb_flags_asm,@function
sb_flags_asm:
	rts
	.size	sb_flags_asm, .-sb_flags_asm
