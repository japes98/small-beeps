/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * hw_start3.c's and hw_test_start3.c's shared names (round 2, clean-r2-cleanup): the macros both use,
 * and what each part takes from the other. Not for any other file.
 */

#ifndef HW_START3_INT_H
#define HW_START3_INT_H


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
#define MARK_TAKING()  led_mark(0xFBFFu, PA_LED2, 0)          /* PLAY */
#define MARK_TAKEN()   led_mark(0xF7FEu, 0, 1u << 9)          /* OCT- */
#define MARK_GIVING()  led_mark(0xEFFDu, 0, 1u << 9)          /* OCT+ */

/* The row holds 40 characters at scale 1: "step n: " and as much of the
 * text as fits, never more (a longer text once overran t, clean-br17-audio4). */
#define STEP_CHARS 40u

/* A spin, not idle, for ms beats, the tick's row drawn every 100 beats; if
 * the beats stand still for about HW_STALL_SPINS turns, the row turns red
 * and is drawn again each time, for ever unless they move. */
#define HW_STALL_SPINS 20000000u

char *put_s(char *p, const char *s);
char *put_dec(char *p, u32 v);
void row(u32 y, const char *text, u32 colour);
void rt_cs_down(void);
void rt_cs_up(void);
u32 spi_byte(u32 b);
void flash_take(void);
void flash_give(u32 irq_on);
void draw_step(void);
void hw_step(const char *text);

extern const char *step_text;

#endif
