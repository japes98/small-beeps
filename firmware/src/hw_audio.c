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
#include "fm.h"
#include "ui.h"
#include "arp.h"
#if defined(SB_USB_MIDI)
#include "usb_midi.h"
#endif
#include "hw_fm1.h"
#include "WL82.h"

#include "hw_audio_int.h"

#if defined(SB_HW_FM1)

struct hw_audio hw_aud;

/* A record in the report log (hw_report.c, SB_HW_REPORT), labelled. */
void report(const char *label)
{
    /* audio10's C: while the log is held, records are dropped and counted. */
    if (hw_aud.holds >> HW_A10_LOG & 1u) {
        hw_aud.log_dropped++;
        return;
    }
    hw_report_save(label);
}

#if defined(SB_USB_MIDI)
/* U3-U (usb_midi.c): a USB stage on the step row and, with a label, a
 * record; main's loop only. */
void usb_midi_note(const char *label, const char *step)
{
    hw_step(step);
#if defined(SB_HW_TEST)
    if (label)
        report(label);
#else
    /* The release logs USB's problems only (round 2): a give-up. Stalls
     * and drops are found by hw_inst_serve from the counts. */
    if (label && label[4] == 'g' && label[5] == 'i')
        hw_inst_problem(label);
#endif
}
#endif
const u8 l_con3[3] = { 0, 0xC2u, 0x83u };    /* L1: the oscillator, /1, 512 a frame; L2: the PLL's audio clock, /1, 256 */
static const u8 a11_index[12] = { 0, 1, 0xFF, 2, 3, 4, 5, 6, 0xFF, 0xFF, 7, 8 };
volatile u32 cv_busy, cv_hold;
u32 cv_ch, cv_set, cv_t0, cv_turn, cv_next, cv_pot_new, cv_pot_v, cv_swept;

/* CON's fields but the enable and start: the SDK's (HW-167: the channel
 * in bits 8-11, bits 0-2 0b110, bits 12-15 0xF, bit 3) or the old (the
 * channel alone). Bit 5, the interrupt enable, is not set in either: the
 * build polls bit 7 (the SDK sets it). */
u32 a11_fields(u32 ch, u32 set)
{
    return set == HW_A11_SDK ? (ch << 8 | 0xFu << 12 | 1u << 3 | 6u) : ch << 8;
}

/* A conversion started: the SDK's three writes, or the old one. */
void cv_start(u32 ch)
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
void cv_record(u32 ch, u32 set, u32 v, u32 d)
{
    u32 i, k, lo = 0xFFFFFFFFu, at = 0, *sl;

#if defined(SB_HW_TEST)
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
            else
                hw_aud.u2c_to++;
        } else {
            cv_record(cv_ch, cv_set, JL_ADC->RES & 0x3FFu, d);
        }
        cv_busy = 0;
    }
#if defined(SB_HW_TEST)
    /* MASTER every other conversion; only MASTER while the scan is held. */
    cv_turn ^= 1u;
    cv_start(cv_turn || hw_hold_sweeps ? 4u : cv_sweep_next());
#else
    /* The release: MASTER alone, as the test build's held scan does
     * (HW-169, HW-170: the SDK's set-up). */
    cv_start(4u);
#endif
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

u32 phase, gain, tone_on = 1, storm_beat, storm_n;

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
void read_master(void)
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
    if (hw_aud.a9_s2 == HW_A9_S2_UPPER)
        return u << 16;
    if (hw_aud.a9_s2 == HW_A9_S2_LOWER)
        return u;
    /* N and N': the sample in one half, its negative in the other (the
     * most negative's negative clamped to the most positive). */
    if (hw_aud.a9_s2 == HW_A10_N || hw_aud.a9_s2 == HW_A10_N2) {
        u32 v = (u16)(s == -32768 ? 32767 : -s);

        return hw_aud.a9_s2 == HW_A10_N ? u << 16 | v : v << 16 | u;
    }
    return u << 16 | u;
}
static s32 syn_tmp[2u * AUDIO_FRAMES];
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

static void synth_fill(s32 *out, u32 frames)
{
    u32 t0 = sb_now(), d, v;
#if defined(SB_HW_TEST)
    /* S: the sweep's notes and algorithm for this call's blocks (the
     * unit's half is two of the engine's blocks, fwtest's one). */
    a12_sweep_step(2u * frames);
#endif
    u32 h, n;

    for (h = 0; h < 2u; h++) {
        fm_block(syn_tmp, frames);
        hw_aud.a9_engine_blocks++;
        for (n = 0; n < frames; n++)
            out[h * frames + n] = (s32)pack16(syn16(syn_tmp[2u * n]));
    }
    d = sb_now() - t0;
    v = sb_fm.voices[0] + sb_fm.voices[1];
    if (d > hw_aud.a10_fill_max)
        hw_aud.a10_fill_max = d;
    if (v >= 8u && d > hw_aud.a10_fill_max8)
        hw_aud.a10_fill_max8 = d;
    if (v > hw_aud.a10_voices_max)
        hw_aud.a10_voices_max = v;
    /* D item 4: the longest per algorithm (sb_fm's, 1 to 10). */
    v = sb_fm.algorithm - 1u;
    if (v < HW_A11_ALGS) {
        if (d > hw_aud.fill_alg[v])
            hw_aud.fill_alg[v] = d;
        if (sb_fm.voices[0] + sb_fm.voices[1] >= 8u && d > hw_aud.fill_alg8[v])
            hw_aud.fill_alg8[v] = d;
    }
#if defined(SB_HW_TEST)
    /* S: the sweep's algorithm's longest fill, with the voices then. */
    if (a12_running()) {
        v = hw_aud.as_alg - 1u;
        if (d > hw_aud.as_fill[v]) {
            hw_aud.as_fill[v] = d;
            hw_aud.as_fill_v[v] = sb_fm.voices[0] + sb_fm.voices[1];
        }
    }
    /* ARP: the steps this fill's blocks played, timed by its start. */
    a13_arp_take(t0);
#else
    (void)t0;
#endif
}

/* The engine (audio.h): one block, and the probe's measures. */
void tone_block(s32 *out, u32 frames)
{
    u32 n, b = sb_beacon.beats, t = sb_now(), want;

    u32 base = frames;
    /* On the unit a half is LEN frames of one word (HW-160): the block's
     * words are twice its frames in fwtest's layout. */
    frames *= 2u;
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

    /* audio9's S1: the synth fills the half in place of the tone; past
     * HW_A9_LATE_MAX late halves since it came on, back to the tone (so
     * main, the screen and the keys keep running). In the tone, the
     * engine's queue of the panel's events is emptied each block, so the
     * synth starts with none stale. */
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
#if defined(SB_HW_TEST)
    /* The test build's fallback: the tone once the synth is too late. The
     * release keeps the synth and logs each underrun (hw_inst_serve). */
    if (hw_aud.a9_synth && sb_audio.underruns - hw_aud.a9_late0 > HW_A9_LATE_MAX) {
        hw_aud.a9_synth = 0;
        hw_aud.a9_fallback = b ? b : 1u;
    }
#endif
    if (hw_aud.a9_synth) {
        synth_fill(out, base);
#if defined(SB_HW_TEST)
        a9_capture(out);
#endif
        return;
    }
    {
        struct input_event e;

        while (input_read_audio(&e))
            ;
    }
    read_master();
    /* B3: MASTER's square (0 silent, 1023 the top), the change ramped
     * evenly over the half; (m^2 >> 4) * GAIN_TOP stays within 32 bits. */
    want = tone_on ? (hw_aud.master * hw_aud.master >> 4) * GAIN_TOP / (1023u * 1023u >> 4) : 0;
    {
        s32 step = ((s32)want - (s32)gain) / (s32)frames;
        u32 end = want;
    for (n = 0; n < frames; n++) {
        s32 s;

        gain = n + 1u == frames ? end : (u32)((s32)gain + step);
        s = (s32)((sine(phase) * (s32)gain) >> 11);
        phase += TONE_STEP;
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
    }
    }
    hw_aud.gain = gain;
#if defined(SB_HW_TEST)
    a9_capture(out);
#endif
}

/* The audio probe's fields for the report log, in tools/report-decode.py's
 * FIELDS[5] order after the common ones (layout 4's log fields come after these): audio1's registers and audio2's,
 * read now; the counts and measures; each step's state and readbacks;
 * core 1's marks; the corex2 words now; each step's snapshots. */
u32 put_words(u32 *w, u32 n, const u32 *v, u32 k)
{
    u32 i;

    for (i = 0; i < k; i++)
        w[n++] = v[i];
    return n;
}


/* --- Round 2's release (docs/DESIGN-NOTES.md, clean-r2-cleanup) ---------- */

/* The release's start: the instrument from power-on with the writes of
 * the test build's cold start in their order, and none of its checks,
 * waits or records (each settled by an entry):
 * - the engine, then the synth on and ALNK0 started (HW-174, HW-175: the
 *   engine fits on core 0, so core 1 isn't started; HW-137);
 * - L2: CON0's run bit off, CON3 the PLL's audio clock, CON1 data 3 as
 *   16-bit I2S, CON0 run on with bits 7 and 8 clear (HW-157, HW-160). The
 *   one check kept is a read: CLK_CON2 bit 9 set stops the link (HW-160),
 *   a problem record and no sound;
 * - R2: PC0, PC1, PC2 and PC6 as a master's pins, OUT 1, DIR 0, DIE 1,
 *   each a read-modify-write of those bits (HW-158, HW-162);
 * - the route: CON0 bits 7 and 8 (HW-162, HW-164);
 * - the panel's message, then ready.
 * The test build's link watch (1 s), the matrix checks before and after
 * each write (which refuse the route while a key is held), the port
 * samples and core 1's marks are gone here: HW-162, HW-164, HW-176 and
 * HW-177 settle the path and the start from cold. */
u32 hw_inst_at[HW_INST_STAGES];
static u32 inst_problems, inst_dropped, inst_summary, inst_seen_under, inst_seen_stall, inst_seen_drop;
static u32 inst_stack_low;

static void inst_at(u32 k)
{
    hw_inst_at[k] = sb_now();
}

void hw_inst_problem(const char *label)
{
    if (inst_problems >= HW_INST_PROBLEMS) {
        inst_dropped++;
        return;
    }
    inst_problems++;
    report(label);
}

void hw_inst_start(void)
{
    u32 c0;

    inst_at(HW_INST_ENGINE);
    fm_init();
    hw_aud.a9_late0 = sb_audio.underruns;
    hw_aud.a9_synth_ons = 1;
    hw_aud.a9_synth = 1;
    inst_at(HW_INST_AUDIO);
    hw_aud.tone_on = 1;
    hw_aud.a8_pcm16 = 1;
    hw_aud.a9_s2 = HW_A10_N;
    audio_start(tone_block);
    hw_aud.started = sb_beacon.beats ? sb_beacon.beats : 1;
    inst_at(HW_INST_L2);
    if (JL_CLOCK->CLK_CON2 & CLK2_ALNK0_EN) {
        hw_aud.a8_off = HW_A8_OFF_L2;
        hw_inst_problem("L2 bit 9");
    } else {
        c0 = JL_ALNK0->CON0;
        JL_ALNK0->CON0 = c0 & ~AL_RUN;
        JL_ALNK0->CON3 = l_con3[2];
        JL_ALNK0->CON1 = L_CON1;
        JL_ALNK0->CON0 = (c0 & ~L_PINS) | AL_RUN;
        hw_aud.l_which = 2;
        hw_aud.l_state = HW_L_KEPT;
        inst_at(HW_INST_R2);
        lcd_wait();
        PORT_W(P_C, R_OUT) |= A8_PC_PINS;
        PORT_W(P_C, R_DIR) &= ~A8_PC_PINS;
        PORT_W(P_C, R_DIE) |= A8_PC_PINS;
        hw_aud.r2_state = HW_A8_R2_SET;
        inst_at(HW_INST_ROUTE);
        JL_ALNK0->CON0 |= L_PINS;
        hw_aud.a9_route = HW_A9_ROUTE_UP;
    }
    inst_at(HW_INST_PANEL);
    hw_aud.start_mode = HW_A12_INSTRUMENT;
    lcd_wait();
    view_message(hw_aud.a9_route == HW_A9_ROUTE_UP ? "small-beeps" : "NO SOUND: CLK_CON2 bit 9", 0);
    hw_hold_screen = 1;
    inst_at(HW_INST_READY);
}

/* Unused words at the bottom of a stack (crt0.S fills both with
 * SB_STACK_FILL), in bytes. */
static u32 stack_free(const u32 *bottom, const u32 *top)
{
    const u32 *p = bottom;

    while (p < top && *p == SB_STACK_FILL)
        p++;
    return (u32)(p - bottom) * 4u;
}

extern u32 __stack_limit[], __irq_stack_top[], __stack_top[];

/* Main's loop, on each wake: the summary once the start is done, then a
 * problem record for each new kind of trouble the counts show (at most
 * HW_INST_PROBLEMS a power-on). */
void hw_inst_serve(void)
{
    u32 m, i;

    if (!inst_summary) {
        inst_summary = 1;
        inst_seen_under = sb_audio.underruns;
        report("Summary");
        return;
    }
    if (sb_audio.underruns != inst_seen_under) {
        inst_seen_under = sb_audio.underruns;
        hw_inst_problem("Underrun");
    }
#if defined(SB_USB_MIDI)
    if (sb_usb.stalls != inst_seen_stall) {
        inst_seen_stall = sb_usb.stalls;
        hw_inst_problem("USB stall");
    }
    if (sb_usb.rx_dropped + sb_usb.out_full != inst_seen_drop) {
        inst_seen_drop = sb_usb.rx_dropped + sb_usb.out_full;
        hw_inst_problem("USB drop");
    }
#else
    (void)inst_seen_stall;
    (void)inst_seen_drop;
#endif
    m = stack_free(__irq_stack_top, __stack_top);
    i = stack_free(__stack_limit, __irq_stack_top);
    if (!(inst_stack_low & 1u) && m < INST_STACK_LOW) {
        inst_stack_low |= 1u;
        hw_inst_problem("Stack low main");
    }
    if (!(inst_stack_low & 2u) && i < INST_STACK_LOW) {
        inst_stack_low |= 2u;
        hw_inst_problem("Stack low irq");
    }
}

/* The release's record (layout 18, tools/report_decode.py's _layout18):
 * the start's stages in us, the counts, the stacks' unused bytes, and
 * with SB_USB_MIDI the USB device's record whole. */
u32 hw_inst_report(u32 *w)
{
    u32 n = 0, i;

    for (i = 0; i < HW_INST_STAGES; i++)
        w[n++] = hw_inst_at[i] / 24u;
    w[n++] = inst_problems;
    w[n++] = inst_dropped;
    w[n++] = sb_beacon.beats;
    w[n++] = sb_audio.blocks;
    w[n++] = sb_audio.underruns;
    w[n++] = sb_audio.fill_max;
    w[n++] = hw_aud.storm;
    w[n++] = hw_aud.a9_route;
    w[n++] = stack_free(__irq_stack_top, __stack_top);
    w[n++] = stack_free(__stack_limit, __irq_stack_top);
#if defined(SB_USB_MIDI)
    n = put_words(w, n, (const u32 *)&sb_usb, USB_REC_WORDS);
#endif
    return n;
}
#endif
