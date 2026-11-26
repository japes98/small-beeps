/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * hw_audio.c's and hw_test_audio.c's shared names (round 2, clean-r2-cleanup): the macros both use,
 * and what each part takes from the other. Not for any other file.
 */

#ifndef HW_AUDIO_INT_H
#define HW_AUDIO_INT_H



#define REG(a) (*(volatile u32 *)(a))
#define SRC_ALNK 11u
/* Q-17: the corex2 words 0x80 to 0x8F, per-core counters, read only. */
#define COREX2_WORD(i) REG(0x01EEE000u + 4u * (0x80u + (i)))
/* HW-43: CON0 bit 11 runs ALNK0. */
#define AL_RUN (1u << 11)

/* --- audio2's clock step (HW-145; the owner's ruling) --------------------- */

#define CLK2_ALNK0_EN (1u << 9)
#define CLK2_CLK_SEL  (1u << 8)

/* --- audio4's steps H and I (HW-140, HW-145, HW-151; the owner's rulings) - */

#define GP_EN   (1u << 0)
#define GP_CLR  (1u << 6)
#define GP_PND  (1u << 7)
#define GP_CSS_INPUT  (4u << 1)     /* counted: the clock system's input */
#define GP_GSS_XOSC   (1u << 12)    /* gate: the crystal oscillator */
#define CLK1_SEL      (7u << 4)     /* CLK_CON1: the clock system's input */
#define CLK1_HSB      3u            /* the high-speed bus */
#define CLK1_AUDIO    5u            /* the audio clock */
#define CLK2_AL1_EN   (1u << 11)
#define CLK2_AL1_SEL  (1u << 10)
#define AL_HALF       0x8000u       /* CON0 bit 15: the half playing */
#define AL_PEND       0x80u         /* CON2 bit 7: a half finished */
#define AL_CLEAR      (1u << 3)     /* CON2 bit 3 clears it */

/* --- audio5's steps K and J (HW-151, HW-153, HW-154; the owner's rulings) - */

#define CLK1_DAC      (3u << 2)     /* CLK_CON1 bits 2-3: the DAC's clock choice (HW-53) */
#define GP_CSS_480    (6u << 1)     /* counted: the counter's own 480 MHz input */

/* --- audio6's step D: JL_IOMAP->CON5, a bit at a time (HW-146, HW-156) --- */

#define IOMAP_WORD(i) REG(0x0005101Cu + 4u * (i))   /* JL_IOMAP CON0 to CON8 (HW-56) */
#define IOMAP_CON5    IOMAP_WORD(5)
#define PA_CHECKED(w, b) ((w)[2] != (b)[2] || (w)[3] != (b)[3] || (w)[4] != (b)[4] || (w)[5] != (b)[5])

/* --- audio7's set-ups L1 and L2 (HW-157, HW-158; the owner's rulings) ---- */

#define L_PINS (3u << 7)            /* CON0 bits 7 and 8: clocks to pins (HW-157), kept clear */
#define L_CON1 0x1000u              /* data 3 an I2S output, 16-bit (HW-157) */

/* --- audio8 (the spec side's clean-br17-audio8; the owner's rulings) ---- */

/* Ports at 0x00050000 + 0x40 x port (A = 0 to H = 7), registers OUT, IN,
 * DIR, DIE, PU, PD, HD0, HD at +0 to +28 (HW-56, the port rule above
 * HW-115). ALNK0's port C pins: PC0, PC1, PC2 and PC6 (HW-141); its group
 * B1 on PA4 to PA10 (HW-156). */
#define PORT_W(port, i) REG(0x00050000u + 0x40u * (port) + 4u * (i))
#define P_A 0u
#define P_C 2u
#define R_OUT 0u
#define R_IN  1u
#define R_DIR 2u
#define R_DIE 3u
#define A8_PC_PINS 0x0047u          /* PC0, PC1, PC2, PC6 */
#define A8_PA_PINS 0x07F0u          /* PA4 to PA10 */
#define A8_PC_LCD  0x0180u          /* PC7 and PC8, which the panel's driver moves */

/* --- audio11 (the spec side's clean-br17-audio11; the owner's rulings) ---
 * B: the SARADC's service. Every conversion the build starts goes through
 * it (MASTER's and the test screen's sweep). It runs from TIMER0's slot
 * (hw_slot, every 83 us) and never waits: a slot finds the conversion in
 * flight done (bit 7) or not; done, it takes the reading and starts the
 * next; not done, it returns, until A11_TIMEOUT. Conversions alternate:
 * MASTER (channel 4), then one channel of the sweep, then MASTER... The
 * sweep leaves out channel 2 (PA10, an LED line), 8 and 9 (PC9 and PC10,
 * the panel), always, and 6 and 7 (PC0 and PC1, the link's clocks) unless
 * the route is down (HW-129). */
#define A11_DONE    (1u << 7)
#define A11_TIMEOUT (5u * 24000u)   /* 5 ms of sb_now's 24 MHz */
#define A11_FIRST_SPINS 2000000u    /* a wait's passes at most, whatever sb_now() does */
#if defined(SB_TEST_A11_SLOW)
/* The test build: bit 7 taken as seen only 300 us after the start, for the
 * waits' sake (fwtest finishes a conversion at once, HW-40). */
#define A11_SEEN(con, d) (((con) & A11_DONE) && (d) >= 300u * 24u)
#else
#define A11_SEEN(con, d) ((con) & A11_DONE)
#endif

/* The sweep's next channel: the kept ones but MASTER's, each in turn;
 * with audio13's U2-C on, channels 12 and 13 (USB D- and D+, HW-129) as
 * two more. */
#define A11_SWEEP_N (HW_A11_CHANS + 2u)
#define A11_SWEEP a13_chan

/* E: the key status in large text, three lines of 12 characters at three
 * times the font (15 x 21 pixels a glyph on an 18 x 24 cell), from y 40
 * to 112, in place of the matrix grid, the ports and the event box. Drawn
 * when it changes (force: after the test screen is drawn again). */
#define A11_BIG_Y 40u

/* --- The tone ------------------------------------------------------------- */

/* 440 Hz at 24 MHz / 544 frames a second (HW-45): the phase step, of 2^32. */
#define TONE_STEP   ((u32)(440ull * 544ull * 4294967296ull / 24000000ull))
/* The gain's top: a sine of +-32767 times it, >> 11, peaks at 838 856,
 * -20 dB of 24-bit full scale; MASTER (0 to 1023) scales it. The ramp:
 * about 20 ms from silence to the top. */
#define GAIN_TOP    52428u
#define GAIN_STEP   60u
/* More interrupts than this in one beat is a storm: a half lasts 1.45 ms
 * at fwtest's rate, so even ten times the rate gives fewer than 8. */
#define STORM_PER_BEAT 40u

/* The synth's level on the unit: the engine's 24-bit full scale (audio.h)
 * >> 8 is 16-bit full scale; 2 more (-12 dB) keep it nearer the tone
 * until levels are set. */
#define A9_SYN_SHIFT 10u

/* S1: the engine (fm_play, core 0 alone) fills a half. On the unit a half
 * is LEN (128) frames of one word (HW-160): two of the engine's 64-frame
 * blocks, each frame's left sample packed; in fwtest a half is LEN words
 * of its own layout (HW-44), one block of 64 frames as build A plays. */
/* M2: a soft clip on the synth's sum, at 16-bit scale: straight to half
 * full scale, then K + R t / (t + R) above it (t the excess), whose slope
 * is 1 where it starts and which never reaches full scale. */
#define A10_KNEE 16384
#define A10_ROOM 16383

/* Frames a half: the unit's 16-bit layout plays twice fwtest's (HW-160). */
#define A8_FRAMES (2u * AUDIO_FRAMES)

#define BLACK  RGB565(0, 0, 0)
#define WHITE  RGB565(31, 63, 31)
#define GREEN  RGB565(0, 63, 0)
#define RED    RGB565(31, 0, 0)
#define YELLOW RGB565(31, 63, 0)
#define DIM    RGB565(16, 32, 16)

#define HW_AUD_BOX_X 150u

/* --- The page ------------------------------------------------------------- */

#define PAGE_REGS_Y 56u
#define GUIDE_N (sizeof guide / sizeof guide[0])
#define GUIDE_BLINK_MS 500u
#define INST_STACK_LOW 512u     /* bytes left: round 3's floor (clean-r3-store, section 5); 256 in round 2 */

void report(const char *label);
u32 a11_fields(u32 ch, u32 set);
void cv_start(u32 ch);
void cv_record(u32 ch, u32 set, u32 v, u32 d);
void read_master(void);
void tone_block(s32 *out, u32 frames);
u32 put_words(u32 *w, u32 n, const u32 *v, u32 k);
u32 cv_sweep_next(void);
void a12_sweep_step(u32 fr);
u32 a12_running(void);
void a13_u2c_record(u32 ch, u32 v);
void a13_arp_take(u32 t);
void a9_capture(const s32 *out);

extern const u8 l_con3[3];
extern volatile u32 cv_busy, cv_hold;
extern u32 cv_ch, cv_set, cv_t0, cv_turn, cv_next, cv_pot_new, cv_pot_v, cv_swept;
extern u32 phase, gain, tone_on, storm_beat, storm_n;
void a13_u2c_record(u32 ch, u32 v);
void a13_arp_take(u32 t);

#endif
