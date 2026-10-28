/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * MIDI out (M6b): the queue, its policy, running status and the
 * transmitter, UART1's transmit DMA (HW-73, HW-74), written from the MIDI
 * 1.0 specification's wire format and running status rules (PROVENANCE
 * P-43) and docs/DESIGN-NOTES.md, M6b. What the engine sends is in
 * fm_play.c.
 */

#include "midi_out.h"
#include "WL82.h"

volatile struct sb_midi_out_record sb_midi_out __attribute__((section(".beacon.midiout")));

/* UART1's CON0 (HW-69, HW-70, HW-73): every write keeps the UART and the
 * receive DMA on (midi.c's receiver); bit 13 written as 1 clears the
 * transmit pending, bit 15, set when a transfer's last byte has gone. */
#define UART_ON         (1u << 0)
#define UART_RX_DMA     (1u << 6)
#define UART_TX_CLEAR   (1u << 13)
#define UART_TX_PENDING (1u << 15)

/* The queue: written at head, sent from tail; one context only. */
static struct midi_msg queue[MIDI_OUT_QUEUE];
static u32 head, tail;

/* The transfer on the wire: its bytes stay as they are until it is done. */
static u8 tx_buf[MIDI_OUT_CHUNK + 4] __attribute__((aligned(4)));
static u32 busy, last_status;

/* Note ons the policy dropped, a bit per channel and note: their note
 * offs are dropped too. */
static u32 dropped_on[16][4];

/* Raw bytes (BR-8): the caller sets the buffer and its length, then
 * raises raw_req; the poll streams it and answers with raw_ack. */
volatile struct sb_midi_out_raw_record sb_midi_out_raw;
static const u8 *volatile raw_buf;
static volatile u32 raw_len, raw_req, raw_ack;
static u32 raw_at;

static u32 kind(const struct midi_msg *m)
{
    return m->status & 0xF0u;
}

/* A note off, or a message that ends notes: these may use the reserve. */
static int ends_notes(const struct midi_msg *m)
{
    u32 k = kind(m);

    return k == MIDI_NOTE_OFF || (k == MIDI_NOTE_ON && !m->data[1])
        || (k == MIDI_CC && (m->data[0] == 120 || m->data[0] == 123));
}

/* A message whose latest value is all that matters: pressure, pitch bend,
 * program change, and control changes but those read in sequence (data
 * entry and the parameter numbers: 6, 38, 96 to 101) and the channel mode
 * messages (120 to 127). */
static int mergeable(const struct midi_msg *m)
{
    u32 c = m->data[0];

    switch (kind(m)) {
    case MIDI_POLY_AT:
    case MIDI_PROGRAM:
    case MIDI_CHANNEL_AT:
    case MIDI_BEND:
        return 1;
    case MIDI_CC:
        return !(c == 6 || c == 38 || (c >= 96 && c <= 101) || c >= 120);
    default:
        return 0;
    }
}

/* Puts m's value into a waiting message of the same kind, channel and
 * controller (or note), looking back from the newest over mergeable
 * messages only, so nothing moves past a note or a mode message. */
static int merge(const struct midi_msg *m)
{
    u32 i = head;

    while (i != tail) {
        struct midi_msg *w = &queue[--i % MIDI_OUT_QUEUE];
        if (w->status == m->status && (m->length == 1 || kind(m) == MIDI_BEND || w->data[0] == m->data[0])) {
            w->data[0] = m->data[0];
            w->data[1] = m->data[1];
            sb_midi_out.merged++;
            return 1;
        }
        if (!mergeable(w))
            break;
    }
    return 0;
}

/* Makes room for a note off in a full queue: the newest waiting message
 * that ends no notes is dropped (a note on so dropped has its note off
 * dropped too). 0 if every waiting message ends notes. */
static int evict(void)
{
    u32 i = head;

    while (i != tail) {
        struct midi_msg *w = &queue[--i % MIDI_OUT_QUEUE];
        if (!ends_notes(w)) {
            if (kind(w) == MIDI_NOTE_ON)
                dropped_on[w->status & 0x0Fu][w->data[0] >> 5] |= 1u << (w->data[0] & 31);
            for (; i + 1 != head; i++)
                queue[i % MIDI_OUT_QUEUE] = queue[(i + 1) % MIDI_OUT_QUEUE];
            head--;
            sb_midi_out.dropped++;
            return 1;
        }
    }
    return 0;
}

/* A note off whose note on was dropped: dropped as well. */
static int off_of_dropped(u32 *bits, u32 note, u32 bit)
{
    if (!(bits[note >> 5] & bit))
        return 0;
    bits[note >> 5] &= ~bit;
    sb_midi_out.offs_dropped++;
    return 1;
}

int midi_out_send(const struct midi_msg *m)
{
    u32 k = kind(m), ch = m->status & 0x0Fu, note = m->data[0] & 0x7Fu;
    u32 *bits = dropped_on[ch], bit = 1u << (note & 31), off, waiting;

    off = k == MIDI_NOTE_OFF || (k == MIDI_NOTE_ON && !m->data[1]);
    if (off && off_of_dropped(bits, note, bit))
        return 0;
    if (mergeable(m) && merge(m))
        return 1;
    waiting = head - tail;
    if (!ends_notes(m) && waiting >= MIDI_OUT_QUEUE - MIDI_OUT_RESERVE) {
        sb_midi_out.dropped++;
        if (k == MIDI_NOTE_ON)
            bits[note >> 5] |= bit;
        return 0;
    }
    if (waiting >= MIDI_OUT_QUEUE) {
        if (!evict()) {
            sb_midi_out.offs_lost++;
            return 0;
        }
        /* The message dropped may have been this note off's note on. */
        if (off && off_of_dropped(bits, note, bit))
            return 0;
        waiting--;
    }
    if (k == MIDI_NOTE_ON)
        bits[note >> 5] &= ~bit;
    queue[head % MIDI_OUT_QUEUE] = *m;
    head++;
    sb_midi_out.queued++;
    if (waiting + 1 > sb_midi_out.waiting_max)
        sb_midi_out.waiting_max = waiting + 1;
    return 1;
}

int midi_out_raw(const u8 *buf, u32 len)
{
    if (raw_req != raw_ack || !len)
        return 0;
    raw_buf = buf;
    raw_len = len;
    sb_midi_out_raw.streams++;
    raw_req = raw_req + 1;        /* last: the poll takes it from here */
    return 1;
}

int midi_out_raw_busy(void)
{
    return raw_req != raw_ack;
}

/* Takes the realtime messages out of the queue, the others keeping their
 * order, into out: their status bytes, at most room. */
static u32 take_realtime(u8 *out, u32 room)
{
    u32 i, w = tail, n = 0;

    for (i = tail; i != head; i++) {
        const struct midi_msg *m = &queue[i % MIDI_OUT_QUEUE];
        if (m->status >= 0xF8u && n < room) {
            out[n++] = m->status;
            sb_midi_out.messages++;
            sb_midi_out_raw.realtime++;
            continue;
        }
        if (w != i)
            queue[w % MIDI_OUT_QUEUE] = *m;
        w++;
    }
    head = w;
    return n;
}

/* A stream's next transfer: the realtime messages waiting, then its next
 * bytes. Its last byte handed on, the caller may use the buffer again. */
static u32 raw_chunk(void)
{
    u32 n = take_realtime(tx_buf, MIDI_OUT_CHUNK), len = raw_len;
    const u8 *buf = raw_buf;

    while (n < MIDI_OUT_CHUNK && raw_at < len)
        tx_buf[n++] = buf[raw_at++];
    sb_midi_out_raw.bytes += n;
    if (raw_at == len) {
        raw_at = 0;
        last_status = 0;          /* the next message carries its status */
        sb_midi_out_raw.done++;
        raw_ack = raw_req;
    }
    return n;
}

int midi_out_channel(u32 k, u32 d1, u32 d2)
{
    struct midi_msg m;

    m.status = (u8)(k | ((midi_settings.out_channel - 1u) & 0x0Fu));
    m.data[0] = (u8)(d1 & 0x7Fu);
    m.data[1] = (u8)(d2 & 0x7Fu);
    m.length = k == MIDI_PROGRAM || k == MIDI_CHANNEL_AT ? 1 : 2;
    return midi_out_send(&m);
}

void midi_out_poll(void)
{
    u32 n = 0;

    if (busy) {
        if (!(JL_UART1->CON0 & UART_TX_PENDING)) {
            sb_midi_out.polls_busy++;
            return;
        }
        JL_UART1->CON0 = UART_ON | UART_RX_DMA | UART_TX_CLEAR;
        busy = 0;
    }
    if (raw_req != raw_ack) {
        /* Raw bytes go first; the queue waits, but for realtime. */
        n = raw_chunk();
        goto send;
    }
    if (tail == head) {
        last_status = 0;           /* the wire has gone quiet */
        return;
    }
    /* Whole messages, up to MIDI_OUT_CHUNK bytes. */
    while (tail != head) {
        const struct midi_msg *m = &queue[tail % MIDI_OUT_QUEUE];
        u32 st = m->status, run = st < 0xF0u && st == last_status, i;

        if (n + m->length + !run > MIDI_OUT_CHUNK)
            break;
        if (run)
            sb_midi_out.running++;
        else
            tx_buf[n++] = (u8)st;
        for (i = 0; i < m->length; i++)
            tx_buf[n++] = m->data[i] & 0x7Fu;
        if (st < 0xF0u)
            last_status = st;
        else if (st < 0xF8u)
            last_status = 0;       /* system common */
        tail++;
        sb_midi_out.messages++;
    }
send:
    JL_UART1->TXADR = (u32)tx_buf;
    JL_UART1->TXCNT = n;           /* last: it starts the transfer (HW-73) */
    busy = 1;
    sb_midi_out.transfers++;
    sb_midi_out.bytes += n;
    sb_midi_out.last_start_tick = sb_ticks();
}
