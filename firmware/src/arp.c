/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * The arpeggiator (ARP; arp.h, docs/DESIGN-NOTES.md, "ARP"): our own
 * design from the owner's answers to docs/ARP-PROPOSAL.md. Core 0, in
 * the audio interrupt only.
 */

#include "arp.h"
#include "audio.h"
#include "midi.h"

volatile struct sb_arp_record sb_arp __attribute__((section(".beacon.arp")));

/* Each rate's step in MIDI clock pulses, in KNOB1's order (arp.h). */
static const u8 rate_pulses[ARP_RATES] = { 48, 36, 24, 18, 12, 8, 9, 6, 4, 3 };
/* The random mode's generator: a fixed linear congruential one (the
 * usual 32-bit constants), from the same seed each time the arpeggiator
 * starts, so a test can predict it (tools/arp_model.py). */
#define RANDOM_SEED 1u

static struct arp_patch set = { 0, 0, ARP_UP, 1, ARP_RATE_DEFAULT, 0, ARP_GATE_DEFAULT };
static u32 running;

/* The notes it holds, in the order they came (ORDER), and how many keys
 * are down now (LATCH: the first key down after none starts a new chord). */
static struct {
    u8 note, velocity;
} held[ARP_HELD];
static u32 n_held, keys_pressed_now;
/* The notes it plays now, ending at off_at. */
static u8 playing[ARP_HELD];
static u32 n_playing;
static u64 off_at;

/* The clock's position: pulses and units of a pulse (< ARP_UNIT). The
 * next step is on the grid at pulse grid (a multiple of its step), the
 * index-th step of the grid (odd steps swing), at next_on in units. */
static u32 pos_pulse, pos_unit;
static u32 grid, grid_index;
static u64 next_on;
static u32 step, rng = RANDOM_SEED, last_note = 0xFFFFFFFFu;

/* MIDI clock: following it (ext); waiting for the first 0xF8 after a
 * Start or Continue (armed, and restart for a Start); ignoring it after a
 * Stop until a Start or Continue; the pulses taken; when the last came;
 * the last 25 arrivals (frames), to smooth the rate over 24; the rate in
 * units a frame. */
static u32 ext, armed, restart, ignoring, pulses, last_clock_block;
u32 arp_busy;

static void busy(void)
{
    arp_busy = running | ext;
}
/* MIDI clock out: running (a Start sent and no Stop since), and a Start
 * due at the next block (the grid starting again at pulse 0). */
static u32 out_running, out_start;
static u32 arrival[25], arrivals;
static u32 ext_rate;

static u64 units(u32 pulse, u32 unit)
{
    return (u64)pulse * ARP_UNIT + unit;
}

static u32 step_pulses(void)
{
    return rate_pulses[set.rate];
}

/* The units of a share (% of a step): a step is pulses x ARP_UNIT, and
 * ARP_UNIT / 100 = 37 500, so this fits 32 bits. */
static u32 share_units(u32 percent)
{
    return step_pulses() * (ARP_UNIT / 100u) * percent;
}

static void place_next(void)
{
    next_on = units(grid, 0) + ((grid_index & 1u) ? share_units(set.swing) : 0u);
}

/* The grid from here on: the next step at the next multiple of the step
 * at or after the clock's position. */
static void regrid(void)
{
    u32 l = step_pulses(), p = pos_pulse + (pos_unit ? 1u : 0u);

    grid_index = (p + l - 1u) / l;
    grid = grid_index * l;
    place_next();
}

static void restart_grid(void)
{
    pos_pulse = 0;
    pos_unit = 0;
    grid = 0;
    grid_index = 0;
    place_next();
    out_start = !ext;
}

static void clock_out(u32 status)
{
    fm_arp_clock_out(status);
    if (status == MIDI_CLOCK)
        sb_arp.clocks_out++;
}

/* MIDI clock out stops (the arpeggiator stops, or follows MIDI clock). */
static void clock_out_stop(void)
{
    if (out_running)
        clock_out(MIDI_STOP);
    out_running = 0;
    out_start = 0;
}

void arp_patch_of(const u8 *b, struct arp_patch *a)
{
    a->on = b[29] & 1u;
    a->latch = (u8)(b[29] >> 1 & 1u);
    a->mode = (u8)(b[29] >> 2 & 7u);
    a->octaves = (u8)((b[29] >> 5 & 3u) + 1u);
    a->rate = b[30] & 15u;
    a->swing = (u8)((b[30] >> 4) * 5u);
    a->gate = b[31];
}

void arp_patch_copy(struct arp_patch *to, const struct arp_patch *from)
{
    to->on = from->on;
    to->latch = from->latch;
    to->mode = from->mode;
    to->octaves = from->octaves;
    to->rate = from->rate;
    to->swing = from->swing;
    to->gate = from->gate;
}

void arp_settings(const struct arp_patch *a)
{
    u32 rate = a->rate != set.rate, swing = a->swing != set.swing;

    arp_patch_copy(&set, a);
    if (set.mode >= ARP_MODES)
        set.mode = ARP_UP;
    if (rate)
        regrid();
    else if (swing)
        place_next();
}

u32 arp_on(void)
{
    return running;
}

static void end_notes(u32 at)
{
    u32 i;

    for (i = 0; i < n_playing; i++)
        fm_arp_off(playing[i], at);
    sb_arp.notes_off += n_playing;
    n_playing = 0;
    sb_arp.sounding = 0;
}

void arp_silence(void)
{
    end_notes(0);
}

void arp_start(void)
{
    running = 1;
    n_held = keys_pressed_now = 0;
    n_playing = 0;
    step = 0;
    rng = RANDOM_SEED;
    if (ext)
        regrid();
    else
        restart_grid();
    sb_arp.marker = ARP_MARKER;
    sb_arp.on = 1;
    sb_arp.held = 0;
    busy();
}

void arp_stop(void)
{
    end_notes(0);
    clock_out_stop();
    running = 0;
    n_held = keys_pressed_now = 0;
    sb_arp.on = 0;
    sb_arp.held = 0;
    busy();
}

void arp_key(int note, u32 velocity, u32 down)
{
    u32 i, j;

    if (!running || note < 0 || note > 127)
        return;
    if (down) {
        keys_pressed_now++;
        /* LATCH: the first key down after none starts a new chord. */
        if (set.latch && keys_pressed_now == 1)
            n_held = 0;
        for (i = 0; i < n_held && held[i].note != note; i++)
            ;
        if (i == n_held) {
            if (!n_held) {
                /* Nothing was held: the pattern starts again, and on the
                 * internal clock so does the grid, so the first note plays
                 * now (on MIDI clock, at the next step). */
                step = 0;
                if (!ext)
                    restart_grid();
            }
            if (n_held == ARP_HELD) {
                for (j = 1; j < ARP_HELD; j++)
                    held[j - 1] = held[j];
                n_held--;
            }
            held[n_held].note = (u8)note;
            n_held++;
        }
        held[i < n_held ? i : n_held - 1].velocity = (u8)velocity;
    } else {
        if (keys_pressed_now)
            keys_pressed_now--;
        if (!set.latch) {
            for (i = j = 0; i < n_held; i++)
                if (held[i].note != note)
                    held[j++] = held[i];
            n_held = j;
        }
    }
    sb_arp.held = n_held;
}

/* The notes of this step: into notes[] and velocities[], how many. */
static u32 pattern(u8 *notes, u8 *velocities)
{
    u32 n = n_held, oct = set.octaves, count = n * oct, i, j, k, o;
    u8 sorted[ARP_HELD], vel[ARP_HELD];

    if (!n)
        return 0;
    /* By pitch, lowest first (UP, DOWN, UP/DOWN, RANDOM, CHORD), or as
     * they came (ORDER). */
    for (i = 0; i < n; i++) {
        u8 x = held[i].note, v = held[i].velocity;
        for (j = i; set.mode != ARP_ORDER && j > 0 && sorted[j - 1] > x; j--) {
            sorted[j] = sorted[j - 1];
            vel[j] = vel[j - 1];
        }
        sorted[j] = x;
        vel[j] = v;
    }
    if (set.mode == ARP_CHORD) {
        o = step % oct;
        for (i = 0; i < n; i++) {
            k = sorted[i] + 12u * o;
            while (k > 127u)
                k -= 12u;
            notes[i] = (u8)k;
            velocities[i] = vel[i];
        }
        return n;
    }
    switch (set.mode) {
    case ARP_DOWN:
        j = count - 1u - step % count;
        break;
    case ARP_UPDOWN:
        if (count == 1u) {
            j = 0;
        } else {
            i = step % (2u * count - 2u);
            j = i < count ? i : 2u * count - 2u - i;
        }
        break;
    case ARP_RANDOM:
        rng = rng * 1664525u + 1013904223u;
        j = (rng >> 8) % count;
        break;
    default:   /* UP, ORDER */
        j = step % count;
        break;
    }
    k = sorted[j % n] + 12u * (j / n);
    while (k > 127u)
        k -= 12u;
    notes[0] = (u8)k;
    velocities[0] = vel[j % n];
    return 1;
}

static void play_step(u32 at, u64 t, u32 block)
{
    u8 notes[ARP_HELD], velocities[ARP_HELD];
    u32 n, i, l = step_pulses();

    end_notes(at);
    n = pattern(notes, velocities);
    for (i = 0; i < n; i++) {
        fm_arp_on(notes[i], velocities[i], at);
        playing[i] = notes[i];
    }
    n_playing = n;
    sb_arp.sounding = n;
    if (n) {
        u32 k = sb_arp.log_count % ARP_LOG;
        step++;
        last_note = notes[0];
        sb_arp.steps++;
        sb_arp.notes_on += n;
        sb_arp.log_time[k] = block * AUDIO_FRAMES + at;
        sb_arp.log_note[k] = notes[0];
        sb_arp.log_count++;
        off_at = t + share_units(set.gate);
    }
    grid += l;
    grid_index++;
    place_next();
    /* A note ends at the next step at the latest (a swung step's gate). */
    if (off_at > next_on)
        off_at = next_on;
}

void arp_block(u32 block)
{
    u64 start, end, t;
    u32 r, d;

    if (ext && block - last_clock_block > ARP_LOST_BLOCKS) {
        ext = 0;
        armed = 0;
        sb_arp.losses++;
        sb_arp.clock = 0;
        busy();
        if (running && !out_start) {
            clock_out(MIDI_CONTINUE);
            out_running = 1;
        }
    }
    if (!running || (ext && armed))
        return;
    r = ext ? ext_rate : ARP_UNIT_FRAME * midi_settings.tempo;
    sb_arp.tempo_x10 = r * 10u / ARP_UNIT_FRAME;
    /* MIDI clock out, on the internal clock: a Start with pulse 0's
     * clock, then a clock each pulse the position passes this block. */
    if (!ext && out_start) {
        clock_out(MIDI_START);
        clock_out(MIDI_CLOCK);
        out_start = 0;
        out_running = 1;
    }
    start = units(pos_pulse, pos_unit);
    end = start + (u64)r * AUDIO_FRAMES;
    /* On MIDI clock, never more than a pulse past the last clock taken. */
    if (ext && end > units(pulses + 1u, 0))
        end = units(pulses + 1u, 0);
    for (;;) {
        u32 off = n_playing && off_at <= next_on, at;
        t = off ? off_at : next_on;
        if (t >= end)
            break;
        at = t <= start ? 0u : ((u32)(t - start) + r - 1u) / r;
        if (at >= AUDIO_FRAMES)
            at = AUDIO_FRAMES - 1u;
        if (off)
            end_notes(at);
        else
            play_step(at, t, block);
    }
    if (end > start) {
        u32 from = pos_pulse;
        d = (u32)(end - start);
        pos_unit += d % ARP_UNIT;
        pos_pulse += d / ARP_UNIT;
        if (pos_unit >= ARP_UNIT) {
            pos_unit -= ARP_UNIT;
            pos_pulse++;
        }
        if (!ext && out_running)
            for (; from != pos_pulse; from++)
                clock_out(MIDI_CLOCK);
    }
}

/* The rate over the last 24 clocks (fewer at first), in units a frame. */
static void clock_rate(u32 now)
{
    u32 k, then;

    if (arrivals == 25u) {
        for (k = 1; k < 25u; k++)
            arrival[k - 1] = arrival[k];
        arrivals--;
    }
    arrival[arrivals++] = now;
    if (arrivals < 2u)
        return;
    k = arrivals - 1u;
    then = arrival[0];
    if (now != then)
        ext_rate = ARP_UNIT * k / (now - then);
}

void arp_clock(u32 status, u32 block)
{
    switch (status) {
    case MIDI_CLOCK:
        if (ignoring)
            return;
        if (!ext || armed) {
            /* Following MIDI clock from here: a Start's first clock is
             * pulse 0 (the pattern starts again); otherwise the clock
             * takes the next whole pulse on. */
            if (ext && restart) {
                restart_grid();
                step = 0;
                end_notes(0);
            } else {
                pos_pulse += pos_unit ? 1u : 0u;
                pos_unit = 0;
            }
            if (!ext)
                ext_rate = ARP_UNIT_FRAME * midi_settings.tempo;
            pulses = pos_pulse;
            ext = 1;
            armed = 0;
            restart = 0;
            arrivals = 0;
            clock_out_stop();
        } else {
            pulses++;
            if (units(pos_pulse, pos_unit) < units(pulses, 0)) {
                pos_pulse = pulses;
                pos_unit = 0;
            }
        }
        clock_rate(block * AUDIO_FRAMES);
        last_clock_block = block;
        sb_arp.pulses++;
        break;
    case MIDI_START:
    case MIDI_CONTINUE:
        /* Until two clocks give a rate, the internal tempo's. */
        if (!ext)
            ext_rate = ARP_UNIT_FRAME * midi_settings.tempo;
        ext = 1;
        armed = 1;
        restart = status == MIDI_START;
        ignoring = 0;
        last_clock_block = block;
        if (restart)
            sb_arp.starts++;
        else
            sb_arp.continues++;
        break;
    case MIDI_STOP:
        /* The clock has stopped: the internal tempo takes over from here,
         * and clocks are ignored until a Start or Continue. */
        if (ext && running) {
            clock_out(MIDI_CONTINUE);
            out_running = 1;
        }
        ext = 0;
        armed = 0;
        ignoring = 1;
        sb_arp.stops++;
        break;
    }
    sb_arp.clock = ext;
    busy();
}

u32 arp_clock_source(void)
{
    return ext;
}

u32 arp_tempo_x10(void)
{
    return (ext ? ext_rate : ARP_UNIT_FRAME * midi_settings.tempo) * 10u / ARP_UNIT_FRAME;
}

int arp_last_note(void)
{
    return (int)last_note;
}
