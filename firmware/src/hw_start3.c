/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * The FM-1 hardware build's start3 parts (SB_HW_FM1; R-HW-1;
 * docs/DESIGN-NOTES.md, clean-br17-start3), each shown on the test screen
 * in rows of its own:
 * (a) the key matrix swept, 16 single-zero column words against rows PA5
 *     to PA8, and the live input registers of ports A, B, C and H;
 * (b) SARADC channels 0 to 11;
 * (c) the flash taken from the code window and given back (HW-128): first
 *     a read-only round trip, then, if it came back, the store's start-up
 *     counter at its default region;
 * (d) core 1 released (HW-9), counting in RAM.
 * All of it runs from RAM (normal .text, copied by sb_start): while the
 * flash is taken nothing may run or read from the window (HW-79). Registers
 * by address from HARDWARE-SPEC: the window and the cache HW-128, the
 * ports and JL_IOMAP HW-56 and HW-85, core 1 HW-9.
 */

#include "sb.h"
#include "hw_fm1.h"
#include "input.h"
#include "store.h"
#include "WL82.h"

#include "hw_start3_int.h"

#if defined(SB_HW_FM1)

struct hw_start3 hw3;
volatile u32 hw_scan_paused;
/* audio10's holds: the screen's redraws (drawing skipped, the text kept)
 * and main's sweeps of the matrix and the SARADC (skipped while the scan
 * is held with 0xFFFF latched). 0 in every other build. */
volatile u32 hw_hold_screen, hw_hold_sweeps;

/* --- Text -------------------------------------------------------------- */

char *put_s(char *p, const char *s)
{
    while (*s)
        *p++ = *s++;
    return p;
}

char *put_dec(char *p, u32 v)
{
    char t[10];
    u32 n = 0;

    do
        t[n++] = (char)('0' + v % 10);
    while (v /= 10);
    while (n)
        *p++ = t[--n];
    return p;
}

/* One row of text at y, 8 pixels high, from x = 6, sent at once. */
void row(u32 y, const char *text, u32 colour)
{
    gfx_fill(4, y, SCREEN_W - 8, FONT_H, RGB565(0, 0, 0));
    gfx_text(6, y, text, colour, RGB565(0, 0, 0), 1);
    lcd_send_rows(y, FONT_H);
    lcd_wait();
}

void rt_cs_down(void)  { PORT(PD, OUT) &= ~1u; }
void rt_cs_up(void) { PORT(PD, OUT) |= 1u; }

u32 spi_byte(u32 b)
{
    JL_SPI0->BUF = b;
    while (!(JL_SPI0->CON & SPI_DONE))
        ;
    JL_SPI0->CON |= SPI_CLEAR;
    return JL_SPI0->BUF & 0xFFu;
}

/* HW-128, "to take it". Interrupts may be on: every handler is in RAM. */
void flash_take(void)
{
    WIN_CON = 0;
    PERI_CIPHER = 0;
    RT_MAP1 &= ~(1u << 1);
    RT_MAP0 &= ~(1u << 5);
    PORT(PD, OUT) |= 1u;                  /* PD0, the chip select: high */
    PORT(PD, DIR) &= ~1u;
    PORT(PD, OUT) &= ~0x30u;              /* PD4, PD5: low */
    PORT(PD, DIR) &= ~0x30u;
    PORT(PD, HD) |= 0x10u;                /* PD4's drive */
    PORT(PD, DIR) |= 0x02u;               /* PD1: in, no pulls */
    PORT(PD, PU) &= ~0x02u;
    PORT(PD, PDN) &= ~0x02u;
    PORT(PD, OUT) |= 0x0Cu;               /* PD2, PD3: high */
    PORT(PD, DIR) &= ~0x0Cu;
    JL_SPI0->CON = 0x28u;
    JL_SPI0->BAUD = 1u;                   /* about 30 MHz (HW-128) */
    JL_SPI0->CON |= SPI_CLEAR | 1u;
    rt_cs_down();                             /* 0xFF twice (HW-123) */
    spi_byte(0xFFu);
    spi_byte(0xFFu);
    rt_cs_up();
}

/* HW-128, "to give it back", with interrupts off for it; on again after if
 * they were: the one give-back, for the round trip and for the store's
 * counter (hw_store_counter), which is the store's only way to the flash
 * on a unit. As HW-134 gives it, by the owner's ruling: CON = 0x00F00000,
 * CON = 0, BAUD = 1, then CON = the mode word read before the take; then
 * HW-128's base (0x4000), the boot block's key, the cache, the cipher on,
 * and bits 8 and 9 of the cache's control set again (HW-134 item 6). */
void flash_give(u32 irq_on)
{
    u32 a, n;

    __asm__ volatile("cli" ::: "memory");
    JL_SPI0->CON = 0;
    PERI_CIPHER = 0;
    WIN_CIPHER = 0;
    RT_MAP0 &= ~(1u << 16);
    WIN_CON = 0x00F00000u;
    WIN_CON = 0;
    WIN_BAUD = 1u;
    WIN_CON = hw3.win_con;
    WIN_BASE = 0x4000u;
    WIN_KEY = hw_boot_key;
    CACHE_CON &= ~CACHE_BITS;
    for (a = 0x01F00000u; a < 0x01F04000u; a += 4)
        REG(a) = 0;
    for (a = 0x01F08000u; a < 0x01F0A200u; a += 4)
        REG(a) = 0;
    for (a = 0x01F0B000u; a < 0x01F0B200u; a += 4)
        REG(a) = 0;
    CACHE_CON |= CACHE_BITS;
    for (n = 0; n < IDLE_POLLS && !(CACHE_CON & CACHE_IDLE); n++)
        ;
    if (n == IDLE_POLLS)
        hw3.idle_timeouts++;
    WIN_CIPHER = 1;
    CACHE_CON |= CACHE_BITS;
    SYNC();
    if (irq_on)
        __asm__ volatile("sti" ::: "memory");
}

/* The report log's take and give-back (hw_report.c): the same as the
 * store's counter's, interrupts on after; refused (-1) unless the round
 * trip came back. */
int hw_flash_take(void)
{
    if (!hw3.back)
        return -1;
    flash_take();
    return 0;
}

void hw_flash_give(void)
{
    flash_give(1);
}

/* Round 2's release: the window's registers read as the round trip reads
 * them, for the log's take and give-back (which write that CON back), and
 * nothing else: no take, no ID read, no LED marks. HW-133 settles the
 * round trip (the flash taken and given back, the app running on). */
void hw_window_keep(void)
{
    hw3.win_con = WIN_CON;
    hw3.win_base = WIN_BASE;
    hw3.win_key = WIN_KEY;
#if defined(SB_TEST_HW_WINDOW)
    /* fwtest's window CON reads 0 (as in hw_round_trip). */
    if (!hw3.win_con)
        hw3.win_con = (0x00280381u & ~0x00F00000u) | 9u << 20;
#endif
    hw3.back = hw3.win_con != 0;
}

/* --- (b) The ADC (HW-40, HW-129) ----------------------------------------- */

/* Channels 3 (PB1) and 4 (PB6) as analogue inputs: input, digital input
 * off, no pulls (this build's choice; section 28 doesn't give it). */
void hw_adc_start(void)
{
    PORT(PB, DIR) |= MASK_B;
    PORT(PB, DIE) &= ~MASK_B;
    PORT(PB, PU) &= ~MASK_B;
    PORT(PB, PDN) &= ~MASK_B;
}

/* --- start3b: where the start-up got to --------------------------------- */

static u32 step_n;
const char *step_text = "";

void draw_step(void)
{
    char t[STEP_CHARS + 16], *p;
    const char *s = step_text;

    p = put_s(t, "step ");
    p = put_dec(p, step_n);
    p = put_s(p, ": ");
    while (*s && p < t + STEP_CHARS)
        *p++ = *s++;
    *p = 0;
    row(HW3_STEP_Y, t, RGB565(0, 63, 31));
}

void hw_step(const char *text)
{
    step_n++;
    step_text = text;
    if (!hw_hold_screen)
        draw_step();
}
#endif
