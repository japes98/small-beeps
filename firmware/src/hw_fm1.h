/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * The FM-1 hardware build (SB_HW_FM1, hw_fm1.c; R-HW-1): the panel's
 * bring-up before the copy to RAM, the start-up's bands, and the halt
 * screen, all polled and in the window; and TIMER0 as the build's one
 * timer (main.c).
 */

#ifndef HW_FM1_H
#define HW_FM1_H

#include "sb.h"

#if defined(SB_HW_FM1)
#if defined(SB_ENGINE_EXTERNAL) || defined(SB_NO_START_SCREENS)
#error "SB_HW_FM1 is the base's own start-up on a unit: not with SB_ENGINE_EXTERNAL or SB_NO_START_SCREENS"
#endif
#if defined(SB_PROBE_RETURN) || defined(SB_PROBE_LIGHT) || defined(SB_PROBE_PANEL)
#error "SB_HW_FM1 is not a probe: build it without SB_PROBE_*"
#endif

void hw_early(void);
/* The block r0 pointed at when m-bootloader called the entry, and the
 * chip key at its +12 (HW-112, HW-126), kept by sb_start. */
extern u32 hw_boot_block, hw_boot_key;
void hw_fill(u32 x, u32 y, u32 w, u32 h, u32 colour);
void hw_band(u32 n);
void hw_halt_screen(void);
void hw_rt_led_window(void);

/* TIMER0, the build's one timer: CON 0x1 counts up from CNT to PRD,
 * from the 60 MHz low-speed bus, prescaler setting 0 (HW-125, HW-119;
 * fwtest's TIMER0 counts 24 MHz, HW-48): an interrupt every HW_SLOT_PRD
 * counts, 83.3 us, one scan slot; twelve make the 1 ms tick. */
#define HW_SLOT_CON   0x1u
#define HW_SLOT_PRD   5000u
#define HW_SLOTS_TICK 12u
/* sb_now()'s 24 MHz units in one slot, and per count: 2000 and 2 / 5. */
#define HW_SLOT_UNITS 2000u
void hw_slot(void) __attribute__((interrupt("")));

/* start3 (hw_start3.c): the matrix, the ports, the ADC, the flash round
 * trip and the store's counter, and core 1, each in rows of its own on the
 * test screen: these, clear of start2's bands (rows 64 to 175 while the
 * start-up draws them), its event line (104 to 119) and the beat (200). */
#define HW3_GRID_Y    40u    /* a title row, then PA5 to PA8 */
#define HW3_PORTS_Y   84u
#define HW3_ADC_Y     124u   /* two rows */
#define HW3_STORE_Y   142u
#define HW3_CORE1_Y   152u
#define HW3_WIN_Y     180u
#define HW3_FLASH_Y   190u
/* start3b: the tick's row (before the test screen only: its beat is drawn
 * there after) and the last step reached, on every screen from band 2 on
 * (hw_step). */
#define HW3_TICK_Y    200u
#define HW3_STEP_Y    216u
/* SB_HW_HOLD (the unit's build): the start-up rows and the round trip's
 * LEDs held this long before interrupts go on, and the tick watched for
 * HW_WATCH_MS after the store's step and after core 1's release. */
#if defined(SB_TEST_SHORT_HOLD)
#define HW_HOLD_MS    200u
#else
#define HW_HOLD_MS    5000u
#endif
#define HW_WATCH_MS   300u
#define HW3_ADC_CHANNELS 12u
struct hw_start3 {
    u32 win_con, win_base, win_key;   /* the window's registers before the take */
    u32 tried, back, idle_timeouts;   /* the round trip: begun, came back */
    u32 id, status1, status2;         /* read in the round trip */
    u32 stored, count;                /* the store's step, the start-up count */
    int get_result, put_result;
    u8 grid[16];                      /* rows PA5-PA8 closed, by column word */
    u32 adc[HW3_ADC_CHANNELS];
    u32 c1_pre, c1_post, c1_word, c1_fn; /* C1_CON before and after the release, the start word read back, the loop's address */
    /* start3c, core 1's release in HW-135's order (hw_core1_start): */
    u32 sd_before, sd_set, sd_after;  /* SYS_DIV read first, after bit 3 set, after it is put back */
    u32 c1_clr1;                      /* C1_CON after bit 1 cleared (c1_post: after bit 3 set) */
    u32 c1_seen, c1_wait_ms;          /* core 1's flag seen; the wait, ms (HW_C1_WAIT_MS: timed out) */
    u32 c1_at;                        /* the beat of the release */
    u32 x2_before[16], x2_after[16];           /* corex2 words 0x80-0x8F before, and a second after */
    u32 count1;                       /* hw_core1_count a second after */
};
extern struct hw_start3 hw3;
extern volatile u32 hw_core1_count, hw_core1_flag, hw_scan_paused;
#define HW_C1_WAIT_MS 100u
void hw_core1_screen(void);
void hw_round_trip(void);
void hw_store_counter(void);
void hw_adc_start(void);
void hw_core1_start(void);
void hw_rows_all(void);
void hw_refresh(u32 second);
extern volatile u32 hw_slots;
void hw_step(const char *text);
void hw_hold(void);
void hw_watch(u32 ms);
void hw_rows_start(void);
#if defined(SB_HW_FINDER)
void hw_finder(void) __attribute__((noreturn));
#endif
#if defined(SB_HW_AUDIO1)
/* audio1 (hw_audio.c, clean-br17-audio1): the audio probe. Its line on the
 * test screen (scale 2), between core 1's row and the window's; the page's
 * hold; how long the tone runs before the "tone on" registers are read. */
#define HW_AUD_Y      160u
#define HW_AUD_REGS   22u
#if defined(SB_TEST_SHORT_HOLD)
#define HW_AUD_PAGE_MS   1000u
#define HW_AUD_SETTLE_MS 300u
#else
#define HW_AUD_PAGE_MS   10000u
#define HW_AUD_SETTLE_MS 1500u
#endif
struct hw_audio {
    u32 regs[2][HW_AUD_REGS];   /* read at main's start, and with the tone on */
    u32 regs_read;              /* the second set read */
    u32 started;                /* the beat the output started (0: not yet) */
    u32 seq;                    /* odd while the handler writes n0 to t1 */
    u32 n0_set, n0, t0, n1, t1; /* sb_audio.blocks and sb_now() at the base and the latest half */
    u32 halves, units, fps10;   /* main's measure: halves and sb_now units since the base, frames a second x 10 */
    u32 master, gain, tone_on;  /* MASTER (0-1023), the tone's gain now, PLAY's toggle */
    u32 storm;                  /* the beat the guard stopped the output (0: never) */
    u32 flips, pend;            /* main's polls on the page: CON0 bit 15 changed, CON2 bit 7 seen set */
};
extern struct hw_audio hw_aud;
void hw_audio_boot(void);
void hw_audio_start(void);
void hw_audio_toggle(void);
void hw_audio_line(void);
void hw_audio_page(void);
#endif
#endif

#endif
