/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * audio1 (SB_HW_AUDIO1, with SB_HW_FM1; BR-17, clean-br17-audio1): a
 * first audio probe for the unit. It tells the next unit run whether the
 * audio link ALNK0 runs on the chip, at what rate, and whether any sound
 * comes out. It is a probe, not the synth.
 *
 * - The output: ALNK0 set up as audio.c does in fwtest (HW-43 to HW-45),
 *   playing from data 3 (ADR3, HW-44). No pin-map register is written:
 *   HARDWARE-SPEC names ALNK0's group A pins on port C (HW-141) but not
 *   the register that selects the group, nor the port set-up the link
 *   needs (SR-20). So the four pins, PC0, PC1, PC2 and PC6, are left as
 *   they are, and no other pin is driven.
 * - The sound: a 440 Hz sine, the same in both channels, at most -20 dB
 *   of full scale, scaled by MASTER (HW-133), ramped in and out over
 *   about 20 ms. It starts once the test screen is up; PLAY stops and
 *   starts it (the output keeps running, so the rate is measured either
 *   way).
 * - Read, never written: PLL2_CON0 and CLK_CON2 (HW-142); JL_ANA's
 *   DAA_CON0 to DAA_CON3, DAA_CON7 and ADA_CON0 to ADA_CON2 (HW-140);
 *   JL_AUDIO's DAC_CON; ALNK0's CON0 to CON3; JL_IOMAP's CON0 and CON1
 *   and port C's OUT, DIR, DIE, PU and PD (HW-56). Once at main's start,
 *   as m-bootloader's call left them (HW-119; nothing of this build has
 *   run but the panel's bring-up, hw_early, which set IOMAP CON1 bit 4
 *   and PC7 to PC10), and once with the tone running.
 * - Whether ALNK0 runs: source 11's interrupts counted (sb_audio.blocks),
 *   the halves alternating as CON0 bit 15 says (an interrupt that finds
 *   the other half free is counted in sb_audio.underruns), and the halves
 *   timed against TIMER0 (sb_now: the 60 MHz low-speed bus, HW-119), as
 *   frames a second. In fwtest, whose TIMER0 counts 24 MHz (HW-48), that
 *   reads 2.5 times fwtest's 44 117.6.
 * - A guard: if source 11 fires far faster than a half's length allows
 *   (its flag not clearing on the chip, say), the source is disabled and
 *   the output stopped, so main keeps running and the screen says so.
 *
 * audio2 (clean-br17-audio2) adds the CLK_CON2 bit 9 step on REC.
 * audio3 (clean-br17-audio3; the owner's approval of 2026-11-20): on the
 * unit core 1 counted from its release, then stopped once ALNK0 was
 * told to run, and ran only while the clock step was taken. audio3
 * records core 1's count at fixed points (its release, around
 * audio_start, around each key's write, on the page), with the beat it
 * was last seen to change; SEQ stops ALNK0 by clearing CON0 bit 11 alone
 * (HW-43; no clock step) and a second press writes back the CON0 read
 * before; core 1's flag and count sit in a 64-byte block of their own
 * (hw_fm1.h); and the page's third view shows all this with the corex2
 * words 0x80 to 0x8F (Q-17) at the page's start and at the view.
 *
 * audio3's steps (the spec side's clean-br17-audio3, HW-147 to HW-149;
 * both allowed by the owner), each by its own key, each undone by a
 * second press of it (the value read before put back):
 * - A (ARP): with CLK_CON2 bit 9 set by REC, ALNK0's CON0 bit 11 cleared
 *   and then set again (HW-45's start, fwtest's), CON0 read back after
 *   each write. A probe: no source says a restart is needed (HW-148).
 * - B (SAVE): with bit 9 set, CLK_CON2 bit 8 set by read-modify-write of
 *   that bit alone (HW-145's other clock choice, the SDK's switched-off
 *   definitions only).
 * A and B are refused unless bit 9 reads set, and REC's undo is refused
 * while B is taken, so B's undo puts CLK_CON2 back first. Each step
 * keeps a snapshot before and 100 ms after its last press (CON0,
 * CLK_CON2, source 11's interrupts, core 1's count); a step's key shows
 * the page's steps view and core 1's view, HOME all four views.
 */

#include "sb.h"
#include "audio.h"
#include "input.h"
#include "hw_fm1.h"
#include "WL82.h"

#if defined(SB_HW_FM1) && defined(SB_HW_AUDIO1)

#if defined(SB_HW_FINDER)
#error "SB_HW_AUDIO1 and SB_HW_FINDER both take HOME: build one or the other"
#endif

#define REG(a) (*(volatile u32 *)(a))
#define SRC_ALNK 11u
/* Q-17: the corex2 words 0x80 to 0x8F, per-core counters, read only. */
#define COREX2_WORD(i) REG(0x01EEE000u + 4u * (0x80u + (i)))
/* HW-43: CON0 bit 11 runs ALNK0. */
#define AL_RUN (1u << 11)

struct hw_audio hw_aud;

static char *put_s(char *p, const char *s);
static char *put_hex(char *p, u32 v, u32 digits);

/* The registers read, in hw_aud.regs' order (hw_fm1.h, HW_AUD_REGS). */
static const char reg_name[HW_AUD_REGS][6] = {
    "PLL2", "CLK2", "DAA0", "DAA1", "DAA2", "DAA3", "DAA7", "ADA0", "ADA1", "ADA2",
    "DAC", "AL0", "AL1", "AL2", "AL3", "MAP0", "MAP1",
    "PCOUT", "PCDIR", "PCDIE", "PCPU", "PCPD",
};

static void read_regs(u32 *r)
{
    r[0] = JL_ANA->PLL2_CON0;
    r[1] = JL_CLOCK->CLK_CON2;
    r[2] = JL_ANA->DAA_CON0;
    r[3] = JL_ANA->DAA_CON1;
    r[4] = JL_ANA->DAA_CON2;
    r[5] = JL_ANA->DAA_CON3;
    r[6] = JL_ANA->DAA_CON7;
    r[7] = JL_ANA->ADA_CON0;
    r[8] = JL_ANA->ADA_CON1;
    r[9] = JL_ANA->ADA_CON2;
    r[10] = JL_AUDIO->DAC_CON;
    r[11] = JL_ALNK0->CON0;
    r[12] = JL_ALNK0->CON1;
    r[13] = JL_ALNK0->CON2;
    r[14] = JL_ALNK0->CON3;
    r[15] = REG(0x0005101Cu);          /* JL_IOMAP->CON0 (HW-56) */
    r[16] = REG(0x00051020u);          /* JL_IOMAP->CON1 */
    r[17] = REG(0x00050080u);          /* JL_PORTC: OUT, DIR, DIE, PU, PD */
    r[18] = REG(0x00050088u);
    r[19] = REG(0x0005008Cu);
    r[20] = REG(0x00050090u);
    r[21] = REG(0x00050094u);
}

/* audio2: the clock, PLL and pin-map words (HW-144 to HW-146), read only. */
static const char more_name[HW_AUD_MORE][6] = {
    "CLK0", "CLK1", "SYSDV", "PLL0", "PLL1", "PL2_1",
    "MAP2", "MAP3", "MAP4", "MAP5", "MAP6", "MAP7", "MAP8",
};

static void read_more(u32 *r)
{
    u32 i;

    r[0] = JL_CLOCK->CLK_CON0;
    r[1] = JL_CLOCK->CLK_CON1;
    r[2] = JL_CLOCK->SYS_DIV;
    r[3] = JL_ANA->PLL_CON0;
    r[4] = JL_ANA->PLL_CON1;
    r[5] = JL_ANA->PLL2_CON1;
    for (i = 0; i < 7; i++)
        r[6 + i] = REG(0x00051024u + 4u * i);   /* JL_IOMAP->CON2 to CON8 */
}

/* --- audio3: core 1's count -------------------------------------------- */

/* The beat the count was last seen to change. */
static void c1_poll(void)
{
    u32 c = hw_core1_count;

    if (c != hw_aud.c1_seen) {
        hw_aud.c1_seen = c;
        hw_aud.c1_moved = sb_beacon.beats;
    }
}

void hw_c1_mark(u32 i)
{
    hw_aud.c1_beat[i] = sb_beacon.beats;
    hw_aud.c1_count[i] = hw_core1_count;
    c1_poll();
}

static void c1_wait(u32 ms)
{
    u32 t = sb_beacon.beats;

    while (sb_beacon.beats - t < ms)
        c1_poll();
}

/* After a key's write: the count then, 10 ms and 100 ms later. */
static void c1_key_marks(void)
{
    hw_c1_mark(HW_C1_KEY);
    c1_wait(10);
    hw_c1_mark(HW_C1_K10);
    c1_wait(90);
    hw_c1_mark(HW_C1_K100);
}

static void read_x2(u32 *w)
{
    u32 i;

    for (i = 0; i < 16; i++)
        w[i] = COREX2_WORD(i);
}

void hw_audio_boot(void)
{
    read_regs(hw_aud.regs[0]);
    read_more(hw_aud.more[0]);
}

/* --- audio2's clock step (HW-145; the owner's ruling) --------------------- */

#define CLK2_ALNK0_EN (1u << 9)
#define CLK2_CLK_SEL  (1u << 8)

static char step_text[40];

/* A step's snapshot: CON0, CLK_CON2, source 11's interrupts, core 1's count. */
static void snap(u32 k, u32 when)
{
    u32 *v = hw_aud.snap[k][when];

    v[0] = JL_ALNK0->CON0;
    v[1] = JL_CLOCK->CLK_CON2;
    v[2] = sb_audio.blocks;
    v[3] = hw_core1_count;
}

/* A step's key refused: said on the step row, counted, nothing written. */
static void refuse(u32 k, const char *why)
{
    hw_step(why);
    hw_aud.refused++;
    snap(k, 1);
}

/* After a step that may start or change the link: a fresh base for the
 * frames a second, taken from the next half the handler sees. */
static void fresh_base(void)
{
    hw_aud.n0_set = 0;
}

/* A key press: CLK_CON2 read, bit 9 alone set, written back and read back;
 * the next press writes back exactly the value read before, and the one
 * after that takes the step again. Nothing else of CLK_CON2 changes (its
 * low byte, bit 8 and bits 10 and 11 stay as read), and nothing else is
 * written. The step row names each write before it is made, so a hang
 * shows which; then the registers are read again. */
void hw_audio_step(void)
{
    char *p;

    snap(HW_K_REC, 0);
    if (hw_aud.step_state == HW_STEP_TAKEN && hw_aud.b_state == HW_STEP_TAKEN) {
        refuse(HW_K_REC, "audio3: REC undo refused: undo B first");
        return;
    }
    if (hw_aud.step_state != HW_STEP_TAKEN) {
        u32 v = JL_CLOCK->CLK_CON2;

        hw_aud.clk_before = v;
        p = put_s(step_text, "audio2: CLK_CON2 ");
        p = put_hex(p, v, 8);
        p = put_s(p, " |bit 9");
        *p = 0;
        hw_step(step_text);
        JL_CLOCK->CLK_CON2 = v | CLK2_ALNK0_EN;
        hw_aud.clk_set = JL_CLOCK->CLK_CON2;
        hw_aud.step_state = HW_STEP_TAKEN;
        p = put_s(step_text, "audio2: bit 9 set, reads ");
    } else {
        p = put_s(step_text, "audio2: CLK_CON2 back to ");
        p = put_hex(p, hw_aud.clk_before, 8);
        *p = 0;
        hw_step(step_text);
        JL_CLOCK->CLK_CON2 = hw_aud.clk_before;
        hw_aud.clk_back = JL_CLOCK->CLK_CON2;
        hw_aud.step_state = HW_STEP_UNDONE;
        p = put_s(step_text, "audio2: put back, reads ");
    }
    p = put_hex(p, JL_CLOCK->CLK_CON2, 8);
    *p = 0;
    hw_step(step_text);
    hw_aud.steps++;
    fresh_base();
    c1_key_marks();
    snap(HW_K_REC, 1);
    read_regs(hw_aud.regs_step);
    read_more(hw_aud.more[2]);
}

/* --- audio3's ALNK0 stop (HW-43; the owner's approval) -------------------- */

/* SEQ: ALNK0's CON0 read, bit 11 alone cleared, written and read back; the
 * next press writes back exactly the CON0 read before, and the one after
 * that stops it again. Nothing else is written: not CLK_CON2, not the
 * interrupt's set-up, not ALNK0's other registers. As with REC, the step
 * row names each write before it is made. */
void hw_audio_alnk(void)
{
    char *p;

    snap(HW_K_SEQ, 0);
    if (hw_aud.al_state != HW_AL_STOPPED) {
        u32 v = JL_ALNK0->CON0;

        hw_aud.al_before = v;
        p = put_s(step_text, "audio3: AL CON0 ");
        p = put_hex(p, v, 8);
        p = put_s(p, " &~bit 11");
        *p = 0;
        hw_step(step_text);
        hw_aud.al_blocks_stop = sb_audio.blocks;
        JL_ALNK0->CON0 = v & ~AL_RUN;
        hw_aud.al_stop = JL_ALNK0->CON0;
        hw_aud.al_state = HW_AL_STOPPED;
        p = put_s(step_text, "audio3: bit 11 cleared, reads ");
    } else {
        p = put_s(step_text, "audio3: AL CON0 back to ");
        p = put_hex(p, hw_aud.al_before, 8);
        *p = 0;
        hw_step(step_text);
        hw_aud.al_blocks_back = sb_audio.blocks;
        JL_ALNK0->CON0 = hw_aud.al_before;
        hw_aud.al_back = JL_ALNK0->CON0;
        hw_aud.al_state = HW_AL_BACK;
        fresh_base();
        p = put_s(step_text, "audio3: put back, reads ");
    }
    p = put_hex(p, JL_ALNK0->CON0, 8);
    *p = 0;
    hw_step(step_text);
    hw_aud.al_keys++;
    c1_key_marks();
    snap(HW_K_SEQ, 1);
}

/* --- audio3's steps A and B (HW-45, HW-145, HW-148; the owner's rulings) - */

/* ARP: step A. With bit 9 set, CON0 read, bit 11 cleared (written, read
 * back), then set again (written, read back); the next press writes back
 * exactly the CON0 read before. Nothing else is written. */
void hw_audio_a(void)
{
    char *p;

    snap(HW_K_A, 0);
    if (hw_aud.a_state != HW_STEP_TAKEN) {
        u32 v;

        if (!(JL_CLOCK->CLK_CON2 & CLK2_ALNK0_EN)) {
            refuse(HW_K_A, "audio3: A refused: bit 9 not set (REC)");
            return;
        }
        v = JL_ALNK0->CON0;
        hw_aud.a_before = v;
        p = put_s(step_text, "audio3: A: CON0 ");
        p = put_hex(p, v, 8);
        p = put_s(p, " -bit 11");
        *p = 0;
        hw_step(step_text);
        JL_ALNK0->CON0 = v & ~AL_RUN;
        hw_aud.a_clr = JL_ALNK0->CON0;
        p = put_s(step_text, "audio3: A: cleared, ");
        p = put_hex(p, hw_aud.a_clr, 8);
        p = put_s(p, " +bit 11");
        *p = 0;
        hw_step(step_text);
        JL_ALNK0->CON0 = (v & ~AL_RUN) | AL_RUN;
        hw_aud.a_set = JL_ALNK0->CON0;
        hw_aud.a_state = HW_STEP_TAKEN;
        p = put_s(step_text, "audio3: A taken, CON0 reads ");
    } else {
        p = put_s(step_text, "audio3: A undo: CON0 to ");
        p = put_hex(p, hw_aud.a_before, 8);
        *p = 0;
        hw_step(step_text);
        JL_ALNK0->CON0 = hw_aud.a_before;
        hw_aud.a_back = JL_ALNK0->CON0;
        hw_aud.a_state = HW_STEP_UNDONE;
        p = put_s(step_text, "audio3: A undone, CON0 reads ");
    }
    p = put_hex(p, JL_ALNK0->CON0, 8);
    *p = 0;
    hw_step(step_text);
    hw_aud.a_keys++;
    fresh_base();
    c1_key_marks();
    snap(HW_K_A, 1);
}

/* SAVE: step B. With bit 9 set, CLK_CON2 read and written with bit 8
 * alone added, read back; the next press writes back exactly the value
 * read before. Its low byte and bits 9 to 11 stay as read. */
void hw_audio_b(void)
{
    char *p;

    snap(HW_K_B, 0);
    if (hw_aud.b_state != HW_STEP_TAKEN) {
        u32 v = JL_CLOCK->CLK_CON2;

        if (!(v & CLK2_ALNK0_EN)) {
            refuse(HW_K_B, "audio3: B refused: bit 9 not set (REC)");
            return;
        }
        hw_aud.b_before = v;
        p = put_s(step_text, "audio3: B: CLK_CON2 ");
        p = put_hex(p, v, 8);
        p = put_s(p, " |bit 8");
        *p = 0;
        hw_step(step_text);
        JL_CLOCK->CLK_CON2 = v | CLK2_CLK_SEL;
        hw_aud.b_set = JL_CLOCK->CLK_CON2;
        hw_aud.b_state = HW_STEP_TAKEN;
        p = put_s(step_text, "audio3: B taken, reads ");
    } else {
        p = put_s(step_text, "audio3: B undo: CLK_CON2 to ");
        p = put_hex(p, hw_aud.b_before, 8);
        *p = 0;
        hw_step(step_text);
        JL_CLOCK->CLK_CON2 = hw_aud.b_before;
        hw_aud.b_back = JL_CLOCK->CLK_CON2;
        hw_aud.b_state = HW_STEP_UNDONE;
        p = put_s(step_text, "audio3: B undone, reads ");
    }
    p = put_hex(p, JL_CLOCK->CLK_CON2, 8);
    *p = 0;
    hw_step(step_text);
    hw_aud.b_keys++;
    fresh_base();
    c1_key_marks();
    snap(HW_K_B, 1);
}

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

static u32 phase, gain, tone_on = 1, storm_beat, storm_n;

/* A sine of the phase's top 16 bits, +-32767 (the phase offset by half a
 * turn): a parabola, 4 x (1 - |x|) for x = -1 .. 1 as -32768 .. 32767,
 * corrected (y + 0.225 (y |y| - y)), within about 0.1 % of a sine. */
static s32 sine(u32 ph)
{
    s32 x = (s32)(ph >> 16) - 32768;
    s32 ax = x < 0 ? -x : x;
    s32 y = x * (32768 - ax) >> 13;
    s32 ay = y < 0 ? -y : y;

    y += ((y * ay >> 15) - y) * 7373 >> 15;
    if (y > 32767)
        y = 32767;
    if (y < -32767)
        y = -32767;
    return y;
}

/* MASTER (0 to 1023) into hw_aud.master: from the engine for the tone's
 * level, and from the page, so the page shows it even when source 11
 * never fires (audio1 on the unit showed "vol 0" with ALNK0 not running). */
static void read_master(void)
{
    int m = input_value(INPUT_MASTER);

    hw_aud.master = m < 0 ? 0u : m > 1023 ? 1023u : (u32)m;
}

static void storm(void)
{
    JL_ALNK0->CON0 = 0;
    sb_irq_disable(SRC_ALNK);
    hw_aud.storm = sb_beacon.beats ? sb_beacon.beats : 1;
}

/* The engine (audio.h): one block, and the probe's measures. */
static void tone_block(s32 *out, u32 frames)
{
    u32 n, b = sb_beacon.beats, t = sb_now(), want;

    if (b != storm_beat) {
        storm_beat = b;
        storm_n = 0;
    }
    if (++storm_n > STORM_PER_BEAT) {
        storm();
        return;
    }
    /* The halves' times, with a sequence for main to read them whole. */
    hw_aud.seq++;
    if (!hw_aud.n0_set) {
        hw_aud.n0 = sb_audio.blocks;
        hw_aud.t0 = t;
        hw_aud.n0_set = 1;
    } else if (t - hw_aud.t0 > 120u * 24000000u) {
        /* sb_now wraps at 179 s: a fresh base every two minutes. */
        hw_aud.n0 = sb_audio.blocks;
        hw_aud.t0 = t;
    }
    hw_aud.n1 = sb_audio.blocks;
    hw_aud.t1 = t;
    hw_aud.seq++;

    read_master();
    want = tone_on ? GAIN_TOP * hw_aud.master / 1023u : 0;
    for (n = 0; n < frames; n++) {
        s32 s;

        if (gain + GAIN_STEP <= want)
            gain += GAIN_STEP;
        else if (gain >= want + GAIN_STEP)
            gain -= GAIN_STEP;
        else
            gain = want;
        s = (s32)((sine(phase) * (s32)gain) >> 11);
        phase += TONE_STEP;
        out[2 * n] = s;
        out[2 * n + 1] = s;
    }
    hw_aud.gain = gain;
}

void hw_audio_start(void)
{
    hw_aud.tone_on = 1;
    hw_c1_mark(HW_C1_PRE);
    audio_start(tone_block);
    hw_c1_mark(HW_C1_POST);
    hw_aud.started = sb_beacon.beats ? sb_beacon.beats : 1;
    c1_wait(10);
    hw_c1_mark(HW_C1_P10);
    c1_wait(90);
    hw_c1_mark(HW_C1_P100);
}

void hw_audio_toggle(void)
{
    tone_on ^= 1;
    hw_aud.tone_on = tone_on;
}

/* u64 / u32 by shifts: no division helper is linked in this build. */
static u32 div64(u64 a, u32 b)
{
    u64 q = 0, r = 0;
    int i;

    if (!b)
        return 0;
    for (i = 63; i >= 0; i--) {
        r = r << 1 | (a >> i & 1u);
        if (r >= b) {
            r -= b;
            q |= 1ull << i;
        }
    }
    return (u32)q;
}

/* Frames a second, times ten, over the span since the base: 0 until it
 * is a second long (sb_now's 24 MHz units). */
static void measure(void)
{
    u32 s, n0, n1, t0, t1;

    do {
        s = hw_aud.seq;
        n0 = hw_aud.n0;
        t0 = hw_aud.t0;
        n1 = hw_aud.n1;
        t1 = hw_aud.t1;
    } while ((s & 1) || s != hw_aud.seq);
    hw_aud.halves = n1 - n0;
    hw_aud.units = t1 - t0;
    if (hw_aud.units >= 24000000u && n1 != n0)
        hw_aud.fps10 = div64((u64)(n1 - n0) * AUDIO_FRAMES * 240000000ull, t1 - t0);
}

/* --- Text ----------------------------------------------------------------- */

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

static char *put_fps(char *p)
{
    p = put_dec(p, hw_aud.fps10 / 10);
    *p++ = '.';
    return put_dec(p, hw_aud.fps10 % 10);
}

#define BLACK  RGB565(0, 0, 0)
#define WHITE  RGB565(31, 63, 31)
#define GREEN  RGB565(0, 63, 0)
#define RED    RGB565(31, 0, 0)
#define YELLOW RGB565(31, 63, 0)
#define DIM    RGB565(16, 32, 16)

#define HW_AUD_BOX_X 196u

static char state_char(u32 st)
{
    return st == HW_STEP_TAKEN ? 'T' : st == HW_STEP_UNDONE ? 'U' : '-';
}

static u32 verdict_colour(void)
{
    if (hw_aud.storm)
        return RGB565(31, 0, 31);
    return sb_audio.blocks ? GREEN : RED;
}

/* The test screen's line (HW_AUD_Y, scale 2), once a second: source 11's
 * interrupts and the frames a second; "STORM" if the guard stopped it. */
void hw_audio_line(void)
{
    char t[32], *p = t;

    measure();
    p = put_s(p, hw_aud.storm ? "STORM " : "A ");
    p = put_dec(p, sb_audio.blocks);
    *p++ = ' ';
    p = put_fps(p);
    *p = 0;
    c1_poll();
    gfx_fill(4, HW_AUD_Y, SCREEN_W - 8, 2 * FONT_H, BLACK);
    gfx_text(6, HW_AUD_Y, t, verdict_colour(), BLACK, 2);
    /* The steps' states at the right, at scale 1 (over the line's tail
     * if it is long): R (REC, bit 9) and S (SEQ) above, A and B below;
     * T taken, U undone, S stopped, R put back, - never pressed. */
    p = put_s(t, "R");
    *p++ = state_char(hw_aud.step_state);
    p = put_s(p, " S");
    *p++ = hw_aud.al_state == HW_AL_STOPPED ? 'S' : hw_aud.al_state == HW_AL_BACK ? 'R' : '-';
    *p = 0;
    gfx_fill(HW_AUD_BOX_X - 2, HW_AUD_Y, SCREEN_W - HW_AUD_BOX_X - 2, 2 * FONT_H, BLACK);
    gfx_text(HW_AUD_BOX_X, HW_AUD_Y, t, WHITE, BLACK, 1);
    p = put_s(t, "A");
    *p++ = state_char(hw_aud.a_state);
    p = put_s(p, " B");
    *p++ = state_char(hw_aud.b_state);
    *p = 0;
    gfx_text(HW_AUD_BOX_X, HW_AUD_Y + FONT_H, t, WHITE, BLACK, 1);
    lcd_send_rows(HW_AUD_Y, 2 * FONT_H);
    lcd_wait();
}

/* --- The page ------------------------------------------------------------- */

#define PAGE_REGS_Y 56u

static void page_top(void)
{
    char t[40], *p;

    measure();
    read_master();
    gfx_fill(0, 0, SCREEN_W, PAGE_REGS_Y, BLACK);
    p = put_s(t, "IRQ ");
    p = put_dec(p, sb_audio.blocks);
    p = put_s(p, " b15 ");
    p = put_dec(p, hw_aud.flips);
    *p = 0;
    gfx_text(6, 0, t, verdict_colour(), BLACK, 2);
    p = put_s(t, "fps ");
    p = put_fps(p);
    *p = 0;
    gfx_text(6, 16, t, verdict_colour(), BLACK, 2);
    p = put_s(t, "h/s ");
    p = put_dec(p, hw_aud.units >= 24000000u ? div64((u64)hw_aud.halves * 24000000u, hw_aud.units) : 0);
    p = put_s(p, hw_aud.storm ? " STORM" : "");
    *p = 0;
    gfx_text(6, 32, t, verdict_colour(), BLACK, 2);
    p = put_s(t, "alt ");
    p = put_dec(p, sb_audio.underruns);
    p = put_s(p, " pend ");
    p = put_dec(p, hw_aud.pend);
    p = put_s(p, " vol ");
    p = put_dec(p, hw_aud.master);
    p = put_s(p, hw_aud.tone_on ? " on" : " off");
    p = put_s(p, hw_aud.step_state == HW_STEP_TAKEN ? " step TAKEN" :
                 hw_aud.step_state == HW_STEP_UNDONE ? " step UNDONE" : " step no");
    *p = 0;
    gfx_text(6, 48, t, WHITE, BLACK, 1);
    lcd_send_rows(0, PAGE_REGS_Y);
    lcd_wait();
}

/* One table of registers: at the call, with the tone on, after the last
 * step ("--------" before any). View 0 is audio1's; view 1 audio2's. */
static void page_regs(u32 view)
{
    char t[48], *p;
    u32 i, n = view ? HW_AUD_MORE : HW_AUD_REGS, y = PAGE_REGS_Y;

    gfx_fill(0, PAGE_REGS_Y, SCREEN_W, SCREEN_H - PAGE_REGS_Y, BLACK);
    p = put_s(t, view ? "2/4 reg  call     tone     " : "1/4 reg  call     tone     ");
    p = put_s(p, hw_aud.step_state == HW_STEP_TAKEN ? "taken" : hw_aud.step_state == HW_STEP_UNDONE ? "undone" : "no step");
    *p = 0;
    gfx_text(6, y, t, DIM, BLACK, 1);
    for (i = 0; i < n; i++) {
        u32 a = view ? hw_aud.more[0][i] : hw_aud.regs[0][i];
        u32 b = view ? hw_aud.more[1][i] : hw_aud.regs[1][i];
        u32 c = view ? hw_aud.more[2][i] : hw_aud.regs_step[i];

        p = put_s(t, view ? more_name[i] : reg_name[i]);
        while (p < t + 6)
            *p++ = ' ';
        p = put_hex(p, a, 8);
        *p++ = ' ';
        p = put_hex(p, b, 8);
        *p++ = ' ';
        p = hw_aud.steps ? put_hex(p, c, 8) : put_s(p, "--------");
        *p = 0;
        y += FONT_H;
        gfx_text(6, y, t, a != b || (hw_aud.steps && b != c) ? YELLOW : WHITE, BLACK, 1);
    }
    if (view) {
        y += FONT_H;
        gfx_text(6, y, "pins and map: none written (SR-20)", DIM, BLACK, 1);
        y += FONT_H;
        p = put_s(t, "CLK2 ");
        p = put_hex(p, hw_aud.clk_before, 8);
        p = put_s(p, " > ");
        p = put_hex(p, hw_aud.clk_set, 8);
        p = put_s(p, " > ");
        p = put_hex(p, hw_aud.clk_back, 8);
        *p = 0;
        gfx_text(6, y, t, WHITE, BLACK, 1);
    }
    lcd_send_rows(PAGE_REGS_Y, SCREEN_H - PAGE_REGS_Y);
    lcd_wait();
}

/* The core 1 view: core 1's count at the fixed points (beat, count,
 * "+" where it moved since the mark before), the beat it was last seen to
 * change, its rate (counts a beat, from its release to audio_start),
 * ALNK0's stop by SEQ, and the corex2 words at the page's start (left)
 * and at this view (right; yellow where they changed). */
static const char mark_name[HW_C1_MARKS][6] = {
    "rel", "pre", "post", "+10", "+100", "s0", "s1", "poll", "key", "k+10", "k+100", "page", "now",
};

static void page_core1(void)
{
    char t[48], *p;
    u32 i, y = PAGE_REGS_Y, db, rate = 0;

    gfx_fill(0, PAGE_REGS_Y, SCREEN_W, SCREEN_H - PAGE_REGS_Y, BLACK);
    for (i = 0; i < HW_C1_MARKS; i++) {
        u32 moved = i && hw_aud.c1_count[i] != hw_aud.c1_count[i - 1];

        p = put_s(t, mark_name[i]);
        while (p < t + 6)
            *p++ = ' ';
        if (hw_aud.c1_beat[i] || hw_aud.c1_count[i]) {
            p = put_dec(p, hw_aud.c1_beat[i]);
            while (p < t + 16)
                *p++ = ' ';
            p = put_dec(p, hw_aud.c1_count[i]);
            p = put_s(p, moved ? " +" : "");
        } else {
            p = put_s(p, "-");
        }
        *p = 0;
        gfx_text(6, y, t, moved ? GREEN : WHITE, BLACK, 1);
        y += FONT_H;
    }
    db = hw_aud.c1_beat[HW_C1_PRE] - hw_aud.c1_beat[HW_C1_REL];
    if (db)
        rate = div64(hw_aud.c1_count[HW_C1_PRE] - hw_aud.c1_count[HW_C1_REL], db);
    p = put_s(t, "3/4 moved ");
    p = put_dec(p, hw_aud.c1_moved);
    p = put_s(p, " now ");
    p = put_dec(p, sb_beacon.beats);
    p = put_s(p, " r ");
    p = put_dec(p, rate);
    *p = 0;
    gfx_text(6, y, t, YELLOW, BLACK, 1);
    y += FONT_H;
    p = put_s(t, "SEQ ");
    p = put_hex(p, hw_aud.al_before, 8);
    p = put_s(p, ">");
    p = put_hex(p, hw_aud.al_stop, 8);
    p = put_s(p, ">");
    p = put_hex(p, hw_aud.al_back, 8);
    p = put_s(p, hw_aud.al_state == HW_AL_STOPPED ? " stop" : hw_aud.al_state == HW_AL_BACK ? " back" : " run");
    *p = 0;
    gfx_text(6, y, t, WHITE, BLACK, 1);
    y += FONT_H;
    for (i = 0; i < 16; i++) {
        p = put_hex(t, 0x80u + i, 2);
        *p++ = ' ';
        p = put_hex(p, hw_aud.x2[0][i], 8);
        *p++ = ' ';
        p = put_hex(p, hw_aud.x2[1][i], 8);
        *p = 0;
        gfx_text(i < 8 ? 0 : 120, y + FONT_H * (i & 7), t, hw_aud.x2[0][i] != hw_aud.x2[1][i] ? YELLOW : WHITE,
                 BLACK, 1);
    }
    lcd_send_rows(PAGE_REGS_Y, SCREEN_H - PAGE_REGS_Y);
    lcd_wait();
}

/* The steps view: each keyed step's state and presses, and its snapshots
 * before and 100 ms after its last press (CON0, CLK_CON2, interrupts,
 * core 1's count), then the same now, and A's and B's readbacks. */
static char *put_snap(char *p, const char *label, const u32 *v)
{
    p = put_s(p, label);
    p = put_hex(p, v[0], 8);
    *p++ = ' ';
    p = put_hex(p, v[1], 8);
    *p++ = ' ';
    p = put_dec(p, v[2]);
    *p++ = ' ';
    return put_dec(p, v[3]);
}

static void page_steps(void)
{
    static const char title[HW_K_N][16] = { "REC  bit 9 ", "SEQ  stop  ", "ARP  A     ", "SAVE B bit8 " };
    char t[48], *p;
    u32 k, y = PAGE_REGS_Y, now[HW_SNAP];

    gfx_fill(0, PAGE_REGS_Y, SCREEN_W, SCREEN_H - PAGE_REGS_Y, BLACK);
    gfx_text(6, y, "4/4 REC=bit9 SEQ=stop ARP=A SAVE=B", YELLOW, BLACK, 1);
    y += FONT_H;
    gfx_text(6, y, "  CON0     CLK2     irq core1", DIM, BLACK, 1);
    for (k = 0; k < HW_K_N; k++) {
        u32 st = k == HW_K_REC ? hw_aud.step_state : k == HW_K_A ? hw_aud.a_state : k == HW_K_B ? hw_aud.b_state : 0;
        u32 n = k == HW_K_REC ? hw_aud.steps : k == HW_K_SEQ ? hw_aud.al_keys : k == HW_K_A ? hw_aud.a_keys : hw_aud.b_keys;

        p = put_s(t, title[k]);
        if (k == HW_K_SEQ)
            p = put_s(p, hw_aud.al_state == HW_AL_STOPPED ? "stopped" : hw_aud.al_state == HW_AL_BACK ? "put back" : "running");
        else
            p = put_s(p, st == HW_STEP_TAKEN ? "taken" : st == HW_STEP_UNDONE ? "undone" : "not taken");
        p = put_s(p, ", presses ");
        p = put_dec(p, n);
        *p = 0;
        y += FONT_H;
        gfx_text(6, y, t, st == HW_STEP_TAKEN || (k == HW_K_SEQ && hw_aud.al_state == HW_AL_STOPPED) ? YELLOW : WHITE,
                 BLACK, 1);
        p = put_snap(t, "b ", hw_aud.snap[k][0]);
        *p = 0;
        y += FONT_H;
        gfx_text(6, y, t, WHITE, BLACK, 1);
        p = put_snap(t, "a ", hw_aud.snap[k][1]);
        *p = 0;
        y += FONT_H;
        gfx_text(6, y, t, WHITE, BLACK, 1);
    }
    now[0] = JL_ALNK0->CON0;
    now[1] = JL_CLOCK->CLK_CON2;
    now[2] = sb_audio.blocks;
    now[3] = hw_core1_count;
    p = put_snap(t, "n ", now);
    *p = 0;
    y += FONT_H;
    gfx_text(6, y, t, GREEN, BLACK, 1);
    p = put_s(t, "A -11 ");
    p = put_hex(p, hw_aud.a_clr, 8);
    p = put_s(p, " +11 ");
    p = put_hex(p, hw_aud.a_set, 8);
    p = put_s(p, " bk ");
    p = put_hex(p, hw_aud.a_back, 8);
    *p = 0;
    y += FONT_H;
    gfx_text(6, y, t, WHITE, BLACK, 1);
    p = put_s(t, "B +8 ");
    p = put_hex(p, hw_aud.b_set, 8);
    p = put_s(p, " bk ");
    p = put_hex(p, hw_aud.b_back, 8);
    p = put_s(p, " refused ");
    p = put_dec(p, hw_aud.refused);
    *p = 0;
    y += FONT_H;
    gfx_text(6, y, t, WHITE, BLACK, 1);
    lcd_send_rows(PAGE_REGS_Y, SCREEN_H - PAGE_REGS_Y);
    lcd_wait();
}

/* The audio page: the counts and the frames a second at the top, redrawn
 * every quarter second, and below them a view at a time, each for a
 * quarter of HW_AUD_PAGE_MS: audio1's registers (at the call, with the
 * tone on and after the last step), audio2's, core 1's, and the steps';
 * the last two redrawn with the top. Meanwhile main polls CON0 bit 15 and
 * CON2 bit 7 itself: the flips of the one, and the times it sees the
 * other set (a half finished whose interrupt hasn't been taken yet). The
 * first time, after a settle, the "tone on" registers are read here, with
 * core 1's count marked before and after. The caller puts the test
 * screen back. */
static void draw_view(u32 v)
{
    if (v < 2)
        page_regs(v);
    else if (v == 2)
        page_core1();
    else
        page_steps();
}

static void page_views(const u8 *order, u32 n)
{
    u32 start, next, last, i = 0, polled = hw_aud.c1_beat[HW_C1_POLL] || hw_aud.c1_count[HW_C1_POLL];

    if (!hw_aud.regs_read) {
        while (sb_beacon.beats - hw_aud.started < HW_AUD_SETTLE_MS)
            c1_poll();
        hw_c1_mark(HW_C1_S0);
        read_regs(hw_aud.regs[1]);
        read_more(hw_aud.more[1]);
        hw_c1_mark(HW_C1_S1);
        hw_aud.regs_read = 1;
    }
    hw_c1_mark(HW_C1_PAGE);
    hw_c1_mark(HW_C1_NOW);
    read_x2(hw_aud.x2[0]);
    read_x2(hw_aud.x2[1]);
    lcd_wait();
    gfx_fill(0, 0, SCREEN_W, SCREEN_H, BLACK);
    draw_view(order[0]);
    page_top();
    start = sb_beacon.beats;
    next = start + 250u;
    last = JL_ALNK0->CON0 & 0x8000u;
    while (sb_beacon.beats - start < n * (HW_AUD_PAGE_MS / 4)) {
        u32 now = JL_ALNK0->CON0 & 0x8000u;

        if (now != last) {
            hw_aud.flips++;
            last = now;
        }
        if (JL_ALNK0->CON2 & 0x80u)
            hw_aud.pend++;
        if (!polled) {
            hw_c1_mark(HW_C1_POLL);
            polled = 1;
        }
        c1_poll();
        if ((int)(sb_beacon.beats - next) >= 0) {
            next += 250u;
            if (i + 1 < n && sb_beacon.beats - start >= (i + 1) * (HW_AUD_PAGE_MS / 4)) {
                i++;
                if (order[i] == 2)
                    read_x2(hw_aud.x2[1]);
                if (order[i] < 2)
                    draw_view(order[i]);
            }
            if (order[i] >= 2) {
                hw_c1_mark(HW_C1_NOW);
                draw_view(order[i]);
            }
            page_top();
        }
    }
}

/* HOME and the first page: all four views. */
void hw_audio_page(void)
{
    static const u8 all[4] = { 0, 1, 2, 3 };

    page_views(all, 4);
}

/* After a step's key: the steps view, then core 1's. */
void hw_audio_keypage(void)
{
    static const u8 keys[2] = { 3, 2 };

    page_views(keys, 2);
}

#endif
