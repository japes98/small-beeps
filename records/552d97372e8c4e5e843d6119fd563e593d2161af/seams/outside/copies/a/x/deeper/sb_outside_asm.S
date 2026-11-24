/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * Assembly in a folder below an outside source folder.
 */

	.text
	.globl	sb_outside_asm
	.type	sb_outside_asm,@function
sb_outside_asm:
	rts
	.size	sb_outside_asm, .-sb_outside_asm
