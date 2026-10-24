/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * The FM engine (M5): six operators a voice, our own algorithms, an
 * envelope per operator and one for pitch, polyphony on both cores, mono
 * with legato and glide, and a small versioned patch format. Designed
 * from first principles and public literature (docs/DESIGN-NOTES.md, M5,
 * "The FM engine"; PROVENANCE P-34); the patch format is documented in
 * docs/PATCH-FORMAT.md.
 *
 * fm.c renders voices (either core); fm_play.c is the engine's control
 * side on core 0: events, voice allocation, the controls and the block
 * callback the audio layer calls (audio.h); core1.S and fm_play.c start
 * core 1 and hand it its voices each block.
 */

#ifndef FM_H
#define FM_H

#include "sb.h"
#include "audio.h"

#define FM_OPS        6u
#define FM_VOICES     16u      /* voices in all: even ones core 0's, odd core 1's */
#define FM_ALGORITHMS 10u
#define FM_PATCHES    9u       /* the test patches (patches.c) */

/* --- The patch format, version 1 (docs/PATCH-FORMAT.md) ------------
 * FM_PATCH_BYTES bytes, every field a byte (or two, little-endian), so a
 * patch can be saved (M7) and shared (the app) as it is. */
#define FM_PATCH_BYTES    112u
#define FM_PATCH_VERSION  1u
#define FM_OP_BYTES       13u
#define FM_OP_OFFSET      32u   /* operator 1's first byte; op n at 32 + 13 (n - 1) */
#define FM_SUM_OFFSET     110u  /* the check sum, the last two bytes */

/* Byte offsets of the header's fields. */
#define FMP_MAGIC0     0u   /* 'F' */
#define FMP_MAGIC1     1u   /* 'M' */
#define FMP_VERSION    2u
#define FMP_LENGTH     3u   /* FM_PATCH_BYTES */
#define FMP_NAME       4u   /* 12 bytes of printable ASCII, NUL-padded */
#define FMP_ALGORITHM  16u  /* 1 to FM_ALGORITHMS */
#define FMP_FEEDBACK   17u  /* 0 (none) to 7: the algorithm's feedback operator */
#define FMP_FLAGS      18u  /* bit 0: mono */
#define FMP_GLIDE      19u  /* glide time, a time code (below); 0: none */
#define FMP_TRANSPOSE  20u  /* signed semitones, -24 to 24 */
#define FMP_PITCH_DEPTH 21u /* signed semitones the pitch envelope's 127 means, -48 to 48 */
#define FMP_PITCH_RATE 22u  /* 3 time codes: to P1, to P2 (held), release to P3 */
#define FMP_PITCH_LEVEL 25u /* 4 signed levels P0 (at note on) to P3, -127 to 127 */
/* 29 to 31: reserved, 0 */

/* Operator n's fields, from its first byte. */
#define FMO_MODE       0u   /* 0: ratio of the note's frequency; 1: fixed */
#define FMO_FREQ       1u   /* u16: ratio x 256, or a fixed frequency in 1/4 Hz */
#define FMO_DETUNE     3u   /* signed cents, -100 to 100 */
#define FMO_LEVEL      4u   /* 0 (off) to 127: 2^((level - 127) / 8) */
#define FMO_VELOCITY   5u   /* velocity sensitivity, 0 to 7 */
#define FMO_RATE       6u   /* 4 time codes: attack, decay 1, decay 2, release */
#define FMO_ENV_LEVEL  10u  /* 3 levels, 0 to 127: peak, after decay 1, held */

/* A time code t (0 to 127) is 2^(t / 8) ms, 1 ms to 60.1 s: the time a
 * stage takes over its whole range (docs/DESIGN-NOTES.md, M5). A level
 * step is 2^(1/8), 0.753 dB; 127 is 0 dB. */

/* The key velocity the panel's keys play at (they sense none): MIDI's
 * 100 of 127. M6's MIDI notes bring their own. */
#define FM_KEY_VELOCITY 100u
/* KEY1 plays MIDI note 53 (F3) at octave 0, as M4's (fm_play.c; the
 * panel's screen marks the notes MIDI holds by it, since M6a). */
#define FM_KEY1_NOTE 53

/* --- Rendering (fm.c) ------------------------------------------------ */

/* An operator's envelope stages. */
enum { ENV_ATTACK, ENV_DECAY1, ENV_DECAY2, ENV_HOLD, ENV_RELEASE, ENV_OFF };

struct fm_op {
    u32 phase;      /* 1 / 2^32 of a cycle */
    u32 inc;        /* this block's phase step */
    s32 gain;       /* the gain reached at the end of the last block, 2^-30 */
    s32 y1, y2;     /* the last two outputs (feedback) */
    /* The envelope: the stage, its attenuation in 2^-16 octaves (for the
     * decays and the release) or its linear gain in 2^-30 (the attack). */
    u32 stage;
    s32 att;
    s32 lin;
    /* Set at note on from the patch and the velocity. */
    s32 step[4];    /* per block: attack in 2^-30 of gain, the rest in att */
    s32 target[3];  /* the levels' attenuations */
    s32 fixed_att;  /* the operator's level and velocity, as attenuation */
    u32 freq;       /* ratio x 256, or the fixed phase step */
    u32 fixed;      /* 1: freq is a fixed phase step */
    s32 detune;     /* 2^-30: the detune's factor */
};

/* A voice. Core 0 sets it up and changes it between blocks only; during
 * a block only the core that owns it touches it (DESIGN-NOTES.md, M5,
 * "Two cores"). */
struct fm_voice {
    struct fm_op op[FM_OPS];
    u32 state;      /* VOICE_* (core 0's) */
    u32 algorithm;  /* 0 to FM_ALGORITHMS - 1 */
    s32 fb_now;     /* the feedback multiplier, 2^-8 of a phase shift */
    s32 fb_target;  /* where it goes over the next block */
    s32 mod_att;    /* attenuation added to every modulator (KNOB3) */
    s32 out_att;    /* attenuation of each carrier: log2 of how many sound */
    u32 fade;       /* 1: fade out over the next block (a stolen voice) */
    u32 silent;     /* set by the renderer: every carrier is off */
    u32 fade_done;  /* set by the renderer: the fade is over */
};

enum { VOICE_IDLE, VOICE_ON };

void fm_tables(void);
/* Renders one block of voice v into mix (adding to it, at -12 dBFS a
 * voice at full level), with buf as scratch; called by the core that
 * owns v, each core with its own buf. */
void fm_render(struct fm_voice *v, s32 *mix, s32 (*buf)[AUDIO_FRAMES]);

/* 2^(f / 65536) for f from 0 to 65536, in 2^-30 (1 to 2). */
u32 fm_exp2_frac(u32 f);
/* 2^(-att / 65536), att >= 0, in 2^-30. */
s32 fm_exp2_neg(s32 att);
/* -log2(gain) in 2^-16 octaves, for a gain in 2^-30: fm_exp2_neg's
 * inverse (by bisection; only when a key is released during an attack). */
s32 fm_att_of(s32 gain);
/* The attenuation that shares the output among this many carriers. */
s32 fm_carrier_att(u32 carriers);
/* The sine at a phase (2^-32 of a cycle), 24-bit full scale. */
s32 fm_sine(u32 phase);
/* The phase step of a pitch (1 / 4096 semitone above MIDI note 0). */
u32 fm_pitch_inc(s32 pitch);

/* The algorithms (fm.c): for each operator 1 to 6 (index 0 to 5), where
 * its output goes: another operator (its index, always lower) or
 * FM_TO_OUT; and which operator has the feedback. */
#define FM_TO_OUT 7u
struct fm_algorithm {
    u8 dest[FM_OPS];
    u8 feedback_op;   /* index */
    u8 carriers;      /* how many go to the output */
};
extern const struct fm_algorithm fm_algorithms[FM_ALGORITHMS];

/* --- The test patches (patches.c) ------------------------------------ */
extern const u8 fm_patches[FM_PATCHES][FM_PATCH_BYTES];
/* 1 if p is a well-formed version 1 patch (magic, version, length, check
 * sum, every field in range). */
int fm_patch_valid(const u8 *p);
u32 fm_patch_sum(const u8 *p);

/* --- The user slots (since M7) ---------------------------------------- */
/* Programs: the test patches (0 to FM_PATCHES - 1), then the user slots;
 * a slot is a program once it holds a patch. Main fills the slots from
 * the store at start-up (fm_user_set, fm_program_set: before the audio
 * starts); the engine takes the panel's save and reset and tells main
 * through fm_saved_seq and fm_reset_seq, which main writes to the store
 * (docs/DESIGN-NOTES.md, M7, "The panel"). */
#define FM_USER_SLOTS 16u
#define FM_PROGRAMS   (FM_PATCHES + FM_USER_SLOTS)
/* SAVE held with KEY1 to KEY16: the patch playing now saved to that slot;
 * SAVE and HOME held for FM_RESET_MS: the factory defaults. */
#define FM_RESET_MS   2000u
/* 1 if a valid patch was put in the slot. */
int fm_user_set(u32 slot, const u8 *patch);
/* Selects a program if it is one; 1 if it was. */
int fm_program_set(u32 program);
/* Saves from the panel: for each slot, the engine adds one to
 * fm_saved_seq[slot] each time it saves there, and records in
 * fm_saved_reset[slot] the number of resets so far (fm_reset_seq), so
 * main writes every slot saved, and none a later reset voided; the
 * patch is fm_user_patch(slot). */
extern volatile u32 fm_saved_seq[FM_USER_SLOTS], fm_saved_reset[FM_USER_SLOTS];
/* Added to by the engine at each factory reset from the panel. */
extern volatile u32 fm_reset_seq;
const u8 *fm_user_patch(u32 slot);

/* --- The control side (fm_play.c) ------------------------------------ */
void fm_init(void);
void fm_block(s32 *out, u32 frames);   /* the audio layer's engine callback */
/* A note from anywhere on core 0 (the panel's keys now, MIDI in M6):
 * velocity 1 to 127. */
void fm_note_on(int note, u32 velocity);
void fm_note_off(int note);
/* The notes MIDI or the sustain pedal holds now, bit n % 32 of word
 * n / 32 (since M6a; written by the engine, read by the screen). */
extern volatile u32 fm_midi_notes[4];

/* Core 1 (core1.S, fm_play.c). */
void fm_core1_entry(void);
void fm_core1_main(void) __attribute__((noreturn));

/* The engine's record, at a fixed place right after the audio record
 * (firmware/app.ld), for the tests (tools/fw-suite.py reads this layout). */
#define FM_MARKER 0x354D4653u   /* "SFM5" in memory order */
struct sb_fm_record {
    u32 marker;
    u32 core1;          /* 1 once core 1 runs the engine's loop */
    u32 core1_blocks;   /* blocks core 1 rendered */
    u32 patch;          /* the program new notes take, 0 to FM_PROGRAMS - 1 (since M7) */
    u32 algorithm;      /* its algorithm, 1 to FM_ALGORITHMS (ALGORITHM may change it) */
    u32 mono;           /* 1 in mono mode */
    u32 voices[2];      /* voices sounding on core 0 and core 1, the last block */
    u32 voices_max;     /* the most sounding at once */
    u32 stolen;         /* notes that took a sounding voice */
    u32 notes;          /* notes started */
    u32 wait_max;       /* the longest core 0 waited for core 1, in ticks */
    s32 pitch_knob;     /* KNOB1: semitones */
    u32 glide;          /* the glide time code in force */
    s32 depth;          /* KNOB3: modulator level steps */
    s32 feedback;       /* KNOB4: feedback steps */
};
extern volatile struct sb_fm_record sb_fm;

#endif
