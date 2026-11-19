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

#if defined(SB_HW_FM1)

#include "input.h"
#include "store.h"
#include "WL82.h"

#define REG(a) (*(volatile u32 *)(a))
#define SYNC() __asm__ volatile("csync" ::: "memory")

/* HW-128: the code window's controller, its cipher, the peripheral
 * cipher and the cache control. */
#define WIN_CON      REG(0x40200)
#define WIN_BASE     REG(0x4020C)
#define WIN_CIPHER   REG(0x40300)
#define WIN_KEY      REG(0x40304)
#define PERI_CIPHER  REG(0x13000)
#define CACHE_CON    REG(0x01EEE008)
#define CACHE_IDLE   (1u << 14)
#define CACHE_BITS   (3u << 8)
#define IDLE_POLLS   1000000u
/* HW-56: JL_IOMAP's CON0 and CON1; port registers from a port's base. */
#define IOMAP_CON0   REG(0x0005101C)
#define IOMAP_CON1   REG(0x00051020)
#define PORT(base, off) REG((base) + (off))
#define PA 0x00050000u
#define PB (0x00050000u + 0x40u)
#define PD 0x000500C0u
#define OUT 0u
#define IN 4u
#define DIR 8u
#define DIE 12u
#define PU 16u
#define PDN 20u
#define HD 28u
/* SPI0 (HW-83, HW-128): CON's bits as the store uses them. */
#define SPI_RX       (1u << 12)
#define SPI_CLEAR    (1u << 14)
#define SPI_DONE     (1u << 15)
/* HW-9: core 1's start address word and C1_CON. */
#define C1_START     REG(0x01C7FFF8)
#define C1_CON       REG(0x01EEE004)
/* HW-117, HW-118: the shift registers' pins and the LED lines. */
#define PA_LATCH  (1u << 1)
#define PA_CLOCK  (1u << 3)
#define PA_DATA   (1u << 4)
#define PA_LEDS   ((1u << 9) | (1u << 10))
#define PH_LEDS   ((1u << 6) | (1u << 9))
#define PA_LED2   (1u << 10)
#define PA_ROWS   (0xFu << 5)
/* The pins this build drives itself, masked out of the port rows: PA1 to
 * PA4 and PA9, PA10 (the matrix, the backlight, the LED lines), PB1 and
 * PB6 (the ADC channels it sets up), PC7 to PC10 (the panel), PH6 and PH9
 * (the LED lines). */
#define MASK_A    0x061Eu
#define MASK_B    0x0042u
#define MASK_C    0x0780u
#define MASK_H    0x0240u
/* The start-up counter's kind: a firmware kind of this build's own
 * (store.h: 0x80 to 0xFE), id 0, a 4-byte count. */
#define COUNTER_KIND 0xF0u

struct hw_start3 hw3;
volatile u32 hw_core1_count;
volatile u32 hw_scan_paused;
void hw_core1_loop(void);

/* --- Text -------------------------------------------------------------- */

static char *put_s(char *p, const char *s)
{
    while (*s)
        *p++ = *s++;
    return p;
}

static char *put_hex(char *p, u32 v, u32 digits)
{
    static const char hex[] = "0123456789ABCDEF";

    while (digits--)
        *p++ = hex[v >> 4 * digits & 0xF];
    return p;
}

static char *put_dec(char *p, u32 v)
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

static char *put_int(char *p, int v)
{
    if (v < 0) {
        *p++ = '-';
        v = -v;
    }
    return put_dec(p, (u32)v);
}

/* One row of text at y, 8 pixels high, from x = 6, sent at once. */
static void row(u32 y, const char *text, u32 colour)
{
    gfx_fill(4, y, SCREEN_W - 8, FONT_H, RGB565(0, 0, 0));
    gfx_text(6, y, text, colour, RGB565(0, 0, 0), 1);
    lcd_send_rows(y, FONT_H);
    lcd_wait();
}

/* --- The matrix's pins, light1's way (HW-117) --------------------------- */

static void shift_word(u32 word)
{
    u32 n;

    for (n = 0; n < 16; n++, word <<= 1) {
        if (word & 0x8000u)
            PORT(PA, OUT) |= PA_DATA;
        else
            PORT(PA, OUT) &= ~PA_DATA;
        SYNC();
        PORT(PA, OUT) |= PA_CLOCK;
        SYNC();
        PORT(PA, OUT) &= ~PA_CLOCK;
        SYNC();
    }
    PORT(PA, OUT) |= PA_LATCH;
    SYNC();
    PORT(PA, OUT) &= ~PA_LATCH;
    SYNC();
}

/* --- (c) The flash, taken and given back (HW-128) ------------------------ */

static void cs_low(void)  { PORT(PD, OUT) &= ~1u; }
static void cs_high(void) { PORT(PD, OUT) |= 1u; }

static u32 spi_byte(u32 b)
{
    JL_SPI0->BUF = b;
    while (!(JL_SPI0->CON & SPI_DONE))
        ;
    JL_SPI0->CON |= SPI_CLEAR;
    return JL_SPI0->BUF & 0xFFu;
}

/* A command and n bytes read back, under one chip select. */
static u32 spi_read(u32 cmd, u32 n)
{
    u32 v = 0;

    cs_low();
    JL_SPI0->CON &= ~SPI_RX;
    spi_byte(cmd);
    JL_SPI0->CON |= SPI_RX;
    while (n--)
        v = v << 8 | spi_byte(0xFFu);
    JL_SPI0->CON &= ~SPI_RX;
    cs_high();
    return v;
}

/* HW-128, "to take it". Interrupts may be on: every handler is in RAM. */
static void flash_take(void)
{
    WIN_CON = 0;
    PERI_CIPHER = 0;
    IOMAP_CON1 &= ~(1u << 1);
    IOMAP_CON0 &= ~(1u << 5);
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
    cs_low();                             /* 0xFF twice (HW-123) */
    spi_byte(0xFFu);
    spi_byte(0xFFu);
    cs_high();
}

/* HW-128, "to give it back", with interrupts off for it; on again after if
 * they were. The window's BAUD isn't written: HARDWARE-SPEC gives no
 * address for it, and the take never wrote it (SR-17). The mode word is
 * the one read before the take; the base is HW-128's, the key the boot
 * block's. */
static void flash_give(u32 irq_on)
{
    u32 a, n;

    __asm__ volatile("cli" ::: "memory");
    JL_SPI0->CON = 0;
    PERI_CIPHER = 0;
    WIN_CIPHER = 0;
    IOMAP_CON0 &= ~(1u << 16);
    WIN_CON = 0x00F00000u;
    WIN_CON = 0;
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
    SYNC();
    if (irq_on)
        __asm__ volatile("sti" ::: "memory");
}

/* (c) step 1, before interrupts are on: the window's registers as
 * m-bootloader left them, shown before anything is changed; then, if its
 * CON reads back, the read-only round trip with its two LEDs. */
void hw_round_trip(void)
{
    char t[48], *p;

    hw3.win_con = WIN_CON;
    hw3.win_base = WIN_BASE;
    hw3.win_key = WIN_KEY;
#if defined(SB_TEST_HW_WINDOW)
    /* The test build only (tools/seams_suite.py, case hw3): fwtest has no
     * window controller, and its CON reads 0, so the round trip and the
     * store's counter would never run there. This build takes HW-128's
     * quad mode word (bits 23-20 at 9) in its place. */
    if (!hw3.win_con)
        hw3.win_con = (0x00280381u & ~0x00F00000u) | 9u << 20;
#endif
    p = put_s(t, "win ");
    p = put_hex(p, hw3.win_con, 8);
    p = put_s(p, " ");
    p = put_hex(p, hw3.win_base, 5);
    p = put_s(p, " key ");
    p = put_hex(p, hw3.win_key & 0xFFFFu, 4);
    p = put_s(p, "/");
    p = put_hex(p, hw_boot_key, 4);
    *p = 0;
    row(HW3_WIN_Y, t, RGB565(31, 63, 31));
    if (!hw3.win_con) {
        row(HW3_FLASH_Y, "window CON reads 0: round trip not tried", RGB565(31, 0, 0));
        return;
    }
    /* The LEDs' pins as HW-117 and HW-118 give them, outputs driven low. */
    PORT(PA, OUT) &= ~(PA_LATCH | PA_CLOCK | PA_DATA | PA_LEDS);
    PORT(PA, DIR) &= ~(PA_LATCH | PA_CLOCK | PA_DATA | PA_LEDS);
    hw3.tried = 1;
    flash_take();
    hw3.id = spi_read(0x9Fu, 3);
    hw3.status1 = spi_read(0x05u, 1);
    hw3.status2 = spi_read(0x35u, 1);
    shift_word(0xFBFFu);                   /* LED 1: PLAY's, from RAM */
    PORT(PA, OUT) |= PA_LED2;
    SYNC();
    flash_give(0);
    hw_rt_led_window();                    /* LED 2: PLAY and REC, from the window */
    hw3.back = 1;
    p = put_s(t, "flash ");
    p = put_hex(p, hw3.id, 6);
    p = put_s(p, " s1 ");
    p = put_hex(p, hw3.status1, 2);
    p = put_s(p, " s2 ");
    p = put_hex(p, hw3.status2, 2);
    p = put_s(p, hw3.idle_timeouts ? " back, idle timeout" : " back");
    *p = 0;
    row(HW3_FLASH_Y, t, RGB565(31, 63, 31));
}

/* (c) step 2, with interrupts on, only if step 1 came back: the store's
 * start-up and its counter, between one take and one give-back. */
void hw_store_counter(void)
{
    u8 b[4];
    u32 version, n = 0;
    int len;

    if (!hw3.back)
        return;
    flash_take();
    store_init();
    len = store_get(COUNTER_KIND, 0, b, sizeof b, &version);
    if (len == 4)
        n = b[0] | (u32)b[1] << 8 | (u32)b[2] << 16 | (u32)b[3] << 24;
    hw3.get_result = len;
    n++;
    b[0] = (u8)n;
    b[1] = (u8)(n >> 8);
    b[2] = (u8)(n >> 16);
    b[3] = (u8)(n >> 24);
    hw3.put_result = store_put(COUNTER_KIND, 0, 1, b, 4);
    hw3.count = hw3.put_result == STORE_OK ? n : n - 1;
    hw3.stored = 1;
    flash_give(1);
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

static void adc_all(void)
{
    u32 ch, n;

    for (ch = 0; ch < HW3_ADC_CHANNELS; ch++) {
        JL_ADC->CON = ch << 8 | 1u << 4 | 1u << 6;
        for (n = 0; n < 1000 && !(JL_ADC->CON & (1u << 7)); n++)
            ;
        hw3.adc[ch] = n < 1000 ? JL_ADC->RES & 0x3FFu : 0xFFFFu;
    }
}

/* --- (a) The matrix, swept from main (HW-117, HW-129) -------------------- */

/* Each of the 16 single-zero column words, latched with the LED lines low,
 * then rows PA5 to PA8 read 10 us later or more (closed reads low); the
 * scan (input.c) skips its slots meanwhile and starts again from slot 0. */
static void sweep(void)
{
    u32 col, t;

    hw_scan_paused = 1;
    PORT(PA, OUT) &= ~PA_LEDS;
    REG(0x000501C0u + OUT) &= ~PH_LEDS;
    SYNC();
    for (col = 0; col < 16; col++) {
        shift_word(0xFFFFu & ~(1u << col));
        t = sb_now();
        while (sb_now() - t < 300u)        /* 12.5 us of 24 MHz units */
            ;
        hw3.grid[col] = (u8)(~PORT(PA, IN) >> 5 & 0xFu);
    }
    shift_word(0xFFFFu);
    input_scan_restart();
    hw_scan_paused = 0;
}

/* --- (d) Core 1 (HW-9) --------------------------------------------------- */

/* After sb_irq_init has written the vector table, whose slot 126 this is;
 * nothing writes that slot afterwards. */
void hw_core1_start(void)
{
    C1_START = (u32)hw_core1_loop;
    SYNC();
    C1_CON |= 1u << 3;
    SYNC();
}

/* --- The rows ------------------------------------------------------------- */

static void draw_grid(void)
{
    char t[40], *p;
    u32 r, c;

    row(HW3_GRID_Y, "matrix  0123456789ABCDEF", RGB565(0, 63, 31));
    for (r = 0; r < 4; r++) {
        p = put_s(t, "PA");
        *p++ = (char)('5' + r);
        p = put_s(p, "     ");
        for (c = 0; c < 16; c++)
            *p++ = hw3.grid[c] >> r & 1 ? '#' : '.';
        *p = 0;
        row(HW3_GRID_Y + FONT_H * (r + 1), t, RGB565(31, 63, 31));
    }
}

static void draw_ports(void)
{
    char t[40], *p = t;

    p = put_s(p, "in A ");
    p = put_hex(p, PORT(PA, IN) & ~MASK_A & 0xFFFFu, 4);
    p = put_s(p, " B ");
    p = put_hex(p, PORT(PB, IN) & ~MASK_B & 0xFFFFu, 4);
    p = put_s(p, " C ");
    p = put_hex(p, REG(0x00050080u + IN) & ~MASK_C & 0xFFFFu, 4);
    p = put_s(p, " H ");
    p = put_hex(p, REG(0x000501C0u + IN) & ~MASK_H & 0xFFFFu, 4);
    *p = 0;
    row(HW3_PORTS_Y, t, RGB565(31, 63, 31));
}

static void draw_adc(void)
{
    char t[48], *p;
    u32 half, ch;

    for (half = 0; half < 2; half++) {
        p = put_s(t, half ? "ad6-11" : "ad 0-5");
        for (ch = 6 * half; ch < 6 * half + 6; ch++) {
            *p++ = ' ';
            p = hw3.adc[ch] > 1023 ? put_s(p, "----") : put_hex(p, hw3.adc[ch], 3);
        }
        *p = 0;
        row(HW3_ADC_Y + FONT_H * half, t, RGB565(31, 63, 0));
    }
}

static void draw_store(void)
{
    char t[48], *p = t;

    if (!hw3.stored) {
        row(HW3_STORE_Y, hw3.tried ? "store: not tried" : "store: no round trip", RGB565(31, 0, 0));
        return;
    }
    p = put_s(p, "on ");
    p = put_dec(p, hw3.count);
    p = put_s(p, " put ");
    p = put_int(p, hw3.put_result);
    p = put_s(p, " get ");
    p = put_int(p, hw3.get_result);
    p = put_s(p, " v");
    p = put_dec(p, sb_store.verify_fail);
    p = put_s(p, " e");
    p = put_dec(p, sb_store_erase_fail);
    p = put_s(p, " ");
    p = put_hex(p, sb_store.part, 6);
    *p = 0;
    row(HW3_STORE_Y, t, hw3.put_result == STORE_OK ? RGB565(0, 63, 0) : RGB565(31, 0, 0));
}

static void draw_core1(void)
{
    char t[48], *p = t;

    p = put_s(p, "core1 ");
    p = put_dec(p, hw_core1_count);
    p = put_s(p, " c1con ");
    p = put_hex(p, C1_CON, 8);
    *p = 0;
    row(HW3_CORE1_Y, t, RGB565(31, 63, 31));
}

/* Once the test screen is up: every row. */
void hw_rows_all(void)
{
    char t[48], *p;

    if (hw3.win_con || hw3.win_base) {
        p = put_s(t, "win ");
        p = put_hex(p, hw3.win_con, 8);
        p = put_s(p, " ");
        p = put_hex(p, hw3.win_base, 5);
        p = put_s(p, " key ");
        p = put_hex(p, hw3.win_key & 0xFFFFu, 4);
        p = put_s(p, "/");
        p = put_hex(p, hw_boot_key, 4);
        *p = 0;
        row(HW3_WIN_Y, t, RGB565(31, 63, 31));
    }
    if (hw3.back) {
        p = put_s(t, "flash ");
        p = put_hex(p, hw3.id, 6);
        p = put_s(p, " s1 ");
        p = put_hex(p, hw3.status1, 2);
        p = put_s(p, " s2 ");
        p = put_hex(p, hw3.status2, 2);
        p = put_s(p, hw3.idle_timeouts ? " back, idle timeout" : " back");
        *p = 0;
        row(HW3_FLASH_Y, t, RGB565(31, 63, 31));
    } else {
        row(HW3_FLASH_Y, "window CON reads 0: round trip not tried", RGB565(31, 0, 0));
    }
    draw_store();
    hw_refresh(1);
}

/* About ten times a second (main.c): the matrix, the ports and the ADC;
 * once a second, core 1's counter. */
void hw_refresh(u32 second)
{
    sweep();
    draw_grid();
    draw_ports();
    adc_all();
    draw_adc();
    if (second)
        draw_core1();
}

#endif
