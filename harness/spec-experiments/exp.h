/* SPDX-License-Identifier: MIT */
/* SPDX-FileCopyrightText: 2026 japes98 */
/*
 * Spec-side black-box experiments (README.md): what they poke, written from
 * the JieLi SDK's register map (vendor/jieli-sdk WL82.h, csfr.h; hwi.h for
 * the interrupt numbers) and, where the SDK has no bit meanings, from the
 * vendored emulator's model (fm1-soc lib.rs, periph.rs, lcd.rs). Spec side
 * only: this file and the images never leave harness/; docs/HARDWARE-SPEC.md
 * cites only their IDs and results.
 */
#ifndef EXP_H
#define EXP_H

typedef unsigned int u32;
typedef unsigned short u16;
typedef unsigned char u8;
typedef int s32;
#define REG(a) (*(volatile u32 *)(a))

/* Results: fixed words in RAM, saved with --ram. */
#define OUT(i) REG(0x01c00100u + 4u * (i))
#define LOG ((volatile u32 *)0x01c01000u)

/* Interrupts: RAM vector table (hwi.h ISR_ENTRY), cpu0's ICFG00.. words
   (csfr.h q32DSP(0)), software latch (ILAT_SET / ILAT_CLR). */
#define VECTOR(n) REG(0x01c7fe00u + 4u * (n))
#define ICFG(n) REG(0x1eef100u + 4u * ((n) >> 3))
#define ICFG_ON(n, prio) (((1u | ((prio) << 1)) & 0xfu) << (((n) & 7u) * 4u))
#define ILAT_SET REG(0x1eef1a0u)
#define ILAT_CLR REG(0x1eef1a4u)
/* The core tick timer (csfr.h TTMR_CON / TTMR_CNT / TTMR_PRD). */
#define TTMR_CON REG(0x1eef0ecu)
#define TTMR_CNT REG(0x1eef0f0u)
#define TTMR_PRD REG(0x1eef0f4u)
#define IRQ_TICK_TMR 3u
#define IRQ_TIMER0 4u
#define IRQ_ALNK 11u
#define IRQ_TIMER5 63u
#define IRQ_SOFT0 120u

/* corex2 (csfr.h): C1_CON, DBG_MSG. */
#define C1_CON REG(0x1eee004u)
#define DBG_MSG REG(0x1eee244u)
#define CORE1_ENTRY REG(0x01c7fff8u)

/* JL_TIMERn (WL82.h): CON, CNT, PRD at +0, +4, +8. */
#define TMR_CON(n) REG(0x10400u + 0x100u * (n))
#define TMR_CNT(n) REG(0x10404u + 0x100u * (n))
#define TMR_PRD(n) REG(0x10408u + 0x100u * (n))

/* JL_PORTx (WL82.h): OUT +0, IN +4. */
#define PA_OUT REG(0x50000u)
#define PA_IN REG(0x50004u)
#define PB_IN REG(0x50044u)
#define PC_OUT REG(0x50080u)
#define PH_OUT REG(0x501c0u)

/* JL_SPI1 (WL82.h): CON, BAUD, BUF, ADR, CNT. */
#define SPI1_CON REG(0x11d00u)
#define SPI1_BUF REG(0x11d08u)
#define SPI1_ADR REG(0x11d0cu)
#define SPI1_CNT REG(0x11d10u)

/* JL_ADC (WL82.h): CON, RES. */
#define ADC_CON REG(0x13100u)
#define ADC_RES REG(0x13104u)

/* JL_ALNK0 (WL82.h): CON0, CON1, CON2, CON3, ADR0..ADR3, LEN. */
#define ALNK_CON0 REG(0x12e00u)
#define ALNK_CON2 REG(0x12e08u)
#define ALNK_ADR3 REG(0x12e1cu)
#define ALNK_LEN REG(0x12e20u)

static inline void irq_on(void)
{
    __asm__ volatile("r0 = 0x100\n\ticfg = r0\n\tsti" ::: "r0");
}

/* Wait about `us` microseconds on TIMER4's 24 MHz count (already running). */
static inline void wait_us(u32 us)
{
    u32 t0 = TMR_CNT(4);
    while (TMR_CNT(4) - t0 < 24u * us) {
    }
}

#endif
