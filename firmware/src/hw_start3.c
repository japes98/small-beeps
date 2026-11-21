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
#define WIN_BAUD     REG(0x00040204)    /* write only (HW-134) */
#define WIN_BASE     REG(0x4020C)
#define WIN_CIPHER   REG(0x40300)
#define WIN_KEY      REG(0x40304)
#define PERI_CIPHER  REG(0x13000)
#define CACHE_CON    REG(0x01EEE008)
#define CACHE_IDLE   (1u << 14)
#define CACHE_BITS   (3u << 8)
#define IDLE_POLLS   1000000u
/* HW-56: JL_IOMAP's CON0 and CON1; port registers from a port's base. */
#define RT_MAP0   REG(0x0005101C)
#define RT_MAP1   REG(0x00051020)
#define PORT(base, off) REG((base) + (off))
#define PA 0x00050000u
#define PB (0x00050000u + 0x40u)
#define PD 0x000500C0u
#define PH 0x000501C0u
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
#define SYS_DIV      REG(0x00010008)            /* JL_CLOCK->SYS_DIV (HW-53, HW-135) */
#define COREX2_WORD(i) REG(0x01EEE000u + 4u * (0x80u + (i)))   /* Q-17's counters, words 0x80-0x8F */
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
#if defined(SB_HW_AUDIO1)
/* audio3: core 1's flag and count alone in a 64-byte block, so nothing
 * core 0 writes shares their cache line (hw_fm1.h). */
struct hw_core1_blk hw_core1_blk __attribute__((aligned(64)));
#else
volatile u32 hw_core1_count, hw_core1_flag;
#endif
volatile u32 hw_scan_paused;
void hw_core1_loop(void);
static void draw_store(void);
static void draw_win(void);
static void draw_flash(void);

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

/* start3b's LED marks in the round trip, one LED at a time (HW-118): the
 * column word, then PA10 or PH9 high. They stay lit through the hold, until
 * the scan starts. */
static void led_mark(u32 word, u32 pa, u32 ph)
{
    PORT(PA, OUT) &= ~PA_LEDS;
    PORT(PH, OUT) &= ~PH_LEDS;
    SYNC();
    shift_word(word);
    PORT(PA, OUT) |= pa;
    PORT(PH, OUT) |= ph;
    SYNC();
}
#define MARK_TAKING()  led_mark(0xFBFFu, PA_LED2, 0)          /* PLAY */
#define MARK_TAKEN()   led_mark(0xF7FEu, 0, 1u << 9)          /* OCT- */
#define MARK_GIVING()  led_mark(0xEFFDu, 0, 1u << 9)          /* OCT+ */

static void rt_cs_down(void)  { PORT(PD, OUT) &= ~1u; }
static void rt_cs_up(void) { PORT(PD, OUT) |= 1u; }

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

    rt_cs_down();
    JL_SPI0->CON &= ~SPI_RX;
    spi_byte(cmd);
    JL_SPI0->CON |= SPI_RX;
    while (n--)
        v = v << 8 | spi_byte(0xFFu);
    JL_SPI0->CON &= ~SPI_RX;
    rt_cs_up();
    return v;
}

/* HW-128, "to take it". Interrupts may be on: every handler is in RAM. */
static void flash_take(void)
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
static void flash_give(u32 irq_on)
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

#if defined(SB_HW_REPORT)
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
#endif

/* (c) step 1, before interrupts are on: the window's registers as
 * m-bootloader left them, shown before anything is changed; then, if its
 * CON reads back, the read-only round trip with its two LEDs. */
void hw_round_trip(void)
{
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
    draw_win();
    if (!hw3.win_con) {
        row(HW3_FLASH_Y, "window CON reads 0: round trip not tried", RGB565(31, 0, 0));
        return;
    }
    /* The LEDs' pins as HW-117 and HW-118 give them, outputs driven low. */
    PORT(PA, OUT) &= ~(PA_LATCH | PA_CLOCK | PA_DATA | PA_LEDS);
    PORT(PA, DIR) &= ~(PA_LATCH | PA_CLOCK | PA_DATA | PA_LEDS);
    PORT(PH, OUT) &= ~PH_LEDS;
    PORT(PH, DIR) &= ~PH_LEDS;
    hw3.tried = 1;
    hw_step("round trip: taking the flash");
    MARK_TAKING();                         /* PLAY: about to take */
    flash_take();
    MARK_TAKEN();                          /* OCT-: taken */
    hw3.id = spi_read(0x9Fu, 3);
    hw3.status1 = spi_read(0x05u, 1);
    hw3.status2 = spi_read(0x35u, 1);
    MARK_GIVING();                         /* OCT+: read, giving back */
    flash_give(0);
    hw_rt_led_window();                    /* OCT- and OCT+: back in the window */
    hw_step("round trip: back");
    hw3.back = 1;
    draw_flash();
}

/* (c) step 2, with interrupts on, only if step 1 came back: the store's
 * start-up and its counter, between one take and one give-back. */
void hw_store_counter(void)
{
    u8 b[4];
    u32 version, n = 0;
    int len;

    if (!hw3.back) {
        hw_step("store: no round trip, not tried");
        return;
    }
    hw_step("store: taking the flash");
    flash_take();
    hw_step("store: store_init");
    store_init();
    hw_step("store: reading the counter");
    len = store_get(COUNTER_KIND, 0, b, sizeof b, &version);
    if (len == 4)
        n = b[0] | (u32)b[1] << 8 | (u32)b[2] << 16 | (u32)b[3] << 24;
    hw3.get_result = len;
    n++;
    b[0] = (u8)n;
    b[1] = (u8)(n >> 8);
    b[2] = (u8)(n >> 16);
    b[3] = (u8)(n >> 24);
    hw_step("store: writing the counter (0xFC000 on)");
    hw3.put_result = store_put(COUNTER_KIND, 0, 1, b, 4);
    hw3.count = hw3.put_result == STORE_OK ? n : n - 1;
    hw3.stored = 1;
    hw_step("store: giving the flash back");
    flash_give(1);
    draw_store();
    hw_step("store: back");
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
#if defined(SB_HW_AUDIO1)
        /* PC0 and PC1 are ALNK0's master and bit clocks in group A
         * (HW-141): not sampled while audio1 may drive them. */
        if (ch == 6 || ch == 7) {
            hw3.adc[ch] = 0xFFFFu;
            continue;
        }
#endif
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

#if defined(SB_HW_AUDIO1)
/* --- audio6's step D: the matrix check and port A (hw_audio.c) ----------- */

/* Rows PA0, PA5 to PA8 and PB7 (HW-117, HW-138, HW-139) as 6 bits, 1 high
 * (open). */
static u32 matrix_rows(void)
{
    u32 a = PORT(PA, IN), b = PORT(PB, IN);

    return (a & 1u) | (a >> 5 & 0xFu) << 1 | (b >> 7 & 1u) << 5;
}

static void matrix_settle(void)
{
    u32 t = sb_now();

    while (sb_now() - t < 300u)        /* 12.5 us of 24 MHz units */
        ;
}

/* With the scan paused by the caller (hw_scan_paused): the LED lines low,
 * as sweep() sets them, 0xFFFF latched (no column) and the rows read into
 * idle; then each of the 16 single-zero column words latched and its
 * closed rows set in map (bit 6 x column + row); 0xFFFF latched at the
 * end. Its port A writes are sweep()'s own. */
void hw_matrix_check(u32 *idle, u32 *map)
{
    u32 col, r, row;

    PORT(PA, OUT) &= ~PA_LEDS;
    REG(0x000501C0u + OUT) &= ~PH_LEDS;
    SYNC();
    map[0] = map[1] = map[2] = 0;
    shift_word(0xFFFFu);
    matrix_settle();
    *idle = matrix_rows();
    for (col = 0; col < 16; col++) {
        shift_word(0xFFFFu & ~(1u << col));
        matrix_settle();
        r = ~matrix_rows() & 0x3Fu;
        for (row = 0; row < 6u; row++)
            if (r >> row & 1u)
                map[(col * 6u + row) / 32u] |= 1u << (col * 6u + row) % 32u;
    }
    shift_word(0xFFFFu);
}

/* Port A's OUT, IN, DIR, DIE, PU, PD, HD0 and HD, read. */
void hw_port_a(u32 *w)
{
    u32 i;

    for (i = 0; i < 8; i++)
        w[i] = REG(PA + 4u * i);
}

/* The scan paused (as sweep() pauses it) and started again. */
void hw_scan_pause(void)
{
    hw_scan_paused = 1;
}

void hw_scan_resume(void)
{
    shift_word(0xFFFFu);
    input_scan_restart();
    hw_scan_paused = 0;
}
#endif

/* --- (d) Core 1 (HW-9) --------------------------------------------------- */

/* After sb_irq_init has written the vector table, whose slot 126 this is;
 * nothing writes that slot afterwards. */
/* Core 1's release as the owner's unit showed it works (clean-br17-encoders:
 * start3c's B started core 1 as A did): HW-135's steps 1 and 3, the start
 * word, then C1_CON bit 3 set and bit 1 cleared, and a wait for core 1's
 * own flag (HW_C1_WAIT_MS at most); SYS_DIV read, never written. With
 * SB_HW_CORE1_SYSDIV (start3c's A, kept for the record), HW-135's full
 * order: SYS_DIV bit 3 set from the value read before C1_CON, and put
 * back exactly as read after the wait, with core 1's screen. Each register is read
 * back after each write, and the corex2 words 0x80 to 0x8F (Q-17: per-core
 * counters whose meaning the SDK doesn't state) before, for a sign of core
 * 1 that doesn't rest on what core 0 sees of its stores (Q-18). */
void hw_core1_start(void)
{
    u32 i, t;

    hw_step("core 1: releasing");
    hw3.c1_fn = (u32)hw_core1_loop;
    for (i = 0; i < 16; i++)
        hw3.x2_before[i] = COREX2_WORD(i);
    hw3.c1_pre = C1_CON;
    hw3.sd_before = SYS_DIV;
    C1_START = hw3.c1_fn;
    SYNC();
    hw3.c1_word = C1_START;
#if defined(SB_HW_CORE1_SYSDIV)
    SYS_DIV = hw3.sd_before | 1u << 3;
    SYNC();
    hw3.sd_set = SYS_DIV;
#endif
    C1_CON |= 1u << 3;
    SYNC();
    hw3.c1_post = C1_CON;
    C1_CON &= ~(1u << 1);
    SYNC();
    hw3.c1_clr1 = C1_CON;
    hw_step("core 1: waiting for its sign");
    t = sb_beacon.beats;
    while (!hw_core1_flag && sb_beacon.beats - t < HW_C1_WAIT_MS)
        ;
    hw3.c1_seen = hw_core1_flag;
    hw3.c1_wait_ms = sb_beacon.beats - t;
#if defined(SB_HW_CORE1_SYSDIV)
    SYS_DIV = hw3.sd_before;
    SYNC();
#endif
    hw3.sd_after = SYS_DIV;
    hw3.c1_at = sb_beacon.beats;
    hw_step(hw3.c1_seen ? "core 1: its sign seen" : "core 1: no sign (timed out)");
}

/* SB_HW_HOLD with SB_HW_CORE1_SYSDIV: core 1's screen, a second or more
 * after the release, held 2 x HW_HOLD_MS: every value the release read,
 * the corex2 words before and a second after (yellow where they changed),
 * core 1's counter. */
#if defined(SB_HW_HOLD) && defined(SB_HW_CORE1_SYSDIV)
static void c1_big(u32 y, const char *label, u32 v, u32 colour)
{
    char t[24], *p = t;

    p = put_s(p, label);
    p = put_hex(p, v, 8);
    *p = 0;
    gfx_text(6, y, t, colour, RGB565(0, 0, 0), 2);
}
#endif

#if defined(SB_HW_HOLD) && defined(SB_HW_CORE1_SYSDIV)
static void core1_draw(void)
{
    char t[24], *p;
    u32 i, white = RGB565(31, 63, 31), dim = RGB565(16, 32, 16), y = 4;

    lcd_wait();
    gfx_fill(0, 0, SCREEN_W, SCREEN_H, RGB565(0, 0, 0));
#if !defined(SB_HW_CORE1_SYSDIV)
    gfx_text(6, y, "CORE1 B: no SYSDIV", RGB565(0, 63, 31), RGB565(0, 0, 0), 2);
#else
    gfx_text(6, y, "CORE1 A: HW-135", RGB565(0, 63, 31), RGB565(0, 0, 0), 2);
#endif
    y += 16;
    p = put_s(t, hw3.c1_seen ? "sign YES " : "sign NO ");
    p = put_dec(p, hw3.c1_wait_ms);
    p = put_s(p, "ms");
    *p = 0;
    gfx_text(6, y, t, hw3.c1_seen ? RGB565(0, 63, 0) : RGB565(31, 0, 0), RGB565(0, 0, 0), 2);
    y += 16;
    p = put_s(t, "count ");
    p = put_dec(p, hw3.count1);
    *p = 0;
    gfx_text(6, y, t, hw3.count1 ? RGB565(0, 63, 0) : RGB565(31, 0, 0), RGB565(0, 0, 0), 2);
    y += 16;
    c1_big(y, "SD    ", hw3.sd_before, white);
    y += 16;
#if !defined(SB_HW_CORE1_SYSDIV)
    gfx_text(6, y, "SD+3  --------", dim, RGB565(0, 0, 0), 2);
#else
    c1_big(y, "SD+3  ", hw3.sd_set, white);
#endif
    y += 16;
    c1_big(y, "SD=   ", hw3.sd_after, hw3.sd_after == hw3.sd_before ? white : RGB565(31, 0, 0));
    y += 16;
    c1_big(y, "C1    ", hw3.c1_pre, white);
    y += 16;
    c1_big(y, "C1+3  ", hw3.c1_post, white);
    y += 16;
    c1_big(y, "C1-1  ", hw3.c1_clr1, white);
    y += 16;
    c1_big(y, hw3.c1_word == hw3.c1_fn ? "W ok  " : "W BAD ", hw3.c1_word, white);
    y += 18;
    for (i = 0; i < 16; i++) {
        p = put_hex(t, 0x80u + i, 2);
        *p++ = ' ';
        p = put_hex(p, hw3.x2_before[i], 8);
        *p++ = '>';
        p = put_hex(p, hw3.x2_after[i], 8);
        *p = 0;
        gfx_text(i < 8 ? 0 : 120, y + FONT_H * (i & 7), t, hw3.x2_before[i] != hw3.x2_after[i] ? RGB565(31, 63, 0) : dim,
                 RGB565(0, 0, 0), 1);
    }
    lcd_send_rows(0, SCREEN_H);
    lcd_wait();
    i = sb_beacon.beats;
    while (sb_beacon.beats - i < 2u * HW_HOLD_MS)
        ;
}
#endif

/* SB_HW_HOLD: a second or more after the release, the corex2 words and
 * core 1's counter sampled again; with SB_HW_CORE1_SYSDIV, core 1's screen. */
void hw_core1_screen(void)
{
#if defined(SB_HW_HOLD)
    u32 i;

    while (sb_beacon.beats - hw3.c1_at < 1000u)
        ;
    for (i = 0; i < 16; i++)
        hw3.x2_after[i] = COREX2_WORD(i);
    hw3.count1 = hw_core1_count;
#if defined(SB_HW_CORE1_SYSDIV)
    core1_draw();
#endif
#endif
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

/* --- start3b: where the start-up got to --------------------------------- */

static u32 step_n;
static const char *step_text = "";

/* The row holds 40 characters at scale 1: "step n: " and as much of the
 * text as fits, never more (a longer text once overran t, clean-br17-audio4). */
#define STEP_CHARS 40u

static void draw_step(void)
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

/* Each step of the start-up, numbered, in the step row as it begins: the
 * row left showing is the step that didn't finish. One row is one
 * transfer whose end is polled (lcd.c), so it is drawn with interrupts off
 * or stopped too. */
void hw_step(const char *text)
{
    step_n++;
    step_text = text;
    draw_step();
}

/* The tick's row: the beats, TIMER0's slots (its interrupt) and count,
 * and core 1's counter; red if the beats have stopped. */
static void draw_tick(u32 stopped)
{
    char t[48], *p;

    p = put_s(t, stopped ? "STOPPED b" : "tick b");
    p = put_dec(p, sb_beacon.beats);
    p = put_s(p, " s");
    p = put_dec(p, hw_slots);
    p = put_s(p, " t");
    p = put_hex(p, JL_TIMER0->CNT, 4);
    p = put_s(p, " c1 ");
    p = put_dec(p, hw_core1_count);
    *p = 0;
    row(HW3_TICK_Y, t, stopped ? RGB565(31, 0, 0) : RGB565(31, 63, 31));
}

/* SB_HW_HOLD: HW_HOLD_MS with the start-up rows and the round trip's LEDs
 * as they are, interrupts still off: TIMER0's slots counted by polling,
 * then TIMER0 stopped and its flag cleared for main to start it. */
void hw_hold(void)
{
#if defined(SB_HW_HOLD)
    u32 slots = 0, last, c;

    hw_step("holding the rows");
    JL_TIMER0->CON = 0;
    JL_TIMER0->CNT = 0;
    JL_TIMER0->PRD = HW_SLOT_PRD;
    JL_TIMER0->CON = HW_SLOT_CON;
    last = JL_TIMER0->CNT;
    while (slots < HW_HOLD_MS * HW_SLOTS_TICK) {
        c = JL_TIMER0->CNT;
        if (c < last)
            slots++;
        last = c;
    }
    JL_TIMER0->CON = 1u << 14;
#endif
}

/* A spin, not idle, for ms beats, the tick's row drawn every 100 beats; if
 * the beats stand still for about HW_STALL_SPINS turns, the row turns red
 * and is drawn again each time, for ever unless they move. */
#define HW_STALL_SPINS 20000000u
void hw_watch(u32 ms)
{
    u32 until = sb_beacon.beats + ms, last = sb_beacon.beats, next = last, spins = 0, b;

    while ((int)((b = sb_beacon.beats) - until) < 0) {
        if (b != last) {
            last = b;
            spins = 0;
        } else if (++spins >= HW_STALL_SPINS) {
            spins = 0;
            draw_tick(1);
            continue;
        }
        if ((int)(b - next) >= 0) {
            draw_tick(0);
            next = b + 100;
        }
    }
    draw_tick(0);
}

static void draw_win(void)
{
    char t[48], *p;

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

static void draw_flash(void)
{
    char t[48], *p;

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
        row(HW3_FLASH_Y, hw3.tried ? "flash: tried, not back" : "window CON reads 0: round trip not tried",
            RGB565(31, 0, 0));
    }
}

/* Over the address pattern once it is sent: the start-up's rows again. */
void hw_rows_start(void)
{
    draw_store();
    draw_win();
    draw_flash();
    draw_step();
}

/* Once the test screen is up: every row. */
void hw_rows_all(void)
{
    draw_win();
    draw_flash();
    draw_store();
    draw_step();
    hw_step("test screen: first sweep");
    hw_refresh(1);
    hw_step("test screen up, main loop next");
}

/* About ten times a second (main.c): the matrix, the ports and the ADC;
 * once a second, core 1's counter. */
void hw_refresh(u32 second)
{
    sweep();
    draw_grid();
    draw_ports();
    /* The scan reads the pot (input.c) from the conversion it started:
     * paused meanwhile, and channel 4's conversion started again after. */
    hw_scan_paused = 1;
    adc_all();
    JL_ADC->CON = 4u << 8 | 1u << 4 | 1u << 6;
    hw_scan_paused = 0;
    draw_adc();
    if (second) {
        draw_core1();
#if defined(SB_HW_AUDIO1)
        if (hw_aud.started)
            hw_audio_line();
#endif
    }
}

#if defined(SB_HW_FINDER)
/* --- The knob finder (SB_HW_FINDER; clean-br17-finder) -------------------
 * After the test screen, main hands over to hw_finder for good: the scan
 * stays paused, and the finder sweeps without a pause between sweeps.
 * Each sweep latches each of the 16 single-zero column words and then
 * 0xFFFF (no column), and reads ports A, B, C, D and H at each, 12.5 us
 * after the latch; then it converts SARADC channels 0 to 11. A pin whose
 * level with no column selected changes is a "pin" change; a pin that
 * reads differently with column c selected than with none is a matrix
 * "cell" (c, pin), and a change in that is a cell change. A channel moving
 * more than its threshold is an ADC change. Each source that changes gets
 * one large line, kept for at least a second, with its count of changes
 * and its level now (an ADC line: its value now and up to three other
 * levels it has taken). For the first HW_FIND_QUIET_MS no control is to
 * be touched: what changes then is marked noisy and left out, and each
 * channel's threshold is set from its spread. The pins this build drives
 * are masked (MASK_A, MASK_B, MASK_C, MASK_H), and port D's PD0 to PD6, the
 * flash's (HW-85); port D is only read. */

#define F_PORTS 5u
#define F_COLS  17u                    /* 16 column words, then none */
#define F_LINES 8u
#define F_PIN   1u
#define F_CELL  2u
#define F_ADC   3u
#if defined(SB_TEST_SHORT_HOLD)
#define HW_FIND_QUIET_MS 400u
#else
#define HW_FIND_QUIET_MS 3000u
#endif
#define F_HOLD_MS 1000u
#define F_BIG_Y(i) (22u + 18u * (i))
#define F_CORE1_Y 170u
#define F_SMALL_Y 188u                 /* five small rows, 188 to 227 */

static const u32 f_base[F_PORTS] = { PA, PB, 0x00050080u, PD, PH };
static const char f_name[F_PORTS] = { 'A', 'B', 'C', 'D', 'H' };
static const u16 f_mask[F_PORTS] = { MASK_A, MASK_B, MASK_C, 0x7Fu, MASK_H };

static u16 f_in[F_COLS][F_PORTS];
static u16 f_prev[F_COLS][F_PORTS];    /* [16]: the pins; [c]: cells of c */
static u16 f_noisy[F_COLS][F_PORTS];
static u32 f_adc_min[HW3_ADC_CHANNELS], f_adc_max[HW3_ADC_CHANNELS];
static u32 f_adc_thr[HW3_ADC_CHANNELS], f_adc_last[HW3_ADC_CHANNELS];
static u32 f_adc_from;                 /* the channel's level before its change */

struct hw_find_line {
    u32 kind, col, port, bit;          /* kind 0: unused */
    u32 count, value, when, fresh, dirty;
    u32 levels[3], nlevels;
};
struct hw_finder {
    u32 sweeps, rate, learning, noisy, dropped;
    struct hw_find_line line[F_LINES];
};
struct hw_finder hw_find;

/* One line of text at scale 2 (16 rows, one polled transfer), sent
 * without waiting for it to end: callers look at lcd_busy first. */
static void big_row(u32 y, const char *text, u32 colour)
{
    gfx_fill(4, y, SCREEN_W - 8, 2 * FONT_H, RGB565(0, 0, 0));
    gfx_text(6, y, text, colour, RGB565(0, 0, 0), 2);
    lcd_send_rows(y, 2 * FONT_H);
}

static void f_event(u32 kind, u32 col, u32 port, u32 bit, u32 value)
{
    struct hw_find_line *l, *pick = 0;
    u32 now = sb_beacon.beats, i, b;

    for (i = 0; i < F_LINES; i++) {
        l = &hw_find.line[i];
        if (l->kind == kind && l->col == col && l->port == port && l->bit == bit) {
            pick = l;
            break;
        }
    }
    if (!pick) {
        for (i = 0; i < F_LINES; i++) {
            l = &hw_find.line[i];
            if (!l->kind) {
                pick = l;
                break;
            }
            if (now - l->when >= F_HOLD_MS && (!pick || l->when < pick->when))
                pick = l;
        }
        if (!pick) {
            hw_find.dropped++;
            return;
        }
        pick->kind = kind;
        pick->col = col;
        pick->port = port;
        pick->bit = bit;
        pick->count = 0;
        pick->nlevels = 0;
        /* A channel's new line starts from the level it left. */
        if (kind == F_ADC) {
            pick->value = f_adc_from;
            pick->count = 1;
        }
    }
    if (kind == F_ADC && pick->count) {
        /* The level it leaves, kept if no kept level is within 0x40. */
        b = pick->value;
        for (i = 0; i < pick->nlevels; i++)
            if ((pick->levels[i] > b ? pick->levels[i] - b : b - pick->levels[i]) < 0x40u)
                break;
        if (i == pick->nlevels) {
            if (pick->nlevels == 3) {
                pick->levels[0] = pick->levels[1];
                pick->levels[1] = pick->levels[2];
                pick->nlevels = 2;
            }
            pick->levels[pick->nlevels++] = b;
        }
    }
    pick->count++;
    pick->value = value;
    pick->when = now;
    pick->fresh = 1;
    pick->dirty = 1;
}

static void f_bits(u32 col, u32 port, u32 changed, u32 now_bits)
{
    u32 bit;

    for (bit = 0; changed; bit++, changed >>= 1)
        if (changed & 1u) {
            if (hw_find.learning) {
                f_noisy[col][port] |= 1u << bit;
                hw_find.noisy++;
            } else {
                f_event(col == 16 ? F_PIN : F_CELL, col, port, bit, now_bits >> bit & 1u);
            }
        }
}

static void f_sweep(void)
{
    u32 col, p, t, v, d;

    for (col = 0; col < F_COLS; col++) {
        shift_word(col < 16 ? 0xFFFFu & ~(1u << col) : 0xFFFFu);
        t = sb_now();
        while (sb_now() - t < 300u)
            ;
        for (p = 0; p < F_PORTS; p++)
            f_in[col][p] = (u16)(PORT(f_base[p], IN) & ~f_mask[p]);
    }
    for (col = 0; col < F_COLS; col++)
        for (p = 0; p < F_PORTS; p++) {
            /* The pins as they read with no column; a cell, as it differs
             * from that with column col. */
            v = col == 16 ? f_in[16][p] : (u32)(f_in[col][p] ^ f_in[16][p]);
            d = (v ^ f_prev[col][p]) & ~f_noisy[col][p] & 0xFFFFu;
            f_prev[col][p] = (u16)v;
            if (d && hw_find.sweeps)
                f_bits(col, p, d, v);
        }
    adc_all();
    for (p = 0; p < HW3_ADC_CHANNELS; p++) {
        v = hw3.adc[p];
        /* Channels 8 and 9 are PC9 and PC10 (HW-129), SPI1's clock and
         * data out to the panel (HW-56, group B): they follow the panel's
         * transfers, so they are left out. */
        if (v > 0x3FFu || p == 8 || p == 9)
            continue;
        if (hw_find.learning) {
            if (!hw_find.sweeps || v < f_adc_min[p])
                f_adc_min[p] = v;
            if (!hw_find.sweeps || v > f_adc_max[p])
                f_adc_max[p] = v;
            f_adc_last[p] = v;
            f_adc_thr[p] = 2u * (f_adc_max[p] - f_adc_min[p]) + 0x18u;
        } else if ((v > f_adc_last[p] ? v - f_adc_last[p] : f_adc_last[p] - v) >= f_adc_thr[p]) {
            f_adc_from = f_adc_last[p];
            f_adc_last[p] = v;
            f_event(F_ADC, 0, 0, p, v);
        }
    }
    hw_find.sweeps++;
}

/* The encoder a cell belongs to, as a short tag: KNOB1 at columns 8 and 9
 * on PA5 (HW-133 item 6); the others where the unit showed them, on PA0
 * (finder1 and start3c, relayed: clean-br17-encoders); PRESETS on PB7 at
 * columns 11 and 12 (encoders1, relayed: clean-br17-presets). */
static const char *f_tag(u32 col, u32 port, u32 bit)
{
    if (port == 0 && bit == 5 && (col == 8 || col == 9))
        return "K1 ";
    if (port == 0 && bit == 0 && col < 10)
        return col == 0 || col == 1 ? "SEL " : col < 4 ? "ALG " : col < 6 ? "K4 " : col < 8 ? "K3 " : "K2 ";
    if (port == 1 && bit == 7 && (col == 11 || col == 12))
        return "PRE ";
    return "";
}

static void f_draw_line(u32 i)
{
    struct hw_find_line *l = &hw_find.line[i];
    char t[48], *p = t;
    u32 k;

    if (l->kind == F_ADC) {
        /* MASTER is channel 4 (HW-133 item 5); the others by number. */
        if (l->bit == 4) {
            p = put_s(p, "MASTER ");
        } else {
            p = put_s(p, "AD");
            p = put_dec(p, l->bit);
            p = put_s(p, " ");
        }
        p = put_hex(p, l->value, 3);
        if (l->nlevels)
            *p++ = ':';
        for (k = 0; k < l->nlevels; k++) {
            if (k)
                *p++ = ' ';
            p = put_hex(p, l->levels[k], 3);
        }
    } else {
        if (l->kind == F_CELL) {
            p = put_s(p, f_tag(l->col, l->port, l->bit));
            p = put_s(p, "c");
            p = put_dec(p, l->col);
            p = put_s(p, " ");
        } else {
            p = put_s(p, "pin ");
        }
        *p++ = 'P';
        *p++ = f_name[l->port];
        p = put_dec(p, l->bit);
        p = put_s(p, l->value ? " =1 x" : " =0 x");
        p = put_dec(p, l->count);
    }
    *p = 0;
    big_row(F_BIG_Y(i), t, l->fresh ? RGB565(31, 63, 0) : RGB565(31, 63, 31));
}

static void f_small(u32 n)
{
    char t[48], *p = t;
    u32 k;

    switch (n) {
    case 0:
        p = put_s(p, "c1 ");
        p = put_hex(p, hw3.c1_pre, 8);
        p = put_s(p, ">");
        p = put_hex(p, hw3.c1_post, 8);
        p = put_s(p, ">");
        p = put_hex(p, hw3.c1_clr1, 8);
        p = put_s(p, " ");
        p = put_hex(p, C1_CON, 8);
        break;
    case 1:
        p = put_s(p, "sd ");
        p = put_hex(p, hw3.sd_before, 8);
        p = put_s(p, ">");
        p = put_hex(p, hw3.sd_set, 8);
        p = put_s(p, ">");
        p = put_hex(p, hw3.sd_after, 8);
        p = put_s(p, hw3.c1_seen ? " sign" : " NO sign");
        break;
    case 2:
        p = put_s(p, "sweeps/s ");
        p = put_dec(p, hw_find.rate);
        p = put_s(p, " noisy ");
        p = put_dec(p, hw_find.noisy);
        p = put_s(p, " lost ");
        p = put_dec(p, hw_find.dropped);
        p = put_s(p, " on ");
        p = put_dec(p, hw3.count);
        break;
    case 3:
    case 4:
        p = put_s(p, n == 3 ? "PU " : "DIR ");
        for (k = 0; k < F_PORTS; k++) {
            *p++ = f_name[k];
            p = put_hex(p, PORT(f_base[k], n == 3 ? PU : DIR) & 0xFFFFu, 4);
            *p++ = ' ';
        }
        break;
    }
    *p = 0;
    row(F_SMALL_Y + FONT_H * n, t, RGB565(31, 63, 31));
}

static void f_core1(void)
{
    char t[24], *p = t;

    p = put_s(p, "core1 ");
    p = put_dec(p, hw_core1_count);
    *p = 0;
    big_row(F_CORE1_Y, t, hw_core1_count ? RGB565(0, 63, 0) : RGB565(31, 0, 0));
}

/* Never returns. */
void hw_finder(void)
{
    u32 i, n, quiet_end, second, last_sweeps = 0, next_line = 0;

    hw_scan_paused = 1;
    PORT(PA, OUT) &= ~PA_LEDS;
    PORT(PH, OUT) &= ~PH_LEDS;
    SYNC();
    lcd_wait();
    gfx_fill(0, 0, SCREEN_W, SCREEN_H, RGB565(0, 0, 0));
    lcd_send_rows(0, SCREEN_H);
    lcd_wait();
    big_row(2, "FINDER: hands off", RGB565(31, 0, 0));
    lcd_wait();
    for (n = 0; n < 5; n++)
        f_small(n);
    hw_find.learning = 1;
    quiet_end = sb_beacon.beats + HW_FIND_QUIET_MS;
    second = sb_beacon.beats + 1000u;
    for (;;) {
        f_sweep();
        if (hw_find.learning && (int)(sb_beacon.beats - quiet_end) >= 0) {
            hw_find.learning = 0;
            lcd_wait();
            big_row(2, "FINDER: turn one", RGB565(0, 63, 0));
        }
        if ((int)(sb_beacon.beats - second) >= 0) {
            second += 1000u;
            hw_find.rate = hw_find.sweeps - last_sweeps;
            last_sweeps = hw_find.sweeps;
            lcd_wait();
            f_core1();
            lcd_wait();
            f_small(0);
            f_small(2);
            for (i = 0; i < F_LINES; i++)
                if (hw_find.line[i].fresh && sb_beacon.beats - hw_find.line[i].when >= F_HOLD_MS) {
                    hw_find.line[i].fresh = 0;
                    hw_find.line[i].dirty = 1;
                }
            continue;
        }
        /* One changed line a sweep at most, and only once the last
         * transfer has ended, so the sweeps go on while it is sent. */
        if (!lcd_busy()) {
            for (n = 0; n < F_LINES; n++) {
                i = (next_line + n) % F_LINES;
                if (hw_find.line[i].dirty) {
                    hw_find.line[i].dirty = 0;
                    f_draw_line(i);
                    next_line = i + 1;
                    break;
                }
            }
        }
    }
}
#endif

#endif
