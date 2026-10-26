/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * The arpeggiator (ARP; docs/ARP-PROPOSAL.md with the owner's answers,
 * docs/DESIGN-NOTES.md, "ARP"): while it is on, the notes held (the
 * panel's keys, MIDI in, the pedal) are not played as a chord; it plays
 * them one at a time (or all together, CHORD) on a clock, in a pattern,
 * over up to four octaves.
 *
 * - Its settings travel with the patch (docs/PATCH-FORMAT.md, version 2:
 *   on, latch, mode, octaves, rate, swing, gate); the tempo and what MIDI
 *   out sends while it runs belong to the instrument (struct
 *   midi_settings, version 4).
 * - The clock: the internal tempo, or MIDI clock (0xF8, 24 a beat; Start,
 *   Stop, Continue) whenever it arrives, back to the internal tempo after
 *   a Stop or ARP_LOST_BLOCKS without a clock. Its position is counted in
 *   ARP_UNIT units a MIDI clock pulse, exactly: 34 x the tempo a frame
 *   (below), so the internal clock never drifts.
 * - MIDI clock out: while it runs on the internal clock, a 0xF8 a pulse,
 *   a Start when its pattern and grid start again (with that pulse's
 *   0xF8), a Stop when it stops or MIDI clock takes over, a Continue when
 *   the internal clock takes over again.
 * - A step falls on its frame within the audio block: the engine starts
 *   and releases its notes at that frame (fm.h, struct fm_voice's
 *   pending start or release; fm.c renders the block in two parts).
 *
 * Everything here runs on core 0, in the audio interrupt (fm_play.c's
 * block callback): the engine passes the notes held as they change, the
 * clock bytes MIDI in received, and calls arp_block() once a block; the
 * arpeggiator plays through fm_arp_on() and fm_arp_off() (fm_play.c).
 */

#ifndef ARP_H
#define ARP_H

#include "sb.h"

/* The modes (bits 2 to 4 of the patch's FMP_ARP byte). */
enum { ARP_UP, ARP_DOWN, ARP_UPDOWN, ARP_ORDER, ARP_RANDOM, ARP_CHORD, ARP_MODES };
#define ARP_RATES        10u   /* 1/2, 1/4., 1/4, 1/8., 1/8, 1/8T, 1/16., 1/16, 1/16T, 1/32 */
#define ARP_RATE_DEFAULT 7u    /* 1/16 */
#define ARP_GATE_DEFAULT 50u   /* % of a step */
#define ARP_GATE_MIN     10u
#define ARP_GATE_MAX     100u
#define ARP_SWING_MAX    75u   /* %, in steps of 5 */
#define ARP_OCTAVES      4u
#define ARP_TEMPO_MIN    40u   /* beats a minute (the settings' tempo) */
#define ARP_TEMPO_MAX    240u
#define ARP_HELD         16u   /* notes it keeps, the earliest first */
/* A MIDI clock pulse (a 24th of a beat), in the clock's units: at t beats
 * a minute a frame (24 MHz / 544) is t x 24 / 60 x 544 / 24 000 000 =
 * 34 t / 3 750 000 pulses. */
#define ARP_UNIT         3750000u
#define ARP_UNIT_FRAME   34u
/* MIDI clock is lost after this many blocks without a 0xF8: 250 ms (10
 * beats a minute, far below any tempo a sender keeps). */
#define ARP_LOST_BLOCKS  172u

/* The patch's settings, from its bytes (fm.h, FMP_ARP to FMP_ARP_GATE). */
struct arp_patch {
    u8 on, latch, mode, octaves, rate, swing, gate;
};
void arp_patch_of(const u8 *patch, struct arp_patch *a);
/* *to = *from, field by field (the firmware has no memcpy). */
void arp_patch_copy(struct arp_patch *to, const struct arp_patch *from);

/* Takes the playing patch's settings (each block the engine's events
 * changed anything). Turning it on or off is the engine's (fm_play.c:
 * the notes held move between it and the engine). */
void arp_settings(const struct arp_patch *a);
/* Starts it, with nothing held yet (the engine passes the notes held
 * after); stops it: every note it plays ends now, nothing is held. */
void arp_start(void);
void arp_stop(void);
/* 1 while it is on. */
u32 arp_on(void);
/* Nonzero while it is on or follows MIDI clock: the engine calls
 * arp_block() only then, so at rest it costs one test a block. */
extern u32 arp_busy;
/* A note held, or let go (by every one holding it: keys, MIDI, pedal). */
void arp_key(int note, u32 velocity, u32 down);
/* The notes it plays end now (a program or mode change, all sound off). */
void arp_silence(void);
/* A MIDI realtime byte from MIDI in: 0xF8 clock, 0xFA Start, 0xFB
 * Continue, 0xFC Stop (others are ignored), at block `block`. */
void arp_clock(u32 status, u32 block);
/* Once a block, before the voices are rendered: the clock moves on a
 * block, and the steps and gate ends within it play at their frames.
 * block is the audio record's count of blocks so far. */
void arp_block(u32 block);
/* What the screen shows: the clock (0 internal, 1 MIDI), its tempo in
 * tenths of a beat a minute, and the last step's first note (-1 none). */
u32 arp_clock_source(void);
u32 arp_tempo_x10(void);
int arp_last_note(void);
/* The arpeggiator plays through these (fm_play.c): a note on or off at
 * frame `at` of the block (0 to AUDIO_FRAMES - 1). */
void fm_arp_on(int note, u32 velocity, u32 at);
void fm_arp_off(int note, u32 at);
/* And MIDI clock out (a realtime status: 0xF8, 0xFA, 0xFB, 0xFC) while it
 * runs on the internal clock. */
void fm_arp_clock_out(u32 status);

/* The arpeggiator's record, after the interface's at 0x01C008D0
 * (firmware/app.ld), for the tests (tools/arp_suite.py reads this
 * layout). Times are frames since the audio started: the block count x
 * AUDIO_FRAMES + the frame. */
#define ARP_MARKER 0x50524153u   /* "SARP" in memory order */
#define ARP_LOG    32u
struct sb_arp_record {
    u32 marker;
    u32 on;            /* 1 while it is on */
    u32 steps;         /* steps that played a note */
    u32 notes_on;      /* notes it started */
    u32 notes_off;     /* and ended */
    u32 sounding;      /* notes it plays now */
    u32 held;          /* notes it holds now */
    u32 clock;         /* 0: internal; 1: MIDI clock */
    u32 tempo_x10;     /* the clock's tempo, tenths of a beat a minute */
    u32 pulses;        /* MIDI clocks taken while following MIDI clock */
    u32 starts, continues, stops, losses;   /* MIDI Start, Continue, Stop; clocks lost */
    u32 log_count;     /* steps logged so far (the log holds the last ARP_LOG) */
    u32 clocks_out;    /* MIDI clocks (0xF8) sent */
    u32 log_time[ARP_LOG];   /* each step's first note on, in frames */
    u8 log_note[ARP_LOG];    /* and its note (its lowest, for CHORD) */
};
extern volatile struct sb_arp_record sb_arp;

#endif
