/* SPDX-License-Identifier: MIT */
/* SPDX-FileCopyrightText: 2026 japes98 */
/*
 * What the harness's test images touch, as the vendored emulator models it
 * (vendor/emulator/crates/fm1-soc: lib.rs, periph.rs, spiflash.rs, lcd.rs).
 * Spec side only: these images test the harness, not the hardware, and
 * nothing here is a source for HARDWARE-SPEC.md.
 */
#ifndef BOARD_H
#define BOARD_H

typedef unsigned int u32;
typedef int s32;
#define REG(a) (*(volatile u32 *)(a))

/* Results the tests read back: fixed words in RAM. */
#define OUT(i) REG(0x01c00100u + 4u * (i))
#define OUTBUF ((volatile unsigned char *)0x01c00200u)

/* The vector table (periph.rs VEC_BASE): word n = IRQ n's handler. */
#define VECTOR(n) REG(0x01c7fe00u + 4u * (n))
/* Interrupt controller enable/priority nibbles for cpu0 (0x1EEF100). */
#define ICFG(n) REG(0x1eef100u + 4u * ((n) >> 3))
#define ICFG_ON(n, prio) (((1u | ((prio) << 1)) & 0xfu) << (((n) & 7u) * 4u))

/* Debug message box (lib.rs Region::Dbg): each word written to +4 is four
   console bytes. */
#define DBG_MSG REG(0x1eee244u)

/* GPIO (lib.rs; periph.rs pa_write, pa_in, pb_in). */
#define PA_OUT REG(0x50000u)
#define PA_IN REG(0x50004u)
#define PB_IN REG(0x50044u)
#define PC_OUT REG(0x50080u)
#define PD_OUT REG(0x500c0u)
#define PH_OUT REG(0x501c0u)

/* SPI1 to the LCD (lib.rs spi1_write): byte at BUF, D/C on PC8. */
#define SPI1_BUF REG(0x11d08u)
/* SPI0 to the flash chip (spiflash.rs): byte at BUF, chip select PD0 low. */
#define SPI0_BUF REG(0x11c08u)

/* SARADC (periph.rs): CON channel bits 8-11, enable bit 4, start bit 6;
   RES the 10-bit value. The pot is channel 4. */
#define ADC_CON REG(0x13100u)
#define ADC_RES REG(0x13104u)

/* UART1 receive DMA ring (periph.rs Uart). */
#define UART1_CON0 REG(0x12100u)
#define UART1_RXSADR REG(0x1211cu)
#define UART1_RXEADR REG(0x12120u)

/* ALNK0 audio out (periph.rs): CON0 bit 11 runs it, bit 15 reads the half
   playing; PEND bit 7 a half finished (written bit 3 clears it); ADR the
   buffer of two halves of LEN words each; IRQ 11. */
#define ALNK_CON0 REG(0x12e00u)
#define ALNK_PEND REG(0x12e08u)
#define ALNK_ADR REG(0x12e1cu)
#define ALNK_LEN REG(0x12e20u)
#define IRQ_ALNK 11u

static inline void irq_on(void)
{
    __asm__ volatile("r0 = 0x100\n\ticfg = r0\n\tsti" ::: "r0");
}

#endif
