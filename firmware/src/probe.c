/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * Test builds only. tools/perf.py builds the firmware with each of
 * SB_PROBE_SLOW, SB_PROBE_BIG, SB_PROBE_LOADED and SB_PROBE_STACK defined,
 * and checks that the performance gates fail the first three and that the
 * stack's high-water mark sees the last (R-PERF-3, R-PERF-5). tools/fw-suite.py builds it
 * with each of SB_TEST_FAULT, SB_TEST_STRAY and SB_TEST_BADINSN, which go
 * wrong on purpose once interrupts are on (R-IRQ-3, R-IRQ-4), and with
 * SB_TEST_FLOOD, which keeps the panel busy (R-LCD-5), SB_TEST_LEDS,
 * which sets every LED to its own brightness (R-LED-2), and
 * SB_TEST_LED_SHOW, whose scan times when it first drives an LED just set
 * (input.c; R-LED-3), and SB_TEST_UNDERRUN, whose engine is late for a
 * block on purpose (R-AUD-3), and SB_TEST_MIDI_BURST, which queues more
 * MIDI out than the queue holds, in one block (R-MIDIOUT-4). Since
 * clean-1027 tools/seams_suite.py builds it with SB_TEST_OWNBASE, which
 * tools/build.sh must refuse (R-BUILD-3). The firmware itself is built
 * with none, and then nothing here is compiled.
 */

#include "sb.h"
#include "input.h"
#include "audio.h"
#include "fm.h"
#include "WL82.h"

#if defined(SB_PROBE_STACK)
static volatile u32 probe_sink;
#endif

#if defined(SB_PROBE_SLOW)
/* Extra work on every heartbeat beat: the speed gate must catch it. */
void sb_probe_slow(void)
{
    volatile u32 i;

    for (i = 0; i < 20; i++)
        ;
}
#endif

#if defined(SB_PROBE_LOADED)
/* Extra work for each voice core 0 renders, each audio block (fm_play.c): none
 * at rest, so only the loaded measure's gates must catch it. */
void sb_probe_loaded(void)
{
    volatile u32 i;

    for (i = 0; i < 1000; i++)
        ;
}
#endif

#if defined(SB_PROBE_BIG)
/* More code (a 1 KiB table among the constants), more static RAM (256
 * bytes of zeroed data), a deeper stack (512 bytes, every word written
 * with a non-zero value) and more start-up work (the frame written
 * PROBE_STARTUP_ROUNDS times): each budget must catch its own. The
 * start-up count moves by a few thousand instructions from one image to
 * the next, so since clean-1028 the extra work is well past that: with
 * BR-12's store change one round (about 750 instructions) no longer
 * showed. */
#define PROBE_STARTUP_ROUNDS 64u
static const u32 probe_table[256] = { 1 };
static volatile u32 probe_ram[64];

static void __attribute__((noinline)) probe_stack(void)
{
    volatile u32 frame[128];
    u32 i;

    for (i = 0; i < 128; i++)
        frame[i] = i + 1;
    probe_ram[0] = frame[127];
}

void sb_probe_big(void)
{
    u32 r;

    for (r = 0; r < PROBE_STARTUP_ROUNDS; r++)
        probe_stack();
    probe_ram[1] = probe_table[sb_beacon.beats & 255];
}
#endif

#if defined(SB_PROBE_STACK)
/* A known amount of stack: a 1 KiB frame, written with zeros (which RAM
 * already holds in fwtest, so only the fill pattern can show them) and
 * read back. The high-water mark must be at least 1024 bytes. */
static void __attribute__((noinline)) probe_zero_frame(void)
{
    volatile u32 frame[256];
    u32 i, sum = 0;

    for (i = 0; i < 256; i++)
        frame[i] = 0;
    for (i = 0; i < 256; i++)
        sum += frame[i];
    probe_sink = sum;
}

void sb_probe_stack(void)
{
    probe_zero_frame();
}
#endif

#if defined(SB_TEST_FAULT)
/* Overruns main's stack: a frame as big as the whole stack, written, so
 * the stack's guard word is overwritten. The next tick must find it and
 * halt with "HALT stack 001". */
static volatile u32 test_sink;

static void __attribute__((noinline)) test_overrun(void)
{
    volatile u32 frame[512];
    u32 i;

    _Static_assert(sizeof frame >= 0x800, "the frame covers main's whole stack");
    for (i = 0; i < 512; i++)
        frame[i] = i;
    test_sink = frame[0];
}

void sb_test_fault(void)
{
    test_overrun();
}
#endif

#if defined(SB_TEST_STRAY)
/* An interrupt nothing handles: software interrupt 7 (source 127, HW-19),
 * enabled (HW-20) and raised (HW-23). It must halt with "HALT stray 07f". */
void sb_test_stray(void)
{
    (&q32DSP(0)->ICFG00)[127 / 8] = (1u | 1u << 1) << 4 * (127 % 8);
    q32DSP(0)->ILAT_SET = 1u << 7;
}
#endif

#if defined(SB_TEST_BADINSN)
/* An instruction the emulated CPU cannot decode. fwtest stops the run with
 * its own fault outcome before any handler of ours runs: a limit of the
 * harness, not something the firmware reports (SR-1). */
void sb_test_badinsn(void)
{
    __asm__ volatile(".short 0xffff\n\t.short 0xffff");
}
#endif

#if defined(SB_TEST_FLOOD)
/* Whole frames back to back, for ever, once the test screen is up: every
 * tick of the run comes while a frame is being sent or set up, and must
 * keep its timing (R-LCD-5). Core 0 never waits here, so fwtest's
 * captures are exact. */
void sb_test_flood(void)
{
    for (;;) {
        lcd_send_rows(0, SCREEN_H);
        lcd_wait();
    }
}
#endif

#if defined(SB_TEST_LEDS)
/* Every LED at its own brightness: LED n at (n mod 9) eighths of full,
 * as levels 0 to 255 round them (input.h), so each of the 9 steps shows
 * on several LEDs and every LED on some step. */
void sb_test_leds(void)
{
    u32 n;

    for (n = 0; n < INPUT_LEDS; n++)
        input_led(n, n % 9 * INPUT_LED_FULL / 8);
}
#endif

#if defined(SB_TEST_UNDERRUN)
/* The engine, late on purpose for one block in 64: it runs on
 * for about 1.2 blocks (420 000 instructions at one a cycle) after
 * filling it, so the next half finishes first. Each must be counted and
 * reported once, "AUDIO UNDERRUN nnnn", and the output must go on. */
void sb_test_late_block(s32 *out, u32 frames)
{
    volatile u32 i;

    fm_block(out, frames);
    if (sb_audio.blocks % 64 == 32)
        for (i = 0; i < 105000; i++)
            ;
}
#endif

#if defined(SB_TEST_MIDI_BURST)
#include "midi.h"
#include "midi_out.h"

/* In one block, about a second in: 16 note ons, 20 moves of one
 * controller and 10 pitch bends (which merge), 16 more note ons (past the
 * queue's room for anything but note offs), then all 32 note offs (past
 * even the reserve). tools/fw-suite.py checks that every note sent ends
 * and that the panel's keys are sent again after. */
#define BURST_BLOCK 700u

void sb_test_midi_burst(void)
{
    u32 n;

    if (sb_audio.blocks != BURST_BLOCK)
        return;
    for (n = 0; n < 16; n++)
        midi_out_channel(MIDI_NOTE_ON, 60 + n, 100);
    for (n = 0; n < 20; n++)
        midi_out_channel(MIDI_CC, 16, n * 6);
    for (n = 0; n < 10; n++)
        midi_out_channel(MIDI_BEND, n * 1000 & 0x7Fu, n * 1000 >> 7);
    for (n = 16; n < 32; n++)
        midi_out_channel(MIDI_NOTE_ON, 60 + n, 100);
    for (n = 0; n < 32; n++)
        midi_out_channel(MIDI_NOTE_ON, 60 + n, 0);
}
#endif

#if defined(SB_TEST_OWNBASE)
/* A store that writes back into the register it stores (pre-increment):
 * tools/build.sh must refuse the build (tools/ownbase.pl). Never run. */
void sb_test_ownbase(void)
{
    __asm__ volatile("[++r1=4] = r1" : : : "r1", "memory");
}
#endif

#if defined(SB_PROBE_PANEL)
/* Phase B's panel probe (BR-17; docs/DESIGN-NOTES.md, clean-br17-panel;
 * R-PROBE-3). crt0.S's _start switches to a stack of our own and calls
 * this before anything else; it brings the panel up as HW-115 gives it,
 * draws four bars and a square, lights the backlight (HW-116), holds for
 * about 5 s, puts the backlight out, switches SPI1 off and returns. It
 * runs before sb_start, so it and everything it calls stay in the window
 * (.boot.text), and it uses no data, no constants in memory and no RAM
 * but its stack. Registers by address, from HARDWARE-SPEC: SPI1 HW-28,
 * the ports and JL_IOMAP HW-56. Every byte goes through BUF (HW-29,
 * HW-115). */
#define PP_BOOT __attribute__((section(".boot.text"), noinline))
#define PP_REG(a) (*(volatile u32 *)(a))
#define PP_PA_OUT PP_REG(0x00050000)
#define PP_PA_DIR PP_REG(0x00050008)
#define PP_PC_OUT PP_REG(0x00050080)
#define PP_PC_DIR PP_REG(0x00050088)
#define PP_IOMAP_CON1 PP_REG(0x00051020)
#define PP_SPI1_CON PP_REG(0x00011D00)
#define PP_SPI1_BAUD PP_REG(0x00011D04)
#define PP_SPI1_BUF PP_REG(0x00011D08)
#define PP_CS (1u << 7)                 /* PC7, the chip select, active low */
#define PP_DC (1u << 8)                 /* PC8: 0 command, 1 data */
#define PP_SPI_PINS ((1u << 8) | (1u << 9) | (1u << 10))
#define PP_BACKLIGHT (1u << 2)          /* PA2, active low (HW-116) */
/* Two-instruction passes of pp_wait in a millisecond at HW-119's 360 MHz,
 * one instruction a cycle; longer if a taken branch costs more. */
#define PP_PASSES_MS 180000u

void sb_probe_panel(void) PP_BOOT;

static void PP_BOOT pp_wait_ms(u32 ms)
{
    u32 n = ms * PP_PASSES_MS;
    __asm__ volatile("1:\n\t%0 += -1\n\tif (%0 != 0) goto 1b" : "+r"(n));
}

/* One byte through BUF: wait for CON bit 15, clear it with bit 14. */
static void PP_BOOT pp_byte(u32 b)
{
    PP_SPI1_BUF = b;
    while (!(PP_SPI1_CON & 0x8000u))
        ;
    PP_SPI1_CON |= 0x4000u;
}

/* A command byte: PC7 low, PC8 low for it, then PC8 high for its data. */
static void PP_BOOT pp_cmd(u32 c)
{
    PP_PC_OUT &= ~PP_CS;
    PP_PC_OUT &= ~PP_DC;
    pp_byte(c);
    PP_PC_OUT |= PP_DC;
}

static void PP_BOOT pp_end(void)
{
    PP_PC_OUT |= PP_CS;
}

static void PP_BOOT pp_pair(u32 a, u32 b)
{
    pp_byte(a >> 8);
    pp_byte(a & 0xFF);
    pp_byte(b >> 8);
    pp_byte(b & 0xFF);
}

/* A w x h rectangle at (x, y) in one RGB565 colour, high byte first
 * (HW-115 step 4). */
static void PP_BOOT pp_fill(u32 x, u32 y, u32 w, u32 h, u32 colour)
{
    u32 n;
    pp_cmd(0x2A);
    pp_pair(x, x + w - 1);
    pp_end();
    pp_cmd(0x2B);
    pp_pair(y, y + h - 1);
    pp_end();
    pp_cmd(0x2C);
    for (n = w * h; n; n--) {
        pp_byte(colour >> 8);
        pp_byte(colour & 0xFF);
    }
    pp_end();
}

void sb_probe_panel(void)
{
    /* HW-115 step 1: PC7 an output driven high; PC8 to PC10 outputs
     * driven low; SPI1 on pin group B. No pull or drive is set. */
    PP_PC_OUT |= PP_CS;
    PP_PC_DIR &= ~PP_CS;
    PP_PC_OUT &= ~PP_SPI_PINS;
    PP_PC_DIR &= ~PP_SPI_PINS;
    PP_IOMAP_CON1 |= 1u << 4;
    /* Step 2: BAUD 4, then CON 0x4021 (on, the pending flag cleared). */
    PP_SPI1_BAUD = 4;
    PP_SPI1_CON = 0x4021;
    /* Step 3. */
    pp_cmd(0x01);                       /* software reset */
    pp_end();
    pp_wait_ms(150);
    pp_cmd(0x11);                       /* sleep out */
    pp_end();
    pp_wait_ms(120);
    pp_cmd(0x3A);                       /* 16-bit pixels */
    pp_byte(0x55);
    pp_end();
    pp_cmd(0x36);
    pp_byte(0x00);
    pp_end();
    pp_cmd(0x21);                       /* inversion on */
    pp_end();
    pp_cmd(0x13);                       /* normal display */
    pp_end();
    pp_fill(0, 0, 240, 240, 0x0000);
    pp_cmd(0x29);                       /* display on */
    pp_end();
    PP_PA_OUT &= ~PP_BACKLIGHT;         /* the backlight on (HW-116) */
    PP_PA_DIR &= ~PP_BACKLIGHT;
    /* The picture: bars red, green, blue and white from the left, and a
     * yellow square in the top-left corner (0, 0). */
    pp_fill(0, 0, 60, 240, 0xF800);
    pp_fill(60, 0, 60, 240, 0x07E0);
    pp_fill(120, 0, 60, 240, 0x001F);
    pp_fill(180, 0, 60, 240, 0xFFFF);
    pp_fill(0, 0, 40, 40, 0xFFE0);
    pp_wait_ms(5000);
    /* Out again: the backlight an input (dark), SPI1 off (HW-119). */
    PP_PA_DIR |= PP_BACKLIGHT;
    PP_SPI1_CON = 0;
}
#endif
