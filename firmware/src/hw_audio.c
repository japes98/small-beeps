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
 * A and B are refused unless bit 9 reads set. Since audio4, of the steps
 * that write CLK_CON2 (REC, B and I), only the one taken last can be
 * undone (each undo writes back the value read before its own press, which
 * would undo a later step's bit behind its back). Each step
 * keeps a snapshot before and 100 ms after its last press (CON0,
 * CLK_CON2, source 11's interrupts, core 1's count); a step's key shows
 * the page's steps view and core 1's view, HOME all the views.
 *
 * audio4's steps (the spec side's clean-br17-audio4, HW-150 to HW-152;
 * both allowed by the owner), each undone by a second press of its key:
 * - H (ENV): JL_GPCNT (HW-151) counts the clock system's input, picked by
 *   CLK_CON1 bits 4-6 (read-modify-write of those bits alone), over a gate
 *   of 32 x 2^HW_H_GATE_N crystal cycles: first the high-speed bus (3; a
 *   check: 180 MHz over 24 MHz, HW-119 and HW-54, is 7.5 times the gate),
 *   then the audio clock (5), in whatever state CLK_CON2 is in. Each takes
 *   two readings of NUM, a gate apart, each after the pending flag (bit 7,
 *   cleared with bit 6), with a timeout. FX measures both again while H is
 *   taken. The undo writes back CLK_CON1 and JL_GPCNT->CON as read.
 * - I (LFO): ALNK1 (0x00015100, HW-140) set up as ALNK0 is in fwtest, from
 *   a buffer of its own, with CLK_CON2 bit 11 set alone; its interrupt
 *   (source 12) is left off, and it is watched by polling CON0 bit 15 and
 *   CON2 bit 7 (cleared with bit 3) for HW_I_POLL_MS. SEL sets bit 10 too
 *   while I is taken. The undo writes back CON0 and CLK_CON2 as read.
 * Every reading goes to the report log as well as the screen.
 */

#include "sb.h"
#include "audio.h"
#include "input.h"
#include "midi_out.h"
#if defined(SB_HW_AUDIO9)
#include "fm.h"
#endif
#if defined(SB_HW_AUDIO12)
#include "ui.h"
#endif
#if defined(SB_HW_AUDIO13)
#include "arp.h"
#endif
#if defined(SB_HW_U3U)
#include "usb_midi.h"
#endif
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
static char *put_dec(char *p, u32 v);
#if defined(SB_HW_AUDIO9)
static char *put_x10(char *p, u32 v);
#endif
static u32 div64(u64 a, u32 b);

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

static char step_text[64];

/* A step's snapshot: CON0, CLK_CON2, source 11's interrupts, core 1's count. */
static void snap(u32 k, u32 when)
{
    u32 *v = hw_aud.snap[k][when];

    v[0] = JL_ALNK0->CON0;
    v[1] = JL_CLOCK->CLK_CON2;
    v[2] = sb_audio.blocks;
    v[3] = hw_core1_count;
}

/* A record in the report log (hw_report.c, SB_HW_REPORT), labelled. */
static void report(const char *label)
{
#if defined(SB_HW_AUDIO10)
    /* audio10's C: while the log is held, records are dropped and counted. */
    if (hw_aud.holds >> HW_A10_LOG & 1u) {
        hw_aud.log_dropped++;
        return;
    }
#endif
#if defined(SB_HW_REPORT)
    hw_report_save(label);
#else
    (void)label;
#endif
}

#if defined(SB_HW_U3U)
/* U3-U (usb_midi.c): a USB stage on the step row and, with a label, a
 * record; main's loop only. */
void usb_midi_note(const char *label, const char *step)
{
    hw_step(step);
    if (label)
        report(label);
}
#endif

/* A step's key refused: said on the step row, counted, nothing written. */
static void refuse(u32 k, const char *why)
{
    static const char label[HW_K_N][16] = { "REC refused", "SEQ refused", "A refused", "B refused", "H refused",
                                            "I refused", "K refused", "J refused" };

    hw_step(why);
    hw_aud.refused++;
    snap(k, 1);
    report(label[k]);
}

/* The CLK_CON2 steps taken, in order (REC, B, I): only the last undoes. */
static const char clk_name[HW_K_N][4] = { "REC", "SEQ", "A", "B", "H", "I", "K", "J" };

static void clk_push(u32 k)
{
    if (hw_aud.clk_depth < 3)
        hw_aud.clk_stack[hw_aud.clk_depth++] = k;
}

static void clk_pop(void)
{
    if (hw_aud.clk_depth)
        hw_aud.clk_depth--;
}

/* 1 if step k's undo may write CLK_CON2 back; if not, it is refused, the
 * step row naming the step to undo first. */
static int clk_may_undo(u32 k)
{
    static char why[64];
    char *p;
    u32 top;

    if (!hw_aud.clk_depth || hw_aud.clk_stack[hw_aud.clk_depth - 1] == k)
        return 1;
    top = hw_aud.clk_stack[hw_aud.clk_depth - 1];
    p = put_s(why, "audio4: ");
    p = put_s(p, clk_name[k]);
    p = put_s(p, " undo refused, undo ");
    p = put_s(p, clk_name[top]);
    p = put_s(p, " first");
    *p = 0;
    refuse(k, why);
    return 0;
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
#if defined(SB_HW_AUDIO8)
/* audio8: after REC's write, the link watched for HW_A8_R9_MS: with bit 9
 * set the PLL's audio clock stops reaching it (HW-160). */
static void r9_watch(void)
{
    u32 start = sb_beacon.beats, irq0 = sb_audio.blocks, last = JL_ALNK0->CON0 & (1u << 15);

    hw_aud.r9_flips = 0;
    hw_aud.r9_clk2 = JL_CLOCK->CLK_CON2;
    while (sb_beacon.beats - start < HW_A8_R9_MS) {
        u32 now = JL_ALNK0->CON0 & (1u << 15);

        if (now != last) {
            hw_aud.r9_flips++;
            last = now;
        }
        c1_poll();
    }
    hw_aud.r9_irq = sb_audio.blocks - irq0;
}
#endif

void hw_audio_step(void)
{
    char *p;

    snap(HW_K_REC, 0);
    if (hw_aud.step_state == HW_STEP_TAKEN && !clk_may_undo(HW_K_REC))
        return;
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
        clk_push(HW_K_REC);
        p = put_s(step_text, "audio2: bit 9 set, reads ");
    } else {
        p = put_s(step_text, "audio2: CLK_CON2 back to ");
        p = put_hex(p, hw_aud.clk_before, 8);
        *p = 0;
        hw_step(step_text);
        JL_CLOCK->CLK_CON2 = hw_aud.clk_before;
        hw_aud.clk_back = JL_CLOCK->CLK_CON2;
        hw_aud.step_state = HW_STEP_UNDONE;
        clk_pop();
        p = put_s(step_text, "audio2: put back, reads ");
    }
    p = put_hex(p, JL_CLOCK->CLK_CON2, 8);
    *p = 0;
    hw_step(step_text);
#if defined(SB_HW_AUDIO8)
    r9_watch();
    hw_step(hw_aud.r9_flips || hw_aud.r9_irq ? "audio8: REC: the link runs" : "audio8: REC: THE LINK STOPPED");
#endif
    hw_aud.steps++;
    fresh_base();
    c1_key_marks();
    snap(HW_K_REC, 1);
    read_regs(hw_aud.regs_step);
    read_more(hw_aud.more[2]);
    report(hw_aud.step_state == HW_STEP_TAKEN ? "REC taken" : "REC undone");
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
#if defined(SB_HW_AUDIO8)
    if (hw_aud.al_state != HW_AL_STOPPED && hw_aud.r2_state == HW_A8_R2_SET) {
        refuse(HW_K_SEQ, "audio8: SEQ refused while R2 is in place");
        return;
    }
#endif
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
    report(hw_aud.al_state == HW_AL_STOPPED ? "SEQ stopped" : "SEQ put back");
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
#if defined(SB_HW_AUDIO8)
        if (hw_aud.r2_state == HW_A8_R2_SET) {
            refuse(HW_K_A, "audio8: A refused while R2 is in place");
            return;
        }
#endif
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
    report(hw_aud.a_state == HW_STEP_TAKEN ? "A taken" : "A undone");
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
        clk_push(HW_K_B);
        p = put_s(step_text, "audio3: B taken, reads ");
    } else {
        if (!clk_may_undo(HW_K_B))
            return;
        p = put_s(step_text, "audio3: B undo: CLK_CON2 to ");
        p = put_hex(p, hw_aud.b_before, 8);
        *p = 0;
        hw_step(step_text);
        JL_CLOCK->CLK_CON2 = hw_aud.b_before;
        hw_aud.b_back = JL_CLOCK->CLK_CON2;
        hw_aud.b_state = HW_STEP_UNDONE;
        clk_pop();
        p = put_s(step_text, "audio3: B undone, reads ");
    }
    p = put_hex(p, JL_CLOCK->CLK_CON2, 8);
    *p = 0;
    hw_step(step_text);
    hw_aud.b_keys++;
    fresh_base();
    c1_key_marks();
    snap(HW_K_B, 1);
    report(hw_aud.b_state == HW_STEP_TAKEN ? "B taken" : "B undone");
}

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

/* One measurement: CLK_CON1 bits 4-6 set to sel (those bits alone), the
 * counter set to count that clock over the gate, and two readings of NUM,
 * each after the pending flag or a timeout, the flag cleared after each. */
static void h_measure(u32 sel, u32 *num, u32 *to, u32 *clk1, u32 *gp, u32 *clk2)
{
    u32 v = JL_CLOCK->CLK_CON1, g = HW_H_GATE_N << 8 | GP_GSS_XOSC | GP_CSS_INPUT, i, t;

    JL_CLOCK->CLK_CON1 = (v & ~CLK1_SEL) | sel << 4;
    *clk1 = JL_CLOCK->CLK_CON1;
    JL_GPCNT->CON = g | GP_CLR;
    JL_GPCNT->CON = g | GP_CLR | GP_EN;
    *gp = JL_GPCNT->CON;
    *clk2 = JL_CLOCK->CLK_CON2;
    *to = 0;
    for (i = 0; i < 2; i++) {
        t = sb_beacon.beats;
        while (!(JL_GPCNT->CON & GP_PND) && sb_beacon.beats - t < HW_H_WAIT_MS)
            c1_poll();
        if (!(JL_GPCNT->CON & GP_PND))
            (*to)++;
        num[i] = JL_GPCNT->NUM;
        JL_GPCNT->CON = g | GP_CLR | GP_EN;
    }
}

static void h_both(void)
{
    char *p;

    hw_step("audio4: H: counting the high-speed bus");
    h_measure(CLK1_HSB, hw_aud.h_check, &hw_aud.h_check_to, &hw_aud.h_clk1_check, &hw_aud.h_gp_check,
              &hw_aud.h_check_clk2);
    hw_step("audio4: H: counting the audio clock");
    h_measure(CLK1_AUDIO, hw_aud.h_audio, &hw_aud.h_audio_to, &hw_aud.h_clk1_audio, &hw_aud.h_gp_audio,
              &hw_aud.h_audio_clk2);
    hw_aud.h_measures++;
    p = put_s(step_text, "audio4: H: bus ");
    p = put_dec(p, hw_aud.h_check[1]);
    p = put_s(p, " audio ");
    p = put_dec(p, hw_aud.h_audio[1]);
    *p = 0;
    hw_step(step_text);
}

/* ENV: step H; a second press undoes it. */
void hw_audio_h(void)
{
    char *p;

    snap(HW_K_H, 0);
    if (hw_aud.h_state != HW_STEP_TAKEN && hw_aud.k_state == HW_STEP_TAKEN) {
        refuse(HW_K_H, "audio5: H refused: undo K first (GLO)");
        return;
    }
    if (hw_aud.h_state != HW_STEP_TAKEN) {
        hw_aud.h_clk1_before = JL_CLOCK->CLK_CON1;
        hw_aud.h_gp_before = JL_GPCNT->CON;
        p = put_s(step_text, "audio4: H: CLK_CON1 ");
        p = put_hex(p, hw_aud.h_clk1_before, 8);
        p = put_s(p, " b4-6");
        *p = 0;
        hw_step(step_text);
        h_both();
        hw_aud.h_state = HW_STEP_TAKEN;
    } else {
        p = put_s(step_text, "audio4: H undo: CLK_CON1 to ");
        p = put_hex(p, hw_aud.h_clk1_before, 8);
        *p = 0;
        hw_step(step_text);
        JL_CLOCK->CLK_CON1 = hw_aud.h_clk1_before;
        hw_aud.h_clk1_back = JL_CLOCK->CLK_CON1;
        JL_GPCNT->CON = hw_aud.h_gp_before;
        hw_aud.h_gp_back = JL_GPCNT->CON;
        hw_aud.h_state = HW_STEP_UNDONE;
        p = put_s(step_text, "audio4: H undone, CLK_CON1 ");
        p = put_hex(p, hw_aud.h_clk1_back, 8);
        *p = 0;
        hw_step(step_text);
    }
    hw_aud.h_keys++;
    c1_key_marks();
    snap(HW_K_H, 1);
    report(hw_aud.h_state == HW_STEP_TAKEN ? "H taken" : "H undone");
}

/* FX: H's two measurements again, in CLK_CON2's state now. */
void hw_audio_h_again(void)
{
    snap(HW_K_H, 0);
    if (hw_aud.h_state != HW_STEP_TAKEN) {
        refuse(HW_K_H, "audio4: FX refused: H not taken (ENV)");
        return;
    }
    h_both();
    c1_key_marks();
    snap(HW_K_H, 1);
    report("H measured");
}

static s32 al1_buffer[2][2u * AUDIO_FRAMES] __attribute__((aligned(8)));

/* ALNK1 watched for HW_I_POLL_MS: CON0 bit 15's changes, CON2 bit 7 seen
 * (and cleared), and the halves a second (x 10) from the changes. */
static void i_poll(void)
{
    u32 t = sb_beacon.beats, last = JL_ALNK1->CON0 & AL_HALF, flips = 0, pend = 0, span;

    while ((span = sb_beacon.beats - t) < HW_I_POLL_MS) {
        u32 now = JL_ALNK1->CON0 & AL_HALF;

        if (now != last) {
            flips++;
            last = now;
        }
        if (JL_ALNK1->CON2 & AL_PEND) {
            pend++;
            JL_ALNK1->CON2 = AL_CLEAR;
        }
        c1_poll();
    }
    hw_aud.i_flips = flips;
    hw_aud.i_pend = pend;
    hw_aud.i_span = span;
    hw_aud.i_hps10 = span ? div64((u64)flips * 10000u, span) : 0;
}

static void i_read(u32 *w)
{
    w[0] = JL_ALNK1->CON0;
    w[1] = JL_ALNK1->CON1;
    w[2] = JL_ALNK1->CON2;
    w[3] = JL_ALNK1->CON3;
}

/* LFO: step I; a second press undoes it. */
void hw_audio_i(void)
{
    char *p;

    snap(HW_K_I, 0);
    if (hw_aud.i_state != HW_STEP_TAKEN) {
        u32 v;

        i_read(hw_aud.i_con_before);
        hw_aud.i_clk_before = JL_CLOCK->CLK_CON2;
        p = put_s(step_text, "audio4: I: CLK_CON2 ");
        p = put_hex(p, hw_aud.i_clk_before, 8);
        p = put_s(p, " |bit 11");
        *p = 0;
        hw_step(step_text);
        JL_ALNK1->ADR3 = (u32)al1_buffer;
        JL_ALNK1->LEN = 2u * AUDIO_FRAMES;
        JL_ALNK1->CON2 = AL_CLEAR;
        JL_ALNK1->CON0 = hw_aud.i_con_before[0] | AL_RUN;
        v = JL_CLOCK->CLK_CON2;
        JL_CLOCK->CLK_CON2 = v | CLK2_AL1_EN;
        hw_aud.i_clk_set = JL_CLOCK->CLK_CON2;
        i_read(hw_aud.i_con_after);
        hw_aud.i_bit10 = 0;
        hw_aud.i_state = HW_STEP_TAKEN;
        clk_push(HW_K_I);
        hw_step("audio4: I: polling ALNK1");
        i_poll();
    } else {
        if (!clk_may_undo(HW_K_I))
            return;
        p = put_s(step_text, "audio4: I undo: CLK_CON2 to ");
        p = put_hex(p, hw_aud.i_clk_before, 8);
        *p = 0;
        hw_step(step_text);
        JL_ALNK1->CON0 = hw_aud.i_con_before[0];
        hw_aud.i_con_back = JL_ALNK1->CON0;
        JL_CLOCK->CLK_CON2 = hw_aud.i_clk_before;
        hw_aud.i_clk_back = JL_CLOCK->CLK_CON2;
        hw_aud.i_state = HW_STEP_UNDONE;
        clk_pop();
    }
    p = put_s(step_text, "audio4: I: b15 ");
    p = put_dec(p, hw_aud.i_flips);
    p = put_s(p, " C2 ");
    p = put_hex(p, JL_CLOCK->CLK_CON2, 8);
    *p = 0;
    hw_step(step_text);
    hw_aud.i_keys++;
    c1_key_marks();
    snap(HW_K_I, 1);
    report(hw_aud.i_state == HW_STEP_TAKEN ? "I taken" : "I undone");
}

/* SEL: with I taken, CLK_CON2 bit 10 set too (that bit alone), and ALNK1
 * polled again; I's undo puts CLK_CON2 back as read before I. */
void hw_audio_i10(void)
{
    u32 v;
    char *p;

    snap(HW_K_I, 0);
    if (hw_aud.i_state != HW_STEP_TAKEN || hw_aud.i_bit10) {
        refuse(HW_K_I, hw_aud.i_bit10 ? "audio4: SEL refused: bit 10 set" : "audio4: SEL refused: I not taken");
        return;
    }
    v = JL_CLOCK->CLK_CON2;
    p = put_s(step_text, "audio4: I: CLK_CON2 ");
    p = put_hex(p, v, 8);
    p = put_s(p, " |bit 10");
    *p = 0;
    hw_step(step_text);
    JL_CLOCK->CLK_CON2 = v | CLK2_AL1_SEL;
    hw_aud.i_clk_set10 = JL_CLOCK->CLK_CON2;
    hw_aud.i_bit10 = 1;
    hw_step("audio4: I: polling ALNK1");
    i_poll();
    p = put_s(step_text, "audio4: I+10: b15 ");
    p = put_dec(p, hw_aud.i_flips);
    *p = 0;
    hw_step(step_text);
    c1_key_marks();
    snap(HW_K_I, 1);
    report("I bit 10");
}

/* --- audio5's steps K and J (HW-151, HW-153, HW-154; the owner's rulings) - */

#define CLK1_DAC      (3u << 2)     /* CLK_CON1 bits 2-3: the DAC's clock choice (HW-53) */
#define GP_CSS_480    (6u << 1)     /* counted: the counter's own 480 MHz input */

/* One of K's measurements, by H's method with K's wait: JL_GPCNT->CON
 * written with the counted clock css, NUM read twice a gate apart (each
 * after the pending flag or HW_K_WAIT_MS), into k_m[i]. CLK_CON1 is set by
 * the caller. */
static void k_count(u32 i, u32 css)
{
    u32 g = HW_H_GATE_N << 8 | GP_GSS_XOSC | css, j, t, *m = hw_aud.k_m[i];

    m[0] = JL_CLOCK->CLK_CON1;
    JL_GPCNT->CON = g | GP_CLR;
    JL_GPCNT->CON = g | GP_CLR | GP_EN;
    m[1] = JL_GPCNT->CON;
    m[5] = JL_CLOCK->CLK_CON2;
    m[4] = 0;
    for (j = 0; j < 2; j++) {
        t = sb_beacon.beats;
        while (!(JL_GPCNT->CON & GP_PND) && sb_beacon.beats - t < HW_K_WAIT_MS)
            c1_poll();
        if (!(JL_GPCNT->CON & GP_PND))
            m[4]++;
        m[2 + j] = JL_GPCNT->NUM;
        JL_GPCNT->CON = g | GP_CLR | GP_EN;
    }
}

/* CLK_CON1 with the bits in mask set to v (read-modify-write of those bits alone). */
static void clk1_bits(u32 mask, u32 v)
{
    JL_CLOCK->CLK_CON1 = (JL_CLOCK->CLK_CON1 & ~mask) | v;
}

/* GLO: step K, every measurement from one press; a second press undoes. */
void hw_audio_k(void)
{
    static const u8 inputs[5] = { CLK1_HSB, 1u, CLK1_AUDIO, 6u, 7u };
    char *p;
    u32 i, dac;

    snap(HW_K_K, 0);
    if (hw_aud.k_state != HW_STEP_TAKEN) {
        if (hw_aud.h_state == HW_STEP_TAKEN) {
            refuse(HW_K_K, "audio5: K refused: undo H first (ENV)");
            return;
        }
        hw_aud.k_clk1_before = JL_CLOCK->CLK_CON1;
        hw_aud.k_gp_before = JL_GPCNT->CON;
        dac = hw_aud.k_clk1_before & CLK1_DAC;
        p = put_s(step_text, "audio5: K: CLK_CON1 ");
        p = put_hex(p, hw_aud.k_clk1_before, 8);
        *p = 0;
        hw_step(step_text);
        report("K starting");
        /* 1: the clock system's inputs 3, 1, 5, 6 and 7. */
        for (i = 0; i < 5; i++) {
            p = put_s(step_text, "audio5: K: input ");
            p = put_dec(p, inputs[i]);
            *p = 0;
            hw_step(step_text);
            clk1_bits(CLK1_SEL, (u32)inputs[i] << 4);
            k_count(i, GP_CSS_INPUT);
        }
        /* 2: the counter's own 480 MHz input. */
        hw_step("audio5: K: the counter's 480 MHz");
        k_count(5, GP_CSS_480);
        /* 3: input 5 with the DAC's clock choice 1, 2, 3, then as read. */
        clk1_bits(CLK1_SEL, CLK1_AUDIO << 4);
        for (i = 0; i < 4; i++) {
            u32 d = i < 3 ? (i + 1u) << 2 : dac;

            p = put_s(step_text, "audio5: K: input 5, DAC choice ");
            p = put_dec(p, d >> 2);
            *p = 0;
            hw_step(step_text);
            clk1_bits(CLK1_DAC, d);
            k_count(6 + i, GP_CSS_INPUT);
        }
        hw_aud.k_state = HW_STEP_TAKEN;
        p = put_s(step_text, "audio5: K: input 5 ");
        p = put_dec(p, hw_aud.k_m[2][3]);
        p = put_s(p, " usb ");
        p = put_dec(p, hw_aud.k_m[4][3]);
        *p = 0;
        hw_step(step_text);
    } else {
        p = put_s(step_text, "audio5: K undo: CLK_CON1 to ");
        p = put_hex(p, hw_aud.k_clk1_before, 8);
        *p = 0;
        hw_step(step_text);
        JL_CLOCK->CLK_CON1 = hw_aud.k_clk1_before;
        hw_aud.k_clk1_back = JL_CLOCK->CLK_CON1;
        JL_GPCNT->CON = hw_aud.k_gp_before;
        hw_aud.k_gp_back = JL_GPCNT->CON;
        hw_aud.k_state = HW_STEP_UNDONE;
    }
    hw_aud.k_keys++;
    c1_key_marks();
    snap(HW_K_K, 1);
    report(hw_aud.k_state == HW_STEP_TAKEN ? "K measured" : "K undone");
}

/* J's registers: ALNK0's CON1 (16 bits) and CON3 (8 bits). */
static u32 j_get(u32 reg)
{
    return reg == 1u ? JL_ALNK0->CON1 : JL_ALNK0->CON3;
}

static void j_set(u32 reg, u32 v)
{
    if (reg == 1u)
        JL_ALNK0->CON1 = v;
    else
        JL_ALNK0->CON3 = v;
}

static char *put_try(char *p, u32 reg, u32 bit)
{
    p = put_s(p, reg == 1u ? "CON1 b" : "CON3 b");
    return put_dec(p, bit);
}

/* 1 if key (the sweep's own: OCT+ for J, OCT- for D) was pressed since
 * the last look; other keys' events are read and set their LEDs, and are
 * otherwise ignored while a sweep runs. */
static int key_pressed_in_sweep(u32 key)
{
    struct input_event e;
    int abort = 0;

    while (input_read(&e)) {
        if (e.control == key && e.kind == INPUT_PRESS)
            abort = 1;
        else if (e.control < INPUT_LEDS && (e.kind == INPUT_PRESS || e.kind == INPUT_RELEASE))
            input_led(e.control, e.kind == INPUT_PRESS || hw_audio_key_lit(e.control) ? INPUT_LED_FULL : 0);
    }
    return abort;
}

/* One try: reg's bit set alone (every other bit as read), read back, the
 * link watched for HW_J_WAIT_MS; 1 if it moved (CON0 bit 15 changed or
 * source 11 counted), and the bit left set; else the register put back
 * exactly as read and read back. Logged either way. */
static int j_try(u32 reg, u32 bit, u32 t)
{
    char *p, label[16];
    u32 start, last, irq0, flips = 0, pend = 0, moved;

    hw_aud.j_reg = reg;
    hw_aud.j_bit = bit;
    hw_aud.j_before = j_get(reg);
    hw_aud.j_written = hw_aud.j_before | 1u << bit;
    p = put_s(step_text, "audio5: J: ");
    p = put_try(p, reg, bit);
    p = put_s(p, " ");
    p = put_hex(p, hw_aud.j_written, 4);
    *p = 0;
    hw_step(step_text);
    irq0 = sb_audio.blocks;
    last = JL_ALNK0->CON0 & AL_HALF;
    j_set(reg, hw_aud.j_written);
    hw_aud.j_read = j_get(reg);
    hw_aud.j_rb[t] = hw_aud.j_read;
    if (!(hw_aud.j_read & 1u << bit))
        hw_aud.j_nohold |= 1u << t;
    start = sb_beacon.beats;
    while (sb_beacon.beats - start < HW_J_WAIT_MS) {
        u32 now = JL_ALNK0->CON0 & AL_HALF;

        if (now != last) {
            flips++;
            last = now;
        }
        if (JL_ALNK0->CON2 & AL_PEND)
            pend++;
        c1_poll();
    }
    hw_guide_tick();
    hw_aud.j_flips = flips;
    hw_aud.j_pend = pend;
    hw_aud.j_irq = sb_audio.blocks - irq0;
    hw_aud.j_con0 = JL_ALNK0->CON0;
    hw_aud.j_con2 = JL_ALNK0->CON2;
    hw_aud.j_clk2 = JL_CLOCK->CLK_CON2;
    moved = flips || hw_aud.j_irq;
    if (!moved) {
        j_set(reg, hw_aud.j_before);
        hw_aud.j_back = j_get(reg);
    } else {
        hw_aud.j_back = hw_aud.j_read;
    }
    hw_aud.j_tries = t + 1u;
    p = put_try(label, reg, bit);
    p = put_s(p, moved ? " moved" : "");
    *p = 0;
    report(label);
    return (int)moved;
}

/* OCT+: step J. A press runs the whole sweep, CON1 bits 0-15 then CON3
 * bits 0-7, each alone and put back, in CLK_CON2's state now; it stops
 * by itself at a try that moves the link, leaving that bit set, and a
 * press while it runs aborts it, the try in progress put back. A press
 * with a bit left set puts it back; any other press sweeps again. */
void hw_audio_j(void)
{
    char *p;
    u32 t;

    snap(HW_K_J, 0);
    if (hw_aud.j_state == HW_J_MOVED) {
        p = put_s(step_text, "audio5: J undo: ");
        p = put_try(p, hw_aud.j_reg, hw_aud.j_bit);
        p = put_s(p, " to ");
        p = put_hex(p, hw_aud.j_before, 4);
        *p = 0;
        hw_step(step_text);
        j_set(hw_aud.j_reg, hw_aud.j_before);
        hw_aud.j_back = j_get(hw_aud.j_reg);
        hw_aud.j_state = HW_J_UNDONE;
        fresh_base();
        c1_key_marks();
        snap(HW_K_J, 1);
        report("J undone");
        return;
    }
    /* With an L set-up running, J's and D's watches would see the link
     * move at once (audio8's L2 runs from start-up): refused. */
    if (hw_aud.l_state == HW_L_KEPT) {
        refuse(HW_K_J, "audio8: J refused while an L set-up runs");
        return;
    }
    hw_aud.j_sweeps++;
    hw_aud.j_tries = 0;
    hw_aud.j_nohold = 0;
    for (t = 0; t < HW_J_TRIES; t++)
        hw_aud.j_rb[t] = 0xFFFFFFFFu;
    hw_aud.j_clk2_sweep = JL_CLOCK->CLK_CON2;
    p = put_s(step_text, "audio5: J sweep, CLK_CON2 ");
    p = put_hex(p, hw_aud.j_clk2_sweep, 8);
    *p = 0;
    hw_step(step_text);
    report("J starting");
    (void)key_pressed_in_sweep(INPUT_OCT_UP);        /* the press that started it */
    hw_aud.j_state = HW_J_DONE;
    for (t = 0; t < HW_J_TRIES; t++) {
        u32 reg = t < 16u ? 1u : 3u, bit = t < 16u ? t : t - 16u;

        if (j_try(reg, bit, t)) {
            hw_aud.j_state = HW_J_MOVED;
            fresh_base();
            break;
        }
        if (key_pressed_in_sweep(INPUT_OCT_UP)) {
            hw_aud.j_state = HW_J_ABORTED;
            break;
        }
    }
    p = put_s(step_text, hw_aud.j_state == HW_J_MOVED ? "audio5: J MOVED at " :
                         hw_aud.j_state == HW_J_ABORTED ? "audio5: J aborted after " : "audio5: J done, last ");
    p = put_try(p, hw_aud.j_reg, hw_aud.j_bit);
    *p = 0;
    hw_step(step_text);
    c1_key_marks();
    snap(HW_K_J, 1);
    report(hw_aud.j_state == HW_J_MOVED ? "J moved" : hw_aud.j_state == HW_J_ABORTED ? "J aborted" : "J done");
}

/* --- audio6's step D: JL_IOMAP->CON5, a bit at a time (HW-146, HW-156) --- */

#define IOMAP_WORD(i) REG(0x0005101Cu + 4u * (i))   /* JL_IOMAP CON0 to CON8 (HW-56) */
#define IOMAP_CON5    IOMAP_WORD(5)
#define PA_CHECKED(w, b) ((w)[2] != (b)[2] || (w)[3] != (b)[3] || (w)[4] != (b)[4] || (w)[5] != (b)[5])

static void d_iomap(u32 *w)
{
    u32 i;

    for (i = 0; i < 9; i++)
        w[i] = IOMAP_WORD(i);
}

static void d_snap_end(void)
{
    hw_aud.d_al0[0] = JL_ALNK0->CON0;
    hw_aud.d_al0[1] = JL_ALNK0->CON1;
    hw_aud.d_al0[2] = JL_ALNK0->CON2;
    hw_aud.d_al0[3] = JL_ALNK0->CON3;
    hw_aud.d_irq_now = sb_audio.blocks;
    hw_aud.d_core1 = hw_core1_count;
    hw_aud.d_clk2 = JL_CLOCK->CLK_CON2;
}

/* The matrix check (D's steps 4 and 6, L's too): the idle rows all high,
 * the cells as the baseline base_map taken just before the write, and
 * port A's DIR, DIE, PU and PD as base_pa, read before. 0 if it passed,
 * else bits: 0 the idle rows, 1 the cells, 2 port A. */
static u32 matrix_check_vs(u32 *idle, u32 *map, u32 *pa, const u32 *base_map, const u32 *base_pa)
{
    u32 bad = 0;

    hw_matrix_check(idle, map);
    hw_port_a(pa);
    if (*idle != 0x3Fu)
        bad |= 1u;
    if (map[0] != base_map[0] || map[1] != base_map[1] || map[2] != base_map[2])
        bad |= 2u;
    if (PA_CHECKED(pa, base_pa))
        bad |= 4u;
    return bad;
}

static u32 d_check(u32 *idle, u32 *map, u32 *pa)
{
    return matrix_check_vs(idle, map, pa, hw_aud.d_map_base, hw_aud.d_pa_before);
}

static char *put_bit(char *p, const char *label, u32 bit)
{
    p = put_s(p, label);
    return put_dec(p, bit);
}

/* One try of bit (steps 1 to 7 of the spec side's prompt): 0 to go on, or
 * a stop reason (HW_D_STOP_*). */
static u32 d_try(u32 bit)
{
    char label[16], *p;
    u32 start, last, irq0, moved, i;

    hw_aud.d_bit = bit;
    hw_aud.d_phase = 1;
    /* 1: what is there, logged before the write (the record complete in
     * the flash before step 2, so a hang leaves it last). */
    hw_aud.d_con5_before = IOMAP_CON5;
    d_iomap(hw_aud.d_iomap_before);
    hw_port_a(hw_aud.d_pa_before);
    d_snap_end();
    hw_aud.d_flips = hw_aud.d_pend = hw_aud.d_irq = 0;
    hw_aud.d_check_set = hw_aud.d_check_after = 0;
    hw_aud.d_con5_written = hw_aud.d_con5_read = hw_aud.d_con5_back = hw_aud.d_con5_after = 0;
    p = put_bit(label, "D b", bit);
    p = put_s(p, " before");
    *p = 0;
    report(label);
    /* 2: the scan paused, the matrix's baseline, then the write. */
    hw_aud.d_phase = 2;
    p = put_bit(step_text, "audio6: D: CON5 bit ", bit);
    p = put_s(p, " of ");
    p = put_hex(p, hw_aud.d_con5_before, 8);
    *p = 0;
    hw_step(step_text);
    hw_scan_pause();
    hw_matrix_check(&hw_aud.d_idle_base, hw_aud.d_map_base);
    irq0 = sb_audio.blocks;
    last = JL_ALNK0->CON0 & AL_HALF;
    hw_aud.d_con5_written = hw_aud.d_con5_before | 1u << bit;
    IOMAP_CON5 = hw_aud.d_con5_written;
    hw_aud.d_con5_read = IOMAP_CON5;
    /* 3: the watch. */
    hw_aud.d_phase = 3;
    hw_aud.d_in_start = REG(0x00050004u);
    start = sb_beacon.beats;
    while (sb_beacon.beats - start < HW_J_WAIT_MS) {
        u32 now = JL_ALNK0->CON0 & AL_HALF;

        if (now != last) {
            hw_aud.d_flips++;
            last = now;
        }
        if (JL_ALNK0->CON2 & AL_PEND)
            hw_aud.d_pend++;
        c1_poll();
    }
    hw_aud.d_in_end = REG(0x00050004u);
    hw_aud.d_irq = sb_audio.blocks - irq0;
    /* 4: the matrix check with the bit still set. */
    hw_aud.d_phase = 4;
    hw_aud.d_check_set = d_check(&hw_aud.d_idle_set, hw_aud.d_map_set, hw_aud.d_pa_set);
#if defined(SB_TEST_D_CHECK_FAIL)
    /* The test build: the check with bit 2 set made to fail (row PA0 low). */
    if (bit == 2u) {
        hw_aud.d_idle_set &= ~1u;
        hw_aud.d_check_set |= 1u;
    }
#endif
    moved = hw_aud.d_flips || hw_aud.d_irq;
    /* 5: the undo, the firmware's own, unless the link moved with the
     * matrix right: then the bit stays and the sweep stops. */
    hw_aud.d_phase = 5;
    if (moved && !hw_aud.d_check_set) {
        hw_aud.d_con5_back = hw_aud.d_con5_read;
        hw_scan_resume();
        d_snap_end();
        hw_aud.d_phase = 7;
        p = put_bit(label, "D b", bit);
        p = put_s(p, " kept");
        *p = 0;
        report(label);
        return HW_D_STOP_MOVED;
    }
    IOMAP_CON5 = hw_aud.d_con5_before;
    hw_aud.d_con5_back = IOMAP_CON5;
    /* 6: the check after the undo. */
    hw_aud.d_phase = 6;
    d_iomap(hw_aud.d_iomap_after);
    hw_aud.d_check_after = d_check(&hw_aud.d_idle_after, hw_aud.d_map_after, hw_aud.d_pa_after);
    hw_aud.d_con5_after = IOMAP_CON5;
    if (hw_aud.d_con5_after != hw_aud.d_con5_before)
        hw_aud.d_check_after |= 8u;
    for (i = 0; i < 9; i++)
        if (i != 5u && hw_aud.d_iomap_after[i] != hw_aud.d_iomap_before[i])
            hw_aud.d_check_after |= 16u;
    hw_scan_resume();
    /* 7: the try's record. */
    hw_aud.d_phase = 7;
    d_snap_end();
    p = put_bit(label, "D b", bit);
    p = put_s(p, hw_aud.d_check_after ? " after BAD" : hw_aud.d_check_set ? " check BAD" : moved ? " moved" : "");
    *p = 0;
    report(label);
    if (hw_aud.d_check_after)
        return HW_D_STOP_AFTER;
    if (moved)
        return HW_D_STOP_MOVED_BAD;
    if (hw_aud.d_check_set)
        return HW_D_STOP_CHECK;
    return HW_D_STOP_NONE;
}

/* --- audio7's set-ups L1 and L2 (HW-157, HW-158; the owner's rulings) ---- */

#define L_PINS (3u << 7)            /* CON0 bits 7 and 8: clocks to pins (HW-157), kept clear */
#define L_CON1 0x1000u              /* data 3 an I2S output, 16-bit (HW-157) */
static const u8 l_con3[3] = { 0, 0xC2u, 0x83u };    /* L1: the oscillator, /1, 512 a frame; L2: the PLL's audio clock, /1, 256 */
static const u32 l_fps10[3] = { 0, 468750u, 441176u };
#if defined(SB_HW_AUDIO8)
static u32 l_boot;          /* audio8: start-up's L2, with no key to wait for */
#endif

/* CON0, CON1 and CON3 back as read before the set-up, in that order, each
 * read back. */
static void l_put_back(void)
{
    JL_ALNK0->CON0 = hw_aud.l_before[0];
    hw_aud.l_back[0] = JL_ALNK0->CON0;
    JL_ALNK0->CON1 = hw_aud.l_before[1];
    hw_aud.l_back[1] = JL_ALNK0->CON1;
    JL_ALNK0->CON3 = hw_aud.l_before[3];
    hw_aud.l_back[2] = JL_ALNK0->CON3;
}

static void l_end(void)
{
    hw_aud.l_clk2_end = JL_CLOCK->CLK_CON2;
    hw_aud.l_core1_end = hw_core1_count;
}

static void l_label(char *label, u32 which, const char *what)
{
    char *p = put_bit(label, "L", which);

    p = put_s(p, " ");
    p = put_s(p, what);
    *p = 0;
}

/* KEY1 (L1) or KEY2 (L2): one set-up, with D's safety machinery. A kept
 * set-up is put back first, by either key; its own key does only that. */
void hw_audio_l(u32 which)
{
    char label[16], *p;
    u32 start, last, irq0, t_first = 0, t_last = 0, moved, i;

#if defined(SB_HW_AUDIO8)
    /* audio8: the L keys don't touch the link under R2's pins and routes
     * (a route needs R2). */
    if (hw_aud.r2_state == HW_A8_R2_SET) {
        hw_step("audio8: L refused while R2 is in place (KEY3)");
        hw_aud.refused++;
        report("L refused");
        return;
    }
#endif
    if (hw_aud.l_state == HW_L_KEPT) {
        p = put_bit(step_text, "audio7: L", hw_aud.l_which);
        p = put_s(p, " undo: CON0, CON1, CON3 back");
        *p = 0;
        hw_step(step_text);
        l_put_back();
        hw_aud.l_state = HW_L_UNDONE;
        fresh_base();
        l_end();
        l_label(label, hw_aud.l_which, "undone");
        report(label);
        if (which == hw_aud.l_which) {
            c1_key_marks();
            return;
        }
    }
    if (hw_aud.l_stopped) {
        hw_step("audio7: L refused: stopped after a failed check");
        hw_aud.refused++;
        report("L refused");
        return;
    }
    /* As D does: the matrix check wants no key held, so the set-up's key
     * is waited for until it is released, at most HW_D_RELEASE_MS. */
    p = put_bit(step_text, "audio7: release KEY", which);
    p = put_s(p, " to start");
    *p = 0;
    hw_step(step_text);
    start = sb_beacon.beats;
#if defined(SB_HW_AUDIO8)
    if (!l_boot)
#endif
    while (input_value(INPUT_KEY(which)) > 0 && sb_beacon.beats - start < HW_D_RELEASE_MS)
        hw_guide_tick();
    /* 1: what is there, logged before the writes. */
    hw_aud.l_which = which;
    hw_aud.l_presses++;
    hw_aud.l_stop = HW_D_STOP_NONE;
    hw_aud.l_phase = 1;
    hw_aud.l_before[0] = JL_ALNK0->CON0;
    hw_aud.l_before[1] = JL_ALNK0->CON1;
    hw_aud.l_before[2] = JL_ALNK0->CON2;
    hw_aud.l_before[3] = JL_ALNK0->CON3;
    hw_aud.l_len_read = JL_ALNK0->LEN;
    hw_aud.l_adr_read = JL_ALNK0->ADR3;
    /* LEN is write-only in the SDK's header: the expectations use what
     * reads back if it isn't 0, else the value audio_start wrote. */
    hw_aud.l_len_used = hw_aud.l_len_read ? hw_aud.l_len_read : 2u * AUDIO_FRAMES;
    hw_aud.l_clk1 = JL_CLOCK->CLK_CON1;
    hw_aud.l_clk2 = JL_CLOCK->CLK_CON2;
    hw_port_a(hw_aud.l_pa_before);
    hw_aud.l_irq0 = sb_audio.blocks;
    hw_aud.l_core1_0 = hw_core1_count;
    hw_aud.l_exp_fps10 = l_fps10[which];
    hw_aud.l_exp_hps10_a = hw_aud.l_exp_fps10 / hw_aud.l_len_used;
    hw_aud.l_exp_hps10_b = 2u * hw_aud.l_exp_fps10 / hw_aud.l_len_used;
    hw_aud.l_flips = hw_aud.l_pend = hw_aud.l_irq = hw_aud.l_span = 0;
    hw_aud.l_hps10 = hw_aud.l_fps10_a = hw_aud.l_fps10_b = 0;
    hw_aud.l_check_set = hw_aud.l_check_after = 0;
    for (i = 0; i < 4; i++)
        hw_aud.l_w[i] = hw_aud.l_rb[i] = 0;
    for (i = 0; i < 3; i++)
        hw_aud.l_back[i] = 0;
    l_end();
    l_label(label, which, "before");
    report(label);
    /* 2: the scan paused, the matrix's baseline, then the writes in
     * HW-157's driver's order, each read back. */
    hw_aud.l_phase = 2;
    p = put_bit(step_text, "audio7: L", which);
    p = put_s(p, ": CON3 ");
    p = put_hex(p, l_con3[which], 2);
    p = put_s(p, " CON1 1000, run");
    *p = 0;
    hw_step(step_text);
    hw_scan_pause();
    hw_matrix_check(&hw_aud.l_idle_base, hw_aud.l_map_base);
    hw_aud.l_w[0] = hw_aud.l_before[0] & ~AL_RUN;
    JL_ALNK0->CON0 = hw_aud.l_w[0];
    hw_aud.l_rb[0] = JL_ALNK0->CON0;
    hw_aud.l_w[1] = l_con3[which];
    JL_ALNK0->CON3 = hw_aud.l_w[1];
    hw_aud.l_rb[1] = JL_ALNK0->CON3;
    hw_aud.l_w[2] = L_CON1;
    JL_ALNK0->CON1 = hw_aud.l_w[2];
    hw_aud.l_rb[2] = JL_ALNK0->CON1;
    hw_aud.l_w[3] = (hw_aud.l_before[0] & ~L_PINS) | AL_RUN;
    irq0 = sb_audio.blocks;
    JL_ALNK0->CON0 = hw_aud.l_w[3];
    hw_aud.l_rb[3] = JL_ALNK0->CON0;
    /* 3: the watch, timed against sb_now() as audio1 times the halves. */
    hw_aud.l_phase = 3;
    last = JL_ALNK0->CON0 & AL_HALF;
    start = sb_beacon.beats;
    while (sb_beacon.beats - start < HW_L_WAIT_MS) {
        u32 now = JL_ALNK0->CON0 & AL_HALF;

        if (now != last) {
            t_last = sb_now();
            if (!hw_aud.l_flips)
                t_first = t_last;
            hw_aud.l_flips++;
            last = now;
        }
        if (JL_ALNK0->CON2 & AL_PEND)
            hw_aud.l_pend++;
        c1_poll();
    }
    hw_aud.l_irq = sb_audio.blocks - irq0;
    if (hw_aud.l_flips >= 2u && t_last != t_first) {
        hw_aud.l_span = t_last - t_first;
        hw_aud.l_hps10 = div64((u64)(hw_aud.l_flips - 1u) * 240000000ull, hw_aud.l_span);
        hw_aud.l_fps10_a = hw_aud.l_hps10 * hw_aud.l_len_used;
        hw_aud.l_fps10_b = hw_aud.l_hps10 * hw_aud.l_len_used / 2u;
    }
    /* 4: the matrix check with the set-up in place. */
    hw_aud.l_phase = 4;
    hw_aud.l_check_set = matrix_check_vs(&hw_aud.l_idle_set, hw_aud.l_map_set, hw_aud.l_pa_set, hw_aud.l_map_base,
                                         hw_aud.l_pa_before);
#if defined(SB_TEST_L_CHECK_FAIL)
    /* The test build: L1's check made to fail (row PA0 low). */
    if (which == 1u) {
        hw_aud.l_idle_set &= ~1u;
        hw_aud.l_check_set |= 1u;
    }
#endif
    moved = hw_aud.l_flips || hw_aud.l_irq;
    /* 5: kept if the link moved with the matrix right; else put back. */
    hw_aud.l_phase = 5;
    if (moved && !hw_aud.l_check_set) {
        hw_scan_resume();
        hw_aud.l_state = HW_L_KEPT;
        hw_aud.l_stop = HW_D_STOP_MOVED;
        fresh_base();
        hw_aud.l_phase = 7;
        l_end();
        l_label(label, which, "kept");
        report(label);
        p = put_bit(step_text, "audio7: L", which);
        p = put_s(p, " MOVED, kept: h/s ");
        p = put_dec(p, hw_aud.l_hps10 / 10u);
        *p = 0;
        hw_step(step_text);
        c1_key_marks();
        return;
    }
    l_put_back();
    /* 6: the check after the undo, and the registers against step 1's. */
    hw_aud.l_phase = 6;
    hw_aud.l_check_after = matrix_check_vs(&hw_aud.l_idle_after, hw_aud.l_map_after, hw_aud.l_pa_after,
                                           hw_aud.l_map_base, hw_aud.l_pa_before);
    if ((hw_aud.l_back[0] ^ hw_aud.l_before[0]) & ~AL_HALF || hw_aud.l_back[1] != hw_aud.l_before[1]
            || hw_aud.l_back[2] != hw_aud.l_before[3])
        hw_aud.l_check_after |= 8u;
    hw_scan_resume();
    /* 7: the set-up's record. */
    hw_aud.l_phase = 7;
    hw_aud.l_stop = hw_aud.l_check_after ? HW_D_STOP_AFTER : moved ? HW_D_STOP_MOVED_BAD :
                    hw_aud.l_check_set ? HW_D_STOP_CHECK : HW_D_STOP_NONE;
    hw_aud.l_state = hw_aud.l_stop ? HW_L_STOPPED : HW_L_DONE;
    if (hw_aud.l_stop)
        hw_aud.l_stopped = 1;
    fresh_base();
    l_end();
    l_label(label, which, hw_aud.l_check_after ? "after BAD" : hw_aud.l_check_set ? "check BAD" :
                          moved ? "moved BAD" : "put back");
    report(label);
    p = put_bit(step_text, "audio7: L", which);
    p = put_s(p, hw_aud.l_stop ? " stopped, put back" : " didn't run, put back");
    *p = 0;
    hw_step(step_text);
    c1_key_marks();
}

static const char *d_stop_word(u32 st)
{
    return st == HW_D_STOP_CHECK ? "matrix broke, undone" : st == HW_D_STOP_MOVED ? "LINK MOVED, bit kept" :
           st == HW_D_STOP_MOVED_BAD ? "moved, matrix broke, undone" : st == HW_D_STOP_AFTER ? "check after undo BAD" :
           st == HW_D_STOP_KEY ? "stopped by OCT-" : "none";
}

/* OCT-: step D. A press runs the sweep of CON5's bits 0 to 31, each tried
 * alone, checked and undone by the firmware itself, stopping at the first
 * try that moves the link or fails a check; a press while it runs stops
 * it after the try in progress; a press with a bit kept puts CON5 back as
 * read. J's register goes back as read before a sweep. */
void hw_audio_d(void)
{
    char *p;
    u32 bit, start, stop = HW_D_STOP_NONE;

    if (hw_aud.d_state == HW_D_KEPT) {
        p = put_s(step_text, "audio6: D undo: CON5 to ");
        p = put_hex(p, hw_aud.d_con5_before, 8);
        *p = 0;
        hw_step(step_text);
        IOMAP_CON5 = hw_aud.d_con5_before;
        hw_aud.d_con5_back = IOMAP_CON5;
        hw_aud.d_state = HW_D_UNDONE;
        fresh_base();
        c1_key_marks();
        d_snap_end();
        report("D undone");
        return;
    }
    if (hw_aud.l_state == HW_L_KEPT) {
        hw_step("audio8: D refused while an L set-up runs");
        hw_aud.refused++;
        report("D refused");
        return;
    }
    hw_aud.d_j_putback = 0;
    if (hw_aud.j_state == HW_J_MOVED) {
        j_set(hw_aud.j_reg, hw_aud.j_before);
        hw_aud.j_back = j_get(hw_aud.j_reg);
        hw_aud.j_state = HW_J_UNDONE;
        hw_aud.d_j_putback = hw_aud.j_reg << 16 | hw_aud.j_before;
        hw_step("audio6: J's bit put back before D");
        report("J back for D");
    }
    hw_aud.d_sweeps++;
    hw_aud.d_tries = 0;
    hw_aud.d_stop = HW_D_STOP_NONE;
    p = put_s(step_text, "audio6: D sweep, CLK_CON2 ");
    p = put_hex(p, JL_CLOCK->CLK_CON2, 8);
    *p = 0;
    hw_step(step_text);
    d_snap_end();
    report("D starting");
    /* The matrix check wants no key held: OCT-, which started the sweep,
     * is waited for until it is released (its cell would otherwise differ
     * between the baseline and the check), at most HW_D_RELEASE_MS. */
    hw_step("audio6: D: release OCT- to start");
    start = sb_beacon.beats;
    while (input_value(INPUT_OCT_DOWN) > 0 && sb_beacon.beats - start < HW_D_RELEASE_MS)
        hw_guide_tick();
    (void)key_pressed_in_sweep(INPUT_OCT_DOWN);
    for (bit = 0; bit < 32u; bit++) {
        hw_aud.d_tries = bit + 1u;
        stop = d_try(bit);
        if (stop)
            break;
        hw_guide_tick();
        if (key_pressed_in_sweep(INPUT_OCT_DOWN)) {
            stop = HW_D_STOP_KEY;
            break;
        }
    }
    hw_aud.d_stop = stop;
    hw_aud.d_state = stop == HW_D_STOP_MOVED ? HW_D_KEPT : stop ? HW_D_STOPPED : HW_D_DONE;
    if (stop == HW_D_STOP_MOVED)
        fresh_base();
    p = put_s(step_text, "audio6: D ");
    p = put_s(p, stop ? d_stop_word(stop) : "done, none stopped it");
    if (stop) {
        p = put_bit(p, " b", hw_aud.d_bit);
    }
    *p = 0;
    hw_step(step_text);
    c1_key_marks();
    d_snap_end();
    report(stop == HW_D_STOP_MOVED ? "D kept" : stop ? "D stopped" : "D done");
}

/* --- audio8 (the spec side's clean-br17-audio8; the owner's rulings) ---- */

#if defined(SB_HW_AUDIO8)
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

static const u8 a8_pin[HW_A8_PINS] = { 0, 1, 2, 6, 4, 5, 6, 7, 8, 9, 10 };
static u32 s1_pc_moved, s1_stop;   /* step 1's (b) moved port C (the sweep's condition) */

static void a8_port(u32 port, u32 *w)
{
    u32 i;

    for (i = 0; i < 8; i++)
        w[i] = PORT_W(port, i);
}

/* Port C's and port A's IN read in a tight loop for ms milliseconds: each
 * counted pin's changes into c (PC0, PC1, PC2, PC6, PA4 to PA10), the
 * loop's passes into *n, the sb_now() units it took into *span. The time
 * is checked every 64 passes. Interrupts stay on: a pass they delay
 * misses changes, so a fast pin may be undercounted, never counted when
 * it doesn't move. */
static void a8_sample(u32 *c, u32 *n, u32 *span, u32 ms)
{
    u32 pc0 = PORT_W(P_C, R_IN), pa0 = PORT_W(P_A, R_IN), t0 = sb_now(), it = 0, t = 0, i;

    for (i = 0; i < HW_A8_PINS; i++)
        c[i] = 0;
    for (;;) {
        u32 pc = PORT_W(P_C, R_IN), pa = PORT_W(P_A, R_IN);
        u32 dc = (pc ^ pc0) & A8_PC_PINS, da = (pa ^ pa0) & A8_PA_PINS;

        if (dc | da) {
            for (i = 0; i < 4; i++)
                c[i] += dc >> a8_pin[i] & 1u;
            for (i = 4; i < HW_A8_PINS; i++)
                c[i] += da >> a8_pin[i] & 1u;
            pc0 = pc;
            pa0 = pa;
        }
        it++;
        if (!(it & 63u)) {
            t = sb_now() - t0;
            if (t >= ms * 24000u)
                break;
        }
    }
    *n = it;
    *span = t;
}

static u32 a8_pc_moved(const u32 *c)
{
    return c[0] | c[1] | c[2] | c[3];
}

static u32 a8_pa_moved(const u32 *c)
{
    u32 i, m = 0;

    for (i = 4; i < HW_A8_PINS; i++)
        m |= c[i];
    return m;
}

static void a8_refuse(const char *why, const char *label)
{
    hw_step(why);
    hw_aud.refused++;
    report(label);
}

/* 1 (and the press refused) if audio8's keys may not run: start-up's L2
 * isn't running, or a check after an undo failed. */
static int a8_off(const char *label)
{
    if (hw_aud.a8_off != HW_A8_OFF_CHECK && hw_aud.l_state == HW_L_KEPT)
        return 0;
    a8_refuse(hw_aud.a8_off == HW_A8_OFF_CHECK ? "audio8: refused: a check after an undo failed" :
              "audio8: refused: L2 isn't running", label);
    return 1;
}

/* 1 (and refused) if the link is stopped by REC's bit 9 (HW-160). */
static int a8_no_link(const char *label)
{
    if (hw_aud.step_state != HW_STEP_TAKEN)
        return 0;
    a8_refuse("audio8: refused: bit 9 set, the link stopped (REC first)", label);
    return 1;
}

/* As L does: the key that started a step is waited for until released. */
static void a8_release(u32 key, const char *text)
{
    u32 start = sb_beacon.beats;

    hw_step(text);
    while (input_value(key) > 0 && sb_beacon.beats - start < HW_D_RELEASE_MS)
        hw_guide_tick();
}

/* CON0 bits 7 and 8 back clear; for a sweep's try CON5 back as read after
 * them. Each read back. */
static void a8_try_undo(u32 kind)
{
    u32 v = JL_ALNK0->CON0;

    JL_ALNK0->CON0 = v & ~L_PINS;
    hw_aud.rt_con0[3] = JL_ALNK0->CON0;
    if (kind == 2u) {
        IOMAP_CON5 = hw_aud.rt_con5[0];
        hw_aud.rt_con5[3] = IOMAP_CON5;
    }
}

static void a8_label(char *label, u32 kind, const char *what)
{
    char *p = kind == 1u ? put_s(label, "S1b") : kind == 3u ? put_s(label, "Route") : put_bit(label, "SW b", hw_aud.rt_bit);

    p = put_s(p, what);
    *p = 0;
}

/* One routed try with D's safety machinery: kind 1, step 1's (b), CON0
 * bits 7 and 8 set; kind 2, a sweep's try, CON5's bit set, then CON0 bits
 * 7 and 8. Logged before the write; the scan held (0xFFFF latched, the
 * LED lines low), the matrix's baseline and the idle rows checked; the
 * writes, each read back; the watch (the samples); then, if port A moved,
 * the undo at once, before the matrix check (which drives columns against
 * rows the link may be driving); else the check, kept if port C moved
 * with the check passed, else undone; the check after an undo; a record.
 * Returns HW_A8_STOP_*. */
static u32 a8_try(u32 kind, u32 bit)
{
    char label[16];
    u32 irq0, last, start, i, moved_a, moved_c;

    hw_aud.rt_kind = kind;
    hw_aud.rt_bit = bit;
    hw_aud.rt_phase = 1;
    hw_aud.rt_stop = HW_A8_STOP_NONE;
    for (i = 0; i < 4; i++)
        hw_aud.rt_con0[i] = hw_aud.rt_con5[i] = 0;
    for (i = 0; i < HW_A8_PINS; i++)
        hw_aud.rt_c1[i] = hw_aud.rt_c2[i] = 0;
    for (i = 0; i < 8; i++)
        hw_aud.rt_pa_set[i] = hw_aud.rt_pa_after[i] = hw_aud.rt_pc_set[i] = 0;
    hw_aud.rt_n1 = hw_aud.rt_span1 = hw_aud.rt_n2 = hw_aud.rt_span2 = 0;
    hw_aud.rt_flips = hw_aud.rt_irq = hw_aud.rt_check_set = hw_aud.rt_check_after = 0;
    hw_aud.rt_con0[0] = JL_ALNK0->CON0;
    hw_aud.rt_con5[0] = IOMAP_CON5;
    d_iomap(hw_aud.rt_iomap_before);
    hw_port_a(hw_aud.rt_pa_before);
    a8_label(label, kind, " before");
    report(label);
    /* 2: held, the baseline, the idle rows, then the writes. */
    hw_aud.rt_phase = 2;
    hw_step(kind == 1u ? "audio8: step 1 (b): TOUCH NO KEY" : kind == 3u ? "audio9: route: TOUCH NO KEY" :
            "audio8: sweep: TOUCH NO KEY");
    hw_scan_hold();
    hw_matrix_check(&hw_aud.rt_idle_base, hw_aud.rt_map_base);
    if (hw_aud.rt_idle_base != 0x3Fu) {
        hw_scan_resume();
        hw_aud.rt_stop = HW_A8_STOP_ROWS;
        hw_aud.rt_phase = 7;
        a8_label(label, kind, " rows BAD");
        report(label);
        return HW_A8_STOP_ROWS;
    }
    irq0 = sb_audio.blocks;
    if (kind == 2u) {
        hw_aud.rt_con5[1] = hw_aud.rt_con5[0] | 1u << bit;
        IOMAP_CON5 = hw_aud.rt_con5[1];
        hw_aud.rt_con5[2] = IOMAP_CON5;
    }
    hw_aud.rt_con0[1] = JL_ALNK0->CON0 | L_PINS;
    JL_ALNK0->CON0 = hw_aud.rt_con0[1];
    hw_aud.rt_con0[2] = JL_ALNK0->CON0;
    /* 3: the watch: a sample at once; for (b), the rest of HW_A8_WATCH_MS
     * and a second sample, unless port A moved in the first. */
    hw_aud.rt_phase = 3;
    /* audio9's route (kind 3): one sample over the whole 100 ms watch. */
    a8_sample(hw_aud.rt_c1, &hw_aud.rt_n1, &hw_aud.rt_span1, kind == 3u ? HW_A8_WATCH_MS : HW_A8_SAMPLE_MS);
    if (kind == 1u && !a8_pa_moved(hw_aud.rt_c1)) {
        last = JL_ALNK0->CON0 & AL_HALF;
        start = sb_beacon.beats;
        while (sb_beacon.beats - start < HW_A8_WATCH_MS - 2u * HW_A8_SAMPLE_MS) {
            u32 now = JL_ALNK0->CON0 & AL_HALF;

            if (now != last) {
                hw_aud.rt_flips++;
                last = now;
            }
            c1_poll();
        }
        a8_sample(hw_aud.rt_c2, &hw_aud.rt_n2, &hw_aud.rt_span2, HW_A8_SAMPLE_MS);
    }
    hw_aud.rt_irq = sb_audio.blocks - irq0;
    a8_port(P_C, hw_aud.rt_pc_set);
#if defined(SB_TEST_A8_PA_MOVE)
    /* The test build: the sweep's bit 3 made to move port A (PA5). */
    if (kind == 2u && bit == 3u)
        hw_aud.rt_c1[5] = 7;
#endif
#if defined(SB_TEST_A8_PC_MOVE)
    /* The test build: step 1's (b) made to move port C (PC2). */
    if (kind == 1u)
        hw_aud.rt_c1[2] = 880;
#endif
#if defined(SB_TEST_A9_PA_MOVE)
    /* The test build: audio9's route made to move port A (PA5). */
    if (kind == 3u)
        hw_aud.rt_c1[5] = 7;
#endif
    moved_a = a8_pa_moved(hw_aud.rt_c1) | a8_pa_moved(hw_aud.rt_c2);
    moved_c = a8_pc_moved(hw_aud.rt_c1) | a8_pc_moved(hw_aud.rt_c2);
    /* 4 and 5: port A moved: undone at once; else the check, then kept or
     * undone. */
    hw_aud.rt_phase = 4;
    if (moved_a) {
        a8_try_undo(kind);
        hw_aud.rt_check_set = 32u;
        hw_aud.rt_stop = HW_A8_STOP_PA;
    } else {
        hw_aud.rt_check_set = matrix_check_vs(&hw_aud.rt_idle_set, hw_aud.rt_map_set, hw_aud.rt_pa_set,
                                              hw_aud.rt_map_base, hw_aud.rt_pa_before);
#if defined(SB_TEST_A8_CHECK_FAIL)
        /* The test build: the check at the sweep's bit 1 made to fail. */
        if (kind == 2u && bit == 1u) {
            hw_aud.rt_idle_set &= ~1u;
            hw_aud.rt_check_set |= 1u;
        }
#endif
#if defined(SB_TEST_A9_CHECK_FAIL)
        /* The test build: audio9's route made to fail its check. */
        if (kind == 3u) {
            hw_aud.rt_idle_set &= ~1u;
            hw_aud.rt_check_set |= 1u;
        }
#endif
        hw_aud.rt_phase = 5;
        /* Kept: port C moved (audio8), or for audio9's route the check
         * alone, since port C's IN can't show the link's pins. */
        if (!hw_aud.rt_check_set && (moved_c || kind == 3u)) {
            hw_scan_resume();
            hw_aud.rt_stop = HW_A8_STOP_PC;
            hw_aud.rt_phase = 7;
            a8_label(label, kind, " kept");
            report(label);
            return HW_A8_STOP_PC;
        }
        a8_try_undo(kind);
        if (hw_aud.rt_check_set)
            hw_aud.rt_stop = HW_A8_STOP_CHECK;
    }
    /* 6: the check after the undo, and the registers against step 1's. */
    hw_aud.rt_phase = 6;
    d_iomap(hw_aud.rt_iomap_after);
    hw_aud.rt_check_after = matrix_check_vs(&hw_aud.rt_idle_after, hw_aud.rt_map_after, hw_aud.rt_pa_after,
                                            hw_aud.rt_map_base, hw_aud.rt_pa_before);
    if ((hw_aud.rt_con0[3] ^ hw_aud.rt_con0[0]) & ~AL_HALF || hw_aud.rt_iomap_after[5] != hw_aud.rt_con5[0])
        hw_aud.rt_check_after |= 8u;
    for (i = 0; i < 9; i++)
        if (i != 5u && hw_aud.rt_iomap_after[i] != hw_aud.rt_iomap_before[i])
            hw_aud.rt_check_after |= 16u;
    hw_scan_resume();
    hw_aud.rt_phase = 7;
    if (hw_aud.rt_check_after) {
        hw_aud.rt_stop = HW_A8_STOP_AFTER;
        hw_aud.a8_off = HW_A8_OFF_CHECK;
    }
    a8_label(label, kind, hw_aud.rt_check_after ? " after BAD" : moved_a ? " PA moved" :
                          hw_aud.rt_check_set ? " check BAD" : "");
    report(label);
    return hw_aud.rt_stop;
}

/* The routes kept (step 1's bits, a sweep's bit) put back. */
static void a8_unroute(void)
{
    char label[16];

#if defined(SB_HW_AUDIO9)
    if (hw_aud.a9_route == HW_A9_ROUTE_UP) {
        hw_step("audio9: route down: CON0 bits 7 8 clear");
        a8_try_undo(3);
        hw_aud.a9_route = HW_A9_ROUTE_DOWN;
        hw_aud.a9_downs++;
        report("Route down");
    }
#endif
    if (hw_aud.sw_state == HW_A8_SW_KEPT) {
        hw_step("audio8: sweep undo: CON0 bits 7 8, CON5 back");
        a8_try_undo(2);
        hw_aud.sw_state = HW_A8_SW_UNDONE;
        a8_label(label, 2, " undone");
        report(label);
    }
    if (hw_aud.s1_state == HW_A8_S1_KEPT) {
        hw_step("audio8: step 1 undo: CON0 bits 7 8 back");
        a8_try_undo(1);
        hw_aud.s1_state = HW_A8_S1_UNDONE;
        report("S1 undone");
    }
}

/* R2's undo: the routes first, then the four pins' bits in DIE, DIR and
 * OUT back as read, each by read-modify-write of those bits alone (the
 * panel's driver moves PC7 and PC8 in OUT meanwhile); then every port C
 * register checked against the read before. */
static void a8_r2_undo(void)
{
    const u32 *b = hw_aud.r2_pc_before;
    u32 i;

    a8_unroute();
    hw_step("audio8: R2 undo: PC0 PC1 PC2 PC6 as read");
    lcd_wait();
    PORT_W(P_C, R_DIE) = (PORT_W(P_C, R_DIE) & ~A8_PC_PINS) | (b[R_DIE] & A8_PC_PINS);
    PORT_W(P_C, R_DIR) = (PORT_W(P_C, R_DIR) & ~A8_PC_PINS) | (b[R_DIR] & A8_PC_PINS);
    PORT_W(P_C, R_OUT) = (PORT_W(P_C, R_OUT) & ~A8_PC_PINS) | (b[R_OUT] & A8_PC_PINS);
    a8_port(P_C, hw_aud.r2_pc_after);
    for (i = 0; i < 8; i++) {
        u32 d = hw_aud.r2_pc_after[i] ^ b[i];

        if (i == R_IN)
            continue;
        if (d & ~(i == R_OUT ? A8_PC_LCD : 0u))
            hw_aud.r2_check |= 4u;
    }
    hw_aud.r2_state = HW_A8_R2_UNDONE;
    report(hw_aud.r2_check & 4u ? "R2 undone BAD" : "R2 undone");
    hw_step(hw_aud.r2_check & 4u ? "audio8: R2 undone, port C NOT as read" : "audio8: R2 undone, port C as read");
}

/* KEY3: R2. The control sample (held, nothing routed), port C read, then
 * PC0, PC1, PC2 and PC6 set as the AW30N's driver sets a master's pins
 * (HW-158): OUT high, then DIR 0, then DIE on, each a read-modify-write
 * of those four bits alone; the pulls and drive as read. Again: undone. */
void hw_a8_r2(void)
{
    const u32 *b = hw_aud.r2_pc_before;
    u32 i;

    if (hw_aud.r2_state == HW_A8_R2_SET) {
        a8_r2_undo();
        c1_key_marks();
        return;
    }
    if (a8_off("R2 refused"))
        return;
    hw_aud.r2_presses++;
    hw_aud.r2_check = 0;
    for (i = 0; i < 8; i++)
        hw_aud.r2_pc_set[i] = hw_aud.r2_pc_after[i] = 0;
    hw_step("audio8: R2: control sample, nothing routed");
    hw_scan_hold();
    a8_sample(hw_aud.ctl, &hw_aud.ctl_n, &hw_aud.ctl_span, HW_A8_SAMPLE_MS);
    hw_scan_resume();
    a8_port(P_C, hw_aud.r2_pc_before);
    report("R2 before");
    hw_step("audio8: R2: PC0 PC1 PC2 PC6: OUT 1, DIR 0, DIE 1");
    lcd_wait();
    PORT_W(P_C, R_OUT) |= A8_PC_PINS;
    PORT_W(P_C, R_DIR) &= ~A8_PC_PINS;
    PORT_W(P_C, R_DIE) |= A8_PC_PINS;
    a8_port(P_C, hw_aud.r2_pc_set);
    for (i = 4; i < 8; i++)
        if (hw_aud.r2_pc_set[i] != b[i])
            hw_aud.r2_check |= 1u;
    if ((hw_aud.r2_pc_set[R_OUT] ^ b[R_OUT]) & ~(A8_PC_PINS | A8_PC_LCD)
            || (hw_aud.r2_pc_set[R_DIR] ^ b[R_DIR]) & ~A8_PC_PINS || (hw_aud.r2_pc_set[R_DIE] ^ b[R_DIE]) & ~A8_PC_PINS)
        hw_aud.r2_check |= 2u;
    if ((hw_aud.r2_pc_set[R_OUT] & A8_PC_PINS) != A8_PC_PINS || hw_aud.r2_pc_set[R_DIR] & A8_PC_PINS
            || (hw_aud.r2_pc_set[R_DIE] & A8_PC_PINS) != A8_PC_PINS)
        hw_aud.r2_check |= 8u;
    hw_aud.r2_state = HW_A8_R2_SET;
    report(hw_aud.r2_check ? "R2 set BAD" : "R2 set");
    hw_step(hw_aud.r2_check ? "audio8: R2 set, port C NOT as expected" : "audio8: R2 set: KEY4 next");
    c1_key_marks();
}

/* KEY4: step 1. (a) a sample with R2 in place and CON0 bits 7 and 8
 * clear, the scan held; (b) the routed try with bits 7 and 8. Kept if
 * port C moved and port A didn't; again: undone. */
void hw_a8_step1(void)
{
    u32 stop;

    if (hw_aud.s1_state == HW_A8_S1_KEPT) {
        a8_unroute();
        c1_key_marks();
        return;
    }
    if (a8_off("S1 refused") || a8_no_link("S1 refused"))
        return;
    if (hw_aud.r2_state != HW_A8_R2_SET) {
        a8_refuse("audio8: step 1 refused: R2 first (KEY3)", "S1 refused");
        return;
    }
    if (hw_aud.sw_state == HW_A8_SW_KEPT) {
        a8_refuse("audio8: step 1 refused: a sweep bit kept (KEY5)", "S1 refused");
        return;
    }
    a8_release(INPUT_KEY(4), "audio8: step 1: let go of KEY4");
    hw_aud.s1_runs++;
    hw_step("audio8: step 1 (a): sampling, bits 7 8 clear");
    hw_scan_hold();
    a8_sample(hw_aud.s1a, &hw_aud.s1a_n, &hw_aud.s1a_span, HW_A8_SAMPLE_MS);
    hw_scan_resume();
    report("S1a");
    stop = a8_try(1, 0);
    s1_pc_moved = a8_pc_moved(hw_aud.rt_c1) || a8_pc_moved(hw_aud.rt_c2);
    s1_stop = stop;
    hw_aud.s1_state = stop == HW_A8_STOP_PC ? HW_A8_S1_KEPT : stop == HW_A8_STOP_NONE ? HW_A8_S1_NONE_MOVED :
                      HW_A8_S1_STOPPED;
    hw_step(stop == HW_A8_STOP_PC ? "audio8: PORT C MOVES, kept: LISTEN" :
            stop == HW_A8_STOP_NONE ? "audio8: step 1: port C didn't move" :
            stop == HW_A8_STOP_PA ? "audio8: step 1: PORT A MOVED, undone" :
            stop == HW_A8_STOP_ROWS ? "audio8: step 1: a key held, not run" : "audio8: step 1: CHECK FAILED, undone");
    c1_key_marks();
}

/* 1 if the sweep may run: step 1 ran and port C didn't move (the owner's
 * ruling), nor did a check fail. */
static int a8_sweep_allowed(void)
{
    return hw_aud.s1_state == HW_A8_S1_NONE_MOVED || (hw_aud.s1_state == HW_A8_S1_STOPPED && !s1_pc_moved
                                                      && hw_aud.a8_off != HW_A8_OFF_CHECK && s1_stop == HW_A8_STOP_PA);
}

/* KEY5: step 2, the sweep of CON5's bits 0 to 31, one press. Each try is
 * a routed try (a8_try); it stops at the first try that keeps (port C
 * moved, port A didn't), moves port A, or fails a check. Again with a bit
 * kept: undone. */
void hw_a8_sweep(void)
{
    u32 bit, stop = HW_A8_STOP_NONE;

    if (hw_aud.sw_state == HW_A8_SW_KEPT) {
        a8_unroute();
        c1_key_marks();
        return;
    }
    if (a8_off("SW refused") || a8_no_link("SW refused"))
        return;
    if (hw_aud.r2_state != HW_A8_R2_SET || !a8_sweep_allowed()) {
        a8_refuse(hw_aud.r2_state != HW_A8_R2_SET ? "audio8: sweep refused: R2 first (KEY3)" :
                  hw_aud.s1_state == HW_A8_S1_NONE ? "audio8: sweep refused: step 1 first (KEY4)" :
                  "audio8: sweep refused: step 1 moved port C", "SW refused");
        return;
    }
    a8_release(INPUT_KEY(5), "audio8: sweep: let go of KEY5");
    hw_aud.sw_sweeps++;
    hw_aud.sw_tries = hw_aud.sw_pa_bits = hw_aud.sw_nohold = 0;
    for (bit = 0; bit < 32u; bit++) {
        hw_aud.sw_tries++;
        stop = a8_try(2, bit);
        if (stop != HW_A8_STOP_ROWS && hw_aud.rt_con5[2] != hw_aud.rt_con5[1])
            hw_aud.sw_nohold |= 1u << bit;
        if (stop == HW_A8_STOP_PA)
            hw_aud.sw_pa_bits |= 1u << bit;
        if (stop != HW_A8_STOP_NONE)
            break;
    }
    hw_aud.sw_stop = stop;
    hw_aud.sw_state = stop == HW_A8_STOP_PC ? HW_A8_SW_KEPT : stop ? HW_A8_SW_STOPPED : HW_A8_SW_DONE;
    report(stop == HW_A8_STOP_PC ? "SW kept" : stop ? "SW stopped" : "SW done");
    hw_step(stop == HW_A8_STOP_PC ? "audio8: sweep: PORT C MOVES, kept: LISTEN" :
            stop == HW_A8_STOP_PA ? "audio8: sweep: PORT A MOVED, undone" :
            stop ? "audio8: sweep stopped, undone" : "audio8: sweep: port C never moved");
    c1_key_marks();
}

static u32 se_get(u32 i)
{
    return hw_aud.se_count[i / 2u] >> 16u * (i & 1u) & 0xFFFFu;
}

static void se_bump(u32 i)
{
    u32 v = se_get(i);

    if (v < 0xFFFFu)
        hw_aud.se_count[i / 2u] += 1u << 16u * (i & 1u);
}

/* KEY6: the sense scan, read-only (R5): every port's IN (A to H) read
 * each millisecond for HW_A8_SENSE_MS, each bit's changes counted, and
 * its first HW_A8_EV_PER changes kept with their times. No port is
 * written: the scan held once before (its latch and LED lines), and the
 * panel's countdown, once a second, moves PC7 to PC10 as any drawing does. */
void hw_a8_sense(void)
{
    static char t[48];
    u32 prev[8], i, p, start, last, now, next, left, bits;
    char *q;

    if (a8_off("SE refused"))
        return;
    a8_release(INPUT_KEY(6), "audio8: sense: let go of KEY6");
    hw_aud.se_runs++;
    hw_aud.se_ms = hw_aud.se_ev_n = hw_aud.se_ev_lost = 0;
    for (i = 0; i < 64u; i++)
        hw_aud.se_count[i] = 0;
    for (p = 0; p < 8u; p++) {
        hw_aud.se_dir[p] = PORT_W(p, R_DIR);
        hw_aud.se_die[p] = PORT_W(p, R_DIE);
        hw_aud.se_in0[p] = prev[p] = PORT_W(p, R_IN);
        hw_aud.se_changed[p] = 0;
    }
    report("SE before");
    hw_scan_hold();
    start = last = sb_beacon.beats;
    next = 0;
    while ((now = sb_beacon.beats - start) < HW_A8_SENSE_MS) {
        if (sb_beacon.beats == last) {
            c1_poll();
            continue;
        }
        last = sb_beacon.beats;
        hw_aud.se_ms++;
        for (p = 0; p < 8u; p++) {
            u32 v = PORT_W(p, R_IN), d = (v ^ prev[p]) & 0xFFFFu;

            prev[p] = v;
            if (!d)
                continue;
            hw_aud.se_changed[p] |= d;
            for (i = 0; i < 16u; i++) {
                if (!(d >> i & 1u))
                    continue;
                se_bump(16u * p + i);
                if (se_get(16u * p + i) > HW_A8_EV_PER)
                    continue;
                if (hw_aud.se_ev_n < HW_A8_EVENTS)
                    hw_aud.se_ev[hw_aud.se_ev_n++] = now << 16 | (v >> i & 1u) << 8 | p << 4 | i;
                else
                    hw_aud.se_ev_lost++;
            }
        }
        if (now >= next) {
            next += 1000u;
            left = (HW_A8_SENSE_MS - now + 999u) / 1000u;
            for (p = bits = 0; p < 8u; p++)
                for (i = 0; i < 16u; i++)
                    bits += hw_aud.se_changed[p] >> i & 1u;
            q = put_s(t, "audio8: SENSE: plug in/out ");
            q = put_dec(q, left);
            q = put_s(q, "s, ");
            q = put_dec(q, bits);
            q = put_s(q, " bits");
            *q = 0;
            hw_step(t);
        }
    }
    hw_scan_resume();
    hw_aud.se_state = HW_A8_SE_DONE;
    report("SE done");
    hw_step("audio8: sense done (its page next)");
}

/* Start-up (R0): L2 as audio7's KEY2 sets it up, with no key to wait
 * for, once the test screen is up; CLK_CON2 bit 9 is left as read (if it
 * reads set, L2 isn't tried: the link wouldn't run, HW-160). audio8's
 * keys run only while it is kept. */
void hw_audio_boot_l2(void)
{
    hw_aud.a8_boot = 1;
    if (JL_CLOCK->CLK_CON2 & CLK2_ALNK0_EN) {
        hw_aud.a8_off = HW_A8_OFF_L2;
        hw_step("audio8: L2 not run: CLK_CON2 bit 9 reads set");
        report("L2 boot bit 9");
        return;
    }
    l_boot = 1;
    hw_audio_l(2);
    l_boot = 0;
    hw_aud.a8_off = hw_aud.l_state == HW_L_KEPT ? HW_A8_OFF_NONE : HW_A8_OFF_L2;
    hw_step(hw_aud.a8_off ? "audio8: L2 FAILED at start-up, put back: audio8 off" : "audio8: L2 running");
}
#endif

/* --- audio9 (the spec side's clean-br17-audio9; the owner's rulings) ---- */

#if defined(SB_HW_AUDIO9)
static const char *const s2_word[HW_A9_S2_N] = { "both halves", "UPPER half only", "LOWER half only" };
static u32 pb5_seen;

static u32 daa7(void)
{
    return JL_ANA->DAA_CON7;        /* read only, never written */
}

/* The route up: R2 if it isn't in place (it is put back by the way
 * down), then the routed try of CON0 bits 7 and 8 (kind 3), kept if port
 * A stayed still and the matrix check passed; else the try's own undo of
 * the bits and its re-check, then R2 put back as read. */
static void a9_route_up(void)
{
    u32 stop;

    if (hw_aud.r2_state != HW_A8_R2_SET)
        hw_a8_r2();
    if (hw_aud.r2_state != HW_A8_R2_SET || hw_aud.r2_check) {
        if (hw_aud.r2_state == HW_A8_R2_SET)
            a8_r2_undo();
        hw_aud.a9_route = HW_A9_ROUTE_UNDONE;
        hw_step("audio9: R2 NOT as expected, put back: no route");
        return;
    }
    stop = a8_try(3, 0);
    if (stop == HW_A8_STOP_PC) {
        hw_aud.a9_route = HW_A9_ROUTE_UP;
        hw_aud.a9_ups++;
        hw_aud.daa7_route = daa7();
        hw_step("audio9: route up: the tone on the speaker");
        return;
    }
    a8_r2_undo();
    hw_aud.a9_route = HW_A9_ROUTE_UNDONE;
    hw_step(stop == HW_A8_STOP_PA ? "audio9: ROUTE UNDONE: port A moved" :
            stop == HW_A8_STOP_ROWS ? "audio9: route not up: a key held" :
            stop == HW_A8_STOP_AFTER ? "audio9: ROUTE UNDONE, CHECK AFTER BAD" : "audio9: ROUTE UNDONE: check failed");
}

/* Start-up (S0): DAA_CON7 read; L2 (audio8's); then, only if it is kept,
 * R2 and the route. */
void hw_audio9_boot(void)
{
    hw_aud.daa7_boot = hw_aud.daa7_last = daa7();
    hw_aud.daa7_reads = 1;
    hw_audio_boot_l2();
    if (hw_aud.l_state != HW_L_KEPT) {
        hw_aud.a9_route = HW_A9_ROUTE_NOL2;
        report("Route no L2");
        hw_step("audio9: L2 didn't run: no route");
        return;
    }
    a9_route_up();
}

/* SEQ: the route down (bits 7 and 8 clear, then port C back as read), or
 * up again (R2, then the routed try). */
void hw_a9_route_key(void)
{
    if (hw_aud.a9_route == HW_A9_ROUTE_UP) {
        a8_r2_undo();
        c1_key_marks();
        return;
    }
    if (a8_off("Route refused"))
        return;
    a8_release(INPUT_SEQ, "audio9: route: let go of SEQ");
    a9_route_up();
    c1_key_marks();
}

/* FX: the synth on (its late halves and longest fill counted from now) or
 * off (the tone). */
void hw_a9_synth_key(void)
{
    if (hw_aud.a9_synth) {
        hw_aud.a9_synth = 0;
        report("Synth off");
#if defined(SB_HW_AUDIO10)
        {
            /* audio10: the synth's longest fill, and with 8 voices (us). */
            static char t[48];
            char *p = put_s(t, "audio10: tone, fill ");

            p = put_dec(p, hw_aud.a10_fill_max / 24u);
            p = put_s(p, "us, 8v ");
            p = put_dec(p, hw_aud.a10_fill_max8 / 24u);
            p = put_s(p, "us");
            *p = 0;
            hw_step(t);
        }
#else
        hw_step("audio9: the tone");
#endif
        return;
    }
    hw_aud.a9_late0 = sb_audio.underruns;
    hw_aud.a9_late = 0;
    sb_audio.fill_max = 0;
    hw_aud.a9_fill_max = 0;
    hw_aud.a9_fallback = 0;
    hw_aud.a9_synth_ons++;
    hw_aud.a9_synth = 1;
    report("Synth on");
    hw_step("audio9: SYNTH: the keys play");
}

/* LFO: S2's next state: both halves, the upper alone, the lower alone. */
void hw_a9_s2_key(void)
{
    static const char label[HW_A9_S2_N][12] = { "S2 both", "S2 upper", "S2 lower" };
    static char t[48];
    char *p;

    hw_aud.a9_s2 = (hw_aud.a9_s2 + 1u) % HW_A9_S2_N;
    report(label[hw_aud.a9_s2]);
    p = put_s(t, "audio9: S2: ");
    p = put_s(p, s2_word[hw_aud.a9_s2]);
    *p = 0;
    hw_step(t);
}

/* From the scan's slot: PB5 (JL_PORTB->IN bit 5, HW-56's port rule),
 * read only; each change counted with its beat. */
void hw_a9_pb5_poll(void)
{
    u32 v = REG(0x00050044u) >> 5 & 1u;

#if defined(SB_TEST_A9_PB5)
    /* The test build: PB5 made to change every 1500 beats. */
    v ^= sb_beacon.beats / 1500u & 1u;
#endif
    if (!pb5_seen) {
        pb5_seen = 1;
        hw_aud.pb5_now = hw_aud.pb5_settled = v;
        return;
    }
    if (v != hw_aud.pb5_now) {
        hw_aud.pb5_now = v;
        hw_aud.pb5_t[hw_aud.pb5_raw_changes % HW_A9_PB5_TIMES] = sb_beacon.beats;
        hw_aud.pb5_raw_changes++;
    }
}

/* From main, about ten times a second: PB5's settled level (a record when
 * it changes), DAA_CON7 each minute (a record when it changes), the
 * synth's late halves and longest fill, and the fallback's record. */
#if defined(SB_HW_AUDIO10)
static void a10_tick(void);
#if defined(SB_HW_AUDIO11)
static void a11_time_now(void);
#endif
#if defined(SB_HW_AUDIO12)
static void a12_tick(void);
static u32 a12_big(char (*t)[16]);
#endif
#if defined(SB_HW_AUDIO13)
static void a13_big(char (*t)[16]);
static void a13_u2c_record(u32 ch, u32 v);
static void a13_arp_take(u32 t);
#endif
#endif

void hw_a9_tick(void)
{
    static u32 daa7_at, fallback_told;
    u32 last = hw_aud.pb5_t[(hw_aud.pb5_raw_changes + HW_A9_PB5_TIMES - 1u) % HW_A9_PB5_TIMES];

    if (pb5_seen && hw_aud.pb5_now != hw_aud.pb5_settled
            && (!hw_aud.pb5_raw_changes || sb_beacon.beats - last >= HW_A9_PB5_SETTLE_MS)) {
        hw_aud.pb5_settled = hw_aud.pb5_now;
        hw_aud.pb5_logged++;
        report(hw_aud.pb5_settled ? "PB5 1" : "PB5 0");
    }
    if (sb_beacon.beats - daa7_at >= HW_A9_DAA7_MS) {
        u32 v = daa7();

        daa7_at = sb_beacon.beats;
        hw_aud.daa7_reads++;
        if (v != hw_aud.daa7_last) {
            hw_aud.daa7_last = v;
            hw_aud.daa7_changes++;
            report("DAA7 changed");
        }
    }
    if (hw_aud.a9_synth || hw_aud.a9_synth_ons) {
        if (hw_aud.a9_synth)
            hw_aud.a9_late = sb_audio.underruns - hw_aud.a9_late0;
        if (sb_audio.fill_max > hw_aud.a9_fill_max)
            hw_aud.a9_fill_max = sb_audio.fill_max;
        hw_aud.a9_fill_last = sb_audio.fill_last;
    }
    if (hw_aud.a9_fallback && fallback_told != hw_aud.a9_fallback) {
        fallback_told = hw_aud.a9_fallback;
        report("Synth fallback");
        hw_step("audio9: SYNTH LATE: back to the tone");
    }
#if defined(SB_HW_AUDIO10)
    a10_tick();
#endif
}
#endif

#if defined(SB_HW_AUDIO10)
/* --- audio10 (the spec side's clean-br17-audio10; the owner's rulings) --- */

static const char fmt_label[HW_A10_FMTS][12] = { "F P", "F U", "F L", "F N", "F N'" };
static const char *const fmt_word[HW_A10_FMTS] = {
    "P: both halves", "U: upper half, lower 0", "L: lower half, upper 0", "N: upper +, lower -", "N': upper -, lower +",
};
static u32 m_prev_raw, m_last_beat, m_logged;
#if defined(SB_HW_AUDIO11)
static u32 m_jump_from;
#endif

/* LFO: F's next format, for everything the link plays. */
void hw_a10_fmt_key(void)
{
    static char t[48];
    char *p;

    hw_aud.a9_s2 = (hw_aud.a9_s2 + 1u) % HW_A10_FMTS;
    hw_aud.a10_fmt_t[hw_aud.a10_fmt_changes % HW_A10_FMT_LOG] = sb_beacon.beats << 3 | hw_aud.a9_s2;
    hw_aud.a10_fmt_changes++;
    report(fmt_label[hw_aud.a9_s2]);
    p = put_s(t, "audio10: F ");
    p = put_s(p, fmt_word[hw_aud.a9_s2]);
    *p = 0;
    hw_step(t);
}

static void hold_log(u32 hold, u32 on)
{
    hw_aud.hold_t[hw_aud.hold_n % HW_A10_HOLD_LOG] = sb_beacon.beats << 8 | hold << 1 | on;
    hw_aud.hold_n++;
}

/* PLAY, HOME, ENV, GLO and REC: the holds. Each toggles, but the scan's:
 * it ends by itself after HW_A10_SCAN_MS (no key works while it holds). */
void hw_a10_hold_key(u32 hold)
{
    static const char label[5][2][16] = {
        { "zero off", "ZERO on" }, { "LED blink on", "LED HELD" }, { "screen on", "SCREEN HELD" },
        { "log on", "LOG HELD" }, { "scan on", "SCAN HELD" },
    };
    static const char *const text[5][2] = {
        { "audio10: the samples back", "audio10: ZERO samples (PLAY again: back)" },
        { "audio10: the LED blink back", "audio10: LED blink HELD (HOME again)" },
        { "audio10: the screen back", "audio10: SCREEN HELD (ENV again)" },
        { "audio10: the log back", "audio10: LOG HELD (GLO again)" },
        { "audio10: the scan back", "audio10: SCAN HELD 5 s, no key works" },
    };
    u32 on = !(hw_aud.holds >> hold & 1u);

    if (hold == HW_A10_SCAN && !on)
        return;
    if (hold == HW_A10_LOG && on)
        report(label[hold][1]);        /* written before the hold begins */
    if (on)
        hw_aud.holds |= 1u << hold;
    else
        hw_aud.holds &= ~(1u << hold);
    hold_log(hold, on);
    if (hold == HW_A10_SCREEN && !on)
        hw_hold_screen = 0;
    hw_step(text[hold][on]);
    if (hold == HW_A10_SCREEN && on)
        hw_hold_screen = 1;
    if (hold == HW_A10_SCAN) {
        hw_aud.scan_until = sb_beacon.beats + HW_A10_SCAN_MS;
        hw_hold_sweeps = 1;
        hw_scan_hold();
    }
    if (hold != HW_A10_LOG || !on)
        report(label[hold][on]);
}

/* From main, each move of MASTER that input.c reports. */
void hw_a10_master(u32 value)
{
    hw_aud.m_value = value;
    hw_aud.m_raw = sb_input.pot_raw;
    hw_aud.m_ring[hw_aud.m_ring_n % HW_A10_MRING] = (sb_beacon.beats >> 2 & 0x3FFFFFu) << 10 | (value & 0x3FFu);
#if defined(SB_HW_AUDIO11)
    {
        u32 k = hw_aud.m_ring_n % HW_A10_MRING, sh = 16u * (k & 1u);

        hw_aud.m_raw_ring[k / 2u] = (hw_aud.m_raw_ring[k / 2u] & ~(0xFFFFu << sh)) | (sb_input.pot_raw & 0xFFFFu) << sh;
    }
#endif
    hw_aud.m_ring_n++;
    hw_aud.m_changes++;
    m_last_beat = sb_beacon.beats;
}

/* From the scan's slot: the pot's raw readings, each step from the one
 * before; more than 32 counts as a jump. */
void hw_a10_pot_poll(void)
{
    u32 raw = sb_input.pot_raw, d;

    if (raw == m_prev_raw)
        return;
    d = raw > m_prev_raw ? raw - m_prev_raw : m_prev_raw - raw;
#if defined(SB_HW_AUDIO11)
    m_jump_from = m_prev_raw;
#endif
    m_prev_raw = raw;
    if (!hw_aud.m_raw && !hw_aud.m_changes) {
        hw_aud.m_raw = raw;     /* the first reading: no step */
        return;
    }
    if (d > 32u) {
        hw_aud.m_jumps++;
#if defined(SB_HW_AUDIO11)
        hw_aud.m_jump_t[hw_aud.m_jump_n % HW_A11_JUMPS] = (sb_beacon.beats >> 2 & 0xFFFu) << 20
                                                          | (m_jump_from & 0x3FFu) << 10 | (raw & 0x3FFu);
        hw_aud.m_jump_n++;
#endif
    }
    if (d > hw_aud.m_maxdelta)
        hw_aud.m_maxdelta = d;
}

/* From hw_a9_tick: the scan hold's end and countdown, MASTER's record
 * once it has stood still HW_A10_STILL_MS, the levels applied now. */
static void a10_tick(void)
{
    static u32 shown;

    hw_aud.m_tone_gain = hw_aud.gain;
    hw_aud.m_synth_target = sb_audio.engine[SYNTH_MASTER];
    if (hw_aud.holds >> HW_A10_SCAN & 1u) {
        s32 left = (s32)(hw_aud.scan_until - sb_beacon.beats);

        if (left <= 0) {
            hw_scan_resume();
            hw_hold_sweeps = 0;
            hw_aud.holds &= ~(1u << HW_A10_SCAN);
            hold_log(HW_A10_SCAN, 0);
            report("scan hold end");
            hw_step("audio10: the scan back (ended by itself)");
        } else if ((u32)left / 1000u != shown) {
            static char t[40];
            char *p;

            shown = (u32)left / 1000u;
            p = put_s(t, "audio10: SCAN HELD, ");
            p = put_dec(p, shown + 1u);
            p = put_s(p, " s");
            *p = 0;
            hw_step(t);
        }
    }
    if (hw_aud.m_changes != m_logged && sb_beacon.beats - m_last_beat >= HW_A10_STILL_MS) {
        m_logged = hw_aud.m_changes;
        report("MASTER still");
    }
#if defined(SB_HW_AUDIO11)
    {
        static u32 timed;

        if (!timed) {
            timed = 1;
            a11_time_now(); /* the start's set-up timed once, TIMER0 running */
        }
    }
    hw_aud.m_level = hw_aud.m_value * hw_aud.m_value * 100u / 10465u;
#if defined(SB_HW_AUDIO12)
    a12_tick();
#endif
    hw_a11_big(0);
#endif
}
#endif

#if defined(SB_HW_AUDIO11)
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
#if !defined(SB_HW_AUDIO13)
static const u8 a11_chan[HW_A11_CHANS] = { 0, 1, 3, 4, 5, 6, 7, 10, 11 };
#endif
static const u8 a11_index[12] = { 0, 1, 0xFF, 2, 3, 4, 5, 6, 0xFF, 0xFF, 7, 8 };
static volatile u32 cv_busy, cv_hold;
static u32 cv_ch, cv_set, cv_t0, cv_turn, cv_next, cv_pot_new, cv_pot_v, cv_swept;

/* CON's fields but the enable and start: the SDK's (HW-167: the channel
 * in bits 8-11, bits 0-2 0b110, bits 12-15 0xF, bit 3) or the old (the
 * channel alone). Bit 5, the interrupt enable, is not set in either: the
 * build polls bit 7 (the SDK sets it). */
static u32 a11_fields(u32 ch, u32 set)
{
    return set == HW_A11_SDK ? (ch << 8 | 0xFu << 12 | 1u << 3 | 6u) : ch << 8;
}

/* A conversion started: the SDK's three writes, or the old one. */
static void cv_start(u32 ch)
{
    u32 set = hw_aud.adc_setup, b = a11_fields(ch, set);

    if (set == HW_A11_SDK) {
        JL_ADC->CON = b | 1u << 6;              /* 1: bit 6 with bit 4 clear (the pending flag) */
        JL_ADC->CON = b | 1u << 6 | 1u << 4;    /* 2: the enable added */
        JL_ADC->CON = b | 1u << 6 | 1u << 4;    /* 3: the start, bit 6 set again */
    } else {
        JL_ADC->CON = b | 1u << 4 | 1u << 6;
    }
    cv_ch = ch;
    cv_set = set;
    cv_t0 = sb_now();
    cv_busy = 1;
}

/* A reading kept: the channel's last, its least and greatest, and its
 * values with counts (exact while it has shown 4 distinct values or
 * fewer; past that the slot with the fewest goes to the newer value, its
 * count to "other"). */
static void cv_record(u32 ch, u32 set, u32 v, u32 d)
{
    u32 i, k, lo = 0xFFFFFFFFu, at = 0, *sl;

#if defined(SB_HW_AUDIO13)
    /* U2-C: the D- and D+ pads (channels 12 and 13), kept apart. */
    if (ch >= 12u) {
        hw_aud.adc_conv_n[set]++;
        a13_u2c_record(ch, v);
        return;
    }
#endif
    i = a11_index[ch];
    hw_aud.adc_last[ch] = v;
    hw3.adc[ch] = v;
    hw_aud.adc_conv_n[set]++;
    if (!hw_aud.adc_conv_min[set] || d < hw_aud.adc_conv_min[set])
        hw_aud.adc_conv_min[set] = d ? d : 1u;
    if (d > hw_aud.adc_conv_max[set])
        hw_aud.adc_conv_max[set] = d;
    if (ch == 4) {
        cv_pot_v = v;
        cv_pot_new = 1;
    }
    if (i == 0xFFu)
        return;
    if (!hw_aud.adc_n[set][i]++) {
        hw_aud.adc_mm[set][i] = v << 16 | v;
    } else {
        if (v < hw_aud.adc_mm[set][i] >> 16)
            hw_aud.adc_mm[set][i] = v << 16 | (hw_aud.adc_mm[set][i] & 0xFFFFu);
        if (v > (hw_aud.adc_mm[set][i] & 0xFFFFu))
            hw_aud.adc_mm[set][i] = (hw_aud.adc_mm[set][i] & 0xFFFF0000u) | v;
    }
    sl = hw_aud.adc_v[set][i];
    for (k = 0; k < HW_A11_SLOTS; k++) {
        u32 c = sl[k] & 0x3FFFFFu;

        if (c && sl[k] >> 22 == v) {
            if (c < 0x3FFFFFu)
                sl[k]++;
            return;
        }
        if (c < lo) {
            lo = c;
            at = k;
        }
    }
    hw_aud.adc_other[set][i] += lo;
    sl[at] = v << 22 | 1u;
}

/* The sweep's next channel: the kept ones but MASTER's, each in turn;
 * with audio13's U2-C on, channels 12 and 13 (USB D- and D+, HW-129) as
 * two more. */
#if defined(SB_HW_AUDIO13)
#define A11_SWEEP_N (HW_A11_CHANS + 2u)
static const u8 a13_chan[A11_SWEEP_N] = { 0, 1, 3, 4, 5, 6, 7, 10, 11, 12, 13 };
#define A11_SWEEP a13_chan
#else
#define A11_SWEEP_N HW_A11_CHANS
#define A11_SWEEP a11_chan
#endif
static u32 cv_sweep_next(void)
{
    u32 n, ch, down = hw_aud.a9_route == HW_A9_ROUTE_DOWN || hw_aud.a9_route == HW_A9_ROUTE_UNDONE
                      || hw_aud.a9_route == HW_A9_ROUTE_NOL2;

    for (n = 0; n < A11_SWEEP_N; n++) {
        ch = A11_SWEEP[cv_next];
        cv_next = (cv_next + 1u) % A11_SWEEP_N;
        if (!cv_next)
            hw_aud.adc_passes++;
        if (ch == 4 || ((ch == 6 || ch == 7) && !down))
            continue;
#if defined(SB_HW_AUDIO13)
        /* U2-C: channels 12 and 13 only while its key has it on. */
        if (ch >= 12u && !hw_aud.u2c_on)
            continue;
#endif
        return ch;
    }
    return 4;
}

/* TIMER0's slot (main.c): the conversion in flight looked at, the next
 * started. */
void hw_a11_adc_poll(void)
{
    u32 t = sb_now(), d, con;

    if (cv_hold)
        return;
    if (cv_busy) {
        d = t - cv_t0;
        con = JL_ADC->CON;
        if (!A11_SEEN(con, d)) {
            if (d < A11_TIMEOUT)
                return;
            hw_aud.adc_conv_to[cv_set]++;
            if (cv_ch < 12u)
                hw3.adc[cv_ch] = 0xFFFFu;
#if defined(SB_HW_AUDIO13)
            else
                hw_aud.u2c_to++;
#endif
        } else {
            cv_record(cv_ch, cv_set, JL_ADC->RES & 0x3FFu, d);
        }
        cv_busy = 0;
    }
    /* MASTER every other conversion; only MASTER while the scan is held. */
    cv_turn ^= 1u;
    cv_start(cv_turn || hw_hold_sweeps ? 4u : cv_sweep_next());
    cv_swept++;
    d = sb_now() - t;
    if (d > hw_aud.adc_pass_max)
        hw_aud.adc_pass_max = d;
}

/* input.c's pot(), once a scan: MASTER's newest reading, if one came. */
int hw_a11_pot_take(u32 *v)
{
    if (!cv_pot_new)
        return 0;
    cv_pot_new = 0;
    *v = cv_pot_v;
    return 1;
}

/* One conversion of channel 4 timed by a tight poll, from main or the
 * start (the slot's service held meanwhile; main never fills a half, so
 * the wait never delays one). Its CON writes, and CON read after them,
 * are kept for the set-up. */
static u32 cv_tight(void)
{
    u32 t0 = sb_now(), d, con, set = hw_aud.adc_setup, b = a11_fields(4, set), v = 0;

    u32 spins = 0;

    cv_hold = 1;
    while (cv_busy && !A11_SEEN(JL_ADC->CON, sb_now() - cv_t0) && sb_now() - t0 < A11_TIMEOUT
           && ++spins < A11_FIRST_SPINS)
        ;
    spins = 0;
    cv_busy = 0;
    cv_start(4);
    hw_aud.sar_con[set][0] = set == HW_A11_SDK ? b | 1u << 6 : b | 1u << 4 | 1u << 6;
    hw_aud.sar_con[set][1] = set == HW_A11_SDK ? b | 1u << 6 | 1u << 4 : 0;
    hw_aud.sar_con[set][2] = hw_aud.sar_con[set][1];
    hw_aud.sar_con[set][3] = JL_ADC->CON;
    for (;;) {
        d = sb_now() - cv_t0;
        con = JL_ADC->CON;
        if (A11_SEEN(con, d)) {
            v = JL_ADC->RES & 0x3FFu;
            cv_record(4, set, v, d);
            break;
        }
        if (d >= A11_TIMEOUT || ++spins >= A11_FIRST_SPINS) {
            hw_aud.adc_conv_to[set]++;
            break;
        }
    }
    hw_aud.adc_conv_tight[set] = d;
    cv_pot_new = 0;
    cv_busy = 0;
    cv_hold = 0;
    return v;
}

static void a11_time_now(void)
{
    cv_tight();
}

/* input_start: MASTER's first reading, in the SDK's set-up. It comes
 * before TIMER0 runs, when sb_now() stands still (main.c), so the wait is
 * counted in passes (A11_FIRST_SPINS, many milliseconds at any clock the
 * chip may run) and not timed; the first conversion timed is main's
 * (a10_tick). */
u32 hw_a11_pot_first(void)
{
    u32 i, k, v = 0;

    hw_aud.adc_setup = HW_A11_SDK;
    for (k = 0; k < 12u; k++)
        hw_aud.adc_last[k] = hw3.adc[k] = 0xFFFFu;
    cv_start(4);
    for (i = 0; i < A11_FIRST_SPINS && !(JL_ADC->CON & A11_DONE); i++)
        ;
    if (i < A11_FIRST_SPINS)
        v = JL_ADC->RES & 0x3FFu;
    else
        hw_aud.adc_conv_to[HW_A11_SDK]++;
    cv_busy = 0;
    return v;
}

/* SEL: the next set-up, the SDK's or the old, named on the step row and
 * logged; one conversion timed at once. */
void hw_a11_setup_key(void)
{
    hw_aud.adc_setup = hw_aud.adc_setup == HW_A11_SDK ? HW_A11_OLD : HW_A11_SDK;
    hw_aud.adc_set_t[hw_aud.adc_set_n % HW_A11_SET_LOG] = sb_beacon.beats << 1 | hw_aud.adc_setup;
    hw_aud.adc_set_n++;
    cv_tight();
    report(hw_aud.adc_setup == HW_A11_SDK ? "ADC SDK" : "ADC old");
    hw_step(hw_aud.adc_setup == HW_A11_SDK ? "audio11: SARADC the SDK's (div 96, delay F, bit 3)"
                                           : "audio11: SARADC the old (fields 0)");
}

/* E: the key status in large text, three lines of 12 characters at three
 * times the font (15 x 21 pixels a glyph on an 18 x 24 cell), from y 40
 * to 112, in place of the matrix grid, the ports and the event box. Drawn
 * when it changes (force: after the test screen is drawn again). */
#define A11_BIG_Y 40u
static int put_differs(const char *a, const char *b)
{
    for (; *a || *b; a++, b++)
        if (*a != *b)
            return 1;
    return 0;
}

static char *put_level(char *p, u32 l)
{
    /* l of 10000: whole per cent, at least 1 when not silent. */
    return put_dec(p, l && l < 100u ? 1u : l / 100u);
}

void hw_a11_big(u32 force)
{
    static const char *const hold_name[5] = { "ZERO", "LED", "SCRN", "LOG", "SCAN" };
    char t[3][16], *p;
    u32 i, h = hw_aud.holds, first = 5, n = 0;

    p = put_s(t[0], "N ");
    p = put_s(p, hw_aud.a9_synth ? "SYNTH " : "TONE ");
    p = put_s(p, hw_aud.adc_setup == HW_A11_SDK ? "SDK" : "OLD");
    *p = 0;
    p = put_s(t[1], "M");
    p = put_dec(p, hw_aud.m_value);
    p = put_s(p, " r");
    p = put_dec(p, sb_input.pot_raw);
    *p = 0;
    p = put_s(t[2], "L");
    p = put_level(p, hw_aud.m_level);
    p = put_s(p, "% ");
    for (i = 0; i < 5u; i++)
        if (h >> i & 1u) {
            if (first == 5u)
                first = i;
            n++;
        }
    if (first == 5u) {
        p = put_s(p, "-");
    } else {
        p = put_s(p, hold_name[first]);
        if (first == HW_A10_SCAN) {
            s32 left = (s32)(hw_aud.scan_until - sb_beacon.beats);
            *p++ = (char)('1' + (left > 0 ? (u32)left / 1000u % 9u : 0u));
        }
        if (n > 1u)
            *p++ = '+';
    }
    *p = 0;
#if defined(SB_HW_AUDIO13)
    /* U2: the cable state, the start's words and U2-C, in place of
     * audio11's lines (the sweep's still take the first two). */
    a13_big(t);
#endif
#if defined(SB_HW_AUDIO12)
    /* S: while the sweep runs (and 10 s after), its two lines. */
    (void)a12_big(t);
#endif
    for (i = 0; i < 3u; i++)
        if (force || put_differs(t[i], hw_aud.big[i]))
            break;
    if (i == 3u)
        return;
    for (i = 0; i < 3u; i++) {
        u32 k;
        for (k = 0; k < 16u; k++)
            hw_aud.big[i][k] = t[i][k];
    }
    if (hw_hold_screen || sb_beacon.screen != SB_SCREEN_TEST)
        return;
    lcd_wait();
    gfx_fill(4, A11_BIG_Y, SCREEN_W - 8, 72, RGB565(0, 0, 0));
    gfx_text(6, A11_BIG_Y, t[0], hw_aud.a9_route == HW_A9_ROUTE_UP ? RGB565(0, 63, 0) : RGB565(31, 0, 0), RGB565(0, 0, 0), 3);
    gfx_text(6, A11_BIG_Y + 24u, t[1], RGB565(31, 63, 31), RGB565(0, 0, 0), 3);
    gfx_text(6, A11_BIG_Y + 48u, t[2], h ? RGB565(31, 63, 0) : RGB565(31, 63, 31), RGB565(0, 0, 0), 3);
    lcd_send_rows(A11_BIG_Y, 72);
    lcd_wait();
}
#endif

#if defined(SB_HW_AUDIO12)
/* --- audio12 (the spec side's clean-br17-audio12; the owner's rulings) ---
 * S: LFO on the test screen (the engine leaves LFO alone) starts a sweep:
 * for each algorithm 1 to 10, ALGORITHM set, an 8-note chord over three
 * octaves held HW_A12_CHORD_FRAMES, released, and its release waited for
 * (every voice idle, at most HW_A12_REL_FRAMES); then the next. LFO during
 * a sweep stops it after the chord in progress, released. It runs in the
 * engine's own context (synth_fill, before the engine's blocks), timed in
 * the frames the synth fills. Each algorithm's longest fill (with the
 * voices then), soft-clipped and saturated samples and late halves (the
 * audio layer's underruns) are kept for the log; the large area shows the
 * algorithm and its longest fill. */
static const u8 a12_chord[HW_A12_NOTES_CHORD] = { 48, 55, 60, 64, 67, 72, 79, 84 };
static u32 a12_end_beat, a12_told;

static void a12_notes(u32 on)
{
    u32 k;

    for (k = 0; k < HW_A12_NOTES_CHORD; k++) {
        if (on)
            fm_note_on(a12_chord[k], FM_KEY_VELOCITY);
        else
            fm_note_off(a12_chord[k]);
    }
}

/* The algorithm's counts since its chord began. */
static void a12_counts(u32 a)
{
    hw_aud.as_soft[a] = hw_aud.a10_soft - hw_aud.as_soft0;
    hw_aud.as_hard[a] = hw_aud.a10_hard - hw_aud.as_hard0;
    hw_aud.as_late[a] = sb_audio.underruns - hw_aud.as_late0;
}

/* From synth_fill, before the engine's blocks: fr frames this call. */
static void a12_sweep_step(u32 fr)
{
    u32 a = hw_aud.as_alg - 1u;

    if (hw_aud.as_state == HW_A12_SW_CHORD) {
        if (!hw_aud.as_frames) {
            fm_a12_algorithm(hw_aud.as_alg);
            hw_aud.as_soft0 = hw_aud.a10_soft;
            hw_aud.as_hard0 = hw_aud.a10_hard;
            hw_aud.as_late0 = sb_audio.underruns;
            a12_notes(1);
            hw_aud.as_chords++;
        }
        a12_counts(a);
        hw_aud.as_frames += fr;
        if (hw_aud.as_frames >= HW_A12_CHORD_FRAMES) {
            a12_notes(0);
            hw_aud.as_state = HW_A12_SW_RELEASE;
            hw_aud.as_frames = 0;
        }
    } else if (hw_aud.as_state == HW_A12_SW_RELEASE) {
        u32 v = sb_fm.voices[0] + sb_fm.voices[1];

        a12_counts(a);
        hw_aud.as_frames += fr;
        if (v && hw_aud.as_frames < HW_A12_REL_FRAMES)
            return;
        hw_aud.as_rel[a] = hw_aud.as_frames | (v ? HW_A12_REL_BOUND : 0u);
        hw_aud.as_frames = 0;
        if (hw_aud.as_stop || hw_aud.as_alg >= HW_A11_ALGS) {
            hw_aud.as_state = hw_aud.as_stop ? HW_A12_SW_STOPPED : HW_A12_SW_DONE;
        } else {
            hw_aud.as_alg++;
            hw_aud.as_state = HW_A12_SW_CHORD;
        }
    }
}

static u32 a12_running(void)
{
    return hw_aud.as_state == HW_A12_SW_CHORD || hw_aud.as_state == HW_A12_SW_RELEASE;
}

/* LFO, on the test screen: a sweep (the synth on first), or a stop asked. */
void hw_a12_sweep_key(void)
{
    u32 k;

    if (a12_running()) {
        hw_aud.as_stop = 1;
        report("Sweep stop asked");
        hw_step("audio12: SWEEP: stops after this chord");
        return;
    }
    if (!hw_aud.a9_synth)
        hw_a9_synth_key();
    for (k = 0; k < HW_A11_ALGS; k++)
        hw_aud.as_fill[k] = hw_aud.as_fill_v[k] = hw_aud.as_soft[k] = hw_aud.as_hard[k] = hw_aud.as_late[k]
            = hw_aud.as_rel[k] = 0;
    hw_aud.as_stop = 0;
    hw_aud.as_alg = 1;
    hw_aud.as_frames = 0;
    hw_aud.as_runs++;
    a12_told = 0;
    /* The state last: the audio interrupt starts the chord when it sees it. */
    __asm__ volatile("" ::: "memory");
    hw_aud.as_state = HW_A12_SW_CHORD;
    report("Sweep start");
    hw_step("audio12: SWEEP: algorithms 1 to 10, hands off");
}

/* From a10_tick: the sweep's end, recorded once. */
static void a12_tick(void)
{
    if ((hw_aud.as_state == HW_A12_SW_DONE || hw_aud.as_state == HW_A12_SW_STOPPED) && !a12_told) {
        a12_told = 1;
        a12_end_beat = sb_beacon.beats ? sb_beacon.beats : 1u;
        report(hw_aud.as_state == HW_A12_SW_DONE ? "Sweep done" : "Sweep stopped");
        hw_step(hw_aud.as_state == HW_A12_SW_DONE ? "audio12: SWEEP DONE (all ten)" : "audio12: SWEEP STOPPED");
    }
}

/* The large area's first two lines while the sweep runs, and for 10 s
 * after it ends: the algorithm (the slowest, after) and its longest fill
 * in us with the voices then. Returns 1 if it wrote them. */
static u32 a12_big(char (*t)[16])
{
    u32 a, k;
    char *p;

    if (a12_running()) {
        a = hw_aud.as_alg - 1u;
        p = put_s(t[0], hw_aud.as_stop ? "STOP A" : "SWEEP A");
    } else if (a12_told && sb_beacon.beats - a12_end_beat < 10000u) {
        for (a = 0, k = 1; k < HW_A11_ALGS; k++)
            if (hw_aud.as_fill[k] > hw_aud.as_fill[a])
                a = k;
        p = put_s(t[0], hw_aud.as_state == HW_A12_SW_DONE ? "DONE A" : "STOPD A");
    } else {
        return 0;
    }
    p = put_dec(p, a + 1u);
    *p = 0;
    p = put_s(t[1], "F");
    p = put_dec(p, hw_aud.as_fill[a] / 24u);
    p = put_s(p, "US ");
    p = put_dec(p, hw_aud.as_fill_v[a]);
    p = put_s(p, "V");
    *p = 0;
    return 1;
}

/* D5, as audio12b (the owner's ruling after #240 stopped on the unit):
 * power-on gives the test screen, as audio11's, and SEL there runs the
 * instrument's start, until it has worked on the unit. Each stage writes a
 * record before it runs and shows itself on the step row, so a stage that
 * hangs names itself: the synth, ALNK0, L2, R2, the route, the panel. A
 * stage the test screen's own start already brought up is recorded and
 * left as it is (ALNK0 isn't started twice). Then the panel (views.c) in
 * place of the test screen, with a line that says whether the route is
 * up and, if not, why (the step row's text; the instrument runs on,
 * silent); main gives the events to the panel, so the test screen's keys
 * do nothing more. */
static void a12_stage(const char *label, const char *step)
{
    report(label);
    hw_step(step);
}

#if defined(SB_HW_AUDIO13)
void hw_a12_instrument(u32 cold)
#else
void hw_a12_instrument(void)
#endif
{
    static char t[40];
    const char *s;
    char *p;

#if defined(SB_HW_AUDIO13)
    /* audio13 (D5, the owner's ruling): from power-on (cold) the engine
     * first, then every stage as #240's start ran them; from SEL on the
     * test screen, as audio12b. */
    if (!cold)
        a8_release(INPUT_SEL, "audio12: instrument: let go of SEL");
    a12_stage("Inst engine", cold ? "audio13: instrument: the engine" : "audio13: instrument: engine already started");
    if (cold) {
        fm_init();
        hw_aud.daa7_boot = hw_aud.daa7_last = daa7();
        hw_aud.daa7_reads = 1;
    }
#else
    a8_release(INPUT_SEL, "audio12: instrument: let go of SEL");
#endif
    a12_stage("Inst synth", "audio12: instrument: the synth");
    if (!hw_aud.a9_synth)
        hw_a9_synth_key();
    a12_stage("Inst ALNK0", hw_aud.started ? "audio12: instrument: ALNK0 already running"
                                           : "audio12: instrument: ALNK0");
    if (!hw_aud.started)
        hw_audio_start();
    a12_stage("Inst L2", hw_aud.l_state == HW_L_KEPT ? "audio12: instrument: L2 already kept"
                                                     : "audio12: instrument: L2");
    if (hw_aud.l_state != HW_L_KEPT)
        hw_audio_boot_l2();
    a12_stage("Inst R2", hw_aud.r2_state == HW_A8_R2_SET ? "audio12: instrument: R2 already set"
                                                         : "audio12: instrument: R2");
    if (hw_aud.l_state == HW_L_KEPT && hw_aud.r2_state != HW_A8_R2_SET && hw_aud.a9_route != HW_A9_ROUTE_UP)
        hw_a8_r2();
    a12_stage("Inst route", hw_aud.a9_route == HW_A9_ROUTE_UP ? "audio12: instrument: route already up"
                                                              : "audio12: instrument: the route");
    if (hw_aud.l_state != HW_L_KEPT) {
        hw_aud.a9_route = HW_A9_ROUTE_NOL2;
        hw_step("audio12: L2 didn't run: no route");
    } else if (hw_aud.a9_route != HW_A9_ROUTE_UP && !a8_off("Route refused")) {
        a9_route_up();
    }
    if (hw_aud.a9_route == HW_A9_ROUTE_UP) {
        p = put_s(t, "audio12: sound on");
    } else {
        s = hw_step_now();
        if (s[0] == 'a' && s[1] == 'u' && s[2] == 'd' && s[3] == 'i' && s[4] == 'o' && s[6] == ':' && s[7] == ' ')
            s += 8;
        p = put_s(t, "NO SOUND: ");
        while (*s && p < t + 38)
            *p++ = *s++;
    }
    *p = 0;
    {
        /* The line in the log too, in the large area's words (unused now). */
        u32 k;

        for (k = 0; k < 48u; k++)
            hw_aud.big[k / 16u][k % 16u] = k < (u32)(p - t) ? t[k] : 0;
    }
    hw_aud.start_mode = HW_A12_INSTRUMENT;
    a12_stage("Inst panel", "audio12: instrument: the panel");
    lcd_wait();
    view_message(t, 0);
    /* No more of the test screen's rows over the panel. */
    hw_hold_screen = 1;
}

/* G: the engine's reports (fm.h), from its context. */
void fm_a12_note_on(u32 note, u32 voice, u32 alg_read, u32 alg_voice, u32 local)
{
    hw_aud.g_note[hw_aud.g_note_n % HW_A12_NOTES] = note << 24 | (voice & 0xFFu) << 16 | (alg_read & 0xFFu) << 8
                                                   | (alg_voice & 0x7Fu) << 1 | (local & 1u);
    hw_aud.g_note_n++;
}

void fm_a12_turn(u32 taken, u32 alg)
{
    if (taken)
        hw_aud.g_turns++;
    else
        hw_aud.g_turns_off++;
    hw_aud.g_turn_alg = alg;
}
#endif

#if defined(SB_HW_AUDIO13)
/* --- audio13 (the spec side's clean-br17-audio13; the owner's rulings) ---
 * D5: power-on starts the instrument (hw_a12_instrument from cold); HOME
 * held at power-on gives the test screen.
 * U2: the USB block read, never written: the first core's CON0 and CON1
 * and the pins' block's CON0 to CON2 (HW-171). No access through CON1's
 * port (an access there is a write, HW-86); no pin's set-up changed; USB
 * stays off. U2-A: at the app's start (start.c), a second later, and on
 * OCT- in the test screen. U2-B: every 100 ms while the test screen shows,
 * each change logged with its beat; SAVE marks the next cable state (a no
 * cable, b a charger, c a computer on, d asleep, e the cable out), and
 * the large area says whether any word differs from state a's. U2-C: OCT+
 * puts channels 12 and 13 (the D- and D+ pads, HW-129, HW-173) into
 * audio11's SARADC sweep, or takes them out; off at start-up; turned on,
 * it marks state a (U2-B's second run). The SARADC's CON is written as
 * audio11 writes it, for these channels too, and nothing else.
 * ARP: each step the engine plays (sb_arp's log), its frame count and the
 * fill's start by sb_now() (TIMER0, the fill times' timer, which the audio
 * interrupts don't drive); the gaps between steps of one chain (keys held,
 * ARP on), the shortest and longest, the longest chain's ends; in the
 * panel, the last gap on its message line; REC there saves the log. */
static const char a13_name[HW_A13_WORDS][3] = { "C0", "C1", "P0", "P1", "P2" };
static u32 a13_first_k, a13_c_last[2] = { 0xFFFFu, 0xFFFFu }, a13_c_logged[2], a13_c_beat[2];
static u32 a13_arp_seen, a13_arp_chain, a13_arp_f, a13_arp_u, a13_arp_f0, a13_arp_u0;
static u32 a13_shown, a13_shown_beat;
#if defined(SB_HW_AUDIO14)
static u32 a14_arp_was_on, a14_arp_n_saved;
#endif

static void u2_read(u32 *w)
{
    w[0] = JL_USB->CON0;
    w[1] = JL_USB->CON1;
    w[2] = JL_USB_IO->CON0;
    w[3] = JL_USB_IO->CON1;
    w[4] = JL_USB_IO->CON2;
#if defined(SB_TEST_A13_U2_CHANGE)
    /* The test build: CON0's bit 5 reads set in states b to d, as a cable
     * might show it (the reading changed, nothing written). */
    if (hw_aud.u2_state >= 1u && hw_aud.u2_state <= 3u)
        w[0] |= 1u << 5;
#endif
}

#if defined(SB_HW_AUDIO14)
/* P (the owner's ruling): the block at 0x16A00, its four words, read
 * only, with U2-A's; nothing is written there or to any clock register. */
static void p_read(u32 *w)
{
    u32 i;

    for (i = 0; i < HW_A14_P_WORDS; i++)
        w[i] = *(volatile u32 *)(HW_A14_P_BASE + 4u * i);
}
#endif

/* HOME let go (the route's check stops on a key held), at most 10 s, and
 * its events dropped, so the test screen doesn't take the press as its
 * own (#240's test-screen start). */
static void a13_let_go_home(void)
{
    u32 t0 = sb_beacon.beats;
    struct input_event e;

    hw_step("audio13: test screen: let go of HOME");
    while (input_value(INPUT_HOME) && sb_beacon.beats - t0 < 10000u)
        sb_wait_ms(10);
    sb_wait_ms(50);
    while (input_read(&e))
        ;
    while (input_read_audio(&e))
        ;
}

/* A cable state marked (SAVE, or U2-C turned on): state a takes the
 * words now as the ones the others are compared with. */
static void a13_mark(u32 st)
{
    hw_aud.u2_state = st;
    hw_aud.u2_mark[hw_aud.u2_mark_n % HW_A13_MARKS] = sb_beacon.beats << 3 | st;
    hw_aud.u2_mark_n++;
    if (!st)
        u2_read(hw_aud.u2_ref);
}

/* main, after core 1's screen: U2-A's first reading kept, its second a
 * second after the start (before the audio path in either start); then
 * HOME read: held, the test screen (returns 0); else the boot's record and
 * the instrument's start from cold (returns 1: no test screen). */
u32 hw_a13_power_on(void)
{
    u32 i, j, k, home = input_value(INPUT_HOME);

    for (i = 0; i < HW_A13_WORDS; i++)
        hw_aud.u2_boot[i] = hw_u2_boot[i];
#if defined(SB_HW_AUDIO14)
    for (i = 0; i < HW_A14_P_WORDS; i++)
        hw_aud.p_boot[i] = hw_p_boot[i];
#endif
    for (i = 0; i < HW_A13_RUNS; i++)
        for (j = 0; j < HW_A13_STATES; j++)
            for (k = 0; k < HW_A13_WORDS; k++)
                hw_aud.u2_and[i][j][k] = 0xFFFFFFFFu;
    for (i = 0; i < HW_A13_C_FIRST; i++)
        hw_aud.u2c_first[i] = 0xFFFFFFFFu;
    hw_step("audio13: U2-A: the second reading");
    while (sb_beacon.beats < 1000u)
        sb_wait_ms(10);
    u2_read(hw_aud.u2_late);
#if defined(SB_HW_AUDIO14)
    p_read(hw_aud.p_late);
#endif
    hw_aud.u2_late_beat = sb_beacon.beats;
    hw_aud.u2_late_blocks = sb_audio.blocks;
    for (i = 0; i < HW_A13_WORDS; i++)
        hw_aud.u2_ref[i] = hw_aud.u2_last[i] = hw_aud.u2_late[i];
    if (home) {
        hw_aud.a13_start = HW_A13_HOME;
        hw_aud.start_mode = HW_A12_TEST;
        a13_let_go_home();
        return 0;
    }
    hw_aud.a13_start = HW_A13_COLD;
    report("boot");
    hw_a12_instrument(1);
    return 1;
}

/* The test screen's U2 keys: OCT- reads the words again; OCT+ turns U2-C
 * on (marking state a) or off; SAVE marks the next cable state. */
void hw_a13_u2_key(u32 control)
{
    static const char *const label[HW_A13_STATES] = { "U2 a", "U2 b", "U2 c", "U2 d", "U2 e" };
    static const char *const say[HW_A13_STATES] = {
        "audio13: U2-B: state a, no cable", "audio13: U2-B: state b, a charger",
        "audio13: U2-B: state c, a computer on", "audio13: U2-B: state d, the computer asleep",
        "audio13: U2-B: state e, the cable out",
    };

    if (control == INPUT_OCT_DOWN) {
        u2_read(hw_aud.u2_key);
#if defined(SB_HW_AUDIO14)
        p_read(hw_aud.p_key);
#endif
        hw_aud.u2_key_beat = sb_beacon.beats;
        hw_aud.u2_key_n++;
        report("U2-A key");
        hw_step("audio13: U2-A: read again");
        return;
    }
    if (control == INPUT_OCT_UP) {
        hw_aud.u2c_on ^= 1u;
        hw_aud.u2c_toggles++;
        if (hw_aud.u2c_on) {
            a13_first_k = (hw_aud.u2c_toggles - 1u) / 2u % HW_A13_C_FIRST;
            hw_aud.u2c_first[a13_first_k] = 0xFFFFFFFFu;
            a13_c_last[0] = a13_c_last[1] = 0xFFFFu;
            hw_aud.u2_run = 1;
            a13_mark(0);
        }
        report(hw_aud.u2c_on ? "U2-C on" : "U2-C off");
        hw_step(hw_aud.u2c_on ? "audio13: U2-C ON: ch12 and ch13 in the sweep; state a"
                              : "audio13: U2-C off");
        return;
    }
    a13_mark((hw_aud.u2_state + 1u) % HW_A13_STATES);
    report(label[hw_aud.u2_state]);
    hw_step(say[hw_aud.u2_state]);
}

/* U2-B: the words every 100 ms while the test screen shows (main's tick):
 * each change logged, each word's bits ever set and always set in the
 * run's state, and the polls there. */
void hw_a13_u2_poll(void)
{
    u32 w[HW_A13_WORDS], i, k, r = hw_aud.u2_run, st = hw_aud.u2_state, sh = 6u * st;

    u2_read(w);
    hw_aud.u2_polls++;
    if ((hw_aud.u2_seen[r] >> sh & 63u) < 63u)
        hw_aud.u2_seen[r] += 1u << sh;
    for (i = 0; i < HW_A13_WORDS; i++) {
        hw_aud.u2_or[r][st][i] |= w[i];
        hw_aud.u2_and[r][st][i] &= w[i];
        if (w[i] != hw_aud.u2_last[i]) {
            k = hw_aud.u2_chg_n % HW_A13_CHANGES;
            hw_aud.u2_chg[k][0] = sb_beacon.beats << 3 | i;
            hw_aud.u2_chg[k][1] = w[i];
            hw_aud.u2_chg_n++;
            hw_aud.u2_last[i] = w[i];
        }
    }
}

/* U2-C: a reading of channel 12 or 13 (the slot's sweep): counted by
 * state, its least and greatest; each turn-on's first; logged when it
 * moves by more than 8 from the channel's last logged, or 2 s after it. */
static void a13_u2c_record(u32 ch, u32 v)
{
    u32 c = ch - 12u, st = hw_aud.u2_state, *f = &hw_aud.u2c_first[a13_first_k], b = sb_beacon.beats, d;

    if (!hw_aud.u2c_n[st][c]++) {
        hw_aud.u2c_mm[st][c] = v << 16 | v;
    } else {
        if (v < hw_aud.u2c_mm[st][c] >> 16)
            hw_aud.u2c_mm[st][c] = v << 16 | (hw_aud.u2c_mm[st][c] & 0xFFFFu);
        if (v > (hw_aud.u2c_mm[st][c] & 0xFFFFu))
            hw_aud.u2c_mm[st][c] = (hw_aud.u2c_mm[st][c] & 0xFFFF0000u) | v;
    }
    if (!c && *f >> 16 == 0xFFFFu)
        *f = v << 16 | (*f & 0xFFFFu);
    if (c && (*f & 0xFFFFu) == 0xFFFFu)
        *f = (*f & 0xFFFF0000u) | v;
    d = v > a13_c_logged[c] ? v - a13_c_logged[c] : a13_c_logged[c] - v;
    if (a13_c_last[c] == 0xFFFFu || d > 8u || b - a13_c_beat[c] >= 2000u) {
        hw_aud.u2c_log[hw_aud.u2c_log_n % HW_A13_C_LOG] = v << 22 | st << 19 | c << 18 | (b >> 6 & 0x3FFFFu);
        hw_aud.u2c_log_n++;
        a13_c_logged[c] = v;
        a13_c_beat[c] = b;
    }
    a13_c_last[c] = v;
}

/* The large area (the test screen): the cable state and whether a word
 * differs from state a's ("SAME AS A", or "CHANGED" and which); the
 * start's five words, one every 2 s; U2-C, off or its last readings. */
static void a13_big(char (*t)[16])
{
#if defined(SB_HW_AUDIO14)
    /* audio14: P's four words after U2-A's five, by their addresses' last
     * three digits ("A00" to "A0C": twelve cells a line). */
    u32 i, n = 0, first = 0, pg = sb_beacon.beats / 2000u % (HW_A13_WORDS + HW_A14_P_WORDS);
#else
    u32 i, n = 0, first = 0, pg = sb_beacon.beats / 2000u % HW_A13_WORDS;
#endif
    char *p = t[0];

    for (i = HW_A13_WORDS; i--;)
        if (hw_aud.u2_last[i] != hw_aud.u2_ref[i]) {
            first = i;
            n++;
        }
    *p++ = (char)('A' + hw_aud.u2_state);
    *p++ = ' ';
    if (!n) {
        p = put_s(p, "SAME AS A");
    } else if (n == 1u) {
        p = put_s(p, "CHANGED ");
        p = put_s(p, a13_name[first]);
    } else if (n <= 3u) {
        p = put_s(p, "CHG ");
        for (i = 0; i < HW_A13_WORDS; i++)
            if (hw_aud.u2_last[i] != hw_aud.u2_ref[i])
                p = put_s(p, a13_name[i]);
    } else {
        p = put_s(p, "CHANGED ");
        p = put_dec(p, n);
        *p++ = 'W';
    }
    *p = 0;
#if defined(SB_HW_AUDIO14)
    if (pg >= HW_A13_WORDS) {
        p = put_hex(t[1], (HW_A14_P_BASE + 4u * (pg - HW_A13_WORDS)) & 0xFFFu, 3);
        *p++ = ' ';
        p = put_hex(p, hw_aud.p_boot[pg - HW_A13_WORDS], 8);
        *p = 0;
    } else
#endif
    {
        p = put_s(t[1], a13_name[pg]);
        *p++ = ' ';
        p = put_hex(p, hw_aud.u2_boot[pg], 8);
        *p = 0;
    }
    if (!hw_aud.u2c_on) {
        p = put_s(t[2], "U2C OFF");
    } else {
        p = put_s(t[2], "U2C ");
        for (i = 0; i < 2u; i++) {
            if (i)
                *p++ = ' ';
            if (a13_c_last[i] == 0xFFFFu)
                *p++ = '-';
            else
                p = put_dec(p, a13_c_last[i]);
        }
    }
    *p = 0;
}

/* ARP (synth_fill, after the engine's blocks): each new step's frame
 * count (sb_arp's log) and t, the fill's start. A chain runs while ARP
 * is on and holds a note; a gap over HW_A13_GAP_MAX frames breaks it. */
static void a13_arp_take(u32 t)
{
    u32 n = sb_arp.log_count, f, g, u, k;

    if (!sb_arp.on || !sb_arp.held) {
        if (a13_arp_chain)
            hw_aud.arp_breaks++;
        a13_arp_chain = 0;
    }
    while (a13_arp_seen != n) {
        f = sb_arp.log_time[a13_arp_seen % ARP_LOG];
        a13_arp_seen++;
        k = hw_aud.arp_n % HW_A13_ARP_LOG;
        hw_aud.arp_log[k][0] = f;
        hw_aud.arp_log[k][1] = t;
        hw_aud.arp_n++;
        g = f - a13_arp_f;
        u = t - a13_arp_u;
        if (a13_arp_chain && g <= HW_A13_GAP_MAX) {
            if (!hw_aud.arp_gaps || g < hw_aud.arp_gmin_f)
                hw_aud.arp_gmin_f = g;
            if (g > hw_aud.arp_gmax_f)
                hw_aud.arp_gmax_f = g;
            if (!hw_aud.arp_gaps || u < hw_aud.arp_gmin_u)
                hw_aud.arp_gmin_u = u;
            if (u > hw_aud.arp_gmax_u)
                hw_aud.arp_gmax_u = u;
            hw_aud.arp_gaps++;
            hw_aud.arp_last_f = g;
            hw_aud.arp_last_u = u;
            a13_arp_chain++;
        } else {
            if (a13_arp_chain)
                hw_aud.arp_breaks++;
            a13_arp_chain = 1;
            a13_arp_f0 = f;
            a13_arp_u0 = t;
        }
        a13_arp_f = f;
        a13_arp_u = t;
        if (a13_arp_chain > hw_aud.arp_best_n) {
            hw_aud.arp_best_n = a13_arp_chain;
            hw_aud.arp_best_f0 = a13_arp_f0;
            hw_aud.arp_best_u0 = a13_arp_u0;
            hw_aud.arp_best_f1 = f;
            hw_aud.arp_best_u1 = t;
        }
    }
}

/* The panel (main's loop in the instrument): while ARP runs, its last gap
 * on the message line, "ARP gap <frames> fr <ms> ms", at most every 0.5 s
 * (main woken for it). */
void hw_a13_panel_tick(void)
{
    static char t[40];
    u32 b = sb_beacon.beats, w, ms10;
    char *p;

#if defined(SB_HW_AUDIO14)
    /* R: ARP turned off with steps not yet in a record: a record of its
     * own, so they reach the flash with or without REC. */
    if (a14_arp_was_on && !sb_arp.on && hw_aud.arp_n != a14_arp_n_saved) {
        a14_arp_n_saved = hw_aud.arp_n;
        hw_aud.arp_offs++;
        report("ARP off");
    }
    a14_arp_was_on = sb_arp.on;
#endif
    if (!sb_arp.on)
        return;
    w = a13_shown_beat + 500u;
    if (hw_aud.arp_gaps != a13_shown && (int)(b - w) >= 0) {
        a13_shown = hw_aud.arp_gaps;
        a13_shown_beat = b;
        w = b + 500u;
        ms10 = hw_aud.arp_last_u / 2400u;
        p = put_s(t, "ARP gap ");
        p = put_dec(p, hw_aud.arp_last_f);
        p = put_s(p, " fr ");
        p = put_dec(p, ms10 / 10u);
        *p++ = '.';
        *p++ = (char)('0' + ms10 % 10u);
        p = put_s(p, " ms");
        *p = 0;
        view_message(t, 0);
    }
    if ((int)(b - w) >= 0)
        w = b + 100u;
    if (!sb_wake_at || (int)(w - sb_wake_at) < 0)
        sb_wake_at = w;
}

/* REC in the panel (views.c): the log saved (not the store), and said on
 * the message line. */
void hw_a13_panel_save(void)
{
    static char t[40];
#if defined(SB_HW_AUDIO14)
    /* R (audio14): a record labelled "ARP save" holding ARP's step log (the
     * gaps, the steps, the last steps' frames and times: every record's
     * audio13 fields), counted in itself; the panel's message line says
     * whether it was saved, and under which number, or why not. */
    char *p;

    hw_aud.arp_saves++;
    a14_arp_n_saved = hw_aud.arp_n;
    report("ARP save");
    hw_aud.arp_save_err = hw_rep.last_err;
    hw_aud.arp_save_seq = hw_rep.seq - (hw_rep.last_err ? 0u : 1u);
    if (!hw_rep.last_err) {
        p = put_s(t, "ARP saved #");
        p = put_dec(p, hw_aud.arp_save_seq);
    } else {
        p = put_s(t, "ARP NOT saved, error ");
        p = put_dec(p, hw_rep.last_err);
    }
    p = put_s(p, ", ");
    p = put_dec(p, hw_aud.arp_n);
    p = put_s(p, " steps");
    *p = 0;
#else
    const char *s;
    char *p;

    report("Panel save");
    p = put_s(t, "log: ");
    for (s = hw_step_now(); *s && p < t + sizeof t - 1u; s++)
        *p++ = *s;
    *p = 0;
#endif
    view_message(t, 0);
}
#endif

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

#if defined(SB_HW_PCM16)
/* The unit's 16-bit word (HW-160): the sample in both halves, or with
 * audio9's S2 in the upper or the lower half alone, the other 0. */
static u32 pack16(s32 s)
{
    u32 u;

    /* audio10's M3: saturated at 16-bit full scale, never wrapped (before
     * audio10 nothing reached it: the tone peaks at 3276, the synth at
     * 8191 after the engine's own clamp). */
    if (s > 32767) {
        s = 32767;
        hw_aud.a10_hard++;
    } else if (s < -32768) {
        s = -32768;
        hw_aud.a10_hard++;
    }
    u = (u16)s;
#if defined(SB_HW_AUDIO9)
    if (hw_aud.a9_s2 == HW_A9_S2_UPPER)
        return u << 16;
    if (hw_aud.a9_s2 == HW_A9_S2_LOWER)
        return u;
#endif
#if defined(SB_HW_AUDIO10)
    /* N and N': the sample in one half, its negative in the other (the
     * most negative's negative clamped to the most positive). */
    if (hw_aud.a9_s2 == HW_A10_N || hw_aud.a9_s2 == HW_A10_N2) {
        u32 v = (u16)(s == -32768 ? 32767 : -s);

        return hw_aud.a9_s2 == HW_A10_N ? u << 16 | v : v << 16 | u;
    }
#endif
    return u << 16 | u;
}
#endif

#if defined(SB_HW_AUDIO9)
/* The synth's level on the unit: the engine's 24-bit full scale (audio.h)
 * >> 8 is 16-bit full scale; 2 more (-12 dB) keep it nearer the tone
 * until levels are set. */
#define A9_SYN_SHIFT 10u
static s32 syn_tmp[2u * AUDIO_FRAMES];

/* S1: the engine (fm_play, core 0 alone) fills a half. On the unit a half
 * is LEN (128) frames of one word (HW-160): two of the engine's 64-frame
 * blocks, each frame's left sample packed; in fwtest a half is LEN words
 * of its own layout (HW-44), one block of 64 frames as build A plays. */
#if defined(SB_HW_AUDIO10)
/* M2: a soft clip on the synth's sum, at 16-bit scale: straight to half
 * full scale, then K + R t / (t + R) above it (t the excess), whose slope
 * is 1 where it starts and which never reaches full scale. */
#define A10_KNEE 16384
#define A10_ROOM 16383
static s32 soft16(s32 y)
{
    u32 a = (u32)(y < 0 ? -y : y), t;

    if (a <= A10_KNEE)
        return y;
    hw_aud.a10_soft++;
    t = a - A10_KNEE;
    if (t > 262143u)
        t = 262143u;            /* R t stays within 32 bits */
    a = A10_KNEE + A10_ROOM * t / (t + A10_ROOM);
    return y < 0 ? -(s32)a : (s32)a;
}

/* The engine's sample at 16-bit scale (12 dB below full scale at the
 * engine's own full scale), soft clipped. */
static s32 syn16(s32 x)
{
#if defined(SB_TEST_A10_GAIN)
    /* The test build: 18 dB more, so 8 voices drive the soft clip. */
    return soft16(x >> (A9_SYN_SHIFT - 3u));
#else
    return soft16(x >> A9_SYN_SHIFT);
#endif
}
#endif

static void synth_fill(s32 *out, u32 frames)
{
#if defined(SB_HW_AUDIO10)
    u32 t0 = sb_now(), d, v;
#endif
#if defined(SB_HW_AUDIO12)
    /* S: the sweep's notes and algorithm for this call's blocks (the
     * unit's half is two of the engine's blocks, fwtest's one). */
#if defined(SB_HW_PCM16)
    a12_sweep_step(2u * frames);
#else
    a12_sweep_step(frames);
#endif
#endif
#if defined(SB_HW_PCM16)
    u32 h, n;

    for (h = 0; h < 2u; h++) {
        fm_block(syn_tmp, frames);
        hw_aud.a9_engine_blocks++;
        for (n = 0; n < frames; n++)
#if defined(SB_HW_AUDIO10)
            out[h * frames + n] = (s32)pack16(syn16(syn_tmp[2u * n]));
#else
            out[h * frames + n] = (s32)pack16(syn_tmp[2u * n] >> A9_SYN_SHIFT);
#endif
    }
#else
    (void)syn_tmp;
    fm_block(out, frames);
    hw_aud.a9_engine_blocks++;
#if defined(SB_HW_AUDIO10)
    /* fwtest's layout: the unit's 16-bit sample, soft clipped and
     * saturated, as fwtest's WAV takes it (<< 8, HW-44). */
    {
        u32 n;

        for (n = 0; n < frames; n++) {
            s32 y = syn16(out[2u * n]);

            if (y > 32767) {
                y = 32767;
                hw_aud.a10_hard++;
            } else if (y < -32768) {
                y = -32768;
                hw_aud.a10_hard++;
            }
            out[2u * n] = out[2u * n + 1u] = y * 256;
        }
    }
#endif
#endif
#if defined(SB_HW_AUDIO10)
    d = sb_now() - t0;
    v = sb_fm.voices[0] + sb_fm.voices[1];
    if (d > hw_aud.a10_fill_max)
        hw_aud.a10_fill_max = d;
    if (v >= 8u && d > hw_aud.a10_fill_max8)
        hw_aud.a10_fill_max8 = d;
    if (v > hw_aud.a10_voices_max)
        hw_aud.a10_voices_max = v;
#if defined(SB_HW_AUDIO11)
    /* D item 4: the longest per algorithm (sb_fm's, 1 to 10). */
    v = sb_fm.algorithm - 1u;
    if (v < HW_A11_ALGS) {
        if (d > hw_aud.fill_alg[v])
            hw_aud.fill_alg[v] = d;
        if (sb_fm.voices[0] + sb_fm.voices[1] >= 8u && d > hw_aud.fill_alg8[v])
            hw_aud.fill_alg8[v] = d;
    }
#endif
#if defined(SB_HW_AUDIO12)
    /* S: the sweep's algorithm's longest fill, with the voices then. */
    if (a12_running()) {
        v = hw_aud.as_alg - 1u;
        if (d > hw_aud.as_fill[v]) {
            hw_aud.as_fill[v] = d;
            hw_aud.as_fill_v[v] = sb_fm.voices[0] + sb_fm.voices[1];
        }
    }
#endif
#if defined(SB_HW_AUDIO13)
    /* ARP: the steps this fill's blocks played, timed by its start. */
    a13_arp_take(t0);
#endif
#endif
}

/* The first words of a half in each S2 state, for the test. */
static void a9_capture(const s32 *out)
{
    u32 i;

    for (i = 0; i < 4u; i++)
        hw_aud.a9_words[hw_aud.a9_s2 < HW_A10_FMTS ? hw_aud.a9_s2 : 0][i] = (u32)out[i];
}
#endif

/* The engine (audio.h): one block, and the probe's measures. */
static void tone_block(s32 *out, u32 frames)
{
    u32 n, b = sb_beacon.beats, t = sb_now(), want;

#if defined(SB_HW_AUDIO9)
    u32 base = frames;
#endif
#if defined(SB_HW_PCM16)
    /* On the unit a half is LEN frames of one word (HW-160): the block's
     * words are twice its frames in fwtest's layout. */
    frames *= 2u;
#endif
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

#if defined(SB_HW_AUDIO9)
    /* audio9's S1: the synth fills the half in place of the tone; past
     * HW_A9_LATE_MAX late halves since it came on, back to the tone (so
     * main, the screen and the keys keep running). In the tone, the
     * engine's queue of the panel's events is emptied each block, so the
     * synth starts with none stale. */
#if defined(SB_HW_AUDIO10)
    /* audio10's C: the link plays zeros (the engine's queue still
     * emptied, so no press waits stale). */
    if (hw_aud.holds >> HW_A10_ZERO & 1u) {
        struct input_event e;

        for (n = 0; n < (frames == base ? 2u * frames : frames); n++)
            out[n] = 0;
        while (input_read_audio(&e))
            ;
        return;
    }
#endif
    if (hw_aud.a9_synth && sb_audio.underruns - hw_aud.a9_late0 > HW_A9_LATE_MAX) {
        hw_aud.a9_synth = 0;
        hw_aud.a9_fallback = b ? b : 1u;
    }
    if (hw_aud.a9_synth) {
        synth_fill(out, base);
        a9_capture(out);
        return;
    }
    {
        struct input_event e;

        while (input_read_audio(&e))
            ;
    }
#endif
    read_master();
#if defined(SB_HW_AUDIO11)
    /* B3: MASTER's square (0 silent, 1023 the top), the change ramped
     * evenly over the half; (m^2 >> 4) * GAIN_TOP stays within 32 bits. */
    want = tone_on ? (hw_aud.master * hw_aud.master >> 4) * GAIN_TOP / (1023u * 1023u >> 4) : 0;
    {
        s32 step = ((s32)want - (s32)gain) / (s32)frames;
        u32 end = want;
#else
    want = tone_on ? GAIN_TOP * hw_aud.master / 1023u : 0;
#endif
    for (n = 0; n < frames; n++) {
        s32 s;

#if defined(SB_HW_AUDIO11)
        gain = n + 1u == frames ? end : (u32)((s32)gain + step);
#else
        if (gain + GAIN_STEP <= want)
            gain += GAIN_STEP;
        else if (gain >= want + GAIN_STEP)
            gain -= GAIN_STEP;
        else
            gain = want;
#endif
        s = (s32)((sine(phase) * (s32)gain) >> 11);
        phase += TONE_STEP;
#if defined(SB_HW_PCM16)
        /* The unit (audio8): a word a frame, 16-bit, the sample in both
         * halves (which is left isn't given, HW-160); >> 8 keeps the
         * level: -20 dB of 16-bit full scale at the top. */
        s >>= 8;
#if defined(SB_TEST_A10_CLAMP)
        /* The test build: each half's first sample the most negative, for
         * N's clamp. */
        if (!n)
            s = -32768;
#endif
        out[n] = (s32)pack16(s);
#else
        out[2 * n] = s;
        out[2 * n + 1] = s;
#endif
    }
#if defined(SB_HW_AUDIO11)
    }
#endif
    hw_aud.gain = gain;
#if defined(SB_HW_AUDIO9)
    a9_capture(out);
#endif
}

void hw_audio_start(void)
{
    hw_aud.tone_on = 1;
#if defined(SB_HW_PCM16)
    hw_aud.a8_pcm16 = 1;
#endif
#if defined(SB_HW_AUDIO10)
#if defined(SB_HW_AUDIO11)
    hw_aud.a9_s2 = HW_A10_N;    /* A: N, the only format (the owner's ruling) */
#else
    hw_aud.a9_s2 = HW_A10_U;    /* F at start-up: U (the owner's ruling) */
#endif
#endif
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

/* Frames a half: the unit's 16-bit layout plays twice fwtest's (HW-160). */
#if defined(SB_HW_PCM16)
#define A8_FRAMES (2u * AUDIO_FRAMES)
#else
#define A8_FRAMES AUDIO_FRAMES
#endif

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
        hw_aud.fps10 = div64((u64)(n1 - n0) * A8_FRAMES * 240000000ull, t1 - t0);
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

#define HW_AUD_BOX_X 150u

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
#if defined(SB_HW_AUDIO9)
    /* audio9: the tone or the synth with its late halves, and PB5 (the
     * raw bit: which level means plugged is the owner's to say). */
    p = put_s(p, hw_aud.storm ? "STORM " : hw_aud.a9_synth ? "SYN " : "TONE ");
    if (hw_aud.a9_synth || hw_aud.a9_synth_ons) {
        p = put_s(p, "L");
        p = put_dec(p, hw_aud.a9_late);
        *p++ = ' ';
    }
    p = put_s(p, "PB5 ");
    p = put_dec(p, hw_aud.pb5_now);
    *p++ = ' ';
    p = put_dec(p, hw_aud.pb5_raw_changes);
#else
    p = put_s(p, hw_aud.storm ? "STORM " : "A ");
    p = put_dec(p, sb_audio.blocks);
    *p++ = ' ';
    p = put_fps(p);
#endif
    *p = 0;
    c1_poll();
    gfx_fill(4, HW_AUD_Y, SCREEN_W - 8, 2 * FONT_H, BLACK);
    gfx_text(6, HW_AUD_Y, t, verdict_colour(), BLACK, 2);
    /* The steps' states at the right, at scale 1 (over the line's tail
     * if it is long): R (REC, bit 9) and S (SEQ) above, A and B below;
     * T taken, U undone, S stopped, R put back, - never pressed. */
#if defined(SB_HW_AUDIO9)
    p = put_s(t, hw_aud.a9_route == HW_A9_ROUTE_UP ? "rt UP" : "rt DOWN");
#if defined(SB_HW_AUDIO10)
    p = put_s(p, " ");
    p = put_s(p, fmt_label[hw_aud.a9_s2 < HW_A10_FMTS ? hw_aud.a9_s2 : 0]);
#else
    p = put_s(p, hw_aud.a9_s2 == HW_A9_S2_UPPER ? " S2 hi" : hw_aud.a9_s2 == HW_A9_S2_LOWER ? " S2 lo" : " S2 both");
#endif
    *p = 0;
    gfx_fill(HW_AUD_BOX_X - 2, HW_AUD_Y, SCREEN_W - HW_AUD_BOX_X - 2, 2 * FONT_H, BLACK);
    gfx_text(HW_AUD_BOX_X, HW_AUD_Y, t, hw_aud.a9_route == HW_A9_ROUTE_UP ? GREEN : RED, BLACK, 1);
#if defined(SB_HW_AUDIO10)
    /* MASTER's value and the ADC's raw reading. */
    p = put_s(t, "M");
    p = put_dec(p, hw_aud.m_value);
    p = put_s(p, " r");
    p = put_dec(p, sb_input.pot_raw);
#else
    p = put_x10(t, hw_aud.fps10);
#endif
    *p = 0;
    gfx_text(HW_AUD_BOX_X, HW_AUD_Y + FONT_H, t, WHITE, BLACK, 1);
    lcd_send_rows(HW_AUD_Y, 2 * FONT_H);
    lcd_wait();
    return;
#endif
    p = put_s(t, "R");
    *p++ = state_char(hw_aud.step_state);
    p = put_s(p, " S");
    *p++ = hw_aud.al_state == HW_AL_STOPPED ? 'S' : hw_aud.al_state == HW_AL_BACK ? 'R' : '-';
    p = put_s(p, " H");
    *p++ = state_char(hw_aud.h_state);
    p = put_s(p, " K");
    *p++ = state_char(hw_aud.k_state);
    p = put_s(p, " D");
    *p++ = hw_aud.d_state == HW_D_KEPT ? 'K' : hw_aud.d_state == HW_D_DONE ? 'D' :
           hw_aud.d_state == HW_D_STOPPED ? 'S' : hw_aud.d_state == HW_D_UNDONE ? 'U' : 'h';
    *p = 0;
    gfx_fill(HW_AUD_BOX_X - 2, HW_AUD_Y, SCREEN_W - HW_AUD_BOX_X - 2, 2 * FONT_H, BLACK);
    gfx_text(HW_AUD_BOX_X, HW_AUD_Y, t, WHITE, BLACK, 1);
    p = put_s(t, "A");
    *p++ = state_char(hw_aud.a_state);
    p = put_s(p, " B");
    *p++ = state_char(hw_aud.b_state);
    p = put_s(p, " I");
    *p++ = state_char(hw_aud.i_state);
    p = put_s(p, " J");
    *p++ = hw_aud.j_state == HW_J_MOVED ? 'M' : hw_aud.j_state == HW_J_DONE ? 'D' :
           hw_aud.j_state == HW_J_ABORTED ? 'X' : hw_aud.j_state == HW_J_UNDONE ? 'U' : '-';
    p = put_s(p, " L");
    *p++ = hw_aud.l_state == HW_L_KEPT ? (char)('0' + hw_aud.l_which) : hw_aud.l_state == HW_L_UNDONE ? 'U' :
           hw_aud.l_state == HW_L_DONE ? 'D' : hw_aud.l_state == HW_L_STOPPED ? 'X' : '-';
    *p = 0;
    gfx_text(HW_AUD_BOX_X, HW_AUD_Y + FONT_H, t, WHITE, BLACK, 1);
    lcd_send_rows(HW_AUD_Y, 2 * FONT_H);
    lcd_wait();
}

/* --- The page ------------------------------------------------------------- */

#define PAGE_REGS_Y 56u

static void page_top(void)
{
    char t[80], *p;

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
    char t[80], *p;
    u32 i, n = view ? HW_AUD_MORE : HW_AUD_REGS, y = PAGE_REGS_Y;

    gfx_fill(0, PAGE_REGS_Y, SCREEN_W, SCREEN_H - PAGE_REGS_Y, BLACK);
    p = put_s(t, view ? "2/8 reg  call     tone     " : "1/8 reg  call     tone     ");
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
    char t[80], *p;
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
    p = put_s(t, "3/8 moved ");
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
    static const char title[HW_K_N][16] = { "REC  bit 9 ", "SEQ  stop  ", "ARP  A     ", "SAVE B bit8 ",
                                            "ENV  H     ", "LFO  I     ", "GLO  K     ", "OCT+ J     " };
    char t[80], *p;
    u32 k, y = PAGE_REGS_Y, now[HW_SNAP];

    gfx_fill(0, PAGE_REGS_Y, SCREEN_W, SCREEN_H - PAGE_REGS_Y, BLACK);
    gfx_text(6, y, "4/8 steps: before (b), after (a), now (n)", YELLOW, BLACK, 1);
    y += FONT_H;
    gfx_text(6, y, "  CON0     CLK2     irq core1", DIM, BLACK, 1);
    /* The first six steps; K's and J's are on their own view. */
    for (k = 0; k <= HW_K_I; k++) {
        u32 st = k == HW_K_REC ? hw_aud.step_state : k == HW_K_A ? hw_aud.a_state : k == HW_K_B ? hw_aud.b_state :
                 k == HW_K_H ? hw_aud.h_state : k == HW_K_I ? hw_aud.i_state : 0;
        u32 n = k == HW_K_REC ? hw_aud.steps : k == HW_K_SEQ ? hw_aud.al_keys : k == HW_K_A ? hw_aud.a_keys :
                k == HW_K_B ? hw_aud.b_keys : k == HW_K_H ? hw_aud.h_keys : hw_aud.i_keys;

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
/* The H and I view: the keys; H's CLK_CON1 and JL_GPCNT->CON sequences,
 * its counts (with the bus count per 1000 gate cycles, 7500 expected, and
 * the audio clock in kHz) and CLK_CON2 at each; I's ALNK1 registers
 * before, after and put back, CLK_CON2's sequence, the last poll, and
 * ALNK1 now. */
static void row_at(u32 *y, const char *t, u32 colour)
{
    gfx_text(6, *y, t, colour, BLACK, 1);
    *y += FONT_H;
}

static char *put_seq(char *p, const char *label, u32 a, u32 b, u32 c, u32 d)
{
    p = put_s(p, label);
    p = put_hex(p, a, 8);
    *p++ = '>';
    p = put_hex(p, b, 8);
    *p++ = '>';
    p = put_hex(p, c, 8);
    *p++ = '>';
    return put_hex(p, d, 8);
}

static char *put_count(char *p, const char *label, const u32 *num, u32 to, u32 clk2, int bus)
{
    p = put_s(p, label);
    p = put_dec(p, num[0]);
    *p++ = ' ';
    p = put_dec(p, num[1]);
    if (bus) {
        p = put_s(p, " x");
        p = put_dec(p, div64((u64)num[1] * 1000u, HW_H_GATE));
    } else {
        *p++ = ' ';
        p = put_dec(p, div64((u64)num[1] * 24000u, HW_H_GATE));
        p = put_s(p, "kHz");
    }
    p = put_s(p, " to");
    p = put_dec(p, to);
    p = put_s(p, " C2 ");
    return put_hex(p, clk2, 8);
}

static const char *state_word(u32 st)
{
    return st == HW_STEP_TAKEN ? "taken" : st == HW_STEP_UNDONE ? "undone" : "not taken";
}

static void page_hi(void)
{
    char t[80], *p;
    u32 y = PAGE_REGS_Y, w[4], i;

    gfx_fill(0, PAGE_REGS_Y, SCREEN_W, SCREEN_H - PAGE_REGS_Y, BLACK);
    row_at(&y, "5/8 ENV=H FX=H again LFO=I SEL=I bit10", YELLOW);
    p = put_s(t, "H ");
    p = put_s(p, state_word(hw_aud.h_state));
    p = put_s(p, ", presses ");
    p = put_dec(p, hw_aud.h_keys);
    p = put_s(p, ", measured ");
    p = put_dec(p, hw_aud.h_measures);
    p = put_s(p, ", gate ");
    p = put_dec(p, HW_H_GATE);
    *p = 0;
    row_at(&y, t, hw_aud.h_state == HW_STEP_TAKEN ? YELLOW : WHITE);
    p = put_seq(t, "C1 ", hw_aud.h_clk1_before, hw_aud.h_clk1_check, hw_aud.h_clk1_audio, hw_aud.h_clk1_back);
    *p = 0;
    row_at(&y, t, WHITE);
    p = put_seq(t, "GP ", hw_aud.h_gp_before, hw_aud.h_gp_check, hw_aud.h_gp_audio, hw_aud.h_gp_back);
    *p = 0;
    row_at(&y, t, WHITE);
    p = put_count(t, "bus ", hw_aud.h_check, hw_aud.h_check_to, hw_aud.h_check_clk2, 1);
    *p = 0;
    row_at(&y, t, GREEN);
    p = put_count(t, "aud ", hw_aud.h_audio, hw_aud.h_audio_to, hw_aud.h_audio_clk2, 0);
    *p = 0;
    row_at(&y, t, GREEN);
    y += FONT_H;
    p = put_s(t, "I ");
    p = put_s(p, state_word(hw_aud.i_state));
    p = put_s(p, ", presses ");
    p = put_dec(p, hw_aud.i_keys);
    p = put_s(p, hw_aud.i_bit10 ? ", bit 10 set" : "");
    *p = 0;
    row_at(&y, t, hw_aud.i_state == HW_STEP_TAKEN ? YELLOW : WHITE);
    p = put_seq(t, "b ", hw_aud.i_con_before[0], hw_aud.i_con_before[1], hw_aud.i_con_before[2],
                hw_aud.i_con_before[3]);
    *p = 0;
    row_at(&y, t, WHITE);
    p = put_seq(t, "a ", hw_aud.i_con_after[0], hw_aud.i_con_after[1], hw_aud.i_con_after[2],
                hw_aud.i_con_after[3]);
    *p = 0;
    row_at(&y, t, WHITE);
    p = put_seq(t, "C2 ", hw_aud.i_clk_before, hw_aud.i_clk_set, hw_aud.i_clk_set10, hw_aud.i_clk_back);
    *p = 0;
    row_at(&y, t, WHITE);
    p = put_s(t, "back CON0 ");
    p = put_hex(p, hw_aud.i_con_back, 8);
    *p = 0;
    row_at(&y, t, WHITE);
    p = put_s(t, "b15 ");
    p = put_dec(p, hw_aud.i_flips);
    p = put_s(p, " pend ");
    p = put_dec(p, hw_aud.i_pend);
    p = put_s(p, " in ");
    p = put_dec(p, hw_aud.i_span);
    p = put_s(p, " ms: h/s ");
    p = put_dec(p, hw_aud.i_hps10 / 10);
    *p++ = '.';
    p = put_dec(p, hw_aud.i_hps10 % 10);
    *p = 0;
    row_at(&y, t, hw_aud.i_flips ? GREEN : RED);
    i_read(w);
    p = put_seq(t, "n ", w[0], w[1], w[2], w[3]);
    *p = 0;
    row_at(&y, t, GREEN);
    p = put_s(t, "core1 ");
    p = put_dec(p, hw_core1_count);
    p = put_s(p, " CLK_CON2 ");
    p = put_hex(p, JL_CLOCK->CLK_CON2, 8);
    *p = 0;
    row_at(&y, t, WHITE);
    (void)i;
    lcd_send_rows(PAGE_REGS_Y, SCREEN_H - PAGE_REGS_Y);
    lcd_wait();
}

/* The K and J view: the keys; each of K's measurements (CLK_CON1 as read
 * back, both counts, the second in kHz of the 24 MHz gate); J's state,
 * its last try (register and bit, before, written, read back, put back;
 * bit 15's changes, pending flags and interrupts over its wait), the
 * tries whose bit didn't hold, and CLK_CON2 when the sweep began. */
static const char k_label[HW_KM_N][6] = { "in3", "in1", "in5", "in6", "in7", "480", "5 d1", "5 d2", "5 d3", "5 dx" };

static const char *j_word(u32 st)
{
    return st == HW_J_DONE ? "done, none moved" : st == HW_J_MOVED ? "MOVED, bit left set" :
           st == HW_J_ABORTED ? "aborted" : st == HW_J_UNDONE ? "undone" : "not run";
}

static void page_kj(void)
{
    char t[80], *p;
    u32 y = PAGE_REGS_Y, i;

    gfx_fill(0, PAGE_REGS_Y, SCREEN_W, SCREEN_H - PAGE_REGS_Y, BLACK);
    row_at(&y, "6/8 GLO=K OCT+=J (again: undo, abort)", YELLOW);
    p = put_s(t, "K ");
    p = put_s(p, state_word(hw_aud.k_state));
    p = put_s(p, ", presses ");
    p = put_dec(p, hw_aud.k_keys);
    p = put_s(p, ", C1 ");
    p = put_hex(p, hw_aud.k_clk1_before, 8);
    *p = 0;
    row_at(&y, t, hw_aud.k_state == HW_STEP_TAKEN ? YELLOW : WHITE);
    for (i = 0; i < HW_KM_N; i++) {
        const u32 *m = hw_aud.k_m[i];

        p = put_s(t, k_label[i]);
        while (p < t + 5)
            *p++ = ' ';
        p = put_hex(p, m[0], 8);
        *p++ = ' ';
        p = put_dec(p, m[2]);
        *p++ = ' ';
        p = put_dec(p, m[3]);
        *p++ = ' ';
        p = put_dec(p, div64((u64)m[3] * 24000u, HW_H_GATE));
        p = put_s(p, "k");
        *p = 0;
        row_at(&y, t, i == 2 ? GREEN : WHITE);
    }
    p = put_s(t, "J ");
    p = put_s(p, j_word(hw_aud.j_state));
    p = put_s(p, ", sweeps ");
    p = put_dec(p, hw_aud.j_sweeps);
    p = put_s(p, ", tries ");
    p = put_dec(p, hw_aud.j_tries);
    *p = 0;
    row_at(&y, t, hw_aud.j_state == HW_J_MOVED ? GREEN : WHITE);
    p = put_s(t, "last ");
    p = put_try(p, hw_aud.j_reg, hw_aud.j_bit);
    p = put_s(p, " ");
    p = put_hex(p, hw_aud.j_before, 4);
    *p++ = '>';
    p = put_hex(p, hw_aud.j_written, 4);
    p = put_s(p, " rb ");
    p = put_hex(p, hw_aud.j_read, 4);
    p = put_s(p, " bk ");
    p = put_hex(p, hw_aud.j_back, 4);
    *p = 0;
    row_at(&y, t, WHITE);
    p = put_s(t, "b15 ");
    p = put_dec(p, hw_aud.j_flips);
    p = put_s(p, " pend ");
    p = put_dec(p, hw_aud.j_pend);
    p = put_s(p, " irq ");
    p = put_dec(p, hw_aud.j_irq);
    p = put_s(p, " C2 ");
    p = put_hex(p, hw_aud.j_clk2_sweep, 8);
    *p = 0;
    row_at(&y, t, hw_aud.j_flips || hw_aud.j_irq ? GREEN : WHITE);
    p = put_s(t, "didn't hold: ");
    p = put_hex(p, hw_aud.j_nohold, 6);
    p = put_s(p, " now CON1 ");
    p = put_hex(p, JL_ALNK0->CON1, 4);
    p = put_s(p, " CON3 ");
    p = put_hex(p, JL_ALNK0->CON3, 2);
    *p = 0;
    row_at(&y, t, WHITE);
    lcd_send_rows(PAGE_REGS_Y, SCREEN_H - PAGE_REGS_Y);
    lcd_wait();
}

/* The D view: the sweep's state, the try in progress or the one it
 * stopped at (the bit, CON5 read, written, read back, put back; the watch's
 * counts; the matrix: idle rows and cells before, with the bit set and
 * after the undo; the checks), port A's registers before, with the bit
 * set and after, and core 1's count. */
static const char d_state_word[5][14] = { "not run", "done, no stop", "STOPPED", "BIT KEPT", "undone" };
static const char pa_name[8][5] = { "OUT", "IN", "DIR", "DIE", "PU", "PD", "HD0", "HD" };

static char *put_check(char *p, u32 bad)
{
    if (!bad)
        return put_s(p, "ok");
    p = put_s(p, "BAD");
    p = put_s(p, bad & 1u ? " rows" : "");
    p = put_s(p, bad & 2u ? " cells" : "");
    p = put_s(p, bad & 4u ? " portA" : "");
    p = put_s(p, bad & 8u ? " CON5" : "");
    p = put_s(p, bad & 16u ? " map" : "");
    return put_s(p, bad & 32u ? " PA moved" : "");
}

static void page_d(void)
{
    char t[80], *p;
    u32 y = PAGE_REGS_Y, i;

    gfx_fill(0, PAGE_REGS_Y, SCREEN_W, SCREEN_H - PAGE_REGS_Y, BLACK);
    row_at(&y, "7/8 D HELD (OCT-), not in this order", YELLOW);
    p = put_s(t, "D ");
    p = put_s(p, d_state_word[hw_aud.d_state < 5u ? hw_aud.d_state : 0]);
    p = put_s(p, ", sweeps ");
    p = put_dec(p, hw_aud.d_sweeps);
    p = put_s(p, ", tries ");
    p = put_dec(p, hw_aud.d_tries);
    *p = 0;
    row_at(&y, t, hw_aud.d_state == HW_D_KEPT ? GREEN : hw_aud.d_state == HW_D_STOPPED ? YELLOW : WHITE);
    p = put_s(t, "stop: ");
    p = put_s(p, d_stop_word(hw_aud.d_stop));
    p = put_s(p, " C2 ");
    p = put_hex(p, hw_aud.d_clk2, 8);
    *p = 0;
    row_at(&y, t, WHITE);
    p = put_bit(t, "b", hw_aud.d_bit);
    p = put_s(p, " C5 ");
    p = put_hex(p, hw_aud.d_con5_before, 8);
    *p++ = '>';
    p = put_hex(p, hw_aud.d_con5_written, 8);
    p = put_s(p, " rb ");
    p = put_hex(p, hw_aud.d_con5_read, 8);
    *p = 0;
    row_at(&y, t, WHITE);
    p = put_s(t, "back ");
    p = put_hex(p, hw_aud.d_con5_back, 8);
    p = put_s(p, " b15 ");
    p = put_dec(p, hw_aud.d_flips);
    p = put_s(p, " pend ");
    p = put_dec(p, hw_aud.d_pend);
    p = put_s(p, " irq ");
    p = put_dec(p, hw_aud.d_irq);
    *p = 0;
    row_at(&y, t, hw_aud.d_flips || hw_aud.d_irq ? GREEN : WHITE);
    p = put_s(t, "rows ");
    p = put_hex(p, hw_aud.d_idle_base, 2);
    *p++ = '>';
    p = put_hex(p, hw_aud.d_idle_set, 2);
    *p++ = '>';
    p = put_hex(p, hw_aud.d_idle_after, 2);
    p = put_s(p, " set ");
    p = put_check(p, hw_aud.d_check_set);
    p = put_s(p, " undo ");
    p = put_check(p, hw_aud.d_check_after);
    *p = 0;
    row_at(&y, t, hw_aud.d_check_set || hw_aud.d_check_after ? RED : WHITE);
    for (i = 0; i < 3; i++) {
        const u32 *m = i == 0 ? hw_aud.d_map_base : i == 1 ? hw_aud.d_map_set : hw_aud.d_map_after;

        p = put_s(t, i == 0 ? "cells " : i == 1 ? "  set " : "  undo ");
        while (p < t + 7)
            *p++ = ' ';
        p = put_hex(p, m[2], 8);
        p = put_hex(p, m[1], 8);
        p = put_hex(p, m[0], 8);
        *p = 0;
        row_at(&y, t, WHITE);
    }
    row_at(&y, "PA   before   bit set  after", DIM);
    for (i = 0; i < 8; i++) {
        p = put_s(t, pa_name[i]);
        while (p < t + 4)
            *p++ = ' ';
        p = put_hex(p, hw_aud.d_pa_before[i], 8);
        *p++ = ' ';
        p = put_hex(p, hw_aud.d_pa_set[i], 8);
        *p++ = ' ';
        p = put_hex(p, hw_aud.d_pa_after[i], 8);
        *p = 0;
        row_at(&y, t, (i >= 2u && i <= 5u) && (hw_aud.d_pa_set[i] != hw_aud.d_pa_before[i] ||
                       hw_aud.d_pa_after[i] != hw_aud.d_pa_before[i]) ? RED : WHITE);
    }
    p = put_s(t, "IN watch ");
    p = put_hex(p, hw_aud.d_in_start, 8);
    *p++ = '>';
    p = put_hex(p, hw_aud.d_in_end, 8);
    p = put_s(p, " c1 ");
    p = put_dec(p, hw_core1_count);
    *p = 0;
    row_at(&y, t, WHITE);
    lcd_send_rows(PAGE_REGS_Y, SCREEN_H - PAGE_REGS_Y);
    lcd_wait();
}

/* The L view: the set-up's state, CON0 to CON3 and LEN before, each write
 * and its read-back, the watch's counts, the halves and frames a second by
 * each LEN reading beside the expected, the checks, what was put back,
 * port A before, with the set-up in place and after, CLK_CON1, CLK_CON2,
 * core 1's count. */
static const char l_state_word[5][16] = { "not run", "KEPT, running", "undone by key", "put back", "STOPPED" };

static char *put_x10(char *p, u32 v)
{
    p = put_dec(p, v / 10u);
    *p++ = '.';
    return put_dec(p, v % 10u);
}

static void page_l(void)
{
    char t[80], *p;
    u32 y = PAGE_REGS_Y, i;

    gfx_fill(0, PAGE_REGS_Y, SCREEN_W, SCREEN_H - PAGE_REGS_Y, BLACK);
    row_at(&y, "8/8 KEY1=L1 KEY2=L2 (again: undo)", YELLOW);
    p = put_bit(t, "L", hw_aud.l_which);
    *p++ = ' ';
    p = put_s(p, l_state_word[hw_aud.l_state < 5u ? hw_aud.l_state : 0]);
    p = put_s(p, ", runs ");
    p = put_dec(p, hw_aud.l_presses);
    p = put_s(p, " C2 ");
    p = put_hex(p, hw_aud.l_clk2, 8);
    *p = 0;
    row_at(&y, t, hw_aud.l_state == HW_L_KEPT ? GREEN : hw_aud.l_state == HW_L_STOPPED ? RED : WHITE);
    p = put_s(t, "was ");
    for (i = 0; i < 4; i++) {
        p = put_hex(p, hw_aud.l_before[i], i < 2u ? 4 : 2);
        *p++ = ' ';
    }
    p = put_s(p, "LEN ");
    p = put_hex(p, hw_aud.l_len_read, 4);
    *p = 0;
    row_at(&y, t, WHITE);
    p = put_s(t, "C0 ");
    p = put_hex(p, hw_aud.l_w[0], 4);
    *p++ = '>';
    p = put_hex(p, hw_aud.l_rb[0], 4);
    p = put_s(p, " C3 ");
    p = put_hex(p, hw_aud.l_w[1], 2);
    *p++ = '>';
    p = put_hex(p, hw_aud.l_rb[1], 2);
    p = put_s(p, " C1 ");
    p = put_hex(p, hw_aud.l_w[2], 4);
    *p++ = '>';
    p = put_hex(p, hw_aud.l_rb[2], 4);
    *p = 0;
    row_at(&y, t, WHITE);
    p = put_s(t, "run C0 ");
    p = put_hex(p, hw_aud.l_w[3], 4);
    *p++ = '>';
    p = put_hex(p, hw_aud.l_rb[3], 4);
    p = put_s(p, " back ");
    p = put_hex(p, hw_aud.l_back[0], 4);
    *p++ = ' ';
    p = put_hex(p, hw_aud.l_back[1], 4);
    *p++ = ' ';
    p = put_hex(p, hw_aud.l_back[2], 2);
    *p = 0;
    row_at(&y, t, WHITE);
    p = put_s(t, "b15 ");
    p = put_dec(p, hw_aud.l_flips);
    p = put_s(p, " pend ");
    p = put_dec(p, hw_aud.l_pend);
    p = put_s(p, " irq ");
    p = put_dec(p, hw_aud.l_irq);
    p = put_s(p, " h/s ");
    p = put_x10(p, hw_aud.l_hps10);
    *p = 0;
    row_at(&y, t, hw_aud.l_flips || hw_aud.l_irq ? GREEN : WHITE);
    p = put_s(t, "f/s a ");
    p = put_x10(p, hw_aud.l_fps10_a);
    p = put_s(p, " b ");
    p = put_x10(p, hw_aud.l_fps10_b);
    *p = 0;
    row_at(&y, t, WHITE);
    p = put_s(t, "want ");
    p = put_x10(p, hw_aud.l_exp_fps10);
    p = put_s(p, " h/s a ");
    p = put_x10(p, hw_aud.l_exp_hps10_a);
    p = put_s(p, " b ");
    p = put_x10(p, hw_aud.l_exp_hps10_b);
    *p = 0;
    row_at(&y, t, DIM);
    p = put_s(t, "check set ");
    p = put_check(p, hw_aud.l_check_set);
    p = put_s(p, " after ");
    p = put_check(p, hw_aud.l_check_after);
    *p = 0;
    row_at(&y, t, hw_aud.l_check_set || hw_aud.l_check_after ? RED : WHITE);
    row_at(&y, "PA   before   set up   after", DIM);
    for (i = 0; i < 8; i++) {
        p = put_s(t, pa_name[i]);
        while (p < t + 4)
            *p++ = ' ';
        p = put_hex(p, hw_aud.l_pa_before[i], 8);
        *p++ = ' ';
        p = put_hex(p, hw_aud.l_pa_set[i], 8);
        *p++ = ' ';
        p = put_hex(p, hw_aud.l_pa_after[i], 8);
        *p = 0;
        row_at(&y, t, (i >= 2u && i <= 5u) && (hw_aud.l_pa_set[i] != hw_aud.l_pa_before[i] ||
                       (hw_aud.l_pa_after[i] && hw_aud.l_pa_after[i] != hw_aud.l_pa_before[i])) ? RED : WHITE);
    }
    p = put_s(t, "C1 ");
    p = put_hex(p, hw_aud.l_clk1, 8);
    p = put_s(p, " c1 ");
    p = put_dec(p, hw_core1_count);
    *p = 0;
    row_at(&y, t, WHITE);
    lcd_send_rows(PAGE_REGS_Y, SCREEN_H - PAGE_REGS_Y);
    lcd_wait();
}

#if defined(SB_HW_AUDIO8)
static const char *const s1_word[5] = { "not run", "KEPT, port C moves", "port C still", "STOPPED", "undone" };
static const char *const sw_word[5] = { "not run", "done, port C still", "KEPT", "STOPPED", "undone" };
static const char *const stop_word[6] = { "-", "port C moved", "PORT A MOVED", "CHECK BAD", "AFTER BAD", "key held" };

static char *put_counts(char *p, const char *label, const u32 *c)
{
    u32 i, a = 0;

    p = put_s(p, label);
    p = put_s(p, " C");
    for (i = 0; i < 4; i++) {
        *p++ = ' ';
        p = put_dec(p, c[i]);
    }
    for (i = 4; i < HW_A8_PINS; i++)
        a += c[i];
    p = put_s(p, " A ");
    return put_dec(p, a);
}

static void page_a8(void)
{
    char t[80], *p;
    u32 y = PAGE_REGS_Y, i;

    gfx_fill(0, PAGE_REGS_Y, SCREEN_W, SCREEN_H - PAGE_REGS_Y, BLACK);
    row_at(&y, "9/9 K3 R2  K4 step 1  K5 sweep  K6 sense", YELLOW);
    p = put_s(t, "L2 ");
    p = put_s(p, l_state_word[hw_aud.l_state < 5u ? hw_aud.l_state : 0]);
    p = put_s(p, hw_aud.a8_off == HW_A8_OFF_CHECK ? ", OFF: check" : hw_aud.l_state != HW_L_KEPT ? ", audio8 OFF" : "");
    *p = 0;
    row_at(&y, t, hw_aud.l_state == HW_L_KEPT && hw_aud.a8_off != HW_A8_OFF_CHECK ? GREEN : RED);
    p = put_s(t, "tone ");
    p = put_s(p, hw_aud.a8_pcm16 ? "16-bit" : "fwtest's");
    p = put_s(p, " f/s ");
    p = put_x10(p, hw_aud.fps10);
    p = put_s(p, " REC b15 ");
    p = put_dec(p, hw_aud.r9_flips);
    *p = 0;
    row_at(&y, t, WHITE);
    p = put_s(t, "R2 ");
    p = put_s(p, hw_aud.r2_state == HW_A8_R2_SET ? "set" : hw_aud.r2_state ? "undone" : "-");
    p = put_s(p, " chk ");
    p = put_dec(p, hw_aud.r2_check);
    p = put_s(p, " PC ");
    for (i = 0; i < 4; i++) {
        p = put_hex(p, hw_aud.r2_state == HW_A8_R2_SET ? hw_aud.r2_pc_set[i == 1u ? 3u : i == 3u ? 4u : i] :
                    hw_aud.r2_pc_after[i == 1u ? 3u : i == 3u ? 4u : i], 4);
        *p++ = ' ';
    }
    *p = 0;
    row_at(&y, t, hw_aud.r2_check ? RED : WHITE);
    row_at(&y, "   (OUT DIE DIR PU)  counts: PC0 1 2 6, PA", DIM);
    p = put_counts(t, "ctl", hw_aud.ctl);
    *p = 0;
    row_at(&y, t, a8_pc_moved(hw_aud.ctl) || a8_pa_moved(hw_aud.ctl) ? YELLOW : WHITE);
    p = put_counts(t, "1a ", hw_aud.s1a);
    *p = 0;
    row_at(&y, t, WHITE);
    p = put_s(t, "1: ");
    p = put_s(p, s1_word[hw_aud.s1_state < 5u ? hw_aud.s1_state : 0]);
    *p = 0;
    row_at(&y, t, hw_aud.s1_state == HW_A8_S1_KEPT ? GREEN : hw_aud.s1_state == HW_A8_S1_STOPPED ? RED : WHITE);
    p = put_s(t, "sweep: ");
    p = put_s(p, sw_word[hw_aud.sw_state < 5u ? hw_aud.sw_state : 0]);
    p = put_s(p, ", tries ");
    p = put_dec(p, hw_aud.sw_tries);
    *p = 0;
    row_at(&y, t, hw_aud.sw_state == HW_A8_SW_KEPT ? GREEN : hw_aud.sw_state == HW_A8_SW_STOPPED ? RED : WHITE);
    p = put_s(t, hw_aud.rt_kind == 2u ? "last: SW bit " : hw_aud.rt_kind ? "last: 1(b)" : "last: -");
    if (hw_aud.rt_kind == 2u)
        p = put_dec(p, hw_aud.rt_bit);
    p = put_s(p, " ");
    p = put_s(p, stop_word[hw_aud.rt_stop < 6u ? hw_aud.rt_stop : 0]);
    p = put_s(p, " C5 ");
    p = put_hex(p, hw_aud.rt_con5[2], 8);
    *p = 0;
    row_at(&y, t, hw_aud.rt_stop >= HW_A8_STOP_PA && hw_aud.rt_stop <= HW_A8_STOP_AFTER ? RED : WHITE);
    p = put_counts(t, "t1 ", hw_aud.rt_c1);
    *p = 0;
    row_at(&y, t, a8_pc_moved(hw_aud.rt_c1) ? GREEN : WHITE);
    p = put_counts(t, "t2 ", hw_aud.rt_c2);
    *p = 0;
    row_at(&y, t, a8_pc_moved(hw_aud.rt_c2) ? GREEN : WHITE);
    p = put_s(t, "chk ");
    p = put_check(p, hw_aud.rt_check_set);
    p = put_s(p, " after ");
    p = put_check(p, hw_aud.rt_check_after);
    *p = 0;
    row_at(&y, t, hw_aud.rt_check_set || hw_aud.rt_check_after ? RED : WHITE);
    p = put_s(t, "sense ");
    p = put_s(p, hw_aud.se_state ? "done" : "-");
    p = put_s(p, " reads ");
    p = put_dec(p, hw_aud.se_ms);
    p = put_s(p, " ev ");
    p = put_dec(p, hw_aud.se_ev_n);
    p = put_s(p, " lost ");
    p = put_dec(p, hw_aud.se_ev_lost);
    *p = 0;
    row_at(&y, t, WHITE);
    for (i = 0; i < 8u; i += 4u) {
        u32 j;

        p = t;
        for (j = i; j < i + 4u; j++) {
            *p++ = (char)('A' + j);
            p = put_hex(p, hw_aud.se_changed[j], 4);
            *p++ = j & 1u ? ' ' : '/';
            p = put_hex(p, hw_aud.se_die[j] & 0xFFFFu, 4);
            *p++ = ' ';
        }
        *p = 0;
        row_at(&y, t, WHITE);
    }
    row_at(&y, "  (port: bits changed / DIE)", DIM);
#if defined(SB_HW_AUDIO9)
    p = put_s(t, "route ");
    p = put_s(p, hw_aud.a9_route == HW_A9_ROUTE_UP ? "UP" : hw_aud.a9_route == HW_A9_ROUTE_DOWN ? "down" :
              hw_aud.a9_route == HW_A9_ROUTE_UNDONE ? "UNDONE" : hw_aud.a9_route == HW_A9_ROUTE_NOL2 ? "no L2" : "-");
    p = put_s(p, " ups ");
    p = put_dec(p, hw_aud.a9_ups);
    p = put_s(p, " downs ");
    p = put_dec(p, hw_aud.a9_downs);
    p = put_s(p, " S2 ");
    p = put_s(p, hw_aud.a9_s2 == HW_A9_S2_UPPER ? "upper" : hw_aud.a9_s2 == HW_A9_S2_LOWER ? "lower" : "both");
    *p = 0;
    row_at(&y, t, hw_aud.a9_route == HW_A9_ROUTE_UP ? GREEN : RED);
    p = put_s(t, hw_aud.a9_synth ? "SYNTH late " : "tone, synth late ");
    p = put_dec(p, hw_aud.a9_late);
    p = put_s(p, " fill max us ");
    p = put_dec(p, hw_aud.a9_fill_max / 24u);
    *p = 0;
    row_at(&y, t, hw_aud.a9_late || hw_aud.a9_fallback ? RED : WHITE);
    p = put_s(t, "PB5 ");
    p = put_dec(p, hw_aud.pb5_now);
    p = put_s(p, " changes ");
    p = put_dec(p, hw_aud.pb5_raw_changes);
    p = put_s(p, " DAA7 ");
    p = put_hex(p, hw_aud.daa7_last, 8);
    *p = 0;
    row_at(&y, t, WHITE);
#endif
    lcd_send_rows(PAGE_REGS_Y, SCREEN_H - PAGE_REGS_Y);
    lcd_wait();
}
#endif

static void draw_view(u32 v)
{
    if (v < 2)
        page_regs(v);
    else if (v == 2)
        page_core1();
    else if (v == 3)
        page_steps();
    else if (v == 4)
        page_hi();
    else if (v == 5)
        page_kj();
    else if (v == 6)
        page_d();
#if defined(SB_HW_AUDIO8)
    else if (v == 8)
        page_a8();
#endif
    else
        page_l();
}

/* audio8: its key pages write no "page" record (the sweep alone takes
 * about 66 of the ring's 96). */
static u32 page_quiet;

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
    if (!page_quiet)
        report("page");
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
            hw_guide_tick();
        }
    }
}

/* The first page: the first four views; HOME: all eight (audio8: and
 * its own, first). */
void hw_audio_page(void)
{
#if defined(SB_HW_AUDIO8)
    static const u8 all[9] = { 8, 0, 1, 2, 3, 4, 5, 6, 7 };

    page_views(all, hw_aud.regs_read ? 9 : 4);
#else
    static const u8 all[8] = { 0, 1, 2, 3, 4, 5, 6, 7 };

    page_views(all, hw_aud.regs_read ? 8 : 4);
#endif
}

#if defined(SB_HW_AUDIO8)
/* After audio8's keys: its view alone. */
void hw_audio_keypage_a8(void)
{
    static const u8 keys[1] = { 8 };

    page_quiet = 1;
    page_views(keys, 1);
    page_quiet = 0;
}
#endif

/* After L's keys: the L view, then core 1's. */
void hw_audio_keypage_l(void)
{
    static const u8 keys[2] = { 7, 2 };

    page_views(keys, 2);
}

/* After D's key: the D view, then core 1's. */
void hw_audio_keypage_d(void)
{
    static const u8 keys[2] = { 6, 2 };

    page_views(keys, 2);
}

/* After K's or J's key: the K and J view, then core 1's. */
void hw_audio_keypage_kj(void)
{
    static const u8 keys[2] = { 5, 2 };

    page_views(keys, 2);
}

/* After H's or I's key: the H and I view, then core 1's. */
void hw_audio_keypage_hi(void)
{
    static const u8 keys[2] = { 4, 2 };

    page_views(keys, 2);
}

/* After a step's key: the steps view, then core 1's. */
void hw_audio_keypage(void)
{
    static const u8 keys[2] = { 3, 2 };

    page_views(keys, 2);
}

/* --- The next key (the owner's request after audio5) ------------------- */

/* The build's suggested order, the one table: each entry a key and what
 * its press does. A press of the entry's key moves on to the next; any
 * other key leaves it. This is audio7's order (the spec side's prompt: L1,
 * bit 9, L2, bit 9 again, L2), then a save; D is held and out of it.
 * While a set-up is kept, the next key is its own, to put it back, ahead
 * of the table; likewise OCT- while D has a bit kept. */
struct guide_step {
    u8 key;
    char what[13];
};
#if defined(SB_HW_AUDIO13)
/* audio13's order (HOME held at power-on; on the battery, no cable, state
 * a): U2-B with U2-C off, SAVE at each change of the cable (b to e); U2-C
 * on (state a again), U2-B again; a save. */
static const struct guide_step guide[] = {
    { INPUT_SAVE, "b charger" }, { INPUT_SAVE, "c computer" },
    { INPUT_SAVE, "d asleep" }, { INPUT_SAVE, "e cable out" },
    { INPUT_OCT_UP, "U2-C on, a" },
    { INPUT_SAVE, "b charger" }, { INPUT_SAVE, "c computer" },
    { INPUT_SAVE, "d asleep" }, { INPUT_SAVE, "e cable out" },
    { INPUT_EDIT, "save" },
};
#elif defined(SB_HW_AUDIO12)
/* audio12's order: the sweep (hands off until "SWEEP DONE"), a save; a
 * second sweep stopped with LFO during a chord, a save; then SEL, the
 * instrument's start (the panel: the test screen is gone until power-off). */
static const struct guide_step guide[] = {
    { INPUT_LFO, "sweep" },
    { INPUT_EDIT, "save" },
    { INPUT_LFO, "sweep again" },
    { INPUT_LFO, "stop it" },
    { INPUT_EDIT, "save" },
    { INPUT_SEL, "instrument" },
};
#elif defined(SB_HW_AUDIO11)
/* audio11's order: in N with MASTER still, about ten seconds with nothing
 * held, then each hold alone (the scan hold ends by itself), the zeros;
 * the old SARADC set-up and back (MASTER turned end to end in each); the
 * synth (an 8-key chord in each algorithm); a save. */
static const struct guide_step guide[] = {
    { INPUT_HOME, "LED hold" }, { INPUT_HOME, "LED back" },
    { INPUT_ENV, "screen hold" }, { INPUT_ENV, "screen back" },
    { INPUT_GLO, "log hold" }, { INPUT_GLO, "log back" },
    { INPUT_REC, "scan hold 5s" },
    { INPUT_PLAY, "zero" }, { INPUT_PLAY, "zero off" },
    { INPUT_SEL, "ADC old" }, { INPUT_SEL, "ADC SDK" },
    { INPUT_FX, "synth" },
    { INPUT_EDIT, "save" },
};
#elif defined(SB_HW_AUDIO10)
/* audio10's order: F from U through L, N, N', P and back to U (listen at
 * each), the synth (the chord test), the holds each on and off (the scan
 * hold ends by itself), a save. */
static const struct guide_step guide[] = {
    { INPUT_LFO, "F L" }, { INPUT_LFO, "F N" }, { INPUT_LFO, "F N'" }, { INPUT_LFO, "F P" }, { INPUT_LFO, "F U" },
    { INPUT_FX, "synth" },
    { INPUT_PLAY, "zero" }, { INPUT_PLAY, "zero off" },
    { INPUT_HOME, "LED hold" }, { INPUT_HOME, "LED back" },
    { INPUT_ENV, "screen hold" }, { INPUT_ENV, "screen back" },
    { INPUT_GLO, "log hold" }, { INPUT_GLO, "log back" },
    { INPUT_REC, "scan hold 5s" },
    { INPUT_EDIT, "save" },
};
#elif defined(SB_HW_AUDIO9)
/* audio9's order: the route is up from start-up and the tone plays; S2's
 * three presses (listen on headphones at each), then the synth (play the
 * keys), then a save. SEQ (the route's undo and redo) is out of it. */
static const struct guide_step guide[] = {
    { INPUT_LFO, "S2 upper" },
    { INPUT_LFO, "S2 lower" },
    { INPUT_LFO, "S2 both" },
    { INPUT_FX, "synth" },
    { INPUT_EDIT, "save" },
};
#elif defined(SB_HW_AUDIO8)
/* audio8's order: L2 runs from start-up; R2, step 1, the sweep (skipped
 * unless step 1 left port C still), the sense scan, a save. D, J, K and
 * L1 are out of it. */
static const struct guide_step guide[] = {
    { INPUT_KEY(3), "R2 pins" },
    { INPUT_KEY(4), "step 1" },
    { INPUT_KEY(5), "sweep" },
    { INPUT_KEY(6), "sense" },
    { INPUT_EDIT, "save" },
};
#else
static const struct guide_step guide[] = {
    { INPUT_KEY(1), "L1" },
    { INPUT_REC, "bit 9" },
    { INPUT_KEY(2), "L2" },
    { INPUT_REC, "bit 9 undo" },
    { INPUT_KEY(2), "L2" },
    { INPUT_EDIT, "save" },
};
#endif
#define GUIDE_N (sizeof guide / sizeof guide[0])
#define GUIDE_BLINK_MS 500u

u32 hw_guide_at;

static const char *key_name(u32 c)
{
    switch (c) {
    case INPUT_OCT_DOWN: return "OCT-";
    case INPUT_OCT_UP:   return "OCT+";
    case INPUT_FX:       return "FX";
    case INPUT_SEL:      return "SEL";
    case INPUT_ENV:      return "ENV";
    case INPUT_LFO:      return "LFO";
    case INPUT_EDIT:     return "EDIT";
    case INPUT_GLO:      return "GLO";
    case INPUT_HOME:     return "HOME";
    case INPUT_SAVE:     return "SAVE";
    case INPUT_ARP:      return "ARP";
    case INPUT_SEQ:      return "SEQ";
    case INPUT_PLAY:     return "PLAY";
    case INPUT_REC:      return "REC";
    case INPUT_KEY(1):   return "KEY1";
    case INPUT_KEY(2):   return "KEY2";
    case INPUT_KEY(3):   return "KEY3";
    case INPUT_KEY(4):   return "KEY4";
    case INPUT_KEY(5):   return "KEY5";
    case INPUT_KEY(6):   return "KEY6";
    default:             return "?";
    }
}

/* The next key and what it does: D's undo while a bit is kept, else the
 * table's entry; 0 when the order is done. */
/* The table's entry now: audio8 skips the sweep unless it may run. */
static u32 guide_at(void)
{
#if defined(SB_HW_AUDIO8)
    if (hw_guide_at < GUIDE_N && guide[hw_guide_at].key == INPUT_KEY(5) && !a8_sweep_allowed())
        return hw_guide_at + 1u;
#endif
    return hw_guide_at;
}

/* 1 while a kept set-up's undo comes before the table (audio7's L; in
 * audio8, L2 is the running state and not undone). */
static int guide_l_undo(void)
{
#if defined(SB_HW_AUDIO8)
    return 0;
#else
    return hw_aud.l_state == HW_L_KEPT;
#endif
}

static u32 guide_next(const char **what)
{
    u32 at = guide_at();

    if (guide_l_undo()) {
        *what = hw_aud.l_which == 1u ? "L1 undo" : "L2 undo";
        return INPUT_KEY(hw_aud.l_which) + 1u;
    }
    if (hw_aud.d_state == HW_D_KEPT) {
        *what = "D undo";
        return INPUT_OCT_DOWN + 1u;
    }
    if (at >= GUIDE_N)
        return 0;
    *what = guide[at].what;
    return guide[at].key + 1u;
}

/* A key pressed on the test screen: the guide moves on if it was the
 * table's next (D's undo of a kept bit isn't in the table). */
void hw_guide_key(u32 control)
{
    u32 at = guide_at();

    if (!guide_l_undo() && hw_aud.d_state != HW_D_KEPT && at < GUIDE_N && control == guide[at].key)
        hw_guide_at = at + 1u;
}

/* "next: KEY (what)" on the step row, or that the order is done. */
void hw_guide_show(void)
{
    static char t[40];
    const char *what = "";
    u32 k = guide_next(&what);
    char *p;

    if (!k) {
        hw_step("next: none, the suggested order is done");
        return;
    }
    p = put_s(t, "next: ");
    p = put_s(p, key_name(k - 1u));
    p = put_s(p, " (");
    p = put_s(p, what);
    p = put_s(p, ")");
    *p = 0;
    hw_step(t);
}

/* The next key's LED, blinking: on and off for GUIDE_BLINK_MS each. A key
 * whose LED is lit for its step blinks too while it is next; once the
 * guide moves on, its press and release set it as before. */
void hw_guide_tick(void)
{
    const char *what;
    u32 k;

#if defined(SB_HW_AUDIO10)
    /* audio10's C: the blink held, the LEDs left as they stand. */
    if (hw_aud.holds >> HW_A10_LED & 1u)
        return;
#endif
    k = guide_next(&what);
    if (k)
        input_led(k - 1u, sb_beacon.beats / GUIDE_BLINK_MS & 1u ? 0 : INPUT_LED_FULL);
}

/* --- leds1: the step keys' LEDs (the owner's request) ---------------------- */

/* 1 while the step a key stands for is taken: REC bit 9, SEQ ALNK0
 * stopped, ARP A, SAVE B, ENV H, FX H (it measures again), LFO I, SEL I
 * with bit 10, GLO K, OCT+ J with a bit left set. EDIT (a save) and every
 * other key: 0. */
u32 hw_audio_key_lit(u32 control)
{
#if defined(SB_HW_AUDIO10)
    /* audio10: SEQ the route, FX the synth, PLAY zeros, ENV the screen
     * hold, GLO the log hold (HOME's LED hold changes no LED). */
    switch (control) {
    case INPUT_SEQ:  return hw_aud.a9_route == HW_A9_ROUTE_UP;
    case INPUT_FX:   return hw_aud.a9_synth;
    case INPUT_PLAY: return hw_aud.holds >> HW_A10_ZERO & 1u;
    case INPUT_ENV:  return hw_aud.holds >> HW_A10_SCREEN & 1u;
    case INPUT_GLO:  return hw_aud.holds >> HW_A10_LOG & 1u;
    default:         return 0;
    }
#endif
#if defined(SB_HW_AUDIO9)
    /* audio9: the old steps' keys are the engine's now; SEQ lit while the
     * route is up, FX while the synth plays, LFO while S2 isn't both. */
    switch (control) {
    case INPUT_REC:  return hw_aud.step_state == HW_STEP_TAKEN;
    case INPUT_SEQ:  return hw_aud.a9_route == HW_A9_ROUTE_UP;
    case INPUT_FX:   return hw_aud.a9_synth;
    case INPUT_LFO:  return hw_aud.a9_s2 != HW_A9_S2_BOTH;
    default:         return 0;
    }
#endif
    switch (control) {
    case INPUT_REC:  return hw_aud.step_state == HW_STEP_TAKEN;
    case INPUT_SEQ:  return hw_aud.al_state == HW_AL_STOPPED;
    case INPUT_ARP:  return hw_aud.a_state == HW_STEP_TAKEN;
    case INPUT_SAVE: return hw_aud.b_state == HW_STEP_TAKEN;
    case INPUT_ENV:
    case INPUT_FX:   return hw_aud.h_state == HW_STEP_TAKEN;
    case INPUT_LFO:  return hw_aud.i_state == HW_STEP_TAKEN;
    case INPUT_SEL:  return hw_aud.i_state == HW_STEP_TAKEN && hw_aud.i_bit10;
    case INPUT_GLO:  return hw_aud.k_state == HW_STEP_TAKEN;
    case INPUT_OCT_UP: return hw_aud.j_state == HW_J_MOVED;
    case INPUT_OCT_DOWN: return hw_aud.d_state == HW_D_KEPT;
    case INPUT_KEY(1): return hw_aud.l_state == HW_L_KEPT && hw_aud.l_which == 1u;
    case INPUT_KEY(2): return hw_aud.l_state == HW_L_KEPT && hw_aud.l_which == 2u;
#if defined(SB_HW_AUDIO8)
    case INPUT_KEY(3): return hw_aud.r2_state == HW_A8_R2_SET;
    case INPUT_KEY(4): return hw_aud.s1_state == HW_A8_S1_KEPT;
    case INPUT_KEY(5): return hw_aud.sw_state == HW_A8_SW_KEPT;
#endif
    default:         return 0;
    }
}

/* After a step key's work: every step key's LED from its state (a step
 * can change another key's: I's undo clears SEL's bit 10), the key just
 * pressed, still held, lit. */
void hw_audio_leds(u32 held)
{
    static const u8 keys[] = { INPUT_REC, INPUT_SEQ, INPUT_ARP, INPUT_SAVE, INPUT_ENV, INPUT_FX, INPUT_LFO, INPUT_SEL,
                               INPUT_GLO, INPUT_OCT_UP, INPUT_OCT_DOWN, INPUT_KEY(1), INPUT_KEY(2),
#if defined(SB_HW_AUDIO8)
                               INPUT_KEY(3), INPUT_KEY(4), INPUT_KEY(5),
#endif
                             };
    u32 i;

    for (i = 0; i < sizeof keys; i++)
        input_led(keys[i], keys[i] == held || hw_audio_key_lit(keys[i]) ? INPUT_LED_FULL : 0);
}

#if defined(SB_HW_REPORT)
/* The audio probe's fields for the report log, in tools/report-decode.py's
 * FIELDS[5] order after the common ones (layout 4's log fields come after these): audio1's registers and audio2's,
 * read now; the counts and measures; each step's state and readbacks;
 * core 1's marks; the corex2 words now; each step's snapshots. */
static u32 put_words(u32 *w, u32 n, const u32 *v, u32 k)
{
    u32 i;

    for (i = 0; i < k; i++)
        w[n++] = v[i];
    return n;
}

#if defined(SB_HW_AUDIO11)
/* A channel's two values with the most readings (value << 22 | count), the
 * greater first; and the readings of its other slots. */
static const u32 *a11_top2(const u32 *sl)
{
    static u32 top[2];
    u32 k;

    top[0] = top[1] = 0;
    for (k = 0; k < HW_A11_SLOTS; k++) {
        u32 c = sl[k] & 0x3FFFFFu;

        if (c > (top[0] & 0x3FFFFFu)) {
            top[1] = top[0];
            top[0] = sl[k];
        } else if (c > (top[1] & 0x3FFFFFu)) {
            top[1] = sl[k];
        }
    }
    return top;
}

static u32 a11_rest(const u32 *sl)
{
    const u32 *top = a11_top2(sl);
    u32 k, r = 0;

    for (k = 0; k < HW_A11_SLOTS; k++)
        r += sl[k] & 0x3FFFFFu;
    return r - (top[0] & 0x3FFFFFu) - (top[1] & 0x3FFFFFu);
}
#endif

u32 hw_audio_report(u32 *w)
{
    u32 n = 0, i, j, k;

    measure();
    read_regs(w + n);
    n += HW_AUD_REGS;
    read_more(w + n);
    n += HW_AUD_MORE;
    w[n++] = sb_audio.blocks;
    w[n++] = sb_audio.underruns;
    w[n++] = hw_aud.flips;
    w[n++] = hw_aud.pend;
    w[n++] = hw_aud.fps10;
    w[n++] = hw_aud.halves;
    w[n++] = hw_aud.master;
    w[n++] = hw_aud.gain;
    w[n++] = hw_aud.tone_on;
    w[n++] = hw_aud.storm;
    w[n++] = hw_aud.started;
    w[n++] = hw_aud.step_state;
    w[n++] = hw_aud.steps;
    w[n++] = hw_aud.clk_before;
    w[n++] = hw_aud.clk_set;
    w[n++] = hw_aud.clk_back;
    w[n++] = hw_aud.al_state;
    w[n++] = hw_aud.al_keys;
    w[n++] = hw_aud.al_before;
    w[n++] = hw_aud.al_stop;
    w[n++] = hw_aud.al_back;
    w[n++] = hw_aud.al_blocks_stop;
    w[n++] = hw_aud.al_blocks_back;
    w[n++] = hw_aud.a_state;
    w[n++] = hw_aud.a_keys;
    w[n++] = hw_aud.a_before;
    w[n++] = hw_aud.a_clr;
    w[n++] = hw_aud.a_set;
    w[n++] = hw_aud.a_back;
    w[n++] = hw_aud.b_state;
    w[n++] = hw_aud.b_keys;
    w[n++] = hw_aud.b_before;
    w[n++] = hw_aud.b_set;
    w[n++] = hw_aud.b_back;
    w[n++] = hw_aud.refused;
    w[n++] = hw_aud.c1_moved;
    for (i = 0; i < HW_C1_MARKS; i++)
        w[n++] = hw_aud.c1_beat[i];
    for (i = 0; i < HW_C1_MARKS; i++)
        w[n++] = hw_aud.c1_count[i];
    read_x2(w + n);
    n += 16;
#if !defined(SB_HW_AUDIO13)
    /* Layout 12 (audio13) leaves out the old steps' snapshots and steps H,
     * I, K, J, D, L1 and L2 (audio2 to audio7, settled), for its own. */
    for (k = 0; k < HW_K_N; k++)
        for (j = 0; j < 2; j++)
            for (i = 0; i < HW_SNAP; i++)
                w[n++] = hw_aud.snap[k][j][i];
    /* Layout 2: steps H and I. */
    w[n++] = hw_aud.h_state;
    w[n++] = hw_aud.h_keys;
    w[n++] = hw_aud.h_measures;
    w[n++] = HW_H_GATE;
    w[n++] = hw_aud.h_clk1_before;
    w[n++] = hw_aud.h_clk1_check;
    w[n++] = hw_aud.h_clk1_audio;
    w[n++] = hw_aud.h_clk1_back;
    w[n++] = hw_aud.h_gp_before;
    w[n++] = hw_aud.h_gp_check;
    w[n++] = hw_aud.h_gp_audio;
    w[n++] = hw_aud.h_gp_back;
    w[n++] = hw_aud.h_check[0];
    w[n++] = hw_aud.h_check[1];
    w[n++] = hw_aud.h_check_to;
    w[n++] = hw_aud.h_check_clk2;
    w[n++] = hw_aud.h_audio[0];
    w[n++] = hw_aud.h_audio[1];
    w[n++] = hw_aud.h_audio_to;
    w[n++] = hw_aud.h_audio_clk2;
    w[n++] = JL_CLOCK->CLK_CON1;
    w[n++] = JL_GPCNT->CON;
    w[n++] = JL_GPCNT->NUM;
    w[n++] = hw_aud.i_state;
    w[n++] = hw_aud.i_keys;
    w[n++] = hw_aud.i_bit10;
    for (i = 0; i < 4; i++)
        w[n++] = hw_aud.i_con_before[i];
    for (i = 0; i < 4; i++)
        w[n++] = hw_aud.i_con_after[i];
    w[n++] = hw_aud.i_con_back;
    w[n++] = hw_aud.i_clk_before;
    w[n++] = hw_aud.i_clk_set;
    w[n++] = hw_aud.i_clk_set10;
    w[n++] = hw_aud.i_clk_back;
    w[n++] = hw_aud.i_flips;
    w[n++] = hw_aud.i_pend;
    w[n++] = hw_aud.i_span;
    w[n++] = hw_aud.i_hps10;
    i_read(w + n);
    n += 4;
    w[n++] = hw_aud.clk_depth;
    /* Layout 3: steps K and J. */
    w[n++] = hw_aud.k_state;
    w[n++] = hw_aud.k_keys;
    w[n++] = hw_aud.k_clk1_before;
    w[n++] = hw_aud.k_gp_before;
    w[n++] = hw_aud.k_clk1_back;
    w[n++] = hw_aud.k_gp_back;
    for (i = 0; i < HW_KM_N; i++)
        for (j = 0; j < 6; j++)
            w[n++] = hw_aud.k_m[i][j];
    w[n++] = hw_aud.j_state;
    w[n++] = hw_aud.j_sweeps;
    w[n++] = hw_aud.j_tries;
    w[n++] = hw_aud.j_reg;
    w[n++] = hw_aud.j_bit;
    w[n++] = hw_aud.j_before;
    w[n++] = hw_aud.j_written;
    w[n++] = hw_aud.j_read;
    w[n++] = hw_aud.j_back;
    w[n++] = hw_aud.j_flips;
    w[n++] = hw_aud.j_pend;
    w[n++] = hw_aud.j_irq;
    w[n++] = hw_aud.j_con0;
    w[n++] = hw_aud.j_con2;
    w[n++] = hw_aud.j_clk2;
    w[n++] = hw_aud.j_clk2_sweep;
    w[n++] = hw_aud.j_nohold;
    for (i = 0; i < HW_J_TRIES; i++)
        w[n++] = hw_aud.j_rb[i];
    w[n++] = JL_ALNK0->CON1;
    w[n++] = JL_ALNK0->CON3;
    /* Layout 5: step D. */
    w[n++] = hw_aud.d_state;
    w[n++] = hw_aud.d_sweeps;
    w[n++] = hw_aud.d_tries;
    w[n++] = hw_aud.d_bit;
    w[n++] = hw_aud.d_stop;
    w[n++] = hw_aud.d_phase;
    w[n++] = hw_aud.d_clk2;
    w[n++] = hw_aud.d_con5_before;
    w[n++] = hw_aud.d_con5_written;
    w[n++] = hw_aud.d_con5_read;
    w[n++] = hw_aud.d_con5_back;
    w[n++] = hw_aud.d_con5_after;
    for (i = 0; i < 9; i++)
        w[n++] = hw_aud.d_iomap_before[i];
    for (i = 0; i < 9; i++)
        w[n++] = hw_aud.d_iomap_after[i];
    for (i = 0; i < 8; i++)
        w[n++] = hw_aud.d_pa_before[i];
    for (i = 0; i < 8; i++)
        w[n++] = hw_aud.d_pa_set[i];
    for (i = 0; i < 8; i++)
        w[n++] = hw_aud.d_pa_after[i];
    w[n++] = hw_aud.d_in_start;
    w[n++] = hw_aud.d_in_end;
    w[n++] = hw_aud.d_flips;
    w[n++] = hw_aud.d_pend;
    w[n++] = hw_aud.d_irq;
    w[n++] = hw_aud.d_idle_base;
    for (i = 0; i < 3; i++)
        w[n++] = hw_aud.d_map_base[i];
    w[n++] = hw_aud.d_idle_set;
    for (i = 0; i < 3; i++)
        w[n++] = hw_aud.d_map_set[i];
    w[n++] = hw_aud.d_idle_after;
    for (i = 0; i < 3; i++)
        w[n++] = hw_aud.d_map_after[i];
    w[n++] = hw_aud.d_check_set;
    w[n++] = hw_aud.d_check_after;
    for (i = 0; i < 4; i++)
        w[n++] = hw_aud.d_al0[i];
    w[n++] = hw_aud.d_irq_now;
    w[n++] = hw_aud.d_core1;
    w[n++] = hw_aud.d_j_putback;
    w[n++] = IOMAP_CON5;
    /* Layout 6: set-ups L1 and L2. */
    w[n++] = hw_aud.l_state;
    w[n++] = hw_aud.l_which;
    w[n++] = hw_aud.l_presses;
    w[n++] = hw_aud.l_stop;
    w[n++] = hw_aud.l_phase;
    w[n++] = hw_aud.l_stopped;
    for (i = 0; i < 4; i++)
        w[n++] = hw_aud.l_before[i];
    w[n++] = hw_aud.l_len_read;
    w[n++] = hw_aud.l_adr_read;
    w[n++] = hw_aud.l_len_used;
    w[n++] = hw_aud.l_clk1;
    w[n++] = hw_aud.l_clk2;
    for (i = 0; i < 8; i++)
        w[n++] = hw_aud.l_pa_before[i];
    w[n++] = hw_aud.l_irq0;
    w[n++] = hw_aud.l_core1_0;
    w[n++] = hw_aud.l_exp_fps10;
    w[n++] = hw_aud.l_exp_hps10_a;
    w[n++] = hw_aud.l_exp_hps10_b;
    for (i = 0; i < 4; i++)
        w[n++] = hw_aud.l_w[i];
    for (i = 0; i < 4; i++)
        w[n++] = hw_aud.l_rb[i];
    w[n++] = hw_aud.l_flips;
    w[n++] = hw_aud.l_pend;
    w[n++] = hw_aud.l_irq;
    w[n++] = hw_aud.l_span;
    w[n++] = hw_aud.l_hps10;
    w[n++] = hw_aud.l_fps10_a;
    w[n++] = hw_aud.l_fps10_b;
    w[n++] = hw_aud.l_idle_base;
    for (i = 0; i < 3; i++)
        w[n++] = hw_aud.l_map_base[i];
    w[n++] = hw_aud.l_idle_set;
    for (i = 0; i < 3; i++)
        w[n++] = hw_aud.l_map_set[i];
    for (i = 0; i < 8; i++)
        w[n++] = hw_aud.l_pa_set[i];
    w[n++] = hw_aud.l_check_set;
    w[n++] = hw_aud.l_idle_after;
    for (i = 0; i < 3; i++)
        w[n++] = hw_aud.l_map_after[i];
    for (i = 0; i < 8; i++)
        w[n++] = hw_aud.l_pa_after[i];
    w[n++] = hw_aud.l_check_after;
    for (i = 0; i < 3; i++)
        w[n++] = hw_aud.l_back[i];
    w[n++] = hw_aud.l_clk2_end;
    w[n++] = hw_aud.l_core1_end;
#else
    (void)i;
    (void)j;
    (void)k;
#endif
    /* Layout 7: audio8 (0 in a build without it). */
    w[n++] = hw_aud.a8_boot;
    w[n++] = hw_aud.a8_off;
    w[n++] = hw_aud.a8_pcm16;
    w[n++] = hw_aud.r9_flips;
    w[n++] = hw_aud.r9_irq;
    w[n++] = hw_aud.r9_clk2;
    n = put_words(w, n, hw_aud.ctl, HW_A8_PINS);
    w[n++] = hw_aud.ctl_n;
    w[n++] = hw_aud.ctl_span;
    w[n++] = hw_aud.r2_state;
    w[n++] = hw_aud.r2_presses;
    w[n++] = hw_aud.r2_check;
    n = put_words(w, n, hw_aud.r2_pc_before, 8);
    n = put_words(w, n, hw_aud.r2_pc_set, 8);
    n = put_words(w, n, hw_aud.r2_pc_after, 8);
    w[n++] = hw_aud.s1_state;
    w[n++] = hw_aud.s1_runs;
    n = put_words(w, n, hw_aud.s1a, HW_A8_PINS);
    w[n++] = hw_aud.s1a_n;
    w[n++] = hw_aud.s1a_span;
    w[n++] = hw_aud.rt_kind;
    w[n++] = hw_aud.rt_bit;
    w[n++] = hw_aud.rt_phase;
    w[n++] = hw_aud.rt_stop;
    n = put_words(w, n, hw_aud.rt_con0, 4);
    n = put_words(w, n, hw_aud.rt_con5, 4);
    n = put_words(w, n, hw_aud.rt_iomap_before, 9);
    n = put_words(w, n, hw_aud.rt_iomap_after, 9);
    w[n++] = hw_aud.rt_idle_base;
    n = put_words(w, n, hw_aud.rt_map_base, 3);
    w[n++] = hw_aud.rt_idle_set;
    n = put_words(w, n, hw_aud.rt_map_set, 3);
    w[n++] = hw_aud.rt_idle_after;
    n = put_words(w, n, hw_aud.rt_map_after, 3);
    n = put_words(w, n, hw_aud.rt_pa_before, 8);
    n = put_words(w, n, hw_aud.rt_pa_set, 8);
    n = put_words(w, n, hw_aud.rt_pa_after, 8);
    n = put_words(w, n, hw_aud.rt_pc_set, 8);
    w[n++] = hw_aud.rt_check_set;
    w[n++] = hw_aud.rt_check_after;
    n = put_words(w, n, hw_aud.rt_c1, HW_A8_PINS);
    w[n++] = hw_aud.rt_n1;
    w[n++] = hw_aud.rt_span1;
    n = put_words(w, n, hw_aud.rt_c2, HW_A8_PINS);
    w[n++] = hw_aud.rt_n2;
    w[n++] = hw_aud.rt_span2;
    w[n++] = hw_aud.rt_flips;
    w[n++] = hw_aud.rt_irq;
    w[n++] = hw_aud.sw_state;
    w[n++] = hw_aud.sw_sweeps;
    w[n++] = hw_aud.sw_tries;
    w[n++] = hw_aud.sw_stop;
    w[n++] = hw_aud.sw_pa_bits;
    w[n++] = hw_aud.sw_nohold;
#if !defined(SB_HW_AUDIO11)
    /* Layout 10 (audio11) leaves out the sense scan's fields. */
    w[n++] = hw_aud.se_state;
    w[n++] = hw_aud.se_runs;
    w[n++] = hw_aud.se_ms;
    n = put_words(w, n, hw_aud.se_dir, 8);
    n = put_words(w, n, hw_aud.se_die, 8);
    n = put_words(w, n, hw_aud.se_in0, 8);
    n = put_words(w, n, hw_aud.se_changed, 8);
    n = put_words(w, n, hw_aud.se_count, 64);
    w[n++] = hw_aud.se_ev_n;
    w[n++] = hw_aud.se_ev_lost;
    n = put_words(w, n, hw_aud.se_ev, HW_A8_EVENTS);
#endif
    /* Layout 8: audio9 (0 in a build without it). */
    w[n++] = hw_aud.a9_route;
    w[n++] = hw_aud.a9_ups;
    w[n++] = hw_aud.a9_downs;
    w[n++] = hw_aud.a9_synth;
    w[n++] = hw_aud.a9_synth_ons;
    w[n++] = hw_aud.a9_s2;
    w[n++] = hw_aud.a9_late0;
    w[n++] = hw_aud.a9_late;
    w[n++] = hw_aud.a9_fill_max;
    w[n++] = hw_aud.a9_fill_last;
    w[n++] = hw_aud.a9_fallback;
    w[n++] = hw_aud.a9_engine_blocks;
    w[n++] = sb_audio.underruns;
    w[n++] = sb_audio.fill_max;
    w[n++] = hw_aud.pb5_now;
    w[n++] = hw_aud.pb5_raw_changes;
    w[n++] = hw_aud.pb5_settled;
    w[n++] = hw_aud.pb5_logged;
    n = put_words(w, n, hw_aud.pb5_t, HW_A9_PB5_TIMES);
    w[n++] = hw_aud.daa7_boot;
    w[n++] = hw_aud.daa7_route;
    w[n++] = hw_aud.daa7_last;
    w[n++] = hw_aud.daa7_reads;
    w[n++] = hw_aud.daa7_changes;
    n = put_words(w, n, hw_aud.a9_words[0], 4u * HW_A10_FMTS);
    w[n++] = sb_midi_out.bytes;
    /* Layout 9: audio10 (0 in a build without it). */
    w[n++] = hw_aud.a10_fmt_changes;
#if !defined(SB_HW_AUDIO11)
    n = put_words(w, n, hw_aud.a10_fmt_t, HW_A10_FMT_LOG);
#endif
    w[n++] = hw_aud.a10_fill_max;
    w[n++] = hw_aud.a10_fill_max8;
    w[n++] = hw_aud.a10_voices_max;
    w[n++] = hw_aud.a10_soft;
    w[n++] = hw_aud.a10_hard;
    w[n++] = hw_aud.m_value;
    w[n++] = hw_aud.m_raw;
    w[n++] = sb_input.pot_raw;
    w[n++] = hw_aud.m_tone_gain;
    w[n++] = hw_aud.m_synth_target;
    w[n++] = hw_aud.m_changes;
    w[n++] = hw_aud.m_jumps;
    w[n++] = hw_aud.m_maxdelta;
    w[n++] = hw_aud.m_ring_n;
    n = put_words(w, n, hw_aud.m_ring, HW_A10_MRING);
    w[n++] = hw_aud.holds;
    w[n++] = hw_aud.hold_n;
    n = put_words(w, n, hw_aud.hold_t, HW_A10_HOLD_LOG);
    w[n++] = hw_aud.log_dropped;
    w[n++] = hw_aud.scan_until;
#if defined(SB_HW_AUDIO11)
    /* Layout 10: audio11. */
    w[n++] = hw_aud.adc_setup;
    w[n++] = hw_aud.adc_set_n;
#if !defined(SB_HW_AUDIO12)
    /* Layout 11 (audio12) leaves out the set-up's change list, the old
     * set-up's channels, MASTER's raw ring and jump list, and the fill per
     * algorithm (the sweep's replaces it): audio11 settled them. */
    n = put_words(w, n, hw_aud.adc_set_t, HW_A11_SET_LOG);
#endif
    n = put_words(w, n, hw_aud.sar_con[0], 4u * HW_A11_SETUPS);
    n = put_words(w, n, hw_aud.adc_conv_n, HW_A11_SETUPS);
    n = put_words(w, n, hw_aud.adc_conv_to, HW_A11_SETUPS);
    n = put_words(w, n, hw_aud.adc_conv_min, HW_A11_SETUPS);
    n = put_words(w, n, hw_aud.adc_conv_max, HW_A11_SETUPS);
    n = put_words(w, n, hw_aud.adc_conv_tight, HW_A11_SETUPS);
    w[n++] = hw_aud.adc_pass_max;
    w[n++] = hw_aud.adc_passes;
    {
        u32 st, c;

#if defined(SB_HW_AUDIO12)
        for (st = 0; st < 1u; st++)
#else
        for (st = 0; st < HW_A11_SETUPS; st++)
#endif
            for (c = 0; c < HW_A11_CHANS; c++) {
                w[n++] = hw_aud.adc_mm[st][c];
                w[n++] = hw_aud.adc_n[st][c];
                n = put_words(w, n, a11_top2(hw_aud.adc_v[st][c]), 2);
                w[n++] = hw_aud.adc_other[st][c] + a11_rest(hw_aud.adc_v[st][c]);
            }
    }
#if !defined(SB_HW_AUDIO12)
    n = put_words(w, n, hw_aud.m_raw_ring, HW_A10_MRING / 2u);
#endif
    w[n++] = hw_aud.m_jump_n;
#if !defined(SB_HW_AUDIO12)
    n = put_words(w, n, hw_aud.m_jump_t, HW_A11_JUMPS);
    {
        u32 k;

        /* The fill per algorithm, 0.1 us units: with 8 voices << 16 | any. */
        for (k = 0; k < HW_A11_ALGS; k++)
            w[n++] = (hw_aud.fill_alg8[k] * 10u / 24u) << 16 | (hw_aud.fill_alg[k] * 10u / 24u & 0xFFFFu);
    }
#endif
    w[n++] = hw_aud.m_level;
    n = put_words(w, n, (const u32 *)(const void *)hw_aud.big, 12);
#endif
#if defined(SB_HW_AUDIO12)
    /* Layout 11: audio12. */
    w[n++] = hw_aud.start_mode;
    w[n++] = hw_aud.as_state;
    w[n++] = hw_aud.as_alg;
    w[n++] = hw_aud.as_runs;
    w[n++] = hw_aud.as_stop;
    w[n++] = hw_aud.as_chords;
    {
        u32 k;

        /* Each algorithm's longest fill, 0.1 us units, with the voices
         * then << 16. */
        for (k = 0; k < HW_A11_ALGS; k++)
            w[n++] = hw_aud.as_fill_v[k] << 16 | (hw_aud.as_fill[k] * 10u / 24u & 0xFFFFu);
    }
    n = put_words(w, n, hw_aud.as_soft, HW_A11_ALGS);
    n = put_words(w, n, hw_aud.as_hard, HW_A11_ALGS);
    n = put_words(w, n, hw_aud.as_late, HW_A11_ALGS);
    n = put_words(w, n, hw_aud.as_rel, HW_A11_ALGS);
    w[n++] = hw_aud.g_note_n;
    n = put_words(w, n, hw_aud.g_note, HW_A12_NOTES);
    w[n++] = hw_aud.g_turns;
    w[n++] = hw_aud.g_turns_off;
    w[n++] = hw_aud.g_turn_alg;
#endif
#if defined(SB_HW_AUDIO13)
    /* Layout 12: audio13 (tools/report_decode.py's _layout12). */
    w[n++] = hw_aud.a13_start;
    n = put_words(w, n, hw_aud.u2_boot, HW_A13_WORDS);
    n = put_words(w, n, hw_aud.u2_late, HW_A13_WORDS);
    w[n++] = hw_aud.u2_late_beat;
    w[n++] = hw_aud.u2_late_blocks;
    n = put_words(w, n, hw_aud.u2_key, HW_A13_WORDS);
    w[n++] = hw_aud.u2_key_beat;
    w[n++] = hw_aud.u2_key_n;
    w[n++] = hw_aud.u2_state;
    w[n++] = hw_aud.u2_run;
    w[n++] = hw_aud.u2_polls;
    n = put_words(w, n, hw_aud.u2_ref, HW_A13_WORDS);
    n = put_words(w, n, hw_aud.u2_last, HW_A13_WORDS);
    w[n++] = hw_aud.u2_mark_n;
    n = put_words(w, n, hw_aud.u2_mark, HW_A13_MARKS);
    w[n++] = hw_aud.u2_chg_n;
    n = put_words(w, n, hw_aud.u2_chg[0], 2u * HW_A13_CHANGES);
    n = put_words(w, n, hw_aud.u2_or[0][0], HW_A13_RUNS * HW_A13_STATES * HW_A13_WORDS);
    n = put_words(w, n, hw_aud.u2_and[0][0], HW_A13_RUNS * HW_A13_STATES * HW_A13_WORDS);
    n = put_words(w, n, hw_aud.u2_seen, HW_A13_RUNS);
    w[n++] = hw_aud.u2c_on;
    w[n++] = hw_aud.u2c_toggles;
    n = put_words(w, n, hw_aud.u2c_n[0], 2u * HW_A13_STATES);
    n = put_words(w, n, hw_aud.u2c_mm[0], 2u * HW_A13_STATES);
    w[n++] = hw_aud.u2c_to;
    n = put_words(w, n, hw_aud.u2c_first, HW_A13_C_FIRST);
    w[n++] = hw_aud.u2c_log_n;
    n = put_words(w, n, hw_aud.u2c_log, HW_A13_C_LOG);
    w[n++] = hw_aud.arp_n;
    w[n++] = hw_aud.arp_breaks;
    w[n++] = hw_aud.arp_gaps;
    w[n++] = hw_aud.arp_gmin_f;
    w[n++] = hw_aud.arp_gmax_f;
    w[n++] = hw_aud.arp_gmin_u;
    w[n++] = hw_aud.arp_gmax_u;
    w[n++] = hw_aud.arp_last_f;
    w[n++] = hw_aud.arp_last_u;
    w[n++] = hw_aud.arp_best_n;
    w[n++] = hw_aud.arp_best_f0;
    w[n++] = hw_aud.arp_best_u0;
    w[n++] = hw_aud.arp_best_f1;
    w[n++] = hw_aud.arp_best_u1;
#if !defined(SB_HW_U3U)
    /* Layout 14 leaves ARP's step log out: R is done (HW-179). */
    n = put_words(w, n, hw_aud.arp_log[0], 2u * HW_A13_ARP_LOG);
#endif
#endif
#if defined(SB_HW_AUDIO14)
    /* Layout 13: audio14 after layout 12 (tools/report_decode.py's _layout13). */
    n = put_words(w, n, hw_aud.p_boot, HW_A14_P_WORDS);
    n = put_words(w, n, hw_aud.p_late, HW_A14_P_WORDS);
    n = put_words(w, n, hw_aud.p_key, HW_A14_P_WORDS);
    w[n++] = hw_aud.arp_saves;
    w[n++] = hw_aud.arp_save_err;
    w[n++] = hw_aud.arp_save_seq;
    w[n++] = hw_aud.arp_offs;
#endif
#if defined(SB_HW_U3U)
    /* Layout 14: the USB device's record, whole (usb_midi.h). */
    n = put_words(w, n, (const u32 *)&sb_usb, USB_REC_WORDS);
#endif
    return n;
}
#endif

#endif
