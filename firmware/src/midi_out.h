/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * MIDI out (M6b; docs/DESIGN-NOTES.md, M6b): a queue of messages, and the
 * transmitter that drains it through UART1's transmit side (HW-72 to
 * HW-74). On the FM-1 the bytes reach no socket (HW-67); in the app they
 * reach other programs.
 *
 * - The engine's block callback (audio.h) is the only writer and the only
 *   reader: midi_out_send() queues a message, midi_out_poll() sends what
 *   waits. Nothing else touches the queue or the UART's transmit side, so
 *   there is no lock and nothing ever waits for the wire.
 * - The transmitter starts a transfer (transmit DMA: TXADR, then TXCNT)
 *   only when the last one has gone (CON0 bit 15, HW-73), never while one
 *   runs, and never changes the bytes of one that runs. A transfer takes
 *   whole messages, up to MIDI_OUT_CHUNK bytes; the poll comes once at
 *   the start of each block and once after the block's events, so a
 *   message queued then has its first byte on the wire at once if the
 *   wire is free.
 * - Running status: a channel message leaves out its status byte when it
 *   is the one sent last, as long as the transmitter has not run dry; the
 *   first message after the queue emptied and the wire went quiet always
 *   carries its status (so a receiver plugged in meanwhile is never left
 *   guessing). System common messages end running status; realtime
 *   messages don't.
 * - When the wire can't keep up (the policy, docs/DESIGN-NOTES.md, M6b):
 *   a control change, pitch bend, pressure or program change replaces a
 *   waiting one of the same kind, channel (and controller or note), if no
 *   note, mode or other message waits after it; MIDI_OUT_RESERVE places
 *   are kept for note offs (and all notes off, all sound off); any other
 *   message that finds the rest full is dropped and counted. A note off
 *   that finds even the reserve full drops the newest waiting message
 *   that ends no notes instead. A note on dropped either way has its note
 *   off dropped too, so the far end never holds a note it was not sent
 *   and never misses the end of one it was.
 */

#ifndef MIDI_OUT_H
#define MIDI_OUT_H

#include "sb.h"
#include "midi.h"

#define MIDI_OUT_QUEUE   32u   /* messages; at most 96 bytes, 31 ms of the wire */
#define MIDI_OUT_RESERVE 8u    /* of them, kept for note offs */
#define MIDI_OUT_CHUNK   12u   /* the most bytes one transfer takes (3.8 ms) */

/* Queues a message (struct midi_msg, midi.h: a status and 0 to 2 data
 * bytes). Engine callback only. Returns 1 if it was queued or merged with
 * a waiting one, 0 if the policy dropped it. */
int midi_out_send(const struct midi_msg *m);
/* A channel message on the out channel (midi_settings.out_channel). */
int midi_out_channel(u32 kind, u32 d1, u32 d2);
/* Sends what waits, if the wire is free. Engine callback only. */
void midi_out_poll(void);

/* --- The MIDI out record, after MIDI in's (firmware/app.ld) ------------ */
#define MIDI_OUT_MARKER 0x424F444Du   /* "MDOB" in memory order */
struct sb_midi_out_record {
    u32 marker;
    u32 queued;         /* messages queued */
    u32 merged;         /* messages that replaced a waiting one */
    u32 dropped;        /* messages the policy dropped (queue full) */
    u32 offs_dropped;   /* note offs dropped because their note on was */
    u32 offs_lost;      /* note offs dropped: the queue held only note offs */
    u32 waiting_max;    /* the most messages waiting at once */
    u32 messages;       /* messages handed to the wire */
    u32 bytes;          /* bytes handed to the wire */
    u32 running;        /* status bytes left out (running status) */
    u32 transfers;      /* transfers started */
    u32 polls_busy;     /* polls that found a transfer still running */
    u32 thru;           /* messages MIDI thru passed on */
    u32 thru_sysex;     /* System Exclusive messages thru did not pass on */
    u32 panel_notes;    /* note ons the panel sent */
    u32 panel_ccs;      /* control changes the panel's knobs sent */
    u32 panel_programs; /* program changes the panel sent */
    u32 last_note_tick; /* sb_ticks() when the panel's last note on was queued */
    u32 last_start_tick;/* sb_ticks() when the last transfer started */
};
extern volatile struct sb_midi_out_record sb_midi_out;

#endif
