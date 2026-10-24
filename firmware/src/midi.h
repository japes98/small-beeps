/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * MIDI in (M6a; docs/DESIGN-NOTES.md, M6a): bytes from the receiver into
 * a ring, our own MIDI 1.0 byte parser, and the settings MIDI uses (the
 * receive channel, the pitch bend range, the controller map), kept in one
 * struct that M7 can save as it is.
 *
 * - The receiver calls midi_rx_byte() for each byte, from its interrupt.
 * - The engine takes whole messages with midi_read(), from its block
 *   callback (audio.h), so MIDI and the panel's events reach it in the
 *   same place; fm_play.c acts on them.
 * - The parser never stalls: running status; realtime bytes anywhere,
 *   even inside another message, without disturbing it; System Exclusive
 *   skipped, however long, ended by any status byte; data bytes with no
 *   status, undefined status bytes and stray EOX dropped and counted.
 */

#ifndef MIDI_H
#define MIDI_H

#include "sb.h"

/* A message as the parser hands it on: a channel message's status (its
 * kind in the high nibble, its channel 0 to 15 in the low) and data
 * bytes, or a realtime or system common status with its data. */
struct midi_msg {
    u8 status;
    u8 data[2];
    u8 length;     /* data bytes: 0 to 2 */
};

/* Message kinds (a channel status's high nibble). */
#define MIDI_NOTE_OFF   0x80u
#define MIDI_NOTE_ON    0x90u
#define MIDI_POLY_AT    0xA0u
#define MIDI_CC         0xB0u
#define MIDI_PROGRAM    0xC0u
#define MIDI_CHANNEL_AT 0xD0u
#define MIDI_BEND       0xE0u
#define MIDI_SYSEX      0xF0u
#define MIDI_EOX        0xF7u
#define MIDI_RESET      0xFFu

/* The receive ring: MIDI_RING bytes, a power of two. At the wire's pace
 * (3 125 bytes a second) a block brings at most 5; when the ring is full,
 * new bytes are dropped (the oldest kept) and counted. */
#define MIDI_RING 256u

/* A System Exclusive message is skipped a byte at a time; past this many
 * data bytes it is counted as too long (the bytes are still skipped). */
#define MIDI_SYSEX_LIMIT 4096u

/* Called by the receiver's interrupt for each byte it takes. */
void midi_rx_byte(u8 b);
/* Parses the bytes received so far into *m, one message at a time: 1, or
 * 0 when no whole message is waiting. Engine callback only (one reader). */
int midi_read(struct midi_msg *m);
/* Parses one byte: 1 when it completes a message, put in *m. */
int midi_parse(u8 b, struct midi_msg *m);
/* Back to the state at power on: no running status, no SysEx. */
void midi_parser_reset(void);

/* The notes MIDI plays, for the screen: the engine posts each note on and
 * off, main takes them (MIDI_SCREEN of them; when full, new ones are
 * dropped). A note is channel << 16 | note << 8 | velocity (0: off). */
#define MIDI_SCREEN 16u
void midi_screen_post(u32 channel, int note, u32 velocity);
int midi_screen_take(u32 *note);

/* --- Settings (stored as they are by M7) ------------------------------- */

/* Where a controller change goes (docs/DESIGN-NOTES.md, M6a, "The
 * controller map"). M8 adds targets and changes the map; MIDI learn will
 * write it. */
enum {
    MIDI_TO_NONE,
    MIDI_TO_MOD,          /* vibrato depth */
    MIDI_TO_VOLUME,
    MIDI_TO_EXPRESSION,
    MIDI_TO_SUSTAIN,
    MIDI_TO_KNOB1,        /* the engine's four controls, as KNOB1 to KNOB4 */
    MIDI_TO_KNOB2,
    MIDI_TO_KNOB3,
    MIDI_TO_KNOB4,
    MIDI_TARGETS
};

#define MIDI_SETTINGS_VERSION 1u
#define MIDI_OMNI             0u     /* channel: receive on every channel */
#define MIDI_CC_ROUTES        16u

struct midi_settings {
    u8 version;           /* MIDI_SETTINGS_VERSION */
    u8 channel;           /* MIDI_OMNI, or 1 to 16 */
    u8 bend_range;        /* semitones each way, 0 to 24 */
    u8 routes;            /* entries of cc[] in use */
    struct {
        u8 cc;            /* 0 to 119 */
        u8 to;            /* MIDI_TO_* */
    } cc[MIDI_CC_ROUTES];
};
_Static_assert(sizeof(struct midi_settings) == 4 + 2 * MIDI_CC_ROUTES, "settings are bytes");

extern struct midi_settings midi_settings;
/* The defaults: omni, a bend of 2 semitones, the default map. */
void midi_settings_default(struct midi_settings *s);

/* --- The MIDI record, after the engine's (firmware/app.ld) ------------ */
#define MIDI_MARKER 0x3649444Du   /* "MDI6" in memory order */
#define MIDI_LOG    64u
struct sb_midi_record {
    u32 marker;
    u32 bytes;          /* bytes received */
    u32 ring_dropped;   /* bytes dropped: the ring was full */
    u32 parsed;         /* bytes the parser took */
    u32 messages;       /* messages it completed (realtime included) */
    u32 realtime;       /* of which realtime */
    u32 sysex;          /* SysEx messages begun */
    u32 sysex_bytes;    /* their data bytes, skipped */
    u32 sysex_long;     /* SysEx messages past MIDI_SYSEX_LIMIT */
    u32 sysex_cut;      /* SysEx ended by a status other than EOX */
    u32 orphans;        /* data bytes with no status to belong to */
    u32 undefined;      /* undefined status bytes (F4, F5, F9, FD) and stray EOX */
    u32 cut;            /* channel or common messages a status byte cut short */
    u32 filtered;       /* channel messages for another channel */
    u32 notes_on;       /* note ons the engine took (velocity > 0) */
    u32 notes_off;      /* note offs, and note ons at velocity 0 */
    u32 held;           /* notes MIDI holds now (key or pedal) */
    u32 pedal;          /* 1 while the sustain pedal is down */
    s32 bend;           /* the pitch bend now, in 1/4096 semitone */
    u32 mod;            /* the mod wheel, 0 to 127 */
    u32 volume;         /* CC7 */
    u32 expression;     /* CC11 */
    u32 program;        /* the last program change taken, or 0xFFFFFFFF */
    u32 last_note_tick; /* sb_ticks() when the last note on was taken */
    u32 log_count;      /* messages logged; the last is log[(log_count - 1) % MIDI_LOG] */
    /* Each message the parser completed, realtime too: status, data 1,
     * data 2, length, in that byte order. */
    u8 log[MIDI_LOG][4];
};
extern volatile struct sb_midi_record sb_midi;

#endif
