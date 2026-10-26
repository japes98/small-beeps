/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * The FM engine's control side (M5; docs/DESIGN-NOTES.md, M5): the block
 * callback, run by core 0 in the audio interrupt. Each block it takes the
 * panel's events (notes, the controls), moves each voice's pitch on
 * (glide, the pitch envelope, KNOB1) and sets its operators' phase steps,
 * then hands core 1 its voices, renders its own, waits for core 1 and
 * mixes. Voice allocation and stealing, mono with legato and glide, and
 * M4's test tone on PLAY are here too. Core 1 runs fm_core1_main.
 * Since M6a MIDI's messages arrive here too, after the panel's events
 * (docs/DESIGN-NOTES.md, M6a): notes from both, held apart so neither
 * ends the other's, the sustain pedal, pitch bend, vibrato, the
 * controller map, program changes and the channel modes.
 * Since M6b the panel's notes, knobs and program changes go to MIDI out,
 * MIDI thru passes on what MIDI in receives, and local control off keeps
 * the panel from playing the engine (docs/DESIGN-NOTES.md, M6b).
 */

#include "fm.h"
#include "arp.h"
#include "input.h"
#include "midi.h"
#include "midi_out.h"
#include "ui.h"

volatile struct sb_fm_record sb_fm __attribute__((section(".beacon.fm")));
/* The interface's state (M8a; ui.h): the engine's, since it takes the
 * panel's events in order; main draws it. */
volatile struct fm_ui fm_ui;

/* --- Shared between the cores (DESIGN-NOTES.md, M5, "Two cores") -----
 * Core 0 changes the voices only between blocks, and core 1 renders its
 * own voices only during one: core 0 posts a block by raising job_seq,
 * core 1 answers with job_done. Each shared load follows csync, and the
 * sequence numbers change under the lock, the SDK's way (HW-65). */
static struct fm_voice voice[FM_VOICES];
static s32 mix[2][AUDIO_FRAMES];
static s32 scratch[2][FM_OPS + 1][AUDIO_FRAMES];
static volatile u32 job_seq, job_done, core1_running;
static volatile u8 job_lock;

/* HW-65: test-and-set the byte until it was clear, csync around. */
static void lock(volatile u8 *b)
{
    __asm__ volatile("csync\n"
                     "1:\n\t"
                     "testset b[%0]\n\t"
                     "ifeq goto 1b\n\t"
                     "csync" : : "r"(b) : "memory");
}

static void unlock(volatile u8 *b)
{
    __asm__ volatile("csync" : : : "memory");
    *b = 0;
}

static u32 shared(volatile u32 *p)
{
    __asm__ volatile("csync" : : : "memory");
    return *p;
}

static void publish(volatile u32 *p, u32 v)
{
    lock(&job_lock);
    *p = v;
    unlock(&job_lock);
}

/* Core 1: renders the odd voices whenever core 0 posts a block. Its loop
 * changes nothing while it waits, so fwtest ends its turns early
 * (HW-64). */
void fm_core1_main(void)
{
    u32 seen = 0;

    publish(&core1_running, 1);
    sb_fm.core1 = 1;
    for (;;) {
        u32 s = shared(&job_seq), n, v;
        if (s == seen)
            continue;
        seen = s;
        for (n = 0; n < AUDIO_FRAMES; n++)
            mix[1][n] = 0;
        for (v = 1; v < FM_VOICES; v += 2)
            if (voice[v].state == VOICE_ON)
                fm_render(&voice[v], mix[1], scratch[1]);
        sb_fm.core1_blocks++;
        publish(&job_done, s);
    }
}

/* HW-9: core 1 starts at the address in this word (also source 126's
 * vector) once bit 3 of C1_CON is set. */
#define CORE1_START (*(volatile u32 *)0x01C7FFF8u)
#define C1_CON      (*(volatile u32 *)0x01EEE004u)
#define CORE1_WAIT  100000u     /* polls of its flag, about 1 ms in fwtest */

static u32 two_cores;

/* --- Core 0's own state ----------------------------------------------- */

/* A patch as the engine uses it, from its bytes. */
struct patch {
    u32 algorithm, feedback, mono, glide;
    s32 transpose, pitch_depth;
    s32 pitch_step[3], pitch_level[4];   /* 2^-16 of a level, a block */
    struct {
        u32 off, fixed, freq;
        s32 detune, level_att, velocity;
        s32 step[4], target[3];
    } op[FM_OPS];
};

/* What core 0 keeps for each voice. */
struct control {
    int note;          /* the note sounding */
    u32 held;          /* its key is down */
    u32 age;           /* when it began, in notes started */
    int next;          /* a note waiting for this voice's fade, or -1 */
    u32 next_velocity, next_held;
    const struct patch *patch;
    s32 pitch;         /* 1 / 4096 semitone above MIDI note 0, glide included */
    s32 glide_to, glide_step;
    u32 glide_left;    /* blocks */
    u32 pitch_stage;   /* 0 toward P1, 1 toward P2 (then held), 2 released */
    s32 pitch_level;   /* the pitch envelope, 2^-16 of a level */
    u32 release_next;  /* since ARP: released within the block it started in, so at the next */
};

static struct control ctl[FM_VOICES];
static struct patch patches[FM_PROGRAMS];
/* The user slots' patches as bytes, and which slots hold one (since M7). */
static u8 user_raw[FM_USER_SLOTS][FM_PATCH_BYTES];
/* The program playing now as bytes, with the operator view's edits, and
 * whether there are any (M8a part 3). */
static u8 edit_raw[FM_PATCH_BYTES];
static u32 edited;
/* Each operator's loudest gain now (2^-30), while the operator view shows
 * (ui.h); main draws them. */
volatile s32 fm_op_level[FM_OPS];
/* The envelope view's live dot (M8a part 4): where the last note started
 * is in the envelope shown, while ENV shows. */
volatile struct fm_env_dot fm_env_dot;
static u32 user_used;
volatile u32 fm_saved_seq[FM_USER_SLOTS], fm_saved_reset[FM_USER_SLOTS];
volatile u32 fm_reset_seq;
static u32 patch_now, algorithm_now, mono, started;
static u32 sounding;        /* voices not idle */
static int octave, mono_stack[16];
static u32 mono_held;
static s32 master;
static int key_note[27];   /* the note each key started; -1: none */
/* The controls this block: KNOB1 to KNOB4 (DESIGN-NOTES.md, M5, "The
 * controls"). */
static s32 pitch_knob, depth_att;
static u32 glide_code;
static int feedback_knob;

/* Who holds each note (M6a): the panel's keys, MIDI, the sustain pedal.
 * The engine hears a note's off only when none holds it any more. */
#define HOLD_PANEL 1u
#define HOLD_MIDI  2u
#define HOLD_PEDAL 4u
static u8 hold[128];
volatile u32 fm_midi_notes[4];   /* notes MIDI or the pedal holds, for the screen */
/* Since ARP: each note's last velocity, for the notes held when the
 * arpeggiator starts or stops. */
static u8 note_velocity[128];

/* A note now held, or no longer held by anything: to the engine, or
 * while it runs to the arpeggiator (since ARP), whose own notes reach
 * the engine through fm_arp_on and fm_arp_off, past hold[]. */
static void held_on(int note, u32 velocity, u32 was)
{
    note_velocity[note] = (u8)velocity;
    if (!arp_on())
        fm_note_on(note, velocity);
    else if (!was)
        arp_key(note, velocity, 1);
}

static void held_off(int note)
{
    if (arp_on())
        arp_key(note, 0, 0);
    else
        fm_note_off(note);
}

/* MIDI's controls: the pitch bend and vibrato (1 / 4096 semitone), the
 * levels (0 to 127), the pedal, the four knobs' offsets (in their own
 * steps), and the parameter number data entry changes (RPN; 0x3FFF:
 * none). */
static s32 bend, vibrato;
static u32 mod_wheel, volume = 127, expression = 127, pedal;
static int midi_knob[4];
/* The panel's KNOB1 to KNOB4 as the engine last took them: frozen while
 * local control is off (M6b). The program the panel's PRESETS last chose. */
static int panel_knob[4];
/* Since M8a: KNOB1 to KNOB4's positions as the patch view's controls,
 * moved only by turns there and held to the span (so turning back from
 * past an end answers at once); the other screens' turns edit instead. */
static int knob_pos[4];
/* midi_settings.knobs as knobs() last took it (M8a): 0 the macros. */
static u32 knobs_mode;
static u32 panel_program;
static u32 lfo_phase, rpn = 0x3FFFu;
/* Since ARP: the keys whose note on MIDI out sent (bit k for KEY k + 1),
 * and the ARP button: held now, held long enough for its screen, since. */
static u32 key_sent, arp_down, arp_long, arp_pressed;
volatile u32 fm_arp_toggles;
#define ARP_HOLD_TICKS (500u * 24000u)   /* 500 ms of the time base */

#define OCTAVES   2
#define SEMITONE  4096

/* The per-block steps of a stage taking 1 ms over its whole range
 * (fm.h's time codes), computed offline for 64 frames at 24 MHz / 544:
 * 16 octaves of attenuation (2^-16), a gain of 1 (2^-30), the pitch
 * envelope's 254 levels (2^-16). */
#define STEP_ATT  1521134u
#define STEP_LIN  1557641473u
#define STEP_LVL  24148006u
/* A fixed frequency's phase step, a quarter hertz's, in 2^-16. */
#define FIXED_Q16 1595024868u
/* A block, in milliseconds, in 2^-16: 64 x 544 / 24 000 x 65536. */
#define BLOCK_MS_Q16 95072u
#define GAIN_ONE  (1 << 30)
/* The vibrato's phase step a block: 5.5 Hz at 44 117.647 / 64 blocks a
 * second, in 2^-32 of a cycle. */
#define LFO_INC   34268112u

/* A stage's step a block: 2^(-code / 8) of the 1 ms one. */
static s32 step_of(u32 code, u32 full)
{
    return (s32)(((u64)full * (u32)fm_exp2_neg((s32)(code << 13))) >> 30);
}

/* How many blocks a time code is: 2^(code / 8) ms over a block's. */
static u32 blocks_of(u32 code)
{
    u64 ms_q30 = (u64)fm_exp2_frac((code & 7u) << 13) << (code >> 3);
    u32 n = (u32)(ms_q30 >> 14) / BLOCK_MS_Q16;

    return n ? n : 1;
}

static int signed8(u8 x)
{
    return x > 127 ? (int)x - 256 : (int)x;
}

static void patch_parse(struct patch *p, const u8 *b)
{
    u32 i, k;

    p->algorithm = b[FMP_ALGORITHM] - 1u;
    p->feedback = b[FMP_FEEDBACK];
    p->mono = b[FMP_FLAGS] & 1u;
    p->glide = b[FMP_GLIDE];
    p->transpose = signed8(b[FMP_TRANSPOSE]);
    p->pitch_depth = signed8(b[FMP_PITCH_DEPTH]);
    for (i = 0; i < 3; i++)
        p->pitch_step[i] = step_of(b[FMP_PITCH_RATE + i], STEP_LVL);
    for (i = 0; i < 4; i++)
        p->pitch_level[i] = signed8(b[FMP_PITCH_LEVEL + i]) * 65536;
    for (i = 0; i < FM_OPS; i++) {
        const u8 *o = b + FM_OP_OFFSET + FM_OP_BYTES * i;
        u32 f = (u32)o[FMO_FREQ] | (u32)o[FMO_FREQ + 1] << 8;
        int cents = signed8(o[FMO_DETUNE]);
        p->op[i].off = o[FMO_LEVEL] == 0;
        p->op[i].fixed = o[FMO_MODE] == 1;
        p->op[i].freq = p->op[i].fixed ? (u32)(((u64)f * FIXED_Q16) >> 16) : f;
        /* 2^(cents / 1200), in 2^-30. */
        p->op[i].detune = cents >= 0 ? (s32)fm_exp2_frac((u32)(cents * 65536 / 1200))
                                     : fm_exp2_neg(-cents * 65536 / 1200);
        p->op[i].level_att = (s32)(127u - o[FMO_LEVEL]) << 13;
        p->op[i].velocity = o[FMO_VELOCITY];
        p->op[i].step[0] = step_of(o[FMO_RATE], STEP_LIN);
        for (k = 1; k < 4; k++)
            p->op[i].step[k] = step_of(o[FMO_RATE + k], STEP_ATT);
        for (k = 0; k < 3; k++)
            p->op[i].target[k] = (s32)(127u - o[FMO_ENV_LEVEL + k]) << 13;
    }
}

int fm_patch_valid(const u8 *b)
{
    u32 i, k;

    if (b[FMP_MAGIC0] != 'F' || b[FMP_MAGIC1] != 'M' || b[FMP_VERSION] != FM_PATCH_VERSION
        || b[FMP_LENGTH] != FM_PATCH_BYTES)
        return 0;
    for (i = FMP_NAME; i < FMP_NAME + 12; i++)
        if (b[i] && (b[i] < 32 || b[i] > 126))
            return 0;
    if (b[FMP_ALGORITHM] < 1 || b[FMP_ALGORITHM] > FM_ALGORITHMS || b[FMP_FEEDBACK] > 7
        || b[FMP_FLAGS] > 1 || b[FMP_GLIDE] > 127)
        return 0;
    if (signed8(b[FMP_TRANSPOSE]) < -24 || signed8(b[FMP_TRANSPOSE]) > 24
        || signed8(b[FMP_PITCH_DEPTH]) < -48 || signed8(b[FMP_PITCH_DEPTH]) > 48)
        return 0;
    for (i = 0; i < 3; i++)
        if (b[FMP_PITCH_RATE + i] > 127)
            return 0;
    for (i = 0; i < 4; i++)
        if (signed8(b[FMP_PITCH_LEVEL + i]) < -127)
            return 0;
    if ((b[FMP_ARP] >> 2 & 7u) > 5u || (b[FMP_ARP] & 0x80u) || (b[FMP_ARP_RATE] & 15u) > 9u
        || b[FMP_ARP_GATE] < 10 || b[FMP_ARP_GATE] > 100)
        return 0;
    for (i = 0; i < FM_OPS; i++) {
        const u8 *o = b + FM_OP_OFFSET + FM_OP_BYTES * i;
        if (o[FMO_MODE] > 1 || signed8(o[FMO_DETUNE]) < -100 || signed8(o[FMO_DETUNE]) > 100
            || o[FMO_LEVEL] > 127 || o[FMO_VELOCITY] > 7)
            return 0;
        for (k = FMO_RATE; k < FM_OP_BYTES; k++)
            if (o[k] > 127)
                return 0;
    }
    return fm_patch_sum(b) == ((u32)b[FM_SUM_OFFSET] | (u32)b[FM_SUM_OFFSET + 1] << 8);
}

int fm_patch_upgrade(u8 *b)
{
    u32 sum;

    if (b[FMP_MAGIC0] == 'F' && b[FMP_MAGIC1] == 'M' && b[FMP_VERSION] == 1u && b[FMP_LENGTH] == FM_PATCH_BYTES
        && !b[FMP_ARP] && !b[FMP_ARP_RATE] && !b[FMP_ARP_GATE]
        && fm_patch_sum(b) == ((u32)b[FM_SUM_OFFSET] | (u32)b[FM_SUM_OFFSET + 1] << 8)) {
        b[FMP_VERSION] = FM_PATCH_VERSION;
        b[FMP_ARP_RATE] = ARP_RATE_DEFAULT;
        b[FMP_ARP_GATE] = ARP_GATE_DEFAULT;
        sum = fm_patch_sum(b);
        b[FM_SUM_OFFSET] = (u8)sum;
        b[FM_SUM_OFFSET + 1] = (u8)(sum >> 8);
    }
    return fm_patch_valid(b);
}

/* Fletcher's 16-bit check sum of the bytes before it. */
u32 fm_patch_sum(const u8 *b)
{
    u32 a = 0, c = 0, i;

    for (i = 0; i < FM_SUM_OFFSET; i++) {
        a = (a + b[i]) % 255u;
        c = (c + a) % 255u;
    }
    return c << 8 | a;
}

/* --- The macros (M8a; docs/M8-PROPOSAL.md, docs/DESIGN-NOTES.md) ------
 * KNOB1 to KNOB4 on the patch view, unless the setting "Knobs: direct"
 * (midi_settings.knobs) gives them M5's controls. Each moves several of
 * the patch's values at once as an offset over the stored patch, so at 0
 * the patch sounds exactly as stored, and turning it back returns there:
 * - BRIGHT: every modulator's level (M5's KNOB3, renamed);
 * - COLOR: the modulators' ratios, from whole numbers (below 0, each
 *   moved toward its nearest whole number, or a half) to inharmonic (above
 *   0, each multiplied by up to the square root of 2, the same sweep on
 *   every patch), and feedback up to 3 steps more at the metallic end;
 * - SHAPE: the carriers' envelopes, from a pluck (below 0: a fast attack,
 *   a short decay, a quick release, the held level falling away) to a pad
 *   (above 0: a slow attack, full sustain, a long release);
 * - MOTION: vibrato (5.5 Hz, up to half a semitone) and a detune spread
 *   across the carriers (the first in tune, the others up to 12 cents
 *   above and below it in turn).
 * The operators' values with COLOR and SHAPE applied are worked out once
 * a change (shape_ops), not each note or block. */
#define MACRO_BRIGHT 0
#define MACRO_COLOR  1
#define MACRO_SHAPE  2
#define MACRO_MOTION 3
static int macro[4];
/* Each macro's range, and MIDI's controllers 16 to 19 over it (64: 0):
 * MOTION has nothing below 0, so a controller's 0 to 64 are all 0. */
static const s8 macro_span[4][2] = { { -64, 32 }, { -32, 32 }, { -64, 64 }, { 0, 64 } };
/* The operators as notes take them now: the patch's, with COLOR and SHAPE. */
static struct fm_op_shape shaped[FM_OPS];
/* MOTION's detune factor for each operator, 2^-30 (1 for a modulator). */
static s32 spread[FM_OPS];
/* What shaped[] was worked out for. */
static u32 shaped_patch = 0xFFFFFFFFu, shaped_algorithm;
static int shaped_color, shaped_shape, shaped_motion;

static int toward(int from, int to, int t)
{
    return from + (to - from) * t / 64;
}

/* COLOR on a ratio (x 256). */
static u32 color_ratio(u32 f, int c)
{
    s32 h;

    if (c > 0)   /* x 2^(c / 64): up to the square root of 2 at 32 */
        return (u32)(((u64)f * fm_exp2_frac((u32)c << 10)) >> 30);
    h = (s32)((f + 128u) & ~255u);
    if (!h)
        h = 128;
    return (u32)((s32)f + (h - (s32)f) * -c / 32);
}

static void shape_ops(void)
{
    const struct patch *p = &patches[patch_now];
    const u8 *raw = fm_program_bytes();
    const struct fm_algorithm *a = &fm_algorithms[algorithm_now];
    int color = macro[MACRO_COLOR], shape = macro[MACRO_SHAPE], motion = macro[MACRO_MOTION];
    u32 i, k, n, side = 0;

    for (i = 0; i < FM_OPS; i++) {
        const u8 *o = raw + FM_OP_OFFSET + FM_OP_BYTES * i;
        u32 carrier = a->dest[i] == FM_TO_OUT;

        shaped[i].freq = p->op[i].freq;
        for (k = 0; k < 4; k++)
            shaped[i].step[k] = p->op[i].step[k];
        for (k = 0; k < 3; k++)
            shaped[i].target[k] = p->op[i].target[k];
        spread[i] = GAIN_ONE;
        if (!carrier && !p->op[i].fixed && color)
            shaped[i].freq = color_ratio(p->op[i].freq, color);
        if (carrier && shape) {
            int r[4], l[3], t = shape < 0 ? -shape : shape;
            for (k = 0; k < 4; k++)
                r[k] = o[FMO_RATE + k];
            for (k = 0; k < 3; k++)
                l[k] = o[FMO_ENV_LEVEL + k];
            if (shape < 0) {
                r[0] = toward(r[0], 0, t);
                r[1] = toward(r[1], 56, t);
                r[2] = toward(r[2], 72, t);
                r[3] = toward(r[3], 48, t);
                l[1] = toward(l[1], 96, t);
                l[2] = toward(l[2], 0, t);
            } else {
                r[0] = toward(r[0], 80, t);
                r[3] = toward(r[3], 96, t);
                l[1] = toward(l[1], 127, t);
                l[2] = toward(l[2], 127, t);
            }
            shaped[i].step[0] = step_of((u32)r[0], STEP_LIN);
            for (k = 1; k < 4; k++)
                shaped[i].step[k] = step_of((u32)r[k], STEP_ATT);
            for (k = 0; k < 3; k++)
                shaped[i].target[k] = (s32)(127 - l[k]) << 13;
        }
        if (carrier && motion) {
            /* The first carrier stays in tune; the others alternately
             * above and below it. */
            int cents = side ? motion * 12 / 64 : 0;
            if (side && !(side & 1))
                cents = -cents;
            side++;
            spread[i] = cents >= 0 ? (s32)fm_exp2_frac((u32)(cents * 65536 / 1200))
                                   : fm_exp2_neg(-cents * 65536 / 1200);
        }
    }
    /* The notes sounding take COLOR's ratios at once. */
    for (n = 0; n < FM_VOICES; n++)
        if (voice[n].state == VOICE_ON && ctl[n].patch == p && voice[n].algorithm == algorithm_now)
            for (i = 0; i < FM_OPS; i++)
                if (!voice[n].op[i].fixed)
                    voice[n].op[i].freq = shaped[i].freq;
    shaped_patch = patch_now;
    shaped_algorithm = algorithm_now;
    shaped_color = color;
    shaped_shape = shape;
    shaped_motion = motion;
}

/* shaped[] for the patch, algorithm and macros now. */
static void ensure_shaped(void)
{
    if (shaped_patch != patch_now || shaped_algorithm != algorithm_now || shaped_color != macro[MACRO_COLOR]
        || shaped_shape != macro[MACRO_SHAPE] || shaped_motion != macro[MACRO_MOTION])
        shape_ops();
}

/* --- Notes ------------------------------------------------------------ */

/* Starts note on voice n from the current patch. A free voice starts from
 * silence at phase 0; one still sounding (the same note again, or mono)
 * keeps its phases and starts its attacks from where its envelopes are,
 * so neither clicks. Since ARP the start may fall at frame `at` of the
 * block (0: its start): the renderer takes it there (fm.h, pending); a
 * release pending before it in the block is dropped. */
static void voice_start(u32 n, int note, u32 velocity, u32 at)
{
    struct fm_voice *v = &voice[n];
    struct control *c = &ctl[n];
    const struct patch *p = &patches[patch_now];
    u32 i, k, fresh = v->state != VOICE_ON, carriers = 0, stage = !fresh && at;
    /* Velocity: up to 8 octaves (48 dB) less at velocity 0, for a
     * sensitivity of 7, in proportion below (DESIGN-NOTES.md, M5). */
    s32 soft = (s32)(127u - velocity) * (8 * 65536 / 7) / 127;

    c->patch = p;
    c->note = note;
    c->held = 1;
    c->next = -1;
    c->age = started++;
    c->pitch = (note + p->transpose) * SEMITONE;
    c->glide_left = 0;
    c->pitch_stage = 0;
    c->pitch_level = p->pitch_level[0];
    c->release_next = 0;
    ensure_shaped();
    if (stage) {
        v->next_shape = shaped;
        v->next_off = 0;
    }
    for (i = 0; i < FM_OPS; i++) {
        struct fm_op *o = &v->op[i];
        if (stage) {
            /* Still sounding until `at`: its envelopes and levels kept
             * for the renderer (fm.h, pending), its frequency now. */
            o->fixed = p->op[i].fixed;
            o->freq = shaped[i].freq;
            o->detune = p->op[i].detune;
            v->next_att[i] = p->op[i].level_att + soft * p->op[i].velocity;
            v->next_off |= p->op[i].off << i;
            carriers += !p->op[i].off && fm_algorithms[algorithm_now].dest[i] == FM_TO_OUT;
            continue;
        }
        if (fresh) {
            o->phase = 0;
            o->gain = 0;
            o->y1 = o->y2 = 0;
            o->lin = 0;
        } else if (o->stage != ENV_ATTACK) {
            o->lin = o->stage == ENV_OFF ? 0 : fm_exp2_neg(o->att);
        }
        o->fixed = p->op[i].fixed;
        o->freq = shaped[i].freq;
        o->detune = p->op[i].detune;
        o->fixed_att = p->op[i].level_att + soft * p->op[i].velocity;
        for (k = 0; k < 4; k++)
            o->step[k] = shaped[i].step[k];
        for (k = 0; k < 3; k++)
            o->target[k] = shaped[i].target[k];
        o->stage = p->op[i].off ? ENV_OFF : ENV_ATTACK;
        carriers += !p->op[i].off && fm_algorithms[algorithm_now].dest[i] == FM_TO_OUT;
    }
    if (stage) {
        v->next_algorithm = algorithm_now;
        v->next_out_att = fm_carrier_att(carriers);
        v->pending = FM_PENDING_START;
        v->at = at;
    } else {
        v->algorithm = algorithm_now;
        v->out_att = fm_carrier_att(carriers);
        v->pending = fresh && at ? FM_PENDING_FRESH : FM_PENDING_NONE;
        v->at = at;
    }
    if (fresh) {
        v->fb_now = 0;
        sounding++;
    }
    v->fade = 0;
    v->fade_done = 0;
    v->silent = 0;
    v->state = VOICE_ON;
    sb_fm.notes++;
    if (!sb_audio.engine[SYNTH_NOTES])
        sb_audio.engine[SYNTH_FIRST_ON] = sb_audio.blocks;
    sb_audio.engine[SYNTH_NOTES]++;
}

/* Since ARP at frame `at` of the block (0: its start); a note whose start
 * is still pending in this block is released at the next. */
static void voice_release(u32 n, u32 at)
{
    struct fm_voice *v = &voice[n];
    u32 i;

    ctl[n].held = 0;
    if (v->pending == FM_PENDING_FRESH || v->pending == FM_PENDING_START) {
        ctl[n].release_next = 1;
        return;
    }
    ctl[n].pitch_stage = 2;
    if (at) {
        if (v->pending == FM_PENDING_NONE) {
            v->pending = FM_PENDING_RELEASE;
            v->at = at;
        }
        return;
    }
    v->pending = FM_PENDING_NONE;
    for (i = 0; i < FM_OPS; i++) {
        struct fm_op *o = &v->op[i];
        if (o->stage == ENV_OFF)
            continue;
        if (o->stage == ENV_ATTACK)
            o->att = fm_att_of(o->lin);
        o->stage = ENV_RELEASE;
    }
}

/* The loudest a voice's carriers are now, to choose which to steal. */
static s32 loudness(u32 n)
{
    const struct fm_algorithm *a = &fm_algorithms[voice[n].algorithm];
    s32 g = 0;
    u32 i;

    for (i = 0; i < FM_OPS; i++)
        if (a->dest[i] == FM_TO_OUT && voice[n].op[i].gain > g)
            g = voice[n].op[i].gain;
    return g;
}

/* Poly: the same note again takes its own voice back; else a free voice,
 * on the core with fewer sounding; else the quietest released voice;
 * else the oldest. A voice taken while it sounds fades out over one block
 * first, and the new note starts the block after (DESIGN-NOTES.md, M5,
 * "Voices"). */
static void poly_on(int note, u32 velocity, u32 at)
{
    u32 n, pick = FM_VOICES, load[2] = { 0, 0 };

    for (n = 0; n < FM_VOICES; n++)
        if (voice[n].state == VOICE_ON) {
            load[n & 1]++;
            if (ctl[n].note == note && ctl[n].next < 0 && !voice[n].fade)
                pick = n;
        }
    if (pick < FM_VOICES) {
        voice_start(pick, note, velocity, at);
        return;
    }
    for (n = 0; n < FM_VOICES; n++) {
        if (voice[n].state == VOICE_ON || (!two_cores && (n & 1)))
            continue;
        if (pick == FM_VOICES || (two_cores && load[n & 1] < load[pick & 1]))
            pick = n;
    }
    if (pick < FM_VOICES) {
        voice_start(pick, note, velocity, at);
        return;
    }
    for (n = 0; n < FM_VOICES; n++) {
        if (voice[n].fade || ctl[n].held || (!two_cores && (n & 1)))
            continue;
        if (pick == FM_VOICES || loudness(n) < loudness(pick))
            pick = n;
    }
    if (pick == FM_VOICES)
        for (n = 0; n < FM_VOICES; n++) {
            if (voice[n].fade || (!two_cores && (n & 1)))
                continue;
            if (pick == FM_VOICES || ctl[n].age < ctl[pick].age)
                pick = n;
        }
    if (pick == FM_VOICES)
        return;   /* every voice is already fading for another note */
    voice[pick].fade = 1;
    ctl[pick].next = note;
    ctl[pick].next_velocity = velocity;
    ctl[pick].next_held = 1;
    ctl[pick].held = 0;
    sb_fm.stolen++;
    sb_audio.engine[SYNTH_STOLEN]++;
}

static void glide_to(u32 n, int note)
{
    struct control *c = &ctl[n];
    s32 to = (note + c->patch->transpose) * SEMITONE;

    c->note = note;
    if (!glide_code) {
        c->pitch = to;
        c->glide_left = 0;
        return;
    }
    c->glide_to = to;
    c->glide_left = blocks_of(glide_code);
    c->glide_step = (to - c->pitch) / (s32)c->glide_left;
}

/* Mono: one voice, the last note held sounds. A note while another is
 * held glides to it without starting the envelopes again (legato);
 * releasing it goes back to the one before. */
static void mono_on(int note, u32 velocity, u32 at)
{
    u32 i, j;

    for (i = j = 0; i < mono_held; i++)
        if (mono_stack[i] != note)
            mono_stack[j++] = mono_stack[i];
    mono_held = j;
    if (mono_held == 16) {
        for (i = 1; i < 16; i++)
            mono_stack[i - 1] = mono_stack[i];
        mono_held--;
    }
    mono_stack[mono_held++] = note;
    if (mono_held > 1 && voice[0].state == VOICE_ON && ctl[0].held)
        glide_to(0, note);
    else
        voice_start(0, note, velocity, at);
}

static void mono_off(int note, u32 at)
{
    u32 i, j;

    for (i = j = 0; i < mono_held; i++)
        if (mono_stack[i] != note)
            mono_stack[j++] = mono_stack[i];
    mono_held = j;
    if (voice[0].state != VOICE_ON || ctl[0].note != note || !ctl[0].held)
        return;
    if (mono_held)
        glide_to(0, mono_stack[mono_held - 1]);
    else
        voice_release(0, at);
}

/* Since ARP at frame `at` of the block (0: its start). */
static void note_on_at(int note, u32 velocity, u32 at)
{
    if (note < 0 || note > 127)
        return;
    velocity = velocity < 1 ? 1 : velocity > 127 ? 127 : velocity;
    if (mono)
        mono_on(note, velocity, at);
    else
        poly_on(note, velocity, at);
}

static void note_off_at(int note, u32 at)
{
    u32 n;

    if (mono) {
        mono_off(note, at);
        return;
    }
    for (n = 0; n < FM_VOICES; n++) {
        if (voice[n].state != VOICE_ON)
            continue;
        if (ctl[n].next == note)
            ctl[n].next_held = 0;
        else if (ctl[n].note == note && ctl[n].held && ctl[n].next < 0)
            voice_release(n, at);
    }
}

void fm_note_on(int note, u32 velocity)
{
    note_on_at(note, velocity, 0);
}

void fm_note_off(int note)
{
    note_off_at(note, 0);
}

static void held_changed(int note);

/* Every voice released, and the pedal's notes let go (PRESETS, a program
 * change, a mode change). Keys still down keep their hold, so their
 * release later is a note off the engine no longer needs. */
static void all_off(void)
{
    u32 n;

    for (n = 0; n < FM_VOICES; n++) {
        if (voice[n].state == VOICE_ON && ctl[n].held)
            voice_release(n, 0);
        ctl[n].next_held = 0;
    }
    arp_silence();
    mono_held = 0;
    for (n = 0; n < 128; n++)
        if (hold[n] & HOLD_PEDAL) {
            hold[n] &= (u8)~HOLD_PEDAL;
            if (!hold[n] && arp_on())
                arp_key((int)n, 0, 0);
            held_changed((int)n);
        }
}

/* --- Holding notes (M6a) ---------------------------------------------- */

static void held_changed(int note)
{
    u32 bit = 1u << (note & 31), w = (u32)note >> 5, n, count = 0;

    if (hold[note] & (HOLD_MIDI | HOLD_PEDAL))
        fm_midi_notes[w] |= bit;
    else
        fm_midi_notes[w] &= ~bit;
    for (n = 0; n < 4; n++) {
        u32 x = fm_midi_notes[n];
        while (x) {
            x &= x - 1;
            count++;
        }
    }
    sb_midi.held = count;
}

/* A key down, on the panel or by MIDI: the note sounds (again). */
static void note_press(int note, u32 velocity, u32 from)
{
    u32 was = hold[note] != 0;

    hold[note] = (u8)((hold[note] | from) & ~HOLD_PEDAL);
    held_changed(note);
    held_on(note, velocity, was);
}

/* A key up: the note ends when nothing else holds it; while the pedal is
 * down, the pedal holds it instead. */
static void note_release(int note, u32 from)
{
    if (!(hold[note] & from))
        return;
    hold[note] &= (u8)~from;
    if (!(hold[note] & (HOLD_PANEL | HOLD_MIDI))) {
        if (pedal)
            hold[note] |= HOLD_PEDAL;
        else if (!hold[note])
            held_off(note);
    }
    held_changed(note);
}

static void pedal_up(void)
{
    int n;

    pedal = 0;
    for (n = 0; n < 128; n++)
        if (hold[n] & HOLD_PEDAL) {
            hold[n] &= (u8)~HOLD_PEDAL;
            if (!hold[n])
                held_off(n);
            held_changed(n);
        }
}

/* All notes off (CC 123, and the mode messages 124 to 127): MIDI's keys
 * let go, as if each had its note off; the pedal still holds them. */
static void midi_notes_off(void)
{
    int n;

    for (n = 0; n < 128; n++)
        if (hold[n] & HOLD_MIDI)
            note_release(n, HOLD_MIDI);
}

/* All sound off (CC 120): MIDI's and the pedal's notes end, and every
 * voice fades out over the next block, as a stolen one does. */
static void sound_off(void)
{
    int n;

    for (n = 0; n < 128; n++)
        if (hold[n] & (HOLD_MIDI | HOLD_PEDAL)) {
            hold[n] &= (u8)~(HOLD_MIDI | HOLD_PEDAL);
            if (!hold[n])
                held_off(n);
            held_changed(n);
        }
    arp_silence();
    for (n = 0; n < (int)FM_VOICES; n++)
        if (voice[n].state == VOICE_ON) {
            voice[n].fade = 1;
            ctl[n].next = -1;
            ctl[n].held = 0;
        }
}

/* --- The test tone (M4's, unchanged): 1 kHz at -6 dBFS after MASTER,
 * started and stopped by PLAY, with 5 ms and 20 ms linear ramps. */
#define TONE_INC  97352592u
#define ENV_FULL  (1 << 24)
#define ATTACK    (ENV_FULL / 221)
#define RELEASE   (ENV_FULL / 882)
enum { TONE_OFF, TONE_ATTACK, TONE_HOLD, TONE_RELEASE };
static u32 tone_state, tone_phase;
static s32 tone_env;

/* --- The controls ------------------------------------------------------ */

static int clamp(int v, int lo, int hi)
{
    return v < lo ? lo : v > hi ? hi : v;
}

/* The operator a raised key's second label names (OP1 to OP6), or -1. */
static int op_of_key(u32 control)
{
    static const u8 keys[FM_OPS] = {
        INPUT_KEY_OP1, INPUT_KEY_OP2, INPUT_KEY_OP3, INPUT_KEY_OP4, INPUT_KEY_OP5, INPUT_KEY_OP6,
    };
    int i;

    for (i = 0; i < (int)FM_OPS; i++)
        if (keys[i] == control)
            return i;
    return -1;
}

/* --- The user slots (M7) --------------------------------------------- */
static u32 program_ok(u32 n)
{
    return n < FM_PATCHES || (n < FM_PROGRAMS && (user_used >> (n - FM_PATCHES) & 1u));
}

/* delta programs on from n, over the programs there are, stopping at the
 * first and the last: no wrap from one end to the other, which jumps
 * across the programs live (the owner's answer on #126). */
static u32 program_step(u32 n, int delta)
{
    while (delta) {
        int d = delta > 0 ? 1 : -1;
        u32 m = n;

        do
            m += (u32)d;
        while (m < FM_PROGRAMS && !program_ok(m));
        if (m >= FM_PROGRAMS)
            break;
        n = m;
        delta -= d;
    }
    return n;
}

static int user_put(u32 slot, const u8 *b)
{
    u32 i;

    if (slot >= FM_USER_SLOTS || !fm_patch_valid(b))
        return 0;
    for (i = 0; i < FM_PATCH_BYTES; i++)
        user_raw[slot][i] = b[i];
    patch_parse(&patches[FM_PATCHES + slot], user_raw[slot]);
    user_used |= 1u << slot;
    shaped_patch = 0xFFFFFFFFu;   /* the patch may be the one playing (M8a) */
    if (FM_PATCHES + slot == patch_now) {
        for (i = 0; i < FM_PATCH_BYTES; i++)
            edit_raw[i] = user_raw[slot][i];
        edited = 0;
    }
    return 1;
}

int fm_user_set(u32 slot, const u8 *patch)
{
    return user_put(slot, patch);
}

const u8 *fm_user_patch(u32 slot)
{
    return user_raw[slot];
}

/* For the screens (M8a). */
/* The program playing now, as patch bytes, with the operator view's
 * edits (since M8a part 3): what the screens show and SAVE writes. */
const u8 *fm_program_bytes(void)
{
    return edit_raw;
}

u32 fm_user_used(void)
{
    return user_used;
}

/* A program's bytes as stored: a test patch's, or a user slot's. */
static const u8 *stored_bytes(u32 n)
{
    return n < FM_PATCHES ? fm_patches[n] : user_raw[n - FM_PATCHES];
}

static void select_patch(u32 n)
{
    u32 i;

    /* The operator view's edits stay with the program until another is
     * chosen (M8a part 3): then the program as stored again. */
    if (edited) {
        patch_parse(&patches[patch_now], stored_bytes(patch_now));
        edited = 0;
    }
    for (i = 0; i < FM_PATCH_BYTES; i++)
        edit_raw[i] = stored_bytes(n)[i];
    shaped_patch = 0xFFFFFFFFu;
    patch_now = n;
    algorithm_now = patches[n].algorithm;
    mono = patches[n].mono;
    sb_fm.patch = n;
}

static void arp_follow(void);

int fm_program_set(u32 n)
{
    if (!program_ok(n))
        return 0;
    select_patch(n);
    panel_program = n;
    arp_follow();
    return 1;
}

/* SAVE held with a key (M7): the patch playing now, with the algorithm
 * and mode the panel set, to user slot `slot`, for main to write to the
 * store. KNOB1 to KNOB4 stay offsets over it, as they are over every
 * patch, and are not saved (docs/DESIGN-NOTES.md, M7, "The panel"). */
static void save_to(u32 slot)
{
    const u8 *from = edit_raw;   /* with the operator view's edits (M8a) */
    u8 b[FM_PATCH_BYTES];
    u32 i, sum;

    for (i = 0; i < FM_PATCH_BYTES; i++)
        b[i] = from[i];
    b[FMP_ALGORITHM] = (u8)(algorithm_now + 1);
    b[FMP_FLAGS] = (u8)(mono ? 1 : 0);
    sum = fm_patch_sum(b);
    b[FM_SUM_OFFSET] = (u8)sum;
    b[FM_SUM_OFFSET + 1] = (u8)(sum >> 8);
    if (!user_put(slot, b))
        return;
    fm_saved_reset[slot] = fm_reset_seq;
    fm_saved_seq[slot]++;
    sb_work++;
}

/* The factory defaults (since M8a from the settings, SAVE confirming
 * it; M7's hold of SAVE and HOME is gone): every user slot emptied, the
 * settings' defaults, the first program; main writes the store's reset. */
static void factory_reset(void)
{
    all_off();
    user_used = 0;
    midi_settings_default(&midi_settings);
    select_patch(0);
    panel_program = 0;
    fm_reset_seq++;
    fm_ui.seq++;
    sb_work++;
}

/* The settings' rows (M8a part 6; views.c draws them in this order). */
enum { ROW_IN, ROW_OUT, ROW_THRU, ROW_LOCAL, ROW_BEND, ROW_KNOBS, ROW_STORE, ROW_RESET, ROWS };

/* KNOB1 on the settings: the row's value one step. */
static void edit_setting(int d)
{
    struct midi_settings *m = &midi_settings;

    switch (fm_ui.row) {
    case ROW_IN:
        m->channel = (u8)clamp(m->channel + d, MIDI_OMNI, 16);
        break;
    case ROW_OUT:
        m->out_channel = (u8)clamp(m->out_channel + d, 1, 16);
        break;
    case ROW_THRU:
        m->thru = d > 0;
        break;
    case ROW_LOCAL:
        m->local = d > 0;
        break;
    case ROW_BEND:
        m->bend_range = (u8)clamp(m->bend_range + d, 0, 24);
        break;
    case ROW_KNOBS:
        m->knobs = d > 0;
        break;
    case ROW_RESET:
        fm_ui.confirm = 1;   /* SAVE does it, anything else cancels */
        break;
    }
}

/* --- The operator view's editing (M8a part 3) -------------------------
 * KNOB1 to KNOB4 on EDIT edit the selected operator of the program
 * playing now, page by page (SELECT): ratio or frequency, level, detune,
 * velocity; mode, coarse, fine; the envelope's three levels. */
static const u16 ratios[] = {
    128, 256, 512, 768, 1024, 1280, 1536, 1792, 2048, 2304, 2560, 2816, 3072, 3328, 3584, 3840, 4096,
};
#define RATIOS (sizeof ratios / sizeof ratios[0])

/* The next whole ratio (or a half) up or down from f (x 256). */
static u32 ratio_step(u32 f, int d)
{
    u32 i;

    if (d > 0) {
        for (i = 0; i < RATIOS; i++)
            if (ratios[i] > f)
                return ratios[i];
        return f;
    }
    for (i = RATIOS; i--;)
        if (ratios[i] < f)
            return ratios[i];
    return f;
}

/* After an edit: the copy's check sum, parsed again. */
static void edit_done(void)
{
    u32 sum = fm_patch_sum(edit_raw);

    edit_raw[FM_SUM_OFFSET] = (u8)sum;
    edit_raw[FM_SUM_OFFSET + 1] = (u8)(sum >> 8);
    patch_parse(&patches[patch_now], edit_raw);
    edited = 1;
    shaped_patch = 0xFFFFFFFFu;
}

static void edit_op(u32 knob, int d)
{
    u8 *o = edit_raw + FM_OP_OFFSET + FM_OP_BYTES * fm_ui.op;
    u32 f = (u32)o[FMO_FREQ] | (u32)o[FMO_FREQ + 1] << 8;

    switch (fm_ui.page * 4u + knob) {
    case 0:   /* RATIO, or the fixed frequency a semitone a detent */
        if (o[FMO_MODE])
            f = d > 0 ? (f * 69433u) >> 16 : (f * 61858u) >> 16;
        else
            f = ratio_step(f, d);
        break;
    case 1:
        o[FMO_LEVEL] = (u8)clamp(o[FMO_LEVEL] + d, 0, 127);
        break;
    case 2:
        o[FMO_DETUNE] = (u8)clamp(signed8(o[FMO_DETUNE]) + d, -100, 100);
        break;
    case 3:
        o[FMO_VELOCITY] = (u8)clamp(o[FMO_VELOCITY] + d, 0, 7);
        break;
    case 4:   /* MODE: ratio 1, or fixed at 440 Hz */
        o[FMO_MODE] = d > 0;
        f = d > 0 ? 1760u : 256u;
        break;
    case 5:   /* COARSE: a whole ratio, or an octave */
        if (o[FMO_MODE])
            f = d > 0 ? f * 2u : f / 2u;
        else
            f = (u32)clamp((int)f + 256 * d, 32, 65535);
        break;
    case 6:   /* FINE: 1/256 of a ratio, or 1 Hz */
        f = (u32)clamp((int)f + (o[FMO_MODE] ? 4 * d : d), 1, 65535);
        break;
    case 8:
    case 9:
    case 10:
        o[FMO_ENV_LEVEL + knob] = (u8)clamp(o[FMO_ENV_LEVEL + knob] + d, 0, 127);
        break;
    default:
        return;
    }
    f = f < 1 ? 1 : f > 65535 ? 65535 : f;
    o[FMO_FREQ] = (u8)f;
    o[FMO_FREQ + 1] = (u8)(f >> 8);
    edit_done();
}

/* The envelope view's editing (M8a part 4): the selected operator's four
 * rates or three levels, the pitch envelope's three rates and depth or
 * four levels, or the glide time. */
static void edit_env(u32 knob, int d)
{
    u8 *o = edit_raw + FM_OP_OFFSET + FM_OP_BYTES * fm_ui.op;

    if (fm_ui.env == 0 && fm_ui.page == 0)
        o[FMO_RATE + knob] = (u8)clamp(o[FMO_RATE + knob] + d, 0, 127);
    else if (fm_ui.env == 0 && knob < 3)
        o[FMO_ENV_LEVEL + knob] = (u8)clamp(o[FMO_ENV_LEVEL + knob] + d, 0, 127);
    else if (fm_ui.env == 1 && fm_ui.page == 0 && knob < 3)
        edit_raw[FMP_PITCH_RATE + knob] = (u8)clamp(edit_raw[FMP_PITCH_RATE + knob] + d, 0, 127);
    else if (fm_ui.env == 1 && fm_ui.page == 0)
        edit_raw[FMP_PITCH_DEPTH] = (u8)clamp(signed8(edit_raw[FMP_PITCH_DEPTH]) + d, -48, 48);
    else if (fm_ui.env == 1)
        edit_raw[FMP_PITCH_LEVEL + knob] = (u8)clamp(signed8(edit_raw[FMP_PITCH_LEVEL + knob]) + d, -127, 127);
    else if (fm_ui.env == 2 && knob == 0)
        edit_raw[FMP_GLIDE] = (u8)clamp(edit_raw[FMP_GLIDE] + d, 0, 127);
    else
        return;
    edit_done();
}

/* --- The arpeggiator (ARP; arp.h) --------------------------------------
 * Its settings are the program's (bytes FMP_ARP to FMP_ARP_GATE, edited
 * as the operator view edits the rest), but for the tempo and what MIDI
 * out sends (the settings, midi_settings). */
static struct arp_patch arp_was;

static void arp_put(const struct arp_patch *a)
{
    edit_raw[FMP_ARP] = (u8)(a->on | a->latch << 1 | a->mode << 2 | (a->octaves - 1u) << 5);
    edit_raw[FMP_ARP_RATE] = (u8)(a->rate | (a->swing / 5u) << 4);
    edit_raw[FMP_ARP_GATE] = a->gate;
    edit_done();
}

/* The ARP screen's knobs: RATE, MODE, OCTAVES, GATE; then SWING, LATCH,
 * TEMPO and MIDI out (the arpeggiator's notes, or the keys held). */
static __attribute__((noinline)) void arp_edit(u32 knob, int d, u32 local)
{
    struct arp_patch a;

    arp_patch_of(edit_raw, &a);
    switch (fm_ui.page * 4u + knob) {
    case 0:
        a.rate = (u8)clamp(a.rate + d, 0, ARP_RATES - 1);
        break;
    case 1:
        a.mode = (u8)clamp(a.mode + d, 0, ARP_MODES - 1);
        break;
    case 2:
        a.octaves = (u8)clamp(a.octaves + d, 1, ARP_OCTAVES);
        break;
    case 3:
        a.gate = (u8)clamp(a.gate + d, ARP_GATE_MIN, ARP_GATE_MAX);
        break;
    case 4:
        a.swing = (u8)clamp(a.swing + 5 * d, 0, ARP_SWING_MAX);
        break;
    case 5:
        a.latch = d > 0;
        break;
    case 6:
        midi_settings.tempo = (u8)clamp(midi_settings.tempo + d, ARP_TEMPO_MIN, ARP_TEMPO_MAX);
        return;
    default:
        midi_settings.arp_out = d > 0;
        return;
    }
    if (local)
        arp_put(&a);
}

/* After any event: the arpeggiator takes the program's settings; turned
 * on, the notes held leave the engine for it; turned off, every note it
 * played ends and the notes held sound again (those the panel holds only
 * with local control on). LATCH turned off lets go of the notes no key
 * holds any more. */
static __attribute__((noinline)) void arp_follow(void)
{
    struct arp_patch a;
    u32 n, on = arp_on();

    arp_patch_of(edit_raw, &a);
    if (on && a.on && arp_was.latch && !a.latch) {
        arp_stop();
        on = 0;
    }
    arp_settings(&a);
    if (a.on && !on) {
        arp_start();
        for (n = 0; n < 128; n++)
            if (hold[n]) {
                fm_note_off((int)n);
                arp_key((int)n, note_velocity[n], 1);
            }
    } else if (!a.on && on) {
        arp_stop();
        for (n = 0; n < 128; n++)
            if ((hold[n] & (HOLD_MIDI | HOLD_PEDAL)) || (midi_settings.local && (hold[n] & HOLD_PANEL)))
                fm_note_on((int)n, note_velocity[n]);
    }
    arp_patch_copy(&arp_was, &a);
    sb_arp.on = arp_on();
}

/* The arpeggiator's notes (arp.h): to the engine with local control on,
 * and to MIDI out unless it sends the keys held. */
void fm_arp_on(int note, u32 velocity, u32 at)
{
    if (midi_settings.local)
        note_on_at(note, velocity, at);
    if (!midi_settings.arp_out)
        midi_out_channel(MIDI_NOTE_ON, (u32)note, velocity);
}

void fm_arp_off(int note, u32 at)
{
    if (midi_settings.local)
        note_off_at(note, at);
    if (!midi_settings.arp_out)
        midi_out_channel(MIDI_NOTE_ON, (u32)note, 0);
}

void fm_arp_clock_out(u32 status)
{
    struct midi_msg m;

    m.status = (u8)status;
    m.data[0] = m.data[1] = 0;
    m.length = 0;
    midi_out_send(&m);
}

/* KNOB1 to KNOB4 as the engine uses them (DESIGN-NOTES.md, M5, "The
 * controls"). */
static void knobs(void)
{
    u32 k;

    if (midi_settings.local)
        for (k = 0; k < 4; k++)
            panel_knob[k] = knob_pos[k];
    /* A change of mode starts MIDI's offsets afresh: they were in the
     * other mode's steps. */
    if (midi_settings.knobs != knobs_mode) {
        knobs_mode = midi_settings.knobs;
        midi_knob[0] = midi_knob[1] = midi_knob[2] = midi_knob[3] = 0;
    }
    if (knobs_mode) {
        /* "Knobs: direct": M5's controls. */
        pitch_knob = clamp(panel_knob[0] + midi_knob[0], -24, 24);
        glide_code = (u32)clamp((int)patches[patch_now].glide + 4 * (panel_knob[1] + midi_knob[1]), 0, 127);
        depth_att = -clamp(panel_knob[2] + midi_knob[2], -64, 32) * 8192;
        feedback_knob = panel_knob[3] + midi_knob[3];
        macro[0] = macro[1] = macro[2] = macro[3] = 0;
    } else {
        for (k = 0; k < 4; k++)
            macro[k] = clamp(panel_knob[k] + midi_knob[k], macro_span[k][0], macro_span[k][1]);
        pitch_knob = 0;
        glide_code = patches[patch_now].glide;
        depth_att = -macro[MACRO_BRIGHT] * 8192;
        feedback_knob = macro[MACRO_COLOR] > 0 ? macro[MACRO_COLOR] * 3 / 32 : 0;
    }
    ensure_shaped();
    for (k = 0; k < 4; k++)
        sb_ui.macro[k] = macro[k];
    fm_ui.knobs = (u8)knobs_mode;
    sb_audio.engine[SYNTH_OCTAVE] = (u32)octave;
    sb_audio.engine[SYNTH_TONE] = tone_state != TONE_OFF && tone_state != TONE_RELEASE;
    sb_fm.algorithm = algorithm_now + 1;
    sb_fm.mono = mono;
    sb_fm.pitch_knob = pitch_knob;
    sb_fm.glide = glide_code;
    sb_fm.depth = -depth_att / 8192;
    sb_fm.feedback = feedback_knob;
}

/* --- MIDI's messages (M6a; docs/DESIGN-NOTES.md, M6a) ---------------- */

/* The four knobs' MIDI offsets: a controller's 64 is none, 0 and 127 the
 * ends of each knob's useful range (KNOB1 +-24 semitones, KNOB2 +-32
 * glide steps, KNOB3 -64 to +32 level steps, KNOB4 +-7 feedback steps). */
static const s8 knob_span[4][2] = { { -24, 24 }, { -32, 32 }, { -64, 32 }, { -7, 7 } };
/* Since M8a, the macros' (macro_span, above), by the same rule. */

static const s8 (*spans(void))[2]
{
    return knobs_mode ? knob_span : macro_span;
}

static int knob_offset(u32 k, u32 v)
{
    const s8 (*span)[2] = spans();

    return v >= 64 ? (int)(v - 64) * span[k][1] / 63 : (int)(64 - v) * span[k][0] / 64;
}

/* Its inverse (M6b): the controller value whose offset is the panel
 * knob's position p (held to the span), so a far end with its own knob at
 * rest takes the same position: the v nearest 64 with knob_offset(k, v)
 * == p (tests/test_midi_model.py checks every p against the model's). */
static u32 knob_value(u32 k, int p)
{
    const s8 (*span)[2] = spans();
    int lo = span[k][0], hi = span[k][1];

    p = clamp(p, lo, hi);
    return p >= 0 ? 64u + (u32)((p * 63 + hi - 1) / hi) : 64u - (u32)((-p * 64 - lo - 1) / -lo);
}

/* A panel knob's move to MIDI out: as the first controller the map
 * routes to it (DESIGN-NOTES.md, M6a), so the map's inverse; none if the
 * map has none, and nothing while the value stays the same (a knob turned
 * on past the end of its span). */
static u8 knob_sent[4] = { 0xFF, 0xFF, 0xFF, 0xFF };

static void knob_out(u32 k)
{
    u32 i, v = knob_value(k, knob_pos[k]);

    if (v == knob_sent[k])
        return;
    for (i = 0; i < midi_settings.routes && i < MIDI_CC_ROUTES; i++)
        if (midi_settings.cc[i].to == MIDI_TO_KNOB1 + k) {
            midi_out_channel(MIDI_CC, midi_settings.cc[i].cc, v);
            knob_sent[k] = (u8)v;
            sb_midi_out.panel_ccs++;
            return;
        }
}

/* Controllers back to rest (CC 121; a reset also): pitch bend, the mod
 * wheel, expression and the pedal; the parameter number to none. */
static void reset_controllers(void)
{
    bend = 0;
    mod_wheel = 0;
    expression = 127;
    rpn = 0x3FFFu;
    if (pedal)
        pedal_up();
}

/* Returns 1 if the controls must be read again. */
static u32 controller(u32 cc, u32 v)
{
    u32 i;

    switch (cc) {
    case 6:                                 /* data entry: RPN 0, the bend range */
        if (rpn == 0)
            midi_settings.bend_range = (u8)(v > 24 ? 24 : v);
        return 0;
    case 100:
        rpn = (rpn & 0x3F80u) | v;
        return 0;
    case 101:
        rpn = (rpn & 0x7Fu) | v << 7;
        return 0;
    case 120:
        sound_off();
        return 0;
    case 122:                               /* local control (M6b) */
        midi_settings.local = v >= 64;
        sb_work++;                          /* the screen shows it */
        return 1;
    case 121:
        reset_controllers();
        return 0;
    case 123:
    case 124:                               /* omni off, omni on: the channel stays */
    case 125:
        midi_notes_off();
        return 0;
    case 126:                               /* mono on, poly on */
    case 127:
        midi_notes_off();
        all_off();
        mono = cc == 126;
        return 1;
    }
    for (i = 0; i < midi_settings.routes && i < MIDI_CC_ROUTES; i++) {
        if (midi_settings.cc[i].cc != cc)
            continue;
        switch (midi_settings.cc[i].to) {
        case MIDI_TO_MOD:
            mod_wheel = v;
            break;
        case MIDI_TO_VOLUME:
            volume = v;
            break;
        case MIDI_TO_EXPRESSION:
            expression = v;
            break;
        case MIDI_TO_SUSTAIN:
            if (v >= 64)
                pedal = 1;
            else if (pedal)
                pedal_up();
            break;
        case MIDI_TO_KNOB1:
        case MIDI_TO_KNOB2:
        case MIDI_TO_KNOB3:
        case MIDI_TO_KNOB4: {
            u32 k = midi_settings.cc[i].to - MIDI_TO_KNOB1;
            /* With the macros (M8a) the default map's two controllers
             * named for M5's controls keep their meaning: 74, brightness,
             * moves BRIGHT, and 5, the glide time, has no macro. */
            if (!knobs_mode && cc == 5)
                return 0;
            if (!knobs_mode && cc == 74)
                k = MACRO_BRIGHT;
            midi_knob[k] = knob_offset(k, v);
            return 1;
        }
        }
        return 0;
    }
    return 0;
}

/* One message; returns 1 if the controls must be read again. */
static u32 midi_message(const struct midi_msg *m)
{
    u32 kind = m->status & 0xF0u, ch = m->status & 0x0Fu, again = 0;
    int note = m->data[0];

    /* MIDI clock and its transport (since ARP): the arpeggiator's. */
    if (m->status >= MIDI_CLOCK && m->status <= MIDI_STOP) {
        arp_clock(m->status, sb_audio.blocks);
        return m->status != MIDI_CLOCK;
    }
    if (m->status == MIDI_RESET) {
        /* A system reset: as at power on, except the settings. */
        midi_notes_off();
        reset_controllers();
        volume = 127;
        midi_knob[0] = midi_knob[1] = midi_knob[2] = midi_knob[3] = 0;
        return 1;
    }
    if (kind == 0xF0u)
        return 0;                           /* realtime, common and SysEx: nothing to play */
    if (midi_settings.channel != MIDI_OMNI && ch != midi_settings.channel - 1u) {
        sb_midi.filtered++;
        return 0;
    }
    switch (kind) {
    case MIDI_NOTE_ON:
        if (m->data[1]) {
            sb_midi.notes_on++;
            sb_midi.last_note_tick = sb_ticks();
            note_press(note, m->data[1], HOLD_MIDI);
            midi_screen_post(ch, note, m->data[1]);
            break;
        }
        /* fall through: a note on at velocity 0 is a note off */
    case MIDI_NOTE_OFF:
        sb_midi.notes_off++;
        note_release(note, HOLD_MIDI);
        midi_screen_post(ch, note, 0);
        break;
    case MIDI_CC:
        again = controller(m->data[0], m->data[1]);
        break;
    case MIDI_PROGRAM:
        /* A program selects a test patch or (since M7) a user slot that
         * holds a patch; any other is ignored. */
        if (program_ok(m->data[0])) {
            all_off();
            select_patch(m->data[0]);
            sb_midi.program = m->data[0];
            again = 1;
        }
        break;
    case MIDI_BEND:
        /* 14 bits, 8192 the middle: +-bend_range semitones. */
        bend = ((s32)(m->data[0] | (u32)m->data[1] << 7) - 8192) * midi_settings.bend_range / 2;
        break;
    default:
        break;                              /* aftertouch: not used yet */
    }
    return again;
}

/* The events since the last block; the controls are read again only
 * when there were some (nothing else changes them). */
static void events(void)
{
    struct input_event e;
    struct midi_msg m;
    u32 any = 0;

    /* MIDI out first: what waits goes on the wire if it is free. */
    midi_out_poll();
#if defined(SB_TEST_MIDI_BURST)
    sb_test_midi_burst();
#endif
    while (input_read_audio(&e)) {
        u32 local = midi_settings.local;

        any = 1;
        sb_audio.engine[SYNTH_EVENTS]++;
        if (e.control >= INPUT_KEY1 && e.control <= INPUT_KEY27) {
            u32 k = e.control - INPUT_KEY1, velocity = FM_KEY_VELOCITY;
            if (e.kind == INPUT_PRESS) {
                /* SAVE held (M7): KEY1 to KEY16 save to their slot, and no
                 * key plays a note. */
                if (input_value(INPUT_SAVE)) {
                    if (k < FM_USER_SLOTS)
                        save_to(k);
                    key_note[k] = -1;
                    continue;
                }
                /* SEL held: MONO and POLY switch the mode (and play no
                 * note); MIDI out sends the mode message (M6b). */
                /* SEL with OP1 to OP6 picks the operator (M8a); SEL with any
                 * of the ten labelled raised keys plays no note. */
                if (input_value(INPUT_SEL) && e.control >= INPUT_KEY_OP1 && e.control <= INPUT_KEY_POLY
                    && op_of_key(e.control) >= 0) {
                    fm_ui.op = (u8)op_of_key(e.control);
                    if (fm_ui.env) {
                        fm_ui.env = 0;   /* back to an operator's envelope */
                        fm_ui.page = 0;
                    }
                    key_note[k] = -1;
                    continue;
                }
                if (input_value(INPUT_SEL) && (e.control == INPUT_KEY_PIT || e.control == INPUT_KEY_GLO)) {
                    /* The envelope view with the pitch envelope, or the
                     * glide (M8a part 4). */
                    fm_ui.screen = UI_ENV;
                    fm_ui.env = e.control == INPUT_KEY_PIT ? 1 : 2;
                    fm_ui.page = 0;
                    key_note[k] = -1;
                    continue;
                }
                if (input_value(INPUT_SEL) && (e.control == INPUT_KEY_MONO || e.control == INPUT_KEY_POLY)) {
                    if (local) {
                        all_off();
                        mono = e.control == INPUT_KEY_MONO;
                    }
                    midi_out_channel(MIDI_CC, e.control == INPUT_KEY_MONO ? 126 : 127,
                                     e.control == INPUT_KEY_MONO);
                    key_note[k] = -1;
                    continue;
                }
                key_note[k] = FM_KEY1_NOTE + (int)k + 12 * octave;
#if defined(SB_TEST_VELOCITY)
                /* The velocity test build: KEY1 to KEY5 play these. */
                {
                    static const u8 velocities[5] = { 127, 100, 64, 32, 1 };
                    if (k < 5)
                        velocity = velocities[k];
                }
#endif
                /* Since ARP the arpeggiator takes the panel's keys even
                 * with local control off, and MIDI out sends them only if
                 * it is off or sends the keys held; a key's note off goes
                 * out only if its note on did. */
                if (local || arp_on())
                    note_press(key_note[k], velocity, HOLD_PANEL);
                if (!arp_on() || midi_settings.arp_out) {
                    midi_out_channel(MIDI_NOTE_ON, (u32)key_note[k], velocity);
                    sb_midi_out.panel_notes++;
                    sb_midi_out.last_note_tick = sb_ticks();
                    key_sent |= 1u << k;
                }
            } else if (e.kind == INPUT_RELEASE && key_note[k] >= 0) {
                /* A note off as a note on at velocity 0, so a run of
                 * notes keeps running status (DESIGN-NOTES.md, M6b). */
                note_release(key_note[k], HOLD_PANEL);
                if (key_sent >> k & 1u)
                    midi_out_channel(MIDI_NOTE_ON, (u32)key_note[k], 0);
                key_sent &= ~(1u << k);
                key_note[k] = -1;
            }
        } else if (e.kind == INPUT_PRESS && (e.control == INPUT_HOME || e.control == INPUT_EDIT
                                             || e.control == INPUT_ENV || e.control == INPUT_GLO)) {
            /* The screens (M8a): HOME always back to the patch view. */
            fm_ui.screen = (u8)(e.control == INPUT_EDIT ? UI_EDIT : e.control == INPUT_ENV ? UI_ENV
                                : e.control == INPUT_GLO ? UI_SETTINGS : UI_PATCH);
            fm_ui.page = 0;
            fm_ui.env = 0;
            fm_ui.confirm = 0;
        } else if (e.control == INPUT_ARP && (e.kind == INPUT_PRESS || e.kind == INPUT_RELEASE)) {
            /* ARP (since ARP): a short press turns the arpeggiator on or
             * off, on its release; held ARP_HOLD_TICKS it shows the ARP
             * screen instead (below, each block). */
            if (e.kind == INPUT_PRESS) {
                arp_down = 1;
                arp_long = 0;
                arp_pressed = e.time;
            } else {
                if (arp_down && !arp_long && local) {
                    edit_raw[FMP_ARP] ^= 1u;
                    edit_done();
                    fm_arp_toggles++;
                }
                arp_down = 0;
            }
        } else if (e.kind == INPUT_PRESS && e.control == INPUT_OCT_DOWN) {
            octave -= octave > -OCTAVES;
        } else if (e.kind == INPUT_PRESS && e.control == INPUT_OCT_UP) {
            octave += octave < OCTAVES;
        } else if (e.kind == INPUT_PRESS && e.control == INPUT_PLAY) {
            tone_state = tone_state == TONE_OFF || tone_state == TONE_RELEASE ? TONE_ATTACK : TONE_RELEASE;
        } else if (e.kind == INPUT_TURN && e.control == INPUT_PRESETS) {
            u32 from = local ? patch_now : panel_program;
            /* A turn on past an end does nothing: no notes cut, no
             * edits lost, nothing sent (as a knob past its span). */
            if (program_step(from, (int)e.value) == from)
                continue;
            panel_program = program_step(from, (int)e.value);
            if (local) {
                all_off();
                select_patch(panel_program);
            }
            midi_out_channel(MIDI_PROGRAM, panel_program, 0);
            sb_midi_out.panel_programs++;
        } else if (e.kind == INPUT_TURN && e.control == INPUT_ALGORITHM) {
            if (local)
                algorithm_now = (algorithm_now + FM_ALGORITHMS * 16 + (u32)(int)e.value) % FM_ALGORITHMS;
        } else if (e.kind == INPUT_TURN && e.control >= INPUT_KNOB1 && e.control <= INPUT_KNOB4) {
            u32 k = e.control - INPUT_KNOB1;
            if (fm_ui.screen == UI_EDIT) {
                if (local)
                    edit_op(k, e.value);
            } else if (fm_ui.screen == UI_ENV) {
                if (local)
                    edit_env(k, e.value);
            } else if (fm_ui.screen == UI_SETTINGS) {
                /* KNOB1 changes the row's value (M8a part 6). */
                if (k == 0)
                    edit_setting(e.value);
            } else if (fm_ui.screen == UI_ARP) {
                arp_edit(k, e.value, local);
            } else {
                const s8 (*span)[2] = spans();
                knob_pos[k] = clamp(knob_pos[k] + e.value, span[k][0], span[k][1]);
                knob_out(k);
            }
        } else if (e.kind == INPUT_TURN && e.control == INPUT_SELECT && fm_ui.screen == UI_EDIT) {
            /* SELECT steps through the operator view's three pages. */
            fm_ui.page = (u8)((fm_ui.page + 3u + (u32)(e.value > 0 ? 1 : 2)) % 3u);
        } else if (e.kind == INPUT_TURN && e.control == INPUT_SELECT && fm_ui.screen == UI_ARP) {
            fm_ui.page ^= 1;   /* the ARP screen's two pages */
        } else if (e.kind == INPUT_TURN && e.control == INPUT_SELECT && fm_ui.screen == UI_SETTINGS) {
            fm_ui.row = (u8)clamp(fm_ui.row + e.value, 0, ROWS - 1);
            fm_ui.confirm = 0;
        } else if (e.kind == INPUT_PRESS && e.control == INPUT_SAVE && fm_ui.confirm) {
            fm_ui.confirm = 0;
            factory_reset();
        } else if (e.kind == INPUT_TURN && e.control == INPUT_SELECT && fm_ui.screen == UI_ENV && fm_ui.env < 2) {
            /* The envelope view's two pages: rates, then levels. */
            fm_ui.page ^= 1;
        }
    }
    /* ARP held: its screen, once (since ARP). */
    if (arp_down && !arp_long && sb_ticks() - arp_pressed >= ARP_HOLD_TICKS) {
        arp_long = 1;
        fm_ui.screen = UI_ARP;
        fm_ui.page = 0;
        fm_ui.confirm = 0;
        any = 1;
    }
    midi_poll();
    if (midi_read(&m)) {
        do {
            /* MIDI thru (M6b): what MIDI in received, never what the
             * firmware sends itself, before the receive channel's filter.
             * A SysEx is only counted: the parser keeps none of its bytes. */
            if (midi_settings.thru) {
                if (m.status == MIDI_SYSEX) {
                    sb_midi_out.thru_sysex++;
                } else {
                    midi_out_send(&m);
                    sb_midi_out.thru++;
                }
            }
            any |= midi_message(&m);
        } while (midi_read(&m));
        sb_midi.bend = bend;
        sb_midi.mod = mod_wheel;
        sb_midi.volume = volume;
        sb_midi.expression = expression;
        sb_midi.pedal = pedal;
    }
    if (any) {
        knobs();
        arp_follow();
        /* Whatever the events changed, the screens show (M8a). */
        fm_ui.seq++;
        sb_work++;
    }
    /* What this block queued goes out at once if the wire is free. */
    midi_out_poll();
    /* Vibrato: a 5.5 Hz sine, up to half a semitone at the wheel's top. */
    /* Since M8a MOTION adds to it, up to half a semitone more. */
    if (mod_wheel || macro[MACRO_MOTION]) {
        lfo_phase += LFO_INC;
        vibrato = (s32)(((s64)fm_sine(lfo_phase) * (s32)(mod_wheel * 2048u / 127u + (u32)macro[MACRO_MOTION] * 32u))
                        >> 23);
    } else {
        vibrato = 0;
    }
}

/* --- Each block ------------------------------------------------------- */

/* A voice's pitch and its operators' phase steps for the next block. */
static void voice_pitch(u32 n)
{
    struct fm_voice *v = &voice[n];
    struct control *c = &ctl[n];
    const struct patch *p = c->patch;
    s32 pitch;
    u32 base, i;
    int fb;

    if (c->glide_left) {
        c->glide_left--;
        c->pitch = c->glide_left ? c->pitch + c->glide_step : c->glide_to;
    }
    pitch = c->pitch + pitch_knob * SEMITONE + bend + vibrato;
    if (p->pitch_depth) {
        u32 s = c->pitch_stage;
        s32 to = p->pitch_level[s == 0 ? 1 : s == 1 ? 2 : 3], step = p->pitch_step[s];
        if (c->pitch_level < to)
            c->pitch_level = to - c->pitch_level <= step ? to : c->pitch_level + step;
        else
            c->pitch_level = c->pitch_level - to <= step ? to : c->pitch_level - step;
        if (s == 0 && c->pitch_level == to)
            c->pitch_stage = 1;
        pitch += (s32)((s64)p->pitch_depth * c->pitch_level * SEMITONE / (127 * 65536));
    }
    base = fm_pitch_inc(pitch);
    for (i = 0; i < FM_OPS; i++) {
        struct fm_op *o = &v->op[i];
        u64 inc = o->fixed ? o->freq : ((u64)base * o->freq) >> 8;
        inc = (inc * (u32)o->detune) >> 30;
        if (macro[MACRO_MOTION])
            inc = (inc * (u32)spread[i]) >> 30;
        o->inc = inc >= 0x80000000u ? 0x80000000u : (u32)inc;
    }
    v->mod_att = depth_att;
    fb = clamp((int)p->feedback + feedback_knob, 0, 7);
    v->fb_target = fb ? 1 << (fb + 9) : 0;
}

void fm_block(s32 *out, u32 frames)
{
    u32 n, on[2] = { 0, 0 }, posted = 0, seq = 0;
    s32 target, step, m, *w;
    int pot;

    /* The voices a fade or a release has finished with. */
    for (n = 0; sounding && n < FM_VOICES; n++) {
        struct fm_voice *v = &voice[n];
        if (v->state != VOICE_ON)
            continue;
        if (v->fade_done) {
            struct control *c = &ctl[n];
            v->state = VOICE_IDLE;
            sounding--;
            if (c->next >= 0) {
                int note = c->next;
                u32 held = c->next_held;
                voice_start(n, note, c->next_velocity, 0);
                if (!held)
                    voice_release(n, 0);
            }
        } else if (v->silent && !v->fade) {
            v->state = VOICE_IDLE;
            sounding--;
            sb_audio.engine[SYNTH_LAST_OFF] = sb_audio.blocks;
        }
    }
    events();
    /* Since ARP: a note released in the block it started in, at this
     * block's start (after the events, so they are taken as before). */
    for (n = 0; sounding && n < FM_VOICES; n++)
        if (ctl[n].release_next && voice[n].state == VOICE_ON)
            voice_release(n, 0);
    /* The arpeggiator's steps within this block, at their frames (ARP),
     * and its notes on the wire at once if it is free. */
    if (arp_busy) {
        arp_block(sb_audio.blocks);
        midi_out_poll();
    }
    pot = input_value(INPUT_MASTER);
    target = pot >= 1023 ? ENV_FULL : pot * pot * 16;
    /* MIDI's volume and expression (127 each until a controller says
     * otherwise), each as its square, the usual curve. */
    if (volume != 127 || expression != 127)
        target = (s32)((u64)target * (volume * volume) / (127 * 127) * (expression * expression) / (127 * 127));
    step = (target - master) / (s32)AUDIO_FRAMES;
    sb_audio.engine[SYNTH_MASTER] = (u32)target;

    for (n = 0; sounding && n < FM_VOICES; n++)
        if (voice[n].state == VOICE_ON) {
            voice_pitch(n);
            on[n & 1]++;
        }
    if (!on[0] && !on[1] && tone_state == TONE_OFF) {
        /* At rest: silence, exactly, and core 1 left waiting. */
        for (n = 0; n < 2 * frames; n++)
            out[n] = 0;
        master = target;
        if (sb_fm.voices[0] | sb_fm.voices[1]) {
            sb_fm.voices[0] = sb_fm.voices[1] = 0;
            sb_audio.engine[SYNTH_VOICES_ON] = 0;
            for (n = 0; n < FM_OPS; n++)
                fm_op_level[n] = 0;
            fm_env_dot.valid = 0;
        }
        if (spec_capture)
            spectrum_feed(0, frames);
        return;
    }
    sb_fm.voices[0] = on[0];
    sb_fm.voices[1] = on[1];
    if (on[0] + on[1] > sb_fm.voices_max)
        sb_fm.voices_max = on[0] + on[1];
    sb_audio.engine[SYNTH_VOICES_ON] = on[0] + on[1];
    if (on[1]) {
        seq = job_seq + 1;
        publish(&job_seq, seq);
        posted = 1;
    }
    for (n = 0; n < AUDIO_FRAMES; n++)
        mix[0][n] = 0;
    for (n = 0; n < FM_VOICES; n += 2)
        if (voice[n].state == VOICE_ON) {
            fm_render(&voice[n], mix[0], scratch[0]);
#if defined(SB_PROBE_LOADED)
            sb_probe_loaded();
#endif
        }
    if (posted) {
        u32 t = sb_now(), d;
        while (shared(&job_done) != seq)
            ;
        d = sb_now() - t;
        if (d > sb_fm.wait_max)
            sb_fm.wait_max = d;
        for (n = 0; n < AUDIO_FRAMES; n++)
            mix[0][n] += mix[1][n];
    }
    /* The envelope view's dot (M8a part 4), only while it shows: the
     * newest note still sounding. */
    if (fm_ui.screen == UI_ENV) {
        u32 pick = FM_VOICES;
        for (n = 0; n < FM_VOICES; n++)
            if (voice[n].state == VOICE_ON && (pick == FM_VOICES || ctl[n].age > ctl[pick].age))
                pick = n;
        if (pick == FM_VOICES || fm_ui.env == 2) {
            fm_env_dot.valid = 0;
        } else if (fm_ui.env == 1) {
            fm_env_dot.stage = ctl[pick].pitch_stage;
            fm_env_dot.att = ctl[pick].pitch_level;
            fm_env_dot.valid = 2;
        } else {
            const struct fm_op *o = &voice[pick].op[fm_ui.op];
            fm_env_dot.stage = o->stage;
            fm_env_dot.att = o->stage == ENV_ATTACK ? o->lin : o->att;
            fm_env_dot.valid = o->stage != ENV_OFF;
        }
    }
    /* The operator view's live levels (M8a), only while it shows. */
    if (fm_ui.screen == UI_EDIT) {
        u32 i;
        for (i = 0; i < FM_OPS; i++) {
            s32 g = 0;
            for (n = 0; n < FM_VOICES; n++)
                if (voice[n].state == VOICE_ON && voice[n].op[i].gain > g)
                    g = voice[n].op[i].gain;
            fm_op_level[i] = g;
        }
    }
    m = master;
    for (n = 0, w = out; n < frames; n++, w += 2) {
        s32 s = (s32)((s64)mix[0][n] * m >> 24);
        m += step;
        s = s > AUDIO_FULL ? AUDIO_FULL : s < -AUDIO_FULL ? -AUDIO_FULL : s;
        w[0] = s;
        w[1] = s;
    }
    master = target;
    /* The test tone after MASTER: its level is fixed. */
    if (tone_state != TONE_OFF) {
        s32 env = tone_env, d = tone_state == TONE_ATTACK ? ATTACK : tone_state == TONE_RELEASE ? -RELEASE : 0;
        for (n = 0, w = out; n < frames; n++, w += 2) {
            s32 s = w[0] + (s32)((s64)fm_sine(tone_phase) * env >> 25);
            tone_phase += TONE_INC;
            if (d) {
                env += d;
                if (env >= ENV_FULL) {
                    env = ENV_FULL;
                    d = 0;
                    tone_state = TONE_HOLD;
                } else if (env <= 0) {
                    env = 0;
                    d = 0;
                    tone_state = TONE_OFF;
                    sb_audio.engine[SYNTH_LAST_OFF] = sb_audio.blocks;
                }
            }
            s = s > AUDIO_FULL ? AUDIO_FULL : s < -AUDIO_FULL ? -AUDIO_FULL : s;
            w[0] = s;
            w[1] = s;
        }
        tone_env = env;
    }
    /* The patch view's spectrum (M8a part 5): a capture main asked for. */
    if (spec_capture)
        spectrum_feed(out, frames);
}

void fm_init(void)
{
    u32 n, saved;

    fm_tables();
    for (n = 0; n < FM_PATCHES; n++)
        patch_parse(&patches[n], fm_patches[n]);
    for (n = 0; n < 27; n++)
        key_note[n] = -1;
    for (n = 0; n < FM_VOICES; n++)
        ctl[n].next = -1;
    select_patch(0);
    midi_settings_default(&midi_settings);
#if defined(SB_TEST_MIDI_CHANNEL)
    midi_settings.channel = 10;   /* the channel test build (tools/fw-suite.py) */
#endif
#if defined(SB_TEST_MIDI_THRU)
    midi_settings.thru = 1;       /* the thru test build: thru on, out on channel 2 */
    midi_settings.out_channel = 2;
#endif
    sb_midi.program = 0xFFFFFFFFu;
    sb_midi.volume = volume;
    sb_midi.expression = expression;
    midi_start();
    knobs();
    arp_follow();
    sb_arp.marker = ARP_MARKER;
    sb_fm.marker = FM_MARKER;
    sb_midi.marker = MIDI_MARKER;
    sb_midi_out.marker = MIDI_OUT_MARKER;
    /* Core 1 (HW-9): its start address in source 126's vector word, then
     * C1_CON bit 3; once it runs, the word gets its stub back. If it
     * never says it runs, core 0 renders every voice. */
    saved = CORE1_START;
    CORE1_START = (u32)fm_core1_entry;
    C1_CON |= 1u << 3;
    for (n = 0; n < CORE1_WAIT && !shared(&core1_running); n++)
        ;
    CORE1_START = saved;
    two_cores = shared(&core1_running);
}
/* Without core 1 the odd voices are never given a note: core 0 plays the
 * even ones, half the polyphony. */
