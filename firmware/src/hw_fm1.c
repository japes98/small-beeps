/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * The FM-1 hardware build's own parts (SB_HW_FM1; docs/DESIGN-NOTES.md,
 * clean-br17-start; R-HW-1). The firmware built for a unit, not for
 * fwtest: the panel brought up as HW-115 gives it before anything else,
 * the backlight on (HW-116), and a polled way to draw on the panel that
 * works before interrupts, the timer or DMA do: the start-up's bands and
 * the halt screen. Everything here is in .boot.text: sb_start calls
 * hw_early before it copies the rest of the code to RAM, and the build
 * never makes the flash busy, so the window can still be read later.
 * Registers by address from HARDWARE-SPEC, as a base and an offset: SPI1
 * HW-28, the ports and JL_IOMAP HW-56.
 */

#include "sb.h"
#include "hw_fm1.h"

#if defined(SB_HW_FM1)

#define HW_BOOT __attribute__((section(".boot.text"), noinline))
#define HW_REG(a) (*(volatile u32 *)(a))
#define HW_PORTA 0x00050000u
#define HW_PORTC 0x00050080u
#define HW_OUT 0u
#define HW_DIR 8u
#define HW_IOMAP_CON1 HW_REG(0x00051020u)
#define HW_SPI1 0x00011D00u
#define HW_SPI1_CON HW_REG(HW_SPI1)
#define HW_SPI1_BAUD HW_REG(HW_SPI1 + 4u)
#define HW_SPI1_BUF HW_REG(HW_SPI1 + 8u)
#define HW_SPI_ON 0x21u                 /* HW-115's CON without bit 14 */
#define HW_SPI_DONE 0x8000u             /* CON bit 15, cleared by bit 14 */
#define HW_SPI_CLEAR 0x4000u
#define HW_CS (1u << 7)                 /* PC7, the chip select, active low */
#define HW_DC (1u << 8)                 /* PC8: 0 command, 1 data */
#define HW_SPI_PINS ((1u << 8) | (1u << 9) | (1u << 10))
#define HW_BACKLIGHT (1u << 2)          /* PA2, active low (HW-116) */
/* Two-instruction passes of hw_wait in a millisecond at HW-119's 360 MHz,
 * one instruction a cycle; longer if a taken branch costs more, which
 * HW-115's waits allow (they are minimums, HW-32). */
#define HW_PASSES_MS 180000u
/* At most this many polls of CON bit 15 for one byte before the halt
 * screen gives up waiting: a DMA transfer may still be going. */
#define HW_POLLS 1000000u

static void HW_BOOT hw_wait_ms(u32 ms)
{
    u32 n = ms * HW_PASSES_MS;
    __asm__ volatile("1:\n\t%0 += -1\n\tif (%0 != 0) goto 1b" : "+r"(n));
}

/* One byte through BUF: wait for CON bit 15, clear it with bit 14. */
static void HW_BOOT hw_byte(u32 b)
{
    HW_SPI1_BUF = b;
    while (!(HW_SPI1_CON & HW_SPI_DONE))
        ;
    HW_SPI1_CON = HW_SPI_ON | HW_SPI_CLEAR;
}

/* A command byte: PC7 low, PC8 low for it, then PC8 high for its data. */
static void HW_BOOT hw_cmd(u32 c)
{
    HW_REG(HW_PORTC + HW_OUT) &= ~HW_CS;
    HW_REG(HW_PORTC + HW_OUT) &= ~HW_DC;
    hw_byte(c);
    HW_REG(HW_PORTC + HW_OUT) |= HW_DC;
}

static void HW_BOOT hw_end(void)
{
    HW_REG(HW_PORTC + HW_OUT) |= HW_CS;
}

static void HW_BOOT hw_pair(u32 a, u32 b)
{
    hw_byte(a >> 8);
    hw_byte(a & 0xFF);
    hw_byte(b >> 8);
    hw_byte(b & 0xFF);
}

/* A w x h rectangle at (x, y) in one RGB565 colour, high byte first
 * (HW-115 step 4), polled. */
void HW_BOOT hw_fill(u32 x, u32 y, u32 w, u32 h, u32 colour)
{
    u32 n;
    hw_cmd(0x2A);
    hw_pair(x, x + w - 1);
    hw_end();
    hw_cmd(0x2B);
    hw_pair(y, y + h - 1);
    hw_end();
    hw_cmd(0x2C);
    for (n = w * h; n; n--) {
        hw_byte(colour >> 8);
        hw_byte(colour & 0xFF);
    }
    hw_end();
}

/* Band n of the start-up (1 to 3), polled: rows 40 + 24 n to 40 + 24 n +
 * 15, blue, green, then white, each added to the ones before. No table:
 * nothing may be read from .rodata before the copy. */
void HW_BOOT hw_band(u32 n)
{
    hw_fill(0, 40 + 24 * n, 240, 16, n == 1 ? 0x001Fu : n == 2 ? 0x07E0u : 0xFFFFu);
}

/* The panel as HW-115 gives it, then the backlight on, then band 1. */
void HW_BOOT hw_early(void)
{
    /* Step 1: PC7 an output driven high; PC8 to PC10 outputs driven low;
     * SPI1 on pin group B. No pull or drive is set. */
    HW_REG(HW_PORTC + HW_OUT) |= HW_CS;
    HW_REG(HW_PORTC + HW_DIR) &= ~HW_CS;
    HW_REG(HW_PORTC + HW_OUT) &= ~HW_SPI_PINS;
    HW_REG(HW_PORTC + HW_DIR) &= ~HW_SPI_PINS;
    HW_IOMAP_CON1 |= 1u << 4;
    /* Step 2: BAUD 4, then CON 0x4021. */
    HW_SPI1_BAUD = 4;
    HW_SPI1_CON = HW_SPI_ON | HW_SPI_CLEAR;
    /* Step 3. */
    hw_cmd(0x01);                       /* software reset */
    hw_end();
    hw_wait_ms(150);
    hw_cmd(0x11);                       /* sleep out */
    hw_end();
    hw_wait_ms(120);
    hw_cmd(0x3A);                       /* 16-bit pixels */
    hw_byte(0x55);
    hw_end();
    hw_cmd(0x36);
    hw_byte(0x00);
    hw_end();
    hw_cmd(0x21);                       /* inversion on */
    hw_end();
    hw_cmd(0x13);                       /* normal display */
    hw_end();
    hw_fill(0, 0, 240, 240, 0x0000);
    hw_cmd(0x29);                       /* display on */
    hw_end();
    /* The backlight on, and kept on: PA2 low also enables the key
     * matrix (HW-116, HW-117). */
    HW_REG(HW_PORTA + HW_OUT) &= ~HW_BACKLIGHT;
    HW_REG(HW_PORTA + HW_DIR) &= ~HW_BACKLIGHT;
    hw_band(1);
}

/* sb_halt's screen: solid red, polled, once any transfer on its way has
 * ended (or after HW_POLLS polls). Interrupts are already off. */
void HW_BOOT hw_halt_screen(void)
{
    u32 n;
    for (n = 0; n < HW_POLLS && !(HW_SPI1_CON & HW_SPI_DONE); n++)
        ;
    HW_SPI1_CON = HW_SPI_ON | HW_SPI_CLEAR;
    HW_REG(HW_PORTC + HW_OUT) |= HW_CS;
    hw_fill(0, 0, 240, 240, 0xF800);
}

#endif
