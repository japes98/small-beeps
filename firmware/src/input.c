/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * The input layer (input.h): the panel's matrix scanned a column at a
 * time by TIMER1's interrupt, keys debounced, encoders decoded, the pot
 * read and filtered, the LEDs multiplexed with the scan, and one event
 * queue for main (docs/DESIGN-NOTES.md, M3).
 *
 * The scan: 12 slots of 83.3 us make 1 ms. In slot k (0 to 10) column k
 * is selected and its LEDs lit; slot 11 selects no column. Each slot's
 * interrupt first reads the rows of the column the slot before selected
 * (they had the whole slot to settle), then selects the next, then
 * works on what it read.
 */

#include "input.h"
#include "audio.h"
#include "WL82.h"

/* HW-33: the column shift registers on port A. A rising edge of PA3
 * shifts in PA4; one of PA1 copies the 16 bits to the outputs; a column
 * is selected while its bit is 0. Each shift moves every bit one place
 * up, so a single 0 shifted in before column 0 walks to column 10 with
 * one shift a slot, and one more shift leaves no column selected. */
#define PA_LATCH  (1u << 1)
#define PA_CLOCK  (1u << 3)
#define PA_DATA   (1u << 4)
/* HW-42: the LED lines of rows 1 to 4: PA9, PA10, PH6, PH9. */
#define PA_LED1   (1u << 9)
#define PA_LED2   (1u << 10)
#define PH_LED3   (1u << 6)
#define PH_LED4   (1u << 9)
#define PA_OURS   (PA_LATCH | PA_CLOCK | PA_DATA | PA_LED1 | PA_LED2)
#define PH_OURS   (PH_LED3 | PH_LED4)

#define COLUMNS   11u
#define ROWS      6u
#define SLOTS     12u

/* HW-48: TIMER1 runs with CON bits 0-1 non-zero, prescaler setting 2
 * divides the 24 MHz clock by 16, CON bit 14 acknowledges; 125 counts of
 * 1.5 MHz are 83.3 us. Source 5 (HW-19). */
#define SCAN_CON  0x21u
#define SCAN_ACK  (1u << 14)
#define SCAN_PRD  125u
#define SRC_TIMER1 5u
/* Below the tick (2), which may preempt it, level with SPI1 (1), and
 * above the audio engine (0), which it may preempt: docs/DESIGN-NOTES.md,
 * M3 and M4. */
#define PRIO_SCAN 1u

/* HW-40: the SARADC. CON bits 8-11 the channel (the pot is 4), bit 4
 * enables, bit 6 with it starts a conversion, bit 7 reads 1 when it is
 * done; RES holds 10 bits. The interrupt (bit 5, HW-60) is not used. */
#define ADC_START (4u << 8 | 1u << 4 | 1u << 6)
#define ADC_DONE  (1u << 7)

/* Keys: a change counts once the contact read the same in KEY_SAMPLES
 * scans in a row (3 ms of 1 ms scans: docs/DESIGN-NOTES.md, M3). */
#define KEY_SAMPLES 4u
/* The pot: the mean of its last 4 readings is reported when it moves
 * more than POT_DEAD from the last value reported, or reaches an end. */
#define POT_DEAD  3u
#define POT_MAX   1023u

/* HW-35 and HW-37: the key or button (its control ID, input.h) at each
 * column and row 1 to 4; NONE where there is none. */
#define NONE      0xFFu
static const u8 key_at[COLUMNS][4] = {
    {  5, 34, 23,  0 }, { 11, 35, 24,  1 }, {  4, 36, 25, 15 }, { 10, 37, 26, 14 },
    {  3, 38, 27, 17 }, {  9, 40, 28, 16 }, {  2, 39, 29, 19 }, {  8, 13, 30, 18 },
    { NONE, 7, 31, 20 }, { NONE, 6, 32, 21 }, { NONE, 12, 33, 22 },
};

/* HW-38 and HW-39: each encoder's contacts, A in column - 1 and B in
 * column, both on row; and its control. */
static const struct { u8 column, row, control; } encoders[] = {
    { 1, 0, INPUT_SELECT },  { 1, 5, INPUT_PRESETS }, { 3, 0, INPUT_ALGORITHM },
    { 5, 0, INPUT_KNOB4 },   { 7, 0, INPUT_KNOB3 },   { 9, 0, INPUT_KNOB2 },
    { 9, 1, INPUT_KNOB1 },
};
#define ENCODERS  (sizeof encoders / sizeof encoders[0])

/* One step of an encoder's contacts, (A << 1 | B) before and after: +1
 * along clockwise's order (B closes, A closes, B opens, A opens: 0, 1,
 * 3, 2, 0), -1 against it, 0 for no change or both changing at once. */
static const s8 quarter[16] = { 0, 1, -1, 0, -1, 0, 0, 1, 1, 0, 0, -1, 0, -1, 1, 0 };

/* LED brightness: in which of 8 scans in a row a level of n eighths is
 * lit, spread out (bit-reversed order). */
static const u8 led_order[8] = { 0, 4, 2, 6, 1, 5, 3, 7 };

volatile struct sb_input_record sb_input __attribute__((section(".beacon.input")));

static u32 slot, phase, pa_base, ph_base;
/* Per column: the rows read (1 = closed), the last KEY_SAMPLES readings of
 * its key rows a byte each, those readings if all were the debounced
 * state, the debounced state, and which rows hold keys. */
static u8 last_rows[COLUMNS], held[COLUMNS], key_rows[COLUMNS];
static u32 history[COLUMNS], steady[COLUMNS];
/* Per odd column: its encoder rows, and their contacts last decoded. */
static u8 enc_rows[COLUMNS];
static u16 enc_seen[COLUMNS];
static u8 enc_ab[ENCODERS];
static s8 enc_steps[ENCODERS];
/* Each control's column << 4 | row, for its LED. */
static u8 key_place[INPUT_LEDS];
/* The LED lines to drive in each slot of each of 8 scans: port A's bits
 * in the low half, port H's in the high half; and this scan's row. */
static u32 led_lines[8][SLOTS];
static const u32 *led_row = led_lines[0];
static u16 pot_last[4];
static u32 pot_sum, pot_next, pot_shown;

static struct input_event queue[INPUT_QUEUE];
static volatile u32 queue_in, queue_out;
/* The audio engine's queue (since M4). */
static struct input_event audio_queue[INPUT_QUEUE];
static volatile u32 audio_in, audio_out;
/* The time of the last event input_read() handed out. */
static u32 taken_time;
#if defined(SB_TEST_LED_SHOW)
/* The column of the last input_led() call, until the scan drives it, and
 * when the call was (R-LED-3's test build). */
static volatile u32 show_column = NONE, show_from;
#endif

/* Queues an event (and logs it), and tells main. Interrupt context. */
static void emit(u32 control, u32 kind, int value)
{
    u32 t = sb_ticks(), n = sb_input.events, in = queue_in;
    volatile struct input_event *l = &sb_input.log[n % INPUT_LOG];

    l->control = (u8)control;
    l->kind = (u8)kind;
    l->value = (s16)value;
    l->time = t;
    sb_input.events = n + 1;
    if (in - queue_out >= INPUT_QUEUE) {
        sb_input.dropped++;
    } else {
        struct input_event *e = &queue[in % INPUT_QUEUE];
        e->control = (u8)control;
        e->kind = (u8)kind;
        e->value = (s16)value;
        e->time = t;
        queue_in = in + 1;
    }
    in = audio_in;
    if (in - audio_out >= INPUT_QUEUE) {
        sb_audio.dropped++;
    } else {
        struct input_event *e = &audio_queue[in % INPUT_QUEUE];
        e->control = (u8)control;
        e->kind = (u8)kind;
        e->value = (s16)value;
        e->time = t;
        audio_in = in + 1;
    }
    sb_work++;
}

/* The key rows of one column, just read: debounce, and report changes. */
static inline __attribute__((always_inline)) void keys(u32 c, u32 rows)
{
    u32 h = history[c] << 8 | (rows & key_rows[c]), on, off, now, changed, r;

    history[c] = h;
    if (h == steady[c])
        return;
    on = h & h >> 8 & h >> 16 & h >> 24;
    off = ~(h | h >> 8 | h >> 16 | h >> 24) & key_rows[c];
    now = (held[c] | on) & ~off & 0xFFu;
    changed = now ^ held[c];
    if (!changed)
        return;
    held[c] = (u8)now;
    steady[c] = now * 0x01010101u;
    for (r = 1; r <= 4; r++) {
        if (changed >> r & 1) {
            u32 k = key_at[c][r - 1], down = now >> r & 1;
            sb_input.values[k] = (int)down;
            emit(k, down ? INPUT_PRESS : INPUT_RELEASE, (int)down);
        }
    }
}

/* The encoders whose B contact is in odd column c, now that both their
 * columns are read: one event per detent, when the contacts are back at
 * rest (both open) after moving more forward than back. */
static inline __attribute__((always_inline)) void turns(u32 c, u32 a_rows, u32 b_rows)
{
    u32 m = enc_rows[c], seen = (a_rows & m) | (b_rows & m) << 6, i;

    if (seen == enc_seen[c])
        return;
    enc_seen[c] = (u16)seen;
    for (i = 0; i < ENCODERS; i++) {
        u32 row = encoders[i].row, ab;
        int steps;

        if (encoders[i].column != c)
            continue;
        ab = (a_rows >> row & 1) << 1 | (b_rows >> row & 1);
        if (ab == enc_ab[i])
            continue;
        steps = enc_steps[i] + quarter[enc_ab[i] << 2 | ab];
        enc_ab[i] = (u8)ab;
        if (ab == 0) {
            int d = steps >= 2 ? 1 : steps <= -2 ? -1 : 0;
            steps = 0;
            if (d) {
                sb_input.values[encoders[i].control] += d;
                emit(encoders[i].control, INPUT_TURN, d);
            }
        }
        enc_steps[i] = (s8)steps;
    }
}

/* Once a scan: the pot's reading from the conversion started a scan ago,
 * and the next one started. */
static void pot(void)
{
    if (JL_ADC->CON & ADC_DONE) {
        u32 v = JL_ADC->RES & POT_MAX, i = pot_next, mean, shown = pot_shown;

        sb_input.pot_raw = v;
        pot_sum += v - pot_last[i];
        pot_last[i] = (u16)v;
        pot_next = (i + 1) & 3;
        mean = pot_sum >> 2;
        if (mean > shown + POT_DEAD || mean + POT_DEAD < shown
            || (mean != shown && (mean == 0 || mean == POT_MAX))) {
            pot_shown = mean;
            sb_input.values[INPUT_MASTER] = (int)mean;
            emit(INPUT_MASTER, INPUT_MOVE, (int)mean);
        }
    }
    JL_ADC->CON = ADC_START;
}

/* TIMER1: one slot of the scan. The ports' other bits are kept in
 * locals: the compiler would read them again after every port write. */
void input_scan(void)
{
    u32 s = slot, base = pa_base, hbase = ph_base, pa, pb, rows, data, lit;

    JL_TIMER1->CON = SCAN_CON | SCAN_ACK;
    pa = JL_PORTA->IN;
    pb = JL_PORTB->IN;
    if (!s) {
        u32 ph = (phase + 1) & 7;
        phase = ph;
        led_row = led_lines[ph];
    }
    lit = led_row[s];

    /* LEDs off; shift in a 0 for column 0, else a 1; latch; LEDs on. */
    data = s ? PA_DATA : 0;
#if !defined(SB_COST_NO_LEDS)
    JL_PORTA->OUT = base | data;
    JL_PORTH->OUT = hbase;
    JL_PORTA->OUT = base | data | PA_CLOCK;
    JL_PORTA->OUT = base | PA_LATCH;
    JL_PORTA->OUT = base | (lit & 0xFFFFu);
    JL_PORTH->OUT = hbase | lit >> 16;
#else
    (void)hbase;
    (void)lit;
    JL_PORTA->OUT = base | data;
    JL_PORTA->OUT = base | data | PA_CLOCK;
    JL_PORTA->OUT = base | PA_LATCH;
    JL_PORTA->OUT = base;
#endif
    slot = s == SLOTS - 1 ? 0 : s + 1;
#if defined(SB_TEST_LED_SHOW)
    if (s == show_column) {
        u32 d = sb_ticks() - show_from;
        if (d > sb_input.led_show_max)
            sb_input.led_show_max = d;
        show_column = NONE;
    }
#endif

    if (!s) {
        sb_input.cycles++;
#if !defined(SB_COST_NO_POT)
        pot();
#else
        (void)pot;
#endif
        return;
    }
    /* HW-34: rows 0 to 5 on PA0, PA5-PA8 and PB7, 0 while closed. */
    s--;
    rows = ~((pa & 1) | (pa >> 4 & 0x1Eu) | (pb >> 2 & 0x20u)) & 0x3Fu;
#if !defined(SB_COST_NO_KEYS)
    keys(s, rows);
#else
    (void)keys;
#endif
#if !defined(SB_COST_NO_ENC)
    if (s & 1)
        turns(s, last_rows[s - 1], rows);
    last_rows[s] = (u8)rows;
#else
    (void)turns;
    (void)last_rows;
#endif
}

int input_read(struct input_event *e)
{
    u32 out = queue_out;

    if (out == queue_in)
        return 0;
    *e = queue[out % INPUT_QUEUE];
    taken_time = e->time;
    queue_out = out + 1;
    sb_input.taken++;
    return 1;
}

int input_read_audio(struct input_event *e)
{
    u32 out = audio_out;

    if (out == audio_in)
        return 0;
    *e = audio_queue[out % INPUT_QUEUE];
    audio_out = out + 1;
    return 1;
}

int input_value(u32 control)
{
    return control < INPUT_CONTROLS ? sb_input.values[control] : 0;
}

void input_led(u32 control, u32 level)
{
    u32 n, c, r, p, t;

    if (control >= INPUT_LEDS)
        return;
    n = ((level > INPUT_LED_FULL ? INPUT_LED_FULL : level) * 8 + INPUT_LED_FULL / 2) / INPUT_LED_FULL;
    c = key_place[control] >> 4;
    r = key_place[control] & 0xFu;
    for (p = 0; p < 8; p++) {
        u32 bit = r == 1 ? PA_LED1 : r == 2 ? PA_LED2 : r == 3 ? PH_LED3 << 16 : PH_LED4 << 16;
        u32 *w = &led_lines[p][c];

        *w = led_order[p] < n ? *w | bit : *w & ~bit;
    }
    t = sb_ticks();
    if (t - taken_time > sb_input.led_lag_max)
        sb_input.led_lag_max = t - taken_time;
    sb_input.led_calls++;
    sb_input.led_time = t;
    sb_input.led_control = control << 8 | level;
#if defined(SB_TEST_LED_SHOW)
    show_from = t;
    show_column = c;
#endif
}

void input_start(void)
{
    u32 c, r, i, v;

    for (c = 0; c < COLUMNS; c++)
        for (r = 1; r <= 4; r++)
            if (key_at[c][r - 1] != NONE) {
                key_rows[c] |= (u8)(1u << r);
                key_place[key_at[c][r - 1]] = (u8)(c << 4 | r);
            }
    for (i = 0; i < ENCODERS; i++)
        enc_rows[encoders[i].column] |= (u8)(1u << encoders[i].row);

    /* The pins' other bits are left as they are (Q-7: no pin set-up). The
     * registers' state at power-up is unknown, so 16 ones go in first:
     * no column selected. */
    pa_base = JL_PORTA->OUT & ~PA_OURS;
    ph_base = JL_PORTH->OUT & ~PH_OURS;
    JL_PORTH->OUT = ph_base;
    for (i = 0; i < 16; i++) {
        JL_PORTA->OUT = pa_base | PA_DATA;
        JL_PORTA->OUT = pa_base | PA_DATA | PA_CLOCK;
    }
    JL_PORTA->OUT = pa_base | PA_LATCH;
    JL_PORTA->OUT = pa_base;

    /* The pot's first reading, waited for, so input_value() has it from
     * the start. */
    JL_ADC->CON = ADC_START;
    for (i = 0; i < 1000 && !(JL_ADC->CON & ADC_DONE); i++)
        ;
    v = JL_ADC->RES & POT_MAX;
    for (i = 0; i < 4; i++)
        pot_last[i] = (u16)v;
    pot_sum = 4 * v;
    pot_shown = v;
    sb_input.values[INPUT_MASTER] = (int)v;
    JL_ADC->CON = ADC_START;

#if defined(SB_COST_NO_SCAN)
    return;
#endif
    sb_irq_enable(SRC_TIMER1, input_scan, PRIO_SCAN);
    JL_TIMER1->CNT = 0;
    JL_TIMER1->PRD = SCAN_PRD;
    JL_TIMER1->CON = SCAN_CON;
}
