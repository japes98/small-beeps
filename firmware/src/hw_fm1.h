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
#if defined(SB_HW_AUDIO8) && !defined(SB_HW_AUDIO1)
#error "SB_HW_AUDIO8 builds on audio1's probe: build it with SB_HW_AUDIO1"
#endif
#if defined(SB_HW_AUDIO9) && !defined(SB_HW_AUDIO8)
#error "SB_HW_AUDIO9 builds on audio8: build it with SB_HW_AUDIO8"
#endif
#if defined(SB_HW_AUDIO10) && !defined(SB_HW_AUDIO9)
#error "SB_HW_AUDIO10 builds on audio9: build it with SB_HW_AUDIO9"
#endif
#if defined(SB_HW_AUDIO11) && !defined(SB_HW_AUDIO10)
#error "SB_HW_AUDIO11 builds on audio10: build it with SB_HW_AUDIO10"
#endif
#if defined(SB_HW_AUDIO12) && !defined(SB_HW_AUDIO11)
#error "SB_HW_AUDIO12 builds on audio11: build it with SB_HW_AUDIO11"
#endif
#if defined(SB_HW_AUDIO13) && !defined(SB_HW_AUDIO12)
#error "SB_HW_AUDIO13 builds on audio12: build it with SB_HW_AUDIO12"
#endif
#if defined(SB_HW_AUDIO14) && !defined(SB_HW_AUDIO13)
#error "SB_HW_AUDIO14 builds on audio13: build it with SB_HW_AUDIO13"
#endif
/* U3-U (clean-br17-u3u): the USB MIDI device on the unit, for the owner's
 * flash only (R-USB-1: the test product ID; published builds keep USB
 * off). Built on audio14, with the device itself (SB_USB_MIDI). */
#if defined(SB_HW_U3U) && !(defined(SB_HW_AUDIO14) && defined(SB_USB_MIDI))
#error "SB_HW_U3U builds on audio14 with the USB device: build it with SB_HW_AUDIO14 and SB_USB_MIDI"
#endif
#if defined(SB_HW_PCM16) && !defined(SB_HW_AUDIO8)
#error "SB_HW_PCM16 is audio8's unit tone: build it with SB_HW_AUDIO8"
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
#if defined(SB_HW_AUDIO1)
/* audio3 (clean-br17-audio3): core 1's flag and count in a block of their
 * own, 64 bytes on a 64-byte boundary, so no store of core 0's shares a
 * cache line with them (Q-18); hw_core1.S writes them by the block. */
struct hw_core1_blk {
    volatile u32 flag, count, pad[14];
};
extern struct hw_core1_blk hw_core1_blk;
#define hw_core1_flag  (hw_core1_blk.flag)
#define hw_core1_count (hw_core1_blk.count)
extern volatile u32 hw_scan_paused;
#else
extern volatile u32 hw_core1_count, hw_core1_flag, hw_scan_paused;
#endif
extern volatile u32 hw_hold_screen, hw_hold_sweeps; /* audio10's holds (hw_start3.c); 0 otherwise */
#define HW_C1_WAIT_MS 100u
void hw_core1_screen(void);
void hw_round_trip(void);
void hw_store_counter(void);
void hw_adc_start(void);
void hw_core1_start(void);
void hw_rows_all(void);
void hw_refresh(u32 second);
extern volatile u32 hw_slots;
#if defined(SB_TEST_NOW_RACE)
/* The test build's check that sb_now() never goes back (main.c). */
struct hw_now_test {
    u32 done, runs;
    u32 backs[5];               /* by the point the slot's time-keeping came at (1 to 4) */
};
extern struct hw_now_test hw_now_test;
#endif
void hw_step(const char *text);
void hw_hold(void);
void hw_watch(u32 ms);
void hw_rows_start(void);
#if defined(SB_HW_REPORT)
/* The report log (hw_report.c, clean-br17-report1): fixed records of
 * HW_LOG_REC bytes in a ring of HW_LOG_SECTORS sectors ending at the app
 * area's end, 0x93FFF (HW-80), past the image, so an install never writes
 * it (HW-110) and a start never does (HW-112): the one definition of where
 * it is. Each sector is erased before its first record (the unit's flash
 * there holds older data). Since audio7 (layout 6) a record is 4096
 * bytes, a sector each, 96 in the ring of 96 sectors; layouts 3 to 5 were
 * 2048 bytes, 1 and 2 1024 (audio5's ring 64 sectors, report1's 32). The
 * ring's first read finds records of every size, so the numbers go on. */
#define HW_LOG_SECTORS 96u
#define HW_LOG_END     0x94000u
#define HW_LOG_BASE    (HW_LOG_END - HW_LOG_SECTORS * 4096u)
#define HW_LOG_REC     4096u
#define HW_LOG_SLOTS   (HW_LOG_SECTORS * 4096u / HW_LOG_REC)
#define HW_LOG_MAGIC   0x4C524253u          /* "SBRL" */
#if defined(SB_HW_U3U)
#define HW_LOG_LAYOUT  14u                  /* tools/report_decode.py's FIELDS[14] */
#elif defined(SB_HW_AUDIO14)
#define HW_LOG_LAYOUT  13u                  /* tools/report_decode.py's FIELDS[13] */
#elif defined(SB_HW_AUDIO13)
#define HW_LOG_LAYOUT  12u                  /* tools/report_decode.py's FIELDS[12] */
#elif defined(SB_HW_AUDIO12)
#define HW_LOG_LAYOUT  11u                  /* tools/report_decode.py's FIELDS[11] */
#elif defined(SB_HW_AUDIO11)
#define HW_LOG_LAYOUT  10u                  /* tools/report_decode.py's FIELDS[10] */
#else
#define HW_LOG_LAYOUT  9u                   /* tools/report_decode.py's FIELDS[9] */
#endif
#define HW_LOG_HEAD    12u                  /* header words before the fields */
#define HW_LOG_FIELDS  (HW_LOG_REC / 4u - HW_LOG_HEAD - 1u)
/* The build's identity in each record: the package's version, which the
 * candidate's pack must match (tools/report-decode.py prints it). The
 * last definition stays the identity of a build without audio13, which
 * seams case report1 builds (tools/seams_suite.py's _build_id). */
#if defined(SB_HW_U3U)
#define HW_BUILD_ID    "0.15.0-hw3z"
#elif defined(SB_HW_AUDIO14)
#define HW_BUILD_ID    "0.14.0-hw3y"
#elif defined(SB_HW_AUDIO13)
#define HW_BUILD_ID    "0.13.0-hw3x"
#else
#define HW_BUILD_ID    "0.12.1-hw3w"
#endif
struct hw_report {
    u32 scanned;                /* the ring read once */
    u32 found;                  /* valid records found then */
    u32 slot, seq;              /* where and with what number the next record goes */
    u32 saved, fails;           /* records written and verified; writes that failed */
    u32 last_err;               /* 1 no flash, 2 image too long, 3 erase, 4 program, 5 verify, 6 busy at the take */
    /* Since the next build after audio5 (three records failed their CRC on
     * the unit): what each failed write saw, the last HW_LOG_FAILS. */
    u32 busy_waits;             /* takes that found the chip busy and waited */
    u32 glitches;               /* verifies that failed once and read back right the second time */
    u32 retries;                /* records written again in the next slot after a failed one */
    u32 page_rewaits;           /* page programs whose wait said busy and were waited on again */
    u32 fail_n;                 /* failed writes so far (fail[] holds the last HW_LOG_FAILS) */
    u32 fail[4][8];             /* seq, slot, err, pages that differ (bit per 256 bytes), first differing byte, bytes read 0xFF where 0xFF wasn't written, the word written there, the word read */
};
#define HW_LOG_FAILS 4u
extern struct hw_report hw_rep;
int hw_flash_take(void);
void hw_flash_give(void);
void hw_report_save(const char *label);
#if defined(SB_HW_AUDIO1)
u32 hw_audio_report(u32 *w);
#endif
#endif
#if defined(SB_HW_FINDER)
void hw_finder(void) __attribute__((noreturn));
#endif
#if defined(SB_HW_AUDIO1)
/* audio1 (hw_audio.c, clean-br17-audio1): the audio probe. Its line on the
 * test screen (scale 2), between core 1's row and the window's; the page's
 * hold; how long the tone runs before the "tone on" registers are read. */
#define HW_AUD_Y      160u
#define HW_AUD_REGS   22u
#define HW_AUD_MORE   13u
#if defined(SB_TEST_SHORT_HOLD)
#define HW_AUD_PAGE_MS   1000u
#define HW_AUD_SETTLE_MS 300u
#else
#define HW_AUD_PAGE_MS   20000u
#define HW_AUD_SETTLE_MS 1500u
#endif
/* audio3: core 1's count at fixed points (hw_aud.c1_beat, c1_count). */
#define HW_C1_REL   0u   /* just after core 1's release */
#define HW_C1_PRE   1u   /* just before audio_start */
#define HW_C1_POST  2u   /* just after it */
#define HW_C1_P10   3u   /* 10 ms after it */
#define HW_C1_P100  4u   /* 100 ms after it */
#define HW_C1_S0    5u   /* the first page's settle over, before its register reads */
#define HW_C1_S1    6u   /* just after those reads */
#define HW_C1_POLL  7u   /* after the first page loop's first CON0 and CON2 reads */
#define HW_C1_KEY   8u   /* just after the last key's write (REC, SEQ, ARP or SAVE) */
#define HW_C1_K10   9u   /* 10 ms after it */
#define HW_C1_K100  10u  /* 100 ms after it */
#define HW_C1_PAGE  11u  /* the page's start */
#define HW_C1_NOW   12u  /* the page's latest redraw */
#define HW_C1_MARKS 13u
/* The keyed steps, in hw_aud.snap's order. */
#define HW_K_REC  0u     /* audio2's CLK_CON2 bit 9 */
#define HW_K_SEQ  1u     /* the core 1 probe's ALNK0 stop */
#define HW_K_A    2u     /* audio3's step A: CON0 bit 11 cleared and set again */
#define HW_K_B    3u     /* audio3's step B: CLK_CON2 bit 8 */
#define HW_K_H    4u     /* audio4's step H: the audio clock measured by JL_GPCNT */
#define HW_K_I    5u     /* audio4's step I: ALNK1 with CLK_CON2 bit 11 */
#define HW_K_K    6u     /* audio5's step K: what input 5 is (JL_GPCNT) */
#define HW_K_J    7u     /* audio5's step J: ALNK0's CON1 and CON3, a bit at a time */
#define HW_K_N    8u
/* Step K's measurements, in order (hw_audio.c, k_label). */
#define HW_KM_N   10u
/* Step K: how long a gate's count is waited for (the pending flag isn't
 * relied on: report1 never saw it set, HW-153); step J: each try's wait. */
#define HW_K_WAIT_MS  5u
#if defined(SB_TEST_SHORT_HOLD)
#define HW_J_WAIT_MS  30u
#else
#define HW_J_WAIT_MS  100u
#endif
#define HW_J_TRIES    24u    /* CON1 bits 0-15, then CON3 bits 0-7 */
#define HW_J_NONE     0u
#define HW_J_DONE     1u     /* swept, nothing moved, every try put back */
#define HW_J_MOVED    2u     /* stopped at a try that moved: its bit left set */
#define HW_J_ABORTED  3u     /* stopped by a second press, the try put back */
#define HW_J_UNDONE   4u     /* the moved try put back by a second press */
/* Step H's gate: 32 x 2^HW_H_GATE_N cycles of the crystal (HW-151), and
 * how long one gate's pending flag is waited for; step I's poll of ALNK1. */
#define HW_H_GATE_N   10u
#define HW_H_GATE     (32u << HW_H_GATE_N)
#define HW_H_WAIT_MS  20u
#if defined(SB_TEST_SHORT_HOLD)
#define HW_I_POLL_MS  300u
#else
#define HW_I_POLL_MS  1000u
#endif
/* A snapshot: CON0, CLK_CON2, source 11's interrupts, core 1's count. */
#define HW_SNAP   4u
#define HW_A9_PB5_TIMES 16u
#define HW_A9_ROUTE_NONE 0u
#define HW_A9_ROUTE_UP   1u  /* bits 7 and 8 set, R2 in place, the check passed */
#define HW_A9_ROUTE_DOWN 2u  /* taken down by its key */
#define HW_A9_ROUTE_UNDONE 3u /* the firmware's own undo: port A moved or a check failed */
#define HW_A9_ROUTE_NOL2 4u  /* L2 didn't run: nothing further at start-up */
#define HW_A9_S2_BOTH  0u
#define HW_A9_S2_UPPER 1u    /* the sample in the word's upper half, the lower 0 */
#define HW_A9_S2_LOWER 2u    /* the lower half, the upper 0 */
#define HW_A9_S2_N     3u
/* audio10's F: the sample's format in a word (a9_s2 holds it). */
#define HW_A10_P   0u        /* the sample in both halves (audio9's) */
#define HW_A10_U   1u        /* the upper half alone, the lower 0 */
#define HW_A10_L   2u        /* the lower half alone, the upper 0 */
#define HW_A10_N   3u        /* the sample upper, its negative lower */
#define HW_A10_N2  4u        /* the negative upper, the sample lower */
#define HW_A10_FMTS 5u
#define HW_A10_FMT_LOG 8u
#define HW_A10_MRING 40u
#define HW_A10_HOLD_LOG 8u
#define HW_A10_SCAN_MS 5000u
#define HW_A10_STILL_MS 1000u
#define HW_A10_ZERO   0u     /* the holds, by bit: the link plays zeros */
#define HW_A10_LED    1u     /* the LED guide's blink held */
#define HW_A10_SCREEN 2u     /* the screen's redraws held */
#define HW_A10_LOG    3u     /* the log's writes held (dropped and counted) */
#define HW_A10_SCAN   4u     /* the matrix scan and main's sweeps held, 0xFFFF latched */
/* audio11 (clean-br17-audio11): the SARADC's set-ups, its channels, the
 * fill per algorithm. */
#define HW_A11_SDK    0u     /* the SDK's three CON writes (HW-167) */
#define HW_A11_OLD    1u     /* the old single write (the new fields 0) */
#define HW_A11_SETUPS 2u
#define HW_A11_CHANS  9u     /* the channels kept: 0, 1, 3, 4, 5, 6, 7, 10, 11 */
#define HW_A11_SLOTS  4u     /* values counted exactly per channel and set-up */
#define HW_A11_SET_LOG 8u
#define HW_A11_JUMPS  8u
#define HW_A11_ALGS   10u    /* FM_ALGORITHMS */
/* audio12 (clean-br17-audio12, audio12b): power-on gives the test screen
 * (HW_A12_TEST); SEL there runs the instrument's start (HW_A12_INSTRUMENT
 * once the panel is up). */
#define HW_A12_INSTRUMENT 1u
#define HW_A12_TEST       2u
/* S: the sweep's states; a chord of HW_A12_NOTES_CHORD notes held
 * HW_A12_CHORD_FRAMES, then its release waited for, at most
 * HW_A12_REL_FRAMES (frames at 44.1 kHz). */
#define HW_A12_SW_IDLE    0u
#define HW_A12_SW_CHORD   1u
#define HW_A12_SW_RELEASE 2u
#define HW_A12_SW_DONE    3u   /* every algorithm played */
#define HW_A12_SW_STOPPED 4u   /* stopped by the key after a chord */
#define HW_A12_NOTES_CHORD 8u
#if defined(SB_TEST_A12_SHORT)
#define HW_A12_CHORD_FRAMES 13230u   /* the test build: 0.3 s */
#else
#define HW_A12_CHORD_FRAMES 66150u   /* 1.5 s */
#endif
#define HW_A12_REL_FRAMES   132300u  /* 3 s */
#define HW_A12_REL_BOUND    0x80000000u /* in sw_rel: the release's wait reached the bound */
/* G: the note-on log's entries. */
#define HW_A12_NOTES 16u
/* audio13 (clean-br17-audio13; the owner's rulings): power-on starts the
 * instrument (HW_A13_COLD), HOME held then gives the test screen
 * (HW_A13_HOME). U2: the USB block's five words (the first core's CON0
 * and CON1, the pins' block's CON0 to CON2, HW-171), read only; the cable
 * states a to e (HW_A13_STATES); the change log, the state marks and
 * U2-C's readings; ARP's steps (frames and sb_now units). */
#define HW_A13_COLD    1u
#define HW_A13_HOME    2u
#define HW_A13_WORDS   5u
#define HW_A13_STATES  5u
#define HW_A13_RUNS    2u    /* U2-B's runs: U2-C off, then on */
#define HW_A13_MARKS   16u
#define HW_A13_CHANGES 24u
#define HW_A13_C_LOG   32u
#define HW_A13_C_FIRST 4u
#define HW_A13_ARP_LOG 48u
#define HW_A13_GAP_MAX 30000u /* frames: a longer gap is a break (a rest, ARP off), not a step's gap */
/* audio14 (clean-br17-audio14). P: the four words of the block at 0x16A00
 * (0x16A00 and the three words after it, the owner's ruling), read only, with U2-A's. */
#define HW_A14_P_BASE  0x16A00u
#define HW_A14_P_WORDS 4u
#define HW_A9_LATE_MAX 50u   /* late halves after which the interrupt goes back to the tone */
#define HW_A9_PB5_SETTLE_MS 50u
#define HW_A9_DAA7_MS 60000u
#define HW_A8_PINS   11u    /* PC0, PC1, PC2, PC6, PA4 to PA10 */
#define HW_A8_EVENTS 32u     /* 120 before layout 9 (audio10 needed the room) */
#define HW_A8_EV_PER 12u
#define HW_A8_SAMPLE_MS 10u
#define HW_A8_WATCH_MS  100u
#define HW_A8_R9_MS     200u
#if defined(SB_TEST_SHORT_HOLD)
#define HW_A8_SENSE_MS  2000u
#else
#define HW_A8_SENSE_MS  20000u
#endif
#define HW_A8_OFF_NONE   0u
#define HW_A8_OFF_NOBOOT 1u  /* not an audio8 build, or start-up's L2 not run yet */
#define HW_A8_OFF_L2     2u  /* start-up's L2 didn't run or failed its check: put back */
#define HW_A8_OFF_CHECK  3u  /* a check after an undo failed: nothing more is written */
#define HW_A8_R2_NONE    0u
#define HW_A8_R2_SET     1u
#define HW_A8_R2_UNDONE  2u
#define HW_A8_S1_NONE    0u
#define HW_A8_S1_KEPT    1u  /* port C moved, port A didn't, the check passed: CON0 bits 7 and 8 kept */
#define HW_A8_S1_NONE_MOVED 2u /* port C didn't move: bits 7 and 8 undone */
#define HW_A8_S1_STOPPED 3u  /* port A moved or a check failed: undone (rt_stop says which) */
#define HW_A8_S1_UNDONE  4u  /* kept, then put back by a key */
#define HW_A8_SW_NONE    0u
#define HW_A8_SW_DONE    1u  /* every bit tried, port C never moved */
#define HW_A8_SW_KEPT    2u  /* port C moved at rt_bit, port A didn't: kept */
#define HW_A8_SW_STOPPED 3u  /* stopped at rt_bit: port A moved or a check failed (sw_stop) */
#define HW_A8_SW_UNDONE  4u  /* the kept bit put back by a key */
#define HW_A8_STOP_NONE  0u
#define HW_A8_STOP_PC    1u  /* port C moved, port A didn't, the check passed: kept */
#define HW_A8_STOP_PA    2u  /* port A moved: undone at once, before the check */
#define HW_A8_STOP_CHECK 3u  /* the matrix check failed: undone */
#define HW_A8_STOP_AFTER 4u  /* the check after the undo failed */
#define HW_A8_STOP_ROWS  5u  /* the rows weren't idle before the write (a key held): nothing written */
#define HW_A8_SE_NONE    0u
#define HW_A8_SE_DONE    1u
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
    /* audio2 (clean-br17-audio2), after audio1's fields so their places stay: */
    u32 more[3][HW_AUD_MORE];   /* the clock, PLL and pin-map words: at main's start, tone on, after the last step */
    u32 regs_step[HW_AUD_REGS]; /* audio1's registers after the last step */
    u32 step_state;             /* HW_STEP_NONE, _TAKEN or _UNDONE */
    u32 steps;                  /* key presses taken */
    u32 clk_before, clk_set, clk_back; /* CLK_CON2 read before, read back after bit 9 set, read back after it is put back */
    /* audio3 (clean-br17-audio3), after audio2's: */
    u32 c1_beat[HW_C1_MARKS], c1_count[HW_C1_MARKS]; /* core 1's count at the fixed points, and their beats */
    u32 c1_seen, c1_moved;      /* the count last seen, and the beat it was last seen to change */
    u32 al_state, al_keys;      /* HW_AL_RUN, _STOPPED or _BACK; SEQ presses taken */
    u32 al_before, al_stop, al_back; /* ALNK0 CON0 read before, read back after bit 11 cleared, read back after it is put back */
    u32 al_blocks_stop, al_blocks_back; /* sb_audio.blocks at the stop and at the restart */
    u32 x2[2][16];              /* corex2 words 0x80-0x8F at the page's start, and at its core 1 view */
    /* audio3's steps A and B (clean-br17-audio3), after the core 1 probe's: */
    u32 a_state, a_keys;        /* step A: HW_STEP_NONE, _TAKEN or _UNDONE; presses taken */
    u32 a_before, a_clr, a_set, a_back; /* CON0 read before; read back after bit 11 cleared, after it set again, after it is put back */
    u32 b_state, b_keys;        /* step B, likewise */
    u32 b_before, b_set, b_back; /* CLK_CON2 read before; read back after bit 8 set, after it is put back */
    u32 refused;                /* presses refused (A or B without bit 9; REC's undo with B taken) */
    u32 snap[HW_K_N][2][HW_SNAP]; /* each step's last press: before and 100 ms after */
    /* audio4's steps H and I (clean-br17-audio4), after audio3's: */
    u32 h_state, h_keys, h_measures;
    u32 h_clk1_before, h_clk1_check, h_clk1_audio, h_clk1_back; /* CLK_CON1 read before; read back after bits 4-6 = 3, = 5, put back */
    u32 h_gp_before, h_gp_check, h_gp_audio, h_gp_back;     /* JL_GPCNT->CON likewise */
    u32 h_check[2], h_audio[2]; /* NUM, two gates apart: the high-speed bus, the audio clock */
    u32 h_check_to, h_audio_to; /* of those two gates, how many timed out */
    u32 h_check_clk2, h_audio_clk2; /* CLK_CON2 at each measurement */
    u32 i_state, i_keys, i_bit10;
    u32 i_con_before[4], i_con_after[4], i_con_back; /* ALNK1's CON0-CON3 before and after; CON0 put back */
    u32 i_clk_before, i_clk_set, i_clk_set10, i_clk_back; /* CLK_CON2 read before; after bit 11, after bit 10, put back */
    u32 i_flips, i_pend, i_span, i_hps10; /* the last poll: CON0 bit 15 changes, CON2 bit 7 seen, over beats; halves a second x 10 */
    u32 clk_stack[3], clk_depth; /* the CLK_CON2 steps taken (REC, B, I), in order: only the last is undone */
    /* audio5's steps K and J (clean-br17-audio5), after audio4's: */
    u32 k_state, k_keys;
    u32 k_clk1_before, k_gp_before, k_clk1_back, k_gp_back; /* CLK_CON1 and JL_GPCNT->CON read before K, read back after its undo */
    u32 k_m[HW_KM_N][6];        /* each measurement: CLK_CON1 and JL_GPCNT->CON as read back, NUM twice, timeouts, CLK_CON2 */
    u32 j_state, j_sweeps, j_tries; /* HW_J_*; sweeps run; tries in the last sweep */
    u32 j_reg, j_bit;           /* the last try: 1 CON1 or 3 CON3, and its bit */
    u32 j_before, j_written, j_read, j_back; /* its register read before, written, read back, read back after it was put back */
    u32 j_flips, j_pend, j_irq, j_con0, j_con2, j_clk2; /* over its wait: CON0 bit 15 changes, CON2 bit 7 seen, source 11's interrupts; CON0, CON2, CLK_CON2 at its end */
    u32 j_clk2_sweep;           /* CLK_CON2 when the last sweep began */
    u32 j_rb[HW_J_TRIES];       /* each try's read-back in the last sweep (0xFFFFFFFF: not tried) */
    u32 j_nohold;               /* tries whose bit didn't read back set: bit t for try t */
    /* audio6's step D (clean-br17-audio6), after audio5's: the last try,
     * which is the one the sweep stopped at if it stopped. */
    u32 d_state, d_sweeps, d_tries, d_bit, d_stop, d_phase; /* HW_D_*; sweeps; tries this sweep; the bit; HW_D_STOP_*; the try's step (1 to 7) */
    u32 d_clk2;                 /* CLK_CON2 at the try */
    u32 d_con5_before, d_con5_written, d_con5_read, d_con5_back, d_con5_after; /* CON5: read, written, read back, put back (read back), read after the undo's check */
    u32 d_iomap_before[9], d_iomap_after[9]; /* JL_IOMAP CON0-CON8 before the try and after its undo */
    u32 d_pa_before[8], d_pa_set[8], d_pa_after[8]; /* port A's OUT, IN, DIR, DIE, PU, PD, HD0, HD: before, with the bit set, after the undo */
    u32 d_in_start, d_in_end;   /* port A's IN at the watch's start and end */
    u32 d_flips, d_pend, d_irq; /* over the watch: CON0 bit 15's changes, CON2 bit 7 seen, source 11's interrupts */
    u32 d_idle_base, d_map_base[3]; /* the matrix just before the write: rows with no column (6 bits, 1 open), closed cells */
    u32 d_idle_set, d_map_set[3]; /* the same with the bit set */
    u32 d_idle_after, d_map_after[3]; /* the same after the undo */
    u32 d_check_set, d_check_after; /* 0 passed; else bit 0 the idle rows, 1 the cells, 2 port A's DIR, DIE, PU or PD, 3 CON5 not back, 4 JL_IOMAP not back */
    u32 d_al0[4], d_irq_now, d_core1; /* ALNK0's CON0-CON3, source 11's count, core 1's count, at the try's end */
    u32 d_j_putback;            /* J's register put back before the sweep: register << 16 | value (0: none) */
    /* audio7's set-ups L1 and L2 (clean-br17-audio7), after audio6's: the
     * last set-up, which is the one kept or stopped at if any. */
    u32 l_state, l_which, l_presses, l_stop, l_phase, l_stopped; /* HW_L_*; 1 or 2; set-ups run; HW_D_STOP_*'s reasons; its step (1 to 7); 1 once a check after an undo failed (no more set-ups) */
    u32 l_before[4];            /* ALNK0's CON0 to CON3 read before */
    u32 l_len_read, l_adr_read, l_len_used; /* LEN and ADR3 as read (write-only registers: what reads back), the LEN the expectations use */
    u32 l_clk1, l_clk2;         /* CLK_CON1 and CLK_CON2 before */
    u32 l_pa_before[8];         /* port A's eight registers before */
    u32 l_irq0, l_core1_0;      /* source 11's and core 1's counts before */
    u32 l_exp_fps10, l_exp_hps10_a, l_exp_hps10_b; /* expected frames a second x 10; halves a second x 10, (a) LEN frames a half, (b) LEN / 2 */
    u32 l_w[4], l_rb[4];        /* written and read back: CON0 stopped, CON3, CON1, CON0 running */
    u32 l_flips, l_pend, l_irq, l_span; /* over the watch: CON0 bit 15's changes, CON2 bit 7 seen, source 11's interrupts; sb_now() units from the first change to the last */
    u32 l_hps10, l_fps10_a, l_fps10_b; /* halves a second x 10, and frames a second x 10 by each LEN reading */
    u32 l_idle_base, l_map_base[3], l_idle_set, l_map_set[3], l_pa_set[8], l_check_set; /* the matrix: before, with the set-up in place (as D's) */
    u32 l_idle_after, l_map_after[3], l_pa_after[8], l_check_after; /* after the undo */
    u32 l_back[3];              /* CON0, CON1 and CON3 read back after they were put back */
    u32 l_clk2_end, l_core1_end;
    /* audio8 (clean-br17-audio8), after audio7's. Pin counts (a sample):
     * PC0, PC1, PC2, PC6, then PA4 to PA10, each pin's changes of IN over
     * the sample; its loop's passes; its sb_now() span. */
    u32 a8_boot, a8_off;        /* 1 once L2 was set up at start-up (SB_HW_AUDIO8); HW_A8_OFF_*: why audio8's keys are refused (0: they aren't) */
    u32 a8_pcm16;               /* 1: the 16-bit tone (SB_HW_PCM16), a word a frame */
    u32 r9_flips, r9_irq, r9_clk2; /* REC: over HW_A8_R9_MS after its write, CON0 bit 15's changes and source 11's interrupts; CLK_CON2 read back */
    u32 ctl[HW_A8_PINS], ctl_n, ctl_span; /* the control sample: before R2's writes, nothing routed */
    u32 r2_state, r2_presses, r2_check; /* HW_A8_R2_*; presses; 0 or bits: 0 the pulls or drive changed, 1 another pin's bits changed, 2 the undo didn't read back as read */
    u32 r2_pc_before[8], r2_pc_set[8], r2_pc_after[8]; /* port C's OUT, IN, DIR, DIE, PU, PD, HD0, HD: before, set, after the undo */
    u32 s1_state, s1_runs;      /* step 1: HW_A8_S1_*; runs */
    u32 s1a[HW_A8_PINS], s1a_n, s1a_span; /* (a): R2 in place, CON0 bits 7 and 8 clear */
    /* The last routed try: step 1's (b) or one of the sweep's tries. */
    u32 rt_kind, rt_bit, rt_phase, rt_stop; /* 1 (b), 2 the sweep; the CON5 bit (sweep); its step (1 to 7); HW_A8_STOP_* */
    u32 rt_con0[4], rt_con5[4]; /* CON0 and CON5: read before, written, read back, read back after the undo */
    u32 rt_iomap_before[9], rt_iomap_after[9];
    u32 rt_idle_base, rt_map_base[3], rt_idle_set, rt_map_set[3], rt_idle_after, rt_map_after[3];
    u32 rt_pa_before[8], rt_pa_set[8], rt_pa_after[8], rt_pc_set[8];
    u32 rt_check_set, rt_check_after; /* as D's, bit 5: port A moved (its pins counted changes) */
    u32 rt_c1[HW_A8_PINS], rt_n1, rt_span1; /* the first sample, just after the write */
    u32 rt_c2[HW_A8_PINS], rt_n2, rt_span2; /* (b) only: the second, at the watch's end */
    u32 rt_flips, rt_irq;       /* over the watch: CON0 bit 15's changes, source 11's interrupts */
    u32 sw_state, sw_sweeps, sw_tries, sw_stop; /* the sweep: HW_A8_SW_*; sweeps; tries; HW_A8_STOP_* of its last try */
    u32 sw_pa_bits, sw_nohold; /* bits whose try moved port A; bits that didn't read back set */
    u32 se_state, se_runs, se_ms; /* the sense scan: HW_A8_SE_*; runs; milliseconds read */
    u32 se_dir[8], se_die[8], se_in0[8], se_changed[8]; /* ports A to H: DIR, DIE, IN at the start; the bits that changed */
    u32 se_count[64];           /* each bit's changes, 16 bits each: port p bit b at half (16p + b) */
    u32 se_ev_n, se_ev_lost;    /* events kept, events not kept (the list full) */
    u32 se_ev[HW_A8_EVENTS];    /* ms << 16 | level << 8 | port << 4 | bit, while the bit has changed at most HW_A8_EV_PER times */
    /* audio9 (clean-br17-audio9), after audio8's. */
    u32 a9_route, a9_ups, a9_downs; /* HW_A9_ROUTE_*; the route put up (start-up included) and taken down */
    u32 a9_synth, a9_synth_ons, a9_s2; /* 1 while the synth fills the halves; times switched on; HW_A9_S2_* */
    u32 a9_late0, a9_late, a9_fill_max, a9_fill_last; /* underruns when the synth came on; late halves since; the longest fill since and the last (sb_now units) */
    u32 a9_fallback;            /* the beat the interrupt went back to the tone after HW_A9_LATE_MAX late halves (0: never) */
    u32 a9_engine_blocks;       /* fm_block calls */
    u32 pb5_now, pb5_raw_changes, pb5_settled, pb5_logged; /* PB5 now; its changes as the scan saw them; the settled level; settled changes written to the log */
    u32 pb5_t[HW_A9_PB5_TIMES]; /* the beats of its last raw changes, newest at (pb5_raw_changes - 1) % HW_A9_PB5_TIMES */
    u32 daa7_boot, daa7_route, daa7_last, daa7_reads, daa7_changes; /* DAA_CON7 at start-up, after the route, last read (each minute); reads; changes seen */
    u32 a9_words[HW_A10_FMTS][4]; /* the first words of a half filled in each format (S2's three, audio10's five; the 16-bit build) */
    /* audio10 (clean-br17-audio10), after audio9's; a9_s2 holds F's format. */
    u32 a10_fmt_changes, a10_fmt_t[HW_A10_FMT_LOG]; /* format changes; their beats << 3 | the format, the last HW_A10_FMT_LOG */
    u32 a10_fill_max, a10_fill_max8, a10_voices_max; /* the synth's own fill (sb_now units): longest, longest with 8 voices sounding; most voices */
    u32 a10_soft, a10_hard;     /* samples the soft clip bent; samples saturated at full scale */
    u32 m_value, m_raw, m_tone_gain, m_synth_target; /* MASTER: its value (the mean input.c reports), the ADC's last reading, the tone's gain and the synth's level now */
    u32 m_changes, m_jumps, m_maxdelta, m_ring_n; /* value changes; raw readings more than 32 from the one before; the largest such step; ring entries */
    u32 m_ring[HW_A10_MRING];   /* beats << 10 (the low 22 bits of beats / 4) | value; the last HW_A10_MRING changes */
    u32 holds, hold_n, hold_t[HW_A10_HOLD_LOG]; /* the holds on now (bits HW_A10_*); changes; beats << 8 | hold << 1 | on */
    u32 log_dropped, scan_until; /* records not written while the log was held; the beat the scan hold ends */
#if defined(SB_HW_AUDIO11)
    /* audio11 (clean-br17-audio11): the SARADC's service (hw_audio.c). */
    u32 adc_setup, adc_set_n, adc_set_t[HW_A11_SET_LOG]; /* HW_A11_*; changes; beats << 1 | set-up */
    u32 sar_con[HW_A11_SETUPS][4]; /* each set-up's CON writes (up to three) and CON read after the last */
    u32 adc_conv_n[HW_A11_SETUPS], adc_conv_to[HW_A11_SETUPS]; /* conversions done; waits ended by the time-out */
    u32 adc_conv_min[HW_A11_SETUPS], adc_conv_max[HW_A11_SETUPS]; /* start to bit 7 seen, sb_now units, by the slot's poll (83 us steps) */
    u32 adc_conv_tight[HW_A11_SETUPS]; /* one conversion timed by a tight poll at each change of set-up (sb_now units) */
    u32 adc_pass_max, adc_passes; /* the longest slot's service time (sb_now units); sweep passes (all channels once) */
    u32 adc_mm[HW_A11_SETUPS][HW_A11_CHANS]; /* min << 16 | max */
    u32 adc_n[HW_A11_SETUPS][HW_A11_CHANS]; /* readings */
    u32 adc_v[HW_A11_SETUPS][HW_A11_CHANS][HW_A11_SLOTS]; /* value << 22 | count (exact while 4 distinct values or fewer) */
    u32 adc_other[HW_A11_SETUPS][HW_A11_CHANS]; /* readings no longer in a slot (a slot given to a newer value) */
    u32 adc_last[12];           /* each channel's last reading (0xFFFF: not converted) */
    u32 m_raw_ring[HW_A10_MRING / 2]; /* the raw reading at each m_ring entry, two 16-bit halves a word */
    u32 m_jump_n, m_jump_t[HW_A11_JUMPS]; /* raw jumps (> 32): beats / 4 << 20 | from << 10 | to, the last HW_A11_JUMPS */
    u32 fill_alg[HW_A11_ALGS], fill_alg8[HW_A11_ALGS]; /* the synth's longest fill per algorithm, and with 8 voices (sb_now units) */
    u32 m_level;                /* the level applied now, of 65536 (MASTER's curve) */
    char big[3][16];            /* E: the large area's three lines */
#endif
#if defined(SB_HW_AUDIO12)
    /* audio12 (clean-br17-audio12). */
    u32 start_mode;             /* HW_A12_TEST from power-on; HW_A12_INSTRUMENT once SEL's start has put the panel up */
    u32 as_state, as_alg, as_runs, as_stop, as_chords; /* S: HW_A12_SW_*; the algorithm playing (1 to 10); sweeps started; a stop asked; chords played */
    u32 as_frames;              /* frames into the chord or release now */
    u32 as_fill[HW_A11_ALGS];   /* each algorithm's longest fill (sb_now units) */
    u32 as_fill_v[HW_A11_ALGS]; /* the voices sounding then */
    u32 as_soft[HW_A11_ALGS], as_hard[HW_A11_ALGS], as_late[HW_A11_ALGS]; /* soft-clipped and saturated samples, late halves and underruns, in each algorithm's chord and release */
    u32 as_rel[HW_A11_ALGS];    /* frames each release took to end (| HW_A12_REL_BOUND if it didn't) */
    u32 as_soft0, as_hard0, as_late0; /* the counts when the algorithm's chord began */
    u32 g_note_n, g_note[HW_A12_NOTES]; /* G: note ons; note << 24 | voice << 16 | ALGORITHM read << 8 | the voice's algorithm << 1 | local control, the last HW_A12_NOTES */
    u32 g_turns, g_turns_off, g_turn_alg; /* ALGORITHM turns the engine took, turns it dropped (local control off), the algorithm after the last */
#endif
#if defined(SB_HW_AUDIO13)
    /* audio13 (clean-br17-audio13). */
    u32 a13_start;              /* HW_A13_COLD or HW_A13_HOME */
    u32 u2_boot[HW_A13_WORDS];  /* U2-A: the five words at the app's start (sb_start, before the copy) */
    u32 u2_late[HW_A13_WORDS];  /* and a second later (before the audio path) */
    u32 u2_late_beat, u2_late_blocks; /* the beat of that reading, and the audio blocks then (0: before the audio path) */
    u32 u2_key[HW_A13_WORDS];   /* and at the last press of the re-read key */
    u32 u2_key_beat, u2_key_n;
    u32 u2_state, u2_run, u2_polls; /* U2-B: the cable state (0 to 4: a to e); the run (0: U2-C off at its a, 1: on); polls */
    u32 u2_ref[HW_A13_WORDS];   /* the words when state a was last marked (or at the first poll) */
    u32 u2_last[HW_A13_WORDS];  /* at the last poll */
    u32 u2_mark_n, u2_mark[HW_A13_MARKS]; /* state marks: beat << 3 | state, the last HW_A13_MARKS */
    u32 u2_chg_n, u2_chg[HW_A13_CHANGES][2]; /* changes: beat << 3 | word, then the new value, the last HW_A13_CHANGES */
    u32 u2_or[HW_A13_RUNS][HW_A13_STATES][HW_A13_WORDS];  /* each word's bits ever set in each run's state */
    u32 u2_and[HW_A13_RUNS][HW_A13_STATES][HW_A13_WORDS]; /* and always set (all ones before the first poll there) */
    u32 u2_seen[HW_A13_RUNS];   /* polls in each run, by state: 6 bits each */
    u32 u2c_on, u2c_toggles;    /* U2-C: channels 12 and 13 in the sweep; key presses */
    u32 u2c_n[HW_A13_STATES][2], u2c_mm[HW_A13_STATES][2]; /* readings by state and channel; min << 16 | max */
    u32 u2c_to;                 /* their conversions that timed out */
    u32 u2c_first[HW_A13_C_FIRST]; /* each turn-on's first readings: ch12 << 16 | ch13 (0xFFFF: none yet) */
    u32 u2c_log_n, u2c_log[HW_A13_C_LOG]; /* readings: value << 22 | state << 19 | ch13 << 18 | beat / 64 (18 bits) */
    u32 arp_n, arp_breaks, arp_gaps;  /* ARP: steps seen; chain breaks (a rest or ARP off); gaps measured */
    u32 arp_gmin_f, arp_gmax_f, arp_gmin_u, arp_gmax_u; /* the shortest and longest gap, frames and sb_now units */
    u32 arp_last_f, arp_last_u; /* the last gap */
    u32 arp_best_n, arp_best_f0, arp_best_u0, arp_best_f1, arp_best_u1; /* the longest chain: steps, its first and last step */
    u32 arp_log[HW_A13_ARP_LOG][2]; /* each step: the engine's frame count, sb_now at its fill; the last HW_A13_ARP_LOG */
#endif
#if defined(SB_HW_AUDIO14)
    /* audio14 (clean-br17-audio14). */
    u32 p_boot[HW_A14_P_WORDS]; /* P: the block at 0x16A00 at the app's start (sb_start, with U2-A's) */
    u32 p_late[HW_A14_P_WORDS]; /* and a second later, with U2-A's (before the audio path) */
    u32 p_key[HW_A14_P_WORDS];  /* and at the last press of U2-A's key */
    u32 arp_saves;              /* R: REC's ARP saves in the panel (this record's counted) */
    u32 arp_save_err;           /* the last save's result before this record: hw_rep.last_err (0: saved) */
    u32 arp_save_seq;           /* the record number that save was given */
    u32 arp_offs;               /* records written by ARP turning off with new steps */
#endif
};
#define HW_L_NONE    0u
#define HW_L_KEPT    1u     /* the link moved with the matrix right: the set-up running */
#define HW_L_UNDONE  2u     /* a kept set-up put back by a key */
#define HW_L_DONE    3u     /* nothing moved: the firmware put it back */
#define HW_L_STOPPED 4u     /* a check failed: put back by the firmware, l_stop says which */
#if defined(SB_TEST_SHORT_HOLD)
#define HW_L_WAIT_MS 300u
#else
#define HW_L_WAIT_MS 1000u
#endif
#define HW_D_NONE     0u
#define HW_D_DONE     1u     /* every bit tried, none stopped it */
#define HW_D_STOPPED  2u     /* stopped at a try (d_stop says why), CON5 put back */
#define HW_D_KEPT     3u     /* the link moved with the matrix right: the bit kept */
#define HW_D_UNDONE   4u     /* the kept bit put back by a press */
#define HW_D_STOP_NONE      0u
#define HW_D_STOP_CHECK     1u   /* the matrix check failed with the bit set: undone */
#define HW_D_STOP_MOVED     2u   /* the link moved, the check passed: kept */
#define HW_D_STOP_MOVED_BAD 3u   /* the link moved, the check failed: undone */
#define HW_D_STOP_AFTER     4u   /* the check after the undo failed */
#define HW_D_STOP_KEY       5u   /* a press of D's key stopped it */
#define HW_D_RELEASE_MS     5000u /* how long D waits for OCT- to be released before its first try */
#define HW_AL_RUN     0u
#define HW_AL_STOPPED 1u
#define HW_AL_BACK    2u
void hw_c1_mark(u32 i);
void hw_audio_alnk(void);
void hw_audio_a(void);
void hw_audio_b(void);
void hw_audio_h(void);
void hw_audio_h_again(void);
void hw_audio_i(void);
void hw_audio_i10(void);
void hw_audio_k(void);
void hw_audio_j(void);
void hw_audio_keypage_kj(void);
void hw_audio_d(void);
void hw_audio_keypage_d(void);
void hw_audio_l(u32 which);
void hw_audio_keypage_l(void);
void hw_audio_boot_l2(void);
void hw_a8_r2(void);
void hw_a8_step1(void);
void hw_a8_sweep(void);
void hw_a8_sense(void);
void hw_audio_keypage_a8(void);
void hw_scan_hold(void);
void hw_audio9_boot(void);
void hw_a9_route_key(void);
void hw_a9_synth_key(void);
void hw_a9_s2_key(void);
void hw_a9_pb5_poll(void);
void hw_a9_tick(void);
void hw_a10_fmt_key(void);
void hw_a10_hold_key(u32 hold);
void hw_a10_master(u32 value);
void hw_a10_pot_poll(void);
void hw_a11_adc_poll(void);
void hw_a11_setup_key(void);
int hw_a11_pot_take(u32 *v);
u32 hw_a11_pot_first(void);
void hw_a11_big(u32 force);
void hw_a12_sweep_key(void);
#if defined(SB_HW_AUDIO13)
void hw_a12_instrument(u32 cold);
u32 hw_a13_power_on(void);
void hw_a13_u2_key(u32 control);
void hw_a13_u2_poll(void);
void hw_a13_panel_tick(void);
extern u32 hw_u2_boot[HW_A13_WORDS];
#if defined(SB_HW_AUDIO14)
extern u32 hw_p_boot[HW_A14_P_WORDS];
#endif
#else
void hw_a12_instrument(void);
#endif
const char *hw_step_now(void);
void hw_matrix_check(u32 *idle, u32 *map);
void hw_port_a(u32 *w);
void hw_scan_pause(void);
void hw_scan_resume(void);
void hw_audio_keypage(void);
void hw_audio_keypage_hi(void);
u32 hw_audio_key_lit(u32 control);
void hw_audio_leds(u32 held);
/* The next key (the owner's request after audio5): the build's suggested
 * order, one table (hw_audio.c, guide); its next key's LED blinks slowly
 * and the step row says "next: KEY (what)". */
void hw_guide_key(u32 control);
void hw_guide_show(void);
void hw_guide_tick(void);
extern u32 hw_guide_at;
#define HW_STEP_NONE   0u
#define HW_STEP_TAKEN  1u
#define HW_STEP_UNDONE 2u
void hw_audio_step(void);
extern struct hw_audio hw_aud;
void hw_audio_boot(void);
void hw_audio_start(void);
void hw_audio_toggle(void);
void hw_audio_line(void);
void hw_audio_page(void);
#endif
#endif

#endif
