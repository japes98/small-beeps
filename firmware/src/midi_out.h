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
 * - Since clean-1027 (BR-8) raw bytes too: midi_out_raw() streams a
 *   buffer through the transmitter as it is (a System Exclusive message,
 *   say), and the queue's messages wait until it has gone, but for
 *   realtime ones (below).
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

/* Raw bytes (since clean-1027, BR-8): sends len bytes from buf through
 * the transmitter as they are, in transfers of up to MIDI_OUT_CHUNK, one
 * whenever the wire is free (midi_out_poll, once a block or more). The
 * queue's messages wait until the last byte has been handed on, except
 * realtime ones (status 0xF8 and up), which go out between two
 * transfers, as MIDI 1.0 lets them do even inside System Exclusive; so
 * they keep their time, a clock's, say. The next message after carries
 * its status (running status starts again). The queue's policy holds
 * meanwhile: a long stream can fill it, and then it drops as it always
 * does (4 096 bytes take 1.3 s of the wire). Returns 1 if it took the
 * buffer, 0 if the last one is still being sent (or len is 0). The
 * buffer must stay as it is until midi_out_raw_busy() returns 0. Call
 * from main's loop (engine.h, sb_engine_serve) or from the block
 * callback, but from one of them only. */
int midi_out_raw(const u8 *buf, u32 len);
int midi_out_raw_busy(void);

/* Raw bytes' counts, for the tests (by its symbol: MIDI out's record
 * keeps its size, as the store's follows it). */
struct sb_midi_out_raw_record {
    u32 streams;        /* buffers taken */
    u32 done;           /* of which wholly handed on */
    u32 bytes;          /* raw bytes handed on */
    u32 realtime;       /* realtime messages sent between a stream's transfers */
};
extern volatile struct sb_midi_out_raw_record sb_midi_out_raw;

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
