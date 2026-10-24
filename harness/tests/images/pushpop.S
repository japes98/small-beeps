/* SPDX-License-Identifier: MIT */
/* SPDX-FileCopyrightText: 2026 japes98 */
/* The 4-byte push and pop of a register list with no rets or pc,
   `[--sp] = {list}` (d8 e8) and `{list} = [sp++]` (d4 e8), for lists
   whose lowest register is above r0, and lists from r0 beside them. Each
   case pops into a different list from the one it pushed, so the order
   shows: the lowest register at the lowest address. Results, OUT(k):
   A  r1..r5 = 0xA1..0xA5; [--sp] = {r5-r1}
      0 sp before, 1 sp after, 2-6 the five words at sp, then
      {r11-r7} = [sp++]: 7-11 r7..r11, 12 sp after
   B  r15 = 0xF15; [--sp] = {r15}; {r9} = [sp++]: 13 r9, 14 sp after
   C  r2, r4, r6, r8, r10, r14 = 0xB2, 0xB4, ... 0xBE;
      [--sp] = {r14, r10, r8, r6, r4, r2}; 15 sp after;
      {r15, r13, r11, r9, r7, r5} = [sp++]: 16-21 r5, r7, ... r15, 22 sp
   D  r0..r7 = 0xC0..0xC7; [--sp] = {r7-r0} (a list from r0);
      {r15-r8} = [sp++]: 23-30 r8..r15; then r8..r15 = 0xD8..0xDF;
      [--sp] = {r15-r8}; {r7-r0} = [sp++]: 31-38 r0..r7, 39 sp after
   E  [--sp] = {} and {} = [sp++] (as bytes: the assembler takes no empty
      list): 40 sp after each, 41 sp after both
   Then main returns and start.S halts. */
	.text
	.globl main
main:
	r12 = 0x01C00100

	r1 = 0xA1
	r2 = 0xA2
	r3 = 0xA3
	r4 = 0xA4
	r5 = 0xA5
	r0 = sp
	[r12+0] = r0
	[--sp] = {r5-r1}
	r6 = sp
	[r12+4] = r6
	r0 = [r6+0]
	[r12+8] = r0
	r0 = [r6+4]
	[r12+12] = r0
	r0 = [r6+8]
	[r12+16] = r0
	r0 = [r6+12]
	[r12+20] = r0
	r0 = [r6+16]
	[r12+24] = r0
	{r11-r7} = [sp++]
	[r12+28] = r7
	[r12+32] = r8
	[r12+36] = r9
	[r12+40] = r10
	[r12+44] = r11
	r0 = sp
	[r12+48] = r0

	r15 = 0xF15
	[--sp] = {r15}
	{r9} = [sp++]
	[r12+52] = r9
	r0 = sp
	[r12+56] = r0

	r2 = 0xB2
	r4 = 0xB4
	r6 = 0xB6
	r8 = 0xB8
	r10 = 0xBA
	r14 = 0xBE
	[--sp] = {r14, r10, r8, r6, r4, r2}
	r0 = sp
	[r12+60] = r0
	{r15, r13, r11, r9, r7, r5} = [sp++]
	[r12+64] = r5
	[r12+68] = r7
	[r12+72] = r9
	[r12+76] = r11
	[r12+80] = r13
	[r12+84] = r15
	r0 = sp
	[r12+88] = r0

	r0 = 0xC0
	r1 = 0xC1
	r2 = 0xC2
	r3 = 0xC3
	r4 = 0xC4
	r5 = 0xC5
	r6 = 0xC6
	r7 = 0xC7
	[--sp] = {r7-r0}
	{r15-r8} = [sp++]
	r0 = 0x01C00100
	[r0+92] = r8
	[r0+96] = r9
	[r0+100] = r10
	[r0+104] = r11
	[r0+108] = r12
	[r0+112] = r13
	[r0+116] = r14
	[r0+120] = r15
	r8 = 0xD8
	r9 = 0xD9
	r10 = 0xDA
	r11 = 0xDB
	r12 = 0xDC
	r13 = 0xDD
	r14 = 0xDE
	r15 = 0xDF
	[--sp] = {r15-r8}
	{r7-r0} = [sp++]
	r12 = 0x01C00100
	[r12+124] = r0
	[r12+128] = r1
	[r12+132] = r2
	[r12+136] = r3
	[r12+140] = r4
	[r12+144] = r5
	[r12+148] = r6
	[r12+152] = r7
	r0 = sp
	[r12+156] = r0

	.byte 0xd8, 0xe8, 0x00, 0x00
	r0 = sp
	[r12+160] = r0
	.byte 0xd4, 0xe8, 0x00, 0x00
	r0 = sp
	[r12+164] = r0
	rts
