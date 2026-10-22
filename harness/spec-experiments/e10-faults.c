/* SPDX-License-Identifier: MIT */
/* SPDX-FileCopyrightText: 2026 japes98 */
/* E-10: what fwtest does with the conditions SR-1 lists. Handlers on
   sources 0, 1 and 2 (hwi.h: SDTAP, EXCEPTION, SYSCALL) count at OUT(1..3).
   provoke() makes each condition and keeps what came back: misaligned word
   and halfword loads from RAM and from the code window, a misaligned word
   store into RAM, a read and a write of an address outside every memory
   (0x00ABCDEC, from the SDK's exception demo), a write to the code window,
   and the four divide-by-zero forms. It runs twice: first as fwtest starts,
   then after writing the exception controls the SDK's debug.c writes
   (q32DSP(0) EMU_CON with every bit its tables name, EMU_SSP/USP limits that
   exclude the current stacks; corex2 DBG_EN behind DBG_WR_EN), which are
   read back. csfr.h gives the addresses: q32DSP(0) at 0x1EEF000 (EMU_CON is
   word 0x34), corex2 at 0x1EEE000 (DBG_WR_EN word 0x90, DBG_MSG_CLR 0x92,
   DBG_EN 0xD0). The addresses come from a volatile word, so the compiler
   can't split a misaligned access into byte accesses (it did with constant
   addresses). Run with --console: DBG_MSG words before and after the
   writes to DBG_WR_EN and DBG_MSG_CLR show what those do to fwtest's
   console. */
#include "exp.h"

#define EMU_CON REG(0x1eef0d0u)
#define EMU_MSG REG(0x1eef0d4u)
#define EMU_SSP_H REG(0x1eef0d8u)
#define EMU_SSP_L REG(0x1eef0dcu)
#define EMU_USP_H REG(0x1eef0e0u)
#define EMU_USP_L REG(0x1eef0e4u)
#define DBG_WR_EN REG(0x1eee240u)
#define DBG_MSG_CLR REG(0x1eee248u)
#define DBG_EN REG(0x1eee340u)

#define SCRATCH 0x01c00400u
#define UNMAPPED 0x00abcdecu

static const u32 table[2] = {0x13121110u, 0x17161514u};
static volatile u32 *const addr = (volatile u32 *)0x01c00300u;

__attribute__((interrupt)) void src0_isr(void) { OUT(1)++; }
__attribute__((interrupt)) void src1_isr(void) { OUT(2)++; }
__attribute__((interrupt)) void src2_isr(void) { OUT(3)++; }

/* Keeps its results at OUT(b) .. OUT(b + 13). */
static __attribute__((noinline)) void provoke(u32 b)
{
    volatile u32 zero = 0u, n = 1234u;
    u32 ram = addr[0], code = addr[1];
    REG(ram) = 0x03020100u;
    REG(ram + 4u) = 0x07060504u;
    REG(ram + 8u) = 0u;
    REG(ram + 12u) = 0u;
    OUT(b + 0) = *(volatile u32 *)(ram + 1u);
    OUT(b + 1) = *(volatile u16 *)(ram + 1u);
    OUT(b + 2) = *(volatile u16 *)(ram + 3u);
    OUT(b + 3) = *(volatile u32 *)(code + 1u);
    *(volatile u32 *)(ram + 9u) = 0xaabbccddu;
    OUT(b + 4) = REG(ram + 8u);
    OUT(b + 5) = REG(ram + 12u);
    OUT(b + 6) = REG(UNMAPPED);
    REG(UNMAPPED) = 0x5a5a5a5au;
    OUT(b + 7) = REG(UNMAPPED);
    *(volatile u32 *)code = 0x12345678u;
    OUT(b + 8) = *(volatile u32 *)code;
    OUT(b + 9) = (u32)((s32)n / (s32)zero);
    OUT(b + 10) = n / zero;
    OUT(b + 11) = (u32)((s32)n % (s32)zero);
    OUT(b + 12) = n % zero;
    OUT(b + 13) = OUT(1) + OUT(2) + OUT(3);
}

int main(void)
{
    VECTOR(0) = (u32)src0_isr;
    VECTOR(1) = (u32)src1_isr;
    VECTOR(2) = (u32)src2_isr;
    ICFG(0) |= ICFG_ON(0, 7u) | ICFG_ON(1, 7u) | ICFG_ON(2, 7u);
    addr[0] = SCRATCH;
    addr[1] = (u32)table;
    irq_on();
    DBG_MSG = 0x0a303145u; /* "E10\n" */
    provoke(4);
    EMU_SSP_L = 0x01c70000u;
    EMU_SSP_H = 0x01c70100u;
    EMU_USP_L = 0x01c70000u;
    EMU_USP_H = 0x01c70100u;
    EMU_CON = 0x001f010fu;
    DBG_WR_EN = 0xe7u;
    DBG_EN = 0x003f0030u;
    DBG_MSG_CLR = 0xffffffffu;
    DBG_MSG = 0x0a646e65u; /* "end\n" */
    OUT(18) = EMU_CON;
    OUT(19) = EMU_SSP_L;
    OUT(20) = EMU_USP_H;
    OUT(21) = DBG_EN;
    provoke(22);
    OUT(36) = EMU_MSG;
    OUT(0) = 0x600dd00eu;
    return 0;
}
