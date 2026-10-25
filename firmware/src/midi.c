/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * MIDI in (M6a): the receive ring and our own MIDI 1.0 byte parser,
 * written from the MIDI 1.0 specification's rules for status, running
 * status, realtime and System Exclusive bytes (docs/DESIGN-NOTES.md,
 * M6a, "The parser"; PROVENANCE P-43), and the receiver: UART1's
 * receive DMA (HW-67 to HW-71). The engine side is in fm_play.c.
 */

#include "midi.h"
#include "WL82.h"

volatile struct sb_midi_record sb_midi __attribute__((section(".beacon.midi")));

struct midi_settings midi_settings;

/* The ring: midi_rx_byte() writes at head, midi_read() reads at tail;
 * each index is written by one side only, so a receiver in an interrupt
 * could write it too. */
static volatile u8 ring[MIDI_RING];
static volatile u32 head, tail;

void midi_rx_byte(u8 b)
{
    u32 h = head;

    sb_midi.bytes++;
    if (h - tail >= MIDI_RING) {
        sb_midi.ring_dropped++;
        return;
    }
    ring[h % MIDI_RING] = b;
    head = h + 1;
}

/* --- The receiver (HW-67 to HW-71) ---------------------------------------
 * The jack's bytes reach UART1, whose receive DMA writes them into a ring
 * of our own (HW-70). Once a block the engine latches how many it wrote
 * since the last time (CON0 bit 7 into HRXCNT, HW-69) and takes them, so
 * no interrupt is needed: the engine acts on MIDI once a block anyway. In
 * fwtest no baud rate, UART clock or pin needs setting (HW-71); on the
 * chip they are still open (Q-12), so this sets none yet. */
#define UART_ON     (1u << 0)   /* HW-70 */
#define UART_RX_DMA (1u << 6)   /* HW-70 */
#define UART_LATCH  (1u << 7)   /* HW-69: the count since the last latch into HRXCNT */
#define MIDI_DMA    256u        /* the DMA's ring: 82 ms of the wire */

static volatile u8 dma_ring[MIDI_DMA] __attribute__((aligned(4)));
static u32 dma_at;

void midi_start(void)
{
    JL_UART1->RXCNT = 0;                         /* no receive pending (HW-70) */
    JL_UART1->RXEADR = (u32)(dma_ring + MIDI_DMA);
    JL_UART1->RXSADR = (u32)dma_ring;            /* starts the DMA at the ring's start */
    JL_UART1->CON0 = UART_ON | UART_RX_DMA;
}

void midi_poll(void)
{
    u32 n;

    JL_UART1->CON0 = UART_ON | UART_RX_DMA | UART_LATCH;
    n = JL_UART1->HRXCNT;
    if (n > MIDI_DMA) {
        /* More than the ring since the last block: the oldest were
         * written over (HW-71); count them lost. */
        sb_midi.bytes += n - MIDI_DMA;
        sb_midi.ring_dropped += n - MIDI_DMA;
        dma_at = (dma_at + n - MIDI_DMA) % MIDI_DMA;
        n = MIDI_DMA;
    }
    while (n--) {
        midi_rx_byte(dma_ring[dma_at]);
        dma_at = (dma_at + 1) % MIDI_DMA;
    }
}

/* The screen's queue: the engine writes at shead, main reads at stail. */
static volatile u32 screen_q[MIDI_SCREEN];
static volatile u32 shead, stail;

void midi_screen_post(u32 channel, int note, u32 velocity)
{
    u32 h = shead;

    if (h - stail >= MIDI_SCREEN)
        return;
    screen_q[h % MIDI_SCREEN] = channel << 16 | (u32)note << 8 | velocity;
    shead = h + 1;
    sb_work++;              /* wakes main to draw it */
}

int midi_screen_take(u32 *note)
{
    u32 t = stail;

    if (t == shead)
        return 0;
    *note = screen_q[t % MIDI_SCREEN];
    stail = t + 1;
    return 1;
}

/* The parser's state: the status the next data bytes belong to (0: none),
 * how many data bytes it takes and has, and whether a SysEx is being
 * skipped (and how long it is so far). */
static u8 status, need, have, data[2];
static u32 sysex, sysex_len;

void midi_parser_reset(void)
{
    status = 0;
    need = have = 0;
    sysex = 0;
    sysex_len = 0;
}

static void log_msg(const struct midi_msg *m)
{
    volatile u8 *e = sb_midi.log[sb_midi.log_count % MIDI_LOG];

    e[0] = m->status;
    e[1] = m->data[0];
    e[2] = m->data[1];
    e[3] = m->length;
    sb_midi.log_count++;
    sb_midi.messages++;
}

/* Data bytes a status takes: channel messages by kind, system common by
 * status; 0xFF for an undefined status. */
static u8 data_bytes(u8 s)
{
    switch (s & 0xF0u) {
    case MIDI_PROGRAM:
    case MIDI_CHANNEL_AT:
        return 1;
    case 0xF0u:
        break;
    default:
        return 2;
    }
    switch (s) {
    case 0xF1u:            /* MIDI time code quarter frame */
    case 0xF3u:            /* song select */
        return 1;
    case 0xF2u:            /* song position */
        return 2;
    case 0xF6u:            /* tune request */
        return 0;
    default:               /* F4, F5: undefined */
        return 0xFFu;
    }
}

/* A status byte ends a SysEx being skipped, and a message still waiting
 * for its data. */
static void end_pending(void)
{
    if (sysex) {
        sb_midi.sysex_cut++;
        sysex = 0;
    }
    if (status && have)
        sb_midi.cut++;
    have = 0;
}

int midi_parse(u8 b, struct midi_msg *m)
{
    sb_midi.parsed++;
    if (b >= 0xF8u) {
        /* Realtime: anywhere, a message of its own; F9 and FD are
         * undefined. Nothing else changes, except at a reset. */
        if (b == 0xF9u || b == 0xFDu) {
            sb_midi.undefined++;
            return 0;
        }
        m->status = b;
        m->data[0] = m->data[1] = 0;
        m->length = 0;
        sb_midi.realtime++;
        log_msg(m);
        if (b == MIDI_RESET) {
            end_pending();
            midi_parser_reset();
        }
        return 1;
    }
    if (b >= 0x80u) {
        u8 n = data_bytes(b);
        int done = 0;

        if (b == MIDI_EOX && sysex) {
            /* The end of a SysEx: handed on with its length (7 bits a
             * byte, capped), for the log only. */
            m->status = MIDI_SYSEX;
            m->data[0] = (u8)(sysex_len & 0x7Fu);
            m->data[1] = (u8)(sysex_len >> 7 > 0x7Fu ? 0x7Fu : sysex_len >> 7);
            m->length = 2;
            sysex = 0;
            log_msg(m);
            done = 1;
        } else {
            end_pending();
        }
        /* Every status but realtime ends running status; a channel
         * status starts it again. */
        status = 0;
        need = 0;
        if (b == MIDI_SYSEX) {
            sysex = 1;
            sysex_len = 0;
            sb_midi.sysex++;
        } else if (b == MIDI_EOX) {
            if (!done)
                sb_midi.undefined++;      /* an EOX with no SysEx */
        } else if (n == 0xFFu) {
            sb_midi.undefined++;
        } else if (n == 0) {
            m->status = b;                 /* tune request */
            m->data[0] = m->data[1] = 0;
            m->length = 0;
            log_msg(m);
            done = 1;
        } else {
            status = b;
            need = n;
        }
        return done;
    }
    /* A data byte. */
    if (sysex) {
        sysex_len++;
        sb_midi.sysex_bytes++;
        if (sysex_len == MIDI_SYSEX_LIMIT + 1)
            sb_midi.sysex_long++;
        return 0;
    }
    if (!status) {
        sb_midi.orphans++;
        return 0;
    }
    data[have++] = b;
    if (have < need)
        return 0;
    m->status = status;
    m->data[0] = data[0];
    m->data[1] = need > 1 ? data[1] : 0;
    m->length = need;
    have = 0;
    if (status >= 0xF0u)
        status = 0;                        /* system common: no running status */
    log_msg(m);
    return 1;
}

int midi_read(struct midi_msg *m)
{
    while (tail != head) {
        u8 b = ring[tail % MIDI_RING];
        tail = tail + 1;
        if (midi_parse(b, m))
            return 1;
    }
    return 0;
}

/* The default controller map (docs/DESIGN-NOTES.md, M6a). */
static const u8 default_routes[][2] = {
    { 1, MIDI_TO_MOD },             /* modulation wheel */
    { 7, MIDI_TO_VOLUME },
    { 11, MIDI_TO_EXPRESSION },
    { 64, MIDI_TO_SUSTAIN },        /* damper pedal */
    { 16, MIDI_TO_KNOB1 },          /* general purpose 1 to 4 */
    { 17, MIDI_TO_KNOB2 },
    { 18, MIDI_TO_KNOB3 },
    { 19, MIDI_TO_KNOB4 },
    { 5, MIDI_TO_KNOB2 },           /* portamento time: the glide */
    { 74, MIDI_TO_KNOB3 },          /* brightness: the modulators' level */
};

void midi_settings_default(struct midi_settings *s)
{
    u32 i, n = sizeof default_routes / sizeof default_routes[0];

    s->version = MIDI_SETTINGS_VERSION;
    s->channel = MIDI_OMNI;
    s->bend_range = 2;
    s->routes = (u8)n;
    for (i = 0; i < MIDI_CC_ROUTES; i++) {
        s->cc[i].cc = i < n ? default_routes[i][0] : 0;
        s->cc[i].to = i < n ? default_routes[i][1] : MIDI_TO_NONE;
    }
    s->out_channel = 1;
    s->thru = 0;
    s->local = 1;
    s->knobs = 0;
    s->tempo = 120;
    s->arp_out = 0;
}
