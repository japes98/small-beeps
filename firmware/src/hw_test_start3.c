/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * The test build's start-up bring-up (round 2, clean-r2-cleanup): what was hw_start3.c's and the release
 * doesn't need (the round trip, the store's counter, core 1, the holds, the test screen's rows and
 * sweeps), built only with SB_HW_TEST (owner-only, never published); docs/DESIGN-NOTES.md says why.
 */

#include "sb.h"
#include "hw_fm1.h"
#include "input.h"
#include "store.h"
#include "WL82.h"
#include "hw_start3_int.h"

#if defined(SB_HW_FM1) && defined(SB_HW_TEST)

/* audio3: core 1's flag and count alone in a 64-byte block, so nothing
 * core 0 writes shares their cache line (hw_fm1.h). */
struct hw_core1_blk hw_core1_blk __attribute__((aligned(64)));
void hw_core1_loop(void);
static void draw_store(void);
static void draw_win(void);
static void draw_flash(void);

static char *put_hex(char *p, u32 v, u32 digits)
{
    static const char hex[] = "0123456789ABCDEF";

    while (digits--)
        *p++ = hex[v >> 4 * digits & 0xF];
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

__attribute__((unused))   /* audio11: the SARADC's service and the large area instead */
static void adc_all(void)
{
    u32 ch, n;

    for (ch = 0; ch < HW3_ADC_CHANNELS; ch++) {
        /* PC0 and PC1 are ALNK0's master and bit clocks in group A
         * (HW-141): not sampled while audio1 may drive them. */
        if (ch == 6 || ch == 7) {
            hw3.adc[ch] = 0xFFFFu;
            continue;
        }
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

/* audio8: the scan paused and held, the LED lines low and no column
 * (0xFFFF latched), so nothing of the scan's moves a port A or H pin
 * while audio8 samples pins. */
void hw_scan_hold(void)
{
    hw_scan_paused = 1;
    PORT(PA, OUT) &= ~PA_LEDS;
    REG(0x000501C0u + OUT) &= ~PH_LEDS;
    SYNC();
    shift_word(0xFFFFu);
}

void hw_scan_resume(void)
{
    shift_word(0xFFFFu);
    input_scan_restart();
    hw_scan_paused = 0;
}

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
    hw3.sd_after = SYS_DIV;
    hw3.c1_at = sb_beacon.beats;
    hw_step(hw3.c1_seen ? "core 1: its sign seen" : "core 1: no sign (timed out)");
}

/* SB_HW_HOLD with SB_HW_CORE1_SYSDIV: core 1's screen, a second or more
 * after the release, held 2 x HW_HOLD_MS: every value the release read,
 * the corex2 words before and a second after (yellow where they changed),
 * core 1's counter. */


/* SB_HW_HOLD: a second or more after the release, the corex2 words and
 * core 1's counter sampled again; with SB_HW_CORE1_SYSDIV, core 1's screen. */
void hw_core1_screen(void)
{
#if defined(SB_HW_TEST)
    u32 i;

    while (sb_beacon.beats - hw3.c1_at < 1000u)
        ;
    for (i = 0; i < 16; i++)
        hw3.x2_after[i] = COREX2_WORD(i);
    hw3.count1 = hw_core1_count;
#endif
}

/* --- The rows ------------------------------------------------------------- */

__attribute__((unused))   /* audio11: the SARADC's service and the large area instead */
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

__attribute__((unused))   /* audio11: the SARADC's service and the large area instead */
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

/* Each step of the start-up, numbered, in the step row as it begins: the
 * row left showing is the step that didn't finish. One row is one
 * transfer whose end is polled (lcd.c), so it is drawn with interrupts off
 * or stopped too. */
/* The step row's text now (audio12: the instrument's start shows why the
 * route didn't come up). */
const char *hw_step_now(void)
{
    return step_text;
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
#if defined(SB_HW_TEST)
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
    if (!hw_hold_sweeps) {
        sweep();
        /* audio11: the SARADC's service (hw_audio.c) converts the sweep's
         * channels one a conversion from TIMER0's slot; the rows show its
         * last readings. */
    }
    if (hw_hold_screen)
        return;
    draw_adc();
    if (second) {
        draw_core1();
#if defined(SB_HW_TEST)
        if (hw_aud.started)
            hw_audio_line();
#endif
    }
}


#endif
