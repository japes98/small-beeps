/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * The panel: an ST7789V-family controller on SPI1 (HW-27 to HW-32).
 * Commands go out a byte at a time; pixels go out by DMA straight from the
 * frame buffer, in chunks that SPI1's interrupt chains, so the core is
 * free while a frame is on its way (docs/DESIGN-NOTES.md, M2).
 */

#include "sb.h"
#include "WL82.h"

/* HW-29: CON bit 15 reads 1 when a transfer is done, writing bit 14
 * clears that, bit 13 makes a finished transfer raise source 16. */
#define SPI_DONE  (1u << 15)
#define SPI_CLEAR (1u << 14)
#define SPI_IRQ   (1u << 13)

/* SPI1's own set-up (clock, mode, pins) on the chip is open (Q-6, SR-3);
 * fwtest needs none (HW-29). These are the CON bits that set-up will
 * keep in every write; none yet. */
#define SPI_CON   0u

/* HW-30: PC8 low for a command byte, high for its parameters and for
 * pixels. Only that bit of the port is ever changed. */
#define LCD_DC    (1u << 8)

/* DS (HW-31, HW-32): the commands used. */
#define SWRESET   0x01u
#define SLPOUT    0x11u
#define CASET     0x2Au
#define RASET     0x2Bu
#define RAMWR     0x2Cu
#define MADCTL    0x36u
#define COLMOD    0x3Au

/* Bytes a DMA transfer sends at most: 16 rows. E-5 (HW-29) confirms
 * 480-byte transfers; how long one may be on the chip is asked in SR-3,
 * so a whole frame goes as 15 of these. */
#define ROW_BYTES (SCREEN_W * 2u)
#define CHUNK     (16u * ROW_BYTES)

/* A frame on its way: the next byte to send and how many are left, set
 * by lcd_send_rows and moved on by lcd_spi_done. */
static const u8 *volatile dma_next;
static volatile u32 dma_left;
/* 1 while a transfer started without the interrupt may still be going. */
static volatile u32 dma_polled;
static u32 frame_start;

static void dc_low(void)  { JL_PORTC->OUT &= ~LCD_DC; }
static void dc_high(void) { JL_PORTC->OUT |= LCD_DC; }

static void send_byte(u32 b)
{
    JL_SPI1->BUF = b;
    while (!(JL_SPI1->CON & SPI_DONE))
        ;
    JL_SPI1->CON = SPI_CON | SPI_CLEAR;
}

/* Waits until no transfer is on its way, so the data/command line may
 * change (HW-30: its level when a transfer starts decides it). A chained
 * frame ends in lcd_spi_done. This spins rather than idling: the last
 * chunk's interrupt could come between the test and an idle, which would
 * then sleep until the next tick (it did, once a frame, in the flood
 * test). Only a command that follows a frame still going out waits. */
void lcd_wait(void)
{
    while (dma_left)
        ;
    if (dma_polled) {
        while (dma_polled && !(JL_SPI1->CON & SPI_DONE))
            ;
        JL_SPI1->CON = SPI_CON | SPI_CLEAR;
        dma_polled = 0;
    }
}

void lcd_command(u8 command, const u8 *params, u32 count)
{
    lcd_wait();
    dc_low();
    send_byte(command);
    dc_high();
    while (count--)
        send_byte(*params++);
}

static void start_chunk(void)
{
    u32 n = dma_left < CHUNK ? dma_left : CHUNK;

    JL_SPI1->ADR = (u32)dma_next;
    dma_next += n;
    sb_beacon.chunks++;
    JL_SPI1->CNT = n;
}

/* Source 16: a chunk of a chained frame is done. Send the next, or end
 * the frame. Only chained chunks raise it: a polled transfer starts with
 * bit 13 clear, which raises nothing (HW-59; before fwtest 0.2.0 it did,
 * and this handler acknowledged it: DESIGN-NOTES.md, M4). */
void lcd_spi_done(void)
{
    u32 n = dma_left < CHUNK ? dma_left : CHUNK;

    dma_left -= n;
    if (dma_left) {
        JL_SPI1->CON = SPI_CON | SPI_CLEAR | SPI_IRQ;
        start_chunk();
    } else {
        JL_SPI1->CON = SPI_CON | SPI_CLEAR;
        sb_beacon.frame_ticks = sb_now() - frame_start;
        sb_beacon.frames++;
    }
}

/* Sends rows first to first + rows - 1 of the frame buffer to the same
 * rows of the panel (HW-31: column and row address set, then memory
 * write, high byte first; sb_fb holds each pixel that way round). Up to
 * one chunk goes as one transfer whose end is polled by the next
 * lcd_wait; more go as a chain of chunks driven by source 16. Returns
 * once the last transfer has started. */
void lcd_send_rows(u32 first, u32 rows)
{
    u32 last = first + rows - 1, bytes = rows * ROW_BYTES;
    u8 cols[4] = { 0, 0, (SCREEN_W - 1) >> 8, (SCREEN_W - 1) & 0xFF };
    u8 lines[4] = { first >> 8, first & 0xFF, last >> 8, last & 0xFF };

    frame_start = sb_now();
    lcd_command(CASET, cols, 4);
    lcd_command(RASET, lines, 4);
    lcd_command(RAMWR, 0, 0);
    dma_next = (const u8 *)&sb_fb[first * SCREEN_W];
    if (bytes <= CHUNK) {
        dma_polled = 1;
        JL_SPI1->CON = SPI_CON | SPI_CLEAR;
        JL_SPI1->ADR = (u32)dma_next;
        sb_beacon.chunks++;
        JL_SPI1->CNT = bytes;
        return;
    }
    dma_left = bytes;
    JL_SPI1->CON = SPI_CON | SPI_CLEAR | SPI_IRQ;
    start_chunk();
}

/* Since M8a: a rectangle of the frame buffer, x to x + w - 1 by y to
 * y + h - 1, to the same place on the panel (HW-31's column and row
 * address set bound the memory write to it). The frame buffer's rows are
 * apart, so the rectangle is copied, once the last transfer is done, into
 * a staging buffer and sent from there as one polled transfer: at most
 * CHUNK bytes (a live part: an operator's level, the envelope's dot). */
static u16 rect_buf[CHUNK / 2] __attribute__((aligned(4)));

void lcd_send_rect(u32 x, u32 y, u32 w, u32 h)
{
    u8 cols[4] = { x >> 8, x & 0xFF, (x + w - 1) >> 8, (x + w - 1) & 0xFF };
    u8 lines[4] = { y >> 8, y & 0xFF, (y + h - 1) >> 8, (y + h - 1) & 0xFF };
    u32 r, i, n = 0;

    if (!w || !h || w * h * 2 > CHUNK || x + w > SCREEN_W || y + h > SCREEN_H)
        return;
    lcd_wait();
    for (r = 0; r < h; r++) {
        const u16 *p = &sb_fb[(y + r) * SCREEN_W + x];
        for (i = 0; i < w; i++)
            rect_buf[n++] = p[i];
    }
    frame_start = sb_now();
    lcd_command(CASET, cols, 4);
    lcd_command(RASET, lines, 4);
    lcd_command(RAMWR, 0, 0);
    dma_polled = 1;
    JL_SPI1->CON = SPI_CON | SPI_CLEAR;
    JL_SPI1->ADR = (u32)rect_buf;
    sb_beacon.chunks++;
    JL_SPI1->CNT = n * 2;
}

/* The controller's start: a software reset, sleep out, 16-bit pixels, and
 * the scan order. The display stays off until the first frame is in
 * (main sends DISPON). Delays from HW-32 and DS pages 163 and 184, each
 * waited on the tick, so they hold on the chip too. */
void lcd_init(void)
{
    /* DS page 215: MY = MX = MV = 0 (rows top to bottom, columns left to
     * right, not exchanged), ML = 0, RGB order (bit 3 clear), MH = 0. */
    static const u8 madctl = 0x00;
    /* DS page 224: 0x55, 65K colours and 16 bits a pixel. */
    static const u8 colmod = 0x55;

    lcd_command(SWRESET, 0, 0);
    /* 5 ms before the next command; 120 ms before sleep out when the
     * reset came in sleep mode, which it does after power-up. */
    sb_wait_ms(120);
    lcd_command(SLPOUT, 0, 0);
    sb_wait_ms(5);
    lcd_command(COLMOD, &colmod, 1);
    lcd_command(MADCTL, &madctl, 1);
}
