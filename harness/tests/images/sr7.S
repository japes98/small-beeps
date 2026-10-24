/* SPDX-License-Identifier: MIT */
/* SPDX-FileCopyrightText: 2026 japes98 */
/* SR-7's minimal reproduction, as the request gives it (docs/SPEC-REQUESTS.md),
   linked on its own at the image window's start. Two words below r4, then
   {r3, r0} = [-r4]; r0, r3 and r4 are kept at 0x01C00020, then a halt. */
	.section .text.start, "ax"
	.globl _start
_start:
	r4 = 0x01C00010
	r1 = 0x29F3A1C5
	[r4+-8] = r1
	r1 = 0x7E41D60B
	[r4+-4] = r1
	{r3, r0} = [-r4]
	r5 = 0x01C00020
	[r5+0] = r0
	[r5+4] = r3
	[r5+8] = r4
	cli
1:	goto 1b
