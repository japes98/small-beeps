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
 */

#include "fm.h"
#include "input.h"
#include "midi.h"

volatile struct sb_fm_record sb_fm __attribute__((section(".beacon.fm")));

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
};

static struct control ctl[FM_VOICES];
static struct patch patches[FM_PATCHES];
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

/* MIDI's controls: the pitch bend and vibrato (1 / 4096 semitone), the
 * levels (0 to 127), the pedal, the four knobs' offsets (in their own
 * steps), and the parameter number data entry changes (RPN; 0x3FFF:
 * none). */
static s32 bend, vibrato;
static u32 mod_wheel, volume = 127, expression = 127, pedal;
static int midi_knob[4];
static u32 lfo_phase, rpn = 0x3FFFu;

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
    for (i = 29; i < 32; i++)
        if (b[i])
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

/* --- Notes ------------------------------------------------------------ */

/* Starts note on voice n from the current patch. A free voice starts from
 * silence at phase 0; one still sounding (the same note again, or mono)
 * keeps its phases and starts its attacks from where its envelopes are,
 * so neither clicks. */
static void voice_start(u32 n, int note, u32 velocity)
{
    struct fm_voice *v = &voice[n];
    struct control *c = &ctl[n];
    const struct patch *p = &patches[patch_now];
    u32 i, k, fresh = v->state != VOICE_ON, carriers = 0;
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
    v->algorithm = algorithm_now;
    for (i = 0; i < FM_OPS; i++) {
        struct fm_op *o = &v->op[i];
        if (fresh) {
            o->phase = 0;
            o->gain = 0;
            o->y1 = o->y2 = 0;
            o->lin = 0;
        } else if (o->stage != ENV_ATTACK) {
            o->lin = o->stage == ENV_OFF ? 0 : fm_exp2_neg(o->att);
        }
        o->fixed = p->op[i].fixed;
        o->freq = p->op[i].freq;
        o->detune = p->op[i].detune;
        o->fixed_att = p->op[i].level_att + soft * p->op[i].velocity;
        for (k = 0; k < 4; k++)
            o->step[k] = p->op[i].step[k];
        for (k = 0; k < 3; k++)
            o->target[k] = p->op[i].target[k];
        o->stage = p->op[i].off ? ENV_OFF : ENV_ATTACK;
        carriers += !p->op[i].off && fm_algorithms[algorithm_now].dest[i] == FM_TO_OUT;
    }
    v->out_att = fm_carrier_att(carriers);
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

static void voice_release(u32 n)
{
    struct fm_voice *v = &voice[n];
    u32 i;

    ctl[n].held = 0;
    ctl[n].pitch_stage = 2;
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
static void poly_on(int note, u32 velocity)
{
    u32 n, pick = FM_VOICES, load[2] = { 0, 0 };

    for (n = 0; n < FM_VOICES; n++)
        if (voice[n].state == VOICE_ON) {
            load[n & 1]++;
            if (ctl[n].note == note && ctl[n].next < 0 && !voice[n].fade)
                pick = n;
        }
    if (pick < FM_VOICES) {
        voice_start(pick, note, velocity);
        return;
    }
    for (n = 0; n < FM_VOICES; n++) {
        if (voice[n].state == VOICE_ON || (!two_cores && (n & 1)))
            continue;
        if (pick == FM_VOICES || (two_cores && load[n & 1] < load[pick & 1]))
            pick = n;
    }
    if (pick < FM_VOICES) {
        voice_start(pick, note, velocity);
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
static void mono_on(int note, u32 velocity)
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
        voice_start(0, note, velocity);
}

static void mono_off(int note)
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
        voice_release(0);
}

void fm_note_on(int note, u32 velocity)
{
    if (note < 0 || note > 127)
        return;
    velocity = velocity < 1 ? 1 : velocity > 127 ? 127 : velocity;
    if (mono)
        mono_on(note, velocity);
    else
        poly_on(note, velocity);
}

void fm_note_off(int note)
{
    u32 n;

    if (mono) {
        mono_off(note);
        return;
    }
    for (n = 0; n < FM_VOICES; n++) {
        if (voice[n].state != VOICE_ON)
            continue;
        if (ctl[n].next == note)
            ctl[n].next_held = 0;
        else if (ctl[n].note == note && ctl[n].held && ctl[n].next < 0)
            voice_release(n);
    }
}

/* Every voice released, and the pedal's notes let go (PRESETS, a program
 * change, a mode change). Keys still down keep their hold, so their
 * release later is a note off the engine no longer needs. */
static void all_off(void)
{
    u32 n;

    for (n = 0; n < FM_VOICES; n++) {
        if (voice[n].state == VOICE_ON && ctl[n].held)
            voice_release(n);
        ctl[n].next_held = 0;
    }
    mono_held = 0;
    for (n = 0; n < 128; n++)
        hold[n] &= (u8)~HOLD_PEDAL;
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
    hold[note] = (u8)((hold[note] | from) & ~HOLD_PEDAL);
    held_changed(note);
    fm_note_on(note, velocity);
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
            fm_note_off(note);
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
                fm_note_off(n);
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
                fm_note_off(n);
            held_changed(n);
        }
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

static void select_patch(u32 n)
{
    patch_now = n;
    algorithm_now = patches[n].algorithm;
    mono = patches[n].mono;
    sb_fm.patch = n;
}

/* KNOB1 to KNOB4 as the engine uses them (DESIGN-NOTES.md, M5, "The
 * controls"). */
static void knobs(void)
{
    pitch_knob = clamp(input_value(INPUT_KNOB1) + midi_knob[0], -24, 24);
    glide_code = (u32)clamp((int)patches[patch_now].glide + 4 * (input_value(INPUT_KNOB2) + midi_knob[1]),
                            0, 127);
    depth_att = -clamp(input_value(INPUT_KNOB3) + midi_knob[2], -64, 32) * 8192;
    feedback_knob = input_value(INPUT_KNOB4) + midi_knob[3];
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

static int knob_offset(u32 k, u32 v)
{
    return v >= 64 ? (int)(v - 64) * knob_span[k][1] / 63 : (int)(64 - v) * knob_span[k][0] / 64;
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
        /* A program selects a test patch; one past them is ignored. */
        if (m->data[0] < FM_PATCHES) {
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

    while (input_read_audio(&e)) {
        any = 1;
        sb_audio.engine[SYNTH_EVENTS]++;
        if (e.control >= INPUT_KEY1 && e.control <= INPUT_KEY27) {
            u32 k = e.control - INPUT_KEY1;
            if (e.kind == INPUT_PRESS) {
                /* SEL held: MONO and POLY switch the mode (and play no note). */
                if (input_value(INPUT_SEL) && (e.control == INPUT_KEY_MONO || e.control == INPUT_KEY_POLY)) {
                    all_off();
                    mono = e.control == INPUT_KEY_MONO;
                    key_note[k] = -1;
                    continue;
                }
                key_note[k] = FM_KEY1_NOTE + (int)k + 12 * octave;
#if defined(SB_TEST_VELOCITY)
                /* The velocity test build: KEY1 to KEY5 play these. */
                {
                    static const u8 velocity[5] = { 127, 100, 64, 32, 1 };
                    note_press(key_note[k], k < 5 ? velocity[k] : FM_KEY_VELOCITY, HOLD_PANEL);
                    continue;
                }
#endif
                note_press(key_note[k], FM_KEY_VELOCITY, HOLD_PANEL);
            } else if (e.kind == INPUT_RELEASE && key_note[k] >= 0) {
                note_release(key_note[k], HOLD_PANEL);
                key_note[k] = -1;
            }
        } else if (e.kind == INPUT_PRESS && e.control == INPUT_OCT_DOWN) {
            octave -= octave > -OCTAVES;
        } else if (e.kind == INPUT_PRESS && e.control == INPUT_OCT_UP) {
            octave += octave < OCTAVES;
        } else if (e.kind == INPUT_PRESS && e.control == INPUT_PLAY) {
            tone_state = tone_state == TONE_OFF || tone_state == TONE_RELEASE ? TONE_ATTACK : TONE_RELEASE;
        } else if (e.kind == INPUT_TURN && e.control == INPUT_PRESETS) {
            all_off();
            select_patch((patch_now + FM_PATCHES * 16 + (u32)(int)e.value) % FM_PATCHES);
        } else if (e.kind == INPUT_TURN && e.control == INPUT_ALGORITHM) {
            algorithm_now = (algorithm_now + FM_ALGORITHMS * 16 + (u32)(int)e.value) % FM_ALGORITHMS;
        }
    }
    while (midi_read(&m))
        any |= midi_message(&m);
    if (any)
        knobs();
    /* Vibrato: a 5.5 Hz sine, up to half a semitone at the wheel's top. */
    lfo_phase += LFO_INC;
    vibrato = mod_wheel ? (s32)(((s64)fm_sine(lfo_phase) * (s32)(mod_wheel * 2048u / 127u)) >> 23) : 0;
    sb_midi.bend = bend;
    sb_midi.mod = mod_wheel;
    sb_midi.volume = volume;
    sb_midi.expression = expression;
    sb_midi.pedal = pedal;
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
                voice_start(n, note, c->next_velocity);
                if (!held)
                    voice_release(n);
            }
        } else if (v->silent && !v->fade) {
            v->state = VOICE_IDLE;
            sounding--;
            sb_audio.engine[SYNTH_LAST_OFF] = sb_audio.blocks;
        }
    }
    events();
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
        }
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
    sb_midi.program = 0xFFFFFFFFu;
    knobs();
    sb_fm.marker = FM_MARKER;
    sb_midi.marker = MIDI_MARKER;
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
